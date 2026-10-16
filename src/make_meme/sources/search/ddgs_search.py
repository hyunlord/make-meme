"""Web image/video search via the ``ddgs`` package.

``ddgs`` (https://github.com/deedy5/ddgs, MIT licensed, verified against
version 9.16.0) aggregates results from Bing/DuckDuckGo-backed engines with
no API key. Field names below (``image``, ``content``, ``duration`` as
"M:SS", nested ``images`` dict, etc.) come from a live call to
``DDGS().images()``/``DDGS().videos()`` made while building this provider;
``ddgs`` does not publish a formal response schema.
"""

from __future__ import annotations

import asyncio
import logging
from typing import ClassVar

from ..models import Candidate, SourceError
from ..utils import describe_exception, parse_duration_to_seconds

logger = logging.getLogger(__name__)


class WebSearchProvider:
    name = "web"
    kinds: ClassVar[set[str]] = {"image", "video"}
    license_safe = False
    requires_key = None

    async def search(self, query: str, kind: str, n: int) -> list[Candidate]:
        if kind not in self.kinds or n <= 0:
            return []
        return await asyncio.to_thread(self._search_sync, query, kind, n)

    def _search_sync(self, query: str, kind: str, n: int) -> list[Candidate]:
        try:
            from ddgs import DDGS
            from ddgs.exceptions import DDGSException
        except ImportError as e:
            raise SourceError(
                "The 'ddgs' package is required for web search but is not installed."
            ) from e

        try:
            with DDGS() as ddgs:
                if kind == "image":
                    results = ddgs.images(query, max_results=n, safesearch="moderate")
                else:
                    results = ddgs.videos(query, max_results=n, safesearch="moderate")
        except DDGSException as e:
            raise SourceError(f"Web search failed: {describe_exception(e)}") from e
        except Exception as e:
            raise SourceError(f"Web search failed unexpectedly: {describe_exception(e)}") from e

        if kind == "image":
            return _image_candidates(results, self.name)
        return _video_candidates(results, self.name)


def _to_int(value: object) -> int | None:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _image_candidates(results: list[dict], provider: str) -> list[Candidate]:
    candidates: list[Candidate] = []
    for i, r in enumerate(results, start=1):
        url = r.get("image")
        if not url:
            continue
        candidates.append(
            Candidate(
                index=i,
                kind="image",
                url=url,
                provider=provider,
                title=r.get("title"),
                thumbnail_url=r.get("thumbnail"),
                width=_to_int(r.get("width")),
                height=_to_int(r.get("height")),
                license="unknown -- check source",
                source_page=r.get("url"),
            )
        )
    return candidates


def _video_candidates(results: list[dict], provider: str) -> list[Candidate]:
    candidates: list[Candidate] = []
    for i, r in enumerate(results, start=1):
        url = r.get("content")
        if not url:
            continue
        images = r.get("images") or {}
        thumbnail = images.get("large") or images.get("medium") or images.get("small") or None
        candidates.append(
            Candidate(
                index=i,
                kind="video",
                url=url,
                provider=provider,
                title=r.get("title"),
                thumbnail_url=thumbnail,
                duration=parse_duration_to_seconds(r.get("duration")),
                source_page=url,
            )
        )
    return candidates
