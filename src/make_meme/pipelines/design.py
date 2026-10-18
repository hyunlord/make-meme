"""Character design: a pet photo -> the reference a pose-driven video model needs.

Wan2.2-Animate copies the reference's look onto the performer's motion; given a dog
lying on a bed it has to invent a standing body (we got a muscular human torso with a
dog head). An image editor (qwen_character) first redraws the pet the way the style asks
(standing upright in the performer's outfit, fur-covered, or a front-facing head), and the
user can check it before the long video render.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from PIL import Image

from make_meme.comfy.client import ComfyClient
from make_meme.pipelines.detect import Subject
from make_meme.pipelines.runtime import ensure_ready, node_files, run_recipe
from make_meme.plan import IdentityRef
from make_meme.recipes.loader import get_recipe
from make_meme.styles import Style


def performer_crop(frame_path: Path, subject: Subject, dest: Path, pad: float = 0.08) -> Path:
    """The performer cut out of a shot frame (for the designer to copy the outfit from).
    With a mask, everyone else is whited out: dancers overlap, and a crop showing two
    outfits made the designer pick the wrong one."""
    with Image.open(frame_path) as f:
        img = f.convert("RGB")
        if subject.mask_path and Path(subject.mask_path).is_file():
            with Image.open(subject.mask_path) as m:
                mask = m.convert("L").resize(img.size).point(lambda v: 255 if v > 127 else 0)
            white = Image.new("RGB", img.size, (255, 255, 255))
            white.paste(img, mask=mask)
            img = white
        x1, y1, x2, y2 = subject.bbox
        px, py = int((x2 - x1) * pad), int((y2 - y1) * pad)
        img.crop((max(0, x1 - px), max(0, y1 - py), min(img.width, x2 + px), min(img.height, y2 + py))).save(dest)
    return dest


def design_photo(style: Style, ident: IdentityRef) -> str | None:
    """Which of the identity's photos the designer starts from."""
    order = ("head", "full") if style.mask == "head" else ("full", "head")
    return next((p for k in order if (p := ident.ref_for(k))), None)


async def design_character(client: ComfyClient, style: Style, ident: IdentityRef, out_dir: Path, *, profile: str,
                           seed: int, outfit: Path | None = None, extra: str = "") -> Path:
    """Design `ident` for `style`; returns the image path (also usable as a video reference)."""
    photo = design_photo(style, ident)
    if photo is None:
        raise ValueError(f"identity {ident.id} has no usable photo to design from")
    recipe = get_recipe("qwen_character")
    await ensure_ready(client, recipe, profile)
    prompt = style.render_design_prompt(subject_desc=ident.description, coat=ident.coat)
    if extra:
        prompt = f"{prompt} {extra.strip()}"
    media = {"photo": Path(photo)}
    if style.design_outfit and outfit is not None:
        media["outfit"] = outfit
    face = ident.ref_for("head")
    if face and face != photo:  # a full-body photo shows the face small: designs drifted to a generic dog
        media["face"] = Path(face)
        prompt += (" Image 3 is a close-up of the same dog: copy only its face from it (eye shape and colour,"
                   " ears, muzzle, markings and fur colour) so it is recognisably this dog; ignore everything else"
                   " in image 3 (harnesses, clothes, seats, background).")
    width, height = style.design_size
    result = await run_recipe(client, recipe, media=media,
                              values={"prompt": prompt, "width": int(width), "height": int(height), "seed": seed},
                              profile=profile, preset="draft", stage="designing")
    files = node_files(result, recipe.outputs["image"])
    if not files:
        raise RuntimeError(f"qwen_character produced no image for {ident.id}")
    out_dir.mkdir(parents=True, exist_ok=True)
    dest = out_dir / f"{style.name}_{ident.id}_{seed}.png"
    await client.download(files[0], dest)
    await asyncio.to_thread(lambda: Image.open(dest).verify())
    return dest
