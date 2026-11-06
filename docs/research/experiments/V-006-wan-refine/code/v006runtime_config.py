# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# Run with the existing research Python; no installation or model import.
"""Validated private runtime contract and CPU-only W1 admission checks."""
from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path

from PIL import Image
from pydantic import BaseModel, ConfigDict, Field


class Runtime(BaseModel):
    """All values are supplied by the resolved scene and frozen runtime config."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    run_id: str
    upstream: Path
    source_hashes: dict[str, str]
    checkpoint_paths: tuple[Path, ...]
    text_encoder: Path
    vae: Path
    tokenizer: Path
    input_paths: tuple[Path, ...]
    input_pixel_hashes: tuple[str, ...]
    output: Path
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    frames: int = Field(gt=0)
    fps: int = Field(gt=0)
    seed: int
    strength: float = Field(gt=0, le=1)
    steps: int = Field(gt=0)
    sigma_shift: float = Field(gt=0)
    guidance: float = Field(gt=0)
    boundary: float = Field(gt=0, le=1)
    expected_sigma: float = Field(gt=0, le=1)
    sigma_tolerance: float = Field(gt=0)
    prompt: str
    negative_prompt: str
    vram_limit_gib: float = Field(gt=0)
    maximum_seconds: float = Field(gt=0)
    tile_size: tuple[int, int]
    tile_stride: tuple[int, int]
    ffmpeg: Path


def sha256_file(path: Path) -> str:
    """Hash a file without materializing weights in memory."""
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def sigma_start(runtime: Runtime) -> float:
    """Compute the official DiffSynth pre-shift strength mapping."""
    return runtime.sigma_shift * runtime.strength / (
        1 + (runtime.sigma_shift - 1) * runtime.strength
    )


def projected_seconds(elapsed_before_step: float, first_step: float, steps: int) -> float:
    """Include existing setup time in the first-step extrapolation."""
    assert elapsed_before_step >= 0 and first_step >= 0 and steps > 0
    return elapsed_before_step + first_step * steps


def check_contract(runtime: Runtime) -> list[Image.Image]:
    """Reject missing, altered, non-bf16 or incompatible inputs before loading."""
    assert runtime.width % 16 == runtime.height % 16 == 0
    assert runtime.frames % 4 == 1
    assert len(runtime.input_paths) == len(runtime.input_pixel_hashes) == runtime.frames
    assert abs(sigma_start(runtime) - runtime.expected_sigma) <= runtime.sigma_tolerance
    assert sigma_start(runtime) < runtime.boundary
    assert runtime.checkpoint_paths
    assert runtime.output.is_absolute() and not runtime.output.exists()
    paths = (*runtime.checkpoint_paths, runtime.text_encoder, runtime.vae,
             runtime.tokenizer, runtime.ffmpeg, *runtime.input_paths)
    assert all(path.is_absolute() and path.exists() for path in paths)
    for relative, expected in runtime.source_hashes.items():
        assert sha256_file(runtime.upstream / relative) == expected, relative
    for path in runtime.checkpoint_paths:
        with path.open("rb") as stream:
            size = struct.unpack("<Q", stream.read(8))[0]
            header = json.loads(stream.read(size))
        tensors = [row for name, row in header.items() if name != "__metadata__"]
        assert tensors and all(row["dtype"] == "BF16" for row in tensors), path.name
    images = []
    for path, expected in zip(runtime.input_paths, runtime.input_pixel_hashes, strict=True):
        with Image.open(path) as image:
            assert image.mode == "RGB" and image.size == (runtime.width, runtime.height)
            assert hashlib.sha256(image.tobytes()).hexdigest() == expected, path.name
            images.append(image.copy())
    return images
