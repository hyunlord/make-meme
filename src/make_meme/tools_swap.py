"""MCP tools backed by ComfyUI recipes: detect_subjects, swap_subjects, make_swap_meme,
list_recipes. Imported by server.py, which owns the FastMCP instance."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import random
from pathlib import Path
from typing import Annotated, Any, Literal

from mcp.server.fastmcp import Image as MCPImage
from mcp.server.fastmcp.exceptions import ToolError
from PIL import Image
from pydantic import BaseModel, Field

from make_meme import ingest, post
from make_meme.assets import Asset
from make_meme.chunking import plan_chunks
from make_meme.comfy.client import ComfyError
from make_meme.comfy.validate import check_recipe
from make_meme.config import get_settings
from make_meme.jobs import JobContext
from make_meme.pipelines.detect import DEFAULT_QUERY, Subject, annotate, detect_in_image, iou
from make_meme.pipelines.runtime import comfy_session, hardware_profile, object_info
from make_meme.pipelines.swap import SwapMapping, SwapPlan, chunk_len_for, run_swap
from make_meme.recipes.loader import RecipeError, all_recipes, get_recipe, recipes_of_kind
from make_meme.safety import UnsafePathError, check_local_media_path
from make_meme.server import extra_checks, get_assets, get_jobs, load_media, mcp

logger = logging.getLogger(__name__)

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".heic", ".heif", ".avif", ".tif", ".tiff"}

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
    if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES:
        try:
            p = check_local_media_path(p)
        except UnsafePathError as e:
            raise ToolError(str(e)) from e
        # register it so phone formats (HEIC) are converted and EXIF rotation is applied;
        # reuse the earlier registration of the same unchanged file instead of duplicating it
        st = p.stat()
        stamp = f"{st.st_size}:{st.st_mtime_ns}"
        store = get_assets()
        for existing in store.list("image", limit=None):
            same = existing.origin.get("source") == str(p) and existing.origin.get("stamp") == stamp
            if same and existing.path.is_file():
                return existing.path
        return store.add(p, "image", origin={"source": str(p), "stamp": stamp}).path
    raise ToolError(f"Reference image {ref!r} not found (use an image asset id from load_media or a file path).")


def _subjects_file(asset: Asset, at_sec: float, query: str) -> Path:
    key = f"{at_sec:.2f}_{hashlib.sha1(query.encode()).hexdigest()[:10]}"
    return asset.path.parent / "subjects" / key / "subjects.json"


async def _detect(asset: Asset, at_sec: float, query: str) -> tuple[list[Subject], Path]:
    duration = float(asset.meta.get("duration") or 0)
    if at_sec < 0 or (duration and at_sec >= duration):
        raise ToolError(f"at_sec must be between 0 and {duration:.2f} (the clip length).")
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
    return subjects, frame_path


def _pin_detection(asset: Asset, at_sec: float, query: str) -> None:
    """Remember which detection the caller last *saw*, so subject numbers passed to
    swap_subjects mean exactly what was shown."""
    asset.meta["last_detection"] = {"file": str(_subjects_file(asset, at_sec, query)), "at_sec": at_sec,
                                    "query": query}
    asset.save(asset.path.parent)


@mcp.tool(structured_output=False)
async def detect_subjects(video: str, query: str = DEFAULT_QUERY, at_sec: float = 0.0) -> list[Any]:
    """Find people/animals in a video's frame (default: first frame, which is what swapping
    uses) and return them numbered 1..n (largest first) with boxes, plus an annotated image.
    `query` is comma-separated short phrases, e.g. "person", "dog, cat", "man in red jacket".
    Pass the numbers to swap_subjects (numbers always refer to your latest detect_subjects
    call with at_sec=0). Requires ComfyUI (see check_setup)."""
    asset = _video_asset(video)
    subjects, frame_path = await _detect(asset, at_sec, query)
    _pin_detection(asset, at_sec, query)
    annotated_path = frame_path.with_name("annotated.jpg")
    with Image.open(frame_path) as frame:
        await asyncio.to_thread(lambda: annotate(frame, subjects).save(annotated_path, quality=90))
    payload: dict[str, Any] = {
        "video": asset.id,
        "at_sec": at_sec,
        "subjects": [{"subject": s.id, "label": s.label, "score": s.score, "bbox": list(s.bbox)} for s in subjects],
    }
    if not subjects:
        payload["hint"] = "Nothing found; try another query (e.g. 'singer', 'dancer') or a different at_sec."
    if at_sec != 0.0:
        payload["note"] = ("Swapping locates subjects on the first frame; to use these numbers in "
                           "swap_subjects run detect_subjects again with at_sec=0 (or trim the clip to start here).")
    return [json.dumps(payload, indent=2), MCPImage(path=str(annotated_path))]


async def _resolve_mapping(asset: Asset, m: Mapping) -> SwapMapping:
    images = [_image_path(r) for r in m.images]
    if isinstance(m.subject, int) or (isinstance(m.subject, str) and m.subject.strip().isdigit()):
        sid = int(m.subject)
        pinned = asset.meta.get("last_detection") or {}
        if pinned and float(pinned.get("at_sec", 0.0)) != 0.0:
            raise ToolError(
                f"Your last detect_subjects was at at_sec={pinned['at_sec']}, but swapping uses the first frame. "
                "Run detect_subjects(at_sec=0) and use those numbers."
            )
        if pinned and Path(pinned["file"]).is_file():
            subjects = [Subject.from_json(d) for d in json.loads(Path(pinned["file"]).read_text())]
        else:
            subjects, _ = await _detect(asset, 0.0, DEFAULT_QUERY)
            _pin_detection(asset, 0.0, DEFAULT_QUERY)
        match = next((s for s in subjects if s.id == sid), None)
        if match is None:
            raise ToolError(f"Subject {sid} not found on the first frame; run detect_subjects to see the numbers.")
    else:
        # phrase lookups don't change the pinned numbering
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
        if not audio and asset.meta.get("has_audio"):
            audio = str(asset.path)  # untrimmed asset: take the soundtrack straight from the source
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
    chunks = max(1, len(plan_chunks(max(1, frames), chunk_len=chunk_len_for(recipe), overlap=1)))
    return {"frames": frames, "chunks": chunks, "passes": n_mappings * chunks}


@mcp.tool()
async def swap_subjects(
    video: str,
    mappings: Annotated[list[Mapping], Field(min_length=1)],
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

    - mappings: one entry per subject to replace — all of them are applied to the SAME
      output video (e.g. two dogs for the two dancers = one video with both dogs).
      Unsure which photo goes where? Call suggest_mappings first. Example:
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
    for i, a in enumerate(resolved):
        for b in resolved[i + 1:]:
            if iou(a.subject.bbox, b.subject.bbox) > 0.7:
                raise ToolError(
                    f"Two mappings point at the same subject ({a.subject.label} at {list(a.subject.bbox)}); "
                    "use distinct subject numbers from detect_subjects."
                )
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
        "output": (f"each job renders ONE video with all {len(resolved)} replacement(s) applied in sequence"
                   + (f"; {variations} jobs = {variations} alternative versions" if variations > 1 else "")),
        "estimate": _estimate(asset, len(resolved), ENGINES[engine]),
        "next": "Call get_job(job_id) every minute or so until status is 'succeeded'.",
    }, indent=2)


async def _plan_assignment(asset: Asset, image_paths: list[Path], images_are: str, query: str = DEFAULT_QUERY):
    """Shared by suggest_mappings and make_swap_meme: which subject gets which photos."""
    from make_meme.pipelines.assign import assign

    subjects, frame_path = await _detect(asset, 0.0, query)
    _pin_detection(asset, 0.0, query)
    try:
        async with comfy_session() as client:
            profile = await hardware_profile(client)
            with Image.open(frame_path) as frame:
                plan = await assign(client, image_paths, subjects, frame.copy(), profile=profile,
                                    images_are=images_are)
    except ValueError as e:
        raise ToolError(str(e)) from e
    except (ComfyError, RecipeError) as e:
        raise ToolError(str(e)) from e
    return plan, subjects, frame_path


ImagesAre = Literal["auto", "same_subject", "different_subjects"]


@mcp.tool(structured_output=False)
async def suggest_mappings(video: str, images: list[str], images_are: ImagesAre = "auto") -> list[Any]:
    """Propose which on-screen subject each reference photo should replace, before a long
    swap. Several photos may be angles of ONE replacement (full body + face of my dog) or
    one photo per DIFFERENT replacement (dog A for the left dancer, dog B for the right);
    'auto' decides from what the photos show (person/animal + colours) and pairs different
    replacements with the subjects that look most alike (hair vs fur colour). The swap
    always produces ONE video containing every replacement. Returns the proposed
    `mappings` (pass them to swap_subjects, adjusted if the user wants), the reasoning,
    and an annotated frame. Use images_are to override the guess."""
    asset = _video_asset(video)
    paths = [_image_path(r) for r in images]
    plan, subjects, frame_path = await _plan_assignment(asset, paths, images_are)
    by_id = {s.id: s for s in subjects}
    mappings = [{"subject": sid, "images": [images[i] for i in idx]} for sid, idx in plan.mappings]
    annotated = frame_path.with_name("annotated_plan.jpg")
    with Image.open(frame_path) as frame:
        chosen = [by_id[sid] for sid, _ in plan.mappings]
        await asyncio.to_thread(lambda: annotate(frame, chosen).save(annotated, quality=90))
    payload = {
        "video": asset.id,
        "mappings": mappings,
        "explanation": plan.reasons,
        "subjects_on_screen": [{"subject": s.id, "label": s.label, "bbox": list(s.bbox)} for s in subjects],
        "output": "one video with all replacements applied",
    }
    return [json.dumps(payload, indent=2, ensure_ascii=False), MCPImage(path=str(annotated))]


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
    images_are: ImagesAre = "auto",
) -> str:
    """One-shot meme: works from links/files OR from text alone. Produces ONE video.
    - video: asset id, path or link (YouTube/TikTok/Instagram/Threads/...); or video_query to search.
    - images: asset ids/paths/links of the replacement(s); or image_query to search photos.
      Several images are either angles of one replacement or one photo per different
      replacement (e.g. two dogs for two dancers); images_are='auto' decides from the
      photos and maps each different replacement to its own on-screen subject.
    - target: which subject to replace when there is one replacement (phrase like "the singer");
      default = the largest subject.
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

    clip = get_assets().get(src["id"])
    if target and len(image_ids) > 1 and images_are != "different_subjects":
        maps = [Mapping(subject=target, images=image_ids)]
        chosen["assignment"] = [f"all photos -> {target!r} (target given)"]
    elif target or len(image_ids) == 1:
        maps = [Mapping(subject=target or 1, images=image_ids)]
        chosen["assignment"] = ["one replacement -> " + (repr(target) if target else "the largest subject")]
    else:
        plan, _, _ = await _plan_assignment(clip, [_image_path(i) for i in image_ids], images_are)
        maps = [Mapping(subject=sid, images=[image_ids[i] for i in idx]) for sid, idx in plan.mappings]
        chosen["assignment"] = plan.reasons
    result = json.loads(await swap_subjects(src["id"], maps, prompt=prompt, engine=engine, quality=quality))
    result["chosen"] = {"video_asset": src["id"], "images": image_ids,
                        "mappings": [m.model_dump() for m in maps], **chosen}
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


@mcp.tool(structured_output=False)
async def reframe_video(video: str, aspect: str = "9:16", query: str = "person, animal") -> list[Any]:
    """Re-crop a clip to another aspect ratio (default vertical 9:16 for Shorts/Reels/TikTok)
    with a camera pan that follows the subjects (found with SAM 3 about once per second).
    Use it before swap_subjects when the people are small in a wide shot: they fill more
    of the frame, which gives the swap far more detail. Returns a new video asset (audio
    kept) plus a preview; `all_subjects_fit` is false if they spread wider than the crop."""
    from make_meme.pipelines.reframe import parse_aspect, reframe

    asset = _video_asset(video)
    try:
        parse_aspect(aspect)
    except ValueError as e:
        raise ToolError(str(e)) from e
    out = asset.path.parent / f"reframed_{aspect.replace(':', 'x')}.mp4"
    try:
        async with comfy_session() as client:
            profile = await hardware_profile(client)
            path, plan, fits = await reframe(client, asset.path, out, aspect=aspect, query=query, profile=profile)
    except (ComfyError, RecipeError) as e:
        raise ToolError(str(e)) from e
    meta = {}
    if asset.meta.get("audio_path"):
        meta["audio_path"] = asset.meta["audio_path"]
    new = await asyncio.to_thread(
        get_assets().add, path, "video", origin={"reframed_from": asset.id, "aspect": aspect, "crop_path": plan},
        meta=meta, parent_ids=[asset.id],
    )
    payload = {"asset_id": new.id, "width": new.meta.get("width"), "height": new.meta.get("height"),
               "duration": new.meta.get("duration"), "all_subjects_fit": fits, "pan_keyframes": len(plan)}
    content: list[Any] = [json.dumps(payload, indent=2)]
    if new.meta.get("preview_path"):
        content.append(MCPImage(path=new.meta["preview_path"]))
    return content
