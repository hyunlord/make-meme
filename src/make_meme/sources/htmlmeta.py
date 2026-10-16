"""Minimal, dependency-free HTML scraping helpers.

Regex-based rather than a real HTML parser -- make-meme's dependency list is
deliberately small (httpx, pillow, yt-dlp, ddgs), and extracting a handful of
``<meta>`` tags and embedded JSON blobs does not need a full DOM. This is
*not* a general HTML parser; it is good enough for the og:*/twitter:* tags
and JSON state blobs that real platforms embed in their pages.
"""

from __future__ import annotations

import html
import json
import re
from collections.abc import Iterator
from typing import Any

_META_TAG_RE = re.compile(r"<meta\b[^>]*>", re.IGNORECASE)
_ATTR_RE = re.compile(r"""(\w[\w:-]*)\s*=\s*"([^"]*)"|(\w[\w:-]*)\s*=\s*'([^']*)'""")
_SCRIPT_JSON_RE = re.compile(
    r'<script[^>]+type=["\']application/(?:ld\+)?json["\'][^>]*>(.*?)</script>',
    re.DOTALL | re.IGNORECASE,
)
_VIDEO_TAG_RE = re.compile(r'<video\b[^>]*\bsrc=["\']([^"\']+)["\']', re.IGNORECASE)
_SOURCE_TAG_RE = re.compile(r'<source\b[^>]*\bsrc=["\']([^"\']+)["\']', re.IGNORECASE)


def parse_meta_tags(html_text: str) -> dict[str, str]:
    """Extract ``<meta property="..." content="...">`` (and ``name=``) pairs.

    Attribute order is not assumed (``content`` may come before or after
    ``property``/``name``). The first value seen for a given key wins.
    """

    result: dict[str, str] = {}
    for tag in _META_TAG_RE.findall(html_text):
        attrs: dict[str, str] = {}
        for m in _ATTR_RE.finditer(tag):
            if m.group(1):
                attrs[m.group(1).lower()] = m.group(2)
            else:
                attrs[m.group(3).lower()] = m.group(4)
        key = attrs.get("property") or attrs.get("name")
        content = attrs.get("content")
        if key and content is not None:
            # Attribute values are HTML-entity-escaped (CDN URLs commonly contain
            # "&" in their query string, serialized as "&amp;"); unescape before use.
            result.setdefault(key.lower(), html.unescape(content))
    return result


def iter_json_blobs(html_text: str) -> Iterator[Any]:
    """Yield parsed JSON objects from ``<script type="application/json">`` tags.

    Blocks that fail to parse (truncated, not actually JSON, etc.) are
    silently skipped.
    """

    for match in _SCRIPT_JSON_RE.finditer(html_text):
        try:
            yield json.loads(match.group(1))
        except (json.JSONDecodeError, ValueError):
            continue


def walk(obj: Any) -> Iterator[Any]:
    """Depth-first walk over nested dict/list structures, yielding every dict/list node."""

    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            yield from walk(v)
    elif isinstance(obj, list):
        yield obj
        for item in obj:
            yield from walk(item)


def find_video_tag_src(html_text: str) -> str | None:
    """Find a ``<video src=...>`` or ``<video><source src=...>`` URL, if any."""

    m = _VIDEO_TAG_RE.search(html_text) or _SOURCE_TAG_RE.search(html_text)
    return html.unescape(m.group(1)) if m else None
