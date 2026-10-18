"""Execute a MemePlan: shot by shot, performer by performer, into ONE video.

Each shot is cut from the plan's clip and handled by the style's engine: `swap` styles
replace the performers cast in that shot with a generation recipe (pipelines.swap.run_swap,
chunked for long shots); `paste` styles paste each cast performer's tracked pet-head
cut-out (pipelines.paste). Shots without cast performers are passed through, and the
shots are concatenated into one silent video (the caller adds the clip's audio).
"""

from __future__ import annotations

import asyncio
import itertools
import logging
import shutil
from collections.abc import Awaitable, Callable
from pathlib import Path

import numpy as np
from PIL import Image

from make_meme import ingest
from make_meme.comfy.client import ComfyClient
from make_meme.pipelines.assign import hist_dist
from make_meme.pipelines.detect import Subject
from make_meme.pipelines.paste import head_cutout, paste_shot
from make_meme.pipelines.reframe import reframe
from make_meme.pipelines.shots import Shot
from make_meme.pipelines.swap import SwapMapping, SwapPlan, preset_size, run_swap
from make_meme.plan import MemePlan
from make_meme.post import concat_videos
from make_meme.recipes.loader import get_recipe
from make_meme.styles import Style

logger = logging.getLogger(__name__)

Report = Callable[[str, float, str], Awaitable[None]]


def cut_segment(video: Path, start: float, end: float, dest: Path) -> Path:
    """Frame-exact, silent cut of frames [round(start*fps), round(end*fps)).

    Consecutive shots must tile the clip exactly: second-based seeking (-ss/-to) gains or
    loses a frame per cut, and over several shots the video drifts against the clip's
    audio (seen as a 0.1 s lag in the NEON test)."""
    fps = float(ingest.probe(video)["fps"]) or 24.0
    first, stop = round(start * fps), round(end * fps)
    stop = max(stop, first + 1)
    vf = f"select='between(n\\,{first}\\,{stop - 1})',setpts=N/FRAME_RATE/TB"
    ingest._run([ingest.FFMPEG, "-y", "-i", str(video), "-vf", vf, "-an", "-c:v", "libx264", "-crf", "14",
                 "-pix_fmt", "yuv420p", str(dest)])
    return dest


async def reframe_by_shots(client: ComfyClient, clip: Path, spans: list[tuple[float, float]], aspect: str,
                           dest: Path, *, profile: str, query: str = "person, animal") -> Path:
    """Subject-following crop computed per shot (a pan must never continue across a cut),
    concatenated back together with the clip's audio."""
    work = dest.parent / f"{dest.stem}_parts"
    work.mkdir(parents=True, exist_ok=True)
    parts: list[Path] = []
    for i, (a, b) in enumerate(spans):
        piece = await asyncio.to_thread(cut_segment, clip, a, b, work / f"shot{i:02d}.mp4")
        out, _, _ = await reframe(client, piece, work / f"shot{i:02d}_v.mp4", aspect=aspect, query=query,
                                  profile=profile)
        parts.append(out)
    silent = work / "joined.mp4"
    if len(parts) == 1:
        shutil.copyfile(parts[0], silent)
    else:
        await concat_videos(parts, silent, overlap=0)
    info = await asyncio.to_thread(ingest.probe, clip)
    if info.get("has_audio"):
        await asyncio.to_thread(ingest._run, [ingest.FFMPEG, "-y", "-i", str(silent), "-i", str(clip), "-map", "0:v:0",
                                              "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", "-shortest", str(dest)])
    else:
        shutil.copyfile(silent, dest)
    return dest


def cast_identities(performer_hists: dict[str, np.ndarray], identity_hists: dict[str, np.ndarray],
                    max_cost_gap: float = 0.05) -> tuple[dict[str, str], str]:
    """Assign identities to performers (one each), minimizing colour distance between a
    performer's head/upper body and an identity's coat; keeps listing order (largest
    performer first) unless appearance clearly prefers another pairing."""
    perf_ids, ident_ids = list(performer_hists), list(identity_hists)
    k = min(len(perf_ids), len(ident_ids))
    if k == 0:
        return {}, "nothing to cast"
    default = dict(zip(perf_ids[:k], ident_ids[:k]))
    default_cost = sum(hist_dist(performer_hists[p], identity_hists[i]) for p, i in default.items())
    best_cost, best = default_cost, default
    for perfs in itertools.permutations(perf_ids, k):
        pairing = dict(zip(perfs, ident_ids[:k]))
        cost = sum(hist_dist(performer_hists[p], identity_hists[i]) for p, i in pairing.items())
        if cost < best_cost - 1e-9:
            best_cost, best = cost, pairing
    if best is not default and best_cost < default_cost - max_cost_gap:
        return best, "paired by appearance (performer hair/head colour vs. coat colour)"
    return default, "paired in size order (appearance gave no clear preference)"


def _subject(shot: Shot, sid: int) -> Subject:
    return next(s for s in shot.subjects if s.id == sid)


async def render_plan(
    client: ComfyClient,
    plan: MemePlan,
    style: Style,
    clip: Path,
    work: Path,
    *,
    profile: str,
    report: Report | None = None,
    cancelled: asyncio.Event | None = None,
) -> Path:
    """Returns a silent mp4 (audio is muxed by the caller) covering the whole clip."""
    if style.engine == "paste":
        return await render_paste(client, plan, style, clip, work, profile=profile, report=report, cancelled=cancelled)
    if style.engine == "animate":
        return await render_animate(client, plan, style, clip, work, profile=profile, report=report,
                                    cancelled=cancelled)
    recipe = get_recipe(style.recipe)
    work.mkdir(parents=True, exist_ok=True)
    info = await asyncio.to_thread(ingest.probe, clip)
    src_size = (int(info["width"]), int(info["height"]))
    fps = int(recipe.constraints.get("fps", 16))
    width, height = preset_size(recipe, plan.quality, src_size, profile)
    shots = [Shot.from_json(s) for s in plan.shots]

    tasks = [(shot, pid) for shot in shots for pid in plan.cast if pid in shot.performers]
    total = max(1, len(tasks))
    done = 0
    outputs: list[Path] = []
    for shot in shots:
        if cancelled is not None and cancelled.is_set():
            raise asyncio.CancelledError
        sdir = work / f"shot{shot.index:02d}"
        sdir.mkdir(exist_ok=True)
        piece = await asyncio.to_thread(cut_segment, clip, shot.start, shot.end, sdir / "input.mp4")
        mappings: list[SwapMapping] = []
        for pid, ident_id in plan.cast.items():
            if pid not in shot.performers:
                continue
            ident = plan.identity(ident_id)
            if ident is None:
                continue
            refs = [r for r in (ident.ref_for(style.refs.get("ref1", "full")),
                                ident.ref_for(style.refs.get("ref2", "head"))) if r]
            if not refs:
                plan.warnings.append(f"identity {ident_id} has no usable reference crops; skipped")
                continue
            mappings.append(SwapMapping(subject=_subject(shot, shot.performers[pid]), images=[Path(r) for r in refs],
                                        prompt=plan.prompts.get(pid), mask_mode=style.mask))
        if not mappings:
            outputs.append(await asyncio.to_thread(_passthrough, piece, sdir / "out.mp4", width, height, fps))
            continue
        n_here = len(mappings)

        async def shot_report(stage: str, frac: float, msg: str, _done=done, _n=n_here, _i=shot.index) -> None:
            if report is not None:
                await report(stage, (_done + frac * _n) / total, f"shot {_i + 1}/{len(shots)} · {msg}")

        swap_plan = SwapPlan(
            video_path=piece, source_size=src_size, mappings=mappings, recipe=recipe, profile=profile,
            quality=plan.quality, prompt=None, negative_prompt=plan.negative_prompt or None, seed=plan.seed,
            clean_refs=True, auto_head_ref=False, work_dir=sdir / "swap",
        )
        outputs.append(await run_swap(client, swap_plan, report=shot_report, cancelled=cancelled))
        done += n_here
    final = work / "render_silent.mp4"
    if len(outputs) == 1:
        shutil.copyfile(outputs[0], final)
    else:
        await concat_videos(outputs, final, overlap=0)
    return final


async def render_paste(
    client: ComfyClient,
    plan: MemePlan,
    style: Style,
    clip: Path,
    work: Path,
    *,
    profile: str,
    report: Report | None = None,
    cancelled: asyncio.Event | None = None,
) -> Path:
    """The `paste` engine: original resolution and frame rate, no generation."""
    work.mkdir(parents=True, exist_ok=True)
    if hasattr(client, "free"):
        # A generation model left loaded by an earlier render (14B + text encoder) pushed a
        # 36 GB Mac into swap and made tracking 6x slower; SAM 3 reloads in seconds.
        await client.free()
    shots = [Shot.from_json(s) for s in plan.shots]
    scale = float(style.params.get("scale", 1.5))
    lift = float(style.params.get("lift", 0.12))
    hold = float(style.params.get("hold_sec", 0.25))

    cutouts = {}
    for pid, ident_id in plan.cast.items():
        ident = plan.identity(ident_id)
        if ident is None:
            continue
        cached = work / f"cutout_{ident_id}.png"
        if cached.is_file():
            cutouts[pid] = Image.open(cached).convert("RGBA")
            continue
        for kind in (style.refs.get("ref1", "head"), style.refs.get("ref2", "full")):
            ref = ident.ref_for(kind)
            if ref and (cut := await head_cutout(client, Path(ref), profile=profile)) is not None:
                cut.save(cached)
                cutouts[pid] = cut
                break
        else:
            plan.warnings.append(f"identity {ident_id}: could not cut a head out of its photos; skipped")

    total = max(1, sum(1 for s in shots if any(p in cutouts for p in s.performers)))
    done = 0
    outputs: list[Path] = []
    for shot in shots:
        if cancelled is not None and cancelled.is_set():
            raise asyncio.CancelledError
        sdir = work / f"shot{shot.index:02d}"
        sdir.mkdir(exist_ok=True)
        piece = await asyncio.to_thread(cut_segment, clip, shot.start, shot.end, sdir / "input.mp4")
        performers = {pid: _subject(shot, sid) for pid, sid in shot.performers.items() if pid in cutouts}
        if not performers:
            outputs.append(piece)
            continue
        if report is not None:
            await report("tracking", done / total, f"shot {shot.index + 1}/{len(shots)} · tracking heads")
        out, warns = await paste_shot(client, piece, performers, cutouts, sdir, profile=profile, scale=scale,
                                      lift=lift, hold_sec=hold, cancelled=cancelled)
        plan.warnings.extend(f"shot {shot.index + 1}: {w}" for w in warns)
        outputs.append(out)
        done += 1
    final = work / "render_silent.mp4"
    if len(outputs) == 1:
        shutil.copyfile(outputs[0], final)
    else:
        await concat_videos(outputs, final, overlap=0)
    return final


async def ensure_characters(client: ComfyClient, plan: MemePlan, style: Style, work: Path, *, profile: str,
                            report: Report | None = None) -> dict[str, Path]:
    """performer id -> designed character reference for `style` (designing missing ones)."""
    from make_meme.pipelines.design import design_character, performer_crop
    from make_meme.pipelines.shots import main_shot

    work.mkdir(parents=True, exist_ok=True)
    shots = [Shot.from_json(s) for s in plan.shots]
    main = main_shot(shots) if shots else None
    refs: dict[str, Path] = {}
    for pid, ident_id in plan.cast.items():
        ident = plan.identity(ident_id)
        if ident is None:
            continue
        existing = ident.characters.get(style.name)
        if existing and Path(existing).is_file():
            refs[pid] = Path(existing)
            continue
        outfit = None
        if style.design_outfit and main is not None and pid in main.performers and main.frame_path:
            outfit = await asyncio.to_thread(performer_crop, Path(main.frame_path), _subject(main, main.performers[pid]),
                                             work / f"outfit_{pid}.png")
        if report is not None:
            await report("designing", 0.0, f"designing {ident_id} as {style.title}")
        path = await design_character(client, style, ident, work / "characters", profile=profile, seed=plan.seed,
                                      outfit=outfit)
        ident.characters[style.name] = str(path)
        refs[pid] = path
    return refs


def cap_to_source(size: tuple[int, int], source: tuple[int, int], multiple: int = 16) -> tuple[int, int]:
    """Never generate more pixels than the clip has: results are pasted onto the clip's own
    frames, so a 720x1280 generation for a 608x1080 clip only costs time."""
    w, h = size
    sw, sh = source
    k = min(1.0, sw / w, sh / h)
    return max(multiple, int(w * k) // multiple * multiple), max(multiple, int(h * k) // multiple * multiple)


# Bump when animate_shot's output changes for the same inputs (e.g. how masks are built), so
# cached shots from an older pipeline aren't reused.
ANIMATE_PIPELINE_VERSION = 2


async def render_animate(
    client: ComfyClient,
    plan: MemePlan,
    style: Style,
    clip: Path,
    work: Path,
    *,
    profile: str,
    report: Report | None = None,
    cancelled: asyncio.Event | None = None,
) -> Path:
    """The `animate` engine (pose-driven replacement) at the clip's resolution and frame rate."""
    import hashlib
    import json

    from make_meme.pipelines.animate import animate_shot, window_ranges

    work.mkdir(parents=True, exist_ok=True)
    recipe = get_recipe(style.recipe)
    info = await asyncio.to_thread(ingest.probe, clip)
    gen_size = cap_to_source(preset_size(recipe, plan.quality, (int(info["width"]), int(info["height"])), profile),
                             (int(info["width"]), int(info["height"])))
    refs = await ensure_characters(client, plan, style, work, profile=profile, report=report)
    shots = [Shot.from_json(s) for s in plan.shots]
    replace_all = bool(style.params.get("replace_all", True))
    retarget = bool(style.params.get("retarget", False))

    def has_work(shot: Shot) -> bool:
        if any(p in refs for p in shot.performers):
            return True  # a matched cast performer
        # unmatched people still get replaced (everyone on screen becomes a cast character)
        return replace_all and any(s.label == "person" for s in shot.subjects)

    busy = [s for s in shots if has_work(s)]
    outputs: list[Path] = []
    for shot in shots:
        if cancelled is not None and cancelled.is_set():
            raise asyncio.CancelledError
        sdir = work / f"shot{shot.index:02d}"
        sdir.mkdir(exist_ok=True)
        piece = await asyncio.to_thread(cut_segment, clip, shot.start, shot.end, sdir / "input.mp4")
        performers = {pid: _subject(shot, sid) for pid, sid in shot.performers.items() if pid in refs}
        if not has_work(shot):
            outputs.append(piece)
            continue
        # Reuse a finished shot when nothing that decides it has changed (resume after a failure).
        info_piece = await asyncio.to_thread(ingest.probe, piece)
        windows = window_ranges(int(info_piece["frame_count"]))
        version = [ANIMATE_PIPELINE_VERSION] + ([windows] if len(windows) > 1 else [])  # windowed shots: v3
        version += [{"replace_all": replace_all, "retarget": retarget, "grow": 6,
                     "values": style.params.get("recipe_values") or {}}]
        key = hashlib.sha1(json.dumps([version, style.name, plan.quality, profile, plan.seed,
                                       gen_size, shot.start, shot.end,
                                       sorted((p, str(refs[p]), plan.prompts.get(p, "")) for p in performers)],
                                      default=str).encode()).hexdigest()
        done_out, key_file = sdir / "out.mp4", sdir / "key.json"
        if done_out.is_file() and key_file.is_file() and json.loads(key_file.read_text()).get("key") == key:
            outputs.append(done_out)
            continue
        i = busy.index(shot)

        async def shot_report(stage: str, frac: float, msg: str, _i=i, _idx=shot.index) -> None:
            if report is not None:
                await report(stage, (_i + frac) / len(busy), f"shot {_idx + 1}/{len(shots)} · {msg}")

        out, warns = await animate_shot(client, recipe, piece, performers, refs, plan.prompts, sdir, profile=profile,
                                        quality=plan.quality, gen_size=gen_size, seed=plan.seed,
                                        negative=plan.negative_prompt, mask_mode=style.mask,
                                        replace_all=replace_all, retarget=retarget,
                                        recipe_values=dict(style.params.get("recipe_values") or {}),
                                        report=shot_report,
                                        cancelled=cancelled)
        plan.warnings.extend(f"shot {shot.index + 1}: {w}" for w in warns)
        key_file.write_text(json.dumps({"key": key}))
        outputs.append(out)
    final = work / "render_silent.mp4"
    if len(outputs) == 1:
        shutil.copyfile(outputs[0], final)
    else:
        await concat_videos(outputs, final, overlap=0)
    return final


def _passthrough(piece: Path, dest: Path, width: int, height: int, fps: int) -> Path:
    out = ingest.normalize(piece, width, height, fps)
    shutil.copyfile(out, dest)
    return dest
