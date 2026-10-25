# /// script
# requires-python = ">=3.11"
# dependencies = ["pillow", "numpy", "torch"]
# ///
"""Build CPU-only review from actual completed cases. Existing files are preserved."""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import subprocess
from pathlib import Path

import numpy as np
import torch
from PIL import Image, ImageDraw, ImageFont

COUNT, WIDTH, HEIGHT, FPS = 17, 896, 512, 24


def digest(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def raw_pixels(value: torch.Tensor) -> np.ndarray:
    if tuple(value.shape) != (3, COUNT, HEIGHT, WIDTH) or not bool(torch.isfinite(value).all()):
        raise ValueError('Expected finite CTHW [3,17,512,896]')
    # Exact single-image cache_video/make_grid normalization: no grid padding.
    normalized = value.detach().cpu().clone().clamp_(-1, 1)
    normalized.add_(1).div_(2)
    return (normalized.permute(1, 2, 3, 0) * 255).to(torch.uint8).numpy()


def load_raw(path: Path) -> tuple[np.ndarray, dict[str, object]]:
    value = torch.load(path, map_location='cpu', weights_only=True)
    if not isinstance(value, torch.Tensor):
        raise ValueError('Raw output must be a tensor')
    return raw_pixels(value), {'sha256': digest(path), 'shape': list(value.shape),
                              'dtype': str(value.dtype), 'range': [float(value.min()), float(value.max())]}


def inputs(task: Path) -> tuple[list[Image.Image], list[Path]]:
    source = [task / 'inputs/source' / f'{i:03d}.png' for i in range(COUNT)]
    raw = [task / 'cases' / label / 'artifacts/raw_output.pt' for label in ('R1', 'R2')]
    required = source + raw + [task / 'task_manifest.json', task / 'references.png']
    for path in required:
        if not path.is_file():
            raise FileNotFoundError(f'Actual artifact missing: {path}')
    images = []
    for path in source:
        with Image.open(path) as image:
            if image.size != (WIDTH, HEIGHT):
                raise ValueError('Source canvas mismatch')
            images.append(image.convert('RGB'))
    return images, raw


def build_task(task: Path, output: Path) -> dict[str, object]:
    source, raw_paths = inputs(task)
    manifest = json.loads((task / 'task_manifest.json').read_text())
    arrays, raw_info = [], []
    for path in raw_paths:
        pixels, info = load_raw(path)
        arrays.append(pixels)
        raw_info.append(info)
    output.mkdir(parents=True, exist_ok=False)
    frames = output / 'frames'
    frames.mkdir()
    sequences = [source] + [[Image.fromarray(x) for x in a] for a in arrays]
    all_sheet = Image.new('RGB', (1344, 280 * COUNT), '#20262e')
    for i in range(COUNT):
        frame = Image.new('RGB', (2688, 544), '#20262e')
        for column, (label, images) in enumerate(zip(('SOURCE', 'A', 'B'), sequences, strict=True)):
            frame.paste(images[i], (column * WIDTH, 32))
            ImageDraw.Draw(frame).text((column * WIDTH + 8, 8), f'{label} | local {i}', fill='white', font=ImageFont.load_default(size=20))
            all_sheet.paste(images[i].resize((448, 256), Image.Resampling.LANCZOS), (448 * column, 280 * i + 24))
            ImageDraw.Draw(all_sheet).text((448 * column + 8, 280 * i + 4), f'{label} | local {i}', fill='white', font=ImageFont.load_default(size=14))
        frame.save(frames / f'{i:03d}.png')
    all_sheet.save(output / 'all17.png')
    events = Image.new('RGB', (2688, 1632))
    for row, index in enumerate((0, 8, 16)):
        with Image.open(frames / f'{index:03d}.png') as image:
            events.paste(image, (0, row * 544))
    events.save(output / 'local0-8-16.png')
    with Image.open(task / 'references.png') as refs:
        refs.save(output / 'references.png')
    for label, images in zip(('A', 'B'), sequences[1:], strict=True):
        folder = output / f'{label}-raw-frames'
        folder.mkdir()
        for i, image in enumerate(images):
            image.save(folder / f'{i:03d}.png')
    video = output / 'comparison-preview24.mp4'
    subprocess.run(['ffmpeg', '-v', 'error', '-framerate', str(FPS), '-i', str(frames / '%03d.png'),
                    '-frames:v', str(COUNT), '-c:v', 'libx264', '-crf', '18', '-pix_fmt', 'yuv420p', str(video)], check=True)
    probe = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-count_frames', '-select_streams', 'v:0',
                    '-show_entries', 'stream=width,height,avg_frame_rate,nb_read_frames', '-of', 'json', str(video)]))
    stream = probe['streams'][0]
    if (stream['width'], stream['height'], stream['avg_frame_rate'], stream['nb_read_frames']) != (2688, 544, '24/1', '17'):
        raise ValueError('Comparison video contract failed')
    subprocess.run(['ffmpeg', '-v', 'error', '-i', str(video), '-f', 'null', '-'], check=True)
    report = {'task_id': task.name, 'source_fps': None, 'preview_fps': FPS, 'timebase_assumed': True,
              'frames': COUNT, 'preview_duration_seconds': COUNT / FPS, 'temporal': 'UNVERIFIED',
              'mapping': {'A': 'R1', 'B': 'R2'}, 'task_manifest_sha256': digest(task / 'task_manifest.json'),
              'raw': raw_info, 'source_frame_hashes': [digest(task / 'inputs/source' / f'{i:03d}.png') for i in range(COUNT)],
              'operations': 'Full canvas; headers outside image; uniform sheet downscale. No warp, interpolation, stabilization or frame duplication.',
              'raw_export': 'Pinned nrow1 make_grid normalization: clone clamp(-1,1), add1 div2, multiply255 uint8.',
              'ffprobe': probe, 'input_contract': manifest,
              'outputs': {str(p.relative_to(output)): digest(p) for p in sorted(output.rglob('*')) if p.is_file()}}
    (output / 'manifest.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def write_viewer(root: Path, names: list[str]) -> None:
    blocks = []
    for name in names:
        safe = html.escape(name, quote=True)
        blocks.append(f'''<section data-task="{safe}"><h2>{safe}: SOURCE / A / B</h2>
<p>Native FPS unknown; preview 24fps, 17 frames, 0.708333s. Temporal quality UNVERIFIED.</p>
<video controls preload="metadata" src="{safe}/comparison-preview24.mp4"></video>
<p>Single playback. Manually restarting crosses the end→start boundary; that boundary is not within-source motion.</p>
<div><button class="prev" disabled>Previous frame</button> <button class="next">Next frame</button>
<label>Local frame <input type="range" min="0" max="16" value="0"><output>0</output></label></div>
<img class="frame" src="{safe}/frames/000.png" alt="Source and neutral A/B frame comparison">
<p><a href="{safe}/all17.png">All 17 frames</a> · <a href="{safe}/local0-8-16.png">Local 0/8/16</a> · <a href="{safe}/manifest.json">Provenance</a></p>
<details><summary>Reveal inputs and mapping (A=R1, B=R2)</summary><img src="{safe}/references.png" alt="Both input references"></details></section>''')
    template = Path(__file__).with_name('viewer.html').read_text()
    (root / 'review.html').write_text(template.replace('<!-- TASKS -->', '\n'.join(blocks)))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--private-root', required=True, type=Path)
    parser.add_argument('--tasks', nargs='+', default=['animal', 'human', 'vehicle'])
    parser.add_argument('--output-name', default='review')
    args = parser.parse_args()
    for name in args.tasks:
        if Path(name).name != name:
            raise ValueError('Task must be a single directory name')
        inputs(args.private_root / 'tasks' / name)
    output = args.private_root / args.output_name
    output.mkdir(exist_ok=False)
    for name in args.tasks:
        build_task(args.private_root / 'tasks' / name, output / name)
    write_viewer(output, args.tasks)
    print(output / 'review.html')


if __name__ == '__main__':
    main()
