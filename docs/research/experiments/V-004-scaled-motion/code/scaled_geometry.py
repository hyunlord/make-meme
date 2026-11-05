"""Pure CPU geometry for fixed-scale object controls and descriptive G8."""
from __future__ import annotations

from dataclasses import dataclass
import math
import statistics
from typing import TypedDict

import numpy as np
from numpy.typing import NDArray
from PIL import Image


@dataclass(frozen=True, slots=True)
class Layer:
    rgb: NDArray[np.uint8]
    core: NDArray[np.bool_]
    support: NDArray[np.bool_]
    unclipped_pixels: int
    visible_pixels: int
    clipped_fraction: float


class Direction(TypedDict):
    topmost_pixel: list[float] | None
    bbox_center_pixel: list[float] | None
    quadrant: str
    topmost_tie_count: int


def direction(mask: NDArray[np.bool_]) -> Direction:
    """Median x among top-row pixels; bbox center uses pixel-index coordinates.

    Axis equality gets an explicit AXIS label; an empty mask is MISSING. This
    statistic can describe a head or ear rather than a kicked leg and is no gate.
    """
    yy, xx = np.nonzero(mask)
    if not len(xx):
        return {'topmost_pixel': None, 'bbox_center_pixel': None, 'quadrant': 'MISSING', 'topmost_tie_count': 0}
    y = float(yy.min())
    top = xx[yy == yy.min()]
    x = float(np.median(top))
    cx, cy = float(xx.min()+xx.max())/2, float(yy.min()+yy.max())/2
    dx, dy = x-cx, y-cy
    if dx == 0 and dy == 0:
        label = 'CENTER'
    elif dx == 0:
        label = 'UP_AXIS' if dy < 0 else 'DOWN_AXIS'
    elif dy == 0:
        label = 'LEFT_AXIS' if dx < 0 else 'RIGHT_AXIS'
    else:
        label = ('UPPER' if dy < 0 else 'LOWER') + ('_LEFT' if dx < 0 else '_RIGHT')
    return {'topmost_pixel': [x, y], 'bbox_center_pixel': [cx, cy], 'quadrant': label,
            'topmost_tie_count': len(top)}


def bbox(mask: NDArray[np.bool_]) -> tuple[int, int, int, int]:
    yy, xx = np.nonzero(mask)
    if not len(xx):
        raise ValueError('A missing source mask has no scale pivot')
    return int(xx.min()), int(yy.min()), int(xx.max()+1), int(yy.max()+1)


def fixed_scales(values: dict[str, list[float]], snap_role: str,
                 interval: tuple[float, float]) -> dict[str, float]:
    scales = {role: float(statistics.median(rows)) for role, rows in values.items()}
    if any(not math.isfinite(value) or value <= 0 for value in scales.values()):
        raise ValueError('Invalid accepted-anchor scale')
    if interval[0] <= scales[snap_role] <= interval[1]:
        scales[snap_role] = 1.0
    return scales


def reflection_owners(boxes: dict[int, tuple[int, int, int, int]], casting: dict[str, int],
                      overlap_fraction: float, margin: float) -> tuple[dict[int, str], dict[int, list[str]]]:
    """Spatial pairing to known real tracks; deterministic nearest-x tie breaking."""
    owners, candidates = {}, {}
    for track, b in boxes.items():
        if track in casting.values():
            continue
        eligible = []
        for role, real_track in casting.items():
            a = boxes[real_track]
            overlap = max(0, min(a[2], b[2])-max(a[0], b[0]))
            if overlap >= overlap_fraction*min(a[2]-a[0], b[2]-b[0]) and b[1] > a[3]-margin:
                eligible.append(role)
        if not eligible:
            raise ValueError(f'Non-body source track {track} has no reflection owner')
        candidates[track] = eligible
        owners[track] = min(eligible, key=lambda role: (
            abs((boxes[casting[role]][0]+boxes[casting[role]][2])-(b[0]+b[2])),
            abs(b[1]-boxes[casting[role]][3]), role))
    return owners, candidates


def affine_layer(rgb: NDArray[np.uint8], core: NDArray[np.bool_], support: NDArray[np.bool_],
                 scale: float, pivot: tuple[float, float]) -> Layer:
    """Scale on an enlarged canvas first, so the denominator includes offscreen pixels.

    Coordinates are pixel-edge coordinates, bbox bottom/top are exclusive/left
    edges. PIL inverse affine NEAREST preserves the original canny sample values.
    Both mask and support use precisely the same transform and origin.
    """
    height, width = core.shape
    assert rgb.shape == (height, width, 3) and support.shape == core.shape
    x0, y0, x1, y1 = bbox(support)
    px, py = pivot
    left, top = min(0, math.floor(px+scale*(x0-px))-2), min(0, math.floor(py+scale*(y0-py))-2)
    right = max(width, math.ceil(px+scale*(x1-px))+2)
    bottom = max(height, math.ceil(py+scale*(y1-py))+2)
    coefficients = (1/scale, 0, px+(left-px)/scale, 0, 1/scale, py+(top-py)/scale)
    size = right-left, bottom-top
    def transform(array: NDArray[np.uint8]) -> NDArray[np.uint8]:
        return np.asarray(Image.fromarray(array).transform(size, Image.Transform.AFFINE, coefficients,
                                                          resample=Image.Resampling.NEAREST, fillcolor=0))
    full_core = transform(core.astype(np.uint8)*255) > 0
    full_support = transform(support.astype(np.uint8)*255) > 0
    full_rgb = transform(rgb)
    view = (slice(-top, -top+height), slice(-left, -left+width))
    visible = full_core[view]
    denominator, numerator = int(full_core.sum()), int(visible.sum())
    if denominator == 0:
        raise ValueError('Scale removed every measured source mask pixel')
    return Layer(full_rgb[view], visible, full_support[view], denominator, numerator,
                 (denominator-numerator)/denominator)


def hold_indices(source_count: int, factor: int) -> list[int]:
    """Endpoint-preserving hold: frame i reads floor(i/factor)."""
    if source_count < 1 or factor < 1:
        raise ValueError('Invalid hold dimensions')
    return [index//factor for index in range((source_count-1)*factor+1)]
