"""The "pasted pet head" edit: no generation, just a tracked cut-out.

For each cast performer in a shot, SAM 3 tracks their head through the shot; each
frame's head mask gives a position, size and tilt, smoothed with a One-Euro filter, and
the pet's head cut-out is pasted there at the video's own resolution and frame rate.
"""

from __future__ import annotations

import asyncio
import math
import subprocess
import tempfile
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter, ImageOps

from make_meme import ingest
from make_meme.comfy.client import ComfyClient
from make_meme.pipelines.detect import Subject, detect_in_image, head_mask_within
from make_meme.pipelines.track import downscale, track_masks

MIN_HEAD_PX = 30  # head masks smaller than this (in tracking pixels) count as "lost"
MAX_TILT = 45.0


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
    """Paste `cutout` onto `frame` (RGB, in place) centred on the head pose, `scale` times as
    wide as the performer's head."""
    target_w = max(4, int(pose.size * scale))
    target_h = max(4, int(cutout.height * target_w / cutout.width))
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
    small, factor = await asyncio.to_thread(downscale, piece, work / "track_in.mp4")
    frame0 = work / "frame0.png"
    (await asyncio.to_thread(ingest.extract_frame, small, 0.0)).save(frame0)
    layers = []
    for pid, subject in performers.items():
        if pid not in cutouts:
            continue
        sx1, sy1, sx2, sy2 = subject.bbox
        scaled = replace(subject, bbox=(int(sx1 / factor), int(sy1 / factor), int(sx2 / factor), int(sy2 / factor)))
        head = await head_mask_within(client, frame0, scaled, work / f"{pid}_head", profile=profile, neck=0.0)
        if head is None:
            warnings.append(f"{pid}: no head visible at the start of the shot; left as is")
            continue
        masks = await track_masks(client, small, head, work / f"{pid}_track", profile=profile, cancelled=cancelled)
        poses = [head_pose(m, scale=factor) for m in masks]
        if sum(p is not None for p in poses) < max(1, len(poses) // 5):
            warnings.append(f"{pid}: head tracked in only {sum(p is not None for p in poses)}/{len(poses)} frames")
        layers.append((cutouts[pid], smooth_poses(poses, fps, hold_frames=round(hold_sec * fps))))
    if not layers:
        return piece, warnings
    out = await asyncio.to_thread(composite_heads, piece, work / "out.mp4", layers, scale=scale, lift=lift)
    return out, warnings
