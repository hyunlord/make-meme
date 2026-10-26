"""Build B033 review sheets from existing lossless frames; never re-encode MP4.

Usage: python build_review.py B027_ROOT B031_ROOT B032_ROOT B033_ROOT DEST
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path
from typing import Final

from PIL import Image, ImageDraw

CROPS: Final = ((160, 170, 760, 430), (80, 340, 760, 465), (0, 395, 430, 512))
KEYS: Final = (0, 8, 16)


def sha256(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def frame(path: Path) -> Image.Image:
    with Image.open(path) as image:
        if image.size != (896, 512):
            raise ValueError(f'Expected896x512: {path.name}')
        return image.convert('RGB')


def sheet(rows: list[tuple[str, Path]], output: Path, *, details: bool) -> None:
    indexes = KEYS if details else tuple(range(17))
    boxes = CROPS if details else ((0, 0, 896, 512),)
    board = Image.new('RGB', (448 * len(rows), 280 * len(indexes) * len(boxes)), '#10151e')
    draw = ImageDraw.Draw(board)
    for ii, index in enumerate(indexes):
        for bi, box in enumerate(boxes):
            y = 280 * (ii * len(boxes) + bi)
            for column, (label, directory) in enumerate(rows):
                draw.text((448 * column + 8, y + 4), f'{label} | {index:02} | {box}', fill='white')
                crop = frame(directory / f'{index:03}.png').crop(box)
                crop.thumbnail((448, 256), Image.Resampling.LANCZOS)
                board.paste(crop, (448 * column, y + 24))
    board.save(output, quality=92, subsampling=0)


def main() -> None:
    b27, b31, b32, b33, destination = (Path(value).resolve() for value in sys.argv[1:6])
    destination.mkdir(parents=True, exist_ok=False)
    definitions = [
        ('SOURCE', 'source.mp4', b27 / 'tasks/vehicle/inputs/driver.mp4', b27 / 'tasks/vehicle/inputs/source'),
        ('SOURCE RECON', 'source-recon.mp4', b33 / 'outputs/SOURCE_RECON/output.mp4', b33 / 'outputs/SOURCE_RECON/frames'),
        ('B031 RAW', 'B031-raw.mp4', b31 / 'video/tasks/vehicle/cases/R1/artifacts/output.mp4', b32 / 'inputs/raw-frames'),
        ('B032 RGB_POST', 'B032-post.mp4', b32 / 'outputs/MASK_ASSISTED/output.mp4', b32 / 'outputs/MASK_ASSISTED/frames'),
        ('FINAL RAW', 'final-raw.mp4', b33 / 'outputs/FINAL_LATENT_ONLY/output.mp4', b33 / 'outputs/FINAL_LATENT_ONLY/frames'),
        ('FINAL RGB_POST', 'final-post.mp4', b33 / 'outputs/FINAL_LATENT_ONLY_RGB_POST/output.mp4', b33 / 'outputs/FINAL_LATENT_ONLY_RGB_POST/frames'),
        ('STEP RAW', 'step-raw.mp4', b33 / 'outputs/STEP_CONSTRAINED/output.mp4', b33 / 'outputs/STEP_CONSTRAINED/frames'),
        ('STEP RGB_POST', 'step-post.mp4', b33 / 'outputs/STEP_CONSTRAINED_RGB_POST/output.mp4', b33 / 'outputs/STEP_CONSTRAINED_RGB_POST/frames'),
    ]
    entries: list[dict[str, str | int]] = []
    for label, name, origin, directory in definitions:
        for index in range(17):
            frame(directory / f'{index:03}.png')
        target = destination / name
        shutil.copyfile(origin, target)
        digest = sha256(target)
        if digest != sha256(origin):
            raise IOError('MP4 copy mismatch')
        entries.append({'label': label, 'path': name, 'bytes': target.stat().st_size, 'sha256': digest, 'origin_sha256': digest})
    for name, indices in [('post', (0, 3, 5, 7)), ('raw', (0, 1, 2, 4, 6))]:
        rows = [(definitions[i][0], definitions[i][3]) for i in indices]
        sheet(rows, destination / f'{name}-all17.jpg', details=False)
        sheet(rows, destination / f'{name}-details.jpg', details=True)
    shutil.copyfile(b32 / 'delivery/review-payload/supports.jpg', destination / 'frozen-B032-supports.jpg')
    shutil.copyfile(Path(__file__).with_name('viewer.html'), destination / 'review.html')
    (destination / 'MEDIA_MANIFEST.json').write_text(json.dumps({
        'videos': entries, 'video_bytes_modified_by_packaging': False,
        'new_derived_encodes': ['source-recon', 'final-raw', 'final-post', 'step-raw', 'step-post'],
        'review_sheet_crops': CROPS, 'review_frames': KEYS, 'source_fps': None,
        'preview_fps': 24, 'timebase_assumed': True, 'temporal': 'UNVERIFIED',
        'wedge_location': 'Rear-wheel wedge may be support margin; target interior not established',
    }, indent=2) + '\n')


if __name__ == '__main__':
    main()
