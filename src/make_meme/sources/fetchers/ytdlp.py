"""Fetcher for any http(s) URL yt-dlp has a dedicated (non-generic) extractor for.

Covers YouTube/Shorts, TikTok (incl. vm.tiktok.com short links), Instagram
reels/posts, X/Twitter, Facebook, Reddit, Bilibili, and hundreds of other
sites -- anything yt-dlp doesn't fall back to its ``GenericIE`` for. Threads
is notably *not* supported by yt-dlp, so it naturally falls through to
:mod:`.threads`.
"""

from __future__ import annotations

import asyncio
import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from ..models import FetchedMedia, SourceError
from ..utils import cache_key, describe_exception, is_url, strip_vtt

logger = logging.getLogger(__name__)

SUBTITLE_LANGS = ["ko", "en"]
MAX_DESCRIPTION_CHARS = 1000
MAX_SUBTITLE_CHARS = 1500
_IGNORED_SUFFIXES = {".json", ".vtt", ".part", ".ytdl", ".description", ".info.json"}


class _YtDlpLogger:
    """Routes yt-dlp's own logging to ours -- stdout is the MCP stdio channel, never yt-dlp's to print."""

    def debug(self, msg: str) -> None:
        logger.debug(msg)

    def info(self, msg: str) -> None:
        logger.info(msg)

    def warning(self, msg: str) -> None:
        logger.warning(msg)

    def error(self, msg: str) -> None:
        logger.error(msg)


@lru_cache(maxsize=1)
def _non_generic_extractors() -> tuple:
    # Compare by IE_NAME rather than importing yt_dlp.extractor.generic.GenericIE and
    # checking identity: installs with a pre-built lazy_extractors module expose a
    # *different* GenericIE class object (yt_dlp.extractor.lazy_extractors.GenericIE)
    # that an identity check would fail to exclude.
    from yt_dlp.extractor import gen_extractor_classes

    return tuple(cls for cls in gen_extractor_classes() if cls.IE_NAME != "generic")


def _suitable_extractor(url: str) -> Any:
    for cls in _non_generic_extractors():
        try:
            if cls.suitable(url):
                return cls
        except Exception:  # noqa: S112, BLE001 - a misbehaving extractor shouldn't break dispatch
            continue
    return None


def map_ytdlp_error(message: str) -> str:
    """Translate a raw yt-dlp error string into an actionable, user-facing message."""

    lower = message.lower()
    if "sign in" in lower or "login" in lower or "cookies" in lower:
        return (
            "This content requires logging in. Set MAKE_MEME_COOKIES_FROM_BROWSER=chrome "
            "(or safari/firefox -- log into the site in that browser first), or set "
            "MAKE_MEME_COOKIES_FILE to a Netscape-format cookies.txt."
        )
    if "private" in lower:
        return "This video/post is private and can't be downloaded without access."
    if "geo" in lower and ("block" in lower or "restrict" in lower):
        return "This content is geo-blocked in the server's region."
    if "removed" in lower or "unavailable" in lower or "not available" in lower or "404" in lower:
        return "This video/post appears to have been removed or is no longer available."
    if "429" in lower or ("rate" in lower and "limit" in lower):
        return "Rate-limited by the platform; wait a bit and try again."
    return f"Could not download: {message.strip()}"


class YtDlpFetcher:
    name = "ytdlp"
    priority = 10

    def can_handle(self, source: str) -> bool:
        if not is_url(source):
            return False
        return _suitable_extractor(source) is not None

    async def fetch(self, source: str, dest_dir: Path) -> FetchedMedia:
        return await asyncio.to_thread(self._fetch_sync, source, dest_dir)

    def _fetch_sync(self, source: str, dest_dir: Path) -> FetchedMedia:
        import yt_dlp

        dest_dir.mkdir(parents=True, exist_ok=True)
        key = cache_key(source)
        outtmpl = str(dest_dir / f"{key}.%(ext)s")

        ydl_opts: dict[str, Any] = {
            "format": (
                "bv*[height<=1080][ext=mp4]+ba[ext=m4a]/b[height<=1080][ext=mp4]/"
                "bv*[height<=1080]+ba/b"
            ),
            "merge_output_format": "mp4",
            "outtmpl": outtmpl,
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "noprogress": True,
            "logger": _YtDlpLogger(),
            "writesubtitles": True,
            "writeautomaticsubtitles": True,
            "subtitleslangs": SUBTITLE_LANGS,
            "subtitlesformat": "vtt",
        }

        cookies_from_browser = os.environ.get("MAKE_MEME_COOKIES_FROM_BROWSER")
        if cookies_from_browser:
            ydl_opts["cookiesfrombrowser"] = (cookies_from_browser,)
        cookies_file = os.environ.get("MAKE_MEME_COOKIES_FILE")
        if cookies_file:
            ydl_opts["cookiefile"] = cookies_file

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(source, download=True)
        except yt_dlp.utils.DownloadError as e:
            raise SourceError(map_ytdlp_error(str(e) or describe_exception(e))) from e

        if info is None:
            raise SourceError(f"yt-dlp returned no information for {source}")
        if info.get("entries"):
            info = info["entries"][0]

        media_path = self._resolve_output_path(info, dest_dir, key)
        kind = "video"
        if media_path is None:
            media_path = self._resolve_thumbnail_fallback(info, dest_dir, key)
            kind = "image"
        if media_path is None:
            raise SourceError(f"yt-dlp did not produce a downloadable file for {source}")

        subtitles_excerpt = self._load_subtitles_excerpt(dest_dir, key)
        description = info.get("description")
        if description and len(description) > MAX_DESCRIPTION_CHARS:
            description = description[:MAX_DESCRIPTION_CHARS] + "..."

        return FetchedMedia(
            path=media_path,
            kind=kind,
            provider=self.name,
            source_url=info.get("webpage_url") or source,
            title=info.get("title"),
            uploader=info.get("uploader") or info.get("channel"),
            duration=info.get("duration"),
            description=description,
            subtitles_excerpt=subtitles_excerpt,
            license=info.get("license"),
            extra={"extractor": info.get("extractor_key") or info.get("extractor")},
        )

    @staticmethod
    def _resolve_output_path(info: dict, dest_dir: Path, key: str) -> Path | None:
        for rd in info.get("requested_downloads") or []:
            fp = rd.get("filepath")
            if fp and Path(fp).exists():
                return Path(fp)
        filename = info.get("_filename") or info.get("filename")
        if filename and Path(filename).exists():
            return Path(filename)
        candidates = sorted(
            p for p in dest_dir.glob(f"{key}.*") if p.suffix.lower() not in _IGNORED_SUFFIXES
        )
        return candidates[0] if candidates else None

    @staticmethod
    def _resolve_thumbnail_fallback(info: dict, dest_dir: Path, key: str) -> Path | None:
        """Image-only posts (e.g. an Instagram photo) have no video; grab the best thumbnail/image instead."""

        url = info.get("thumbnail")
        if not url:
            thumbnails = info.get("thumbnails") or []
            if thumbnails:
                url = thumbnails[-1].get("url")
        if not url:
            return None

        import httpx

        dest = dest_dir / f"{key}.jpg"
        try:
            resp = httpx.get(url, timeout=30.0, follow_redirects=True)
            resp.raise_for_status()
            dest.write_bytes(resp.content)
        except httpx.HTTPError as e:
            logger.warning("failed to download image-only fallback thumbnail: %s", e)
            return None
        return dest

    @staticmethod
    def _load_subtitles_excerpt(dest_dir: Path, key: str) -> str | None:
        for lang in SUBTITLE_LANGS:
            vtt_path = dest_dir / f"{key}.{lang}.vtt"
            if vtt_path.exists():
                return strip_vtt(
                    vtt_path.read_text(encoding="utf-8", errors="replace"), MAX_SUBTITLE_CHARS
                )
        for vtt_path in sorted(dest_dir.glob(f"{key}*.vtt")):
            return strip_vtt(
                vtt_path.read_text(encoding="utf-8", errors="replace"), MAX_SUBTITLE_CHARS
            )
        return None
