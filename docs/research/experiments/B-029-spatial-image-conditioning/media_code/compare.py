# /// script
# requires-python = ">=3.11"
# dependencies = ["pillow", "numpy", "torch"]
# ///
# Run with the existing environment: python compare.py OLD_ROOT NEW_ROOT TASK REF MODE
"""Build one completed B027/B029 case comparison without touching raw artifacts."""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import torch
from PIL import Image, ImageDraw, ImageFont

WIDTH: Final = 896
HEIGHT: Final = 512
COUNT: Final = 17
FPS: Final = 24


@dataclass(frozen=True, slots=True)
class ReviewContractError(ValueError):
    detail: str

    def __str__(self) -> str:
        return self.detail


def digest(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def source_frames(folder: Path) -> list[Image.Image]:
    images = []
    for index in range(COUNT):
        with Image.open(folder / f'{index:03d}.png') as image:
            if image.size != (WIDTH, HEIGHT):
                raise ReviewContractError('Source canvas must be 896x512')
            images.append(image.convert('RGB'))
    return images


def raw_frames(path: Path) -> list[Image.Image]:
    value = torch.load(path, map_location='cpu', weights_only=True)
    if not isinstance(value, torch.Tensor):
        raise ReviewContractError('Raw must be a tensor')
    if tuple(value.shape) != (3, COUNT, HEIGHT, WIDTH) or not bool(value.isfinite().all()):
        raise ReviewContractError('Expected finite raw CTHW [3,17,512,896]')
    pixels = ((value.detach().cpu().clone().clamp(-1, 1) + 1) / 2 * 255)
    arrays = pixels.permute(1, 2, 3, 0).to(torch.uint8).numpy()
    return [Image.fromarray(array) for array in arrays]


def render_row(images: list[Image.Image], labels: tuple[str, ...], index: int | None) -> Image.Image:
    if len(images) != len(labels) or any(image.size != (WIDTH, HEIGHT) for image in images):
        raise ReviewContractError('Labels and full-canvas images must agree')
    row = Image.new('RGB', (WIDTH * len(images), HEIGHT + 32), '#20262e')
    draw = ImageDraw.Draw(row)
    for column, (image, label) in enumerate(zip(images, labels, strict=True)):
        row.paste(image, (column * WIDTH, 32))
        title = label if index is None else f'{label} | local {index}'
        draw.text((column * WIDTH + 8, 6), title, fill='white', font=ImageFont.load_default(size=20))
    return row


@dataclass(frozen=True, slots=True)
class Case:
    baseline: Path
    current: Path
    task: str
    reference: str
    mode: str = "METHOD"

    @property
    def name(self) -> str:
        return f'{self.task}-{self.reference}-{self.mode}'


def build_case(case: Case) -> Path:
    old = case.baseline / 'tasks' / case.task
    new = case.current / 'tasks' / case.task
    raw_old = old / 'cases' / case.reference / 'artifacts/raw_output.pt'
    raw_new = new / 'METHOD/cases' / case.reference / 'artifacts/raw_output.pt'
    raw_control = new / 'CONTROL/cases' / case.reference / 'artifacts/raw_output.pt'
    labels = ('SOURCE', 'B027 BASE', 'B029 METHOD')
    raw_paths = {'B027': raw_old, 'METHOD': raw_new}
    source = source_frames(old / 'inputs/source')
    sequences = [source, raw_frames(raw_old), raw_frames(raw_new)]
    if case.mode == 'CONTROL':
        sequences.append(raw_frames(raw_control))
        labels += ('B029 CONTROL',)
        raw_paths['CONTROL'] = raw_control
    columns = len(sequences)
    output = case.current / 'review' / case.name
    output.mkdir(parents=True, exist_ok=False)
    frames = output / 'frames'
    frames.mkdir()
    sheet = Image.new('RGB', (WIDTH * columns // 2, 272 * COUNT), '#20262e')
    events = Image.new('RGB', (WIDTH * columns, 544 * 3), '#20262e')
    for index in range(COUNT):
        row = render_row([sequence[index] for sequence in sequences], labels, index)
        row.save(frames / f'{index:03d}.png')
        sheet.paste(row.resize((WIDTH * columns // 2, 272), Image.Resampling.LANCZOS), (0, index * 272))
        if index in (0, 8, 16):
            events.paste(row, (0, (0, 8, 16).index(index) * 544))
    sheet.save(output / 'all17.png')
    events.save(output / 'local0-8-16.png')
    with Image.open(old / 'inputs' / case.reference / 'reference.png') as image:
        render_row([image.convert('RGB')], ('B027 REFERENCE: unchanged',), None).save(output / 'references.png')
    for label, raw in raw_paths.items():
        shutil.copyfile(raw.with_name('output.mp4'), output / f'{label}-output.mp4')
    video = output / 'comparison-preview24.mp4'
    subprocess.run(['ffmpeg', '-v', 'error', '-framerate', str(FPS), '-i', str(frames / '%03d.png'),
                    '-frames:v', str(COUNT), '-c:v', 'libx264', '-crf', '18', '-pix_fmt', 'yuv420p', str(video)], check=True)
    probe = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-count_frames', '-select_streams', 'v:0',
                    '-show_entries', 'stream=width,height,avg_frame_rate,nb_read_frames', '-of', 'json', str(video)]))
    stream = probe['streams'][0]
    if (stream['width'], stream['height'], stream['avg_frame_rate'], stream['nb_read_frames']) != (WIDTH * columns, 544, '24/1', '17'):
        raise ReviewContractError('Comparison video contract mismatch')
    subprocess.run(['ffmpeg', '-v', 'error', '-i', str(video), '-f', 'null', '-'], check=True)
    manifest = {'case': case.name, 'source_fps': None, 'preview_fps': FPS, 'timebase_assumed': True,
                'temporal': 'UNVERIFIED', 'labels': labels, 'mode': case.mode, 'raw_sha256': {label: digest(path) for label, path in raw_paths.items()},
                'raw_export': 'clone clamp(-1,1), add1 div2, multiply255, uint8; full canvas unchanged',
                'source_sha256': [digest(old / 'inputs/source' / f'{i:03d}.png') for i in range(COUNT)],
                'operations': 'Headers outside canvas. Sheet-only uniform downscale. No alignment/interpolation/warp.',
                'ffprobe': probe, 'outputs': {str(p.relative_to(output)): digest(p) for p in sorted(output.rglob('*')) if p.is_file()}}
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return output


def main() -> None:
    if len(sys.argv) != 6:
        raise ReviewContractError('Usage: compare.py B027_ROOT B029_ROOT TASK R1_or_R2 METHOD_or_CONTROL')
    old, new, task, reference, mode = sys.argv[1:]
    if task not in ('animal', 'human', 'vehicle') or reference not in ('R1', 'R2'):
        raise ReviewContractError('Unexpected fixed-panel case')
    if mode not in ('METHOD', 'CONTROL') or (mode == 'CONTROL' and (task not in ('animal', 'vehicle') or reference != 'R1')):
        raise ReviewContractError('Unexpected fixed-panel mode')
    result = build_case(Case(Path(old), Path(new), task, reference, mode))
    print(result)


if __name__ == '__main__':
    main()
