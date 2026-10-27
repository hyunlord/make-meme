"""Build B034 review sheets from existing lossless frames; never re-encode MP4.

Usage: python build_review.py PRIVATE_REVIEW_MANIFEST.json DEST
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path
from typing import Final

from PIL import Image, ImageDraw

CASE_IDS: Final = ("rigid_R1", "nonrigid_R1")
KEYS: Final = (0, 8, 16)


def sha256(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def frame(path: Path) -> Image.Image:
    with Image.open(path) as image:
        if image.size != (896, 512):
            raise ValueError(f'Expected896x512: {path.name}')
        return image.convert('RGB')


def sheet(rows: list[tuple[str, Path]], output: Path, *, details: bool, crops: tuple[tuple[int, int, int, int], ...] = ()) -> None:
    indexes = KEYS if details else tuple(range(17))
    boxes = crops if details else ((0, 0, 896, 512),)
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
    manifest_path, destination = (Path(value).resolve() for value in sys.argv[1:3])
    config = json.loads(manifest_path.read_text())
    if tuple(case['case_id'] for case in config['cases']) != CASE_IDS:
        raise ValueError('Expected the two frozen case IDs in order')
    destination.mkdir(parents=True, exist_ok=False)
    cases: list[dict[str, object]] = []
    entries: list[dict[str, object]] = []
    for case in config['cases']:
        alias = case['case_id']
        task = Path(case['task_root'])
        target = destination / alias
        target.mkdir()
        images = []
        for label, key in [('SOURCE f0', 'source_image'), ('TARGET original', 'target_image'),
                           ('TARGET model input', 'target_model_image'), ('A0 generated anchor', 'anchor_image'),
                           ('R_star', 'reference_image')]:
            if not case.get(key):
                continue
            origin = Path(case[key])
            name = key + origin.suffix.lower()
            shutil.copyfile(origin, target / name)
            images.append({'label': label, 'path': alias + '/' + name})
            entries.append({'case': alias, 'path': alias + '/' + name, 'sha256': sha256(origin), 'bytes': origin.stat().st_size})
        source_frames = task / 'inputs/source'
        original_source_video = task / 'inputs/driver.mp4'
        source_video = Path(case['source_preview']) if case.get('source_preview') else original_source_video
        definitions = [('SOURCE', source_video, source_frames)]
        expected = ('SOURCE_RECON', 'BASE', 'BASE_RGB_POST', 'FINAL_LATENT_ONLY',
                    'FINAL_LATENT_ONLY_RGB_POST', 'STEP_CONSTRAINED', 'STEP_CONSTRAINED_RGB_POST')
        present = case.get('completed_outputs', [])
        if len(present) != len(set(present)) or set(present) - set(expected):
            raise ValueError('Unknown or duplicate output names')
        if case['anchor_status'] == 'ANCHOR_UNSUITABLE' and present:
            raise ValueError('Unsuitable anchor must not have video outputs')
        for name in expected:
            if name in present:
                directory = task / 'outputs' / name
                definitions.append((name, directory / 'output.mp4', directory / 'frames'))
        videos = []
        for label, origin, frames in definitions:
            for index in range(17):
                frame(frames / f'{index:03}.png')
            name = label.lower() + '.mp4'
            shutil.copyfile(origin, target / name)
            digest = sha256(target / name)
            if digest != sha256(origin):
                raise IOError('MP4 copy mismatch')
            videos.append({'label': label, 'path': alias + '/' + name,
                           'derived_preview': label == 'SOURCE' and bool(case.get('source_preview'))})
            entries.append({'case': alias, 'path': alias + '/' + name, 'sha256': digest,
                            'origin_sha256': digest, 'bytes': origin.stat().st_size})
        crops = tuple(tuple(int(v) for v in box) for box in case.get('frozen_crops', []))
        if any(len(box) != 4 or not (0 <= box[0] < box[2] <= 896 and 0 <= box[1] < box[3] <= 512) for box in crops):
            raise ValueError('Invalid frozen crop')
        sheets = []
        for group in ('raw', 'post'):
            rows = [(label, frames) for label, _, frames in definitions
                    if label == 'SOURCE' or (label.endswith('_RGB_POST') == (group == 'post'))]
            if group == 'post' and len(rows) == 1:
                continue
            sheet(rows, target / f'{group}-all17.jpg', details=False)
            sheets.append({'label': group + ' all17', 'path': alias + f'/{group}-all17.jpg'})
            if crops:
                sheet(rows, target / f'{group}-details.jpg', details=True, crops=crops)
                sheets.append({'label': group + ' local0/8/16 frozen crops', 'path': alias + f'/{group}-details.jpg'})
        cases.append({'case_id': alias, 'anchor_status': case['anchor_status'],
                      'video_status': case['video_status'], 'reason': case.get('reason', ''),
                      'images': images, 'videos': videos, 'sheets': sheets,
                      'original_source_sha256': sha256(original_source_video),
                      'source_preview_is_new_encode': bool(case.get('source_preview')),
                      'not_run': [name for name in expected if name not in present], 'frozen_crops': crops})
    data = {'cases': cases, 'source_fps': None, 'preview_fps': 24, 'timebase_assumed': True,
            'temporal': 'UNVERIFIED', 'videos_reencoded_by_packaging': False}
    template = Path(__file__).with_name('viewer.html').read_text()
    encoded = json.dumps(data, ensure_ascii=False).replace('<', '\\u003c')
    (destination / 'review.html').write_text(template.replace('__REVIEW_DATA__', encoded))
    (destination / 'MEDIA_MANIFEST.json').write_text(json.dumps({**data, 'files': entries}, ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    main()
