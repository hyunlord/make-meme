"""Typed, tensor-only ALG adaptation; no model loading or RNG operations."""
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal, TypedDict, assert_never

from torch import Tensor
from torch.nn import functional as F

Branch = Literal['c_orig', 'u_orig', 'u_low', 'c_low']


@dataclass(frozen=True, slots=True)
class AlgSettings:
    enabled: bool = True
    ratio: float = 0.4
    start: float = 0.0
    end: float = 0.2

    def __post_init__(self) -> None:
        assert 0 < self.ratio <= 1 and 0 <= self.start <= self.end <= 1

    def active(self, index: int, steps: int) -> bool:
        assert steps > 0 and 0 <= index < steps
        return self.enabled and self.ratio < 1 and self.start <= index / max(steps - 1, 1) <= self.end

    def expected_calls(self, steps: int) -> int:
        return sum(3 if self.active(i, steps) else 2 for i in range(steps))


def spatial_size(height: int, width: int, ratio: float) -> tuple[int, int]:
    return max(1, round(height * ratio)), max(1, round(width * ratio))


def low_pass_reference(value: Tensor, ratio: float) -> Tensor:
    """Filter independent H/W planes of CTHW or BCTHW, preserving signed values."""
    assert value.ndim in (4, 5) and value.is_floating_point() and 0 < ratio <= 1
    if ratio == 1:
        return value.clone()
    batched = value.unsqueeze(0) if value.ndim == 4 else value
    b, c, t, h, w = batched.shape
    planes = batched.permute(0, 2, 1, 3, 4).reshape(b * t, c, h, w)
    low = F.interpolate(planes, size=spatial_size(h, w, ratio), mode='bilinear', align_corners=False, antialias=True)
    restored = F.interpolate(low, size=(h, w), mode='bilinear', align_corners=False, antialias=True)
    result = restored.reshape(b, t, c, h, w).permute(0, 2, 1, 3, 4).contiguous()
    return result.squeeze(0) if value.ndim == 4 else result


def guided_prediction(predict: Callable[[Branch], Tensor], settings: AlgSettings,
                      index: int, steps: int, scale: float) -> Tensor:
    """Sequential predictions retain baseline order when ALG is inactive."""
    assert scale > 1
    if settings.active(index, steps):
        original_negative = predict('u_orig')
        low_negative = predict('u_low')
        low_positive = predict('c_low')
        return original_negative + scale * (low_positive - low_negative)
    positive = predict('c_orig')
    negative = predict('u_orig')
    return negative + scale * (positive - negative)


class Condition(TypedDict):
    context: list[Tensor]
    clip_fea: Tensor
    ref_latents: list[Tensor]
    ref_masks: list[Tensor]
    pose_latents: list[Tensor]
    driving_masks: list[Tensor]
    seq_len: float
    history_mask: Tensor | None
    replace_flag: bool
    additional_ref_latents: list[Tensor] | None
    additional_ref_masks: list[Tensor] | None


def branch_condition(branch: Branch, positive: Condition, negative: Condition,
                     filtered: Tensor) -> Condition:
    """Replace only the reference list in a new container, never its parent."""
    match branch:
        case 'c_orig':
            return positive
        case 'u_orig':
            return negative
        case 'c_low':
            return {**positive, 'ref_latents': [filtered]}
        case 'u_low':
            return {**negative, 'ref_latents': [filtered]}
    assert_never(branch)
