# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "scipy"]
# ///
"""CPU reinsertion geometry. Run fixtures with python -m pytest."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray
from scipy.ndimage import distance_transform_edt


@dataclass(frozen=True, slots=True)
class BlendPolicy:
    window: tuple[int, int]
    ramp_in: tuple[int, int]
    ramp_out: tuple[int, int]
    lower_fraction: float
    dilation_px: int
    feather_px: int


def temporal_weight(frame: int, policy: BlendPolicy) -> float:
    """Inclusive linear ramps have zero replacement at both outer endpoints."""
    if not policy.window[0] <= frame <= policy.window[1]:
        return 0.
    incoming = (frame - policy.ramp_in[0]) / (policy.ramp_in[1] - policy.ramp_in[0])
    outgoing = (policy.ramp_out[1] - frame) / (policy.ramp_out[1] - policy.ramp_out[0])
    return max(0., min(1., incoming, outgoing))


def leg_alpha(body: NDArray[np.bool_], frame: int, policy: BlendPolicy) -> NDArray[np.float64]:
    """Native-pixel lower bbox, Euclidean dilation, finite inward feather."""
    region = np.zeros_like(body)
    weight = temporal_weight(frame, policy)
    if not body.any() or weight == 0:
        return region.astype(np.float64)
    y, x = np.nonzero(body)
    bottom = int(y.max()) + 1
    top = int(np.ceil(bottom - policy.lower_fraction * (bottom - int(y.min()))))
    region[top:bottom, int(x.min()):int(x.max()) + 1] = True
    expanded = distance_transform_edt(~region) <= policy.dilation_px
    inside = distance_transform_edt(np.pad(expanded, 1))[1:-1, 1:-1]
    return np.clip(inside / policy.feather_px, 0, 1) * weight


def mix(base: NDArray[np.uint8], refined: NDArray[np.uint8], alpha: NDArray[np.float64]) -> NDArray[np.uint8]:
    """Nearest-integer blend with explicit byte-exact zero/one endpoints."""
    result = np.rint(base * (1 - alpha[:, :, None]) + refined * alpha[:, :, None]).astype(np.uint8)
    result[alpha == 0] = base[alpha == 0]
    result[alpha == 1] = refined[alpha == 1]
    return result
