from __future__ import annotations

import socket

import httpx
import pytest

from make_meme.sources.models import SourceError
from make_meme.sources.netsafe import (
    is_blocked_address,
    safe_client,
    safe_get,
    safe_stream,
    validate_url,
)

# ---- literal IP addresses -------------------------------------------------


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/",
        "http://127.0.0.1:8188/",  # the local ComfyUI server
        "http://10.0.0.5/",
        "http://172.16.1.1/",
        "http://192.168.1.1/",
        "http://169.254.169.254/latest/meta-data/",  # cloud instance metadata
        "http://100.64.0.1/",  # CGNAT
        "http://0.0.0.0/",
        "http://[::1]/",
        "http://[::ffff:127.0.0.1]/",  # IPv4-mapped loopback
        "http://[::ffff:10.0.0.1]/",  # IPv4-mapped private
        "http://[fc00::1]/",  # IPv6 unique-local
        "http://[fe80::1]/",  # IPv6 link-local
    ],
)
def test_validate_url_rejects_private_ip_literals(url):
    with pytest.raises(SourceError, match="private/local address"):
        validate_url(url)


def test_validate_url_allows_public_ip_literal():
    validate_url("http://93.184.216.34/")  # does not raise


@pytest.mark.parametrize(
    "raw",
    ["127.0.0.1", "10.1.2.3", "169.254.169.254", "::1", "::ffff:127.0.0.1", "fc00::1", "fe80::1"],
)
def test_is_blocked_address_true_for_private(raw):
    import ipaddress

    assert is_blocked_address(ipaddress.ip_address(raw)) is True


@pytest.mark.parametrize("raw", ["8.8.8.8", "1.1.1.1", "93.184.216.34"])
def test_is_blocked_address_false_for_public(raw):
    import ipaddress

    assert is_blocked_address(ipaddress.ip_address(raw)) is False


# ---- scheme validation ------------------------------------------------------


def test_validate_url_rejects_non_http_schemes():
    with pytest.raises(SourceError, match="unsupported URL scheme"):
        validate_url("file:///etc/passwd")
    with pytest.raises(SourceError, match="unsupported URL scheme"):
        validate_url("ftp://example.com/x")


# ---- hostname resolution (monkeypatched DNS) -------------------------------


def test_validate_url_rejects_hostname_resolving_to_private_address(monkeypatch):
    def fake_getaddrinfo(host, *args, **kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("127.0.0.1", 0))]

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)
    with pytest.raises(SourceError, match="private/local address"):
        validate_url("http://evil.example.com/")


def test_validate_url_rejects_if_any_resolved_address_is_private(monkeypatch):
    """A hostname with multiple A/AAAA records is blocked if *any* of them is private."""

    def fake_getaddrinfo(host, *args, **kwargs):
        return [
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.216.34", 0)),
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("127.0.0.1", 0)),
        ]

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)
    with pytest.raises(SourceError, match="private/local address"):
        validate_url("http://multi.example.com/")


def test_validate_url_allows_hostname_resolving_to_public_address(monkeypatch):
    def fake_getaddrinfo(host, *args, **kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.216.34", 0))]

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)
    validate_url("http://public.example.com/")  # does not raise


def test_validate_url_unresolvable_host_raises_source_error(monkeypatch):
    def fake_getaddrinfo(host, *args, **kwargs):
        raise socket.gaierror("Name or service not known")

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)
    with pytest.raises(SourceError, match="Could not resolve"):
        validate_url("http://nonexistent.invalid/")


# ---- env override -----------------------------------------------------------


def test_allow_private_urls_env_override(monkeypatch):
    monkeypatch.setenv("MAKE_MEME_ALLOW_PRIVATE_URLS", "1")
    validate_url("http://127.0.0.1:8188/")  # does not raise


def test_allow_private_urls_env_override_must_be_exactly_1(monkeypatch):
    monkeypatch.setenv("MAKE_MEME_ALLOW_PRIVATE_URLS", "true")
    with pytest.raises(SourceError, match="private/local address"):
        validate_url("http://127.0.0.1/")


# ---- redirect re-validation --------------------------------------------------


@pytest.mark.asyncio
async def test_safe_get_rejects_redirect_from_public_to_private(patch_httpx_transport):
    def handler(request: httpx.Request) -> httpx.Response:
        if "public.example.com" in str(request.url):
            return httpx.Response(302, headers={"location": "http://127.0.0.1:8188/secret"})
        return httpx.Response(200, text="should never get here")

    patch_httpx_transport(handler)
    async with safe_client() as client:
        with pytest.raises(SourceError, match="private/local address"):
            await safe_get(client, "http://public.example.com/start")


@pytest.mark.asyncio
async def test_safe_get_follows_redirect_between_two_public_hosts(patch_httpx_transport):
    def handler(request: httpx.Request) -> httpx.Response:
        if "public.example.com" in str(request.url):
            return httpx.Response(302, headers={"location": "http://other.example.com/final"})
        return httpx.Response(200, text="final content")

    patch_httpx_transport(handler)
    async with safe_client() as client:
        resp = await safe_get(client, "http://public.example.com/start")
    assert resp.text == "final content"


@pytest.mark.asyncio
async def test_safe_get_gives_up_after_too_many_redirects(patch_httpx_transport):
    counter = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        counter["n"] += 1
        return httpx.Response(
            302, headers={"location": f"http://public.example.com/{counter['n']}"}
        )

    patch_httpx_transport(handler)
    async with safe_client() as client:
        with pytest.raises(SourceError, match="Too many redirects"):
            await safe_get(client, "http://public.example.com/0")


@pytest.mark.asyncio
async def test_safe_stream_rejects_redirect_to_private_address(patch_httpx_transport, tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        if "public.example.com" in str(request.url):
            return httpx.Response(
                302, headers={"location": "http://169.254.169.254/latest/meta-data/"}
            )
        return httpx.Response(200, content=b"secret cloud metadata")

    patch_httpx_transport(handler)
    async with safe_client() as client:
        with pytest.raises(SourceError, match="private/local address"):
            async with safe_stream(client, "GET", "http://public.example.com/start") as resp:
                await resp.aread()


@pytest.mark.asyncio
async def test_safe_stream_yields_final_response_after_public_redirect(patch_httpx_transport):
    def handler(request: httpx.Request) -> httpx.Response:
        if "public.example.com" in str(request.url):
            return httpx.Response(302, headers={"location": "http://other.example.com/final"})
        return httpx.Response(200, content=b"the real media bytes")

    patch_httpx_transport(handler)
    async with (
        safe_client() as client,
        safe_stream(client, "GET", "http://public.example.com/start") as resp,
    ):
        body = await resp.aread()
    assert body == b"the real media bytes"


@pytest.mark.asyncio
async def test_safe_client_forces_follow_redirects_false():
    async with safe_client(follow_redirects=True) as client:
        assert client.follow_redirects is False
