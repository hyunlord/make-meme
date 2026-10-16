"""Search provider for Openverse (openverse.org) -- openly-licensed images, no API key."""

from __future__ import annotations

import logging
from typing import ClassVar

import httpx

from ..models import Candidate, SourceError
from ..utils import describe_exception

logger = logging.getLogger(__name__)

OPENVERSE_API_URL = "https://api.openverse.org/v1/images/"
# Openverse's API has been observed taking >15s to respond under load; a short connect
# timeout still fails fast on genuinely unreachable hosts.
REQUEST_TIMEOUT = httpx.Timeout(40.0, connect=10.0)


def _format_license(result: dict) -> str:
    name = (result.get("license") or "").upper()
    if not name:
        return "unknown -- check source"
    label = f"CC {name}"
    version = result.get("license_version")
    if version:
        label += f" {version}"
    creator = result.get("creator")
    if creator:
        label += f" ({creator})"
    return label


def parse_openverse_response(data: dict, provider_name: str = "openverse") -> list[Candidate]:
    """Pure parsing function (no I/O) so it can be unit-tested against a saved JSON fixture."""

    results = data.get("results") or []
    candidates: list[Candidate] = []
    for i, r in enumerate(results, start=1):
        url = r.get("url")
        if not url:
            continue
        candidates.append(
            Candidate(
                index=i,
                kind="image",
                url=url,
                provider=provider_name,
                title=r.get("title"),
                thumbnail_url=r.get("thumbnail"),
                width=r.get("width"),
                height=r.get("height"),
                license=_format_license(r),
                source_page=r.get("foreign_landing_url"),
            )
        )
    return candidates


class OpenverseSearchProvider:
    name = "openverse"
    kinds: ClassVar[set[str]] = {"image"}
    license_safe = True
    requires_key = None

    async def search(self, query: str, kind: str, n: int) -> list[Candidate]:
        if kind != "image" or n <= 0:
            return []
        params = {"q": query, "page_size": min(max(n, 1), 20)}
        try:
            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
                resp = await client.get(OPENVERSE_API_URL, params=params)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as e:
            raise SourceError(f"Openverse search failed: {describe_exception(e)}") from e

        return parse_openverse_response(data, self.name)
