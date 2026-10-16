"""Fetch media by link, or find it by text search.

Public API (used by the rest of make-meme and safe for third parties to
depend on)::

    await fetch(source, dest_dir) -> FetchedMedia
    await search(query, kind, n=8, provider=None, license_safe=False) -> list[Candidate]
    await build_candidate_grid(candidates) -> PIL.Image.Image

Everything else (fetchers, search providers, HTML scraping helpers) is an
implementation detail. Third parties can add their own fetchers/search
providers via the ``make_meme.fetchers``/``make_meme.search_providers``
entry point groups -- see :mod:`.base` -- without needing to import from
this package at all.
"""

from __future__ import annotations

from .base import Fetcher, SearchProvider, get_registry, register_fetcher, register_search_provider
from .dispatcher import fetch
from .fetchers import register_builtin_fetchers
from .grid import build_candidate_grid
from .models import Candidate, FetchedMedia, SourceError
from .search import register_builtin_search_providers
from .search import search as search

register_builtin_fetchers()
register_builtin_search_providers()

__all__ = [
    "Candidate",
    "FetchedMedia",
    "Fetcher",
    "SearchProvider",
    "SourceError",
    "build_candidate_grid",
    "fetch",
    "get_registry",
    "register_fetcher",
    "register_search_provider",
    "search",
]
