"""Execute a MemePlan: shot by shot, performer by performer, into ONE video.

Each shot is cut from the plan's clip, the performers cast in that shot are swapped one
after another (pipelines.swap.run_swap, chunked for long shots), shots without cast
performers are passed through at the same size/fps, and everything is concatenated with
the clip's original audio.
"""

from __future__ import annotations

import asyncio
import itertools
import logging
import shutil
from collections.abc import Awaitable, Callable
from pathlib import Path

import numpy as np

from make_meme import ingest
from make_meme.comfy.client import ComfyClient
from make_meme.pipelines.assign import hist_dist
from make_meme.pipelines.detect import Subject
from make_meme.pipelines.reframe import reframe
from make_meme.pipelines.shots import Shot
from make_meme.pipelines.swap import SwapMapping, SwapPlan, preset_size, run_swap
from make_meme.plan import MemePlan
from make_meme.post import concat_videos
from make_meme.recipes.loader import get_recipe
from make_meme.styles import Style

logger = logging.getLogger(__name__)

Report = Callable[[str, float, str], Awaitable[None]]


def cut_segment(video: Path, start: float, end: float, dest: Path, *, keep_audio: bool = False) -> Path:
    """Re-encoded, frame-accurate cut of [start, end)."""
    cmd = [ingest.FFMPEG, "-y", "-i", str(video), "-ss", f"{start:.3f}", "-to", f"{end:.3f}",
           "-c:v", "libx264", "-crf", "14", "-pix_fmt", "yuv420p"]
    cmd += ["-c:a", "aac"] if keep_audio else ["-an"]
    ingest._run([*cmd, str(dest)])
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
            clean_refs=style.refs.get("ref1", "full").startswith("full"), auto_head_ref=False, work_dir=sdir / "swap",
        )
        outputs.append(await run_swap(client, swap_plan, report=shot_report, cancelled=cancelled))
        done += n_here
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
