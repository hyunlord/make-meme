# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "pillow"]
# ///
# Run: existing Python test_prepare_inputs.py
"""Small CPU fixtures for mask polarity, geometry and source preservation."""
import numpy as np
from PIL import Image

from input_geometry import dilate, generation_rgb, condition, vace_geometry, subject_reference


def test_square_radius() -> None:
    mask = np.zeros((61, 61), dtype=bool)
    mask[30, 30] = True
    expanded = dilate(mask, 24)
    assert int(expanded.sum()) == 49 * 49
    assert expanded[6:55, 6:55].all()


def test_rgb_white_not_integer_red() -> None:
    mask = np.array([[False, True]])
    rgb = generation_rgb(mask)
    assert rgb.tolist() == [[[0, 0, 0], [255, 255, 255]]]


def test_outside_source_and_depth_inside() -> None:
    source = np.full((3, 4, 3), 19, dtype=np.uint8)
    mask = np.zeros((3, 4), dtype=bool)
    mask[1, 2] = True
    inside = np.full_like(source, 222)
    result = condition(source, mask, inside)
    assert np.array_equal(result[~mask], source[~mask])
    assert result[mask].tolist() == [[222, 222, 222]]


def test_vace_crop_geometry() -> None:
    canvas = Image.new('L', (1280, 720), 0)
    assert vace_geometry(canvas, nearest=True).size == (832, 480)


def test_white_reference_keeps_subject() -> None:
    rgb = np.full((20, 20, 3), 17, dtype=np.uint8)
    mask = np.zeros((20, 20), dtype=bool)
    mask[4:16, 8:12] = True
    ref, bbox = subject_reference(rgb, mask)
    assert ref.shape == (480, 832, 3)
    assert bbox == [8, 4, 12, 16]
    assert (ref[:, :336] == 255).all()
    assert (ref[:, 336:496] == 17).all()


if __name__ == '__main__':
    tests = [test_square_radius, test_rgb_white_not_integer_red,
             test_outside_source_and_depth_inside, test_vace_crop_geometry,
             test_white_reference_keeps_subject]
    for test in tests:
        test()
    print(f'{len(tests)} CPU input fixture groups PASS')
