# /// script
# requires-python = ">=3.11"
# dependencies = ["pillow", "pydantic", "numpy"]
# ///
"""PIL packs an int fill as a single RGB integer; the VACE mask must be white on every channel."""
from pathlib import Path
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from encode_probe import generation_mask


def test_legacy_int_fill_is_red_not_white() -> None:
    assert Image.new('RGB', (2, 2), 255).getpixel((0, 0)) == (255, 0, 0)
    assert np.asarray(generation_mask(5, 'legacy_int'))[0, 0].tolist() == [255, 0, 0]


def test_white_fill_matches_official_helper_contract() -> None:
    for t in range(33):
        pixels = np.asarray(generation_mask(t, 'white'))
        expected = 0 if t in (0, 32) else 255
        assert pixels.shape == (240, 416, 3) and (pixels == expected).all()


if __name__ == '__main__':
    test_legacy_int_fill_is_red_not_white()
    test_white_fill_matches_official_helper_contract()
    print('PASS')
