# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# Run via C-014 CPU runner using existing research Python; no installs.
"""Endpoint-observed, fixed-envelope RGB compositor; no model or oracle imports.

Reuses B-032's explicit alpha endpoint-copy principle, adapted to RGB uint8
and the preregistered float64/rint contract rather than normalized raw tensors.
"""
from dataclasses import dataclass
from pathlib import Path
import os
import tempfile

import numpy as np
from numpy.typing import NDArray
from PIL import Image

RGB = NDArray[np.uint8]
Mask = NDArray[np.bool_]
Alpha = NDArray[np.float64]
WIDTH, HEIGHT = 416, 240


@dataclass(frozen=True, slots=True)
class ContractError(ValueError):
    reason: str

    def __str__(self) -> str:
        return self.reason


@dataclass(frozen=True, slots=True)
class PlateResult:
    image: RGB
    source_map: NDArray[np.uint8]
    start_valid: Mask
    end_valid: Mask


def validate_rgb(image: RGB) -> None:
    if image.dtype != np.uint8 or image.shape != (HEIGHT, WIDTH, 3):
        raise ContractError('Expected RGB uint8 416x240 without conversion')


def load_rgb(path: Path) -> RGB:
    with Image.open(path) as image:
        if image.format != 'PNG' or image.mode != 'RGB' or image.size != (WIDTH, HEIGHT):
            raise ContractError('Expected lossless PNG RGB 416x240')
        result = np.array(image, dtype=np.uint8)
    validate_rgb(result)
    return result


def distance(center_xy: tuple[float, float]) -> Alpha:
    if len(center_xy) != 2:
        raise ContractError('Expected an (x,y) pixel-index center')
    cx, cy = center_xy
    if not np.isfinite([cx, cy]).all() or not (0 <= cx < WIDTH and 0 <= cy < HEIGHT):
        raise ContractError('Center must be finite and inside pixel-index bounds')
    y, x = np.indices((HEIGHT, WIDTH), dtype=np.float64)
    return np.hypot(x-cx, y-cy)


def plate_from_validity(start: RGB, end: RGB, validity: tuple[Mask, Mask]) -> PlateResult:
    """Same-pixel selector, exposed separately to test an unknown-coverage failure."""
    validate_rgb(start); validate_rgb(end)
    u0, ut = validity
    if any(u.dtype != np.bool_ or u.shape != (HEIGHT, WIDTH) for u in validity):
        raise ContractError('Expected boolean observation masks matching RGB dimensions')
    if not np.all(u0 | ut):
        raise ContractError('PLATE_NOT_ESTABLISHED: unknown pixels remain')
    if not np.array_equal(start[u0 & ut], end[u0 & ut]):
        raise ContractError('PLATE_NOT_ESTABLISHED: common observed background differs')
    source_map = np.where(u0, 1, 2).astype(np.uint8)
    plate = np.where(u0[..., None], start, end).astype(np.uint8)
    return PlateResult(plate, source_map, u0, ut)


def build_plate(start: RGB, end: RGB) -> PlateResult:
    """Only actual endpoint images enter; fixed known centers and 52px exclusion."""
    visible = (distance((104.0, 120.0)) > 52, distance((312.0, 120.0)) > 52)
    return plate_from_validity(start, end, visible)


def alpha(center_xy: tuple[float, float]) -> Alpha:
    d = distance(center_xy)
    result = np.zeros((HEIGHT, WIDTH), dtype=np.float64)
    result[d <= 44] = 1.0
    ring = (d > 44) & (d < 52)
    result[ring] = 0.5 * (1 + np.cos(np.pi * (d[ring]-44)/8))
    return result


def blend(raw: RGB, plate: RGB, edit: Alpha) -> RGB:
    validate_rgb(raw); validate_rgb(plate)
    if edit.dtype != np.float64 or edit.shape != (HEIGHT, WIDTH):
        raise ContractError('Expected full-precision float64 HW alpha')
    if not np.isfinite(edit).all() or np.any((edit < 0) | (edit > 1)):
        raise ContractError('Alpha must be finite within [0,1]')
    mixed = edit[..., None] * raw + (1-edit[..., None]) * plate
    out = np.clip(np.rint(mixed), 0, 255).astype(np.uint8)
    out[edit == 1] = raw[edit == 1]
    out[edit == 0] = plate[edit == 0]
    return out


def save_rgb_new(path: Path, image: RGB) -> RGB:
    """Atomically publish a new PNG, refusing any existing destination; read back."""
    validate_rgb(image)
    if path.exists():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.c014-', suffix='.png', dir=path.parent)
    temp_path = Path(temporary)
    try:
        with os.fdopen(fd, 'wb') as stream:
            Image.fromarray(image).save(stream, format='PNG')
            stream.flush()
            os.fsync(stream.fileno())
        readback = load_rgb(temp_path)
        if not np.array_equal(readback, image):
            raise ContractError('Saved PNG failed exact readback')
        os.link(temp_path, path)
    finally:
        temp_path.unlink()
    return readback
