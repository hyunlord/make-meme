# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
# Import from the existing pinned SCAIL worker; no dependency installation.
"""Reversible image-only attention output gate; upstream files remain read-only."""
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass
from enum import StrEnum
from pathlib import Path
from types import MethodType
from typing import Final, TypedDict, assert_never
import hashlib
import inspect
import json
import textwrap
import torch
from safetensors.torch import load_file
from torch import Tensor, nn

SOURCE_SHA256: Final = 'bbcfc38ee8c4dc8e9f31987e617b57af267c46e8bd25ee046f76e7426d6f5d6c'
Forward = Callable[[nn.Module, Tensor, Tensor, Tensor | None], Tensor]


class GateMode(StrEnum):
    OFF = 'OFF'
    METHOD = 'METHOD'
    CONTROL = 'CONTROL'


@dataclass(frozen=True, slots=True)
class GateConfig:
    mode: GateMode
    strength: float = .5
    report_path: Path | None = None


@dataclass(frozen=True, slots=True)
class TokenLayout:
    start: int
    length: int
    suffix: int
    grid: tuple[int, int, int]


class GateReport(TypedDict):
    mode: str
    strength: float
    source_sha256: str
    patched_forward_sha256: str
    source_diff: str
    support_sha256: str
    block_calls: dict[str, int]
    layouts: dict[str, dict[str, int | tuple[int, int, int]]]
    first_gate: dict[str, str | float | list[int] | list[float]]
    extra_forward: int


def coefficients(support: Tensor, mode: GateMode, strength: float) -> Tensor:
    """Return fresh float32 coefficients, preserving each time-slice mean."""
    assert support.ndim == 3 and support.dtype == torch.float32
    assert bool(torch.isfinite(support).all()) and 0 <= float(support.min()) <= float(support.max()) <= 1
    assert 0 <= strength <= .5
    match mode:
        case GateMode.OFF:
            return torch.ones_like(support)
        case GateMode.METHOD:
            selected = support
        case GateMode.CONTROL:
            selected = torch.roll(support, (support.shape[1]//2, support.shape[2]//2), (1,2))
        case unreachable:
            assert_never(unreachable)
    return 1 + strength * (selected - support.mean((1,2), keepdim=True))


def apply_generated(image: Tensor, weights: Tensor, layout: TokenLayout) -> Tensor:
    """Only generated image features change; preserve input tensor and its dtype."""
    assert tuple(weights.shape) == layout.grid
    assert image.ndim == 3 and image.shape[1] == layout.start + layout.length + layout.suffix
    assert layout.length == weights.numel()
    end = layout.start + layout.length
    generated = image[:, layout.start:end] * weights.to(device=image.device, dtype=image.dtype).reshape(1,-1,1)
    return torch.cat((image[:, :layout.start], generated, image[:, end:]), dim=1)


def compile_forward(original: Forward, transform: Callable[[Tensor], Tensor]) -> Forward:
    """Compile exactly one addition-site insertion in the pinned official function."""
    source = textwrap.dedent(inspect.getsource(original))
    needle = '    x = x + img_x\n'
    assert source.count(needle) == 1
    patched = source.replace(needle, '    img_x = _b029_image_gate(img_x)\n' + needle)
    namespace = dict(original.__globals__)
    namespace['_b029_image_gate'] = transform
    exec(compile(patched, '<B029-image-only-insertion>', 'exec'), namespace)
    return namespace['forward']


class BlockState:
    """Mutable per-block call counter/layout; stores no model activations."""
    def __init__(self, name: str, weights: Tensor, owner: 'GateInstallation') -> None:
        self.name = name
        self.weights = weights
        self.owner = owner
        self.layout: TokenLayout | None = None
        self.calls = 0
        self.converted: Tensor | None = None

    def bind(self, module: nn.Module, args: tuple[Tensor, ...], kwargs: Mapping[str, int | Tensor]) -> None:
        """Read actual official block metadata before cross-attention executes."""
        del module
        grid = kwargs['grid_sizes']
        assert isinstance(grid, Tensor) and list(grid.shape) == [1,3]
        dimensions = tuple(int(value) for value in grid[0].tolist())
        assert len(dimensions) == 3
        start = int(kwargs['additional_ref_length']) + int(kwargs['ref_length'])
        layout = TokenLayout(start, int(kwargs['seq_length']), int(kwargs['pose_length']), dimensions)
        assert layout.grid == tuple(self.weights.shape) and layout.length == self.weights.numel()
        assert args[0].shape[1] == start + layout.length + layout.suffix
        if self.layout is not None:
            assert self.layout == layout
        self.layout = layout

    def apply(self, image: Tensor) -> Tensor:
        """Apply the gate without retaining image features or changing RNG."""
        assert self.layout is not None
        if self.converted is None:
            self.converted = self.weights.to(device=image.device, dtype=image.dtype)
        assert self.converted.device == image.device and self.converted.dtype == image.dtype
        result = apply_generated(image, self.converted, self.layout)
        self.calls += 1
        if not self.owner.first_gate:
            measured = self.converted.detach().float().cpu()
            self.owner.first_gate = {'module':self.name, 'shape':list(measured.shape), 'dtype':str(image.dtype),
                'min':float(measured.min()), 'max':float(measured.max()), 'mean_per_time':measured.mean((1,2)).tolist(),
                'FP32_mean_error':float((self.weights.mean((1,2))-1).abs().max())}
            self.owner.write_report()
        return result


class GateInstallation:
    """Own reversible hooks and small gates; no weights or feature snapshots."""
    def __init__(self, config: GateConfig, support_sha: str) -> None:
        self.config = config
        self.support_sha = support_sha
        self.states: list[BlockState] = []
        self.handles: list[torch.utils.hooks.RemovableHandle] = []
        self.originals: list[tuple[nn.Module, MethodType]] = []
        self.first_gate: dict[str, str | float | list[int] | list[float]] = {}
        self.patch_sha = ''
        self.source_diff = ''

    def report(self) -> GateReport:
        """Return scalar/metadata observations without a retained feature tensor."""
        return {'mode':self.config.mode.value,'strength':self.config.strength,'source_sha256':SOURCE_SHA256,
            'patched_forward_sha256':self.patch_sha,'source_diff':self.source_diff,'support_sha256':self.support_sha,
            'block_calls':{state.name:state.calls for state in self.states},
            'layouts':{state.name:asdict(state.layout) for state in self.states if state.layout is not None},
            'first_gate':self.first_gate,'extra_forward':0}

    def write_report(self) -> None:
        """Persist an atomic small report when the first image output is observed."""
        if self.config.report_path is not None:
            path = self.config.report_path
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_suffix('.tmp')
            temporary.write_text(json.dumps(self.report(), indent=2)+'\n')
            temporary.replace(path)

    def assert_complete(self, expected_calls: int = 80, expected_blocks: int = 40) -> None:
        """Check real application counts after the original sampler completes."""
        assert len(self.states) == expected_blocks
        assert all(state.calls == expected_calls and state.layout is not None for state in self.states)
        self.write_report()

    def remove(self) -> None:
        """Restore original instance forward methods and remove owned hooks."""
        for handle in self.handles:
            handle.remove()
        for module, original in self.originals:
            module.forward = original
        self.handles.clear()
        self.originals.clear()
        for state in self.states:
            state.converted = None


def install(model: nn.Module, support_path: Path, config: GateConfig) -> GateInstallation:
    """Bind the exact official image path; OFF/zero leaves its forward untouched."""
    payload = load_file(str(support_path), device='cpu')
    assert set(payload) == {'E'}
    support = payload['E']
    weights = coefficients(support, config.mode, config.strength)
    owner = GateInstallation(config, hashlib.sha256(support_path.read_bytes()).hexdigest())
    enabled = config.mode is not GateMode.OFF and config.strength != 0
    for index, block in enumerate(model.blocks):
        cross = block.cross_attn
        assert type(cross).__name__ == 'WanI2VCrossAttention'
        original = cross.forward
        source_file = inspect.getsourcefile(original.__func__)
        assert source_file is not None and hashlib.sha256(Path(source_file).read_bytes()).hexdigest() == SOURCE_SHA256
        source = textwrap.dedent(inspect.getsource(original.__func__))
        patched = source.replace('    x = x + img_x\n', '    img_x = _b029_image_gate(img_x)\n    x = x + img_x\n')
        owner.patch_sha = hashlib.sha256(patched.encode()).hexdigest()
        owner.source_diff = '+ img_x = _b029_image_gate(img_x) before existing x = x + img_x; no other upstream expression changed'
        if enabled:
            state = BlockState(f'blocks.{index}.cross_attn', weights, owner)
            owner.states.append(state)
            owner.originals.append((cross, original))
            cross.forward = MethodType(compile_forward(original.__func__, state.apply), cross)
            owner.handles.append(block.register_forward_pre_hook(state.bind, with_kwargs=True))
    assert len(model.blocks) == 40
    return owner
