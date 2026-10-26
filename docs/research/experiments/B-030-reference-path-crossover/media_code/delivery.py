# /// script
# requires-python = ">=3.11"
# dependencies = ["pillow"]
# ///
"""CPU review derivatives; original source and output MP4 bytes remain untouched."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

LABELS = ('SOURCE', 'Y11: VAE1 / CLIP1', 'Y12: VAE1 / CLIP2',
          'Y21: VAE2 / CLIP1', 'Y22: VAE2 / CLIP2')


def digest(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def render_row(frames: list[Image.Image], index: int) -> Image.Image:
    if len(frames) != 5 or any(frame.size != (896, 512) for frame in frames):
        raise ValueError('Expected five unmodified 896x512 canvases')
    row = Image.new('RGB', (2240, 280), '#111827')
    draw = ImageDraw.Draw(row)
    for column, (frame, label) in enumerate(zip(frames, LABELS, strict=True)):
        row.paste(frame.resize((448, 256), Image.Resampling.LANCZOS), (column * 448, 24))
        draw.text((column * 448 + 8, 5), f'{label} | local {index:02}', fill='white')
    return row


def decode(path: Path, destination: Path) -> list[Image.Image]:
    destination.mkdir()
    subprocess.run(['ffmpeg', '-v', 'error', '-i', str(path), '-vsync', '0',
                    str(destination / '%03d.png')], check=True)
    files = sorted(destination.glob('*.png'))
    if len(files) != 17:
        raise ValueError(f'Expected 17 frames: {path.name}: {len(files)}')
    return [Image.open(path).convert('RGB') for path in files]


def task(baseline: Path, experiment: Path, destination: Path, name: str) -> None:
    original = baseline / 'tasks' / name
    fresh = experiment / 'tasks' / name
    target = destination / name
    target.mkdir(parents=True, exist_ok=False)
    sources = {
        'source.mp4': original / 'inputs/driver.mp4',
        'Y11.mp4': original / 'cases/R1/artifacts/output.mp4',
        'Y12.mp4': fresh / 'cases/R1/artifacts/output.mp4',
        'Y21.mp4': fresh / 'cases/R2/artifacts/output.mp4',
        'Y22.mp4': original / 'cases/R2/artifacts/output.mp4',
    }
    for reference in ('R1', 'R2'):
        sources[f'{reference}.png'] = original / 'inputs' / reference / 'reference.png'
        sources[f'{reference}-mask.png'] = original / 'inputs' / reference / 'reference-mask.png'
    manifest = []
    for name_out, source in sources.items():
        shutil.copyfile(source, target / name_out)
        checksum = digest(source)
        if checksum != digest(target / name_out):
            raise ValueError('Copy hash mismatch')
        manifest.append({'file': name_out, 'sha256': checksum, 'bytes': source.stat().st_size})
    with tempfile.TemporaryDirectory(prefix='b030-review-frames-') as temporary:
        series = [decode(sources[label], Path(temporary) / str(index))
                  for index, label in enumerate(('source.mp4', 'Y11.mp4', 'Y12.mp4', 'Y21.mp4', 'Y22.mp4'))]
        rows = [render_row([frames[index] for frames in series], index) for index in range(17)]
        sheet = Image.new('RGB', (2240, 280 * 17))
        for index, row in enumerate(rows):
            sheet.paste(row, (0, index * 280))
        sheet.save(target / 'all17.jpg', quality=94, subsampling=0)
        events = Image.new('RGB', (2240, 840))
        for row_number, frame_number in enumerate((0, 8, 16)):
            events.paste(rows[frame_number], (0, row_number * 280))
        events.save(target / 'local0-8-16.png')
    (target / 'MEDIA_MANIFEST.json').write_text(json.dumps({
        'originals': manifest, 'sheet_input': 'exact MP4 decoded RGB frames',
        'sheet_only_scale': 0.5, 'all_canvases_equal_scale': True,
        'output_video_reencoded': False, 'source_fps': None, 'preview_fps': 24,
        'timebase_assumed': True, 'temporal_quality': 'UNVERIFIED',
    }, indent=2) + '\n')


def viewer(destination: Path) -> None:
    template = Path(__file__).with_name('viewer.html').read_text()
    (destination / 'review.html').write_text(template)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('baseline', type=Path)
    parser.add_argument('experiment', type=Path)
    parser.add_argument('destination', type=Path)
    parser.add_argument('--task', choices=('human', 'vehicle'))
    args = parser.parse_args()
    for name in (args.task,) if args.task else ('human', 'vehicle'):
        task(args.baseline, args.experiment, args.destination, name)
    viewer(args.destination)


if __name__ == '__main__':
    main()
