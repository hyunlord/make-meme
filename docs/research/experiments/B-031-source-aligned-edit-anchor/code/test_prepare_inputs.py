# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "pillow", "pytest"]
# ///
# Run: python -m pytest test_prepare_inputs.py
from PIL import Image
import numpy as np

from prepare_inputs import crop_target


def test_bbox_margin_and_subject_pixels_are_preserved() -> None:
    # Given: a non-square exact RGB target and indexed instance mask.
    rgb = np.arange(30 * 40 * 3, dtype=np.uint8).reshape(30, 40, 3)
    labels = np.zeros((30, 40), dtype=np.uint8)
    labels[10:20, 10:30] = 1
    # When: the fixed ten-percent-per-side crop is applied.
    result = crop_target(Image.fromarray(rgb), Image.fromarray(labels))
    # Then: original subject pixels survive and all exterior pixels are128.
    assert result.bbox == (10, 10, 30, 20)
    assert result.crop_box == (8, 9, 32, 21)
    actual = np.asarray(result.rgb)
    support = np.asarray(result.support) > 0
    assert np.array_equal(actual[support], rgb[9:21, 8:32][support])
    assert np.all(actual[~support] == 128)
    assert int(support.sum()) == 200


def test_margin_is_clipped_to_native_image_bounds() -> None:
    # Given: a target reaches the top-left image boundary.
    rgb = Image.new("RGB", (20, 20), (1, 2, 3))
    labels = np.zeros((20, 20), dtype=np.uint8)
    labels[:10, :10] = 1
    # When: margin would extend beyond the original image.
    result = crop_target(rgb, Image.fromarray(labels))
    # Then: no invented padding or resize is introduced.
    assert result.crop_box == (0, 0, 11, 11)
    assert result.rgb.size == (11, 11)
