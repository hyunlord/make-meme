# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
# Run through prepare_inputs.py with the existing Pillow/NumPy environment.
"""One recorded isotropic, pixel-center-consistent reference affine."""
from dataclasses import dataclass
from typing import Final
import numpy as np
from PIL import Image

Q: Final = 0.8


@dataclass(frozen=True, slots=True)
class Geometry:
    bbox: tuple[int, int, int, int]
    scale: float
    inverse_affine: tuple[float, float, float, float, float, float]


def normalize(rgb: Image.Image, mask: Image.Image) -> tuple[Image.Image, Image.Image, Geometry]:
    """Map pixel-edge bbox center to canvas center; PIL samples pixel centers."""
    assert rgb.size == mask.size and rgb.mode == 'RGB' and mask.mode == 'L'
    bbox = mask.getbbox()
    assert bbox is not None
    x0, y0, x1, y1 = bbox
    width, height = rgb.size
    scale = min(Q*width/(x1-x0), Q*height/(y1-y0))
    inverse = (1/scale, 0.0, (x0+x1)/2-width/(2*scale),
               0.0, 1/scale, (y0+y1)/2-height/(2*scale))
    warped = rgb.transform(rgb.size, Image.Transform.AFFINE, inverse,
                           Image.Resampling.BICUBIC, fillcolor=(128,128,128))
    support = mask.transform(mask.size, Image.Transform.AFFINE, inverse,
                             Image.Resampling.NEAREST, fillcolor=0)
    array = np.asarray(warped).copy()
    array[np.asarray(support) == 0] = 128
    return Image.fromarray(array), support, Geometry(bbox, scale, inverse)
