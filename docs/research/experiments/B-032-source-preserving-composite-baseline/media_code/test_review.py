# /// script
# requires-python = ">=3.11"
# dependencies = ["pytest", "pillow"]
# ///
"""Run: python -m pytest test_review.py. Small CPU checks only."""
from pathlib import Path

import pytest
from PIL import Image

from build_review import frame, sha256


def test_frame_rejects_wrong_canvas(tmp_path: Path) -> None:
    path = tmp_path / 'tiny.png'
    Image.new('RGB', (20, 20)).save(path)
    with pytest.raises(ValueError, match='Expected896x512'):
        frame(path)


def test_frame_retains_rgb_values(tmp_path: Path) -> None:
    path = tmp_path / 'rgb.png'
    Image.new('RGB', (896, 512), (2, 127, 250)).save(path)
    image = frame(path)
    assert image.size == (896, 512)
    assert image.getpixel((800, 400)) == (2, 127, 250)


def test_digest_reads_actual_bytes(tmp_path: Path) -> None:
    path = tmp_path / 'bytes'
    path.write_bytes(b'abc')
    assert sha256(path) == 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad'
