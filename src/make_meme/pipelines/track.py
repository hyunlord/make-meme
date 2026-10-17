"""Per-frame object masks: SAM 3 video tracking from a first-frame mask (sam3_track recipe)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

from make_meme import ingest
from make_meme.comfy.client import ComfyClient
from make_meme.pipelines.runtime import ensure_ready, node_files, run_recipe
from make_meme.recipes.loader import get_recipe

TRACK_WIDTH = 540  # tracking runs on a downscaled copy; geometry is scaled back up


def downscale(video: Path, dest: Path, width: int = TRACK_WIDTH) -> tuple[Path, float]:
    """Same frames, smaller (even) size. Returns (path, factor from small to original pixels)."""
    info = ingest.probe(video)
    w, h = int(info["width"]), int(info["height"])
    if w <= width:
        return video, 1.0
    sh = round(h * width / w / 2) * 2
    ingest._run([ingest.FFMPEG, "-y", "-i", str(video), "-vf", f"scale={width}:{sh},setsar=1", "-an",
                 "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", str(dest)])
    return dest, w / width


async def track_masks(client: ComfyClient, video: Path, first_mask: Path, out_dir: Path, *,
                      profile: str, cancelled=None) -> list[np.ndarray]:
    """Boolean mask per frame of `video` for the object in `first_mask` (same size as the video)."""
    recipe = get_recipe("sam3_track")
    await ensure_ready(client, recipe, profile)
    result = await run_recipe(client, recipe, media={"video": video, "mask": first_mask}, values={},
                              profile=profile, stage="tracking", cancelled=cancelled)
    out_dir.mkdir(parents=True, exist_ok=True)
    masks: list[np.ndarray] = []
    for i, f in enumerate(node_files(result, recipe.outputs["masks"])):
        dest = await client.download(f, out_dir / f"{i:05d}.png")
        with Image.open(dest) as im:
            masks.append(np.asarray(im.convert("L")) > 127)
    return masks
