"""Async ffmpeg post-processing helpers: concat chunks, mux audio, retime, preview frame.

Unlike ``ingest.py`` (blocking, run via ``asyncio.to_thread``), these are
``async`` directly since they're invoked from within a job's own coroutine,
which is already running on the event loop.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from .ingest import probe

logger = logging.getLogger(__name__)

FFMPEG = "ffmpeg"
AI_GENERATED_COMMENT = "AI-generated with make-meme"


_STDERR_TAIL_LINES = 8


async def _run(cmd: list[str]) -> None:
    logger.debug("running: %s", " ".join(cmd))
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    try:
        _, stderr = await proc.communicate()
    except asyncio.CancelledError:
        proc.kill()
        await proc.wait()
        raise
    if proc.returncode != 0:
        tail = "\n".join(stderr.decode(errors="replace").strip().splitlines()[-_STDERR_TAIL_LINES:])
        raise RuntimeError(f"command failed ({proc.returncode}): {' '.join(cmd)}\nstderr (tail):\n{tail}")


async def concat_videos(paths: list[Path], out: Path, overlap: int = 1) -> Path:
    """Concatenate chunk videos, dropping ``overlap`` leading frames off every chunk after the first."""

    if not paths:
        raise ValueError("concat_videos requires at least one input path")

    inputs: list[str] = []
    for p in paths:
        inputs += ["-i", str(p)]

    filter_parts = []
    labels = []
    for i in range(len(paths)):
        if i == 0 or overlap <= 0:
            filter_parts.append(f"[{i}:v]setpts=PTS-STARTPTS[v{i}]")
        else:
            filter_parts.append(f"[{i}:v]trim=start_frame={overlap},setpts=PTS-STARTPTS[v{i}]")
        labels.append(f"[v{i}]")
    filter_parts.append(f"{''.join(labels)}concat=n={len(paths)}:v=1:a=0[outv]")
    filter_complex = ";".join(filter_parts)

    cmd = [
        FFMPEG, "-y", *inputs,
        "-filter_complex", filter_complex,
        "-map", "[outv]",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        str(out),
    ]
    await _run(cmd)
    return out


async def mux_audio(video: Path, audio: Path, out: Path) -> Path:
    """Mux ``audio`` onto ``video`` (trimmed to the video's duration) and tag it as AI-generated."""

    cmd = [
        FFMPEG, "-y",
        "-i", str(video),
        "-i", str(audio),
        "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "copy", "-c:a", "aac",
        "-shortest",
        "-metadata", f"comment={AI_GENERATED_COMMENT}",
        str(out),
    ]
    await _run(cmd)
    return out


async def retime(video: Path, fps: float, out: Path) -> Path:
    """Retime ``video`` to ``fps`` using motion-compensated interpolation (e.g. 16->30fps)."""

    cmd = [
        FFMPEG, "-y", "-i", str(video),
        "-vf", f"minterpolate=fps={fps}:mi_mode=mci",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        str(out),
    ]
    await _run(cmd)
    return out


async def make_preview(video: Path, out_jpg: Path, at: float = 0.5) -> Path:
    """Grab a preview frame at ``at`` (fraction of total duration, default: midpoint)."""

    info = await asyncio.to_thread(probe, video)
    timestamp = max(0.0, min(info["duration"], info["duration"] * at))
    cmd = [
        FFMPEG, "-y",
        "-i", str(video),
        "-ss", str(timestamp),
        "-vframes", "1", "-q:v", "2",
        str(out_jpg),
    ]
    await _run(cmd)
    return out_jpg
