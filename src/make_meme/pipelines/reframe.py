"""Auto-reframe a landscape clip to a vertical (or any) aspect that follows the subjects,
like short-form editors do. Subjects are located with SAM 3 about once per second; the
crop window pans along a smoothed path through their centers and is clamped so it never
leaves the frame. Rendering is a single ffmpeg crop with a piecewise-linear x/y(t)."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from itertools import pairwise
from pathlib import Path

from make_meme import ingest
from make_meme.comfy.client import ComfyClient
from make_meme.pipelines.detect import detect_in_image

logger = logging.getLogger(__name__)


@dataclass
class Keyframe:
    t: float
    box: tuple[int, int, int, int] | None  # union of subjects, source pixels


def parse_aspect(aspect: str) -> float:
    w, _, h = aspect.partition(":")
    try:
        value = float(w) / float(h)
    except (ValueError, ZeroDivisionError):
        raise ValueError(f"aspect must look like '9:16', got {aspect!r}") from None
    if not 0.2 <= value <= 5:
        raise ValueError(f"aspect {aspect!r} is out of range")
    return value


def crop_size(src_w: int, src_h: int, aspect: float) -> tuple[int, int]:
    """Largest even-sized window of `aspect` inside the source."""
    if src_w / src_h > aspect:
        h = src_h
        w = round(h * aspect)
    else:
        w = src_w
        h = round(w / aspect)
    return w - w % 2, h - h % 2


def plan_path(keys: list[Keyframe], src: tuple[int, int], win: tuple[int, int]) -> list[tuple[float, int, int]]:
    """(t, x, y) top-left positions: centered on the subjects, gaps filled from neighbours,
    lightly smoothed (3-point average) and clamped to the frame."""
    sw, sh = src
    ww, wh = win
    centers: list[tuple[float, float, float] | None] = []
    for k in keys:
        if k.box is None:
            centers.append(None)
        else:
            x1, y1, x2, y2 = k.box
            centers.append((k.t, (x1 + x2) / 2, (y1 + y2) / 2))
    known = [c for c in centers if c is not None]
    if not known:
        return [(0.0, (sw - ww) // 2, (sh - wh) // 2)]
    filled = []
    for k, c in zip(keys, centers):
        if c is None:  # nearest known center in time
            c = min(known, key=lambda kc: abs(kc[0] - k.t))
            c = (k.t, c[1], c[2])
        filled.append(c)
    smooth = []
    for i, (t, cx, cy) in enumerate(filled):
        window = filled[max(0, i - 1) : i + 2]
        smooth.append((t, sum(w[1] for w in window) / len(window), sum(w[2] for w in window) / len(window)))
    out = []
    for k, (t, cx, cy) in zip(keys, smooth):
        x, y = cx - ww / 2, cy - wh / 2
        if k.box is not None:  # smoothing must never push a subject out of the window
            x1, y1, x2, y2 = k.box
            if x2 - x1 <= ww:
                x = min(max(x, x2 - ww), x1)
            if y2 - y1 <= wh:
                y = min(max(y, y2 - wh), y1)
        x = int(min(max(x, 0), sw - ww))
        y = int(min(max(y, 0), sh - wh))
        out.append((round(t, 3), x, y))
    return out


def _piecewise(points: list[tuple[float, int]]) -> str:
    """ffmpeg expression for a piecewise-linear function of t through `points`."""
    if len(points) == 1:
        return str(points[0][1])
    expr = str(points[-1][1])
    for (t0, v0), (t1, v1) in reversed(list(pairwise(points))):
        slope = (v1 - v0) / max(t1 - t0, 1e-6)
        expr = f"if(lt(t,{t1}),{v0}+({slope:.4f})*(t-{t0}),{expr})"
    return expr


def crop_filter(path: list[tuple[float, int, int]], win: tuple[int, int]) -> str:
    xs = _piecewise([(t, x) for t, x, _ in path])
    ys = _piecewise([(t, y) for t, _, y in path])
    return f"crop={win[0]}:{win[1]}:x='{xs}':y='{ys}'"


async def reframe(
    client: ComfyClient,
    video: Path,
    dest: Path,
    *,
    aspect: str = "9:16",
    query: str = "person, animal",
    profile: str,
    step_sec: float = 1.0,
) -> tuple[Path, list[tuple[float, int, int]], bool]:
    """Returns (output path, crop path, all_subjects_fit). Audio is kept."""
    info = await asyncio.to_thread(ingest.probe, video)
    src = (int(info["width"]), int(info["height"]))
    win = crop_size(*src, parse_aspect(aspect))
    # sample strictly inside the video stream (containers often run a little longer than it)
    duration = float(info["frame_count"]) / float(info["fps"]) if info.get("fps") else float(info["duration"])
    last = max(0.0, duration - 0.2)
    times = [round(i * step_sec, 3) for i in range(int(last / step_sec) + 1)]
    if last - times[-1] > 0.3:
        times.append(round(last, 3))
    work = dest.parent / f"{dest.stem}_frames"
    work.mkdir(parents=True, exist_ok=True)
    keys: list[Keyframe] = []
    fits = True
    for t in times:
        frame = work / f"t{t:.2f}.png"
        (await asyncio.to_thread(ingest.extract_frame, video, t)).save(frame)
        subjects = await detect_in_image(client, frame, query, work / f"det{t:.2f}", profile=profile)
        if not subjects:
            keys.append(Keyframe(t, None))
            continue
        box = (min(s.bbox[0] for s in subjects), min(s.bbox[1] for s in subjects),
               max(s.bbox[2] for s in subjects), max(s.bbox[3] for s in subjects))
        fits = fits and (box[2] - box[0]) <= win[0] and (box[3] - box[1]) <= win[1]
        keys.append(Keyframe(t, box))
    path = plan_path(keys, src, win)
    vf = crop_filter(path, win)
    await asyncio.to_thread(
        ingest._run,
        [ingest.FFMPEG, "-y", "-i", str(video), "-vf", vf, "-c:v", "libx264", "-crf", "16",
         "-pix_fmt", "yuv420p", "-c:a", "copy", str(dest)],
    )
    return dest, path, fits
