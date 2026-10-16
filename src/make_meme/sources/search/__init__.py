"""``search()`` dispatch: picks default providers per kind, merges, dedupes, and re-numbers.

Default provider choice:

- ``kind="video"``: try ``youtube`` first, then ``web``, to fill up to ``n``
  (deduped by URL).
- ``kind="image"``: ``openverse`` only when ``license_safe=True``; otherwise
  ``web`` first, falling back to (and topping up from) ``openverse`` if
  ``web`` errors, rate-limits, or doesn't return enough results.

Pass ``provider=`` to force a single named provider instead.
"""

from __future__ import annotations

import logging
import os

from ..base import SearchProvider, get_registry, register_search_provider
from ..models import Candidate, SourceError
from ..utils import describe_exception
from .ddgs_search import WebSearchProvider
from .openverse import OpenverseSearchProvider
from .ytdlp_search import YouTubeSearchProvider

logger = logging.getLogger(__name__)

_BUILTIN_PROVIDERS = (YouTubeSearchProvider(), WebSearchProvider(), OpenverseSearchProvider())


def register_builtin_search_providers() -> None:
    for provider in _BUILTIN_PROVIDERS:
        register_search_provider(provider)


def _default_provider_names(kind: str, license_safe: bool) -> list[str]:
    if kind == "video":
        return ["youtube", "web"]
    if license_safe:
        return ["openverse"]
    return ["web", "openverse"]


def _shorten_query(query: str) -> str | None:
    """Drop the last word of ``query``, or return None if it's already a single word.

    Some providers (Openverse in particular) return zero results for long,
    descriptive queries ("shiba inu dog standing full body") that would
    match fine as a shorter phrase ("shiba inu dog").
    """

    words = query.split()
    if len(words) <= 1:
        return None
    return " ".join(words[:-1])


async def _search_with_shortening(
    prov: SearchProvider, query: str, kind: str, n: int
) -> tuple[list[Candidate], str]:
    """Call ``prov.search()``, retrying with a progressively shorter query on zero results.

    A real failure (the provider raises) propagates immediately -- a shorter query
    wouldn't fix a rate limit or network error. Only a *successful* empty result
    triggers a retry, dropping one word at a time until something comes back or
    there's nothing left to drop. Returns the results plus whichever query actually
    produced them, so the caller can log when a fallback query was used.
    """

    attempt_query = query
    results: list[Candidate] = []
    while True:
        results = await prov.search(attempt_query, kind, n)
        if results:
            return results, attempt_query
        shortened = _shorten_query(attempt_query)
        if shortened is None:
            return results, attempt_query
        attempt_query = shortened


async def search(
    query: str,
    kind: str,
    n: int = 8,
    provider: str | None = None,
    license_safe: bool = False,
) -> list[Candidate]:
    if kind not in ("image", "video"):
        raise SourceError(f"Unsupported search kind {kind!r}; expected 'image' or 'video'.")
    if n <= 0:
        return []

    registry = get_registry()
    providers = registry.search_providers()

    if provider:
        chosen = providers.get(provider)
        if chosen is None:
            raise SourceError(
                f"Unknown search provider {provider!r}. Available: {', '.join(sorted(providers)) or 'none'}."
            )
        if kind not in chosen.kinds:
            raise SourceError(f"Provider {provider!r} does not support {kind!r} search.")
        names = [provider]
    else:
        names = [name for name in _default_provider_names(kind, license_safe) if name in providers]
        if not names:
            raise SourceError(f"No search provider registered for kind {kind!r}.")

    collected: list[Candidate] = []
    seen_urls: set[str] = set()
    errors: list[str] = []

    for name in names:
        if len(collected) >= n:
            break
        prov = providers[name]
        if prov.requires_key and not os.environ.get(prov.requires_key):
            errors.append(f"{name}: requires {prov.requires_key} to be set")
            continue
        try:
            results, used_query = await _search_with_shortening(
                prov, query, kind, n - len(collected)
            )
        except SourceError as e:
            errors.append(f"{name}: {e}")
            continue
        except Exception as e:
            logger.exception("search provider %s raised unexpectedly", name)
            errors.append(f"{name}: unexpected error: {describe_exception(e)}")
            continue
        if used_query != query:
            logger.info(
                "provider %s returned 0 results for %r; used shortened query %r instead",
                name,
                query,
                used_query,
            )
        for c in results:
            if c.url in seen_urls:
                continue
            seen_urls.add(c.url)
            collected.append(c)
            if len(collected) >= n:
                break

    if not collected:
        hint = "; ".join(errors) if errors else "no results, even after trying shorter queries"
        raise SourceError(
            f"Search for {query!r} ({kind}) returned nothing ({hint}). "
            "Try a shorter or less specific query."
        )

    for i, c in enumerate(collected, start=1):
        c.index = i
    return collected[:n]


__all__ = ["register_builtin_search_providers", "search"]
