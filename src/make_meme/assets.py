"""Asset registry: every loaded/generated media file gets a stable id + metadata.

Assets let pipeline stages chain (e.g. a swap's output video becomes the
input to another swap) and let tools report what they produced without the
caller needing to know the on-disk layout.
"""

from __future__ import annotations

import json
import logging
import secrets
import shutil
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

from .config import get_settings

logger = logging.getLogger(__name__)

AssetKind = Literal["video", "image"]

_ID_PREFIXES: dict[str, str] = {"video": "vid", "image": "img"}


@dataclass
class Asset:
    id: str
    kind: AssetKind
    path: Path
    origin: dict[str, Any] = field(default_factory=dict)
    meta: dict[str, Any] = field(default_factory=dict)
    parent_ids: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def to_json(self) -> dict[str, Any]:
        data = asdict(self)
        data["path"] = str(self.path)
        return data

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> Asset:
        return cls(
            id=data["id"],
            kind=data["kind"],
            path=Path(data["path"]),
            origin=dict(data.get("origin") or {}),
            meta=dict(data.get("meta") or {}),
            parent_ids=list(data.get("parent_ids") or []),
            created_at=float(data.get("created_at", time.time())),
        )

    def save(self, directory: Path) -> None:
        """Persist this asset's record as ``asset.json`` inside ``directory``."""

        directory.mkdir(parents=True, exist_ok=True)
        (directory / "asset.json").write_text(json.dumps(self.to_json(), indent=2, default=str))


# Formats ComfyUI's LoadImage (and many models' preprocessing) can't read directly.
_CONVERT_SUFFIXES = {".heic", ".heif", ".avif", ".gif", ".tif", ".tiff"}


def _normalize_image(path: Path) -> Path:
    """Make an image safe for every downstream consumer: phone formats (HEIC/HEIF/AVIF)
    become PNG, and EXIF orientation is baked in so ComfyUI, SAM 3 and our own geometry
    all see the same upright pixels. Returns the (possibly new) path."""
    from PIL import Image, ImageOps

    try:
        import pillow_heif

        pillow_heif.register_heif_opener()
    except ImportError:  # optional at runtime; HEIC then fails with a clear OSError below
        pass

    with Image.open(path) as im:
        rotated = im.getexif().get(0x0112, 1) not in (1, None)
        if path.suffix.lower() not in _CONVERT_SUFFIXES and not rotated:
            return path
        upright = ImageOps.exif_transpose(im)
        if upright.mode not in ("RGB", "RGBA", "L"):
            upright = upright.convert("RGBA" if "A" in upright.getbands() else "RGB")
        out = path.with_suffix(".png")
        upright.save(out)
    if out != path:
        path.unlink(missing_ok=True)
    return out


def _new_id(kind: str) -> str:
    prefix = _ID_PREFIXES.get(kind, "ast")
    return f"{prefix}_{secrets.token_hex(4)}"


class AssetStore:
    """Manages assets under ``$MAKE_MEME_HOME/assets/<id>/``, one directory per asset."""

    def __init__(self, root: Path | None = None) -> None:
        settings = get_settings()
        self.root = root or settings.assets_dir
        self.root.mkdir(parents=True, exist_ok=True)

    def _dir_for(self, asset_id: str) -> Path:
        return self.root / asset_id

    def add(
        self,
        path: Path,
        kind: AssetKind,
        *,
        origin: dict[str, Any] | None = None,
        meta: dict[str, Any] | None = None,
        parent_ids: list[str] | None = None,
        move: bool = False,
    ) -> Asset:
        """Register ``path`` as a new asset, copying (or moving, if ``move``) it into the store.

        For a video, probes duration/fps/width/height/has_audio via
        :func:`make_meme.ingest.probe`, merges them into ``meta`` (without
        overriding anything already passed in ``meta``), and extracts a
        first-frame preview (``meta["preview_path"]``). For an image, reads
        width/height via Pillow. Probe/preview failures are non-fatal: the
        asset is still created, just without the derived metadata.
        """

        asset_id = _new_id(kind)
        asset_dir = self._dir_for(asset_id)
        asset_dir.mkdir(parents=True, exist_ok=True)
        dest = asset_dir / path.name
        if move:
            shutil.move(str(path), str(dest))
        else:
            shutil.copy2(str(path), str(dest))

        merged_meta: dict[str, Any] = dict(meta or {})
        if kind == "video":
            from . import ingest

            try:
                probed = ingest.probe(dest)
            except (RuntimeError, ValueError, json.JSONDecodeError):
                probed = None
            if probed:
                for key in ("duration", "fps", "width", "height", "has_audio"):
                    merged_meta.setdefault(key, probed[key])

            if "preview_path" not in merged_meta:
                try:
                    preview_path = asset_dir / "preview.jpg"
                    ingest.extract_frame(dest, 0.0).save(preview_path)
                    merged_meta["preview_path"] = str(preview_path)
                except (RuntimeError, OSError):
                    logger.warning("could not extract a preview frame for %s", dest)
        elif kind == "image":
            try:
                dest = _normalize_image(dest)
                from PIL import Image

                with Image.open(dest) as im:
                    merged_meta.setdefault("width", im.width)
                    merged_meta.setdefault("height", im.height)
            except OSError:
                logger.warning("could not read image dimensions for %s", dest)

        asset = Asset(
            id=asset_id,
            kind=kind,
            path=dest,
            origin=dict(origin or {}),
            meta=merged_meta,
            parent_ids=list(parent_ids or []),
        )
        asset.save(asset_dir)
        return asset

    def get(self, asset_id: str) -> Asset | None:
        info_path = self._dir_for(asset_id) / "asset.json"
        if not info_path.exists():
            return None
        return Asset.from_json(json.loads(info_path.read_text()))

    def list(self, kind: AssetKind | None = None, limit: int = 50) -> list[Asset]:
        """List known assets, newest first."""

        assets: list[Asset] = []
        if not self.root.is_dir():
            return assets
        for d in self.root.iterdir():
            if not d.is_dir():
                continue
            info_path = d / "asset.json"
            if not info_path.exists():
                continue
            try:
                asset = Asset.from_json(json.loads(info_path.read_text()))
            except (json.JSONDecodeError, KeyError, TypeError):
                continue
            if kind is not None and asset.kind != kind:
                continue
            assets.append(asset)
        assets.sort(key=lambda a: a.created_at, reverse=True)
        return assets[:limit]

    def resolve(self, ref: str) -> Asset:
        """Resolve an asset id to its :class:`Asset`, raising ``KeyError`` if not found."""

        asset = self.get(ref)
        if asset is None:
            raise KeyError(f"no asset with id {ref!r}")
        return asset
