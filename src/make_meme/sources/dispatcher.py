"""``fetch()`` dispatch: tries registered fetchers in priority order, with sidecar-file caching."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from pathlib import Path

from .base import get_registry
from .models import FetchedMedia, SourceError
from .utils import cache_key

logger = logging.getLogger(__name__)


def _sidecar_path(dest_dir: Path, source: str) -> Path:
    return dest_dir / f"{cache_key(source)}.json"


def _load_cached(dest_dir: Path, source: str) -> FetchedMedia | None:
    sidecar = _sidecar_path(dest_dir, source)
    if not sidecar.exists():
        return None
    try:
        data = json.loads(sidecar.read_text())
        media = FetchedMedia(**{**data, "path": Path(data["path"])})
    except (OSError, ValueError, TypeError, KeyError):
        logger.warning("ignoring unreadable/malformed cache sidecar %s", sidecar, exc_info=True)
        return None
    if not media.path.exists():
        return None
    return media


def _save_cache(dest_dir: Path, source: str, media: FetchedMedia) -> None:
    sidecar = _sidecar_path(dest_dir, source)
    data = asdict(media)
    data["path"] = str(media.path)
    try:
        sidecar.write_text(json.dumps(data, indent=2))
    except OSError:
        logger.warning("failed to write cache sidecar %s", sidecar, exc_info=True)


async def fetch(source: str, dest_dir: Path) -> FetchedMedia:
    """Resolve ``source`` (a URL or local file path) to a :class:`FetchedMedia`.

    Tries each registered :class:`~make_meme.sources.base.Fetcher` whose
    ``can_handle(source)`` is true, in ascending ``priority`` order, falling
    through to the next on failure. If every matching fetcher fails, raises
    :class:`SourceError` aggregating their reasons.

    Successful downloads are cached under ``dest_dir``, keyed by a hash of
    the normalized source: a second call with the same ``source`` and
    ``dest_dir`` returns the cached :class:`FetchedMedia` without any network
    access, as long as the underlying file still exists.
    """

    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)

    cached = _load_cached(dest_dir, source)
    if cached is not None:
        logger.debug("cache hit for %r -> %s", source, cached.path)
        return cached

    registry = get_registry()
    candidates = []
    for fetcher in registry.fetchers():
        try:
            handles = fetcher.can_handle(source)
        except Exception:
            logger.exception("fetcher %s.can_handle() raised for %r", fetcher.name, source)
            continue
        if handles:
            candidates.append(fetcher)

    if not candidates:
        raise SourceError(
            f"Don't know how to fetch {source!r}. Expected a local file path, a direct media URL, "
            "or a link to a supported site (YouTube, TikTok, Instagram, Threads, X/Twitter, Reddit, "
            "Facebook, Bilibili, or a page with og:video/og:image tags)."
        )

    errors: list[str] = []
    for fetcher in candidates:
        try:
            media = await fetcher.fetch(source, dest_dir)
        except SourceError as e:
            errors.append(f"{fetcher.name}: {e}")
            continue
        except Exception as e:
            logger.exception("fetcher %s raised unexpectedly for %r", fetcher.name, source)
            errors.append(f"{fetcher.name}: unexpected error: {e}")
            continue
        _save_cache(dest_dir, source, media)
        return media

    raise SourceError(
        f"Could not fetch media from {source!r}:\n" + "\n".join(f"- {e}" for e in errors)
    )
