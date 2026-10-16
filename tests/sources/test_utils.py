from __future__ import annotations

import httpx
import pytest

from make_meme.sources.models import SourceError
from make_meme.sources.utils import (
    cache_key,
    describe_exception,
    download_to_file,
    extension_from_content_type,
    format_duration,
    guess_extension,
    is_url,
    kind_from_content_type,
    max_download_bytes,
    normalize_source,
    parse_duration_to_seconds,
    strip_vtt,
)


def test_describe_exception_includes_message_when_present():
    assert describe_exception(ValueError("oops")) == "ValueError: oops"


def test_describe_exception_falls_back_to_type_name_when_message_empty():
    # httpx.ReadTimeout and similar often have an empty str() -- never show a bare
    # trailing colon with nothing after it.
    assert describe_exception(httpx.ReadTimeout("")) == "ReadTimeout"
    assert describe_exception(TimeoutError()) == "TimeoutError"


def test_is_url():
    assert is_url("https://example.com/x")
    assert is_url("http://example.com")
    assert not is_url("/local/path.mp4")
    assert not is_url("not a url at all")
    assert not is_url("~/videos/clip.mp4")


def test_cache_key_stable_and_normalizes_whitespace():
    a = cache_key("https://example.com/video")
    b = cache_key("  https://example.com/video  ")
    assert a == b
    assert a != cache_key("https://example.com/other")
    assert len(a) == 40  # sha1 hex digest


def test_normalize_source_strips():
    assert normalize_source("  foo  ") == "foo"


@pytest.mark.parametrize(
    "text,expected",
    [
        ("3:21", 201.0),
        ("1:02:03", 3723.0),
        ("45", 45.0),
        (None, None),
        ("", None),
        ("not a duration", None),
    ],
)
def test_parse_duration_to_seconds(text, expected):
    assert parse_duration_to_seconds(text) == expected


@pytest.mark.parametrize(
    "seconds,expected",
    [
        (None, "?:??"),
        (0, "0:00"),
        (65, "1:05"),
        (3723, "1:02:03"),
    ],
)
def test_format_duration(seconds, expected):
    assert format_duration(seconds) == expected


def test_kind_and_extension_from_content_type():
    assert kind_from_content_type("video/mp4; charset=binary") == "video"
    assert kind_from_content_type("image/jpeg") == "image"
    assert kind_from_content_type("text/html") is None
    assert kind_from_content_type(None) is None
    assert extension_from_content_type("video/mp4") == ".mp4"
    assert extension_from_content_type("image/jpeg") == ".jpg"
    assert extension_from_content_type("application/octet-stream") is None


def test_guess_extension_prefers_url_suffix():
    assert guess_extension("https://example.com/clip.mov", "video") == ".mov"
    assert guess_extension("https://example.com/clip.mov?x=1", "video") == ".mov"
    assert guess_extension("https://example.com/no-extension", "video") == ".mp4"
    assert guess_extension("https://example.com/no-extension", "image") == ".jpg"


def test_strip_vtt_dedupes_rolling_captions():
    vtt = """WEBVTT

00:00:00.000 --> 00:00:02.000
Hello there

00:00:01.000 --> 00:00:03.000
Hello there
general kenobi
"""
    excerpt = strip_vtt(vtt)
    assert excerpt == "Hello there general kenobi"


def test_strip_vtt_strips_inline_tags_and_respects_max_chars():
    vtt = "WEBVTT\n\n00:00:00.000 --> 00:00:01.000\n<c>Hello</c> <00:00:00.500>world\n"
    assert strip_vtt(vtt, max_chars=1000) == "Hello world"
    assert len(strip_vtt("word " * 1000, max_chars=50)) <= 50


def test_max_download_bytes_reads_env(monkeypatch):
    monkeypatch.setenv("MAKE_MEME_MAX_DOWNLOAD_MB", "10")
    assert max_download_bytes() == 10 * 1024 * 1024
    monkeypatch.delenv("MAKE_MEME_MAX_DOWNLOAD_MB", raising=False)
    assert max_download_bytes() == 500 * 1024 * 1024


def test_max_download_bytes_invalid_falls_back(monkeypatch):
    monkeypatch.setenv("MAKE_MEME_MAX_DOWNLOAD_MB", "not-a-number")
    assert max_download_bytes() == 500 * 1024 * 1024


@pytest.mark.asyncio
async def test_download_to_file_success(tmp_path, patch_httpx_transport):
    body = b"fake video bytes"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=body, headers={"content-type": "video/mp4"})

    patch_httpx_transport(handler)
    dest = tmp_path / "out.mp4"
    async with httpx.AsyncClient() as client:
        content_type = await download_to_file(client, "https://example.com/v.mp4", dest)
    assert content_type == "video/mp4"
    assert dest.read_bytes() == body


@pytest.mark.asyncio
async def test_download_to_file_http_error_raises_source_error(tmp_path, patch_httpx_transport):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404)

    patch_httpx_transport(handler)
    dest = tmp_path / "out.mp4"
    async with httpx.AsyncClient() as client:
        with pytest.raises(SourceError):
            await download_to_file(client, "https://example.com/missing.mp4", dest)
    assert not dest.exists()


@pytest.mark.asyncio
async def test_download_to_file_enforces_size_cap(tmp_path, patch_httpx_transport, monkeypatch):
    monkeypatch.setenv("MAKE_MEME_MAX_DOWNLOAD_MB", "0.001")  # ~1KB cap

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"x" * 1_000_000, headers={"content-type": "video/mp4"})

    patch_httpx_transport(handler)
    dest = tmp_path / "out.mp4"
    async with httpx.AsyncClient() as client:
        with pytest.raises(SourceError, match="limit"):
            await download_to_file(client, "https://example.com/big.mp4", dest)
    assert not dest.exists()


@pytest.mark.asyncio
async def test_download_to_file_rejects_declared_content_length_over_cap(
    tmp_path, patch_httpx_transport, monkeypatch
):
    monkeypatch.setenv("MAKE_MEME_MAX_DOWNLOAD_MB", "0.001")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=b"x" * 10,
            headers={"content-type": "video/mp4", "content-length": "5000000"},
        )

    patch_httpx_transport(handler)
    dest = tmp_path / "out.mp4"
    async with httpx.AsyncClient() as client:
        with pytest.raises(SourceError, match="limit"):
            await download_to_file(client, "https://example.com/big.mp4", dest)
    assert not dest.exists()
