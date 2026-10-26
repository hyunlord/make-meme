# /// script
# requires-python = ">=3.11"
# dependencies = ["pillow"]
# ///
"""CPU review media from existing RGB frames; never encodes or changes an MP4.

Run: python build_review.py B027_ROOT B031_ROOT B032_ROOT DESTINATION
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from PIL import Image, ImageDraw

LABELS: Final = ('SOURCE', 'B031 RAW', 'FIXED_ENVELOPE', 'MASK_ASSISTED')
FRAMES: Final = tuple(range(17))
KEYS: Final = (0, 8, 16)
CROPS: Final = ((160, 170, 760, 430), (80, 340, 760, 465), (0, 395, 430, 512))


@dataclass(frozen=True, slots=True)
class ReviewRoots:
    baseline: Path
    anchor: Path
    experiment: Path
    destination: Path


def sha256(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def copied(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)


def frame(path: Path) -> Image.Image:
    with Image.open(path) as image:
        if image.size != (896, 512):
            raise ValueError(f'Expected896x512: {path.name}')
        return image.convert('RGB')


def sequences(roots: ReviewRoots) -> tuple[Path, Path, Path, Path]:
    return (roots.baseline / 'tasks/vehicle/inputs/source',
            roots.experiment / 'inputs/raw-frames',
            roots.experiment / 'outputs/FIXED_ENVELOPE/frames',
            roots.experiment / 'outputs/MASK_ASSISTED/frames')


def sheets(roots: ReviewRoots) -> None:
    """Full17 and fixed-coordinate keyframe crops are review derivatives only."""
    rows = sequences(roots)
    board = Image.new('RGB', (1792, 280 * 17), '#10151e')
    draw = ImageDraw.Draw(board)
    for index in FRAMES:
        for column, (label, directory) in enumerate(zip(LABELS, rows, strict=True)):
            draw.text((448 * column + 8, 280 * index + 4), f'{label} | local {index:02}', fill='white')
            board.paste(frame(directory / f'{index:03}.png').resize((448, 256), Image.Resampling.LANCZOS),
                        (448 * column, 280 * index + 24))
    board.save(roots.destination / 'all17.jpg', quality=92, subsampling=0)
    detail = Image.new('RGB', (1792, 280 * 9), '#10151e')
    draw = ImageDraw.Draw(detail)
    for ki, index in enumerate(KEYS):
        for ci, box in enumerate(CROPS):
            row = ki * 3 + ci
            for column, (label, directory) in enumerate(zip(LABELS, rows, strict=True)):
                draw.text((448 * column + 8, 280 * row + 4),
                          f'{label} | {index:02} | crop {box}', fill='white')
                crop = frame(directory / f'{index:03}.png').crop(box)
                crop.thumbnail((448, 256), Image.Resampling.LANCZOS)
                detail.paste(crop, (448 * column, 280 * row + 24))
    detail.save(roots.destination / 'details.jpg', quality=94, subsampling=0)


def supports(roots: ReviewRoots) -> None:
    paths = (roots.baseline / 'tasks/vehicle/inputs/source-mask',
             roots.experiment / 'annotations/target',
             roots.experiment / 'outputs/FIXED_ENVELOPE/edit-support',
             roots.experiment / 'outputs/MASK_ASSISTED/edit-support')
    labels = ('SOURCE RED GT SUPPORT', 'ANNOTATED TARGET (PARTIAL)', 'FIXED E (0..255 preview)', 'MASK E (0..255 preview)')
    board = Image.new('RGB', (1792, 280 * 17), '#10151e')
    draw = ImageDraw.Draw(board)
    for index in FRAMES:
        for column, (label, directory) in enumerate(zip(labels, paths, strict=True)):
            draw.text((448 * column + 8, 280 * index + 4), f'{label} | local {index:02}', fill='white')
            board.paste(frame(directory / f'{index:03}.png').resize((448, 256), Image.Resampling.NEAREST),
                        (448 * column, 280 * index + 24))
    board.save(roots.destination / 'supports.jpg', quality=94, subsampling=0)


def main() -> None:
    roots = ReviewRoots(*(Path(value).resolve() for value in sys.argv[1:5]))
    roots.destination.mkdir(parents=True, exist_ok=False)
    videos = (roots.baseline / 'tasks/vehicle/inputs/driver.mp4',
              roots.anchor / 'video/tasks/vehicle/cases/R1/artifacts/output.mp4',
              roots.experiment / 'outputs/FIXED_ENVELOPE/output.mp4',
              roots.experiment / 'outputs/MASK_ASSISTED/output.mp4')
    names = ('source.mp4', 'B031-raw.mp4', 'fixed.mp4', 'mask.mp4')
    for source, name in zip(videos, names, strict=True):
        copied(source, roots.destination / name)
    sheets(roots)
    supports(roots)
    copied(Path(__file__).with_name('viewer.html'), roots.destination / 'review.html')
    entries = [{'path': name, 'bytes': (roots.destination / name).stat().st_size,
                'sha256': sha256(roots.destination / name), 'origin_sha256': sha256(source)}
               for source, name in zip(videos, names, strict=True)]
    if any(row['sha256'] != row['origin_sha256'] for row in entries):
        raise IOError('MP4 copy integrity failure')
    (roots.destination / 'MEDIA_MANIFEST.json').write_text(json.dumps({
        'videos': entries, 'existing_video_modified': False, 'new_composite_encodes': 2,
        'review_sheet_crops': CROPS, 'source_fps': None, 'preview_fps': 24,
        'timebase_assumed': True, 'temporal': 'UNVERIFIED'}, indent=2) + '\n')


if __name__ == '__main__':
    main()
