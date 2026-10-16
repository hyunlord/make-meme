"""Fetcher for local file paths and URLs that point straight at a media file."""

from __future__ import annotations

import logging
from pathlib import Path
from urllib.parse import urlparse

from ..models import FetchedMedia, SourceError
from ..netsafe import safe_client
from ..utils import USER_AGENT_DESKTOP, cache_key, download_to_file, is_url, kind_from_content_type

logger = logging.getLogger(__name__)

VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm", ".mkv", ".avi", ".m4v", ".flv"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tiff"}


def _kind_from_extension(ext: str) -> str | None:
    if ext in VIDEO_EXTENSIONS:
        return "video"
    if ext in IMAGE_EXTENSIONS:
        return "image"
    return None


class DirectFetcher:
    """Local filesystem paths, and URLs whose path ends in a recognized media extension.

    URLs with no/ambiguous extension are left for :class:`~.generic.GenericFetcher`
    (lowest priority), which sniffs the response Content-Type as a last resort.
    """

    name = "direct"
    priority = 0

    def can_handle(self, source: str) -> bool:
        if not is_url(source):
            return True
        ext = Path(urlparse(source).path).suffix.lower()
        return _kind_from_extension(ext) is not None

    async def fetch(self, source: str, dest_dir: Path) -> FetchedMedia:
        if not is_url(source):
            return self._fetch_local(source)
        return await self._fetch_url(source, dest_dir)

    def _fetch_local(self, source: str) -> FetchedMedia:
        path = Path(source).expanduser()
        if not path.is_file():
            raise SourceError(f"Local file not found: {path}")
        kind = _kind_from_extension(path.suffix.lower())
        if kind is None:
            raise SourceError(
                f"{path} doesn't look like an image or video file (unrecognized extension {path.suffix!r})."
            )
        return FetchedMedia(path=path, kind=kind, provider=self.name, source_url=None)

    async def _fetch_url(self, source: str, dest_dir: Path) -> FetchedMedia:
        ext = Path(urlparse(source).path).suffix.lower()
        kind = _kind_from_extension(ext)
        if kind is None:
            raise SourceError(f"{source} does not look like a direct media URL.")

        dest = dest_dir / f"{cache_key(source)}{ext}"
        if not dest.exists():
            async with safe_client(headers={"User-Agent": USER_AGENT_DESKTOP}) as client:
                content_type = await download_to_file(client, source, dest)
            resolved_kind = kind_from_content_type(content_type)
            if resolved_kind is not None and resolved_kind != kind:
                logger.warning(
                    "content-type %s for %s disagrees with extension-based kind %s; trusting content-type",
                    content_type,
                    source,
                    kind,
                )
                kind = resolved_kind

        return FetchedMedia(path=dest, kind=kind, provider=self.name, source_url=source)
