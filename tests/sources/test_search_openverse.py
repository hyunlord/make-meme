from __future__ import annotations

import json

import httpx
import pytest

from make_meme.sources.models import SourceError
from make_meme.sources.search.openverse import (
    REQUEST_TIMEOUT,
    OpenverseSearchProvider,
    parse_openverse_response,
)


def test_parse_openverse_response_from_fixture(fixtures_dir):
    data = json.loads((fixtures_dir / "openverse_response.json").read_text())
    candidates = parse_openverse_response(data)

    assert len(candidates) == 3
    first = candidates[0]
    assert first.kind == "image"
    assert first.url == "https://live.staticflickr.com/7165/6556553517_a6cf8d416c_b.jpg"
    assert first.thumbnail_url.endswith("/thumb/")
    assert first.width == 1024
    assert first.height == 768
    assert first.source_page == "https://www.flickr.com/photos/76758469@N00/6556553517"
    assert first.license == "CC BY 2.0 (Yuya Tamai)"
    assert [c.index for c in candidates] == [1, 2, 3]


def test_parse_openverse_response_skips_entries_without_url():
    data = {
        "results": [{"title": "no url"}, {"url": "https://example.com/x.jpg", "license": "by-sa"}]
    }
    candidates = parse_openverse_response(data)
    assert len(candidates) == 1
    assert candidates[0].license == "CC BY-SA"


def test_parse_openverse_response_unknown_license():
    data = {"results": [{"url": "https://example.com/x.jpg"}]}
    candidates = parse_openverse_response(data)
    assert candidates[0].license == "unknown -- check source"


@pytest.mark.asyncio
async def test_search_rejects_video_kind():
    provider = OpenverseSearchProvider()
    assert await provider.search("x", "video", 5) == []


@pytest.mark.asyncio
async def test_search_wraps_http_errors(patch_httpx_transport):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    patch_httpx_transport(handler)
    provider = OpenverseSearchProvider()
    with pytest.raises(SourceError):
        await provider.search("shiba inu", "image", 5)


def test_request_timeout_is_generous():
    # Regression: the real API has been observed taking ~16.5s to respond, which a
    # 15s-wide timeout turned into a ReadTimeout (and an empty, useless error message).
    assert REQUEST_TIMEOUT.read == 40.0
    assert REQUEST_TIMEOUT.connect == 10.0


@pytest.mark.asyncio
async def test_timeout_error_message_includes_exception_type_not_empty(patch_httpx_transport):
    # Regression: httpx.ReadTimeout's str() is often empty, which used to produce
    # "Openverse search failed: " with nothing useful after the colon.
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("")

    patch_httpx_transport(handler)
    provider = OpenverseSearchProvider()
    with pytest.raises(SourceError, match="ReadTimeout"):
        await provider.search("shiba inu", "image", 5)


@pytest.mark.asyncio
async def test_search_parses_live_response_shape(patch_httpx_transport, fixtures_dir):
    data = json.loads((fixtures_dir / "openverse_response.json").read_text())

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=data)

    patch_httpx_transport(handler)
    provider = OpenverseSearchProvider()
    results = await provider.search("shiba inu", "image", 3)
    assert len(results) == 3
    assert all(c.provider == "openverse" for c in results)
