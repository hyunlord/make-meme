from __future__ import annotations

from pathlib import Path

import httpx
import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


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


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "network: hits real external services; skipped unless MAKE_MEME_NETWORK_TESTS=1"
    )
