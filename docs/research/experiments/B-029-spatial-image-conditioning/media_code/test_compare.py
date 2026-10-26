"""Review contracts: unchanged full canvas and complete ordered frame coverage."""
from pathlib import Path

import pytest
from PIL import Image

from compare import ReviewContractError, render_row, source_frames


def test_row_preserves_full_canvas_pixels() -> None:
    # Given full-sized distinct images, when joined, then their pixels are unchanged.
    images = [Image.new('RGB', (896, 512), color) for color in ('red', 'green', 'blue', 'yellow')]
    row = render_row(images, ('SOURCE', 'B027 BASE', 'METHOD', 'CONTROL'), 8)
    for column, image in enumerate(images):
        assert row.crop((896 * column, 32, 896 * (column + 1), 544)).tobytes() == image.tobytes()


def test_missing_source_frame_stops_review(tmp_path: Path) -> None:
    # Given incomplete input, when loaded, then no fabricated frame is substituted.
    with pytest.raises(FileNotFoundError):
        source_frames(tmp_path)


def test_wrong_canvas_stops_review() -> None:
    # Given an inconsistent canvas, when rendered, then no silent resizing occurs.
    with pytest.raises(ReviewContractError):
        render_row([Image.new('RGB', (10, 10))], ('SOURCE',), 0)
