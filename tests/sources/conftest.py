from __future__ import annotations

import os
import socket
from pathlib import Path

import httpx
import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"
FAKE_PUBLIC_IP = "93.184.216.34"  # a real, non-private address (example.com); used as a stand-in


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES_DIR


def read_fixture(name: str) -> str:
    return (FIXTURES_DIR / name).read_text(encoding="utf-8")


@pytest.fixture
def patch_httpx_transport(monkeypatch):
    """Force every ``httpx.AsyncClient()`` built during the test through a MockTransport.

    Returns a function ``apply(handler)`` where ``handler(request) -> httpx.Response``
    (same signature as ``httpx.MockTransport``). No real network I/O happens.
    """

    def apply(handler):
        transport = httpx.MockTransport(handler)
        original_init = httpx.AsyncClient.__init__

        def patched_init(self, *args, **kwargs):
            kwargs.setdefault("transport", transport)
            original_init(self, *args, **kwargs)

        monkeypatch.setattr(httpx.AsyncClient, "__init__", patched_init)
        return transport

    return apply


@pytest.fixture(autouse=True)
def _fake_dns_for_offline_tests(monkeypatch):
    """Make hostname resolution deterministic and offline for every test by default.

    ``netsafe.validate_url()`` resolves hostnames via ``socket.getaddrinfo`` to check
    for SSRF against private/local addresses, which would otherwise mean every fetcher
    test (using made-up hostnames like "example.com", "threads.com", etc. against a
    MockTransport) does a real DNS lookup. This fakes resolution to a fixed public IP
    so those tests stay offline; tests of the SSRF check itself override this with
    their own ``monkeypatch.setattr(socket, "getaddrinfo", ...)`` to simulate a
    hostname resolving to a private address. Skipped for real network tests
    (MAKE_MEME_NETWORK_TESTS=1), which need real DNS.
    """

    if os.environ.get("MAKE_MEME_NETWORK_TESTS"):
        return

    def fake_getaddrinfo(host, *args, **kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", (FAKE_PUBLIC_IP, 0))]

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "network: hits real external services; skipped unless MAKE_MEME_NETWORK_TESTS=1"
    )
