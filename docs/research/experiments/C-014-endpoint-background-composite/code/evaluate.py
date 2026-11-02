# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# Run: existing-research-python evaluate.py PRIVATE_MANIFEST ROOT C012_ROOT C013_ROOT
"""CPU-only RAW/POST evaluation; no compositor or renderer oracle generation."""
from __future__ import annotations

import importlib.util
import json
import math
import os
from pathlib import Path
import sys
from types import ModuleType
from typing import TypedDict

for variable in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[variable] = '2'

import cv2
import numpy as np
from numpy.typing import NDArray
from PIL import Image

RGB = NDArray[np.uint8]
Mask = NDArray[np.bool_]
PRIMARY = (0, 4, 8, 12, 16, 20, 24, 28, 32)
CENTRAL = (8, 12, 16, 20, 24)
CASES = ('I50_S1', 'S_S1', 'ON2048_S2_A')


class Zone(TypedDict):
    pixels: int
    rgb_mae: float | None
    absolute_channel_difference_p95: float | None
    pixel_mean_rgb_difference_gt25_fraction: float | None


def module_at(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_rgb(path: Path) -> RGB:
    with Image.open(path) as image:
        if image.format != 'PNG' or image.mode != 'RGB' or image.size != (416, 240):
            raise ValueError(('RGB_PNG_CONTRACT', path.name, image.format, image.mode, image.size))
        return np.array(image)


def distance(center: list[float]) -> NDArray[np.float64]:
    yy, xx = np.mgrid[:240, :416]
    return np.hypot(xx - center[0], yy - center[1])


def zone_stats(frame: RGB, plate: RGB, mask: Mask) -> Zone:
    count = int(mask.sum())
    if count == 0:
        return {'pixels': 0, 'rgb_mae': None, 'absolute_channel_difference_p95': None,
                'pixel_mean_rgb_difference_gt25_fraction': None}
    delta = np.abs(frame.astype(np.float64) - plate.astype(np.float64))[mask]
    return {'pixels': count, 'rgb_mae': float(delta.mean()),
            'absolute_channel_difference_p95': float(np.percentile(delta, 95)),
            'pixel_mean_rgb_difference_gt25_fraction': float((delta.mean(axis=1) > 25).mean())}


def zones(center: list[float]) -> dict[str, Mask]:
    d = distance(center)
    return {'OBJECT_CORE': d <= 28, 'PRESERVED_COLLAR': (d > 32) & (d <= 44),
            'FEATHER_RING': (d > 44) & (d < 52), 'COPIED_OUTSIDE': d >= 52}


def a_position(rows: list[dict], targets: list[list[float]]) -> dict:
    """Reuse the C-012 A-only criteria; pair separation and background are not position gates."""
    errors = [math.dist(row['center'], q) if row['status'] == 'ok' and row['center'] is not None
              else None for row, q in zip(rows, targets, strict=True)]
    observed = [errors[t] for t in PRIMARY if errors[t] is not None]
    mean = sum(observed) / len(observed) if observed else None
    side = sum(rows[t]['status'] == 'ok' and rows[t]['center'] is not None
               and rows[t]['center'][1] < 120 for t in CENTRAL)
    endpoints = all(errors[t] is not None and errors[t] <= 19.6 for t in (0, 32))
    central_valid = all(errors[t] is not None for t in CENTRAL)
    passed = len(observed) >= 8 and mean is not None and mean <= 19.6 and endpoints and side >= 4 and central_valid
    return {'criteria': 'C-012 A-only c1/c3/c4/c5 and no central detection failure; pair criteria not applicable',
            'errors_px': errors, 'identified_samples': len(observed), 'mean_observed_error_px': mean,
            'endpoint_errors_px': [errors[0], errors[32]], 'central_upper_count': side,
            'central_detection_valid': central_valid, 'position_pass': passed,
            'all33_single': all(row['status'] == 'ok' for row in rows)}


def evaluate(manifest: Path, root: Path, parents: tuple[Path, Path]) -> dict:
    c012, c013 = parents
    cv2.setNumThreads(2)
    reader_module = module_at('c014_parent_reader', c012 / 'code/evaluate.py')
    criteria = module_at('c014_parent_criteria', c013 / 'code/criteria.py')
    reader = reader_module.Reader(c012 / 'task')
    inputs = json.loads(manifest.read_text())['cases']
    paths = json.loads((root / 'PATHS.json').read_text())
    previous = json.loads((c013 / 'METRICS.json').read_text())['runs']
    plate = load_rgb(root / 'plate/background_from_endpoints.png')
    far = np.ones((240, 416), dtype=np.bool_)
    for name in CASES:
        target = paths[name]
        if len(target) != 33 or np.asarray(target).shape != (33, 2) or not np.isfinite(target).all():
            raise ValueError(('PATH_CONTRACT', name))
        for center in target:
            far &= distance(center) >= 52
    runs = {}
    for name in CASES:
        raw_dir = Path(inputs[name]['raw_frames'])
        post_dir = root / 'outputs' / name / 'frames'
        rows = []
        mismatches = []
        for t, center in enumerate(paths[name]):
            raw = load_rgb(raw_dir / f'{t:03d}.png')
            post = load_rgb(post_dir / f'{t:03d}.png')
            before, after = reader.ball(raw), reader.ball(post)
            old = previous[name]['rows'][t]
            if before['status'] != old['status'] or before['center'] != old['center'] or abs(before['peak'] - old['peak']) > 1e-7:
                mismatches.append(t)
            shift = math.dist(before['center'], after['center']) if before['center'] is not None and after['center'] is not None else None
            regions = zones(center)
            d = distance(center)
            rows.append({'frame': t, 'target_center': center, 'raw': before, 'post': after,
                         'center_shift_px': shift,
                         'core44_exact': bool(np.array_equal(raw[d <= 44], post[d <= 44])),
                         'outside52_exact': bool(np.array_equal(post[d >= 52], plate[d >= 52])),
                         'zones': {key: {'raw': zone_stats(raw, plate, mask), 'post': zone_stats(post, plate, mask)} for key, mask in regions.items()},
                         'far_roi': {'raw': zone_stats(raw, plate, far), 'post': zone_stats(post, plate, far)}})
        raw_rows = [r['raw'] for r in rows]
        post_rows = [r['post'] for r in rows]
        if name == 'ON2048_S2_A':
            before_judge, after_judge = a_position(raw_rows, paths[name]), a_position(post_rows, paths[name])
        else:
            before_judge = criteria.judge(raw_rows, paths[name], s_path=name == 'S_S1')
            after_judge = criteria.judge(post_rows, paths[name], s_path=name == 'S_S1')
        shifts = [r['center_shift_px'] for r in rows if r['center_shift_px'] is not None]
        warnings = [t for t in PRIMARY if rows[t]['center_shift_px'] is not None and rows[t]['center_shift_px'] > 2]
        new_key_failure = [t for t in (0, *CENTRAL, 32) if rows[t]['raw']['status'] == 'ok' and rows[t]['post']['status'] != 'ok']
        before_pass = before_judge.get('full_path_quality_pass', before_judge['position_pass'])
        after_pass = after_judge.get('full_path_quality_pass', after_judge['position_pass'])
        retained = before_pass and after_pass and not warnings and not new_key_failure
        verdict = 'POSITION_RETAINED' if retained else 'POSITION_OR_DETECTION_REGRESSION'
        if mismatches or not before_judge['position_pass']:
            verdict = 'UNCERTAIN'
        summary = {}
        for zone in rows[0]['zones']:
            summary[zone] = {}
            for version in ('raw', 'post'):
                series = [r['zones'][zone][version] for r in rows]
                summary[zone][version] = {key: float(np.mean([s[key] for s in series]))
                                         if all(s[key] is not None for s in series) else None for key in series[0]}
        runs[name] = {'rows': rows, 'raw_judgment': before_judge, 'post_judgment': after_judge,
                      'raw_parent_parity': 'PASS' if not mismatches else 'MISMATCH', 'raw_parent_mismatch_frames': mismatches,
                      'max_center_shift_px': max(shifts) if shifts else None,
                      'primary_center_shift_gt2_frames': warnings, 'post_only_key_detection_failure_frames': new_key_failure,
                      'position_verdict': verdict, 'zone_mean_all33': summary,
                      'core44_exact_all33': all(r['core44_exact'] for r in rows),
                      'outside52_exact_all33': all(r['outside52_exact'] for r in rows),
                      'clipping': 'PENDING_VISUAL_REVIEW', 'seam': 'PENDING_VISUAL_REVIEW'}
    return {'experiment': 'C-014', 'reference': 'endpoint-observed plate', 'detector': {'template': 64, 'present': .5, 'duplicate_ratio': .75, 'search': 'whole_frame'},
            'far_roi_pixels': int(far.sum()), 'far_roi_definition': 'outside union of all 99 requested outer disks; copy-contract check, not independent gain',
            'runs': runs, 'temporal': 'UNVERIFIED', 'object_core_background_error_interpretation': 'NOT a background quality metric',
            'summary_aggregation': 'arithmetic mean of per-frame zone metrics; p95 is mean of per-frame per-channel absolute-difference p95'}


def main() -> None:
    args = [arg for arg in sys.argv[1:] if arg != '--cpu-only']
    if len(args) != 4:
        raise SystemExit('Usage: evaluate.py PRIVATE_MANIFEST ROOT C012_ROOT C013_ROOT')
    manifest, root, c012, c013 = map(Path, args)
    report = evaluate(manifest, root, (c012, c013))
    output = root / 'METRICS.json'
    with output.open('x') as stream:
        json.dump(report, stream, indent=2)
        stream.write('\n')
    print(json.dumps({name: {'position': run['position_verdict'], 'max_shift': run['max_center_shift_px'],
                            'raw_parent_parity': run['raw_parent_parity']} for name, run in report['runs'].items()}))


if __name__ == '__main__':
    main()
