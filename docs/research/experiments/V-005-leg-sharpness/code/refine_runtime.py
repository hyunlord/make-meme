"""Isolated R1 adapter: source latent in stage one, official upsample chain in stage two.

Imported only inside the guarded model worker. No upstream file is modified.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
from collections.abc import Iterator
from typing import TYPE_CHECKING

from refine_schedule import Selection, select_schedule

if TYPE_CHECKING:
    from ltx_pipelines.ic_lora import ICLoraPipeline
    from ltx_pipelines.chunks.state import Chunk


def seeded_chunks(chunks: Iterator[Chunk], pipeline: ICLoraPipeline, source: Path) -> Iterator[Chunk]:
    """Encode the fixed source at the first-stage shape without changing conditioning factories."""
    from ltx_pipelines.utils.media_io import decode_video_by_frame, video_preprocess
    from ltx_core.types import VIDEO_SCALE_FACTORS

    count = 0
    for chunk in chunks:
        count += 1
        if count != 1 or chunk.video is None or chunk.layout.start_pixel_frame != 0:
            raise RuntimeError('R1 supports exactly one complete video chunk')
        height = chunk.video.shape[-2] * VIDEO_SCALE_FACTORS.height
        width = chunk.video.shape[-1] * VIDEO_SCALE_FACTORS.width
        frames = decode_video_by_frame(str(source), device=chunk.video.device,
                                       frame_cap=chunk.layout.pixel_frames)
        pixels = video_preprocess(frames, height, width, chunk.video.dtype, chunk.video.device)
        if pixels.shape[2] != chunk.layout.pixel_frames:
            raise RuntimeError('Source frame count does not match first-stage chunk')
        latent = pipeline.image_conditioner(lambda encoder: encoder(pixels))
        del pixels
        if latent.shape != chunk.video.shape:
            raise RuntimeError('Encoded source shape differs from first-stage latent')
        yield replace(chunk, video=latent.to(dtype=chunk.video.dtype))
    if count != 1:
        raise RuntimeError('R1 source encode did not run')


@contextmanager
def refinement(pipeline: ICLoraPipeline, source: Path, requested: float,
               observed: list[Selection]) -> Iterator[None]:
    """Wrap only the official chunk denoise seam; retain its noiser and condition masks."""
    import ltx_pipelines.ic_lora as official

    original = official.denoise_chunks
    stage_count = 0

    def denoise(chunks, stage, sigmas, noiser, fps, **kwargs):
        nonlocal stage_count
        stage_count += 1
        if stage_count > 2:
            raise RuntimeError('Unexpected extra R1 diffusion stage')
        selection = select_schedule(sigmas.detach().cpu().tolist(), requested)
        observed.append(selection)
        selected = sigmas[selection.start_index:]
        if stage_count == 1:
            chunks = seeded_chunks(chunks, pipeline, source)
        return original(chunks, stage, sigmas=selected, noiser=noiser, fps=fps, **kwargs)

    official.denoise_chunks = denoise
    try:
        yield
        if stage_count != 2:
            raise RuntimeError('Both R1 stages must execute')
    finally:
        official.denoise_chunks = original
