"""Per-frame object labels: SAM 3 video tracking by text (sam3_track recipe)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

from make_meme import ingest
from make_meme.comfy.client import ComfyClient
from make_meme.pipelines.runtime import ensure_ready, node_files, run_recipe
from make_meme.recipes.loader import get_recipe

TRACK_WIDTH = 540  # tracking runs on a downscaled copy; geometry is scaled back up


def downscale(video: Path, dest: Path, width: int = TRACK_WIDTH, stride: int = 1) -> tuple[Path, float]:
    """Every `stride`-th frame at a smaller (even) size. Returns (path, factor from small to
    original pixels)."""
    info = ingest.probe(video)
    w, h = int(info["width"]), int(info["height"])
    if w <= width and stride == 1:
        return video, 1.0
    tw = min(width, w)
    sh = round(h * tw / w / 2) * 2
    vf = f"scale={tw}:{sh},setsar=1"
    if stride > 1:
        vf = f"select='not(mod(n\\,{stride}))',setpts=N/FRAME_RATE/TB," + vf
    ingest._run([ingest.FFMPEG, "-y", "-i", str(video), "-vf", vf, "-an",
                 "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", str(dest)])
    return dest, w / tw


async def track_labels(client: ComfyClient, video: Path, out_dir: Path, *, profile: str, query: str = "head",
                       detect_interval: int = 2, max_objects: int = 6, cancelled=None) -> list[np.ndarray]:
    """Per frame of `video`, a label map: 0 = background, k = tracked object k-1 (identities
    are stable across frames; objects found later get new numbers)."""
    recipe = get_recipe("sam3_track")
    await ensure_ready(client, recipe, profile)
    result = await run_recipe(client, recipe, media={"video": video},
                              values={"query": query, "detect_interval": detect_interval, "max_objects": max_objects},
                              profile=profile, stage="tracking", cancelled=cancelled)
    out_dir.mkdir(parents=True, exist_ok=True)
    labels: list[np.ndarray] = []
    for i, f in enumerate(node_files(result, recipe.outputs["labels"])):
        dest = await client.download(f, out_dir / f"{i:05d}.png")
        with Image.open(dest) as im:
            labels.append(np.asarray(im.convert("L")).copy())
    return labels
