"""TEST_ONLY LoRA component. No merge, inference integration, or full-model loading."""
from collections.abc import Mapping
from hashlib import sha256
from pathlib import Path
from typing import Annotated, ClassVar, Literal, override

import torch
import torch.nn.functional as F
from pydantic import BaseModel, ConfigDict, Field
from safetensors.torch import load_file, save_file
from torch import Tensor, nn


class LowRankLinear(nn.Module):
    """Frozen projection plus FP32 rank-4 adapter, residual cast to base output dtype."""

    def __init__(self, base: nn.Linear, rank: int = 4, alpha: float = 4.0) -> None:
        super().__init__()
        if rank != 4 or alpha != 4.0:
            raise ValueError('B018 fixes rank=4, alpha=4, dropout=0')
        self.base: nn.Linear = base
        for parameter in base.parameters():
            _ = parameter.requires_grad_(False)
        self.rank: int = rank
        self.alpha: float = alpha
        self.enabled: bool = True
        self.lora_A: nn.Parameter = nn.Parameter(torch.empty(
            rank, base.in_features, device=base.weight.device, dtype=torch.float32))
        self.lora_B: nn.Parameter = nn.Parameter(torch.zeros(
            base.out_features, rank, device=base.weight.device, dtype=torch.float32))
        _ = nn.init.kaiming_uniform_(self.lora_A, a=5 ** .5)

    @override
    def forward(self, x: Tensor) -> Tensor:
        baseline = self.base.forward(x)
        if not self.enabled:
            return baseline
        if self.lora_A.dtype != torch.float32 or self.lora_B.dtype != torch.float32:
            raise ValueError('adapter masters must remain FP32; cast base before wrapping')
        with torch.autocast(device_type=x.device.type, enabled=False):
            delta = F.linear(F.linear(x.float(), self.lora_A), self.lora_B)
            delta = delta * (self.alpha / self.rank)
        return baseline + delta.to(dtype=baseline.dtype)

    def adapter_parameters(self) -> tuple[nn.Parameter, nn.Parameter]:
        return self.lora_A, self.lora_B


class Frozen(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra='forbid')


class ModuleSpec(Frozen):
    rank: Literal[4] = 4
    alpha: Annotated[float, Field(ge=4.0, le=4.0)] = 4.0
    dropout: Literal[0] = 0
    in_features: int
    out_features: int
    dtype: Literal['float32'] = 'float32'


class AdapterSchema(Frozen):
    schema_version: Literal[1] = 1
    label: Literal['TEST_ONLY/NOT_FOR_INFERENCE'] = 'TEST_ONLY/NOT_FOR_INFERENCE'
    serialization: Literal['safetensors'] = 'safetensors'
    payload_sha256: str
    modules: dict[str, ModuleSpec]
    provenance: dict[str, str]


def specifications(modules: Mapping[str, LowRankLinear]) -> dict[str, ModuleSpec]:
    if not modules or any(not key or '/' in key for key in modules):
        raise ValueError('at least one named adapter is required')
    if any(module.rank != 4 or module.alpha != 4.0 for module in modules.values()):
        raise ValueError('adapter settings changed from the fixed B018 contract')
    return {name: ModuleSpec(in_features=module.base.in_features,
                             out_features=module.base.out_features)
            for name, module in modules.items()}


def adapter_state(modules: Mapping[str, LowRankLinear]) -> dict[str, Tensor]:
    return {f'{name}.{suffix}': tensor.detach().cpu().contiguous()
            for name, module in modules.items()
            for suffix, tensor in (('lora_A', module.lora_A), ('lora_B', module.lora_B))}


def save_adapters(path: Path, modules: Mapping[str, LowRankLinear],
                  provenance: dict[str, str]) -> None:
    specs = specifications(modules)
    tensors = adapter_state(modules)
    if any(tensor.dtype != torch.float32 or not bool(torch.isfinite(tensor).all())
           for tensor in tensors.values()):
        raise ValueError('only finite FP32 adapter tensors may be saved')
    save_file(tensors, str(path))
    schema = AdapterSchema(payload_sha256=sha256(path.read_bytes()).hexdigest(),
                           modules=specs, provenance=provenance)
    _ = path.with_suffix('.json').write_text(schema.model_dump_json(indent=2) + '\n')


def load_adapters(path: Path, modules: Mapping[str, LowRankLinear]) -> AdapterSchema:
    schema = AdapterSchema.model_validate_json(path.with_suffix('.json').read_text())
    if path.stat().st_size > 64 * 1024 * 1024:
        raise ValueError('adapter payload exceeds 64MiB bound')
    if sha256(path.read_bytes()).hexdigest() != schema.payload_sha256:
        raise ValueError('adapter payload hash mismatch')
    if schema.modules != specifications(modules):
        raise ValueError('adapter module specification mismatch')
    tensors = load_file(str(path), device='cpu')
    expected = {f'{name}.{suffix}': parameter
                for name, module in modules.items()
                for suffix, parameter in (('lora_A', module.lora_A), ('lora_B', module.lora_B))}
    if tensors.keys() != expected.keys():
        raise ValueError('adapter key set mismatch')
    for key, value in tensors.items():
        parameter = expected[key]
        if value.shape != parameter.shape or value.dtype != torch.float32:
            raise ValueError(f'adapter shape/dtype mismatch: {key}')
        if parameter.dtype != torch.float32 or not bool(torch.isfinite(value).all()):
            raise ValueError(f'invalid adapter master or nonfinite value: {key}')
    # Validate every tensor before changing any destination parameter.
    with torch.no_grad():
        for key, parameter in expected.items():
            _ = parameter.copy_(tensors[key].to(device=parameter.device))
    return schema
