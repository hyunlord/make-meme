"""CPU contracts only; fixture output is not a model generation result."""
from pathlib import Path

import numpy as np
import pytest
import torch

from build_review import inputs, raw_pixels, write_viewer


def test_exact_normalization_and_input_preserved() -> None:
    raw = torch.zeros(3, 17, 512, 896, dtype=torch.bfloat16)
    raw[0, 0, 0, :5] = torch.tensor([-2, -1, 0, 1, 2])
    old = raw.clone()
    pixels = raw_pixels(raw)
    assert pixels.shape == (17, 512, 896, 3)
    assert pixels.dtype == np.uint8
    assert pixels[0, 0, :5, 0].tolist() == [0, 0, 127, 255, 255]
    assert torch.equal(raw, old)


def test_missing_actual_output_rejected(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        inputs(tmp_path)


def test_wrong_shape_and_nonfinite_rejected() -> None:
    with pytest.raises(ValueError):
        raw_pixels(torch.zeros(3, 1, 2, 2))
    value = torch.zeros(3, 17, 512, 896)
    value[0, 0, 0, 0] = float('nan')
    with pytest.raises(ValueError):
        raw_pixels(value)


def test_viewer_contract(tmp_path: Path) -> None:
    write_viewer(tmp_path, ['animal'])
    content = (tmp_path / 'review.html').read_text()
    assert '<video controls preload="metadata"' in content
    assert '<video autoplay' not in content
    assert ' loop' not in content.split('<video')[1].split('>')[0]
    assert 'A=R1, B=R2' in content
    assert 'Native FPS unknown' in content
    assert 'max="16"' in content
