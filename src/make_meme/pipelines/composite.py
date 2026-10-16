"""Merge several independent single-subject swaps of the same clip into one video.

A swap model regenerates the whole frame, so running subject 2 on subject 1's output lets
it repaint (or re-target) subject 1. Instead every subject is swapped from the original
clip, and here each output contributes only where it actually changed the frame: the
per-pixel difference to the original, cleaned up, dilated and feathered. Where two
changes overlap, the stronger change wins. The swap models reproduce the untouched
background almost exactly (median difference ~1/255), so the masks are tight.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

from make_meme import ingest

DIFF_THRESHOLD = 24.0  # mean |RGB difference| (0-255) that counts as "changed"
OPEN_PX = 3  # remove speckles smaller than this
GROW_PX = 5  # include the soft edge around the changed region
FEATHER_PX = 3.0


def change_mask(base: np.ndarray, layer: np.ndarray, threshold: float = DIFF_THRESHOLD) -> tuple[np.ndarray, np.ndarray]:
    """(soft alpha in [0, 1], raw difference) for one frame of one layer."""
    diff = np.abs(layer.astype(np.float32) - base.astype(np.float32)).mean(axis=-1)
    hard = Image.fromarray(((diff > threshold) * 255).astype(np.uint8), "L")
    hard = hard.filter(ImageFilter.MinFilter(OPEN_PX)).filter(ImageFilter.MaxFilter(OPEN_PX))
    hard = hard.filter(ImageFilter.MaxFilter(2 * GROW_PX + 1))
    soft = hard.filter(ImageFilter.GaussianBlur(FEATHER_PX))
    return np.asarray(soft, dtype=np.float32) / 255.0, diff


def composite_frame(base: np.ndarray, layers: list[np.ndarray], threshold: float = DIFF_THRESHOLD) -> np.ndarray:
    if not layers:
        return base
    alphas, diffs = zip(*(change_mask(base, layer, threshold) for layer in layers), strict=True)
    owner = np.argmax(np.stack(diffs), axis=0)  # strongest change owns contested pixels
    out = base.astype(np.float32)
    for k, (layer, alpha) in enumerate(zip(layers, alphas, strict=True)):
        a = alpha.copy()
        if len(layers) > 1:
            # Contested pixels go to the strongest change; the feathered edge stays shared.
            contested = np.zeros_like(a, dtype=bool)
            for j, other in enumerate(alphas):
                if j != k:
                    contested |= other > 0.5
            a[contested & (owner != k)] = 0.0
        out = out * (1.0 - a[..., None]) + layer.astype(np.float32) * a[..., None]
    return np.clip(out + 0.5, 0, 255).astype(np.uint8)


def composite_swaps(base: Path, layers: list[Path], dest: Path, *, fps: int,
                    threshold: float = DIFF_THRESHOLD) -> Path:
    """Stream ``base`` and each layer (same size, same fps) frame by frame into ``dest``."""
    info = ingest.probe(base)
    w, h = int(info["width"]), int(info["height"])
    frame_bytes = w * h * 3

    def reader(path: Path) -> subprocess.Popen:
        return subprocess.Popen(
            [ingest.FFMPEG, "-v", "error", "-i", str(path), "-f", "rawvideo", "-pix_fmt", "rgb24",
             "-s", f"{w}x{h}", "-"],
            stdout=subprocess.PIPE,
        )

    tmp = dest.with_name(f"{dest.stem}.tmp{dest.suffix}")
    readers = [reader(base), *(reader(p) for p in layers)]
    writer = subprocess.Popen(
        [ingest.FFMPEG, "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}",
         "-r", str(fps), "-i", "-", "-c:v", "libx264", "-crf", "14", "-pix_fmt", "yuv420p", str(tmp)],
        stdin=subprocess.PIPE,
    )
    frames = 0
    try:
        while True:
            chunks = [r.stdout.read(frame_bytes) for r in readers]
            # Stop at the shortest stream (chunk stitching can leave one frame of difference).
            if any(len(c) < frame_bytes for c in chunks):
                break
            imgs = [np.frombuffer(c, np.uint8).reshape(h, w, 3) for c in chunks]
            writer.stdin.write(composite_frame(imgs[0], imgs[1:], threshold).tobytes())
            frames += 1
    finally:
        for r in readers:
            r.stdout.close()
            r.kill()
            r.wait()
        writer.stdin.close()
        code = writer.wait()
    if code != 0 or frames == 0:
        tmp.unlink(missing_ok=True)
        raise RuntimeError(f"compositing {len(layers)} swaps over {base.name} failed (ffmpeg exit {code}, {frames} frames)")
    tmp.replace(dest)
    return dest
