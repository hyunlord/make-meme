"""Fetcher for threads.net / threads.com post URLs.

yt-dlp has no Threads extractor, so this scrapes the page HTML directly:
first for JSON blobs embedding ``video_versions``/``image_versions2``/
``carousel_media`` (how Meta ships the actual CDN media URLs), then falling
back to ``og:video``/``og:image`` meta tags. Logged-out pages often omit the
media entirely, in which case we raise an actionable error pointing at
``MAKE_MEME_COOKIES_FILE``.
"""

from __future__ import annotations

import http.cookiejar
import logging
import os
import re
from pathlib import Path
from urllib.parse import urlparse

import httpx

from ..htmlmeta import iter_json_blobs, parse_meta_tags, walk
from ..models import FetchedMedia, SourceError
from ..utils import (
    USER_AGENT_DESKTOP,
    USER_AGENT_MOBILE,
    cache_key,
    describe_exception,
    download_to_file,
    guess_extension,
    is_url,
    kind_from_content_type,
)

logger = logging.getLogger(__name__)

THREADS_DOMAINS = {"threads.net", "www.threads.net", "threads.com", "www.threads.com"}
_UPLOADER_RE = re.compile(r"\(@([\w.]+)\)")


def _area(d: dict) -> int:
    return (d.get("width") or 0) * (d.get("height") or 0)


def _best_video_url(blobs: list) -> str | None:
    best_url: str | None = None
    best_area = -1
    for blob in blobs:
        for node in walk(blob):
            if not isinstance(node, dict):
                continue
            versions = node.get("video_versions")
            if not isinstance(versions, list):
                continue
            for v in versions:
                if not isinstance(v, dict) or not v.get("url"):
                    continue
                area = _area(v)
                if area > best_area:
                    best_area = area
                    best_url = v["url"]
    return best_url


def _best_image_url(blobs: list) -> str | None:
    for blob in blobs:
        for node in walk(blob):
            if not isinstance(node, dict):
                continue
            iv2 = node.get("image_versions2")
            candidates = iv2.get("candidates") if isinstance(iv2, dict) else None
            if isinstance(candidates, list) and candidates:
                best = max((c for c in candidates if isinstance(c, dict)), key=_area, default=None)
                if best and best.get("url"):
                    return best["url"]
    return None


def _looks_like_has_media(html: str) -> bool:
    markers = ("video_versions", "image_versions2", "og:video", "og:image")
    return any(m in html for m in markers)


def _load_cookies() -> httpx.Cookies | None:
    cookies_file = os.environ.get("MAKE_MEME_COOKIES_FILE")
    if not cookies_file:
        return None
    jar = http.cookiejar.MozillaCookieJar(cookies_file)
    try:
        jar.load(ignore_discard=True, ignore_expires=True)
    except OSError as e:
        logger.warning("failed to load MAKE_MEME_COOKIES_FILE=%s: %s", cookies_file, e)
        return None
    cookies = httpx.Cookies()
    for c in jar:
        cookies.set(c.name, c.value, domain=c.domain, path=c.path)
    return cookies


class ThreadsFetcher:
    name = "threads"
    priority = 5

    def can_handle(self, source: str) -> bool:
        if not is_url(source):
            return False
        return urlparse(source).netloc.lower() in THREADS_DOMAINS

    async def fetch(self, source: str, dest_dir: Path) -> FetchedMedia:
        dest_dir.mkdir(parents=True, exist_ok=True)
        cookies = _load_cookies()

        async with httpx.AsyncClient(
            cookies=cookies, follow_redirects=True, timeout=20.0
        ) as client:
            html = await self._fetch_html(client, source)
            meta = parse_meta_tags(html)
            blobs = list(iter_json_blobs(html))

            media_url = _best_video_url(blobs)
            kind = "video"
            if not media_url:
                media_url = _best_image_url(blobs)
                kind = "image"
            if not media_url:
                media_url = meta.get("og:video:secure_url") or meta.get("og:video")
                kind = "video"
            if not media_url:
                media_url = meta.get("og:image")
                kind = "image"
            if not media_url:
                raise SourceError(
                    "Threads didn't expose the media without login; set MAKE_MEME_COOKIES_FILE to a "
                    "Netscape-format cookies.txt exported while logged in, or download the media "
                    "manually and pass the file path instead."
                )

            dest = dest_dir / f"{cache_key(source)}{guess_extension(media_url, kind)}"
            referer = f"https://{urlparse(source).netloc}/"
            try:
                content_type = await download_to_file(
                    client, media_url, dest, headers={"Referer": referer}
                )
            except SourceError as e:
                # A signed CDN URL that 403s almost always means the page was served a
                # logged-out/stripped-down view; the same cookies fix as "nothing found" applies.
                raise SourceError(
                    f"{e} -- this usually means Threads served a logged-out page. Try setting "
                    "MAKE_MEME_COOKIES_FILE to a Netscape-format cookies.txt exported while logged in."
                ) from e

        resolved_kind = kind_from_content_type(content_type) or kind
        title = meta.get("og:title")
        uploader_match = _UPLOADER_RE.search(title) if title else None

        return FetchedMedia(
            path=dest,
            kind=resolved_kind,
            provider=self.name,
            source_url=source,
            title=title,
            uploader=uploader_match.group(1) if uploader_match else None,
            description=meta.get("og:description"),
        )

    async def _fetch_html(self, client: httpx.AsyncClient, source: str) -> str:
        fetched: list[str] = []
        errors: list[str] = []
        for ua in (USER_AGENT_DESKTOP, USER_AGENT_MOBILE):
            try:
                resp = await client.get(source, headers={"User-Agent": ua})
            except httpx.HTTPError as e:
                errors.append(describe_exception(e))
                continue
            if resp.status_code >= 400:
                errors.append(f"HTTP {resp.status_code}")
                continue
            fetched.append(resp.text)
            if _looks_like_has_media(resp.text):
                return resp.text
        if fetched:
            return fetched[0]
        raise SourceError(
            f"Could not fetch the Threads page ({'; '.join(errors) or 'unknown error'})."
        )
