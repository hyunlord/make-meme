# /// script
# requires-python = ">=3.11"
# dependencies = ["pillow"]
# ///
"""Build private B031 review material without re-encoding any MP4.

Run: python delivery.py B027_ROOT B031_ROOT DESTINATION
Final public reports and run receipts are copied separately before packaging.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from PIL import Image, ImageDraw

TASKS: Final = ('animal', 'human', 'vehicle')
REFS: Final = ('R1', 'R2')


@dataclass(frozen=True, slots=True)
class Roots:
    baseline: Path
    experiment: Path
    destination: Path


def digest(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def anchor_state(case: Path) -> str:
    if (case / 'A0.png').is_file():
        return 'RAW_SAVED_REVIEW_SEPARATE'
    if (case / 'attempt.json').is_file():
        return 'ATTEMPTED_WITHOUT_OUTPUT'
    return 'NOT_RUN'


def copy(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    if digest(source) != digest(target):
        raise IOError(f'Copy hash mismatch: {source.name}')


def frames(path: Path, target: Path) -> list[Image.Image]:
    target.mkdir()
    subprocess.run(['ffmpeg', '-v', 'error', '-i', str(path), '-vsync', '0',
                    str(target / '%03d.png')], check=True)
    files = sorted(target.glob('*.png'))
    if len(files) != 17:
        raise ValueError(f'Expected17frames: {path.name}: {len(files)}')
    images = []
    for item in files:
        with Image.open(item) as image:
            if image.size != (896, 512):
                raise ValueError(f'Unexpectedcanvas: {path.name}')
            images.append(image.convert('RGB'))
    return images


def sheet(videos: dict[str, Path], target: Path) -> None:
    """One full-canvas all17 sheet, not a selected-frame quality proxy."""
    with tempfile.TemporaryDirectory(prefix='b031-sheet-') as temporary:
        series = [frames(path, Path(temporary) / str(i)) for i, path in enumerate(videos.values())]
        width, row_height = 448 * len(series), 280
        board = Image.new('RGB', (width, row_height * 17), '#10151e')
        draw = ImageDraw.Draw(board)
        for index in range(17):
            for column, (label, sequence) in enumerate(zip(videos, series, strict=True)):
                draw.text((column * 448 + 8, index * row_height + 5),
                          f'{label} | local {index:02}', fill='white')
                board.paste(sequence[index].resize((448, 256), Image.Resampling.LANCZOS),
                            (column * 448, index * row_height + 24))
        board.save(target, quality=92, subsampling=0)


def task(roots: Roots, name: str) -> str:
    """Copy one task's complete fixed panel; return its HTML-neutral JSON entry."""
    base = roots.baseline / 'tasks' / name
    target = roots.destination / name
    target.mkdir(parents=True, exist_ok=False)
    copy(base / 'inputs/driver.mp4', target / 'source.mp4')
    videos = {'SOURCE': target / 'source.mp4'}
    cases = []
    for reference in REFS:
        case_id = f'{name}_{reference}'
        source_input = roots.experiment / 'inputs' / case_id
        for item in source_input.iterdir():
            if item.is_file():
                copy(item, target / reference / 'inputs' / item.name)
        baseline = base / 'cases' / reference / 'artifacts/output.mp4'
        copy(baseline, target / f'B027-{reference}.mp4')
        videos[f'B027 {reference}'] = target / f'B027-{reference}.mp4'
        anchor = roots.experiment / 'anchors' / case_id
        state = anchor_state(anchor)
        for filename in ('A0.png', 'attempt.json', 'result.json'):
            if (anchor / filename).is_file():
                copy(anchor / filename, target / reference / filename)
        effective = anchor / 'effective-inputs'
        if effective.is_dir():
            entries = [{'path': str(item.relative_to(anchor)), 'bytes': item.stat().st_size,
                        'sha256': digest(item)} for item in sorted(effective.rglob('*')) if item.is_file()]
            (target / reference / 'EFFECTIVE_INPUTS_FULL_ONLY.json').write_text(json.dumps({
                'archive': 'full', 'reason': 'Encoder resize evidence retained without compact duplicates',
                'files': entries}, indent=2) + '\n')
        review_path = roots.experiment / 'delivery/REVIEW_STATUS.json'
        review = json.loads(review_path.read_text()) if review_path.is_file() else {'cases': {}}
        eligibility = review['cases'].get(case_id, {}).get('eligibility', 'NOT_REVIEWED')
        cases.append({'reference': reference, 'state': state, 'eligibility': eligibility, 'anchor_saved': (anchor / 'A0.png').is_file()})
    # Video worker publishes only eligible R1. Missing is explicitly shown, never substituted.
    video = roots.experiment / 'video/tasks' / name / 'cases/R1/artifacts/output.mp4'
    if video.is_file():
        copy(video, target / 'B031-R1.mp4')
        videos['B031 R1'] = target / 'B031-R1.mp4'
    reference_root = roots.experiment / 'video' / name / 'inputs'
    for filename in ('reference.png', 'reference-mask.png', 'anchor_suitability.json', 'mask-receipt.json'):
        if (reference_root / filename).is_file():
            copy(reference_root / filename, target / filename)
    sheet(videos, target / 'all17.jpg')
    manifest = [{'path': str(path.relative_to(target)), 'bytes': path.stat().st_size,
                 'sha256': digest(path)} for path in sorted(target.rglob('*')) if path.is_file()]
    (target / 'MEDIA_MANIFEST.json').write_text(json.dumps({'files': manifest,
        'video_reencoded': False, 'source_fps': None, 'preview_fps': 24,
        'timebase_assumed': True, 'temporal': 'UNVERIFIED'}, indent=2) + '\n')
    return json.dumps({'name': name, 'cases': cases, 'video_saved': video.is_file(),
        'rstar_saved': (reference_root / 'reference.png').is_file(),
        'sheet_columns': len(videos), 'sheet_labels': list(videos)}, ensure_ascii=False)


def main() -> None:
    roots = Roots(*(Path(value).resolve() for value in sys.argv[1:4]))
    roots.destination.mkdir(parents=True, exist_ok=True)
    data = '[' + ','.join(task(roots, name) for name in TASKS) + ']'
    template = Path(__file__).with_name('viewer.html').read_text()
    (roots.destination / 'review.html').write_text(template.replace('/*TASK_DATA*/[]', data))
    copy(roots.experiment / 'inputs/INPUT_CONTRACT.json', roots.destination / 'INPUT_CONTRACT.json')


if __name__ == '__main__':
    main()
