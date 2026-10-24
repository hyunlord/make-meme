"""Bounded CPU decoding; hashes all declared RGB24 frames and rejects extra frames."""
import subprocess
from fractions import Fraction
from hashlib import sha256
from pathlib import Path
from typing import ClassVar

from case_schema import Asset, Frozen
from pydantic import BaseModel, ConfigDict, ValidationError


class Stream(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra='ignore')
    width: int
    height: int
    avg_frame_rate: str
    time_base: str


class Frame(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra='ignore')
    best_effort_timestamp_time: str


class Probe(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra='ignore')
    streams: tuple[Stream, ...]
    frames: tuple[Frame, ...]


class MediaReport(Frozen):
    status: str
    file_sha256: str = ''
    frame_sha256: tuple[str, ...] = ()
    width: int = 0
    height: int = 0
    fps: float = 0
    timestamps: tuple[float, ...] = ()
    errors: tuple[str, ...] = ()


def file_hash(path: Path) -> str:
    digest = sha256()
    with path.open('rb') as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def command(args: list[str]) -> str:
    completed = subprocess.run(args, check=True, capture_output=True, text=True, timeout=120)
    if completed.stderr.strip():
        raise ValueError(f'media tool reported an error: {completed.stderr[:1000]}')
    return completed.stdout


def inspect_media(asset: Asset) -> MediaReport:
    try:
        return inspect_existing(asset)
    except (OSError, subprocess.SubprocessError, ValidationError, ValueError,
            ZeroDivisionError) as error:
        return MediaReport(status='FAIL', errors=(f'{type(error).__name__}: {error}',))


def inspect_existing(asset: Asset) -> MediaReport:
    probe = Probe.model_validate_json(command([
        'ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_streams',
        '-show_frames', '-show_entries',
        'stream=width,height,avg_frame_rate,time_base:frame=best_effort_timestamp_time',
        '-of', 'json', str(asset.path),
    ]))
    if len(probe.streams) != 1:
        raise ValueError('expected exactly one selected video stream')
    stream = probe.streams[0]
    if stream.width * stream.height > 4096 * 4096:
        raise ValueError('decoded resolution exceeds bounded inspection limit')
    if len(probe.frames) > 240:
        raise ValueError('more than 240 frames; bounded inspection refused')
    timestamps = tuple(float(frame.best_effort_timestamp_time) for frame in probe.frames)
    fps = float(Fraction(stream.avg_frame_rate)) if asset.kind == 'VIDEO' else asset.fps
    tolerance = float(Fraction(stream.time_base)) / 2 + 1e-6
    errors: list[str] = []
    if (stream.width, stream.height) != (asset.width, asset.height):
        errors.append('DIMENSIONS_MISMATCH')
    if len(timestamps) != asset.frames:
        errors.append('FRAME_COUNT_MISMATCH')
    if asset.kind == 'VIDEO' and abs(fps - asset.fps) > 1e-5:
        errors.append('FPS_MISMATCH')
    if len(timestamps) == asset.frames and any(
        abs(actual - expected) > tolerance
        for actual, expected in zip(timestamps, asset.timestamps, strict=True)
    ):
        errors.append('ENCODED_TIMESTAMPS_MISMATCH')
    if asset.kind == 'VIDEO' and len(timestamps) == asset.frames:
        for t, index in zip(timestamps, asset.frame_indices, strict=True):
            expected_delta = (index - asset.frame_indices[0]) / asset.source_fps
            if abs((t - timestamps[0]) - expected_delta) > tolerance:
                errors.append('SOURCE_TIME_RESAMPLED_OR_MISDECLARED')
                break
    hashed = command([
        'ffmpeg', '-v', 'error', '-i', str(asset.path), '-map', '0:v:0', '-an',
        '-frames:v', str(asset.frames + 1), '-fps_mode', 'passthrough',
        '-pix_fmt', 'rgb24', '-c:v', 'rawvideo', '-f', 'framehash',
        '-hash', 'sha256', '-',
    ])
    hashes = tuple(line.rsplit(',', 1)[1].strip() for line in hashed.splitlines()
                   if line and not line.startswith('#'))
    if len(hashes) != asset.frames:
        errors.append('DECODED_FRAME_COUNT_MISMATCH')
    if any(len(digest) != 64 for digest in hashes):
        raise ValueError('unexpected framehash output')
    return MediaReport(status='FAIL' if errors else 'PASS', file_sha256=file_hash(asset.path),
                       frame_sha256=hashes, width=stream.width, height=stream.height,
                       fps=fps, timestamps=timestamps, errors=tuple(errors))
