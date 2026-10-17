"""Pose-guided replacement with Wan2.2-Animate (wan_animate_replace recipe).

Per shot: every person is tracked (SAM 3, re-detecting), each cast performer's per-frame
body mask is found (and, for head styles, their head + neck), and for each performer the
recipe gets
  * a pose video showing only that performer (ViTPose picks one person per frame),
  * the background frames with the region to replace blanked out, and that mask,
  * the character reference padded to the generation size.
Generation runs at the shot's own frame rate (the model doesn't care, and it keeps the
audio in sync); each result is scaled back and pasted inside its feathered mask onto the
original-resolution frames, so everything outside the region is the original pixels.
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
from make_meme.pipelines.detect import Subject
from make_meme.pipelines.runtime import ensure_ready, node_files, run_recipe
from make_meme.pipelines.swap import _perf
from make_meme.pipelines.track import track_labels
from make_meme.recipes.loader import Recipe

GROW_PX = 10  # generation mask margin around the performer (at generation size), as in Wan's preprocessing
BLOCK_PX = 32  # the region handed to the model is blockified, like Wan-Animate's official preprocessing
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


def blockify(mask: np.ndarray, block: int = BLOCK_PX) -> np.ndarray:
    """Every block x block cell touched by the mask becomes fully masked. With an exact
    silhouette the model just fills the person-shaped hole (we got black human silhouettes
    instead of dogs); a coarse region leaves it room to draw the character's own shape."""
    h, w = mask.shape
    gh, gw = -(-h // block), -(-w // block)
    padded = np.zeros((gh * block, gw * block), bool)
    padded[:h, :w] = mask
    cells = padded.reshape(gh, block, gw, block).any(axis=(1, 3))
    return np.repeat(np.repeat(cells, block, axis=0), block, axis=1)[:h, :w]


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


def _write_video(frames: list[np.ndarray], dest: Path, fps: int | str, *, lossless: bool = False) -> Path:
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


def build_inputs(frames: list[np.ndarray], masks: list[np.ndarray], out_dir: Path, fps: int | str,
                 pose_masks: list[np.ndarray] | None = None) -> dict[str, Path]:
    """pose / bg / mask videos for one performer, padded to 4k+1 frames. `masks` is the
    region to regenerate; `pose_masks` (default: the same) is what the pose video keeps."""
    out_dir.mkdir(parents=True, exist_ok=True)
    pose_masks = pose_masks or masks
    n = padded_length(len(frames))
    frames = frames + [frames[-1]] * (n - len(frames))
    masks = masks + [masks[-1]] * (n - len(masks))
    pose_masks = pose_masks + [pose_masks[-1]] * (n - len(pose_masks))
    pose, bg, mk = [], [], []
    for fr, m, pm in zip(frames, masks, pose_masks, strict=True):
        keep = grow(pm, POSE_GROW_PX)[..., None]
        pose.append(np.where(keep, fr, 127))
        gm = blockify(grow(m, GROW_PX))
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


WINDOW = 77  # frames per generation: longer clips switch Wan2.2-Animate to its looping mode, where
#              the background/mask conditioning didn't hold (dogs came back as black silhouettes)
OVERLAP = 5  # frames shared by consecutive windows, crossfaded


def window_ranges(n: int, window: int = WINDOW, overlap: int = OVERLAP) -> list[tuple[int, int]]:
    """[a, b) frame ranges covering n frames, each at most `window` long, consecutive ones
    sharing `overlap` frames."""
    if n <= window:
        return [(0, n)]
    out, a = [], 0
    while True:
        b = min(n, a + window)
        out.append((a, b))
        if b == n:
            return out
        a = b - overlap


async def _generate_window(client, recipe, frames, region, body, ref, wdir, rate, *, profile, quality, seed, prompt,
                           negative, qc, label, warnings, progress, cancelled) -> list[np.ndarray]:
    """One model run over <= WINDOW frames; returns generated frames (generation size, float)."""
    media = await asyncio.to_thread(build_inputs, frames, region, wdir, rate, body)
    media["ref"] = ref
    n = padded_length(len(frames))
    files: list[Path] = []
    for attempt in range(2 if qc else 1):
        values = {"width": frames[0].shape[1], "height": frames[0].shape[0], "num_frames": n, "seed": seed + attempt,
                  "prompt": prompt, "negative_prompt": negative}
        meta = {"profile": profile, "recipe": recipe.name, "width": values["width"], "height": values["height"],
                "frames": n, "steps": int(recipe.preset_values(quality, profile).get("steps", 0))}
        async with _perf(client, f"{label} attempt {attempt + 1}", meta):  # feeds render estimates
            result = await run_recipe(client, recipe, media=media, values=values, profile=profile, preset=quality,
                                      on_progress=progress, cancelled=cancelled)
        gen_dir = wdir / f"frames{attempt}"
        gen_dir.mkdir(parents=True, exist_ok=True)
        files = [await client.download(f, gen_dir / f"{i:05d}.png")
                 for i, f in enumerate(node_files(result, recipe.outputs["frames"])[: len(frames)])]
        if not qc or await looks_replaced(client, files, region, wdir, profile=profile):
            break
        warnings.append(f"{label}: the original person still showed; retried with another seed")
    if len(files) < len(frames):
        warnings.append(f"{label}: model returned {len(files)}/{len(frames)} frames")
    out = []
    for f in files:
        with Image.open(f) as im:
            out.append(np.asarray(im.convert("RGB"), np.float32))
    return out


def head_and_neck(head: np.ndarray, body: np.ndarray, neck: float = 0.45) -> np.ndarray:
    """The head mask plus a neck strip below it (clipped to the body), so a generated head
    joins the original shoulders instead of floating."""
    ys, xs = np.nonzero(head)
    if len(xs) == 0:
        return head
    x1, x2, y1, y2 = xs.min(), xs.max(), ys.min(), ys.max()
    w, h = x2 - x1 + 1, y2 - y1 + 1
    strip = np.zeros_like(head)
    strip[y2 - int(0.1 * h):min(head.shape[0], y2 + int(neck * h)), x1 + int(0.2 * w):x2 - int(0.2 * w) + 1] = True
    return head | (strip & grow(body, 4))


def resize_mask(mask: np.ndarray, width: int, height: int) -> np.ndarray:
    return np.asarray(Image.fromarray((mask * 255).astype(np.uint8)).resize((width, height),
                                                                             Image.Resampling.BILINEAR)) > 127


def frame_rate(video: Path) -> str:
    out = subprocess.run([ingest.FFPROBE, "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=r_frame_rate",
                          "-of", "default=nw=1:nk=1", str(video)], capture_output=True, text=True, check=True)
    return out.stdout.strip() or "24"


async def looks_replaced(client: ComfyClient, frames: list[Path], masks: list[np.ndarray], work: Path, *,
                         profile: str, query: str = "animal") -> bool:
    """QC: does the regenerated region show the pet (not the original person)? Checks a
    few frames, cropped to the region, with SAM 3."""
    from make_meme.pipelines.detect import detect_in_image

    picks = sorted({0, len(frames) // 2, len(frames) - 1})
    hits = 0
    for i in picks:
        ys, xs = np.nonzero(masks[i])
        if len(xs) == 0:
            continue
        with Image.open(frames[i]) as im:
            sx, sy = im.width / masks[i].shape[1], im.height / masks[i].shape[0]
            crop = im.convert("RGB").crop((int(xs.min() * sx), int(ys.min() * sy), int(xs.max() * sx) + 1,
                                           int(ys.max() * sy) + 1))
        path = work / f"qc_{i:05d}.png"
        crop.save(path)
        if await detect_in_image(client, path, f"{query}:1", work / f"qc_{i:05d}", profile=profile, min_area_frac=0.05):
            hits += 1
    return hits * 2 >= len(picks)


async def animate_shot(client: ComfyClient, recipe: Recipe, piece: Path, performers: dict[str, Subject],
                       refs: dict[str, Path], prompts: dict[str, str], work: Path, *, profile: str, quality: str,
                       gen_size: tuple[int, int], seed: int, negative: str = "", mask_mode: str = "full_body",
                       qc: bool = True, report=None, cancelled=None) -> tuple[Path, list[str]]:
    """Replace each performer in `piece` (one shot, at the clip's resolution and frame rate;
    performer boxes in its pixels) with their reference. Returns (video with the same size,
    frame rate and frame count, warnings)."""
    from make_meme.pipelines.paste import assign_heads
    from make_meme.pipelines.track import downscale

    await ensure_ready(client, recipe, profile)
    work.mkdir(parents=True, exist_ok=True)
    info = await asyncio.to_thread(ingest.probe, piece)
    width, height = int(info["width"]), int(info["height"])
    rate = await asyncio.to_thread(frame_rate, piece)
    gw, gh = gen_size
    frames = await asyncio.to_thread(read_frames, piece)
    small, factor = await asyncio.to_thread(downscale, piece, work / "track_in.mp4")
    labels = await track_labels(client, small, work / "people", profile=profile, query="person",
                                detect_interval=4, max_objects=8, cancelled=cancelled)
    bodies = {pid: tuple(int(v / factor) for v in s.bbox) for pid, s in performers.items() if pid in refs}
    body_tracks = assign_bodies(labels, bodies)
    head_tracks = {}
    if mask_mode == "head":
        head_labels = await track_labels(client, small, work / "heads", profile=profile, cancelled=cancelled)
        head_tracks = assign_heads(head_labels, bodies)
    warnings: list[str] = []
    gen_frames = [np.asarray(Image.fromarray(f).resize((gw, gh), Image.Resampling.LANCZOS)) for f in frames]
    out = [f.astype(np.float32) for f in frames]
    todo = list(bodies)
    n_todo = len(todo)
    for idx, pid in enumerate(todo, start=1):
        try:
            body = fill_masks(body_tracks[pid])
        except ValueError:
            warnings.append(f"{pid}: not found in this shot; left as is")
            continue
        region = body
        if mask_mode == "head":
            try:
                heads = fill_masks(head_tracks.get(pid, []))
            except ValueError:
                warnings.append(f"{pid}: no head found in this shot; left as is")
                continue
            region = [head_and_neck(h, b) for h, b in zip(heads, body, strict=True)]
        missing = sum(m is None for m in body_tracks[pid])
        if missing > len(body) // 3:
            warnings.append(f"{pid}: tracked in {len(body) - missing}/{len(body)} frames")
        region_gen = [resize_mask(m, gw, gh) for m in region]
        body_gen = [resize_mask(m, gw, gh) for m in body]
        pdir = work / pid
        pdir.mkdir(parents=True, exist_ok=True)
        ref = await asyncio.to_thread(padded_ref, refs[pid], gw, gh, pdir / "ref.png")
        gen: list[np.ndarray | None] = [None] * len(frames)
        windows = window_ranges(len(frames))
        n_windows = len(windows)
        for w_i, (a, b) in enumerate(windows):

            async def progress(stage, frac, msg, _i=idx, _n=n_todo, _w=w_i, _nw=n_windows):
                if report is not None and frac >= 0:
                    await report("generating", ((_i - 1) + (_w + frac) / _nw) / _n,
                                 f"performer {_i}/{_n}, part {_w + 1}/{_nw}: {msg}")

            part = await _generate_window(
                client, recipe, gen_frames[a:b], region_gen[a:b], body_gen[a:b], ref, pdir / f"w{w_i}", rate,
                profile=profile, quality=quality, seed=seed, prompt=prompts.get(pid, ""), negative=negative,
                qc=qc and mask_mode != "head", label=pid, warnings=warnings, progress=progress, cancelled=cancelled)
            for j, g in enumerate(part):
                i = a + j
                if gen[i] is None:
                    gen[i] = g
                else:  # overlap with the previous window: crossfade so the seam doesn't jump
                    t = (j + 1) / (OVERLAP + 1)
                    gen[i] = gen[i] * (1 - t) + g * t
        for i, g in enumerate(gen):
            if g is None:
                continue
            g_full = np.asarray(Image.fromarray(np.clip(g + 0.5, 0, 255).astype(np.uint8)).resize(
                (width, height), Image.Resampling.LANCZOS), np.float32)
            # paste back the whole region the model regenerated (blocks), feathered
            m = resize_mask(blockify(grow(region_gen[i], GROW_PX)), width, height)
            alpha = np.asarray(Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(3)),
                               np.float32)[..., None] / 255.0
            out[i] = out[i] * (1 - alpha) + g_full * alpha
    dest = work / "out.mp4"
    await asyncio.to_thread(_write_video, [np.clip(f + 0.5, 0, 255).astype(np.uint8) for f in out], dest, rate)
    return dest, warnings
