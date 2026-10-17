"""The "pasted pet head" edit: no generation, just a tracked cut-out.

SAM 3 tracks every head in a shot (re-detecting every few frames, so heads lost to fast
motion or turns are picked up again); each tracked head is tied to a cast performer by
where it first appears (inside the performer's body box at the start, or next to where
that performer's head was last seen). Each frame's head mask gives a position, width and
tilt, smoothed with a One-Euro filter, and the pet's head cut-out is pasted there at the
video's own resolution and frame rate.
"""

from __future__ import annotations

import asyncio
import math
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter, ImageOps

from make_meme import ingest
from make_meme.comfy.client import ComfyClient
from make_meme.pipelines.detect import Subject, detect_in_image
from make_meme.pipelines.track import downscale, track_labels

MIN_HEAD_PX = 30  # head masks smaller than this (in tracking pixels) count as "lost"
MAX_TILT = 45.0
TRACK_STRIDE = 2


@dataclass
class HeadPose:
    cx: float
    cy: float
    size: float  # head width across its main axis, in pixels (long hair stretches the length, not the width)
    angle: float  # degrees; positive = top of the head leans to the right (clockwise)


def head_pose(mask: np.ndarray, scale: float = 1.0) -> HeadPose | None:
    """Pose of a head from its mask via second moments (an ellipse fit)."""
    ys, xs = np.nonzero(mask)
    if len(xs) < MIN_HEAD_PX:
        return None
    cx, cy = xs.mean(), ys.mean()
    cov = np.cov(np.stack([xs - cx, ys - cy]))
    vals, vecs = np.linalg.eigh(cov)
    major = vecs[:, 1]  # largest eigenvalue
    vx, vy = float(major[0]), float(major[1])
    if vy > 0:  # point the axis up the head (image y grows downward)
        vx, vy = -vx, -vy
    elongation = math.sqrt(max(vals[1], 1e-6) / max(vals[0], 1e-6))
    angle = math.degrees(math.atan2(vx, -vy)) if elongation > 1.15 else 0.0  # round blobs have no axis
    if abs(angle) > 90:  # a head lying sideways reads as a wide blob; keep tilt sane
        angle = 0.0
    angle = max(-MAX_TILT, min(MAX_TILT, angle))
    size = 4.0 * math.sqrt(max(vals[0], 1.0))  # full width of the fitted ellipse (minor axis)
    return HeadPose(cx * scale, cy * scale, size * scale, angle)


def _centre_and_width(mask: np.ndarray) -> tuple[float, float, float] | None:
    ys, xs = np.nonzero(mask)
    if len(xs) < MIN_HEAD_PX:
        return None
    return float(xs.mean()), float(ys.mean()), float(xs.max() - xs.min() + 1)


def assign_heads(labels: list[np.ndarray], bodies: dict[str, tuple[int, int, int, int]],
                 max_gap: int = 12) -> dict[str, list[np.ndarray | None]]:
    """Tie tracked heads (label maps from track_labels) to performers.

    `bodies` are the performers' body boxes on the first frame (label-map pixels). A tracked
    object belongs to a performer for good once claimed: at the start, the head nearest the
    top-centre of a performer's body box (and inside it); later, an unclaimed head that
    appears near where a performer's head was last seen, within `max_gap` frames.
    Heads of other people are never claimed."""
    owner: dict[int, str] = {}
    last: dict[str, tuple[float, float, float, int]] = {}  # performer -> (cx, cy, width, frame)
    out: dict[str, list[np.ndarray | None]] = {pid: [] for pid in bodies}
    for f, lab in enumerate(labels):
        objs = {}
        for k in np.unique(lab):
            if k == 0:
                continue
            m = lab == k
            if (cw := _centre_and_width(m)) is not None:
                objs[int(k)] = (m, cw)
        live = {owner[k] for k in objs if k in owner}
        for k, (_m, (cx, cy, w)) in sorted(objs.items()):
            if k in owner:
                continue
            best, best_d = None, float("inf")
            for pid, (x1, y1, x2, y2) in bodies.items():
                if pid in live:
                    continue
                if pid in last:
                    lx, ly, lw, lf = last[pid]
                    if f - lf > max_gap:
                        continue
                    d = math.hypot(cx - lx, cy - ly)
                    if d > 1.5 * max(lw, w) + 0.15 * (f - lf) * lw:
                        continue
                else:
                    pad = 0.1 * (x2 - x1)
                    if not (x1 - pad <= cx <= x2 + pad and y1 - pad <= cy <= y1 + 0.6 * (y2 - y1)):
                        continue
                    d = math.hypot(cx - (x1 + x2) / 2, cy - (y1 + 0.1 * (y2 - y1)))
                if d < best_d:
                    best, best_d = pid, d
            if best is not None:
                owner[k] = best
                live.add(best)
        for pid in bodies:
            mine = [m for k, (m, _) in objs.items() if owner.get(k) == pid]
            if mine:
                mask = np.logical_or.reduce(mine)
                cw = _centre_and_width(mask)
                if cw is not None:
                    last[pid] = (*cw, f)
                out[pid].append(mask)
            else:
                out[pid].append(None)
    return out


def expand_poses(poses: list[HeadPose | None], n: int, stride: int) -> list[HeadPose | None]:
    """Poses tracked on every `stride`-th frame -> all `n` frames (linear in between)."""
    if stride == 1:
        return (poses + [None] * n)[:n]
    out: list[HeadPose | None] = []
    for i in range(n):
        j, r = divmod(i, stride)
        a = poses[j] if j < len(poses) else None
        b = poses[j + 1] if j + 1 < len(poses) else None
        if r == 0 or a is None or b is None:
            out.append(a if a is not None else (b if r * 2 >= stride else None))
            continue
        t = r / stride
        out.append(HeadPose(*(x + (y - x) * t for x, y in zip((a.cx, a.cy, a.size, a.angle),
                                                               (b.cx, b.cy, b.size, b.angle), strict=True))))
    return out


class OneEuro:
    """One-Euro filter (Casiez et al. 2012): smooth when still, responsive when moving."""

    def __init__(self, fps: float, min_cutoff: float = 1.2, beta: float = 0.03, d_cutoff: float = 1.0) -> None:
        self.rate, self.min_cutoff, self.beta, self.d_cutoff = fps, min_cutoff, beta, d_cutoff
        self.x: float | None = None
        self.dx = 0.0

    def _alpha(self, cutoff: float) -> float:
        tau = 1.0 / (2 * math.pi * cutoff)
        return 1.0 / (1.0 + tau * self.rate)

    def __call__(self, x: float) -> float:
        if self.x is None:
            self.x = x
            return x
        dx = (x - self.x) * self.rate
        self.dx += self._alpha(self.d_cutoff) * (dx - self.dx)
        cutoff = self.min_cutoff + self.beta * abs(self.dx)
        self.x += self._alpha(cutoff) * (x - self.x)
        return self.x


def smooth_poses(poses: list[HeadPose | None], fps: float, hold_frames: int) -> list[tuple[HeadPose, float] | None]:
    """Smoothed (pose, opacity) per frame. Short losses hold the last pose; longer ones hide
    the head. Opacity ramps over a few frames so heads don't pop in and out."""
    filters = [OneEuro(fps) for _ in range(4)]
    out: list[tuple[HeadPose, float] | None] = []
    last: HeadPose | None = None
    missing = 0
    fade = max(1, round(fps * 0.1))
    opacity = 0.0
    for p in poses:
        if p is not None:
            vals = [f(v) for f, v in zip(filters, (p.cx, p.cy, p.size, p.angle), strict=True)]
            last = HeadPose(*vals)
            missing = 0
            # Visible from the shot's first frame: no fade. Reappearing after a hide: fade in.
            opacity = 1.0 if not out else min(1.0, opacity + 1.0 / fade)
            out.append((last, opacity))
        elif last is not None and missing < hold_frames:
            missing += 1
            out.append((last, opacity))
        else:
            out.append(None)
            opacity = 0.0
    return out


def cutout_from_mask(photo: Image.Image, mask: Image.Image, feather: float = 1.5) -> Image.Image:
    """RGBA crop of the masked region with a slightly eroded, feathered edge."""
    alpha = mask.convert("L").resize(photo.size).point(lambda v: 255 if v > 127 else 0)
    alpha = alpha.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(feather))
    rgba = photo.convert("RGB").copy()
    rgba.putalpha(alpha)
    bbox = alpha.point(lambda v: 255 if v > 32 else 0).getbbox()
    return rgba.crop(bbox) if bbox else rgba


async def head_cutout(client: ComfyClient, photo_path: Path, *, profile: str) -> Image.Image | None:
    """The pet's head (SAM 3 'head', else the whole animal) from a reference photo."""
    photo = ImageOps.exif_transpose(Image.open(photo_path)).convert("RGB")
    with tempfile.TemporaryDirectory(prefix="mm-cutout-") as tmp:
        for query in ("head:1", "animal:1", "person:1"):
            found = await detect_in_image(client, photo_path, query, Path(tmp), profile=profile, min_area_frac=0.01)
            if found:
                with Image.open(found[0].mask_path) as m:
                    return cutout_from_mask(photo, m.copy())
    return None


def paste_head(frame: Image.Image, cutout: Image.Image, pose: HeadPose, opacity: float, *,
               scale: float, lift: float) -> None:
    """Paste `cutout` onto `frame` (RGB, in place) centred on the head pose. Its geometric
    mean side (sqrt(w*h)) becomes `scale` times the performer's head width, so a cut-out made
    wide by floppy ears or tall by a hanging tongue isn't blown up."""
    k = pose.size * scale / math.sqrt(cutout.width * cutout.height)
    target_w, target_h = max(4, int(cutout.width * k)), max(4, int(cutout.height * k))
    head = cutout.resize((target_w, target_h), Image.Resampling.LANCZOS)
    if abs(pose.angle) > 0.5:
        head = head.rotate(-pose.angle, resample=Image.Resampling.BICUBIC, expand=True)  # PIL rotates CCW
    if opacity < 1.0:
        a = head.getchannel("A").point(lambda v: int(v * opacity))
        head.putalpha(a)
    # Lift along the head's own axis so a tilted head stays on the neck line.
    rad = math.radians(pose.angle)
    dx, dy = math.sin(rad) * lift * target_h, -math.cos(rad) * lift * target_h
    x = round(pose.cx + dx - head.width / 2)
    y = round(pose.cy + dy - head.height / 2)
    frame.paste(head, (x, y), head)


def composite_heads(video: Path, dest: Path, layers: list[tuple[Image.Image, list[tuple[HeadPose, float] | None]]],
                    *, scale: float, lift: float) -> Path:
    """Stream `video` frame by frame, pasting each layer's cut-out at its per-frame pose."""
    info = ingest.probe(video)
    w, h = int(info["width"]), int(info["height"])
    rate = _frame_rate(video)
    frame_bytes = w * h * 3
    reader = subprocess.Popen([ingest.FFMPEG, "-v", "error", "-i", str(video), "-f", "rawvideo",
                               "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    tmp = dest.with_name(f"{dest.stem}.tmp{dest.suffix}")
    writer = subprocess.Popen([ingest.FFMPEG, "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                               "-s", f"{w}x{h}", "-r", rate, "-i", "-", "-c:v", "libx264", "-crf", "16",
                               "-pix_fmt", "yuv420p", str(tmp)], stdin=subprocess.PIPE)
    n = 0
    try:
        while len(buf := reader.stdout.read(frame_bytes)) == frame_bytes:
            frame = Image.frombuffer("RGB", (w, h), buf, "raw", "RGB", 0, 1).copy()
            for cutout, poses in layers:
                if n < len(poses) and poses[n] is not None:
                    pose, opacity = poses[n]
                    paste_head(frame, cutout, pose, opacity, scale=scale, lift=lift)
            writer.stdin.write(frame.tobytes())
            n += 1
    finally:
        reader.stdout.close()
        reader.kill()
        reader.wait()
        writer.stdin.close()
        code = writer.wait()
    if code != 0 or n == 0:
        tmp.unlink(missing_ok=True)
        raise RuntimeError(f"pasting heads onto {video.name} failed (ffmpeg exit {code}, {n} frames)")
    tmp.replace(dest)
    return dest


def _frame_rate(video: Path) -> str:
    """Exact frame rate as ffprobe reports it (e.g. 24000/1001), so the output keeps the input's timing."""
    out = subprocess.run([ingest.FFPROBE, "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=r_frame_rate", "-of", "default=nw=1:nk=1", str(video)],
                         capture_output=True, text=True, check=True).stdout.strip()
    return out or "24"


async def paste_shot(client: ComfyClient, piece: Path, performers: dict[str, Subject],
                     cutouts: dict[str, Image.Image], work: Path, *, profile: str, scale: float, lift: float,
                     hold_sec: float, cancelled=None) -> tuple[Path, list[str]]:
    """Paste each performer's pet head onto `piece` (one shot). `performers` maps performer id
    to their subject on the shot's first frame (in `piece` pixel coordinates).
    Returns (video, warnings)."""
    work.mkdir(parents=True, exist_ok=True)
    warnings: list[str] = []
    info = await asyncio.to_thread(ingest.probe, piece)
    fps = float(info["fps"]) or 24.0
    stride = TRACK_STRIDE if fps > 20 else 1  # track every other frame of 24-60 fps video
    small, factor = await asyncio.to_thread(downscale, piece, work / "track_in.mp4", stride=stride)
    wanted = {pid: s for pid, s in performers.items() if pid in cutouts}
    if not wanted:
        return piece, warnings
    labels = await track_labels(client, small, work / "track", profile=profile, cancelled=cancelled)
    bodies = {pid: tuple(int(v / factor) for v in s.bbox) for pid, s in wanted.items()}
    heads = assign_heads(labels, bodies, max_gap=max(2, 12 // stride))
    layers = []
    for pid, masks in heads.items():
        tracked = [head_pose(m, scale=factor) if m is not None else None for m in masks]
        poses = expand_poses(tracked, int(info["frame_count"]), stride)
        seen = sum(p is not None for p in poses)
        if seen == 0:
            warnings.append(f"{pid}: no head found in this shot; left as is")
            continue
        if seen < len(poses) // 2:
            warnings.append(f"{pid}: head found in {seen}/{len(poses)} frames")
        layers.append((cutouts[pid], smooth_poses(poses, fps, hold_frames=round(hold_sec * fps))))
    if not layers:
        return piece, warnings
    out = await asyncio.to_thread(composite_heads, piece, work / "out.mp4", layers, scale=scale, lift=lift)
    return out, warnings
