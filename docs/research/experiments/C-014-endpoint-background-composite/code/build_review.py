# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# Run: existing-research-python build_review.py PRIVATE_MANIFEST ROOT REVIEW_ROOT
"""Build offline review from observed inputs, RAW, and fixed CPU composites."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import sys

import numpy as np
from PIL import Image, ImageDraw

CASES = ('I50_S1', 'S_S1', 'ON2048_S2_A')
PRIMARY = tuple(range(0, 33, 4))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def copy_verified(source: Path, target: Path) -> str:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise FileExistsError(target)
    shutil.copy2(source, target)
    expected = digest(source)
    if digest(target) != expected:
        raise OSError(f'Copy hash mismatch: {target.name}')
    return expected


def overlay(image: Image.Image, center: list[float]) -> Image.Image:
    y, x = np.indices((240, 416), dtype=np.float64)
    radius = np.hypot(x-center[0], y-center[1])
    weight = np.where(radius <= 44, 1.0, np.where(radius >= 52, 0.0,
        0.5*(1+np.cos(np.pi*(radius-44)/8))))
    tint = np.zeros((240, 416, 4), dtype=np.uint8)
    tint[:, :, :3] = (42, 90, 200)
    tint[:, :, 3] = np.rint(weight*42).astype(np.uint8)
    result = Image.alpha_composite(image.convert('RGBA'), Image.fromarray(tint)).convert('RGB')
    pen = ImageDraw.Draw(result)
    for r, color in ((28, '#ffffff'), (44, '#2a5ac8'), (52, '#a52f1a')):
        pen.ellipse((center[0]-r, center[1]-r, center[0]+r, center[1]+r), outline=color, width=1)
    return result


def build_case(case: str, manifest: dict, context: tuple[Path, Path, dict]) -> dict:
    root, out, paths = context
    origin = manifest['cases'][case]
    media = {}
    for kind, source in [('RAW', Path(origin['raw_mp4'])),
                         ('POST', root/'outputs'/case/'composite.mp4')]:
        relative = f'media/{case}-{kind}.mp4'
        media[kind] = {'path': relative, 'sha256': copy_verified(source, out/relative)}
    frame_hashes = {'RAW': [], 'POST': []}
    sheets = {kind: Image.new('RGB', (208*6, 140*6), 'white') for kind in ('RAW', 'POST')}
    boundary = Image.new('RGB', (224*3, 140*3), 'white')
    for t in range(33):
        center = paths[case][t]
        images = {}
        for kind, folder in [('RAW', Path(origin['raw_frames'])),
                             ('POST', root/'outputs'/case/'frames')]:
            relative = f'frames/{case}/{kind}/{t:03d}.png'
            frame_hashes[kind].append(copy_verified(folder/f'{t:03d}.png', out/relative))
            with Image.open(out/relative) as original:
                image = original.convert('RGB')
            images[kind] = image
            sheets[kind].paste(image.resize((208, 120)), (t % 6*208, t//6*140+20))
            ImageDraw.Draw(sheets[kind]).text((t % 6*208+4, t//6*140+3), f'{kind} t={t} DERIVED', fill='black')
            cx, cy = map(round, center)
            crop = image.crop((cx-56, cy-56, cx+56, cy+56))
            destination = out/'crops'/case/kind/f'{t:03d}.png'
            destination.parent.mkdir(parents=True, exist_ok=True)
            crop.save(destination)
            if t in PRIMARY:
                i = PRIMARY.index(t)
                x = i % 3*224 + (112 if kind == 'POST' else 0)
                boundary.paste(crop, (x, i//3*140+28))
                ImageDraw.Draw(boundary).text((x+3, i//3*140+3), f'{kind} t={t}', fill='black')
        destination = out/'overlays'/case/f'{t:03d}.png'
        destination.parent.mkdir(parents=True, exist_ok=True)
        overlay(images['RAW'], center).save(destination)
    (out/'sheets').mkdir(exist_ok=True)
    for kind, sheet in sheets.items():
        sheet.save(out/'sheets'/f'{case}-{kind}-all33.png')
    boundary.save(out/'sheets'/f'{case}-boundary9.png')
    return {'id': case, 'media': media, 'frame_sha256': frame_hashes}


def main() -> None:
    manifest_path, root, out = map(Path, sys.argv[1:4])
    manifest = json.loads(manifest_path.read_text())
    paths = json.loads((root/'PATHS.json').read_text())
    out.mkdir(parents=True, exist_ok=False)
    entries = [build_case(case, manifest, (root, out, paths)) for case in CASES]
    for key in ('start', 'end'):
        copy_verified(Path(manifest['anchors'][key]), out/'anchors'/f'{key}.png')
    for name in ('background_from_endpoints.png', 'source_map.png'):
        copy_verified(root/'plate'/name, out/'plate'/name)
    with Image.open(root/'plate/source_map.png') as image:
        values = np.array(image)
    if values.ndim == 2:
        colors = np.zeros((*values.shape, 3), dtype=np.uint8)
        colors[values == 1] = (42, 90, 200)
        colors[values == 2] = (207, 126, 38)
        Image.fromarray(colors).save(out/'plate/source_map_display.png')
    else:
        shutil.copy2(out/'plate/source_map.png', out/'plate/source_map_display.png')
    metrics = json.loads((root/'METRICS.json').read_text())
    summaries = {name: {'position': metrics['runs'][name]['position_verdict'],
                        'shift': metrics['runs'][name]['max_center_shift_px'],
                        'core': metrics['runs'][name]['core44_exact_all33'],
                        'outside': metrics['runs'][name]['outside52_exact_all33']}
                 for name in CASES}
    data = {'cases': list(CASES), 'summaries': summaries}
    html = Path(__file__).with_name('viewer.html').read_text().replace('/*DATA*/{}', json.dumps(data))
    (out/'index.html').write_text(html)
    receipt = {'videos': entries, 'raw_copied_byte_exact': True, 'post_is_cpu_composite': True,
               'derived': ['overlays', 'crops', 'sheets', 'source_map_display'],
               'crop': '112x112 centered at rounded requested coordinate; identical RAW/POST',
               'temporal': 'UNVERIFIED'}
    (out/'MEDIA_MANIFEST.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps({'videos': 6, 'lossless_frames': 198, 'temporal': 'UNVERIFIED'}))


if __name__ == '__main__':
    main()
