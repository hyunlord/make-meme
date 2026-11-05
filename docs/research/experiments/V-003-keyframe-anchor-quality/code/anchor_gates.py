"""CPU anchor gates; all scene-specific decisions come from the scene JSON.

Run: python anchor_gates.py SCENE.json PRIVATE_RUNTIME.json OUTPUT.json
Runtime: source_summary, anchor_summary, source_image, anchor_image,
source_frame_index (index in the existing source SAM summary).
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import permutations
from pathlib import Path
from typing import TypedDict
import hashlib
import json
import math
import sys

import numpy as np
from numpy.typing import NDArray
from PIL import Image, ImageFilter


@dataclass(frozen=True, slots=True)
class Policy:
    size: tuple[int, int]
    cast: dict[str, int]
    overlap: float
    reflection_margin: float
    count: int
    shift: float
    height: dict[str, tuple[float, float]]
    aspect: tuple[float, float]
    dilation: int
    mae: float

    @classmethod
    def read(cls, path: Path) -> Policy:
        """Parse the supplied configuration without substituting scene defaults."""
        raw = json.loads(path.read_text())
        scene = raw['scene']
        gates = raw['anchor_generation']['gates']
        cast = scene['casting_track_indices']
        height = {role: tuple(value) for role in cast for key, value in gates.items()
                  if key.lower().endswith(f'_{role.lower()}_bbox_height_ratio')}
        if set(height) != set(cast):
            raise ValueError('Every casting role needs a bbox-height gate')
        dilation = gates['G5_dilation_px']
        return cls(tuple(raw['anchor_generation']['resolution_master']), cast,
                   scene['reflection_rule']['x_overlap_min_frac_of_narrower'],
                   scene['reflection_rule']['lower_top_below_upper_bottom_minus_px'],
                   gates['G1_real_dog_count']['equals'], gates['G2_centroid_shift_max_frac_width'],
                   height, tuple(gates['G6_upright_aspect_ratio_vs_source']), dilation,
                   gates['G5_background_mae_max'])


@dataclass(frozen=True, slots=True)
class Row:
    track: int
    present: bool
    bbox: tuple[float, float, float, float] | None
    center: tuple[float, float] | None
    area: int


class Geometry(TypedDict):
    casting: dict[str, int]
    actual_count: int
    center_shift_px: dict[str, float]
    bbox_height_ratio: dict[str, float]
    aspect_ratio_vs_source: dict[str, float]
    gates: dict[str, bool]


def classify(rows: list[Row], policy: Policy) -> tuple[list[int], list[int]]:
    """Apply the ordered-pair reflection rule without threshold changes."""
    present = [row for row in rows if row.present and row.bbox is not None]
    reflected: set[int] = set()
    for upper in present:
        a = upper.bbox
        assert a is not None
        for lower in present:
            b = lower.bbox
            assert b is not None
            if upper.track == lower.track:
                continue
            overlap = max(0, min(a[2], b[2])-max(a[0], b[0]))
            width = min(a[2]-a[0], b[2]-b[0])
            if width > 0 and overlap >= policy.overlap*width and b[1] > a[3]-policy.reflection_margin:
                reflected.add(lower.track)
    return sorted(row.track for row in present if row.track not in reflected), sorted(reflected)


def geometry(source: list[Row], anchor: list[Row], policy: Policy) -> Geometry:
    """Bind anchor detections to fixed source casts by minimum total distance."""
    actual, _ = classify(anchor, policy)
    result: Geometry = {'casting': {}, 'actual_count': len(actual), 'center_shift_px': {},
                        'bbox_height_ratio': {}, 'aspect_ratio_vs_source': {},
                        'gates': {name: False for name in ('G1', 'G2', 'G3', 'G4', 'G6')}}
    result['gates']['G1'] = len(actual) == policy.count
    source_actual, _ = classify(source, policy)
    if not result['gates']['G1'] or not set(policy.cast.values()).issubset(source_actual):
        return result
    s = {row.track: row for row in source}
    a = {row.track: row for row in anchor}
    roles = list(policy.cast)
    if len(roles) != len(actual):
        raise ValueError('Actual count and casting role count disagree')
    def cost(candidate: tuple[int, ...]) -> float:
        centers = [(s[policy.cast[role]].center, a[track].center) for role, track in zip(roles, candidate)]
        return sum(math.dist(x, y) if x is not None and y is not None else math.inf for x, y in centers)
    assignment = min(permutations(actual), key=cost)
    result['casting'] = dict(zip(roles, assignment))
    height_pass = []
    for role, track in result['casting'].items():
        first, second = s[policy.cast[role]], a[track]
        assert first.bbox is not None and second.bbox is not None
        assert first.center is not None and second.center is not None
        sw, sh = first.bbox[2]-first.bbox[0], first.bbox[3]-first.bbox[1]
        aw, ah = second.bbox[2]-second.bbox[0], second.bbox[3]-second.bbox[1]
        if min(sw, sh, aw, ah) <= 0:
            raise ValueError('Degenerate bounding box')
        result['center_shift_px'][role] = math.dist(first.center, second.center)
        result['bbox_height_ratio'][role] = ah/sh
        result['aspect_ratio_vs_source'][role] = (ah/aw)/(sh/sw)
        lo, hi = policy.height[role]
        height_pass.append(lo <= ah/sh <= hi)
    result['gates'].update(G2=all(x <= policy.shift*policy.size[0] for x in result['center_shift_px'].values()),
                          G3=height_pass[0], G4=height_pass[1],
                          G6=all(policy.aspect[0] <= x <= policy.aspect[1]
                                 for x in result['aspect_ratio_vs_source'].values()))
    return result


def read_rows(summary: Path, index: int, policy: Policy) -> list[Row]:
    raw = json.loads(summary.read_text())
    if tuple(raw['coordinate_size']) != policy.size:
        raise ValueError('SAM coordinates differ from configured master canvas')
    frame = next(frame for frame in raw['frames'] if frame['index'] == index)
    return [Row(row['track_index'], row['present'], tuple(row['bbox']) if row['bbox'] else None,
                tuple(row['center']) if row['center'] else None, row['area']) for row in frame['objects']]


def mask_union(folder: Path, rows: list[Row], index: int, policy: Policy) -> NDArray[np.bool_]:
    union = np.zeros((policy.size[1], policy.size[0]), dtype=bool)
    for row in rows:
        with Image.open(folder/f'{index:03d}-track-{row.track:02d}.png') as image:
            if image.size != policy.size:
                raise ValueError('Mask dimensions disagree')
            mask = np.asarray(image.convert('L')) > 0
        if int(mask.sum()) != row.area:
            raise ValueError('Mask area disagrees with SAM summary')
        union |= mask
    return union


def main() -> None:
    scene, runtime, output = map(Path, sys.argv[1:])
    policy = Policy.read(scene)
    cfg = json.loads(runtime.read_text())
    source_summary, anchor_summary = Path(cfg['source_summary']), Path(cfg['anchor_summary'])
    index = cfg['source_frame_index']
    source, anchor = read_rows(source_summary, index, policy), read_rows(anchor_summary, 0, policy)
    result = geometry(source, anchor, policy)
    union = mask_union(source_summary.parent, source, index, policy) | mask_union(anchor_summary.parent, anchor, 0, policy)
    dilated = Image.fromarray(union.astype(np.uint8)*255).filter(ImageFilter.MaxFilter(2*policy.dilation+1))
    outside = ~np.asarray(dilated).astype(bool)
    with Image.open(cfg['source_image']) as image:
        if image.size != policy.size:
            raise ValueError('Source image dimensions disagree')
        source_rgb = np.asarray(image.convert('RGB'), dtype=np.float32)
    with Image.open(cfg['anchor_image']) as image:
        if image.size != policy.size:
            raise ValueError('Anchor image dimensions disagree')
        anchor_rgb = np.asarray(image.convert('RGB'), dtype=np.float32)
    mae = float(np.abs(source_rgb-anchor_rgb)[outside].mean()) if outside.any() else None
    result['gates']['G5'] = mae is not None and mae <= policy.mae
    failed = [gate for gate, passed in sorted(result['gates'].items()) if not passed]
    report = {**result, 'failed_gates': failed, 'all_gates_pass': not failed,
              'background_mae': mae, 'background_pixels': int(outside.sum()),
              'G7': {'status': 'NOT_MEASURED', 'reason': 'Separate existing-local-model embedding measurement required', 'gating': False},
              'source_frame_index': index, 'coordinate_size': policy.size,
              'source_classification': classify(source, policy), 'anchor_classification': classify(anchor, policy),
              'scene_config_sha256': hashlib.sha256(scene.read_bytes()).hexdigest(),
              'input_summary_sha256': {role: hashlib.sha256(path.read_bytes()).hexdigest()
                                       for role, path in [('source', source_summary), ('anchor', anchor_summary)]}}
    payload = json.dumps(report, ensure_ascii=False, indent=2)+'\n'
    temporary = output.with_suffix(output.suffix+'.partial')
    temporary.write_text(payload)
    temporary.replace(output)
    if output.read_text() != payload:
        raise OSError('Gate report readback differs')
    print(json.dumps({'failed_gates': failed, 'background_mae': mae}))


if __name__ == '__main__':
    main()
