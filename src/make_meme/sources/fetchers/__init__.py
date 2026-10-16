"""Built-in fetchers, registered in priority order at import time."""

from __future__ import annotations

from ..base import register_fetcher
from .direct import DirectFetcher
from .generic import GenericFetcher
from .threads import ThreadsFetcher
from .ytdlp import YtDlpFetcher

_BUILTIN_FETCHERS = (DirectFetcher(), ThreadsFetcher(), YtDlpFetcher(), GenericFetcher())


def register_builtin_fetchers() -> None:
    for fetcher in _BUILTIN_FETCHERS:
        register_fetcher(fetcher)


__all__ = [
    "DirectFetcher",
    "GenericFetcher",
    "ThreadsFetcher",
    "YtDlpFetcher",
    "register_builtin_fetchers",
]
