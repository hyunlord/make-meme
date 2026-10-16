"""FastMCP server exposing make-meme's media tools (stdio transport).

Logging goes to stderr only -- stdout is the MCP stdio channel and must never
receive anything else.

This module owns the shared ``mcp`` FastMCP instance plus the ``get_assets()``
/``get_jobs()`` singletons, so other modules (``tools_swap.py`` with
detect/swap tools backed by ComfyUI recipes, ``tools_trend.py`` with
analyze_meme_usage) can register more ``@mcp.tool()``/``@mcp.prompt()``
functions against the same server. See the bottom of this file.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import shutil
import sys
import uuid
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any, Literal

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp import Image as MCPImage
from mcp.server.fastmcp.exceptions import ToolError

from . import ingest
from .assets import AssetStore
from .config import get_settings
from .jobs import JobManager
from .safety import UnsafePathError, check_local_media_path

logging.basicConfig(
    level=logging.INFO,
    stream=sys.stderr,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

mcp = FastMCP("make-meme")

# Other modules can append an async `() -> Any` callable here; check_setup()
# calls each and includes its result under a key named after the callable.
extra_checks: list[Callable[[], Awaitable[Any]]] = []

_assets: AssetStore | None = None
_jobs: JobManager | None = None


def get_assets() -> AssetStore:
    global _assets
    if _assets is None:
        _assets = AssetStore()
    return _assets


def get_jobs() -> JobManager:
    global _jobs
    if _jobs is None:
        _jobs = JobManager()
    return _jobs


def _load_sources_backend():
    """Import ``make_meme.sources`` lazily; it's built separately and may lag behind.

    Raises :class:`ToolError` with an actionable message rather than letting
    an ImportError/AttributeError propagate as a stack trace to the LLM.
    """

    try:
        from . import sources
    except ImportError as exc:
        raise ToolError(
            "Media search/fetch isn't available yet (make_meme.sources failed to import: "
            f"{exc}). Use a local file path with load_media instead, or try again later."
        ) from exc
    missing = [n for n in ("fetch", "search", "build_candidate_grid", "SourceError") if not hasattr(sources, n)]
    if missing:
        raise ToolError(f"Media search/fetch backend is incomplete (missing: {', '.join(missing)}).")
    return sources


# --------------------------------------------------------------------------
# check_setup
# --------------------------------------------------------------------------


async def _check_setup_impl() -> dict[str, Any]:
    report: dict[str, Any] = {}

    for tool in ("ffmpeg", "ffprobe"):
        path = shutil.which(tool)
        report[tool] = {
            "found": path is not None,
            "path": path,
            "hint": None if path else f"Install {tool} (e.g. `brew install ffmpeg`) and put it on PATH.",
        }

    try:
        from . import sources  # noqa: F401

        report["sources"] = {"available": True}
    except ImportError as exc:
        report["sources"] = {
            "available": False,
            "error": str(exc),
            "hint": "search_media/load_media (for URLs/search) won't work until this is fixed.",
        }

    settings = get_settings()
    try:
        from .comfy.client import ComfyClient  # sends COMFY_TOKEN when set (remote proxy)

        async with ComfyClient(settings.comfy_url) as client:
            stats = await client.system_stats()
            devices = stats.get("devices") or [{}]
            device = devices[0]
            report["comfyui"] = {
                "reachable": True,
                "url": settings.comfy_url,
                "device": device.get("name"),
                "vram_total": device.get("vram_total"),
                "vram_free": device.get("vram_free"),
            }
    except Exception as exc:  # noqa: BLE001 - ComfyUI may be unreachable/misconfigured in any way
        report["comfyui"] = {
            "reachable": False,
            "url": settings.comfy_url,
            "error": str(exc),
            "hint": f"Start ComfyUI so it listens at {settings.comfy_url} (override with COMFY_URL).",
        }

    for check in extra_checks:
        name = getattr(check, "__name__", "extra_check")
        try:
            report[name] = await check()
        except Exception as exc:  # noqa: BLE001 - a third-party check may raise anything
            report[name] = {"ok": False, "error": str(exc)}

    return report


@mcp.tool()
async def check_setup() -> str:
    """Check that make-meme's dependencies are ready: ffmpeg/ffprobe on PATH, whether the media
    search/fetch backend is importable, and whether ComfyUI is reachable at COMFY_URL. Call this
    first if other tools are failing, for actionable fix hints."""

    report = await _check_setup_impl()
    return json.dumps(report, indent=2)


# --------------------------------------------------------------------------
# search_media / load_media / inspect_media
# --------------------------------------------------------------------------

_ASSET_ID_RE = re.compile(r"^(vid|img)_[0-9a-f]+$")
_SEARCH_REF_RE = re.compile(r"^([0-9a-f]+):(\d+)$")
VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".webm", ".m4v", ".avi"}


def _looks_like_asset_id(source: str) -> bool:
    return bool(_ASSET_ID_RE.match(source))


def _looks_like_video_path(path: Path) -> bool:
    return path.suffix.lower() in VIDEO_EXTS


def _is_url(s: str) -> bool:
    return "://" in s


async def _resolve_search_ref(source: str) -> tuple[str, dict[str, Any]]:
    """If ``source`` is ``"<search_id>:<n>"``, resolve it to the candidate's URL + metadata."""

    match = _SEARCH_REF_RE.match(source)
    if not match:
        return source, {}
    search_id, index_str = match.groups()
    settings = get_settings()
    search_path = settings.searches_dir / f"{search_id}.json"
    if not search_path.exists():
        raise ToolError(f"No search session found with id {search_id!r}; call search_media first.")
    data = json.loads(search_path.read_text())
    index = int(index_str)
    candidate = next((c for c in data.get("candidates", []) if c.get("index") == index), None)
    if candidate is None:
        raise ToolError(f"Search {search_id!r} has no candidate #{index}.")
    url = candidate.get("url")
    if not url:
        raise ToolError(f"Candidate #{index} in search {search_id!r} has no URL.")
    return url, {"candidate": candidate}


@mcp.tool(structured_output=False)
async def search_media(
    query: str,
    kind: Literal["video", "image"] = "video",
    n: int = 8,
    provider: str | None = None,
    license_safe: bool = False,
) -> list[Any]:
    """Search the web for a video or image by text -- no video/image attachment needed. Returns a
    numbered thumbnail grid image plus a JSON list of candidates (title, duration, license, etc).
    Pass "<search_id>:<candidate_number>" as the `source` argument to load_media to fetch and
    register the chosen candidate as an asset. Set license_safe=True to restrict results to
    permissively-licensed media."""

    sources = _load_sources_backend()
    try:
        candidates = await sources.search(query, kind=kind, n=n, provider=provider, license_safe=license_safe)
    except sources.SourceError as exc:
        raise ToolError(str(exc)) from exc

    if not candidates:
        return [json.dumps({"search_id": None, "candidates": [], "message": "no results found"})]

    search_id = uuid.uuid4().hex[:12]
    settings = get_settings()
    settings.searches_dir.mkdir(parents=True, exist_ok=True)
    candidate_dicts = [vars(c) for c in candidates]
    payload = {"search_id": search_id, "query": query, "kind": kind, "candidates": candidate_dicts}
    (settings.searches_dir / f"{search_id}.json").write_text(json.dumps(payload, indent=2, default=str))

    grid = await sources.build_candidate_grid(candidates)
    grid_path = settings.searches_dir / f"{search_id}.jpg"
    await asyncio.to_thread(lambda: grid.convert("RGB").save(grid_path))

    return [
        json.dumps(
            {
                "search_id": search_id,
                "candidates": candidate_dicts,
                "hint": f'Use load_media(source="{search_id}:<number>") to fetch a candidate.',
            },
            indent=2,
            default=str,
        ),
        MCPImage(path=str(grid_path)),
    ]


@mcp.tool(structured_output=False)
async def load_media(
    source: str,
    start_sec: float | None = None,
    end_sec: float | None = None,
) -> list[Any]:
    """Load media by: an existing asset id (vid_.../img_...), "<search_id>:<number>" from
    search_media, a local file path, or any URL (YouTube/TikTok/Instagram/direct link/etc).
    Fetches are cached. For video, optionally trim to [start_sec, end_sec] (creates a child asset);
    returns the asset's id/metadata plus a preview image. Clips longer than 15s produce a warning
    since generation is slow and chunked. Use the returned asset id with inspect_media and (once
    available) detect_subjects/swap_subjects."""

    assets = get_assets()

    if _looks_like_asset_id(source):
        asset = assets.get(source)
        if asset is None:
            raise ToolError(f"No asset found with id {source!r}")
    else:
        resolved_source, candidate_meta = await _resolve_search_ref(source)
        local_path = Path(resolved_source).expanduser()
        if not _is_url(resolved_source) and local_path.is_file():
            try:
                local_path = check_local_media_path(local_path)
            except UnsafePathError as exc:
                raise ToolError(str(exc)) from exc
            kind: Literal["video", "image"] = "video" if _looks_like_video_path(local_path) else "image"
            asset = await asyncio.to_thread(
                assets.add,
                local_path,
                kind,
                origin={"source": str(local_path), **candidate_meta},
            )
        else:
            existing = assets.find_by_url(resolved_source) if _is_url(resolved_source) else None
            if existing is not None:
                asset = existing
            else:
                sources = _load_sources_backend()
                dest_dir = get_settings().videos_dir / "_fetched"
                try:
                    fetched = await sources.fetch(resolved_source, dest_dir)
                except sources.SourceError as exc:
                    raise ToolError(str(exc)) from exc
                origin = {
                    "source": source,
                    "url": fetched.source_url,
                    "provider": fetched.provider,
                    "title": fetched.title,
                    "uploader": fetched.uploader,
                    "license": fetched.license,
                    "description": fetched.description,
                    "subtitles_excerpt": fetched.subtitles_excerpt,
                    **candidate_meta,
                }
                # copy (not move): sources.fetch()'s own on-disk cache for this URL is keyed
                # to fetched.path, so moving it away would force a re-download next time.
                asset = await asyncio.to_thread(
                    assets.add, fetched.path, fetched.kind, origin=origin, move=False
                )

    warnings: list[str] = list(asset.meta.get("warnings", []))

    if asset.kind == "video" and (start_sec is not None or end_sec is not None):
        asset = await asyncio.to_thread(
            ingest.prepare_clip,
            asset.path,
            start_sec,
            end_sec,
            parent_ids=[asset.id],
            extra_origin={"trimmed_from": asset.id},
        )
        warnings = list(asset.meta.get("warnings", []))

    preview_path = asset.meta.get("preview_path") or (str(asset.path) if asset.kind == "image" else None)

    payload = asset.to_json()
    payload["warnings"] = warnings
    content: list[Any] = [json.dumps(payload, indent=2, default=str)]
    if preview_path:
        content.append(MCPImage(path=str(preview_path)))
    return content


@mcp.tool(structured_output=False)
async def inspect_media(asset_id: str, frames: int = 12) -> list[Any]:
    """Inspect a loaded asset without needing to attach the file again: returns metadata (duration,
    resolution, origin/title/uploader if fetched from a link), and for video a storyboard image
    (evenly spaced labeled frames) plus suggested trim segments (start, end, score, reason) from
    scene-cut detection, so you can pick a good range before calling load_media again with
    start_sec/end_sec."""

    assets = get_assets()
    asset = assets.get(asset_id)
    if asset is None:
        raise ToolError(f"No asset found with id {asset_id!r}")

    payload: dict[str, Any] = {
        "id": asset.id,
        "kind": asset.kind,
        "meta": asset.meta,
        "origin": asset.origin,
    }

    if asset.kind != "video":
        return [json.dumps(payload, indent=2, default=str), MCPImage(path=str(asset.path))]

    def _work() -> tuple[list[dict[str, Any]], Path]:
        segments = ingest.suggest_segments(asset.path)
        board = ingest.storyboard(asset.path, frames=frames)
        board_path = asset.path.parent / "storyboard.jpg"
        board.save(board_path)
        return segments, board_path

    segments, board_path = await asyncio.to_thread(_work)
    payload["suggested_segments"] = segments
    return [json.dumps(payload, indent=2, default=str), MCPImage(path=str(board_path))]


# --------------------------------------------------------------------------
# jobs / assets
# --------------------------------------------------------------------------


@mcp.tool(structured_output=False)
async def get_job(job_id: str) -> list[Any]:
    """Get a job's status: stage, progress (0-1), message, and on success its result (e.g. an
    output asset id) plus a preview image if one is available."""

    jobs = get_jobs()
    job = jobs.get(job_id)
    if job is None:
        raise ToolError(f"No job found with id {job_id!r}")
    content: list[Any] = [json.dumps(job.to_json(), indent=2)]
    if job.status == "succeeded" and job.result:
        preview_path = job.result.get("preview_path")
        if preview_path and Path(preview_path).is_file():
            content.append(MCPImage(path=preview_path))
    return content


@mcp.tool()
async def cancel_job(job_id: str) -> str:
    """Request cancellation of a queued or running job. Cancellation is cooperative and may take a
    moment to take effect."""

    jobs = get_jobs()
    return json.dumps({"cancelled": jobs.cancel(job_id)})


@mcp.tool()
async def list_jobs() -> str:
    """List all known jobs (queued/running/succeeded/failed/cancelled) with their current status."""

    jobs = get_jobs()
    return json.dumps([j.to_json() for j in jobs.list()], indent=2)


@mcp.tool()
async def list_assets(kind: Literal["video", "image"] | None = None) -> str:
    """List previously loaded/generated assets (optionally filtered to "video" or "image"), newest
    first. Use an asset's id with inspect_media or load_media."""

    assets = get_assets()
    return json.dumps([a.to_json() for a in assets.list(kind=kind)], indent=2, default=str)


# --------------------------------------------------------------------------
# Prompts
# --------------------------------------------------------------------------


_PLAN_FLOW = (
    "Recommended flow (it keeps every decision in one plan the user can check):\n"
    "1. plan_meme(intent=<the user's words>, video=<link/path/asset> or query=<song or idea>, "
    "photos=[...] or folder=<dir>, style=<optional, see list_styles>, length_sec=<optional>).\n"
    "   It picks the segment memes actually reuse, splits camera cuts, reframes to 9:16, sorts the "
    "photos into individuals (group photos are split), picks the best references, decides who "
    "becomes whom and writes the prompts.\n"
    "2. Show the user the plan: segment and why, performers -> identities (preview image), style, "
    "warnings (e.g. missing standing photo), and the time estimate. Look at the reference photos "
    "yourself and, if you can tell, re-run plan_meme with descriptions={'A': 'an Italian greyhound "
    "with a blue-grey coat'} for better prompts. If style_candidates has several entries, ask which "
    "look the user wants (e.g. pet_head_swap = only the head, pet_full_body = whole body).\n"
    "3. render_meme(plan_id, style=...) — optionally first with preview_seconds=5 to check quickly.\n"
    "4. get_job(job_id) until it succeeds; show the result. Every render is ONE video.\n"
    "Lower-level tools (search_media, inspect_media, detect_subjects, swap_subjects, ...) remain "
    "for fine control."
)


@mcp.prompt()
def swap_meme_from_text(idea: str) -> str:
    """Make a subject-swap meme video starting from just a text idea (no video/image attached)."""

    return (
        f"The user wants to make a meme video from this idea: {idea!r}\n"
        "If they haven't given photos of the replacement, ask for them, or use "
        "search_media(kind='image') and load_media to get some.\n\n" + _PLAN_FLOW
    )


@mcp.prompt()
def swap_meme_from_link(url: str, who: str) -> str:
    """Make a subject-swap meme video from a video link, replacing a subject described by `who`."""

    return (
        f"The user gave this video link: {url!r} and wants to replace someone with: {who!r}.\n"
        f"Use video={url!r} in plan_meme.\n\n" + _PLAN_FLOW
    )


@mcp.prompt()
def pet_dance_meme(song: str, photos_folder: str) -> str:
    """Turn the performers of a song's MV into your pets (head-only or full-body)."""

    return (
        f"The user wants the performers of {song!r} replaced by their pets; photos are in "
        f"{photos_folder!r} (unsorted, may include group photos).\n"
        f"Call plan_meme(intent=..., query={song!r}, folder={photos_folder!r}) and continue:\n\n" + _PLAN_FLOW
    )


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------

def _import_optional_tool_module(module_name: str) -> None:
    """Import an optional tool module for its @mcp.tool()/@mcp.prompt() side effects.

    A missing/broken optional module must not crash the server, but it must not
    fail silently either -- log the real exception at ERROR level so a typo or
    bad import doesn't quietly remove a whole tool.
    """

    try:
        __import__(module_name)
    except ImportError:
        logger.exception("could not import %s; its tools will not be registered", module_name)


# tools_swap.py adds detect_subjects/swap_subjects/make_swap_meme (ComfyUI
# recipes); tools_trend.py adds analyze_meme_usage; tools_plan.py adds the
# recommended plan_meme -> render_meme flow plus organize_photos/list_styles.
for _optional_module in ("make_meme.tools_trend", "make_meme.tools_swap", "make_meme.tools_plan"):
    _import_optional_tool_module(_optional_module)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
