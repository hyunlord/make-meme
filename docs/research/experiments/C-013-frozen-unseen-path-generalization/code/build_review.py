# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# Run: research-python build_review.py PARENT_ROOT C013_ROOT REVIEW_ROOT
"""Package unchanged MP4 and PNG frames with derived comparison sheets."""
from pathlib import Path
import json
import shutil
import sys
from PIL import Image, ImageDraw


def main() -> None:
    parent, root, out = map(Path, sys.argv[1:4])
    out.mkdir(parents=True, exist_ok=True)
    metrics = json.loads((root / 'METRICS.json').read_text())
    paths = json.loads((root / 'PATHS.json').read_text())['paths']
    entries = []
    names = ['I25_S1', 'I50_S1', 'I75_S1', 'S_S1', 'ON2048_A', 'ON2048_B', 'BASE_S2', 'ON2048_S2_A', 'ON2048_S2_B']
    for name in names:
        fresh = name in ('I25_S1', 'I50_S1', 'I75_S1', 'S_S1', 'BASE_S2')
        source = (root if fresh else parent) / 'outputs' / name
        (out / 'media').mkdir(exist_ok=True)
        (out / 'frames' / name).mkdir(parents=True, exist_ok=True)
        (out / 'sheets').mkdir(exist_ok=True)
        shutil.copy2(source / 'generated.mp4', out / 'media' / f'{name}.mp4')
        for t in range(33):
            shutil.copy2(source / 'frames' / f'{t:03d}.png', out / 'frames' / name / f'{t:03d}.png')
        sheet = Image.new('RGB', (416 * 3, 268 * 3), 'white')
        draw = ImageDraw.Draw(sheet)
        for i, t in enumerate(range(0, 33, 4)):
            with Image.open(source / 'frames' / f'{t:03d}.png') as im:
                sheet.paste(im, (i % 3 * 416, i // 3 * 268 + 28))
            draw.text((i % 3 * 416 + 8, i // 3 * 268 + 8), f'{name} / t={t} / DERIVED SHEET', fill='black')
        sheet.save(out / 'sheets' / f'{name}.png')
        run = metrics['runs'][name]
        j = run.get('judgment')
        path = name.removesuffix('_S1')
        target = paths[path]['center_xy_pixel_index'] if path in paths else []
        if name in ('ON2048_A', 'ON2048_B'):
            sys.path.insert(0, str(parent / 'code'))
            from render_task import path_center
            target = [path_center(name[-1], t / 32) for t in range(33)]
        description = f"배경 RGB MAE {run['background_mean_all33']['rgb_mae']:.2f}"
        if j:
            description += f" · 주시점 오차 {j['mean_observed_error_px']:.2f}px · {j['interpretation']} · 검출 실패 {len(j['bad_frames'])}/33"
        entries.append({'id': name, 'tab': 'new' if j else ('seed2' if 'S2' in name else 'parent'), 'label': 'C-013 신규 생성 / 원 MP4' if fresh else 'C-012 이전 생성 / 원 MP4', 'description': description, 'target': target, 'centers': [row['center'] for row in run['rows']], 'oracle': path if path in paths else None})
    for name in paths:
        (out / 'oracle' / name).mkdir(parents=True, exist_ok=True)
        for t in range(33):
            shutil.copy2(root / 'oracle' / name / 'frames' / f'{t:03d}.png', out / 'oracle' / name / f'{t:03d}.png')
    data = {'entries': entries, 'summary': metrics['interpolation_verdict'] + ' · ' + metrics['s_verdict']}
    html = (Path(__file__).parent / 'viewer.html').read_text().replace('/*DATA*/{}', json.dumps(data, ensure_ascii=False))
    (out / 'index.html').write_text(html)
    print(json.dumps({'videos':len(entries),'frames':33*len(entries),'original_mp4_preserved':True}))


if __name__ == '__main__':
    main()
