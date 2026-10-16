"""Last-resort fetcher for any other http(s) page.

Tries, in order: the response's own Content-Type (covers "direct" media URLs
with no recognizable extension), ``og:video``/``twitter:player:stream`` meta
tags, a ``<video>``/``<source>`` tag, then ``og:image``. This is deliberately
the lowest-priority fetcher -- it only runs once every more specific fetcher
(direct, threads, yt-dlp) has declined the URL.
"""

from __future__ import annotations

import logging
from pathlib import Path
from urllib.parse import urljoin

import httpx

from ..htmlmeta import find_video_tag_src, parse_meta_tags
from ..models import FetchedMedia, SourceError
from ..netsafe import safe_client, safe_get
from ..utils import (
    USER_AGENT_DESKTOP,
    cache_key,
    describe_exception,
    download_to_file,
    extension_from_content_type,
    guess_extension,
    is_url,
    kind_from_content_type,
)

logger = logging.getLogger(__name__)


class GenericFetcher:
    name = "generic"
    priority = 100

    def can_handle(self, source: str) -> bool:
        return is_url(source)

    async def fetch(self, source: str, dest_dir: Path) -> FetchedMedia:
        dest_dir.mkdir(parents=True, exist_ok=True)

        async with safe_client(timeout=20.0, headers={"User-Agent": USER_AGENT_DESKTOP}) as client:
            try:
                resp = await safe_get(client, source)
            except httpx.HTTPError as e:
                raise SourceError(f"Could not fetch {source}: {describe_exception(e)}") from e
            if resp.status_code >= 400:
                raise SourceError(f"{source} returned HTTP {resp.status_code}")

            content_type = resp.headers.get("content-type", "")
            direct_kind = kind_from_content_type(content_type)
            if direct_kind is not None:
                # The URL serves the media directly (no HTML page to scrape).
                ext = extension_from_content_type(content_type) or guess_extension(
                    source, direct_kind
                )
                dest = dest_dir / f"{cache_key(source)}{ext}"
                dest.write_bytes(resp.content)
                return FetchedMedia(
                    path=dest, kind=direct_kind, provider=self.name, source_url=source
                )

            html = resp.text
            meta = parse_meta_tags(html)
            media_url = (
                meta.get("og:video:secure_url")
                or meta.get("og:video")
                or meta.get("twitter:player:stream")
            )
            kind = "video"
            if not media_url:
                media_url = find_video_tag_src(html)
            if not media_url:
                media_url = meta.get("og:image")
                kind = "image"
            if not media_url:
                raise SourceError(
                    f"Could not find a video or image on {source} (no og:video/og:image tags, "
                    "<video>/<source> tags, or twitter:player:stream)."
                )

            media_url = urljoin(str(resp.url), media_url)
            dest = dest_dir / f"{cache_key(source)}{guess_extension(media_url, kind)}"
            downloaded_content_type = await download_to_file(
                client, media_url, dest, headers={"Referer": source}
            )

        resolved_kind = kind_from_content_type(downloaded_content_type) or kind
        return FetchedMedia(
            path=dest,
            kind=resolved_kind,
            provider=self.name,
            source_url=source,
            title=meta.get("og:title"),
            description=meta.get("og:description"),
        )
