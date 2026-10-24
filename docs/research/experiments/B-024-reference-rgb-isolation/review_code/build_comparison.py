# /// script
# requires-python = ">=3.11"
# dependencies = ["pillow"]
# ///
# How to run: use the existing CPU Python environment; see --help. No download required.
"""CPU review only: exact 17-frame 30fps source/B023 replacement/B024 neutral-reference comparison.

Inputs must be RGB PNG sequences named 000.png through 016.png, each 896x512.
No optical flow, alignment, temporal interpolation, frame selection or duplication.
Run only after both actual model outputs have been exported by their owning runner.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw

FRAMES = 17
SIZE = (896, 512)
FPS = 30


def sha256(path: Path) -> str:
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()


def load_sequence(folder: Path) -> list[Image.Image]:
    paths = [folder / f'{i:03d}.png' for i in range(FRAMES)]
    if sorted(p.name for p in folder.glob('*.png')) != [p.name for p in paths]:
        raise ValueError(f'Expected exactly 17 numbered PNGs: {folder}')
    images: list[Image.Image] = []
    for path in paths:
        with Image.open(path) as source:
            if source.size != SIZE:
                raise ValueError(f'Unexpected canvas: {path}: {source.size}')
            images.append(source.convert('RGB'))
    return images


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target', type=Path, required=True)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--replacement', type=Path, required=True)
    parser.add_argument('--reference', type=Path, required=True)
    parser.add_argument('--neutral-reference', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    folders = [args.target, args.baseline, args.replacement]
    sequences = [load_sequence(folder) for folder in folders]
    # Validate everything before writing; never replace an earlier review run.
    with Image.open(args.reference) as reference_source:
        reference = reference_source.convert('RGB')
    args.output.mkdir(parents=True, exist_ok=False)
    frames = args.output / 'comparison-frames'
    frames.mkdir()
    labels = ['SOURCE: real f126..142', 'B023: original reference RGB', 'B024: neutral reference RGB']
    sheet = Image.new('RGB', (1344, FRAMES * 280), '#202020')
    for index in range(FRAMES):
        combined = Image.new('RGB', (2688, 544), '#202020')
        draw = ImageDraw.Draw(combined)
        for column, sequence in enumerate(sequences):
            draw.text((column * 896 + 8, 8), f'{labels[column]} | local {index} | source {126 + index}', fill='white')
            combined.paste(sequence[index], (column * 896, 32))
            sheet.paste(sequence[index].resize((448, 256), Image.Resampling.LANCZOS), (column * 448, index * 280 + 24))
            ImageDraw.Draw(sheet).text((column * 448 + 4, index * 280 + 4), f'{labels[column]} f{index}', fill='white')
        combined.save(frames / f'{index:03d}.png')
    sheet.save(args.output / 'comparison-all17.png')
    events = Image.new('RGB', (2688, 3 * 544), '#202020')
    for row, index in enumerate((0, 8, 16)):
        with Image.open(frames / f'{index:03d}.png') as event:
            events.paste(event, (0, row * 544))
    events.save(args.output / 'comparison-local0-8-16.png')
    # Reference is separate, never inserted into the motion timeline.
    reference.save(args.output / 'comparison-reference.png')
    with Image.open(args.neutral_reference) as neutral:
        neutral.save(args.output / 'comparison-reference-gray.png')
    video = args.output / 'comparison-30fps.mp4'
    subprocess.run(['ffmpeg', '-v', 'error', '-framerate', str(FPS), '-i', str(frames / '%03d.png'), '-frames:v', str(FRAMES), '-c:v', 'libx264', '-crf', '18', '-pix_fmt', 'yuv420p', str(video)], check=True)
    metadata = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-count_frames', '-select_streams', 'v:0', '-show_entries', 'stream=width,height,avg_frame_rate,nb_read_frames,duration', '-of', 'json', str(video)]))
    stream = metadata['streams'][0]
    if (stream['width'], stream['height'], stream['avg_frame_rate'], stream['nb_read_frames']) != (2688, 544, '30/1', '17'):
        raise RuntimeError('Encoded timeline/canvas mismatch')
    report = {'scope': 'Static technical review artifacts, not quality acceptance', 'temporal_quality': 'UNVERIFIED', 'physical_timeline': {'fps': FPS, 'frames': FRAMES, 'seconds': FRAMES / FPS}, 'source_frames': list(range(126, 143)), 'operations': 'Same full canvas per input; headers added outside image; no warp, interpolation or duplicate frames. Sheet uniformly downscaled for display only.', 'metadata': metadata, 'inputs': [{'role': labels[k], 'frames': [{'path': str(folder / f'{i:03d}.png'), 'sha256': sha256(folder / f'{i:03d}.png')} for i in range(FRAMES)]} for k, folder in enumerate(folders)], 'reference': {'path': str(args.reference), 'sha256': sha256(args.reference)}, 'neutral_reference': {'path': str(args.neutral_reference), 'sha256': sha256(args.neutral_reference)}, 'outputs': [{'path': str(p.relative_to(args.output)), 'sha256': sha256(p), 'bytes': p.stat().st_size} for p in sorted(args.output.rglob('*')) if p.is_file()]}
    (args.output / 'comparison-manifest.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()


def export_raw(raw_path: Path, output: Path, sheet_path: Path) -> None:
    """Exact pinned cache_video pre-encoding operations; CPU, no model imports."""
    import torch
    import torchvision
    raw = torch.load(raw_path, map_location='cpu', weights_only=True)
    if not isinstance(raw, torch.Tensor) or tuple(raw.shape) != (3, 17, 512, 896) or not bool(torch.isfinite(raw).all()):
        raise ValueError('Unexpected raw tensor')
    output.mkdir(parents=True, exist_ok=False)
    value = raw.unsqueeze(0).clamp(-1, 1)
    frames = torch.stack([torchvision.utils.make_grid(u, nrow=1, normalize=True, value_range=(-1, 1)) for u in value.unbind(2)], dim=1).permute(1, 2, 3, 0)
    frames = (frames * 255).type(torch.uint8).cpu().numpy()
    sheet = Image.new('RGB', (4 * 448, 5 * 280), '#202020')
    for index, frame in enumerate(frames):
        im = Image.fromarray(frame)
        im.save(output / f'{index:03d}.png')
        x, y = (index % 4) * 448, (index // 4) * 280
        sheet.paste(im.resize((448, 256), Image.Resampling.LANCZOS), (x, y + 24))
        ImageDraw.Draw(sheet).text((x + 4, y + 4), f'Frame {index} / source {126 + index}', fill='white')
    sheet.save(sheet_path)
    (output / 'raw-export.json').write_text(json.dumps({'raw': str(raw_path), 'raw_sha256': sha256(raw_path), 'range': [float(raw.min()), float(raw.max())], 'shape': list(raw.shape), 'operation': 'Pinned cache_video clamp(-1,1), make_grid normalize=True value_range=(-1,1) nrow1, mul255 uint8; no codec loss', 'temporal_quality': 'UNVERIFIED'}, indent=2) + '\n')
