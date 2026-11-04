# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "pillow"]
# ///
# Run: imported by prepare_inputs.py using the existing research Python.
"""Fixed CPU image geometry; no model or tracking imports."""
from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
from numpy.typing import NDArray
from PIL import Image


def sha256(path: Path) -> str:
    with path.open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def vace_geometry(image: Image.Image, *, nearest: bool = False) -> Image.Image:
    interpolation = Image.Resampling.NEAREST if nearest else Image.Resampling.BILINEAR
    return image.resize((853, 480), interpolation).crop((10, 0, 842, 480))


def ltx_geometry(image: Image.Image) -> Image.Image:
    return image.resize((1152, 648), Image.Resampling.BILINEAR).crop((0, 4, 1152, 644))


def dilate(mask: NDArray[np.bool_], radius: int) -> NDArray[np.bool_]:
    """Chebyshev-radius binary dilation, clipped at image edges; integral sum."""
    assert mask.ndim == 2 and radius >= 0
    padded = np.pad(mask.astype(np.int64), radius)
    integral = np.pad(padded.cumsum(0).cumsum(1), ((1, 0), (1, 0)))
    size = 2 * radius + 1
    count = (integral[size:, size:] - integral[:-size, size:]
             - integral[size:, :-size] + integral[:-size, :-size])
    return count > 0


def generation_rgb(mask: NDArray[np.bool_]) -> NDArray[np.uint8]:
    return np.repeat((mask.astype(np.uint8) * 255)[:, :, None], 3, axis=2)


def condition(source: NDArray[np.uint8], mask: NDArray[np.bool_],
              inside: NDArray[np.uint8]) -> NDArray[np.uint8]:
    assert source.shape == inside.shape and source.shape[:2] == mask.shape
    return np.where(mask[:, :, None], inside, source).astype(np.uint8)


def read_rgb(path: Path) -> NDArray[np.uint8]:
    with Image.open(path) as image:
        return np.asarray(image.convert('RGB')).copy()


def read_mask(path: Path) -> NDArray[np.bool_]:
    with Image.open(path) as image:
        assert image.size == (1280, 720), (path.name, image.size)
        pixels = np.asarray(image.convert('L'))
    assert set(np.unique(pixels).tolist()) <= {0, 255}, path.name
    return pixels > 0


def write_rgb(path: Path, rgb: NDArray[np.uint8]) -> None:
    """Atomic PNG save followed by exact RGB readback."""
    assert rgb.dtype == np.uint8 and rgb.ndim == 3 and rgb.shape[2] == 3
    temporary = path.with_suffix('.partial.png')
    Image.fromarray(rgb).save(temporary)
    assert np.array_equal(read_rgb(temporary), rgb)
    temporary.replace(path)


def subject_reference(rgb: NDArray[np.uint8], mask: NDArray[np.bool_]) -> tuple[NDArray[np.uint8], list[int]]:
    """Tight SAM subject crop, white outside, aspect-fit centered white canvas."""
    ys, xs = np.nonzero(mask)
    assert xs.size > 0
    x0, y0, x1, y1 = int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1
    white = np.full_like(rgb, 255)
    foreground = np.where(mask[:, :, None], rgb, white)[y0:y1, x0:x1]
    scale = min(480 / (y1 - y0), 832 / (x1 - x0))
    width, height = int((x1 - x0) * scale), int((y1 - y0) * scale)
    fitted = Image.fromarray(foreground).resize((width, height), Image.Resampling.BILINEAR)
    canvas = Image.new('RGB', (832, 480), (255, 255, 255))
    canvas.paste(fitted, ((832 - width) // 2, (480 - height) // 2))
    return np.asarray(canvas), [x0, y0, x1, y1]
