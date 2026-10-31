# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""C-012 fixed position reader and pilot criteria. Fixed before any generated output is seen.

The reader never receives the requested path: it searches the WHOLE frame with one template
(the start-anchor ball crop), reports the best peak, and flags missing/duplicate. It does not pick
the candidate closest to the answer and does not warp outputs.
"""
from pathlib import Path
import json
import math
import sys

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from render_task import W, H, D, MARKERS, SAMPLE_FRAMES, path_center

TEMPLATE = 64            # square crop around the start-anchor ball
PRESENT = 0.50           # TM_CCOEFF_NORMED peak needed to call the ball present
DUPLICATE_RATIO = 0.75   # second peak (>= 1 d away) >= PRESENT and >= ratio*first -> duplicate
MARKER_BOX = 25
TOL = 0.35 * D           # 19.6 px


def load_rgb(path: Path) -> np.ndarray:
    with Image.open(path) as image:
        return np.array(image.convert('RGB'))


class Reader:
    def __init__(self, task: Path):
        start = load_rgb(task / 'anchors/start.png')
        cx, cy = path_center('A', 0.0)
        h = TEMPLATE // 2
        x0, y0 = int(round(cx - (TEMPLATE - 1) / 2)), int(round(cy - (TEMPLATE - 1) / 2))
        self.offset = (cx - x0, cy - y0)                 # template-pixel position of the ball centre
        self.template = start[y0:y0 + TEMPLATE, x0:x0 + TEMPLATE].copy()
        bg = load_rgb(task / 'background.png')
        self.markers = {}
        for name, (mx, my) in MARKERS.items():
            r = MARKER_BOX // 2
            self.markers[name] = (bg[my - r:my + r + 1, mx - r:mx + r + 1].copy(), (mx - r, my - r))
        del h

    def ball(self, frame: np.ndarray) -> dict:
        assert frame.shape == (H, W, 3) and frame.dtype == np.uint8
        score = cv2.matchTemplate(frame, self.template, cv2.TM_CCOEFF_NORMED)
        _, first, _, loc = cv2.minMaxLoc(score)
        suppressed = score.copy()
        x, y = loc
        suppressed[max(0, y - D):y + D + 1, max(0, x - D):x + D + 1] = -1
        _, second, _, loc2 = cv2.minMaxLoc(suppressed)
        center = [x + self.offset[0], y + self.offset[1]]
        status = 'ok'
        if first < PRESENT:
            status = 'missing'
        elif second >= PRESENT and second >= DUPLICATE_RATIO * first:
            status = 'duplicate'
        return {'status': status, 'center': center if status == 'ok' else None, 'peak': float(first),
                'second_peak': float(second), 'raw_best_center': center,
                'second_center': [loc2[0] + self.offset[0], loc2[1] + self.offset[1]]}

    def background_shift(self, frame: np.ndarray) -> dict:
        shifts = {}
        for name, (crop, (x0, y0)) in self.markers.items():
            score = cv2.matchTemplate(frame, crop, cv2.TM_CCOEFF_NORMED)
            _, peak, _, loc = cv2.minMaxLoc(score)
            shifts[name] = {'dx': loc[0] - x0, 'dy': loc[1] - y0, 'peak': float(peak)}
        moved = [math.hypot(s['dx'], s['dy']) for s in shifts.values()]
        return {'markers': shifts, 'median_shift_px': float(np.median(moved))}


def read_video(reader: Reader, frames: list[np.ndarray], taus: list[float]) -> list[dict]:
    rows = []
    for frame, tau in zip(frames, taus):
        rows.append({'tau': tau, **reader.ball(frame), 'background': reader.background_shift(frame)})
    return rows


def path_rows(rows: list[dict], path: str) -> list[float | None]:
    out = []
    for row in rows:
        gx, gy = path_center(path, row['tau'])
        out.append(None if row['center'] is None else math.hypot(row['center'][0] - gx, row['center'][1] - gy))
    return out


def judge_pair(rows_a: list[dict], rows_b: list[dict]) -> dict:
    """Pilot criteria (work order 11.3) for one method; rows are the 9 pre-registered samples."""
    result = {}
    central = [i for i, r in enumerate(rows_a) if 0.25 - 1e-9 <= r['tau'] <= 0.75 + 1e-9]
    interior = [i for i, r in enumerate(rows_a) if 0 < r['tau'] < 1]
    for name, rows in (('A', rows_a), ('B', rows_b)):
        errors = path_rows(rows, name)
        observed = [e for e in errors if e is not None]
        bad = [i for i, r in enumerate(rows) if r['status'] != 'ok']
        sign = -1 if name == 'A' else 1
        side = [rows[i]['center'] is not None and sign * (rows[i]['center'][1] - H * 0.5) > 0 for i in central]
        bg = max(r['background']['median_shift_px'] for r in rows)
        result[name] = {
            'errors_px': errors, 'missing_or_duplicate': [rows[i]['status'] for i in bad], 'bad_indices': bad,
            'c1_identified_8_of_9': len(rows) - len(bad) >= 8,
            'c3_mean_observed_error_px': float(np.mean(observed)) if observed else None,
            'c3_pass': bool(observed) and float(np.mean(observed)) <= TOL,
            'c4_start_end_pass': errors[0] is not None and errors[-1] is not None and errors[0] <= TOL and errors[-1] <= TOL,
            'c5_central_side_count': int(sum(side)), 'c5_pass': sum(side) >= 4,
            'c8_max_background_shift_px': bg, 'c8_pass': bg <= 3.0,
            'central_missing': any(i in central for i in bad)}
    mid = 4   # the pre-registered tau=4/8 sample; for N != 33 frames its actual tau is round(0.5*(N-1))/(N-1)
    ca, cb = rows_a[mid]['center'], rows_b[mid]['center']
    gap = None if ca is None or cb is None else math.hypot(ca[0] - cb[0], ca[1] - cb[1])
    truth = abs(path_center('A', rows_a[mid]['tau'])[1] - path_center('B', rows_a[mid]['tau'])[1])
    result['c6_mid_gap_px'] = gap
    result['c6_pass'] = gap is not None and gap >= 0.5 * truth
    matched, swapped = [], []
    for i in interior:
        for rows, own, other in ((rows_a, 'A', 'B'), (rows_b, 'B', 'A')):
            c = rows[i]['center']
            if c is None:
                continue
            tau = rows[i]['tau']
            matched.append(math.dist(c, path_center(own, tau)))
            swapped.append(math.dist(c, path_center(other, tau)))
    result['c7_matched_mean_px'] = float(np.mean(matched)) if matched else None
    result['c7_swapped_mean_px'] = float(np.mean(swapped)) if swapped else None
    result['c7_pass'] = bool(matched) and np.mean(matched) <= 0.5 * np.mean(swapped)
    every = all(result[p][k] for p in 'AB' for k in ('c1_identified_8_of_9', 'c3_pass', 'c4_start_end_pass', 'c5_pass', 'c8_pass'))
    every = every and result['c6_pass'] and result['c7_pass']
    branch = result['A']['c5_pass'] and result['B']['c5_pass'] and result['c6_pass']
    central_missing = result['A']['central_missing'] or result['B']['central_missing']
    if every and not central_missing:
        verdict = 'CAPABILITY_PASS'
    elif branch:
        verdict = 'PARTIAL_CONTROL'
    else:
        verdict = 'NO_CONTROL'
    result['verdict_mechanical'] = verdict
    result['note'] = 'c9 (appearance kept, not a colour blob) is the template peak >= PRESENT plus the visual sheet check.'
    return result


def judge_single(rows: list[dict]) -> dict:
    """BASE has no trajectory input; report errors against both target paths only."""
    return {'errors_vs_A_px': path_rows(rows, 'A'), 'errors_vs_B_px': path_rows(rows, 'B'),
            'statuses': [r['status'] for r in rows], 'centers': [r['center'] for r in rows]}


def frames_from_dir(folder: Path, indices) -> list[np.ndarray]:
    return [load_rgb(folder / f'{i:03d}.png') for i in indices]


def fixtures(task: Path) -> dict:
    """Validate the reader on renderer truth, an empty background and a duplicate-object frame."""
    reader = Reader(task)
    taus = [t / 32 for t in SAMPLE_FRAMES]
    out = {}
    for path in 'AB':
        rows = read_video(reader, frames_from_dir(task / path / 'source', SAMPLE_FRAMES), taus)
        out[f'truth_{path}'] = {'max_error_px': max(path_rows(rows, path)), 'statuses': [r['status'] for r in rows],
                                'min_peak': min(r['peak'] for r in rows)}
    out['truth_pair'] = judge_pair(read_video(reader, frames_from_dir(task / 'A/source', SAMPLE_FRAMES), taus),
                                   read_video(reader, frames_from_dir(task / 'B/source', SAMPLE_FRAMES), taus))['verdict_mechanical']
    empty = reader.ball(load_rgb(task / 'background.png'))
    out['empty_background'] = {'status': empty['status'], 'peak': empty['peak']}
    a16 = load_rgb(task / 'A/source/016.png'); b16 = load_rgb(task / 'B/source/016.png')
    mb = np.array(Image.open(task / 'B/mask/016.png')) > 0
    dup = a16.copy(); dup[mb] = b16[mb]
    d = reader.ball(dup)
    out['duplicate_object'] = {'status': d['status'], 'peak': d['peak'], 'second_peak': d['second_peak']}
    shifted = np.roll(load_rgb(task / 'A/source/016.png'), (6, 9), (0, 1))
    out['camera_shift_9x6'] = reader.background_shift(shifted)['median_shift_px']
    out['pass'] = (out['truth_A']['max_error_px'] < 1.0 and out['truth_B']['max_error_px'] < 1.0
                   and out['truth_pair'] == 'CAPABILITY_PASS' and empty['status'] == 'missing'
                   and d['status'] == 'duplicate' and out['camera_shift_9x6'] > 9)
    return out


if __name__ == '__main__':
    print(json.dumps(fixtures(Path(sys.argv[1])), indent=2))
