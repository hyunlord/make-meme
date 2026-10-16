"""Shared helpers: URL/cache-key utilities, capped streaming downloads, duration/VTT parsing."""

from __future__ import annotations

import hashlib
import logging
import os
import re
from pathlib import Path
from urllib.parse import urlparse

import httpx

from .models import SourceError

logger = logging.getLogger(__name__)

DEFAULT_MAX_DOWNLOAD_MB = 500

USER_AGENT_DESKTOP = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
USER_AGENT_MOBILE = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1"
)

_CONTENT_TYPE_TO_EXT = {
    "video/mp4": ".mp4",
    "video/webm": ".webm",
    "video/quicktime": ".mov",
    "video/x-matroska": ".mkv",
    "video/x-m4v": ".m4v",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
}


def describe_exception(e: BaseException) -> str:
    """Format an exception for a user-facing ``SourceError`` message.

    Some exceptions (notably ``httpx.ReadTimeout`` and friends) have an empty
    ``str(e)``, which produces useless messages like "Openverse search
    failed: " with nothing after the colon. This always includes the
    exception's type name, falling back to just the type name when there's
    no message at all.
    """

    msg = str(e)
    return f"{type(e).__name__}: {msg}" if msg else type(e).__name__


def is_url(source: str) -> bool:
    try:
        return urlparse(source).scheme in ("http", "https")
    except ValueError:
        return False


def normalize_source(source: str) -> str:
    """Normalize a source string before hashing it for caching purposes."""

    return source.strip()


def cache_key(source: str) -> str:
    """A stable, filesystem-safe key for ``source`` used to name cached files/sidecars."""

    return hashlib.sha1(normalize_source(source).encode("utf-8")).hexdigest()


def max_download_bytes() -> int:
    """Read ``MAKE_MEME_MAX_DOWNLOAD_MB`` fresh on every call (so tests can monkeypatch it)."""

    raw = os.environ.get("MAKE_MEME_MAX_DOWNLOAD_MB", str(DEFAULT_MAX_DOWNLOAD_MB))
    try:
        mb = float(raw)
    except ValueError:
        logger.warning("invalid MAKE_MEME_MAX_DOWNLOAD_MB=%r, using default", raw)
        mb = DEFAULT_MAX_DOWNLOAD_MB
    return int(mb * 1024 * 1024)


def extension_from_content_type(content_type: str | None) -> str | None:
    if not content_type:
        return None
    ct = content_type.split(";")[0].strip().lower()
    return _CONTENT_TYPE_TO_EXT.get(ct)


def kind_from_content_type(content_type: str | None) -> str | None:
    if not content_type:
        return None
    ct = content_type.split(";")[0].strip().lower()
    if ct.startswith("video/"):
        return "video"
    if ct.startswith("image/"):
        return "image"
    return None


def guess_extension(url: str, kind: str) -> str:
    """Best-effort file extension for ``url``, falling back to a sane default for ``kind``."""

    ext = Path(urlparse(url).path).suffix.lower()
    if ext and len(ext) <= 6:
        return ext
    return ".mp4" if kind == "video" else ".jpg"


async def download_to_file(
    client: httpx.AsyncClient,
    url: str,
    dest: Path,
    *,
    headers: dict[str, str] | None = None,
) -> str | None:
    """Stream ``url`` to ``dest``, enforcing ``MAKE_MEME_MAX_DOWNLOAD_MB``.

    Returns the response's Content-Type header (if any). Raises
    :class:`SourceError` on HTTP errors, network errors, or if the size cap
    is exceeded; partial files are cleaned up in that case.
    """

    limit = max_download_bytes()
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        async with client.stream(
            "GET", url, headers=headers, follow_redirects=True, timeout=60.0
        ) as resp:
            if resp.status_code >= 400:
                raise SourceError(f"Download failed (HTTP {resp.status_code}) for {url}")
            content_type = resp.headers.get("content-type")
            declared_length = resp.headers.get("content-length")
            if declared_length and declared_length.isdigit() and int(declared_length) > limit:
                raise SourceError(
                    f"{url} is {int(declared_length) / 1024 / 1024:.0f}MB, over the "
                    f"{limit / 1024 / 1024:.0f}MB limit (raise it with MAKE_MEME_MAX_DOWNLOAD_MB)."
                )
            written = 0
            with open(dest, "wb") as f:  # noqa: ASYNC230 - interleaved with awaited chunks, not a long blocking call
                async for chunk in resp.aiter_bytes(chunk_size=65536):
                    written += len(chunk)
                    if written > limit:
                        raise SourceError(
                            f"{url} exceeded the {limit / 1024 / 1024:.0f}MB download limit "
                            "(raise it with MAKE_MEME_MAX_DOWNLOAD_MB)."
                        )
                    f.write(chunk)
            return content_type
    except httpx.HTTPError as e:
        dest.unlink(missing_ok=True)
        raise SourceError(f"Network error downloading {url}: {describe_exception(e)}") from e
    except SourceError:
        dest.unlink(missing_ok=True)
        raise


def parse_duration_to_seconds(text: str | None) -> float | None:
    """Parse "H:MM:SS" / "MM:SS" / "SS" (e.g. ddgs's ``"3:21"``) into seconds."""

    if not text or not isinstance(text, str):
        return None
    parts = text.strip().split(":")
    if not parts or not all(p.strip() for p in parts):
        return None
    try:
        numbers = [float(p) for p in parts]
    except ValueError:
        return None
    seconds = 0.0
    for n in numbers:
        seconds = seconds * 60 + n
    return seconds


def format_duration(seconds: float | None) -> str:
    """Render seconds as "M:SS" or "H:MM:SS", e.g. for grid captions."""

    if seconds is None:
        return "?:??"
    total = round(seconds)
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


_VTT_TIMESTAMP_RE = re.compile(r"\d{2}:\d{2}:\d{2}\.\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}\.\d{3}")
_VTT_INLINE_TAG_RE = re.compile(r"<[^>]+>")


def strip_vtt(vtt_text: str, max_chars: int = 1500) -> str:
    """Convert WebVTT subtitle text to a deduplicated plain-text excerpt.

    Auto-generated captions repeat the same rolling lines across many cues;
    this keeps each distinct line only once, in order, up to ``max_chars``.
    """

    lines_out: list[str] = []
    seen: set[str] = set()
    for raw_line in vtt_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.upper().startswith("WEBVTT"):
            continue
        if line.isdigit():
            continue
        if "-->" in line or _VTT_TIMESTAMP_RE.search(line):
            continue
        if line.startswith(("NOTE", "STYLE", "::cue", "Kind:", "Language:")):
            continue
        line = _VTT_INLINE_TAG_RE.sub("", line).strip()
        if line and line not in seen:
            seen.add(line)
            lines_out.append(line)
        if len(" ".join(lines_out)) >= max_chars:
            break
    return " ".join(lines_out)[:max_chars]
