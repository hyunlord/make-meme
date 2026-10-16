"""YouTube search via yt-dlp's ``ytsearch`` pseudo-extractor.

Uses ``extract_flat`` so this is a single lightweight request (a search
results page), not one request per video.
"""

from __future__ import annotations

import asyncio
import logging
from typing import ClassVar

from ..models import Candidate, SourceError
from ..utils import describe_exception

logger = logging.getLogger(__name__)


class YouTubeSearchProvider:
    name = "youtube"
    kinds: ClassVar[set[str]] = {"video"}
    license_safe = False
    requires_key = None

    async def search(self, query: str, kind: str, n: int) -> list[Candidate]:
        if kind != "video" or n <= 0:
            return []
        return await asyncio.to_thread(self._search_sync, query, n)

    def _search_sync(self, query: str, n: int) -> list[Candidate]:
        import yt_dlp

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "noprogress": True,
            "extract_flat": True,
            "skip_download": True,
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(f"ytsearch{n}:{query}", download=False)
        except Exception as e:
            raise SourceError(f"YouTube search failed: {describe_exception(e)}") from e

        entries = (info or {}).get("entries") or []
        candidates: list[Candidate] = []
        for i, entry in enumerate(entries, start=1):
            if not entry:
                continue
            video_id = entry.get("id")
            if not video_id:
                continue
            url = f"https://www.youtube.com/watch?v={video_id}"
            thumbnail = entry.get("thumbnail") or f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
            candidates.append(
                Candidate(
                    index=i,
                    kind="video",
                    url=url,
                    provider=self.name,
                    title=entry.get("title"),
                    thumbnail_url=thumbnail,
                    duration=entry.get("duration"),
                    source_page=url,
                )
            )
        return candidates
