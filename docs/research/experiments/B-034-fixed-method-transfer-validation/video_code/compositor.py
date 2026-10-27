"""CPU edit-support compositor; semantic support is not object alpha."""
from __future__ import annotations

import math
from dataclasses import dataclass
import numpy as np
from numpy.typing import NDArray
from scipy.ndimage import distance_transform_edt

BoolArray = NDArray[np.bool_]
FloatArray = NDArray[np.float32]

@dataclass(frozen=True, slots=True)
class Box:
    x0: int
    y0: int
    x1: int
    y1: int

    @property
    def width(self) -> int:
        return self.x1 - self.x0

    @property
    def height(self) -> int:
        return self.y1 - self.y0


def bbox(mask: BoolArray) -> Box:
    if mask.ndim != 2 or not mask.any():
        raise ValueError('Expected nonempty 2D support')
    y, x = np.nonzero(mask)
    return Box(int(x.min()), int(y.min()), int(x.max()) + 1, int(y.max()) + 1)


def fixed_envelope(sources: BoolArray, anchor: BoolArray) -> tuple[FloatArray, Box]:
    if sources.ndim != 3 or sources.shape[1:] != anchor.shape:
        raise ValueError('Source and anchor support shape mismatch')
    union = np.any(sources, axis=0) | anchor
    b = bbox(union)
    height, width = anchor.shape
    expanded = Box(max(0, math.floor(b.x0 - .1*b.width)),
                   max(0, math.floor(b.y0 - .1*b.height)),
                   min(width, math.ceil(b.x1 + .1*b.width)),
                   min(height, math.ceil(b.y1 + .1*b.height)))
    y, x = np.indices(anchor.shape)
    # Pixel-center distance to rectangle edges; first inside center is 0.5px.
    inside_distance = np.minimum.reduce((x-expanded.x0+.5, expanded.x1-x-.5,
                                         y-expanded.y0+.5, expanded.y1-y-.5))
    return np.clip(inside_distance / 8, 0, 1).astype(np.float32), expanded


def radius_for_sources(sources: BoolArray) -> int:
    b = bbox(np.any(sources, axis=0))
    return max(2, math.ceil(.02 * max(b.width, b.height)))


def mask_assisted(source: BoolArray, target: BoolArray, radius: int) -> FloatArray:
    if source.shape != target.shape or source.ndim != 2 or radius < 0:
        raise ValueError('Invalid support contract')
    union = source | target
    if not union.any():
        raise ValueError('Empty union')
    core = distance_transform_edt(~union) <= radius
    return np.clip(1-distance_transform_edt(~core)/4, 0, 1).astype(np.float32)


def blend(source: FloatArray, generated: FloatArray, edit: FloatArray) -> FloatArray:
    if source.shape != generated.shape or source.shape[:-1] != edit.shape or source.shape[-1] != 3:
        raise ValueError('Expected matching HWC RGB and HW edit support')
    if not all(np.isfinite(a).all() for a in (source, generated, edit)):
        raise ValueError('Nonfinite input')
    if edit.min() < 0 or edit.max() > 1:
        raise ValueError('Edit support outside [0,1]')
    mixed = (1-edit[..., None])*source + edit[..., None]*generated
    # Explicit endpoint copies also avoid arithmetic rounding at E=0 or E=1.
    return np.where((edit == 0)[..., None], source,
                    np.where((edit == 1)[..., None], generated, mixed)).astype(np.float32)


def to_uint8(image: FloatArray) -> NDArray[np.uint8]:
    return np.floor((np.clip(image, -1, 1)+1)*127.5).astype(np.uint8)
