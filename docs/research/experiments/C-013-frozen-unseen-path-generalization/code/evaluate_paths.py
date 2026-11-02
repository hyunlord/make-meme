# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# Run: existing-research-python evaluate_paths.py PARENT_ROOT NEW_ROOT fixtures|evaluate
"""Reuse the frozen full-frame C-012 reader; render evaluation-only oracles."""
from pathlib import Path
import json
import math
import sys
import cv2
import numpy as np
from PIL import Image
from criteria import CORE, judge


def main() -> None:
    parent, root = Path(sys.argv[1]), Path(sys.argv[2])
    sys.path.insert(0, str(parent / 'code'))
    from evaluate import Reader, load_rgb, fixtures
    from render_task import sprite, place, compose, path_center
    reader = Reader(parent / 'task')
    paths = json.loads((root / 'PATHS.json').read_text())['paths']
    bg = load_rgb(parent / 'task/background.png')
    spr = sprite()
    oracle = root / 'oracle'
    union = np.zeros((240, 416), np.uint8)
    truths = {}
    for name, entry in paths.items():
        folder = oracle / name
        (folder / 'frames').mkdir(parents=True, exist_ok=True)
        (folder / 'mask').mkdir(exist_ok=True)
        rows = []
        for t, (x, y) in enumerate(entry['center_xy_pixel_index']):
            rgb, mask = compose(bg, place(spr, x, y))
            Image.fromarray(rgb).save(folder / 'frames' / f'{t:03d}.png')
            Image.fromarray(mask).save(folder / 'mask' / f'{t:03d}.png')
            union |= mask
            rows.append(reader.ball(rgb))
        truths[name] = rows
    for path in ('A', 'B'):
        for t in range(33):
            union |= np.array(Image.open(parent / 'task' / path / 'mask' / f'{t:03d}.png'))
    # Euclidean-radius 8px dilation, specified explicitly before output evaluation.
    yy, xx = np.mgrid[-8:9, -8:9]
    roi = cv2.dilate(union, ((xx * xx + yy * yy) <= 64).astype(np.uint8)) == 0
    Image.fromarray(roi.astype(np.uint8) * 255).save(root / 'background-roi.png')
    if sys.argv[3] == 'fixtures':
        report = {'label': 'EVALUATION_ORACLE_NOT_MODEL_OUTPUT', 'parent': fixtures(parent / 'task'), 'new': {}, 'trained_rejections': {}}
        for name, rows in truths.items():
            result = judge(rows, paths[name]['center_xy_pixel_index'], s_path=name == 'S')
            report['new'][name] = result
            assert max(result['errors_px']) < 1 and result['full_path_quality_pass']
            for old in ('A', 'B'):
                oldrows = [reader.ball(load_rgb(parent / 'task' / old / 'source' / f'{t:03d}.png')) for t in range(33)]
                check = judge(oldrows, paths[name]['center_xy_pixel_index'], s_path=name == 'S')
                report['trained_rejections'][f'{name}_from_{old}'] = check
                assert not check['full_path_quality_pass']
        assert report['parent']['pass']
        report['pass'] = True
        (root / 'FIXTURES.json').write_text(json.dumps(report, indent=2))
        print('FIXTURES_PASS')
        return
    assert json.loads((root / 'FIXTURES.json').read_text())['pass']
    runs = {}
    sources = {f'{p}_S1': root / 'outputs' / f'{p}_S1' for p in paths}
    sources['BASE_S2'] = root / 'outputs/BASE_S2'
    sources.update({p: parent / 'outputs' / p for p in ('BASE', 'ON2048_A', 'ON2048_B', 'ON2048_S2_A', 'ON2048_S2_B')})
    for name, folder in sources.items():
        if not (folder / 'frames/032.png').exists():
            runs[name] = {'status': 'ARTIFACT_UNAVAILABLE'}
            continue
        rows = []
        for t in range(33):
            frame = load_rgb(folder / 'frames' / f'{t:03d}.png')
            difference = np.abs(frame.astype(np.float64) - bg)[roi]
            markers = reader.background_shift(frame)
            shifts = np.array([[r['dx'], r['dy']] for r in markers['markers'].values()])
            reliable = all(r['peak'] >= .5 for r in markers['markers'].values()) and float(np.max(np.linalg.norm(shifts - np.median(shifts, axis=0), axis=1))) <= 3
            markers['interpretation'] = 'CONSISTENT_MARKERS' if reliable else 'MARKER_UNRELIABLE / BACKGROUND_DEFORMATION'
            rows.append({'frame': t, **reader.ball(frame), 'markers': markers,
                         'background': {'rgb_mae': float(difference.mean()), 'absolute_channel_difference_p95': float(np.percentile(difference, 95)), 'pixel_mean_rgb_difference_gt25_fraction': float((difference.mean(axis=1) > 25).mean())}})
        summary = {key: float(np.mean([r['background'][key] for r in rows])) for key in rows[0]['background']}
        runs[name] = {'status': 'EVALUATED', 'rows': rows, 'background_mean_all33': summary}
        if name in [f'{p}_S1' for p in paths]:
            path = name.removesuffix('_S1')
            runs[name]['judgment'] = judge(rows, paths[path]['center_xy_pixel_index'], s_path=path == 'S')
        if name in ('ON2048_A', 'ON2048_B'):
            for path in paths:
                runs[name].setdefault('observed_parent_vs_requested', {})[path] = judge(rows, paths[path]['center_xy_pixel_index'], s_path=path == 'S')
    joint = []
    complete = all(runs[f'{p}_S1']['status'] == 'EVALUATED' for p in ('I25', 'I50', 'I75'))
    for t in (CORE if complete else ()):
        centers = [runs[f'{p}_S1']['rows'][t]['center'] for p in ('I25', 'I50', 'I75')]
        gaps = None if any(c is None for c in centers) else [centers[i + 1][1] - centers[i][1] for i in (0, 1)]
        target_gap = paths['I50']['center_xy_pixel_index'][t][1] - paths['I25']['center_xy_pixel_index'][t][1]
        x_ok = gaps is not None and all(abs(c[0] - (104 + 208 * t / 32)) <= 8.4 for c in centers)
        joint.append({'frame': t, 'centers': centers, 'adjacent_y_gaps': gaps, 'minimum_gap': target_gap / 2, 'pass': bool(x_ok and all(g > 0 and g >= target_gap / 2 for g in gaps))})
    interpolation = complete and all(r['pass'] for r in joint) and all(runs[f'{p}_S1']['judgment']['full_path_quality_pass'] for p in ('I25', 'I50', 'I75'))
    result = {'experiment': 'C-013', 'detector': {'template': 64, 'present': .5, 'duplicate_ratio': .75, 'search': 'whole_frame'}, 'roi_pixels': int(roi.sum()), 'roi_dilation': 'Euclidean disk radius8', 'runs': runs, 'interpolation_joint': joint, 'interpolation_verdict': ('SAME_SCENE_INTERPOLATION_SUPPORTED' if interpolation else 'INTERPOLATION_NOT_SUPPORTED') if complete else 'INCONCLUSIVE', 's_verdict': ('NEW_PATH_SHAPE_SUPPORTED' if runs['S_S1']['judgment']['full_path_quality_pass'] else 'NEW_PATH_SHAPE_NOT_SUPPORTED') if runs['S_S1']['status'] == 'EVALUATED' else 'INCONCLUSIVE', 'verdict_scope': 'MECHANICAL_GEOMETRY_ONLY: appearance and identity continuity require static review; temporal unverified', 'temporal': 'UNVERIFIED', 'appearance_review': 'PENDING_STATIC_REVIEW'}
    (root / 'METRICS.json').write_text(json.dumps(result, indent=2))
    print(json.dumps({k: v for k, v in result.items() if k != 'runs'}, indent=2))


if __name__ == '__main__':
    main()
