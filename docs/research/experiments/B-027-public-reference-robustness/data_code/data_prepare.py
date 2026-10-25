#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "pillow", "pydantic>=2"]
# ///
# How to run: python3 data_prepare.py DAVIS_ROOT FROZEN_SELECTION_JSON OUTPUT_ROOT
# Use existing Python dependencies and ffmpeg only; do not install during B-027.
"""Prepare a fixed public, mask-given panel without changing object geometry."""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Final, Self, TypedDict

import numpy as np
from PIL import Image, ImageDraw
from pydantic import BaseModel, ConfigDict, Field, model_validator

CANVAS: Final = (896, 512)
FPS: Final = 24


class InputContractError(ValueError):
    """The actual source or processed artifact violates the fixed input contract."""


class Task(BaseModel):
    """One preselected source track and two references from one target track."""
    model_config = ConfigDict(frozen=True, extra='allow')
    task_id: str = Field(pattern=r'^[a-zA-Z0-9_-]+$')
    prompt: str = Field(min_length=1)
    source_sequence: str = Field(pattern=r'^[a-zA-Z0-9_-]+$')
    source_track: int = Field(gt=0, lt=255)
    source_frames: tuple[int, ...] = Field(min_length=17, max_length=17)
    target_sequence: str = Field(pattern=r'^[a-zA-Z0-9_-]+$')
    target_track: int = Field(gt=0, lt=255)
    reference_frames: tuple[int, int]

    @model_validator(mode='after')
    def temporal_contract(self) -> Self:
        """Reject frame skipping and self-copy masquerading as a new target."""
        if self.source_frames != tuple(range(self.source_frames[0], self.source_frames[0]+17)):
            raise InputContractError('Source frames must be consecutive.')
        if min(self.source_frames + self.reference_frames) < 0 or self.reference_frames[0] == self.reference_frames[1]:
            raise InputContractError('Frames must be nonnegative and references distinct.')
        if (self.source_sequence, self.source_track) == (self.target_sequence, self.target_track):
            raise InputContractError('Source and target tracks must differ.')
        return self


class Selection(BaseModel):
    """The complete panel, fixed before any generated output is viewed."""
    model_config = ConfigDict(frozen=True, extra='allow')
    tasks: tuple[Task, ...] = Field(min_length=1, max_length=3)


@dataclass(frozen=True, slots=True)
class Geometry:
    source_size: tuple[int, int]
    resized_size: tuple[int, int]
    offset: tuple[int, int]
    canvas: tuple[int, int] = CANVAS
    rgb_resample: str = 'LANCZOS'
    mask_resample: str = 'NEAREST'


class VideoCheck(TypedDict):
    sha256: str
    frame_count: int
    preview_fps: int
    roundtrip_rgb_exact: bool


def sha(path: Path) -> str:
    """Hash one artifact without retaining its contents."""
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def fit_pair(rgb: Image.Image, support: Image.Image) -> tuple[Image.Image, Image.Image, Geometry]:
    """Use the same aspect fit for RGB and binary support, with no crop or warp."""
    if rgb.size != support.size:
        raise InputContractError('RGB and indexed mask dimensions differ.')
    scale = min(CANVAS[0]/rgb.width, CANVAS[1]/rgb.height)
    size = (round(rgb.width*scale), round(rgb.height*scale))
    offset = ((CANVAS[0]-size[0])//2, (CANVAS[1]-size[1])//2)
    image = Image.new('RGB', CANVAS, 'black')
    mask = Image.new('L', CANVAS, 0)
    image.paste(rgb.resize(size, Image.Resampling.LANCZOS), offset)
    mask.paste(support.resize(size, Image.Resampling.NEAREST), offset)
    return image, mask, Geometry(rgb.size, size, offset)


def reference_pair(rgb: Image.Image, support: Image.Image) -> tuple[Image.Image, Image.Image]:
    """Preserve resized subject pixels exactly and neutralize every other pixel."""
    selected = np.asarray(support) != 0
    pixels = np.asarray(rgb)
    neutral = np.full_like(pixels, 128)
    neutral[selected] = pixels[selected]
    semantic = np.zeros_like(pixels)
    semantic[selected] = (255, 0, 0)
    if not selected.any() or not np.array_equal(neutral[selected], pixels[selected]):
        raise InputContractError('Empty support or changed reference subject pixels.')
    return Image.fromarray(neutral), Image.fromarray(semantic)


def encode_verify(frames: list[Image.Image], output: Path) -> VideoCheck:
    """Encode all RGB bytes losslessly and verify the actual decoder output."""
    width, height = frames[0].size
    raw = b''.join(frame.tobytes() for frame in frames)
    command = ['ffmpeg', '-v', 'error', '-n', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
               '-s', f'{width}x{height}', '-r', str(FPS), '-i', 'pipe:0', '-an',
               '-c:v', 'libx264rgb', '-crf', '0', '-preset', 'fast', str(output)]
    subprocess.run(command, input=raw, check=True, timeout=120)
    decoded = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(output), '-f', 'rawvideo',
                              '-pix_fmt', 'rgb24', 'pipe:1'], capture_output=True, check=True, timeout=120).stdout
    if decoded != raw:
        raise InputContractError(f'Lossless RGB roundtrip failed: {output.name}')
    return VideoCheck(sha256=sha(output), frame_count=len(frames), preview_fps=FPS, roundtrip_rgb_exact=True)


def load_frame(dataset: Path, sequence: str, frame: int, track: int, destination: Path) -> tuple[Image.Image, Image.Image, dict[str, str]]:
    """Read actual palette indices, preserve original media, and bind their hashes."""
    rgb_path = dataset/'JPEGImages/480p'/sequence/f'{frame:05d}.jpg'
    mask_path = dataset/'Annotations/480p'/sequence/f'{frame:05d}.png'
    with Image.open(rgb_path) as source, Image.open(mask_path) as mask:
        rgb = source.convert('RGB')
        labels = np.asarray(mask)
        if labels.ndim != 2 or not np.any(labels == track):
            raise InputContractError(f'Track absent or non-indexed mask: {sequence}/{frame}')
        support = Image.fromarray(np.uint8(labels == track)*255)
    destination.mkdir(parents=True, exist_ok=False)
    shutil.copy2(rgb_path, destination/'original.jpg')
    shutil.copy2(mask_path, destination/'instance-mask.png')
    rgb.save(destination/'decoded-rgb.png')
    return rgb, support, {'rgb_sha256': sha(rgb_path), 'indexed_mask_sha256': sha(mask_path)}


def sheet(frames: list[Image.Image], labels: list[str], path: Path, columns: int) -> None:
    """Show the full common canvas at one fixed scale, without subject crops."""
    cell = (448, 280)
    canvas = Image.new('RGB', (columns*cell[0], ((len(frames)+columns-1)//columns)*cell[1]), '#202020')
    draw = ImageDraw.Draw(canvas)
    for index, (frame, label) in enumerate(zip(frames, labels, strict=True)):
        x, y = (index % columns)*cell[0], (index//columns)*cell[1]
        draw.text((x+5, y+4), label, fill='white')
        canvas.paste(frame.resize((448, 256), Image.Resampling.LANCZOS), (x, y+24))
    canvas.save(path)


def prepare_task(dataset: Path, task: Task, output: Path, selection_hash: str) -> None:
    """Produce an immutable task directory and the actual preprocessing evidence."""
    root = output/'tasks'/task.task_id
    inputs = root/'inputs'
    inputs.mkdir(parents=True, exist_ok=False)
    records = []
    frames, masks = [], []
    for local, frame in enumerate(task.source_frames):
        rgb, support, hashes = load_frame(dataset, task.source_sequence, frame, task.source_track, inputs/'original-source'/f'{local:03d}')
        image, mask, geometry = fit_pair(rgb, support)
        selected = np.asarray(mask) != 0
        semantic = np.full((*selected.shape, 3), 255, dtype=np.uint8)
        semantic[selected] = (255, 0, 0)
        frames.append(image)
        masks.append(Image.fromarray(semantic))
        (inputs/'source').mkdir(exist_ok=True)
        (inputs/'source-mask').mkdir(exist_ok=True)
        image.save(inputs/'source'/f'{local:03d}.png')
        masks[-1].save(inputs/'source-mask'/f'{local:03d}.png')
        records.append({'local': local, 'frame': frame, 'hashes': hashes, 'geometry': asdict(geometry), 'support_area': int(selected.sum())})
    refs = []
    reference_images = []
    for reference_id, frame in zip(('R1', 'R2'), task.reference_frames, strict=True):
        folder = inputs/reference_id
        rgb, support, hashes = load_frame(dataset, task.target_sequence, frame, task.target_track, folder/'original')
        fitted, mask, geometry = fit_pair(rgb, support)
        reference, semantic = reference_pair(fitted, mask)
        reference.save(folder/'reference.png')
        semantic.save(folder/'reference-mask.png')
        fitted.save(folder/'resized-before-isolation.png')
        mask.save(folder/'support.png')
        reference_images.append(reference)
        refs.append({'reference_id': reference_id, 'frame': frame, 'sequence': task.target_sequence, 'track': task.target_track,
                     'hashes': hashes, 'geometry': asdict(geometry), 'bbox': mask.getbbox(), 'support_area': int(np.count_nonzero(np.asarray(mask))),
                     'subject_rgb_exact': True, 'outside_rgb_constant': 128, 'reference_sha256': sha(folder/'reference.png'),
                     'reference_mask_sha256': sha(folder/'reference-mask.png')})
    videos = {'driver': encode_verify(frames, inputs/'driver.mp4'), 'driver_mask': encode_verify(masks, inputs/'driver-mask.mp4')}
    sheet(frames, [f'SOURCE local{i} / f{f}' for i, f in enumerate(task.source_frames)], root/'source-all17.jpg', 4)
    sheet(reference_images, [f'R{i+1} / target f{f}' for i, f in enumerate(task.reference_frames)], root/'references.png', 2)
    manifest = {**task.model_dump(mode='json'), 'dataset': 'DAVIS-2017-trainval-480p', 'mask_given': True,
                'source_fps': None, 'preview_fps': FPS, 'timebase_assumed': True, 'native_timing_claimed': False,
                'canvas_wh': list(CANVAS), 'selection_sha256': selection_hash, 'source_records': records,
                'target_refs': refs, 'videos': videos, 'rgb_resample': 'LANCZOS', 'mask_resample': 'NEAREST',
                'source_padding_rgb': [0, 0, 0], 'source_semantic': 'RED selected track / WHITE remainder',
                'reference_semantic': 'RED selected track / BLACK remainder', 'reference_background_rgb': [128, 128, 128]}
    (root/'task_manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')


def main() -> None:
    """Consume a preselected panel without selecting on model outputs."""
    dataset, selection_path, output = map(Path, sys.argv[1:])
    selection = Selection.model_validate_json(selection_path.read_text())
    for task in selection.tasks:
        prepare_task(dataset, task, output, sha(selection_path))


if __name__ == '__main__':
    main()
