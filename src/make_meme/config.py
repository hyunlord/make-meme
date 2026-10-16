"""Runtime configuration for make-meme, loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    """Resolved runtime paths and endpoints.

    All paths are derived from ``MAKE_MEME_HOME``. Directories are not
    created at construction time (so tests can point at a throwaway
    ``MAKE_MEME_HOME`` without side effects); call :meth:`ensure_dirs`
    before writing to them.
    """

    home: Path
    comfy_url: str
    comfy_dir: Path
    videos_dir: Path
    jobs_dir: Path
    outputs_dir: Path
    models_dir: Path
    assets_dir: Path
    searches_dir: Path

    def ensure_dirs(self) -> None:
        for d in (
            self.home,
            self.videos_dir,
            self.jobs_dir,
            self.outputs_dir,
            self.models_dir,
            self.assets_dir,
            self.searches_dir,
        ):
            d.mkdir(parents=True, exist_ok=True)


def _build_settings() -> Settings:
    home = Path(os.environ.get("MAKE_MEME_HOME", str(Path.home() / ".make-meme"))).expanduser()
    comfy_url = os.environ.get("COMFY_URL", "http://127.0.0.1:8188")
    comfy_dir = Path(os.environ.get("COMFY_DIR", str(home / "ComfyUI"))).expanduser()
    return Settings(
        home=home,
        comfy_url=comfy_url,
        comfy_dir=comfy_dir,
        videos_dir=home / "videos",
        jobs_dir=home / "jobs",
        outputs_dir=home / "outputs",
        models_dir=home / "models",
        assets_dir=home / "assets",
        searches_dir=home / "searches",
    )


@lru_cache(maxsize=1)
def _cached_settings() -> Settings:
    return _build_settings()


def get_settings() -> Settings:
    """Return the process-wide :class:`Settings`, built once and cached.

    Reads ``MAKE_MEME_HOME``, ``COMFY_URL``, and ``COMFY_DIR`` from the
    environment the first time this is called. Use :func:`reset_settings_cache`
    in tests after changing env vars.
    """

    return _cached_settings()


def reset_settings_cache() -> None:
    """Clear the cached :class:`Settings` so the next call re-reads env vars.

    Intended for tests that set ``MAKE_MEME_HOME``/``COMFY_URL``/``COMFY_DIR``
    per-test via ``monkeypatch.setenv``.
    """

    _cached_settings.cache_clear()
