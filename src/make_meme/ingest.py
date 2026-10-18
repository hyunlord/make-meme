"""Video ingestion: trim, probe, normalize, extract frames, storyboard, suggest segments.

All functions here are blocking (they shell out to ffmpeg/ffprobe); callers on
the MCP event loop should run them via ``asyncio.to_thread``.

Fetching media from URLs/search is owned by ``make_meme.sources`` -- this
module only ever operates on local files that are already on disk.
"""

from __future__ import annotations

import io
import json
import logging
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from .assets import Asset, AssetStore

logger = logging.getLogger(__name__)

MAX_RECOMMENDED_CLIP_SECONDS = 15.0
FFMPEG = "ffmpeg"
FFPROBE = "ffprobe"


_STDERR_TAIL_LINES = 8


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    logger.debug("running: %s", " ".join(cmd))
    proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if proc.returncode != 0:
        tail = "\n".join(proc.stderr.strip().splitlines()[-_STDERR_TAIL_LINES:])
        raise RuntimeError(f"command failed ({proc.returncode}): {' '.join(cmd)}\nstderr (tail):\n{tail}")
    return proc


def _parse_rate(rate: str) -> float:
    if "/" in rate:
        num, _, den = rate.partition("/")
        try:
            num_f, den_f = float(num), float(den)
            return num_f / den_f if den_f else 0.0
        except ValueError:
            return 0.0
    try:
        return float(rate)
    except ValueError:
        return 0.0


def _display_rotation_degrees(stream: dict[str, Any]) -> int:
    """Return the net display rotation (one of 0, 90, 180, 270) from ffprobe stream metadata.

    Checks the classic ``tags.rotate`` tag first, then a "Display Matrix" entry
    in ``side_data_list`` (the form modern ffmpeg/ffprobe uses). Either can
    report a rotation that doesn't match the stream's *coded* width/height --
    e.g. a phone video shot with the sensor landscape but a rotate=90 tag
    telling players (and ffmpeg's own auto-rotate on decode) to display it
    portrait.
    """

    rotate_tag = (stream.get("tags") or {}).get("rotate")
    if rotate_tag is not None:
        try:
            return int(rotate_tag) % 360
        except (TypeError, ValueError):
            pass
    for side_data in stream.get("side_data_list") or []:
        if side_data.get("side_data_type") == "Display Matrix" and "rotation" in side_data:
            try:
                return round(float(side_data["rotation"])) % 360
            except (TypeError, ValueError):
                continue
    return 0


def probe(path: Path) -> dict[str, Any]:
    """Probe a media file with ffprobe: duration, fps, width, height, has_audio, frame_count.

    ``width``/``height`` are *display* dimensions: swapped from the coded
    dimensions when the stream carries a +-90 degree rotation (see
    :func:`_display_rotation_degrees`), matching what ffmpeg will actually
    output when it decodes/re-encodes the file (auto-rotate is on by default).
    """

    proc = _run(
        [
            FFPROBE,
            "-v", "error",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            str(path),
        ]
    )
    data = json.loads(proc.stdout)
    streams = data.get("streams", [])
    video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)
    if video_stream is None:
        raise ValueError(f"no video stream found in {path}")

    fps = _parse_rate(video_stream.get("r_frame_rate", "0/1"))
    duration = float(data.get("format", {}).get("duration") or video_stream.get("duration") or 0.0)
    width = int(video_stream.get("width", 0))
    height = int(video_stream.get("height", 0))
    if _display_rotation_degrees(video_stream) in (90, 270):
        width, height = height, width
    nb_frames = video_stream.get("nb_frames")
    frame_count = int(nb_frames) if nb_frames and str(nb_frames).isdigit() else round(duration * fps)

    return {
        "duration": duration,
        "fps": fps,
        "width": width,
        "height": height,
        "has_audio": audio_stream is not None,
        "frame_count": frame_count,
    }


def prepare_clip(
    src: Path,
    start_sec: float | None = None,
    end_sec: float | None = None,
    *,
    parent_ids: list[str] | None = None,
    extra_origin: dict[str, Any] | None = None,
) -> Asset:
    """Trim ``src`` to ``[start_sec, end_sec]`` and register the result as a new video Asset.

    The trimmed clip is re-encoded (h264+aac) for frame accuracy, then handed
    to :class:`~make_meme.assets.AssetStore`, which copies it into its own
    managed directory. Also writes, alongside it, an extracted audio track
    (``audio.m4a``, referenced by ``meta["audio_path"]``) if the clip has
    audio, and a first-frame preview (``preview.jpg``, referenced by
    ``meta["preview_path"]``). Adds a warning to ``meta["warnings"]`` if the
    clip exceeds :data:`MAX_RECOMMENDED_CLIP_SECONDS`.
    """

    with tempfile.TemporaryDirectory(prefix="make-meme-clip-") as tmp:
        trimmed = Path(tmp) / "clip.mp4"
        # -ss/-t placed after -i for frame-accurate trimming (we re-encode anyway).
        cmd = [FFMPEG, "-y", "-i", str(src)]
        if start_sec is not None:
            cmd += ["-ss", str(start_sec)]
        if end_sec is not None:
            duration = max(end_sec - (start_sec or 0.0), 0.0)
            cmd += ["-t", str(duration)]
        cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(trimmed)]
        _run(cmd)

        clip_meta = probe(trimmed)
        warnings: list[str] = []
        if clip_meta["duration"] > MAX_RECOMMENDED_CLIP_SECONDS:
            warnings.append(
                f"Clip is {clip_meta['duration']:.1f}s, longer than the recommended "
                f"{MAX_RECOMMENDED_CLIP_SECONDS:.0f}s; generation will be slow and may run in "
                "many chunks."
            )

        origin = {"source": str(src), "start_sec": start_sec, "end_sec": end_sec}
        origin.update(extra_origin or {})

        store = AssetStore()
        asset = store.add(
            trimmed,
            "video",
            origin=origin,
            meta={"warnings": warnings},
            parent_ids=parent_ids,
        )

        # AssetStore.add() already extracted a first-frame preview (meta["preview_path"])
        # for this video kind; only the audio track is this function's own concern.
        asset_dir = asset.path.parent
        if clip_meta["has_audio"]:
            audio_path = asset_dir / "audio.m4a"
            _run([FFMPEG, "-y", "-i", str(asset.path), "-vn", "-c:a", "aac", str(audio_path)])
            asset.meta["audio_path"] = str(audio_path)
            asset.save(asset_dir)

        return asset


def normalize(video_id_or_path: Path, width: int, height: int, fps: int = 16) -> Path:
    """Scale+center-crop a video to exactly ``width``x``height`` at ``fps``, no audio.

    ``width``/``height`` should already be multiples of 16 (the Wan models'
    requirement); this does not round them itself. Idempotent by output
    filename, written next to ``video_id_or_path``.
    """

    source_path = Path(video_id_or_path)
    out_path = source_path.parent / f"normalized_{width}x{height}_{fps}fps.mp4"
    if out_path.exists():
        return out_path

    scale_filter = (
        f"scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height},setsar=1,fps={fps}"  # square pixels: models output SAR 1:1
    )
    # Encode to a temp file first and atomically rename into place, so a crash/interrupt
    # mid-encode can never leave a truncated file behind that the exists()-check above
    # would mistake for a valid, complete cache entry. Keep the .mp4 suffix last -- ffmpeg
    # infers the output container from the file extension.
    tmp_path = out_path.with_name(f"{out_path.stem}.tmp{out_path.suffix}")
    try:
        _run(
            [
                FFMPEG, "-y", "-i", str(source_path),
                "-vf", scale_filter,
                "-an",
                "-c:v", "libx264", "-pix_fmt", "yuv420p",
                str(tmp_path),
            ]
        )
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise
    os.replace(tmp_path, out_path)
    return out_path


def extract_frame(video_path: Path, at_sec: float) -> Image.Image:
    """Extract a single frame at ``at_sec`` as a PIL Image."""

    proc = subprocess.run(
        [
            FFMPEG, "-y",
            "-i", str(video_path),
            "-ss", str(at_sec),
            "-vframes", "1",
            "-f", "image2pipe",
            "-vcodec", "png",
            "pipe:1",
        ],
        check=False,
        capture_output=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"failed to extract frame at {at_sec}s from {video_path}: "
            f"{proc.stderr.decode(errors='replace')}"
        )
    return Image.open(io.BytesIO(proc.stdout)).convert("RGB")


def _format_timestamp(seconds: float) -> str:
    total = max(0, int(seconds))
    return f"{total // 60:02d}:{total % 60:02d}"


def storyboard(video_path: Path, frames: int = 12, cols: int = 4) -> Image.Image:
    """Build a grid of ``frames`` uniformly-spaced frames, each labeled with its mm:ss timestamp."""

    meta = probe(video_path)
    duration = meta["duration"]
    if duration <= 0 or frames <= 0:
        raise ValueError(f"video has no measurable duration or frames<=0: {video_path}")

    timestamps = [duration * (i + 0.5) / frames for i in range(frames)]
    thumbs = [extract_frame(video_path, t) for t in timestamps]

    cell_w = 320
    thumb_w, thumb_h = thumbs[0].size
    cell_h = int(thumb_h * (cell_w / thumb_w)) if thumb_w else 180
    thumbs = [t.resize((cell_w, cell_h)) for t in thumbs]

    rows = -(-len(thumbs) // cols)
    grid = Image.new("RGB", (cell_w * cols, cell_h * rows), color="black")
    draw = ImageDraw.Draw(grid)
    try:
        font = ImageFont.load_default(size=16)
    except TypeError:
        font = ImageFont.load_default()

    for i, (thumb, ts) in enumerate(zip(thumbs, timestamps)):
        row, col = divmod(i, cols)
        x, y = col * cell_w, row * cell_h
        grid.paste(thumb, (x, y))
        label = _format_timestamp(ts)
        text_bbox = draw.textbbox((0, 0), label, font=font)
        text_w, text_h = text_bbox[2] - text_bbox[0], text_bbox[3] - text_bbox[1]
        draw.rectangle([x, y, x + text_w + 8, y + text_h + 6], fill="black")
        draw.text((x + 4, y + 2), label, fill="white", font=font)

    return grid


def _detect_scene_cuts(video_path: Path, threshold: float = 0.3) -> list[float]:
    """Return timestamps (seconds) of detected scene cuts via ffmpeg's scene filter."""

    proc = subprocess.run(
        [
            FFMPEG, "-i", str(video_path),
            "-vf", f"select='gt(scene,{threshold})',showinfo",
            "-f", "null", "-",
        ],
        check=False,
        capture_output=True, text=True,
    )
    cuts: list[float] = []
    for line in proc.stderr.splitlines():
        if "pts_time:" not in line:
            continue
        match = re.search(r"pts_time:([0-9.]+)", line)
        if match:
            cuts.append(float(match.group(1)))
    return cuts


def detect_hard_cuts(video_path: Path, *, min_diff: float = 20.0, spike: float = 3.0) -> list[float]:
    """Cuts between similar-looking scenes, which ffmpeg's scene score misses (NEON: white
    room to white room, 1.67 s and 11.46 s): a frame whose mean change jumps well above its
    neighbours' (camera motion changes every frame a little; a cut changes one a lot)."""
    import numpy as np

    info = probe(video_path)
    fps = float(info.get("fps") or 0) or 24.0
    raw = subprocess.run([FFMPEG, "-v", "error", "-i", str(video_path), "-vf", "scale=96:96", "-f", "rawvideo",
                          "-pix_fmt", "gray", "-"], capture_output=True, check=True).stdout
    frames = np.frombuffer(raw, np.uint8).reshape(-1, 96, 96).astype(np.float32)
    diff = np.abs(np.diff(frames, axis=0)).mean(axis=(1, 2))
    cuts = []
    for i, d in enumerate(diff):
        around = np.r_[diff[max(0, i - 3):i], diff[i + 1:i + 4]]
        base = float(np.median(around)) if len(around) else 0.0
        if d > min_diff and d > spike * base + 5.0:
            cuts.append(round((i + 1) / fps, 3))
    return cuts


def suggest_segments(
    video_path: Path,
    target_len: float = 8.0,
    max_segments: int = 5,
) -> list[dict[str, Any]]:
    """Suggest up to ``max_segments`` candidate clips of about ``target_len`` seconds.

    Uses ffmpeg scene-cut detection (``select='gt(scene,0.3)'``) to split the
    video into scenes, then fits a ``target_len``-second window inside each
    scene (anchored at the scene's start), skipping the first/last 3% of the
    video (likely intro/outro) and any scene shorter than a second.
    Deterministic given the same input file. Each suggestion is
    ``{"start": float, "end": float, "score": float, "reason": str}``, sorted
    by score descending.
    """

    meta = probe(video_path)
    duration = meta["duration"]
    if duration <= 0:
        return []

    cuts = sorted(set(_detect_scene_cuts(video_path)))
    boundaries = [0.0, *cuts, duration]

    margin = duration * 0.03
    lo, hi = margin, duration - margin
    if hi <= lo:
        lo, hi = 0.0, duration

    candidates: list[dict[str, Any]] = []
    for i in range(len(boundaries) - 1):
        seg_start = max(boundaries[i], lo)
        seg_end = min(boundaries[i + 1], hi)
        if seg_end - seg_start < 1.0:
            continue

        window_end = min(seg_end, seg_start + target_len)
        window_start = max(seg_start, window_end - target_len)
        length = window_end - window_start
        if length <= 0:
            continue

        length_score = 1.0 - abs(length - target_len) / target_len
        scene_len = seg_end - seg_start
        fit_score = min(1.0, scene_len / target_len)
        score = round(0.6 * length_score + 0.4 * fit_score, 4)

        reason = (
            "no scene cuts detected; sampled from the full clip"
            if not cuts
            else f"within a scene spanning {seg_start:.1f}s-{seg_end:.1f}s"
        )
        candidates.append(
            {
                "start": round(window_start, 2),
                "end": round(window_end, 2),
                "score": score,
                "reason": reason,
            }
        )

    candidates.sort(key=lambda c: c["score"], reverse=True)
    return candidates[:max_segments]
