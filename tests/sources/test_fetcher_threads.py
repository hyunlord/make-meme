from __future__ import annotations

import httpx
import pytest

from make_meme.sources.fetchers.threads import ThreadsFetcher
from make_meme.sources.models import SourceError


@pytest.mark.parametrize(
    "url",
    [
        "https://www.threads.net/@jane.doe/post/ABC123",
        "https://threads.net/@jane.doe/post/ABC123",
        "https://www.threads.com/@jane.doe/post/ABC123",
        "https://threads.com/@jane.doe/post/ABC123",
    ],
)
def test_can_handle_threads_domains(url):
    assert ThreadsFetcher().can_handle(url) is True


@pytest.mark.parametrize(
    "url",
    [
        "https://www.instagram.com/p/ABC123/",
        "https://example.com/threads.net-but-not-really",
        "/local/path.mp4",
    ],
)
def test_can_handle_rejects_non_threads(url):
    assert ThreadsFetcher().can_handle(url) is False


@pytest.mark.asyncio
async def test_picks_highest_resolution_video_from_json_blob(
    tmp_path, fixtures_dir, patch_httpx_transport
):
    requested_urls = []

    html = (fixtures_dir / "threads_video_json.html").read_text(encoding="utf-8")

    def handler(request: httpx.Request) -> httpx.Response:
        requested_urls.append(str(request.url))
        if "threads.com" in str(request.url):
            return httpx.Response(200, text=html)
        return httpx.Response(200, content=b"video-bytes", headers={"content-type": "video/mp4"})

    patch_httpx_transport(handler)
    media = await ThreadsFetcher().fetch("https://www.threads.com/@jane.doe/post/ABC123", tmp_path)

    assert media.kind == "video"
    assert media.provider == "threads"
    assert any("high.mp4" in u for u in requested_urls)  # the 1080x1920 version, not low/mid
    assert media.title == "Jane Doe (@jane.doe) on Threads"
    assert media.uploader == "jane.doe"
    assert media.path.read_bytes() == b"video-bytes"


@pytest.mark.asyncio
async def test_falls_back_to_og_video_when_no_json_blob(
    tmp_path, fixtures_dir, patch_httpx_transport
):
    requested_urls = []
    html = (fixtures_dir / "threads_og_video.html").read_text(encoding="utf-8")

    def handler(request: httpx.Request) -> httpx.Response:
        requested_urls.append(str(request.url))
        if "threads.com" in str(request.url):
            return httpx.Response(200, text=html)
        return httpx.Response(200, content=b"og-video-bytes", headers={"content-type": "video/mp4"})

    patch_httpx_transport(handler)
    media = await ThreadsFetcher().fetch("https://www.threads.com/@john.smith/post/XYZ", tmp_path)

    assert media.kind == "video"
    assert any("og_fallback_secure.mp4" in u for u in requested_urls)
    assert media.uploader == "john.smith"


@pytest.mark.asyncio
async def test_carousel_image_only_post_returns_image(
    tmp_path, fixtures_dir, patch_httpx_transport
):
    requested_urls = []
    html = (fixtures_dir / "threads_carousel_image.html").read_text(encoding="utf-8")

    def handler(request: httpx.Request) -> httpx.Response:
        requested_urls.append(str(request.url))
        if "threads.com" in str(request.url):
            return httpx.Response(200, text=html)
        return httpx.Response(200, content=b"image-bytes", headers={"content-type": "image/jpeg"})

    patch_httpx_transport(handler)
    media = await ThreadsFetcher().fetch(
        "https://www.threads.com/@alice.pics/post/CAROUSEL", tmp_path
    )

    assert media.kind == "image"
    # Highest-resolution candidate from the first carousel item that has one.
    assert any("carousel_1_large.jpg" in u for u in requested_urls)


@pytest.mark.asyncio
async def test_raises_actionable_error_when_nothing_found(tmp_path, patch_httpx_transport):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="<html><head></head><body>logged out wall</body></html>")

    patch_httpx_transport(handler)
    with pytest.raises(SourceError, match="MAKE_MEME_COOKIES_FILE"):
        await ThreadsFetcher().fetch("https://www.threads.com/@nobody/post/NOPE", tmp_path)


@pytest.mark.asyncio
async def test_raises_when_page_fetch_fails_entirely(tmp_path, patch_httpx_transport):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    patch_httpx_transport(handler)
    with pytest.raises(SourceError):
        await ThreadsFetcher().fetch("https://www.threads.com/@nobody/post/NOPE", tmp_path)
