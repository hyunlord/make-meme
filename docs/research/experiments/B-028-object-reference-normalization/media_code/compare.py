# /// script
# requires-python = ">=3.11"
# dependencies = ["pillow", "numpy", "torch"]
# ///
# Run with the existing environment: python compare.py OLD_ROOT NEW_ROOT TASK REF
"""Build one completed B027/B028 case comparison without touching raw artifacts."""
from __future__ import annotations

import hashlib
import html
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

    @property
    def name(self) -> str:
        return f'{self.task}-{self.reference}'


def build_case(case: Case) -> Path:
    old = case.baseline / 'tasks' / case.task
    new = case.current / 'tasks' / case.task
    raw_old = old / 'cases' / case.reference / 'artifacts/raw_output.pt'
    raw_new = new / 'cases' / case.reference / 'artifacts/raw_output.pt'
    source = source_frames(old / 'inputs/source')
    sequences = [source, raw_frames(raw_old), raw_frames(raw_new)]
    output = case.current / 'review' / case.name
    output.mkdir(parents=True, exist_ok=False)
    frames = output / 'frames'
    frames.mkdir()
    sheet = Image.new('RGB', (1344, 272 * COUNT), '#20262e')
    events = Image.new('RGB', (2688, 544 * 3), '#20262e')
    for index in range(COUNT):
        row = render_row([sequence[index] for sequence in sequences], ('SOURCE', 'B027', 'B028'), index)
        row.save(frames / f'{index:03d}.png')
        sheet.paste(row.resize((1344, 272), Image.Resampling.LANCZOS), (0, index * 272))
        if index in (0, 8, 16):
            events.paste(row, (0, (0, 8, 16).index(index) * 544))
    sheet.save(output / 'all17.png')
    events.save(output / 'local0-8-16.png')
    refs = []
    for folder in (old, new):
        with Image.open(folder / 'inputs' / case.reference / 'reference.png') as image:
            refs.append(image.convert('RGB'))
    render_row(refs, ('ORIGINAL REFERENCE', 'NORMALIZED REFERENCE'), None).save(output / 'references.png')
    for label, folder in (('B027', old), ('B028', new)):
        shutil.copyfile(folder / 'cases' / case.reference / 'artifacts/output.mp4', output / f'{label}-output.mp4')
    video = output / 'comparison-preview24.mp4'
    subprocess.run(['ffmpeg', '-v', 'error', '-framerate', str(FPS), '-i', str(frames / '%03d.png'),
                    '-frames:v', str(COUNT), '-c:v', 'libx264', '-crf', '18', '-pix_fmt', 'yuv420p', str(video)], check=True)
    probe = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-count_frames', '-select_streams', 'v:0',
                    '-show_entries', 'stream=width,height,avg_frame_rate,nb_read_frames', '-of', 'json', str(video)]))
    stream = probe['streams'][0]
    if (stream['width'], stream['height'], stream['avg_frame_rate'], stream['nb_read_frames']) != (2688, 544, '24/1', '17'):
        raise ReviewContractError('Comparison video contract mismatch')
    subprocess.run(['ffmpeg', '-v', 'error', '-i', str(video), '-f', 'null', '-'], check=True)
    manifest = {'case': case.name, 'source_fps': None, 'preview_fps': FPS, 'timebase_assumed': True,
                'temporal': 'UNVERIFIED', 'raw_sha256': {'B027': digest(raw_old), 'B028': digest(raw_new)},
                'raw_export': 'clone clamp(-1,1), add1 div2, multiply255, uint8; full canvas unchanged',
                'source_sha256': [digest(old / 'inputs/source' / f'{i:03d}.png') for i in range(COUNT)],
                'operations': 'Headers outside canvas. Sheet-only uniform downscale. No alignment/interpolation/warp.',
                'ffprobe': probe, 'outputs': {str(p.relative_to(output)): digest(p) for p in sorted(output.rglob('*')) if p.is_file()}}
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return output


def refresh_viewer(root: Path) -> None:
    """Expose completed cases only; missing output is never substituted."""
    sections = []
    for folder in sorted(root.iterdir()):
        if not (folder / 'manifest.json').is_file():
            continue
        name = html.escape(folder.name, quote=True)
        sections.append(f'''<section data-task="{name}"><h2>{name}: SOURCE / B027 / B028</h2>
<p>17 frames; preview 24fps; source FPS unknown. Temporal quality UNVERIFIED.</p>
<video controls preload="metadata" src="{name}/comparison-preview24.mp4"></video>
<p>End-to-start replay is a loop boundary, not within-clip motion.</p>
<div><button class="prev" disabled>Previous frame</button> <button class="next">Next frame</button>
<label>Local frame <input type="range" min="0" max="16" value="0"><output>0</output></label></div>
<img class="frame" src="{name}/frames/000.png" alt="Full canvas source and B027 B028 outputs">
<p><a href="{name}/all17.png">All17</a> · <a href="{name}/local0-8-16.png">Local0/8/16</a> · <a href="{name}/manifest.json">Provenance</a></p>
<details><summary>Original / normalized reference</summary><img src="{name}/references.png" alt="References at identical canvas scale"></details></section>''')
    template = Path(__file__).with_name('viewer.html').read_text()
    (root / 'review.html').write_text(template.replace('<!-- TASKS -->', '\n'.join(sections)))


def main() -> None:
    if len(sys.argv) != 5:
        raise ReviewContractError('Usage: compare.py B027_ROOT B028_ROOT TASK R1_or_R2')
    old, new, task, reference = sys.argv[1:]
    if task not in ('animal', 'human', 'vehicle') or reference not in ('R1', 'R2'):
        raise ReviewContractError('Unexpected fixed-panel case')
    result = build_case(Case(Path(old), Path(new), task, reference))
    refresh_viewer(result.parent)
    print(result)


if __name__ == '__main__':
    main()
