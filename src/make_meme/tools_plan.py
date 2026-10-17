"""High-level meme tools: organize_photos, plan_meme, render_meme, list_styles.

Recommended flow for any MCP client:
  plan_meme(...)  -> show the plan (segment, shots, who becomes whom, style, prompts,
                     estimate, warnings) to the user and let them adjust
  render_meme(plan_id, ...) -> one job -> ONE video
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
from pathlib import Path
from typing import Any, Literal

import numpy as np
from mcp.server.fastmcp import Image as MCPImage
from mcp.server.fastmcp.exceptions import ToolError
from PIL import Image, ImageDraw

from make_meme import post
from make_meme.comfy.client import ComfyError
from make_meme.config import get_settings
from make_meme.jobs import JobContext
from make_meme.pipelines.assign import subject_head_hist
from make_meme.pipelines.detect import _font
from make_meme.pipelines.render import cast_identities, reframe_by_shots, render_plan
from make_meme.pipelines.runtime import comfy_session, hardware_profile
from make_meme.pipelines.shots import Shot, analyze_shots, main_shot
from make_meme.plan import IdentityRef, MemePlan, load_plan, new_plan_id, save_plan
from make_meme.recipes.loader import RecipeError, get_recipe
from make_meme.server import _load_sources_backend, get_assets, get_jobs, load_media, mcp
from make_meme.styles import StyleError, all_styles, get_style, guess_style
from make_meme.tools_swap import IMAGE_SUFFIXES, _image_path

logger = logging.getLogger(__name__)

Aspect = Literal["9:16", "16:9", "1:1", "4:5", "source"]


def _collect_photos(photos: list[str] | None, folder: str | None) -> list[Path]:
    paths: list[Path] = []
    for ref in photos or []:
        paths.append(_image_path(ref))
    if folder:
        d = Path(folder).expanduser()
        if not d.is_dir():
            raise ToolError(f"Folder {folder!r} not found.")
        for f in sorted(d.iterdir()):
            if f.is_file() and f.suffix.lower() in IMAGE_SUFFIXES and not f.name.startswith("."):
                paths.append(_image_path(str(f)))
    if not paths:
        raise ToolError("Give `photos` (asset ids/paths) or a `folder` of photos of the replacement(s).")
    return paths


def _identity_ref(ident: Any) -> IdentityRef:
    heads = [i for i in ident.instances if getattr(i, "head_path", None)]
    head_alt = next((i.head_path for i in heads if ident.ref_head is None or i is not ident.ref_head), None)
    full_alt = next((i.crop_path for i in ident.instances if i is not ident.ref_full), None)
    return IdentityRef(
        id=ident.id, label=ident.label, description=ident.description, coat=ident.coat,
        photos=len({str(i.photo) for i in ident.instances}), confidence=round(float(ident.confidence), 2),
        ref_full=str(ident.ref_full.crop_path) if ident.ref_full else None,
        ref_head=str(ident.ref_head.head_path) if ident.ref_head and ident.ref_head.head_path else None,
        ref_head_alt=str(head_alt) if head_alt else None, ref_full_alt=str(full_alt) if full_alt else None,
        advice=list(ident.advice),
    )


async def _organize(client, paths: list[Path], out_dir: Path, profile: str):
    from make_meme.pipelines import photos as photos_mod

    identities = await photos_mod.organize_photos(client, paths, out_dir, profile=profile)
    sheet = out_dir / "contact_sheet.jpg"
    await asyncio.to_thread(lambda: photos_mod.contact_sheet(identities).convert("RGB").save(sheet, quality=88))
    return identities, sheet


@mcp.tool(structured_output=False)
async def organize_photos(photos: list[str] | None = None, folder: str | None = None) -> list[Any]:
    """Sort an unsorted pile of photos into the individual people/animals they show
    (group photos are split into each subject), pick the best two references per
    individual (full body + head close-up — the swap model takes at most two, so extra
    photos help by giving better choices), describe each one, and say what photo would
    improve results. Returns identities A, B, ... and a contact sheet image. plan_meme
    does this automatically; call it directly to inspect or before choosing a style."""
    paths = _collect_photos(photos, folder)
    out_dir = get_settings().home / "photo_sets" / f"set_{random.getrandbits(32):08x}"
    try:
        async with comfy_session() as client:
            profile = await hardware_profile(client)
            identities, sheet = await _organize(client, paths, out_dir, profile)
    except (ComfyError, RecipeError) as e:
        raise ToolError(str(e)) from e
    payload = {"photos": len(paths), "identities": [i.to_json() for i in identities],
               "note": "Describe each identity (breed, name) yourself if you can see the photos; pass it as "
                       "`descriptions` to plan_meme for better prompts."}
    return [json.dumps(payload, indent=2, ensure_ascii=False, default=str), MCPImage(path=str(sheet))]


@mcp.tool()
async def list_styles() -> str:
    """List meme styles (how the replacement is done: e.g. pet_head_swap = only the head
    becomes the pet, pet_full_body = the whole body becomes the pet)."""
    return json.dumps([s.summary() for s in all_styles().values()], indent=2, ensure_ascii=False)


def _preview(plan: MemePlan, shots: list[Shot], identities: list[IdentityRef]) -> Path:
    main = main_shot(shots)
    frame = Image.open(main.frame_path).convert("RGB")
    frame.thumbnail((720, 720))
    sx = frame.width / Image.open(main.frame_path).width
    thumbs = []
    for ident in identities:
        src = ident.ref_head or ident.ref_full
        if src:
            t = Image.open(src).convert("RGB")
            t.thumbnail((160, 160))
            thumbs.append((ident.id, t))
    canvas = Image.new("RGB", (frame.width + 190, max(frame.height, 190 * max(1, len(thumbs)))), (24, 24, 24))
    canvas.paste(frame, (0, 0))
    d = ImageDraw.Draw(canvas)
    font = _font(22)
    by_perf = {p: s for p, s in main.performers.items()}
    for pid, sid in by_perf.items():
        subj = next(s for s in main.subjects if s.id == sid)
        x1, y1, x2, y2 = (int(v * sx) for v in subj.bbox)
        d.rectangle([x1, y1, x2, y2], outline=(255, 200, 0), width=3)
        tag = f"{pid}→{plan.cast.get(pid, '-')}"
        d.rectangle([x1, y1, x1 + 12 + d.textlength(tag, font=font), y1 + 30], fill=(255, 200, 0))
        d.text((x1 + 6, y1 + 3), tag, font=font, fill=(0, 0, 0))
    for k, (iid, t) in enumerate(thumbs):
        canvas.paste(t, (frame.width + 15, 15 + 190 * k))
        d.text((frame.width + 15, 15 + 190 * k + t.height + 2), iid, font=font, fill=(255, 255, 255))
    out = get_settings().home / "plans" / f"{plan.id}_preview.jpg"
    canvas.save(out, quality=88)
    return out


def _estimate(plan: MemePlan, shots: list[Shot], profile: str, width: int, height: int, steps: int) -> dict:
    from make_meme.chunking import plan_chunks
    from make_meme.pipelines.swap import chunk_len_for

    try:
        from make_meme.perf import estimate_seconds
    except ImportError:
        estimate_seconds = None
    total, basis = 0.0, "unknown"
    for shot in shots:
        n = sum(1 for pid in plan.cast if pid in shot.performers)
        if not n:
            continue
        frames = max(1, round(shot.duration * 16))
        for ch in plan_chunks(frames, chunk_len=chunk_len_for(get_recipe("mocha_swap"), profile), overlap=1):
            length = ch.end - ch.start + ch.pad
            if estimate_seconds is not None:
                est = estimate_seconds(profile, "mocha_swap", width, height, length, steps)
                total += n * float(est["seconds"])
                basis = est.get("basis", basis)
    return {"seconds": round(total), "minutes": round(total / 60, 1), "basis": basis, "profile": profile}


# Measured on an M4 Max: SAM 3 text tracking at 540 px wide ~1.9 s per tracked frame; every
# other frame is tracked, one run per shot for all performers, plus ~10 s per shot overhead.
PASTE_SEC_PER_FRAME = 0.95
PASTE_SEC_PER_SHOT = 10.0


def _refresh_estimate(plan: MemePlan, style) -> None:
    """(Re-)estimate for `style`: at plan time, and again at render time since perf.jsonl
    may have gained samples and preview/quality/cast overrides change the work."""
    est = plan.estimate or {}
    profile = est.get("profile")
    clip_size = est.get("clip_size") or est.get("output_size")
    if not profile or not clip_size:
        return
    clip_size = (int(clip_size[0]), int(clip_size[1]))
    shots = [Shot.from_json(s) for s in plan.shots]
    base = {"profile": profile, "clip_size": list(clip_size), "quality": plan.quality, "engine": style.engine}
    if style.engine == "paste":
        busy = [s for s in shots if any(p in s.performers for p in plan.cast)]
        seconds = 15 + sum(PASTE_SEC_PER_SHOT + round(s.duration * 24) * PASTE_SEC_PER_FRAME for s in busy)
        plan.estimate = {**base, "seconds": round(seconds), "minutes": round(seconds / 60, 1),
                         "basis": "default-guess", "output_size": list(clip_size)}
        return
    try:
        recipe = get_recipe(style.recipe)
    except RecipeError:
        return
    from make_meme.pipelines.swap import preset_size

    w, h = preset_size(recipe, plan.quality, clip_size, profile)
    steps = int(recipe.preset_values(plan.quality, profile).get("steps", 4))
    if style.engine == "animate":
        plan.estimate = {**base, **_animate_estimate(plan, shots, recipe.name, profile, w, h, steps),
                         "generation_size": [w, h], "output_size": list(clip_size)}
        return
    plan.estimate = {**base, **_estimate(plan, shots, profile, w, h, steps), "output_size": [w, h]}


def _animate_estimate(plan: MemePlan, shots: list[Shot], recipe: str, profile: str, w: int, h: int,
                      steps: int) -> dict:
    """One generation per cast performer per shot, at the clip's frame rate, in windows of
    at most 77 frames (plus a character design per identity, ~1 min)."""
    from make_meme.perf import estimate_seconds

    total, basis = 60.0 * len(set(plan.cast.values())), "default-guess"
    for shot in shots:
        n = sum(1 for pid in plan.cast if pid in shot.performers)
        frames = max(1, round(shot.duration * 24))
        while n and frames > 0:
            window = min(frames, 77)
            est = estimate_seconds(profile, recipe, w, h, window, steps)
            total += n * float(est["seconds"])
            basis = est.get("basis", basis)
            frames -= window
    return {"seconds": round(total), "minutes": round(total / 60, 1), "basis": basis}


@mcp.tool(structured_output=False)
async def plan_meme(
    intent: str,
    video: str | None = None,
    query: str | None = None,
    photos: list[str] | None = None,
    folder: str | None = None,
    style: str | None = None,
    start_sec: float | None = None,
    end_sec: float | None = None,
    length_sec: float | None = None,
    aspect: Aspect = "9:16",
    quality: Literal["draft", "high"] = "draft",
    descriptions: dict[str, str] | None = None,
    scene: str | None = None,
    cast: dict[str, str] | None = None,
) -> list[Any]:
    """Plan a subject-swap meme end to end (no generation yet). Use this first.
    - intent: the user's request in their words (used to pick a style, e.g. "head only").
    - video (asset id / path / any link) or query (text search for the song/MV).
    - photos and/or folder: replacement photos, unsorted is fine (organized automatically).
    - style: see list_styles; if omitted it's inferred from intent, or candidates are returned.
    - segment: start/end, or automatically the part shorts/memes reuse most, of length_sec
      (style default ~15 s). Shots (camera cuts) are handled separately and the same
      performer keeps the same replacement across cuts.
    - aspect: 9:16 reframes to vertical following the performers ("source" keeps it).
    - descriptions: {"A": "an Italian greyhound with a blue-grey coat"} improves prompts.
    - cast: override who becomes whom, {"P1": "B", "P2": "A"}.
    Returns the plan (id, segment, shots, performers P1.., identities A.., cast, prompts,
    estimate, warnings) and a preview image. Show it to the user, then call render_meme."""
    _load_sources_backend()
    try:
        chosen_style = get_style(style) if style else None
    except StyleError as e:
        raise ToolError(str(e)) from e

    # 1) source video
    if video is None:
        if not query:
            raise ToolError("Give a video (asset id/path/link) or a query to search for it.")
        from make_meme.tools_trend import _pick_reference

        video = await _pick_reference(_load_sources_backend(), query)
    src = json.loads((await load_media(video))[0])
    src_asset = get_assets().get(src["id"])
    if src_asset is None or src_asset.kind != "video":
        raise ToolError("The source must be a video.")

    # 2) segment
    warnings: list[str] = []
    segment: dict[str, Any]
    want_len = float(length_sec or (chosen_style.defaults.get("length_sec") if chosen_style else 15) or 15)
    duration = float(src_asset.meta.get("duration") or 0)
    if start_sec is None and end_sec is None:
        from make_meme.tools_trend import analyze_meme_usage

        usage = json.loads((await analyze_meme_usage(query or intent, reference=src_asset.id, n=10))[0])
        hot = usage.get("most_reused") or []
        if hot and hot[0].get("shorts", 0) >= 2:
            start = float(hot[0]["start"])
            basis = f"start of the most reused range in shorts ({hot[0]['shorts']} shorts)"
        elif usage.get("hook"):
            start = max(0.0, float(usage["hook"]["start"]) - 1.0)
            basis = "the song's most repeated section (few shorts to learn from)"
        else:
            start, basis = 0.0, "no usage data; from the beginning"
        segment = {"start": round(start, 2), "end": round(min(duration or start + want_len, start + want_len), 2),
                   "basis": basis, "typical_short_length": usage.get("typical_length_sec")}
    else:
        s = float(start_sec or 0.0)
        e = float(end_sec if end_sec is not None else s + want_len)
        segment = {"start": s, "end": e, "basis": "given"}
    if segment["end"] - segment["start"] > 30:
        warnings.append("Segments over 30 s take very long; consider shorter.")

    clip = json.loads((await load_media(src_asset.id, segment["start"], segment["end"]))[0])
    clip_asset = get_assets().get(clip["id"])
    work = get_settings().home / "plans" / f"work_{clip_asset.id}"

    try:
        async with comfy_session() as client:
            profile = await hardware_profile(client)
            # 3) shots (+ shot-wise vertical reframe), performers
            shots, performer_ids = await analyze_shots(client, clip_asset.path, work / "shots", profile=profile)
            if aspect != "source" and shots:
                spans = [(s.start, s.end) for s in shots]
                framed = await reframe_by_shots(client, clip_asset.path, spans, aspect,
                                                clip_asset.path.parent / f"reframed_{aspect.replace(':', 'x')}.mp4",
                                                profile=profile)
                new = await asyncio.to_thread(get_assets().add, framed, "video",
                                              origin={"reframed_from": clip_asset.id, "aspect": aspect},
                                              meta={k: v for k, v in clip_asset.meta.items() if k == "audio_path"},
                                              parent_ids=[clip_asset.id])
                clip_asset = new
                shots, performer_ids = await analyze_shots(client, clip_asset.path, work / "shots_v", profile=profile)
            if not performer_ids:
                raise ToolError("No people or animals were found in this segment; try another segment or video.")
            # 4) photos -> identities
            paths = _collect_photos(photos, folder)
            identities_raw, _sheet = await _organize(client, paths, work / "photos", profile)
    except (ComfyError, RecipeError) as e:
        raise ToolError(str(e)) from e
    identities = [_identity_ref(i) for i in identities_raw]
    for ident in identities:
        if descriptions and ident.id in descriptions:
            ident.description = descriptions[ident.id]
        warnings += [f"{ident.id}: {a}" for a in ident.advice]
    if not identities:
        raise ToolError("No person or animal could be found in the photos.")

    # 5) cast performers -> identities
    main = main_shot(shots)
    with Image.open(main.frame_path) as f:
        perf_hists = {pid: subject_head_hist(f, next(s for s in main.subjects if s.id == sid))
                      for pid, sid in main.performers.items()}
    ident_hists = {i.id: np.mean([inst.hist for inst in raw.instances], axis=0)
                   for i, raw in zip(identities, identities_raw)}
    auto_cast, cast_reason = cast_identities(perf_hists, ident_hists)
    final_cast = dict(cast) if cast else auto_cast
    if len(identities) < len(performer_ids):
        warnings.append(f"{len(performer_ids)} performers but {len(identities)} identities: "
                        f"only {', '.join(final_cast)} will be replaced.")
    unmatched = [s.index for s in shots if s.subjects and not s.performers]
    if unmatched:
        warnings.append(f"Shots {unmatched} show people we couldn't match to the main performers; they stay original.")

    # 6) style + prompts
    label = identities[0].label
    style_name, candidates = (chosen_style.name, [chosen_style.name]) if chosen_style else guess_style(intent, label)
    st = get_style(style_name or candidates[0])
    prompts = {pid: st.render_prompt(subject_desc=plan_ident.description, coat=plan_ident.coat, scene=scene or "")
               for pid, iid in final_cast.items() if (plan_ident := next((i for i in identities if i.id == iid), None))}

    plan = MemePlan(
        id=new_plan_id(), intent=intent, source_asset=src_asset.id, source_title=src_asset.origin.get("title"),
        segment=segment, clip_asset=clip_asset.id, aspect=aspect, style=style_name, style_candidates=candidates,
        quality=quality, seed=random.randint(0, 2**31 - 1), shots=[s.to_json() for s in shots],
        performers=[{"id": pid, "bbox": list(next(s for s in main.subjects if s.id == sid).bbox)}
                    for pid, sid in main.performers.items()],
        identities=identities, cast=final_cast, prompts=prompts, negative_prompt=st.negative, scene=scene or "",
        warnings=warnings,
    )
    clip_size = (int(clip_asset.meta.get("width", 1)), int(clip_asset.meta.get("height", 1)))
    plan.estimate = {"profile": profile, "clip_size": list(clip_size)}
    _refresh_estimate(plan, st)
    save_plan(plan)
    preview = await asyncio.to_thread(_preview, plan, shots, identities)
    payload = plan.to_json()
    payload["cast_reason"] = cast_reason
    payload["next"] = ("Show this to the user. Then render_meme(plan_id" +
                       (", style=<one of style_candidates>)" if not style_name else ")") +
                       "; optionally preview_seconds=5 for a quick test first.")
    return [json.dumps(payload, indent=2, ensure_ascii=False, default=str), MCPImage(path=str(preview))]


def _save_characters(plan: MemePlan) -> None:
    """Persist designed character references into the saved plan (even after a preview
    render, which works on a trimmed copy)."""
    saved = load_plan(plan.id)
    if saved is None:
        return
    for ident in plan.identities:
        if (target := saved.identity(ident.id)) is not None:
            target.characters.update(ident.characters)
    save_plan(saved)


@mcp.tool(structured_output=False)
async def design_characters(plan_id: str, style: str, identity: str | None = None, extra: str = "",
                            seed: int | None = None) -> list[Any]:
    """Design (or redesign) the character reference each cast identity will become in an
    `animate` style, e.g. the dog standing upright in the performer's outfit. Show the
    images to the user before render_meme: the video copies this look. Pass `identity` to
    redo just one, `extra` to steer it ("bigger ears", "smiling"), `seed` for a new variation.
    render_meme designs missing ones automatically."""
    from make_meme.pipelines.render import ensure_characters

    plan = load_plan(plan_id)
    if plan is None:
        raise ToolError(f"No plan {plan_id!r}; call plan_meme first.")
    try:
        st = get_style(style)
    except StyleError as e:
        raise ToolError(str(e)) from e
    if st.engine != "animate":
        raise ToolError(f"Style {style!r} doesn't use a designed character (engine: {st.engine}).")
    targets = [identity] if identity else sorted(set(plan.cast.values()))
    for ident_id in targets:
        ident = plan.identity(ident_id)
        if ident is None:
            raise ToolError(f"Plan {plan_id} has no identity {ident_id!r}")
        ident.characters.pop(st.name, None)  # redo
    if seed is not None:
        plan.seed = seed
    work = get_settings().home / "plans" / f"{plan.id}_design"
    try:
        async with comfy_session() as client:
            profile = await hardware_profile(client)
            if extra:
                from make_meme.pipelines.design import design_character

                for ident_id in targets:
                    ident = plan.identity(ident_id)
                    ident.characters[st.name] = str(await design_character(
                        client, st, ident, work / "characters", profile=profile, seed=plan.seed, extra=extra))
            refs = await ensure_characters(client, plan, st, work, profile=profile)
    except (ComfyError, RecipeError, ValueError) as e:
        raise ToolError(str(e)) from e
    _save_characters(plan)
    images: list[Any] = [json.dumps({"plan_id": plan.id, "style": st.name,
                                     "characters": {pid: str(p) for pid, p in refs.items()},
                                     "next": "Show these to the user; redesign with extra/seed if needed, then "
                                             f"render_meme(plan_id={plan.id!r}, style={st.name!r})."},
                                    ensure_ascii=False)]
    images += [MCPImage(path=str(p)) for p in refs.values()]
    return images


@mcp.tool()
async def render_meme(
    plan_id: str,
    style: str | None = None,
    quality: Literal["draft", "high"] | None = None,
    cast: dict[str, str] | None = None,
    seed: int | None = None,
    preview_seconds: float | None = None,
    keep_audio: bool = True,
    descriptions: dict[str, str] | None = None,
) -> str:
    """Render a plan from plan_meme into ONE video (background job; poll get_job).
    Override style / quality / cast / seed if the user changed their mind.
    descriptions={"A": "an Italian greyhound with a blue-grey coat"} rewrites the prompts
    (describe what you see in the reference photos: species, breed, coat).
    preview_seconds=5 renders only the first seconds for a quick check."""
    plan = load_plan(plan_id)
    if plan is None:
        raise ToolError(f"No plan {plan_id!r}; call plan_meme first.")
    try:
        st = get_style(style or plan.style or (plan.style_candidates[0] if plan.style_candidates else ""))
    except StyleError as e:
        raise ToolError(str(e)) from e
    for ident_id, text in (descriptions or {}).items():
        ident = plan.identity(ident_id)
        if ident is None:
            raise ToolError(f"Plan {plan_id} has no identity {ident_id!r}; identities: {[i.id for i in plan.identities]}")
        ident.description = text
    if (style and style != plan.style) or descriptions or not plan.prompts:
        plan.prompts = {pid: st.render_prompt(subject_desc=i.description, coat=i.coat, scene=plan.scene)
                        for pid, iid in plan.cast.items() if (i := plan.identity(iid))}
        plan.negative_prompt = st.negative
    if quality:
        plan.quality = quality
    if cast:
        plan.cast = dict(cast)
    if seed is not None:
        plan.seed = seed
    if preview_seconds:
        kept = []
        for s in plan.shots:
            if s["start"] >= preview_seconds:
                break
            kept.append({**s, "end": min(s["end"], preview_seconds)})
        plan.shots = kept
    clip_asset = get_assets().get(plan.clip_asset)
    if clip_asset is None:
        raise ToolError("The plan's clip is gone; re-run plan_meme.")
    settings = get_settings()
    try:  # estimate for the machine that will render (the plan may have been made elsewhere)
        async with comfy_session() as client:
            plan.estimate["profile"] = await hardware_profile(client)
    except ComfyError:
        pass
    _refresh_estimate(plan, st)

    async def job(ctx: JobContext) -> dict[str, Any]:
        # Keyed by plan + style (not job) so a re-run after a failure reuses finished chunks.
        work = settings.outputs_dir / "renders" / f"{plan.id}_{st.name}{'_preview' if preview_seconds else ''}"
        work.mkdir(parents=True, exist_ok=True)

        async def report(stage: str, progress: float, message: str) -> None:
            ctx.update(stage=stage, progress=min(0.95, progress * 0.95), message=message)

        async with comfy_session() as client:
            profile = await hardware_profile(client)
            if st.engine in ("swap", "animate"):  # paste styles have no prompts to encode
                try:
                    from make_meme.perf import precache_prompts

                    ctx.update(stage="preparing", message="encoding prompts once (saves memory during sampling)")
                    await precache_prompts(client, [(p, plan.negative_prompt) for p in plan.prompts.values()],
                                           profile=profile)
                except ImportError:
                    pass
            silent = await render_plan(client, plan, st, clip_asset.path, work / "work", profile=profile,
                                       report=report, cancelled=ctx.cancelled)
        _save_characters(plan)
        out = settings.outputs_dir / f"{ctx.job_id}.mp4"
        audio = clip_asset.meta.get("audio_path") or (str(clip_asset.path) if clip_asset.meta.get("has_audio") else None)
        if keep_audio and audio and Path(audio).is_file():
            await post.mux_audio(silent, Path(audio), out)
        else:
            await post._run(["ffmpeg", "-y", "-i", str(silent), "-c", "copy",
                             "-metadata", f"comment={post.AI_GENERATED_COMMENT}", str(out)])
        result_asset = await asyncio.to_thread(
            get_assets().add, out, "video", origin={"plan_id": plan.id, "style": st.name, "job_id": ctx.job_id},
            parent_ids=[clip_asset.id])
        preview = await post.make_preview(result_asset.path, result_asset.path.parent / "preview.jpg")
        return {"asset_id": result_asset.id, "path": str(result_asset.path), "preview_path": str(preview),
                "style": st.name, "plan_id": plan.id}

    job_obj = get_jobs().submit(f"render:{st.name}", job)
    plan.renders.append({"job_id": job_obj.id, "style": st.name, "preview_seconds": preview_seconds})
    if not preview_seconds:
        save_plan(plan)
    return json.dumps({"job_id": job_obj.id, "plan_id": plan.id, "style": st.name, "estimate": plan.estimate,
                       "output": "ONE video with every cast performer replaced",
                       "next": "Poll get_job(job_id)."}, indent=2, ensure_ascii=False)
