"""Subject-swap pipeline: normalize → per-mapping, per-chunk recipe runs → stitch.

Several mappings (e.g. member A → my photo, member B → my dog) run one after another:
the output of one pass is the input video of the next. Long clips are split into
4n+1-frame chunks; each chunk re-locates the subject on its first frame (SAM 3 +
IoU tracking against the previous chunk) so the mask follows the performer.
"""

from __future__ import annotations

import asyncio
import logging
import shutil
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path

from make_meme import ingest
from make_meme.chunking import plan_chunks
from make_meme.comfy.client import ComfyClient
from make_meme.pipelines.detect import Subject, binary_mask, clean_reference, detect_in_image, iou
from make_meme.pipelines.runtime import ensure_ready, node_files, run_recipe
from make_meme.post import concat_videos
from make_meme.recipes.loader import Recipe

logger = logging.getLogger(__name__)

Report = Callable[[str, float, str], Awaitable[None] | None]


@dataclass
class SwapMapping:
    subject: Subject  # where the subject is on the first frame (source pixel coords)
    images: list[Path]  # reference photos of the replacement (1st = full body, 2nd = face close-up)
    prompt: str | None = None


@dataclass
class SwapPlan:
    video_path: Path  # source clip (any fps/size)
    source_size: tuple[int, int]
    mappings: list[SwapMapping]
    recipe: Recipe
    profile: str
    quality: str = "draft"
    prompt: str | None = None
    negative_prompt: str | None = None
    seed: int = 42
    clean_refs: bool = True
    work_dir: Path = field(default_factory=lambda: Path("."))


def preset_size(recipe: Recipe, quality: str, source_size: tuple[int, int], profile: str) -> tuple[int, int]:
    """Preset resolution for this hardware, flipped for portrait sources (TikTok/Reels/Shorts)."""
    preset = recipe.preset_values(quality, profile)
    w = int(preset.get("width", recipe.inputs["width"].default if "width" in recipe.inputs else 832))
    h = int(preset.get("height", recipe.inputs["height"].default if "height" in recipe.inputs else 480))
    sw, sh = source_size
    if sh > sw and w > h:
        w, h = h, w
    return w, h


def chunk_len_for(recipe: Recipe) -> int:
    return int(recipe.constraints.get("max_frames", 81))


async def _emit(report: Report | None, stage: str, progress: float, message: str) -> None:
    if report is None:
        return
    res = report(stage, progress, message)
    if asyncio.iscoroutine(res):
        await res


async def run_swap(
    client: ComfyClient,
    plan: SwapPlan,
    *,
    report: Report | None = None,
    cancelled: asyncio.Event | None = None,
) -> Path:
    """Returns a silent mp4 at the recipe fps containing all replacements."""
    recipe = plan.recipe
    await ensure_ready(client, recipe, plan.profile)
    fps = int(recipe.constraints.get("fps", 16))
    width, height = preset_size(recipe, plan.quality, plan.source_size, plan.profile)
    work = plan.work_dir
    work.mkdir(parents=True, exist_ok=True)

    current = await asyncio.to_thread(_normalize, plan.video_path, work / "pass0.mp4", width, height, fps)
    total_frames = int((await asyncio.to_thread(ingest.probe, current))["frame_count"])
    chunks = plan_chunks(total_frames, chunk_len=chunk_len_for(recipe), overlap=1)
    steps_total = max(1, len(plan.mappings) * len(chunks))
    done = 0

    for m_index, mapping in enumerate(plan.mappings, start=1):
        refs = mapping.images[:2]
        if plan.clean_refs:
            refs = [await clean_reference(client, p, work / f"refs{m_index}", profile=plan.profile) for p in refs]
        prompt = " ".join(p for p in (plan.prompt, mapping.prompt) if p) or None
        prev_bbox = _scale_bbox(mapping.subject.bbox, plan.source_size, (width, height))
        first_mask = binary_mask(Path(mapping.subject.mask_path), width, height)

        outputs: list[Path] = []
        for c_index, chunk in enumerate(chunks):
            if cancelled is not None and cancelled.is_set():
                raise asyncio.CancelledError
            label = f"subject {m_index}/{len(plan.mappings)}, chunk {c_index + 1}/{len(chunks)}"
            chunk_dir = work / f"m{m_index}_c{c_index}"
            chunk_dir.mkdir(exist_ok=True)
            chunk_video = await asyncio.to_thread(
                _cut_chunk, current, chunk_dir / "input.mp4", chunk.start, chunk.end, chunk.pad, fps
            )
            if c_index == 0:
                mask = first_mask
            else:
                mask, prev_bbox = await _relocate(
                    client, chunk_video, mapping.subject.label, prev_bbox, chunk_dir, plan.profile, width, height
                )
            mask_path = chunk_dir / "mask.png"
            mask.convert("RGB").save(mask_path)

            async def on_progress(stage: str, frac: float, msg: str, _label=label, _done=done) -> None:
                if frac >= 0:
                    await _emit(report, "generating", (_done + frac) / steps_total, f"{_label}: {msg}")

            media = {"video": chunk_video, "mask": mask_path, "ref1": refs[0]}
            if len(refs) > 1:
                media["ref2"] = refs[1]
            values = {"seed": plan.seed, "width": width, "height": height}
            if prompt:
                values["prompt"] = prompt
            if plan.negative_prompt:
                values["negative_prompt"] = plan.negative_prompt
            await _emit(report, "generating", done / steps_total, f"{label}: submitting")
            result = await run_recipe(
                client, recipe, media=media, values=values, profile=plan.profile, preset=plan.quality,
                on_progress=on_progress, cancelled=cancelled,
            )
            frames_dir = chunk_dir / "frames"
            frames_dir.mkdir(exist_ok=True)
            files = node_files(result, recipe.outputs["frames"])
            if not files:
                raise RuntimeError(f"{recipe.name} produced no frames for {label}")
            for i, f in enumerate(files):
                await client.download(f, frames_dir / f"{i:05d}.png")
            keep = (chunk.end - chunk.start)  # drop padding frames
            outputs.append(await asyncio.to_thread(_encode_frames, frames_dir, chunk_dir / "out.mp4", fps, keep))
            done += 1
            await _emit(report, "generating", done / steps_total, f"{label}: done")

        stitched = work / f"pass{m_index}.mp4"
        if len(outputs) == 1:
            shutil.copyfile(outputs[0], stitched)
        else:
            await concat_videos(outputs, stitched, overlap=1)
        current = stitched

    return current


def _normalize(src: Path, dest: Path, width: int, height: int, fps: int) -> Path:
    out = ingest.normalize(src, width, height, fps)
    if out != dest:
        shutil.copyfile(out, dest)
    return dest


def _cut_chunk(video: Path, dest: Path, start: int, end: int, pad: int, fps: int) -> Path:
    """Frame-exact cut [start, end) + `pad` repeats of the last frame (4n+1 length)."""
    vf = f"select='between(n\\,{start}\\,{end - 1})',setpts=N/({fps}*TB)"
    if pad > 0:
        vf += f",tpad=stop_mode=clone:stop={pad}"
    ingest._run([ingest.FFMPEG, "-y", "-i", str(video), "-vf", vf, "-an", "-r", str(fps),
                 "-c:v", "libx264", "-crf", "12", "-pix_fmt", "yuv420p", str(dest)])
    return dest


def _encode_frames(frames_dir: Path, dest: Path, fps: int, keep: int) -> Path:
    ingest._run([ingest.FFMPEG, "-y", "-framerate", str(fps), "-i", str(frames_dir / "%05d.png"),
                 "-frames:v", str(keep), "-c:v", "libx264", "-crf", "14", "-pix_fmt", "yuv420p", str(dest)])
    return dest


def _scale_bbox(bbox, src: tuple[int, int], dst: tuple[int, int]) -> tuple[int, int, int, int]:
    """Map a bbox through the cover-scale + center-crop used by normalize."""
    sw, sh = src
    dw, dh = dst
    scale = max(dw / sw, dh / sh)
    ox, oy = (sw * scale - dw) / 2, (sh * scale - dh) / 2
    x1, y1, x2, y2 = bbox
    return (round(x1 * scale - ox), round(y1 * scale - oy), round(x2 * scale - ox), round(y2 * scale - oy))


async def _relocate(client, chunk_video, label, prev_bbox, chunk_dir, profile, width, height):
    """Find the same subject on the chunk's first frame: best IoU with its last known box."""
    frame = await asyncio.to_thread(ingest.extract_frame, chunk_video, 0.0)
    frame_path = chunk_dir / "first.png"
    frame.save(frame_path)
    found = await detect_in_image(client, frame_path, f"{label}:5", chunk_dir / "det", profile=profile)
    if not found:
        raise RuntimeError(
            f"Lost track of the '{label}' at a chunk boundary; try a shorter clip or a clip without cuts."
        )
    best = max(found, key=lambda s: iou(s.bbox, prev_bbox))
    if iou(best.bbox, prev_bbox) < 0.05:
        best = min(found, key=lambda s: _center_dist(s.bbox, prev_bbox))
    return binary_mask(Path(best.mask_path), width, height), best.bbox


def _center_dist(a, b) -> float:
    return ((a[0] + a[2] - b[0] - b[2]) ** 2 + (a[1] + a[3] - b[1] - b[3]) ** 2) ** 0.5
