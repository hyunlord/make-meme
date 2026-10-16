from __future__ import annotations

import httpx
import pytest

from make_meme.sources.fetchers.direct import DirectFetcher
from make_meme.sources.models import SourceError


def test_can_handle_local_file_path(tmp_path):
    fetcher = DirectFetcher()
    assert fetcher.can_handle(str(tmp_path / "anything.mp4"))
    assert fetcher.can_handle("~/some/path.jpg")


def test_can_handle_url_requires_known_extension():
    fetcher = DirectFetcher()
    assert fetcher.can_handle("https://example.com/video.mp4")
    assert fetcher.can_handle("https://example.com/photo.jpeg")
    assert not fetcher.can_handle("https://example.com/watch?v=abc")
    assert not fetcher.can_handle("https://example.com/no-extension")


@pytest.mark.asyncio
async def test_fetch_local_video_file(tmp_path):
    video = tmp_path / "clip.mp4"
    video.write_bytes(b"fake")
    media = await DirectFetcher().fetch(str(video), tmp_path / "dest")
    assert media.kind == "video"
    assert media.provider == "direct"
    assert media.path == video
    assert media.source_url is None


@pytest.mark.asyncio
async def test_fetch_local_missing_file_raises():
    with pytest.raises(SourceError, match="not found"):
        await DirectFetcher().fetch("/nonexistent/path/video.mp4", None)


@pytest.mark.asyncio
async def test_fetch_local_unrecognized_extension_raises(tmp_path):
    weird = tmp_path / "data.xyz"
    weird.write_bytes(b"???")
    with pytest.raises(SourceError, match="unrecognized extension"):
        await DirectFetcher().fetch(str(weird), tmp_path / "dest")


@pytest.mark.asyncio
async def test_fetch_direct_url_downloads(tmp_path, patch_httpx_transport):
    body = b"fake-mp4-bytes"

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("user-agent")
        return httpx.Response(200, content=body, headers={"content-type": "video/mp4"})

    patch_httpx_transport(handler)
    dest_dir = tmp_path / "dest"
    media = await DirectFetcher().fetch("https://example.com/clip.mp4", dest_dir)
    assert media.kind == "video"
    assert media.provider == "direct"
    assert media.path.read_bytes() == body
    assert media.source_url == "https://example.com/clip.mp4"


@pytest.mark.asyncio
async def test_fetch_direct_url_content_type_overrides_extension(tmp_path, patch_httpx_transport):
    # Extension says video, server actually serves an image -- trust the server.
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"img", headers={"content-type": "image/jpeg"})

    patch_httpx_transport(handler)
    media = await DirectFetcher().fetch("https://example.com/thing.mp4", tmp_path / "dest")
    assert media.kind == "image"


@pytest.mark.asyncio
async def test_fetch_direct_url_reuses_existing_cached_file(tmp_path, patch_httpx_transport):
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url)
        return httpx.Response(200, content=b"data", headers={"content-type": "video/mp4"})

    patch_httpx_transport(handler)
    dest_dir = tmp_path / "dest"
    await DirectFetcher().fetch("https://example.com/clip.mp4", dest_dir)
    await DirectFetcher().fetch("https://example.com/clip.mp4", dest_dir)
    assert len(calls) == 1
