"""Plugin architecture: ``Fetcher``/``SearchProvider`` protocols plus a registry.

Built-in fetchers and search providers register themselves at import time
(see ``fetchers/__init__.py`` and ``search/__init__.py``). Third parties can
add their own without touching this package at all, via Python entry points:

.. code-block:: toml

    [project.entry-points."make_meme.fetchers"]
    my_site = "my_package.my_site:MySiteFetcher"

    [project.entry-points."make_meme.search_providers"]
    my_search = "my_package.my_search:MySearchProvider"

Each entry point should resolve to either a class (instantiated with no
arguments) or an already-constructed instance. Discovery happens lazily, the
first time the registry is asked for its fetchers/providers; failures to
import or instantiate a plugin are logged and skipped rather than raised, so
one broken third-party plugin can't take down the whole server.
"""

from __future__ import annotations

import logging
from importlib.metadata import entry_points
from pathlib import Path
from typing import Protocol, runtime_checkable

from .models import Candidate, FetchedMedia

logger = logging.getLogger(__name__)

FETCHER_ENTRY_POINT_GROUP = "make_meme.fetchers"
SEARCH_PROVIDER_ENTRY_POINT_GROUP = "make_meme.search_providers"


@runtime_checkable
class Fetcher(Protocol):
    """A plugin that can turn some class of ``source`` string into local media.

    ``priority`` controls dispatch order: fetchers are tried in ascending
    priority order (lower runs first), and the dispatcher falls through to
    the next matching fetcher if one raises. Built-in priorities: ``direct``
    (local paths / direct media URLs) = 0, ``threads`` = 5, ``ytdlp`` = 10,
    ``generic`` (last-resort og:video/og:image scraping) = 100.
    """

    name: str
    priority: int

    def can_handle(self, source: str) -> bool:
        """Return True if this fetcher should attempt ``source``. Must not do network I/O."""
        ...

    async def fetch(self, source: str, dest_dir: Path) -> FetchedMedia:
        """Resolve ``source`` to a local file under ``dest_dir``, raising ``SourceError`` on failure."""
        ...


@runtime_checkable
class SearchProvider(Protocol):
    """A plugin that can search the web (or a specific service) for media candidates."""

    name: str
    kinds: set[str]
    license_safe: bool
    requires_key: str | None

    async def search(self, query: str, kind: str, n: int) -> list[Candidate]:
        """Return up to ``n`` candidates of ``kind`` ("image" or "video") for ``query``."""
        ...


class Registry:
    """Holds the active fetchers and search providers, newest-registration-wins by name."""

    def __init__(self) -> None:
        self._fetchers: list[Fetcher] = []
        self._search_providers: dict[str, SearchProvider] = {}
        self._discovered = False

    def register_fetcher(self, fetcher: Fetcher) -> None:
        self._fetchers = [f for f in self._fetchers if f.name != fetcher.name]
        self._fetchers.append(fetcher)
        self._fetchers.sort(key=lambda f: f.priority)

    def register_search_provider(self, provider: SearchProvider) -> None:
        self._search_providers[provider.name] = provider

    def fetchers(self) -> list[Fetcher]:
        self.ensure_discovered()
        return list(self._fetchers)

    def search_providers(self) -> dict[str, SearchProvider]:
        self.ensure_discovered()
        return dict(self._search_providers)

    def ensure_discovered(self) -> None:
        """Run entry-point plugin discovery exactly once."""

        if self._discovered:
            return
        self._discovered = True
        _discover_plugins(self)


def _instantiate(loaded: object) -> object:
    return loaded() if isinstance(loaded, type) else loaded


def _select_entry_points(group: str):
    eps = entry_points()
    try:
        return eps.select(group=group)  # Python >= 3.10 / importlib_metadata >= 3.6
    except AttributeError:  # pragma: no cover - only hit on very old importlib.metadata
        return eps.get(group, [])


def _discover_plugins(registry: Registry) -> None:
    try:
        fetcher_eps = list(_select_entry_points(FETCHER_ENTRY_POINT_GROUP))
    except Exception:
        logger.exception("failed to enumerate %s entry points", FETCHER_ENTRY_POINT_GROUP)
        fetcher_eps = []

    for ep in fetcher_eps:
        try:
            registry.register_fetcher(_instantiate(ep.load()))
        except Exception:
            logger.exception("failed to load fetcher plugin %r (%s)", ep.name, ep.value)

    try:
        provider_eps = list(_select_entry_points(SEARCH_PROVIDER_ENTRY_POINT_GROUP))
    except Exception:
        logger.exception("failed to enumerate %s entry points", SEARCH_PROVIDER_ENTRY_POINT_GROUP)
        provider_eps = []

    for ep in provider_eps:
        try:
            registry.register_search_provider(_instantiate(ep.load()))
        except Exception:
            logger.exception("failed to load search provider plugin %r (%s)", ep.name, ep.value)


_registry = Registry()


def get_registry() -> Registry:
    return _registry


def register_fetcher(fetcher: Fetcher) -> None:
    get_registry().register_fetcher(fetcher)


def register_search_provider(provider: SearchProvider) -> None:
    get_registry().register_search_provider(provider)
