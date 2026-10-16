"""Public data types for :mod:`make_meme.sources`.

These are the only types other parts of make-meme (and third-party
fetcher/search-provider plugins) should depend on.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


@dataclass
class FetchedMedia:
    """A single piece of media resolved to a local file on disk."""

    path: Path
    kind: Literal["video", "image"]
    provider: str
    source_url: str | None
    title: str | None = None
    uploader: str | None = None
    duration: float | None = None
    description: str | None = None
    subtitles_excerpt: str | None = None
    license: str | None = None
    extra: dict = field(default_factory=dict)


@dataclass
class Candidate:
    """One result from :func:`make_meme.sources.search`, not yet downloaded."""

    index: int
    kind: Literal["video", "image"]
    url: str
    provider: str
    title: str | None = None
    thumbnail_url: str | None = None
    duration: float | None = None
    width: int | None = None
    height: int | None = None
    license: str | None = None
    source_page: str | None = None


class SourceError(Exception):
    """Raised when media can't be fetched or searched.

    The message is shown directly to the end user, so it should be short and
    actionable (what went wrong, and what they can do about it) rather than a
    raw stack trace or library-internal error string.
    """
