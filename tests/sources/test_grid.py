from __future__ import annotations

import pytest
from PIL import Image

from make_meme.sources.grid import (
    CAPTION_HEIGHT,
    COLS,
    IMAGE_CELL,
    PADDING,
    VIDEO_CELL,
    build_candidate_grid,
    format_duration,
)
from make_meme.sources.models import Candidate


def _video_candidate(index, title="A Video", duration=201.0, thumbnail_url=None):
    return Candidate(
        index=index,
        kind="video",
        url=f"https://example.com/{index}",
        provider="x",
        title=title,
        duration=duration,
        thumbnail_url=thumbnail_url,
    )


def _image_candidate(index, title="A Pic", width=800, height=600, thumbnail_url=None):
    return Candidate(
        index=index,
        kind="image",
        url=f"https://example.com/{index}",
        provider="x",
        title=title,
        width=width,
        height=height,
        thumbnail_url=thumbnail_url,
    )


@pytest.mark.asyncio
async def test_empty_candidate_list_returns_placeholder_image():
    img = await build_candidate_grid([])
    assert isinstance(img, Image.Image)
    assert img.width > 0 and img.height > 0


@pytest.mark.asyncio
async def test_grid_dimensions_match_expected_layout_no_network():
    # thumbnail_url=None means _fetch_thumbnail never makes an HTTP call -- fully offline.
    candidates = [_video_candidate(i) for i in range(1, 6)]  # 5 candidates -> 2 rows of 4 cols
    img = await build_candidate_grid(candidates)

    cell_w = max(VIDEO_CELL[0], IMAGE_CELL[0])
    cell_h = max(VIDEO_CELL[1], IMAGE_CELL[1]) + CAPTION_HEIGHT
    rows = 2
    expected_w = COLS * cell_w + (COLS + 1) * PADDING
    expected_h = rows * cell_h + (rows + 1) * PADDING

    assert img.size == (expected_w, expected_h)


@pytest.mark.asyncio
async def test_grid_handles_mixed_kinds_with_placeholders():
    candidates = [_video_candidate(1), _image_candidate(2), _video_candidate(3, thumbnail_url=None)]
    img = await build_candidate_grid(candidates)
    assert isinstance(img, Image.Image)
    assert img.mode == "RGB"


@pytest.mark.asyncio
async def test_grid_respects_max_width_cap():
    candidates = [
        _video_candidate(i) for i in range(1, 41)
    ]  # enough rows to exceed MAX_GRID_WIDTH if uncapped width grew
    img = await build_candidate_grid(candidates)
    from make_meme.sources.grid import MAX_GRID_WIDTH

    assert img.width <= MAX_GRID_WIDTH


def test_caption_includes_duration_and_truncated_title():
    from make_meme.sources.grid import _caption_for

    c = _video_candidate(1, title="A" * 50, duration=65)
    caption = _caption_for(c)
    assert caption.startswith(format_duration(65))
    assert "..." in caption
    assert len(caption) < 50


def test_caption_includes_dimensions_for_image():
    from make_meme.sources.grid import _caption_for

    c = _image_candidate(1, title="pic", width=800, height=600)
    assert _caption_for(c) == "800x600 pic"
