# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# Run: build_review.py /abs/experiment_root /abs/review_out
"""C-012 compact review package: MP4s (derived), 9-sample sheets, requested-vs-observed path plots, viewer.

Generated originals are untouched; every file here is a derived copy for viewing.
"""
from pathlib import Path
import json
import shutil
import subprocess
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
from render_task import path_center, W, H

ROWS = [
    ('truth', 'ORACLE_RENDERER (정답, 학습 target — 생성 아님)', 'task/A/source', 'task/B/source', 33, None),
    ('recon', 'VAE 재구성 (RECONSTRUCTION_CONTROL 진단 — 생성 아님)', 'outputs/build/recon_A', 'outputs/build/recon_B', 33, 'recon'),
    ('base', 'ENDPOINT_BASE (adapter OFF, 궤적 입력 없음 — A/B 공통 1개)', 'outputs/BASE/frames', 'outputs/BASE/frames', 33, None),
    ('layout', 'NATIVE_LAYOUT (정답 mask 윤곽 — dense 정보)', 'outputs/LAYOUT_A/frames', 'outputs/LAYOUT_B/frames', 33, 'LAYOUT'),
    ('on256', 'adapter ckpt 256 (seed 20261028)', 'outputs/ON256_A/frames', 'outputs/ON256_B/frames', 33, 'ON256'),
    ('on1024', 'adapter ckpt 1024 (seed 20261028)', 'outputs/ON1024_A/frames', 'outputs/ON1024_B/frames', 33, 'ON1024'),
    ('on2048', 'adapter ckpt 2048 (seed 20261028) — 최초 기준 통과', 'outputs/ON2048_A/frames', 'outputs/ON2048_B/frames', 33, 'ON2048'),
    ('on2048s2', 'adapter ckpt 2048 (사전 고정 두 번째 seed 20261029)', 'outputs/ON2048_S2_A/frames', 'outputs/ON2048_S2_B/frames', 33, 'ON2048_S2'),
    ('draganything', 'DragAnything 공식 (첫 이미지+궤적, 576×320·20f → 416×240 역변환)', 'outputs/DRAGANYTHING/eval416_A', 'outputs/DRAGANYTHING/eval416_B', 20, 'DRAGANYTHING'),
]


def mp4(folder: Path, n: int, fps: int, out: Path) -> None:
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-framerate', str(fps), '-i', str(folder / '%03d.png'), '-frames:v', str(n),
                    '-c:v', 'libx264', '-crf', '18', '-pix_fmt', 'yuv420p', str(out)], check=True)


def sheet(folder: Path, n: int, out: Path) -> None:
    idx = [round(k / 8 * (n - 1)) for k in range(9)]
    s = Image.new('RGB', (9 * 208, 134), '#202020'); d = ImageDraw.Draw(s)
    for c, i in enumerate(idx):
        with Image.open(folder / f'{i:03d}.png') as im:
            s.paste(im.convert('RGB').resize((208, 120)), (c * 208, 14))
        d.text((c * 208 + 4, 1), f'tau={i}/{n - 1}', fill='white')
    s.save(out)


def plot(metric: dict | None, out: Path) -> None:
    img = Image.new('RGB', (W * 2, H * 2), '#f4f1ea'); d = ImageDraw.Draw(img)
    for path, colour in (('A', (40, 90, 200)), ('B', (200, 70, 40))):
        pts = [(path_center(path, t / 64)[0] * 2, path_center(path, t / 64)[1] * 2) for t in range(65)]
        d.line(pts, fill=colour, width=2)
        if metric:
            for r in metric[f'rows_{path}']:
                x, y = r['raw_best_center']
                if r['status'] == 'ok':
                    d.ellipse((2 * x - 7, 2 * y - 7, 2 * x + 7, 2 * y + 7), fill=colour)
                else:
                    d.line((2 * x - 8, 2 * y - 8, 2 * x + 8, 2 * y + 8), fill=colour, width=3)
                    d.line((2 * x - 8, 2 * y + 8, 2 * x + 8, 2 * y - 8), fill=colour, width=3)
    d.line((0, H, 2 * W, H), fill=(150, 150, 150), width=1)
    d.text((8, 8), 'line = requested path (A blue, B red); dot = read centre; x = missing/duplicate (best peak shown)', fill='black')
    img.save(out)


def main() -> None:
    root, out = Path(sys.argv[1]), Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=False)
    metrics = json.loads((root / 'METRICS.json').read_text())
    entries = []
    for key, label, fa, fb, n, mkey in ROWS:
        fps = 16 if n == 33 else 7
        item = {'key': key, 'label': label, 'frames': n, 'fps': fps, 'files': {}}
        for side, folder in (('A', fa), ('B', fb)):
            if key == 'base' and side == 'B':
                continue
            folder = root / folder
            mp4(folder, n, fps, out / f'{key}_{side}.mp4')
            sheet(folder, n, out / f'{key}_{side}_sheet.png')
            item['files'][side] = {'mp4': f'{key}_{side}.mp4', 'sheet': f'{key}_{side}_sheet.png'}
            if n == 20:
                mp4(folder, n, 10, out / f'{key}_{side}_compare10fps.mp4')   # comparison speed: 20f over ~2 s like 33f@16
                item['files'][side]['compare'] = f'{key}_{side}_compare10fps.mp4'
        m = metrics.get(mkey) if mkey else None
        plot(m if m and 'rows_A' in m else None, out / f'{key}_paths.png')
        item['paths_plot'] = f'{key}_paths.png'
        if m and 'judge' in m and 'verdict_mechanical' in m['judge']:
            j = m['judge']
            item['judge'] = {'verdict': j['verdict_mechanical'], 'mid_gap_px': j['c6_mid_gap_px'],
                             'matched_px': j['c7_matched_mean_px'], 'swapped_px': j['c7_swapped_mean_px'],
                             'A': {k: j['A'][k] for k in ('c3_mean_observed_error_px', 'missing_or_duplicate', 'c5_central_side_count', 'c8_max_background_shift_px')},
                             'B': {k: j['B'][k] for k in ('c3_mean_observed_error_px', 'missing_or_duplicate', 'c5_central_side_count', 'c8_max_background_shift_px')}}
        entries.append(item)
    shutil.copy(root / 'task/anchors/start.png', out / 'anchor_start.png')
    shutil.copy(root / 'task/anchors/end.png', out / 'anchor_end.png')
    (out / 'entries.json').write_text(json.dumps(entries, indent=2))
    html = (Path(__file__).resolve().parent / 'viewer.html').read_text().replace('/*ENTRIES*/[]', json.dumps(entries))
    (out / 'index.html').write_text(html)
    print(json.dumps({'entries': len(entries), 'files': len(list(out.iterdir()))}))


if __name__ == '__main__':
    main()
