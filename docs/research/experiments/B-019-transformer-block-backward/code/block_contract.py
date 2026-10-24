"""Fixed B019 synthetic inputs/budgets; not real encoder activations or FM targets."""
from dataclasses import dataclass
from hashlib import sha256

import torch
from torch import Tensor


@dataclass(frozen=True, slots=True)
class TokenLayout:
    t: int
    h: int
    w: int

    @property
    def ref(self) -> int:
        return self.h * self.w

    @property
    def video(self) -> int:
        return self.t * self.h * self.w

    @property
    def pose(self) -> int:
        return self.t * (self.h // 2) * (self.w // 2)

    @property
    def total(self) -> int:
        return self.ref + self.video + self.pose


def token_layout(long: bool = False) -> TokenLayout:
    return TokenLayout(5, 56, 32) if long else TokenLayout(1, 4, 4)


def expected_counts(long: bool) -> tuple[int, int, int]:
    """Block forward/backward/optimizer counts, not internal FA kernel counts."""
    return (9, 4, 3) if long else (8, 3, 3)


def runtime_dtype(name: str) -> torch.dtype:
    """Cast directly from stored values; never round-trip FP32 islands via BF16."""
    return torch.float32 if 'norm' in name or name == 'modulation' else torch.bfloat16


def tensor_sha256(value: Tensor) -> str:
    return sha256(value.detach().cpu().contiguous().view(torch.uint8).numpy().tobytes()).hexdigest()


def make_conditions(seed: int) -> tuple[Tensor, Tensor]:
    generator = torch.Generator(device='cpu').manual_seed(seed)
    context = torch.randn((1, 769, 5120), generator=generator, dtype=torch.float32).to(torch.bfloat16)
    e = torch.rand((1, 6, 5120), generator=generator, dtype=torch.float32) * .1 - .05
    e[:, 2] = 1.0
    e[:, 5] = 1.0
    validate_conditions(context, e)
    return context, e


def validate_conditions(context: Tensor, e: Tensor) -> None:
    if tuple(context.shape) != (1, 769, 5120) or context.dtype != torch.bfloat16:
        raise ValueError('context must be projected BF16[1,257+512,5120]')
    if tuple(e.shape) != (1, 6, 5120) or e.dtype != torch.float32:
        raise ValueError('e must be FP32[1,6,5120]')
    if not bool(torch.isfinite(context).all()) or not bool(torch.isfinite(e).all()):
        raise ValueError('synthetic conditions must be finite')
    if not bool((e[:, (2, 5), :] == 1).all()):
        raise ValueError('synthetic self/FFN input gate components must equal one')
    if not bool((e[:, (0, 1, 3, 4), :].abs() <= .05).all()):
        raise ValueError('synthetic shift/scale components must be bounded by .05')


def validate_fixture(x: Tensor, target: Tensor, x_hash: str, target_hash: str) -> None:
    if tuple(x.shape) != (1, 36, 5120) or tuple(target.shape) != (1, 36, 5120):
        raise ValueError('B018 actual fixture shapes must remain [1,36,5120]')
    if x.dtype != torch.bfloat16 or target.dtype != torch.float32:
        raise ValueError('B018 actual fixture dtype mismatch')
    if not bool(torch.isfinite(x).all()) or not bool(torch.isfinite(target).all()):
        raise ValueError('B018 actual fixture must be finite')
    if tensor_sha256(x) != x_hash or tensor_sha256(target) != target_hash:
        raise ValueError('B018 actual fixture hash mismatch')
