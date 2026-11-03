"""V-001-only FFmpeg replacement for Bernini's small decord CPU reader surface.

Decode every frame once, in presentation order, without resizing, resampling,
or repairing corrupt frames. This deliberately fails on decoding errors instead
of repeating a previous frame. Only the two audited Bernini reader imports use
this module; it is not installed globally as decord.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from io import BytesIO
from math import isfinite
from operator import index
import subprocess
from tempfile import NamedTemporaryFile
from typing import assert_never

import av
import numpy as np
from numpy.typing import NDArray


def _decode_rgb(source: str | BytesIO) -> bytes:
    """Use the installed FFmpeg RGB definition; PyAV only reads metadata."""
    match source:
        case str():
            return subprocess.run(
                ["/usr/bin/ffmpeg", "-nostdin", "-v", "error", "-xerror", "-noautorotate",
                 "-i", source, "-map", "0:v:0", "-fps_mode", "passthrough",
                 "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                capture_output=True, check=True,
            ).stdout
        case BytesIO():
            # A real seekable file also supports MP4 with a trailing moov atom.
            with NamedTemporaryFile(suffix=".video") as temporary:
                temporary.write(source.getvalue())
                temporary.flush()
                return _decode_rgb(temporary.name)
        case unreachable:
            assert_never(unreachable)


def cpu(device_id: int = 0) -> int:
    """Support the sole audited context, decord.cpu(0)."""
    if device_id != 0:
        message = "Only CPU context 0 is supported"
        raise ValueError(message)
    return device_id


@dataclass(frozen=True, slots=True)
class FrameBatch:
    pixels: NDArray[np.uint8]

    def asnumpy(self) -> NDArray[np.uint8]:
        return self.pixels


class VideoReader:
    """Eager reader for a single bounded V-001 clip, accepting path or BytesIO."""

    def __init__(
        self, source: str | BytesIO, num_threads: int = 1,
        ctx: int = 0, fault_tol: int = 1,
    ) -> None:
        if ctx != 0 or num_threads != 1 or fault_tol != 1:
            message = "Unsupported reader options: require CPU0, one thread, fault_tol=1"
            raise ValueError(message)
        with av.open(source, "r") as container:
            if len(container.streams.video) != 1:
                message = "Expected exactly one video stream"
                raise ValueError(message)
            stream = container.streams.video[0]
            rate = stream.average_rate
            if rate is None or not isfinite(float(rate)) or float(rate) <= 0:
                message = "Video average frame rate is unavailable"
                raise ValueError(message)
            self._fps = float(rate)
            width, height = stream.codec_context.width, stream.codec_context.height
        raw = _decode_rgb(source)
        frame_bytes = width * height * 3
        if frame_bytes <= 0 or not raw or len(raw) % frame_bytes:
            message = "Missing or incomplete decoded RGB frames"
            raise ValueError(message)
        self._frames: NDArray[np.uint8] = np.frombuffer(raw, dtype=np.uint8).reshape(-1, height, width, 3)

    def __len__(self) -> int:
        return len(self._frames)

    def get_avg_fps(self) -> float:
        return self._fps

    def seek(self, position: int) -> None:
        """Audited callers seek only to zero; indexed reads have no cursor."""
        if position != 0:
            message = "Only the audited seek(0) operation is supported"
            raise ValueError(message)

    def get_batch(self, indices: Iterable[int]) -> FrameBatch:
        positions = [index(value) for value in indices]
        if any(value < 0 or value >= len(self) for value in positions):
            message = "Frame index outside decoded clip"
            raise IndexError(message)
        return FrameBatch(self._frames[positions])
