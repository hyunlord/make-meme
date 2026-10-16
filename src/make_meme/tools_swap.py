"""MCP tools backed by ComfyUI recipes: detect_subjects, swap_subjects, make_swap_meme,
list_recipes. Imported by server.py, which owns the FastMCP instance."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import random
from pathlib import Path
from typing import Any, Literal

from mcp.server.fastmcp import Image as MCPImage
from mcp.server.fastmcp.exceptions import ToolError
from PIL import Image
from pydantic import BaseModel, Field

from make_meme import ingest, post
from make_meme.assets import Asset
from make_meme.comfy.client import ComfyError
from make_meme.comfy.validate import check_recipe
from make_meme.config import get_settings
from make_meme.jobs import JobContext
from make_meme.pipelines.detect import DEFAULT_QUERY, Subject, annotate, detect_in_image
from make_meme.pipelines.runtime import comfy_session, hardware_profile, object_info
from make_meme.pipelines.swap import SwapMapping, SwapPlan, chunk_len_for, run_swap
from make_meme.recipes.loader import RecipeError, all_recipes, get_recipe, recipes_of_kind
from make_meme.server import extra_checks, get_assets, get_jobs, load_media, mcp

logger = logging.getLogger(__name__)

# engine name exposed to the LLM -> recipe. Add entries as swap recipes land.
ENGINES = {"mocha": "mocha_swap"}


class Mapping(BaseModel):
    subject: int | str = Field(
        description="Subject number from detect_subjects, or a short phrase to find it (e.g. 'the dog', 'man in red')."
    )
    images: list[str] = Field(
        min_length=1,
        description="Image asset ids or local paths of the replacement. 1st = full body/clear shot; "
        "optional 2nd = face close-up (improves identity). More than 2 are ignored.",
    )
    prompt: str | None = Field(default=None, description="Extra direction for this subject only.")


def _video_asset(ref: str) -> Asset:
    asset = get_assets().get(ref)
    if asset is None:
        raise ToolError(f"No asset {ref!r}. Load the video first with load_media.")
    if asset.kind != "video":
        raise ToolError(f"{ref} is an image; swap_subjects needs a video asset.")
    return asset


def _image_path(ref: str) -> Path:
    asset = get_assets().get(ref)
    if asset is not None:
        if asset.kind != "image":
            raise ToolError(f"{ref} is a video; reference images must be photos.")
        return asset.path
    p = Path(ref).expanduser()
    if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".bmp"}:
        return p
    raise ToolError(f"Reference image {ref!r} not found (use an image asset id from load_media or a file path).")


def _subjects_file(asset: Asset, at_sec: float, query: str) -> Path:
    key = f"{at_sec:.2f}_{hashlib.sha1(query.encode()).hexdigest()[:10]}"
    return asset.path.parent / "subjects" / key / "subjects.json"


async def _detect(asset: Asset, at_sec: float, query: str) -> tuple[list[Subject], Path]:
    cache = _subjects_file(asset, at_sec, query)
    frame_path = cache.parent / "frame.png"
    if cache.is_file():
        return [Subject.from_json(d) for d in json.loads(cache.read_text())], frame_path
    cache.parent.mkdir(parents=True, exist_ok=True)
    frame = await asyncio.to_thread(ingest.extract_frame, asset.path, at_sec)
    frame.save(frame_path)
    try:
        async with comfy_session() as client:
            profile = await hardware_profile(client)
            subjects = await detect_in_image(client, frame_path, query, cache.parent, profile=profile)
    except (ComfyError, RecipeError) as e:
        raise ToolError(str(e)) from e
    cache.write_text(json.dumps([s.to_json() for s in subjects], indent=2))
    # remember the default detection for swap_subjects
    if at_sec == 0.0:
        asset.meta.setdefault("subjects_files", {})[query] = str(cache)
        asset.save(asset.path.parent)
    return subjects, frame_path


@mcp.tool()
async def detect_subjects(video: str, query: str = DEFAULT_QUERY, at_sec: float = 0.0) -> list[Any]:
    """Find people/animals in a video's frame (default: first frame, which is what swapping
    uses) and return them numbered 1..n (largest first) with boxes, plus an annotated image.
    `query` is comma-separated short phrases, e.g. "person", "dog, cat", "man in red jacket".
    Pass the numbers to swap_subjects. Requires ComfyUI (see check_setup)."""
    asset = _video_asset(video)
    subjects, frame_path = await _detect(asset, at_sec, query)
    annotated_path = frame_path.with_name("annotated.jpg")
    with Image.open(frame_path) as frame:
        await asyncio.to_thread(lambda: annotate(frame, subjects).save(annotated_path, quality=90))
    payload = {
        "video": asset.id,
        "at_sec": at_sec,
        "subjects": [{"subject": s.id, "label": s.label, "score": s.score, "bbox": list(s.bbox)} for s in subjects],
    }
    if not subjects:
        payload["hint"] = "Nothing found; try another query (e.g. 'singer', 'dancer') or a different at_sec."
    return [json.dumps(payload, indent=2), MCPImage(path=str(annotated_path))]


async def _resolve_mapping(asset: Asset, m: Mapping) -> SwapMapping:
    images = [_image_path(r) for r in m.images]
    if isinstance(m.subject, int) or (isinstance(m.subject, str) and m.subject.strip().isdigit()):
        sid = int(m.subject)
        match = None
        # prefer the detection the user actually looked at (most recent query first)
        for path in reversed(list((asset.meta.get("subjects_files") or {}).values())):
            if Path(path).is_file():
                seen = [Subject.from_json(d) for d in json.loads(Path(path).read_text())]
                match = next((s for s in seen if s.id == sid), None)
                if match is not None:
                    break
        if match is None:
            subjects, _ = await _detect(asset, 0.0, DEFAULT_QUERY)
            match = next((s for s in subjects if s.id == sid), None)
        if match is None:
            raise ToolError(f"Subject {sid} not found on the first frame; run detect_subjects to see the numbers.")
    else:
        subjects, _ = await _detect(asset, 0.0, f"{m.subject}:3")
        if not subjects:
            raise ToolError(f"Couldn't find {m.subject!r} on the first frame; try detect_subjects with another query.")
        match = max(subjects, key=lambda s: (s.score, s.area))
    return SwapMapping(subject=match, images=images, prompt=m.prompt)


def _submit_swap(
    asset: Asset,
    mappings: list[SwapMapping],
    *,
    engine: str,
    quality: str,
    prompt: str | None,
    negative_prompt: str | None,
    seed: int,
    keep_audio: bool,
    interpolate: bool,
    label: str,
) -> dict[str, Any]:
    recipe = get_recipe(ENGINES[engine])
    settings = get_settings()

    async def job(ctx: JobContext) -> dict[str, Any]:
        work = settings.outputs_dir / ctx.job_id
        work.mkdir(parents=True, exist_ok=True)

        async def report(stage: str, progress: float, message: str) -> None:
            ctx.update(stage=stage, progress=progress * 0.95, message=message)

        async with comfy_session() as client:
            profile = await hardware_profile(client)
            plan = SwapPlan(
                video_path=asset.path,
                source_size=(int(asset.meta.get("width", 0)) or 1, int(asset.meta.get("height", 0)) or 1),
                mappings=mappings, recipe=recipe, profile=profile, quality=quality, prompt=prompt,
                negative_prompt=negative_prompt, seed=seed, work_dir=work / "work",
            )
            silent = await run_swap(client, plan, report=report, cancelled=ctx.cancelled)

        ctx.update(stage="finishing", progress=0.96, message="interpolating / adding audio")
        final = silent
        if interpolate:
            final = await post.retime(final, 30, work / "interp.mp4")
        audio = asset.meta.get("audio_path")
        out = settings.outputs_dir / f"{ctx.job_id}.mp4"
        if keep_audio and audio and Path(audio).is_file():
            await post.mux_audio(final, Path(audio), out)
        else:
            await post._run(["ffmpeg", "-y", "-i", str(final), "-c", "copy",
                             "-metadata", f"comment={post.AI_GENERATED_COMMENT}", str(out)])
        result_asset = await asyncio.to_thread(
            get_assets().add, out, "video",
            origin={"recipe": recipe.name, "job_id": ctx.job_id, "prompt": prompt, "seed": seed,
                    "mappings": [{"subject": m.subject.id, "label": m.subject.label,
                                  "images": [str(p) for p in m.images], "prompt": m.prompt} for m in mappings]},
            parent_ids=[asset.id],
        )
        preview = await post.make_preview(result_asset.path, result_asset.path.parent / "preview.jpg")
        return {"asset_id": result_asset.id, "path": str(result_asset.path), "preview_path": str(preview),
                "seed": seed, "label": label}

    job_obj = get_jobs().submit(f"swap:{recipe.name}", job)
    return {"job_id": job_obj.id, "seed": seed, "label": label}


def _estimate(asset: Asset, n_mappings: int, recipe_name: str) -> dict[str, Any]:
    recipe = get_recipe(recipe_name)
    frames = round(float(asset.meta.get("duration", 0)) * int(recipe.constraints.get("fps", 16)))
    chunks = max(1, -(-frames // (chunk_len_for(recipe) - 1)))
    return {"frames": frames, "chunks": chunks, "passes": n_mappings * chunks}


@mcp.tool()
async def swap_subjects(
    video: str,
    mappings: list[Mapping],
    prompt: str | None = None,
    engine: Literal["mocha"] = "mocha",
    quality: Literal["draft", "high"] = "draft",
    variations: int = 1,
    seed: int | None = None,
    keep_audio: bool = True,
    interpolate: bool = False,
    negative_prompt: str | None = None,
) -> str:
    """Replace subjects in a video with the people/animals in reference photos. Starts a
    background job (minutes to tens of minutes) and returns job ids; poll get_job.

    - mappings: one entry per subject to replace, e.g.
      [{"subject": 1, "images": ["img_ab12", "img_cd34"]}, {"subject": "the dog", "images": ["img_ef56"]}]
    - prompt: optional direction for the result ("wearing sunglasses, energetic dance").
    - engine: "mocha" (keeps the original performance; works for animals).
    - variations: generate N versions with different seeds to pick from (each is a job).
    - keep_audio: put the original soundtrack back. interpolate: 16→30 fps smoothing.
    Use a short clip (≤ 5 s is one chunk; longer clips run in several chunks)."""
    if engine not in ENGINES or ENGINES[engine] not in all_recipes():
        raise ToolError(f"Engine {engine!r} is not available. Available: "
                        f"{[e for e, r in ENGINES.items() if r in all_recipes()]}")
    if not 1 <= variations <= 4:
        raise ToolError("variations must be between 1 and 4.")
    asset = _video_asset(video)
    resolved = [await _resolve_mapping(asset, m) for m in mappings]
    base_seed = seed if seed is not None else random.randint(0, 2**31 - 1)
    jobs = [
        _submit_swap(asset, resolved, engine=engine, quality=quality, prompt=prompt,
                     negative_prompt=negative_prompt, seed=base_seed + i, keep_audio=keep_audio,
                     interpolate=interpolate, label=f"variation {i + 1}/{variations}")
        for i in range(variations)
    ]
    return json.dumps({
        "jobs": jobs,
        "subjects": [{"subject": m.subject.id, "label": m.subject.label, "bbox": list(m.subject.bbox),
                      "reference_images": [str(p) for p in m.images[:2]]} for m in resolved],
        "estimate": _estimate(asset, len(resolved), ENGINES[engine]),
        "next": "Call get_job(job_id) every minute or so until status is 'succeeded'.",
    }, indent=2)


@mcp.tool()
async def make_swap_meme(
    video: str | None = None,
    images: list[str] | None = None,
    video_query: str | None = None,
    image_query: str | None = None,
    prompt: str | None = None,
    start_sec: float | None = None,
    end_sec: float | None = None,
    target: str | None = None,
    engine: Literal["mocha"] = "mocha",
    quality: Literal["draft", "high"] = "draft",
) -> str:
    """One-shot meme: works from links/files OR from text alone.
    - video: asset id, path or link (YouTube/TikTok/Instagram/Threads/...); or video_query to search.
    - images: asset ids/paths/links of the replacement; or image_query to search photos.
    - target: which subject to replace (phrase like "the singer"); default = the largest subject.
    - If no start/end is given, the top suggested ~5 s segment is used.
    Returns a job id plus what was chosen; poll get_job. For more control use
    search_media → load_media → inspect_media → detect_subjects → swap_subjects."""
    if not (video or video_query):
        raise ToolError("Give a video (id/path/link) or a video_query to search for one.")
    if not (images or image_query):
        raise ToolError("Give reference images (ids/paths/links) or an image_query to search for photos.")
    from make_meme.server import search_media  # local import: avoid cycles at import time

    chosen: dict[str, Any] = {}
    if video is None:
        res = json.loads((await search_media(video_query, kind="video", n=5))[0])
        if not res["candidates"]:
            raise ToolError(f"No videos found for {video_query!r}.")
        video = f"{res['search_id']}:1"
        chosen["video_search"] = {"query": video_query, "picked": res["candidates"][0]}
    src = json.loads((await load_media(video))[0])
    src_asset = get_assets().get(src["id"])
    if start_sec is None and end_sec is None and float(src_asset.meta.get("duration", 0)) > 6:
        segs = await asyncio.to_thread(ingest.suggest_segments, src_asset.path, 5.0, 3)
        if segs:
            start_sec, end_sec = segs[0]["start"], segs[0]["end"]
            chosen["segment"] = segs[0]
    if start_sec is not None or end_sec is not None:
        src = json.loads((await load_media(src_asset.id, start_sec, end_sec))[0])

    image_ids: list[str] = []
    if images:
        for ref in images:
            image_ids.append(json.loads((await load_media(ref))[0])["id"])
    else:
        res = json.loads((await search_media(image_query, kind="image", n=6))[0])
        for cand in res["candidates"][:2]:
            try:
                image_ids.append(json.loads((await load_media(f"{res['search_id']}:{cand['index']}"))[0])["id"])
            except ToolError as e:
                logger.info("skipping image candidate %s: %s", cand.get("index"), e)
        if not image_ids:
            raise ToolError(f"Couldn't download any image for {image_query!r}; pass images explicitly.")
        chosen["image_search"] = {"query": image_query, "picked": image_ids}

    subject: int | str = target if target else 1
    result = json.loads(await swap_subjects(
        src["id"], [Mapping(subject=subject, images=image_ids)], prompt=prompt, engine=engine, quality=quality,
    ))
    result["chosen"] = {"video_asset": src["id"], "images": image_ids, **chosen}
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
async def list_recipes() -> str:
    """List generation recipes (engines) and whether the connected ComfyUI can run them now."""
    out = []
    try:
        async with comfy_session() as client:
            profile = await hardware_profile(client)
            info = await object_info(client, refresh=True)
            for r in all_recipes().values():
                out.append({"name": r.name, "kind": r.kind, "title": r.title, "description": r.description,
                            **check_recipe(r, info, profile).summary()})
    except ComfyError as e:
        return json.dumps({"comfyui": str(e), "recipes": [{"name": r.name, "kind": r.kind, "title": r.title}
                                                          for r in all_recipes().values()]}, indent=2)
    return json.dumps(out, indent=2)


async def _recipes_check() -> dict[str, Any]:
    try:
        async with comfy_session() as client:
            profile = await hardware_profile(client)
            info = await object_info(client, refresh=True)
            return {"recipes": [check_recipe(r, info, profile).summary() for r in recipes_of_kind("swap")
                                + recipes_of_kind("detect")], "profile": profile}
    except ComfyError as e:
        return {"recipes": "skipped", "reason": str(e)}


extra_checks.append(_recipes_check)
