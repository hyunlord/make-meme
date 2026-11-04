# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# Run through metrics.py; CPU-only V-001 helper copies are in v001_metrics/.
"""Canonical silhouette and preservation measurements; no tracking inference."""
from __future__ import annotations

from pathlib import Path
from typing import TypedDict
import sys

import numpy as np
from numpy.typing import NDArray
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent / 'v001_metrics'))
from output_metrics import Frame, canonical, visible_support
from reflections import Cast, classify
from sam_analysis import ObjectRow


class Silhouettes(TypedDict):
    observed: dict[str, float | None]
    all_frame: dict[str, float | None]
    output_lab_ig_height_ratio: float | None
    source_lab_ig_height_ratio: float | None


def silhouette_score(source: NDArray[np.bool_], output: NDArray[np.bool_] | None) -> tuple[float | None, float | None]:
    """Missing output is an explicit empty prediction, not a measured perfect match."""
    if not source.any():
        return None, None
    if output is None:
        return None, 0.0
    union = int((source | output).sum())
    score = float((source & output).sum()) / union
    return score, score


def height_ratio(objects: list[ObjectRow], casting: Cast | None) -> float | None:
    """Lab/IG height ratio only when both cast tracks are actual non-reflections."""
    if casting is None:
        return None
    rows = {row['track_index']: row for row in objects}
    actual = set(classify(objects)['actual_track_indices'])
    if any(track not in actual or rows[track]['area_fraction'] < .005 for track in casting.values()):
        return None
    lab, ig = rows[casting['Lab']]['bbox'], rows[casting['IG']]['bbox']
    assert lab is not None and ig is not None
    return (lab[3]-lab[1])/(ig[3]-ig[1])


def silhouettes(source: Frame, output: Frame, casting: Cast | None, visible: NDArray[np.bool_]) -> Silhouettes:
    """Use undilated source masks and a fixed first-frame cast across the clip."""
    observed: dict[str, float | None] = {'Lab': None, 'IG': None}
    all_frame: dict[str, float | None] = {'Lab': None, 'IG': None}
    if casting is not None:
        actual = set(classify(output.objects)['actual_track_indices'])
        rows = {row['track_index']: row for row in output.objects}
        for role, source_id in [('Lab', 0), ('IG', 1)]:
            track = casting[role]
            mask = output.masks.get(track) if track in actual and rows[track]['area_fraction'] >= .005 else None
            observed[role], all_frame[role] = silhouette_score(source.masks[source_id] & visible, None if mask is None else mask & visible)
    return {'observed': observed, 'all_frame': all_frame,
            'output_lab_ig_height_ratio': height_ratio(output.objects, casting),
            'source_lab_ig_height_ratio': height_ratio(source.objects, {'Lab': 0, 'IG': 1})}


def outside_preservation(source: Frame, output: Frame, mask_path: Path, visible: NDArray[np.bool_]) -> tuple[int, float | None]:
    """Compare against original RGB over common field of view outside fixed edit mask."""
    with Image.open(mask_path) as image:
        assert image.size == (832, 480)
        rgb = np.asarray(image.convert('RGB'))
        assert np.array_equal(rgb[:, :, 0], rgb[:, :, 1]) and np.array_equal(rgb[:, :, 1], rgb[:, :, 2])
        assert set(np.unique(rgb)).issubset({0, 255})
        mask = np.asarray(canonical(image.convert('L'), 'E2', mask=True)) > 0
    roi = visible & visible_support('E2') & ~mask
    count = int(roi.sum())
    value = float(np.abs(output.rgb.astype(np.float32)-source.rgb.astype(np.float32))[roi].mean()) if count else None
    return count, value
