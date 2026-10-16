"""Pure functions for planning Wan-model-compatible video chunks.

Wan2.x models require each generated chunk's frame count to be of the form
``4n+1``. A long clip is generated in overlapping chunks, each conditioned on
the previous chunk's last frame(s), then stitched back together (see
``post.concat_videos``).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Chunk:
    start: int  # inclusive frame index into the source
    end: int  # exclusive frame index into the source
    pad: int = 0  # frames to pad (by repeating the last available frame) to reach a 4n+1 length


def _round_up_to_4n_plus_1(length: int) -> int:
    """Round ``length`` up to the nearest value of the form ``4n+1`` (n >= 0), minimum 1."""

    if length <= 1:
        return 1
    n = -(-(length - 1) // 4)  # ceil((length - 1) / 4)
    return 4 * n + 1


def plan_chunks(total_frames: int, chunk_len: int = 81, overlap: int = 1) -> list[Chunk]:
    """Plan overlapping chunks covering ``total_frames``, each of length ``4n+1``.

    ``chunk_len`` must itself satisfy ``4n+1``. Chunks advance by
    ``chunk_len - overlap`` frames, so consecutive chunks share ``overlap``
    frames (for conditioning continuity). The final chunk may be shorter than
    ``chunk_len`` but is still rounded up to the nearest ``4n+1`` length;
    ``pad`` reports how many frames beyond ``total_frames`` it needs -- the
    caller pads by repeating the last available frame that many times.
    """

    if total_frames <= 0:
        return []
    if chunk_len < 5 or (chunk_len - 1) % 4 != 0:
        raise ValueError(f"chunk_len must satisfy 4n+1 (n>=1), got {chunk_len}")
    if overlap < 0 or overlap >= chunk_len:
        raise ValueError(f"overlap must be in [0, chunk_len), got {overlap}")

    step = chunk_len - overlap
    chunks: list[Chunk] = []
    start = 0
    while start < total_frames:
        remaining = total_frames - start
        if remaining >= chunk_len:
            chunks.append(Chunk(start=start, end=start + chunk_len, pad=0))
        else:
            needed_len = _round_up_to_4n_plus_1(remaining)
            chunks.append(Chunk(start=start, end=total_frames, pad=needed_len - remaining))
            break
        start += step
    return chunks


def estimate_seconds(
    frames: int,
    quality: str,
    seconds_per_chunk: float,
    chunk_len: int = 81,
    overlap: int = 1,
) -> float:
    """Rough wall-clock estimate: number of chunks * seconds_per_chunk, scaled by quality."""

    chunks = plan_chunks(frames, chunk_len=chunk_len, overlap=overlap)
    num_chunks = len(chunks) or 1
    quality_multiplier = {"draft": 1.0, "high": 2.2}.get(quality, 1.0)
    return num_chunks * seconds_per_chunk * quality_multiplier
