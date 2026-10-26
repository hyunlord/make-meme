# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
# Run: python -m pytest code/test_normalize.py; use installed environment only.
import numpy as np
from PIL import Image
from normalize import normalize


def test_subject_centers_and_isotropic_scale() -> None:
    rgb = Image.new('RGB', (100, 60), (200, 40, 10))
    mask = Image.new('L', rgb.size)
    mask.paste(255, (10, 10, 30, 30))
    output, support, geometry = normalize(rgb, mask)
    assert geometry.scale == 2.4
    assert support.getbbox() == (26, 6, 74, 54)
    assert output.size == rgb.size


def test_outside_constant_and_mask_labels() -> None:
    rgb = Image.new('RGB', (100, 60), (200, 40, 10))
    mask = Image.new('L', rgb.size)
    mask.paste(255, (20, 10, 80, 50))
    output, support, _ = normalize(rgb, mask)
    selected = np.asarray(support) != 0
    assert set(np.unique(np.asarray(support))) <= {0, 255}
    assert np.all(np.asarray(output)[~selected] == 128)
    assert np.all(np.asarray(output)[selected] == (200, 40, 10))


def test_inputs_immutable_and_identity_pixel_centers() -> None:
    data = np.arange(100*60*3, dtype=np.uint8).reshape(60, 100, 3)
    rgb = Image.fromarray(data)
    mask = Image.new('L', rgb.size)
    mask.paste(255, (10, 6, 90, 54))
    before = rgb.tobytes(), mask.tobytes()
    output, support, geometry = normalize(rgb, mask)
    selected = np.asarray(support) != 0
    assert geometry.scale == 1
    assert np.array_equal(np.asarray(output)[selected], data[selected])
    assert before == (rgb.tobytes(), mask.tobytes())
