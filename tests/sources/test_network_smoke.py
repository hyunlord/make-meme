"""Real network smoke tests -- skipped unless MAKE_MEME_NETWORK_TESTS=1.

Run explicitly with:

    MAKE_MEME_NETWORK_TESTS=1 uv run pytest tests/sources/test_network_smoke.py -v
"""

from __future__ import annotations

import os

import pytest

from make_meme.sources import fetch, search

pytestmark = pytest.mark.skipif(
    not os.environ.get("MAKE_MEME_NETWORK_TESTS"),
    reason="network tests only run with MAKE_MEME_NETWORK_TESTS=1",
)


@pytest.mark.asyncio
@pytest.mark.network
async def test_youtube_search_returns_results():
    results = await search("newjeans", "video", n=5, provider="youtube")
    assert len(results) >= 3
    assert all(r.url.startswith("https://www.youtube.com/watch?v=") for r in results)


@pytest.mark.asyncio
@pytest.mark.network
async def test_openverse_search_returns_licensed_images():
    results = await search("shiba inu", "image", n=5, license_safe=True)
    assert len(results) >= 3
    assert all(r.license for r in results)


@pytest.mark.asyncio
@pytest.mark.network
async def test_fetch_short_public_youtube_video(tmp_path):
    # "Me at the zoo" -- the first video ever uploaded to YouTube, 19s long, always public.
    media = await fetch("https://www.youtube.com/watch?v=jNQXAC9IVRw", tmp_path)
    assert media.kind == "video"
    assert media.path.exists()
    assert media.path.stat().st_size > 0
    assert media.duration and media.duration < 60
