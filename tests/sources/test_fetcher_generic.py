from __future__ import annotations

import httpx
import pytest

from make_meme.sources.fetchers.generic import GenericFetcher
from make_meme.sources.models import SourceError


def test_can_handle_any_http_url():
    fetcher = GenericFetcher()
    assert fetcher.can_handle("https://example.com/whatever")
    assert not fetcher.can_handle("/local/path.mp4")


@pytest.mark.asyncio
async def test_resolves_relative_og_video_url(tmp_path, fixtures_dir, patch_httpx_transport):
    html = (fixtures_dir / "generic_og_video.html").read_text(encoding="utf-8")
    requested = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(str(request.url))
        if str(request.url) == "https://example.com/page":
            return httpx.Response(200, text=html, headers={"content-type": "text/html"})
        if str(request.url) == "https://example.com/media/clip.mp4":
            return httpx.Response(
                200, content=b"video-bytes", headers={"content-type": "video/mp4"}
            )
        return httpx.Response(404)

    patch_httpx_transport(handler)
    media = await GenericFetcher().fetch("https://example.com/page", tmp_path)

    assert media.kind == "video"
    assert media.provider == "generic"
    assert media.path.read_bytes() == b"video-bytes"
    assert media.title == "Some Random Video Page"
    assert "https://example.com/media/clip.mp4" in requested


@pytest.mark.asyncio
async def test_direct_content_type_hit_skips_html_parsing(tmp_path, patch_httpx_transport):
    """A URL with no extension that actually serves a video is caught via Content-Type sniffing."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"raw-video", headers={"content-type": "video/webm"})

    patch_httpx_transport(handler)
    media = await GenericFetcher().fetch("https://example.com/no-extension-video", tmp_path)
    assert media.kind == "video"
    assert media.path.suffix == ".webm"
    assert media.path.read_bytes() == b"raw-video"


@pytest.mark.asyncio
async def test_falls_back_to_video_tag_when_no_og_tags(tmp_path, patch_httpx_transport):
    html = (
        '<html><body><video><source src="https://example.com/fallback.mp4"></video></body></html>'
    )

    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == "https://example.com/page2":
            return httpx.Response(200, text=html, headers={"content-type": "text/html"})
        return httpx.Response(200, content=b"vid", headers={"content-type": "video/mp4"})

    patch_httpx_transport(handler)
    media = await GenericFetcher().fetch("https://example.com/page2", tmp_path)
    assert media.kind == "video"


@pytest.mark.asyncio
async def test_falls_back_to_og_image_when_no_video_found(tmp_path, patch_httpx_transport):
    html = (
        '<html><head><meta property="og:image" content="https://example.com/pic.jpg"></head></html>'
    )

    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == "https://example.com/page3":
            return httpx.Response(200, text=html, headers={"content-type": "text/html"})
        return httpx.Response(200, content=b"img", headers={"content-type": "image/jpeg"})

    patch_httpx_transport(handler)
    media = await GenericFetcher().fetch("https://example.com/page3", tmp_path)
    assert media.kind == "image"


@pytest.mark.asyncio
async def test_raises_when_nothing_found(tmp_path, patch_httpx_transport):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            text="<html><body>nothing here</body></html>",
            headers={"content-type": "text/html"},
        )

    patch_httpx_transport(handler)
    with pytest.raises(SourceError, match="Could not find a video or image"):
        await GenericFetcher().fetch("https://example.com/empty", tmp_path)


@pytest.mark.asyncio
async def test_raises_on_http_error_status(tmp_path, patch_httpx_transport):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404)

    patch_httpx_transport(handler)
    with pytest.raises(SourceError, match="404"):
        await GenericFetcher().fetch("https://example.com/missing", tmp_path)
