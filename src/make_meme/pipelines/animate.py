"""Pose-guided replacement with Wan2.2-Animate (wan_animate_replace recipe).

Per shot: every person is tracked (SAM 3, re-detecting), each cast performer's per-frame
body mask is found, and for each performer the recipe gets
  * a pose video showing only that performer (ViTPose picks one person per frame),
  * the background frames with that performer blanked out, and the mask itself,
  * the reference photo padded to the generation size.
Each performer is generated from the original shot, then pasted back inside their own
(grown) mask, so the background and everyone else stay untouched.
"""

from __future__ import annotations

import asyncio
import math
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter, ImageOps

from make_meme import ingest
from make_meme.comfy.client import ComfyClient
from make_meme.pipelines.detect import Subject, clean_reference
from make_meme.pipelines.runtime import ensure_ready, node_files, run_recipe
from make_meme.pipelines.swap import _scale_bbox
from make_meme.pipelines.track import track_labels
from make_meme.recipes.loader import Recipe

GROW_PX = 6  # generation mask margin around the performer (at generation size)
POSE_GROW_PX = 10  # how much of the performer's surroundings the pose video keeps


def assign_bodies(labels: list[np.ndarray], bodies: dict[str, tuple[int, int, int, int]],
                  min_iou: float = 0.3, max_gap: int = 16) -> dict[str, list[np.ndarray | None]]:
    """Tie tracked people (label maps) to performers: at first by overlap with the performer's
    body box on the shot's first frame, later (when a person is re-detected under a new
    number) by closeness to where that performer was last seen."""
    owner: dict[int, str] = {}
    last: dict[str, tuple[float, float, float, int]] = {}
    out: dict[str, list[np.ndarray | None]] = {pid: [] for pid in bodies}
    for f, lab in enumerate(labels):
        objs = {}
        for k in np.unique(lab):
            if k == 0:
                continue
            m = lab == k
            ys, xs = np.nonzero(m)
            if len(xs) < 50:
                continue
            objs[int(k)] = (m, (xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))
        live = {owner[k] for k in objs if k in owner}
        for k, (_m, box) in sorted(objs.items(), key=lambda kv: -int(kv[1][0].sum())):
            if k in owner:
                continue
            cx, cy, w = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2, box[2] - box[0]
            best, best_score = None, 0.0
            for pid, anchor in bodies.items():
                if pid in live:
                    continue
                if pid in last:
                    lx, ly, lw, lf = last[pid]
                    if f - lf > max_gap:
                        continue
                    d = math.hypot(cx - lx, cy - ly)
                    score = 1.0 - d / max(lw, w, 1.0)
                else:
                    score = _iou(box, anchor) if f < 3 else 0.0
                    score = score if score >= min_iou else 0.0
                if score > best_score:
                    best, best_score = pid, score
            if best is not None:
                owner[k] = best
                live.add(best)
        for pid in bodies:
            mine = [m for k, (m, _) in objs.items() if owner.get(k) == pid]
            if mine:
                mask = np.logical_or.reduce(mine)
                ys, xs = np.nonzero(mask)
                last[pid] = ((xs.min() + xs.max()) / 2, (ys.min() + ys.max()) / 2, float(xs.max() - xs.min()), f)
                out[pid].append(mask)
            else:
                out[pid].append(None)
    return out


def _iou(a, b) -> float:
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


def grow(mask: np.ndarray, px: int) -> np.ndarray:
    if px <= 0:
        return mask
    im = Image.fromarray((mask * 255).astype(np.uint8), "L").filter(ImageFilter.MaxFilter(2 * px + 1))
    return np.asarray(im) > 127


def fill_masks(masks: list[np.ndarray | None]) -> list[np.ndarray]:
    """Frames where the performer wasn't found reuse the nearest found mask (short gaps:
    a missing mask would make the model leave the original person in that frame)."""
    found = [i for i, m in enumerate(masks) if m is not None]
    if not found:
        raise ValueError("performer never found in the shot")
    return [masks[i] if masks[i] is not None else masks[min(found, key=lambda j: abs(j - i))]
            for i in range(len(masks))]


def padded_length(n: int) -> int:
    """Smallest 4k+1 >= n (Wan's latent frame rule)."""
    return n if (n - 1) % 4 == 0 else n + (4 - (n - 1) % 4)


def _write_video(frames: list[np.ndarray], dest: Path, fps: int, *, lossless: bool = False) -> Path:
    h, w = frames[0].shape[:2]
    cmd = [ingest.FFMPEG, "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}",
           "-r", str(fps), "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p",
           *(["-qp", "0"] if lossless else ["-crf", "12"]), str(dest)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    try:
        for fr in frames:
            proc.stdin.write(np.ascontiguousarray(fr, dtype=np.uint8).tobytes())
    finally:
        proc.stdin.close()
        code = proc.wait()
    if code != 0:
        raise RuntimeError(f"writing {dest.name} failed (ffmpeg exit {code})")
    return dest


def read_frames(video: Path) -> list[np.ndarray]:
    info = ingest.probe(video)
    w, h = int(info["width"]), int(info["height"])
    raw = subprocess.run([ingest.FFMPEG, "-v", "error", "-i", str(video), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         capture_output=True, check=True).stdout
    return [f for f in np.frombuffer(raw, np.uint8).reshape(-1, h, w, 3)]


def build_inputs(frames: list[np.ndarray], masks: list[np.ndarray], out_dir: Path, fps: int) -> dict[str, Path]:
    """pose / bg / mask videos for one performer, padded to 4k+1 frames."""
    out_dir.mkdir(parents=True, exist_ok=True)
    n = padded_length(len(frames))
    frames = frames + [frames[-1]] * (n - len(frames))
    masks = masks + [masks[-1]] * (n - len(masks))
    pose, bg, mk = [], [], []
    for fr, m in zip(frames, masks, strict=True):
        keep = grow(m, POSE_GROW_PX)[..., None]
        pose.append(np.where(keep, fr, 127))
        gm = grow(m, GROW_PX)
        bg.append(np.where(gm[..., None], 0, fr))
        mk.append(np.repeat((gm * 255).astype(np.uint8)[..., None], 3, axis=-1))
    return {
        "pose_video": _write_video(pose, out_dir / "pose.mp4", fps),
        "bg_video": _write_video(bg, out_dir / "bg.mp4", fps),
        "mask_video": _write_video(mk, out_dir / "mask.mp4", fps, lossless=True),
    }


def padded_ref(photo: Path, width: int, height: int, dest: Path) -> Path:
    """Reference fitted inside width x height on white (what the model expects)."""
    img = ImageOps.exif_transpose(Image.open(photo)).convert("RGB")
    img.thumbnail((width, height), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (width, height), (255, 255, 255))
    canvas.paste(img, ((width - img.width) // 2, (height - img.height) // 2))
    canvas.save(dest)
    return dest


async def animate_shot(client: ComfyClient, recipe: Recipe, video: Path, source_size: tuple[int, int],
                       performers: dict[str, Subject], refs: dict[str, Path], prompts: dict[str, str], work: Path, *,
                       profile: str, quality: str, seed: int, negative: str = "", report=None,
                       cancelled=None) -> tuple[Path, list[str]]:
    """`video` is the shot normalized (cover-scaled + centre-cropped) to the generation size
    and fps from a clip of `source_size`; performer boxes are in clip pixels. Returns the
    shot with each performer replaced (same size, fps and frame count) and warnings."""
    await ensure_ready(client, recipe, profile)
    work.mkdir(parents=True, exist_ok=True)
    info = await asyncio.to_thread(ingest.probe, video)
    w, h, fps = int(info["width"]), int(info["height"]), round(float(info["fps"]) or 16)
    frames = await asyncio.to_thread(read_frames, video)
    labels = await track_labels(client, video, work / "people", profile=profile, query="person",
                                detect_interval=4, max_objects=8, cancelled=cancelled)
    bodies = {pid: _scale_bbox(s.bbox, source_size, (w, h)) for pid, s in performers.items()}
    tracks = assign_bodies(labels, bodies)
    warnings: list[str] = []
    out = [f.astype(np.float32) for f in frames]
    n_perf = len(tracks)
    for idx, (pid, masks) in enumerate(tracks.items(), start=1):
        if pid not in refs:
            continue
        try:
            filled = fill_masks(masks)
        except ValueError:
            warnings.append(f"{pid}: not found in this shot; left as is")
            continue
        missing = sum(m is None for m in masks)
        if missing > len(masks) // 3:
            warnings.append(f"{pid}: tracked in {len(masks) - missing}/{len(masks)} frames")
        pdir = work / pid
        media = await asyncio.to_thread(build_inputs, frames, filled, pdir, fps)
        clean = await clean_reference(client, refs[pid], pdir, profile=profile)
        media["ref"] = await asyncio.to_thread(padded_ref, clean, w, h, pdir / "ref.png")
        n = padded_length(len(frames))
        values = {"width": w, "height": h, "num_frames": n, "seed": seed, "prompt": prompts.get(pid, ""),
                  "negative_prompt": negative}

        async def progress(stage, frac, msg, _i=idx, _n=n_perf):
            if report is not None and frac >= 0:
                await report("generating", ((_i - 1) + frac) / _n, f"performer {_i}/{_n}: {msg}")

        result = await run_recipe(client, recipe, media=media, values=values, profile=profile, preset=quality,
                                  on_progress=progress, cancelled=cancelled)
        gen_dir = pdir / "frames"
        gen_dir.mkdir(exist_ok=True)
        files = node_files(result, recipe.outputs["frames"])
        gen = []
        for i, f in enumerate(files[: len(frames)]):
            dest = await client.download(f, gen_dir / f"{i:05d}.png")
            with Image.open(dest) as im:
                gen.append(np.asarray(im.convert("RGB").resize((w, h))).astype(np.float32))
        if len(gen) < len(frames):
            warnings.append(f"{pid}: model returned {len(gen)}/{len(frames)} frames")
        for i, g in enumerate(gen):
            a = np.asarray(Image.fromarray((grow(filled[i], GROW_PX) * 255).astype(np.uint8))
                           .filter(ImageFilter.GaussianBlur(2)), np.float32)[..., None] / 255.0
            out[i] = out[i] * (1 - a) + g * a
    dest = work / "out.mp4"
    await asyncio.to_thread(_write_video, [np.clip(f + 0.5, 0, 255).astype(np.uint8) for f in out], dest, fps)
    return dest, warnings
