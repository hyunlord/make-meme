# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# Run: existing Python anchor_gates.py /private/scorer-config.json /private/gates.json
"""CPU-only V-001 anchor gates on the common 1280x720 canvas."""
from __future__ import annotations

from pathlib import Path
from typing import TypedDict
import hashlib
import json
import math
import sys

import numpy as np
from numpy.typing import NDArray
from PIL import Image, ImageFilter

from reflections import Cast, Classified, classify, first_frame_cast
from sam_analysis import ObjectRow


class Geometry(TypedDict):
    casting: Cast | None
    actual_count: int
    center_shift_px: dict[str, float]
    bbox_height_ratio: dict[str, float]
    gates: dict[str, bool]


def geometry(source: list[ObjectRow], anchor: list[ObjectRow]) -> Geometry:
    """Keep G2-G4 failed/unmeasured if G1 does not establish two actual dogs."""
    actual_count = len(classify(anchor)['actual_track_indices'])
    result: Geometry = {'casting': None, 'actual_count': actual_count, 'center_shift_px': {},
                        'bbox_height_ratio': {}, 'gates': {'G1': actual_count == 2,
                        'G2': False, 'G3': False, 'G4': False}}
    if actual_count != 2:
        return result
    source_cast, anchor_cast = first_frame_cast(source), first_frame_cast(anchor)
    result['casting'] = anchor_cast
    source_rows = {row['track_index']: row for row in source}
    anchor_rows = {row['track_index']: row for row in anchor}
    for role in ('Lab', 'IG'):
        a, b = source_rows[source_cast[role]], anchor_rows[anchor_cast[role]]
        assert a['center'] is not None and b['center'] is not None
        assert a['bbox'] is not None and b['bbox'] is not None
        result['center_shift_px'][role] = math.dist(a['center'], b['center'])
        result['bbox_height_ratio'][role] = (b['bbox'][3]-b['bbox'][1])/(a['bbox'][3]-a['bbox'][1])
    result['gates'].update(G2=all(x <= 102.4 for x in result['center_shift_px'].values()),
                          G3=.85 <= result['bbox_height_ratio']['Lab'] <= 1.60,
                          G4=.70 <= result['bbox_height_ratio']['IG'] <= 1.30)
    return result


def background_mae(source: NDArray[np.uint8], anchor: NDArray[np.uint8],
                   union: NDArray[np.bool_]) -> tuple[float | None, int]:
    """Dilate the complete actual+reflection mask union by 24 pixels."""
    assert source.shape == anchor.shape == (720, 1280, 3)
    assert union.shape == (720, 1280)
    dilated = np.asarray(Image.fromarray(union.astype('uint8')*255).filter(ImageFilter.MaxFilter(49))) > 0
    outside = ~dilated
    count = int(outside.sum())
    value = float(np.abs(source.astype(np.float32)-anchor.astype(np.float32))[outside].mean()) if count else None
    return value, count


def masks(folder: Path, objects: list[ObjectRow]) -> dict[int, NDArray[np.bool_]]:
    """Read every saved instance, including reflection masks, without selection."""
    result: dict[int, NDArray[np.bool_]] = {}
    for row in objects:
        path = folder/f"000-track-{row['track_index']:02d}.png"
        with Image.open(path) as image:
            assert image.size == (1280, 720)
            mask = np.asarray(image) > 0
        assert int(mask.sum()) == row['area']
        result[row['track_index']] = mask
    return result


class ReflectionColor(TypedDict):
    above_track_index: int
    reflection_track_index: int
    above_mean_rgb: list[float]
    reflection_mean_rgb: list[float]
    mean_rgb_absolute_difference: float


def reflection_colors(rgb: NDArray[np.uint8], instance_masks: dict[int, NDArray[np.bool_]],
                      classified: Classified) -> list[ReflectionColor]:
    """Descriptive color differences only; no unregistered match threshold."""
    rows: list[ReflectionColor] = []
    for pair in classified['pairs']:
        a, b = pair['above_track_index'], pair['reflection_track_index']
        first, second = rgb[instance_masks[a]].mean(axis=0), rgb[instance_masks[b]].mean(axis=0)
        rows.append({'above_track_index': a, 'reflection_track_index': b,
                     'above_mean_rgb': first.tolist(), 'reflection_mean_rgb': second.tolist(),
                     'mean_rgb_absolute_difference': float(np.abs(first-second).mean())})
    return rows


def main() -> None:
    config_path, output = map(Path, sys.argv[1:])
    config = json.loads(config_path.read_text())
    source_summary = Path(config['source_summary'])
    anchor_summary = Path(config['anchor_summary'])
    source, anchor = (json.loads(p.read_text()) for p in (source_summary, anchor_summary))
    assert source['coordinate_size'] == anchor['coordinate_size'] == [1280, 720]
    source_objects, anchor_objects = source['frames'][0]['objects'], anchor['frames'][0]['objects']
    source_masks, anchor_masks = masks(source_summary.parent, source_objects), masks(anchor_summary.parent, anchor_objects)
    union = np.zeros((720, 1280), dtype=bool)
    for mask in (*source_masks.values(), *anchor_masks.values()):
        union |= mask
    with Image.open(config['source_image']) as image:
        source_rgb = np.asarray(image.convert('RGB'))
    with Image.open(config['anchor_image']) as image:
        anchor_rgb = np.asarray(image.convert('RGB'))
    result = geometry(source_objects, anchor_objects)
    mae, pixel_count = background_mae(source_rgb, anchor_rgb, union)
    result['gates']['G5'] = mae is not None and mae <= 12
    failed = [name for name, passed in result['gates'].items() if not passed]
    report = {'amendment': 2, 'coordinate_size': [1280, 720], **result,
              'source_classification': classify(source_objects), 'anchor_classification': classify(anchor_objects),
              'background_mae': mae, 'background_pixels': pixel_count, 'dilation_radius_px': 24,
              'background_exclusion': 'union of all source and anchor actual/reflection masks',
              'failed_gates': failed, 'all_gates_pass': not failed,
              'reflection_color_reference_only': reflection_colors(anchor_rgb, anchor_masks, classify(anchor_objects)),
              'reflection_color_quality_verdict': 'UNVERIFIED_NO_THRESHOLD',
              'input_summary_sha256': {'source': hashlib.sha256(source_summary.read_bytes()).hexdigest(),
                                       'anchor': hashlib.sha256(anchor_summary.read_bytes()).hexdigest()}}
    temporary = output.with_suffix(output.suffix+'.partial')
    temporary.write_text(json.dumps(report, indent=2)+'\n')
    temporary.replace(output)
    assert json.loads(output.read_text()) == report
    print(json.dumps(report))


if __name__ == '__main__':
    main()
