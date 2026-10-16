"""Guards for local file paths passed in tool arguments.

Tool arguments can be influenced by untrusted web content (prompt injection), and a
loaded file is shown back to the model and may be uploaded to a remote ComfyUI. Media
files the user points at are the whole point of the tool, so plain photo/video paths
stay allowed; what we refuse is reaching into hidden/config locations (~/.ssh, ~/.aws,
dot-directories, system dirs) where nobody keeps meme material.
"""

from __future__ import annotations

import os
from pathlib import Path

from make_meme.config import get_settings

_BLOCKED_PREFIXES = ("/etc", "/private/etc", "/var/root", "/System", "/Library/Keychains", "/proc", "/sys", "/dev")


class UnsafePathError(ValueError):
    """Message is user-facing."""


def check_local_media_path(path: Path) -> Path:
    """Resolve `path` and refuse hidden or system locations (unless inside MAKE_MEME_HOME,
    or explicitly allowed via MAKE_MEME_ALLOWED_DIRS, os.pathsep-separated)."""
    resolved = path.expanduser().resolve()
    home = get_settings().home.expanduser().resolve()
    allowed = [home] + [Path(p).expanduser().resolve()
                        for p in os.environ.get("MAKE_MEME_ALLOWED_DIRS", "").split(os.pathsep) if p]
    if any(resolved.is_relative_to(a) for a in allowed):
        return resolved
    if any(str(resolved).startswith(p + "/") or str(resolved) == p for p in _BLOCKED_PREFIXES):
        raise UnsafePathError(f"Refusing to read {resolved}: system location.")
    hidden = [part for part in resolved.parts[1:-1] if part.startswith(".")]
    if hidden or resolved.name.startswith("."):
        raise UnsafePathError(
            f"Refusing to read {resolved}: it is inside a hidden directory ({hidden[0] if hidden else resolved.name}). "
            "Move the file somewhere normal (e.g. ~/Downloads) or add its folder to MAKE_MEME_ALLOWED_DIRS."
        )
    return resolved
