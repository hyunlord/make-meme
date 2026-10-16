"""Subject detection (SAM 3 recipe) and mask geometry helpers."""

from __future__ import annotations

import hashlib
import json
import logging
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps

from make_meme.comfy.client import ComfyClient, ComfyError
from make_meme.pipelines.runtime import ensure_ready, node_files, node_text_outputs, run_recipe
from make_meme.recipes.loader import get_recipe

logger = logging.getLogger(__name__)

DEFAULT_QUERY = "person, animal"


@dataclass
class Subject:
    id: int
    label: str
    score: float
    bbox: tuple[int, int, int, int]  # x1, y1, x2, y2 in source pixels
    mask_path: str

    @property
    def area(self) -> int:
        x1, y1, x2, y2 = self.bbox
        return max(0, x2 - x1) * max(0, y2 - y1)

    def to_json(self) -> dict:
        d = asdict(self)
        d["bbox"] = list(self.bbox)
        return d

    @classmethod
    def from_json(cls, d: dict) -> Subject:
        return cls(id=d["id"], label=d["label"], score=d["score"], bbox=tuple(d["bbox"]), mask_path=d["mask_path"])


def parse_query(query: str) -> list[str]:
    """'person, dog:3' -> ['person:5', 'dog:3'] (default up to 5 matches per term)."""
    terms = []
    for raw in query.split(","):
        term = raw.strip()
        if not term:
            continue
        terms.append(term if ":" in term else f"{term}:5")
    return terms or ["person:5"]


def iou(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> float:
    ix1, iy1, ix2, iy2 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


def _inside(inner: tuple[int, int, int, int], outer: tuple[int, int, int, int]) -> float:
    """Fraction of `inner`'s area that lies within `outer`."""
    ix1, iy1 = max(inner[0], outer[0]), max(inner[1], outer[1])
    ix2, iy2 = min(inner[2], outer[2]), min(inner[3], outer[3])
    area = max(1, (inner[2] - inner[0]) * (inner[3] - inner[1]))
    return max(0, ix2 - ix1) * max(0, iy2 - iy1) / area


def dedupe(subjects: list[Subject], threshold: float = 0.7, contained: float = 0.8) -> list[Subject]:
    """Drop lower-scored boxes that overlap a kept box (e.g. 'animal' and 'dog' hitting the
    same dog), and boxes of a *different* label lying mostly inside a kept one (e.g. a
    person's hair or torso picked up by the 'animal' query). Same-label containment is
    kept: one dancer standing in front of another is two real subjects."""
    kept: list[Subject] = []
    for s in sorted(subjects, key=lambda s: s.score, reverse=True):
        if any(iou(s.bbox, k.bbox) >= threshold for k in kept):
            continue
        if any(k.label != s.label and _inside(s.bbox, k.bbox) >= contained for k in kept):
            continue
        kept.append(s)
    return kept


async def detect_in_image(
    client: ComfyClient,
    image_path: Path,
    query: str,
    out_dir: Path,
    *,
    profile: str,
    threshold: float = 0.5,
    min_area_frac: float = 0.02,
) -> list[Subject]:
    """Run SAM 3 once per query term; returns subjects numbered 1..n by area (largest first).
    Tiny detections (< min_area_frac of the frame) are dropped: they are almost always
    background clutter and too small to swap anyway."""
    recipe = get_recipe("sam3_detect")
    await ensure_ready(client, recipe, profile)
    out_dir.mkdir(parents=True, exist_ok=True)
    with Image.open(image_path) as im:
        img_w, img_h = ImageOps.exif_transpose(im).size
    found: list[Subject] = []
    for term in parse_query(query):
        label, _, count = term.rpartition(":")
        label = label.strip()
        # ComfyUI's SAM 3 tokenizer only strips ":N" for N > 1; send a bare label for one match
        sam_query = label if count.strip() == "1" else term
        try:
            result = await run_recipe(
                client, recipe, media={"image": image_path}, values={"query": sam_query, "threshold": threshold},
                profile=profile, stage="detecting",
            )
        except ComfyError as e:
            if _is_empty_detection_error(e):
                continue  # SAM 3 found nothing: SaveImage can't save an empty mask batch
            raise
        boxes = _parse_boxes(node_text_outputs(result, recipe.outputs["boxes"]))
        masks = node_files(result, recipe.outputs["masks"])
        if len(masks) != len(boxes):
            logger.warning("sam3: %d boxes but %d masks for %r", len(boxes), len(masks), term)
        for box, mask_file in zip(boxes, masks):
            dest = out_dir / f"mask_{len(found):03d}.png"
            await client.download(mask_file, dest)
            x, y, w, h = box["x"], box["y"], box["width"], box["height"]
            bbox = (max(0, round(x)), max(0, round(y)), min(img_w, round(x + w)), min(img_h, round(y + h)))
            found.append(Subject(0, label, round(float(box.get("score", 0.0)), 3), bbox, str(dest)))
    min_area = min_area_frac * img_w * img_h
    subjects = sorted((s for s in dedupe(found) if s.area >= min_area), key=lambda s: s.area, reverse=True)
    for i, s in enumerate(subjects, start=1):
        s.id = i
    return subjects


def _is_empty_detection_error(e: ComfyError) -> bool:
    """ComfyUI fails the sam3_detect workflow with this when there are zero matches."""
    msg = str(e)
    return "SaveImage" in msg and "out of bounds for dimension 0 with size 0" in msg


def _parse_boxes(texts: list[str]) -> list[dict]:
    for text in texts:
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            continue
        # SAM3_Detect returns per-frame lists; we send a single image.
        if isinstance(data, list) and data and isinstance(data[0], list):
            return [b for b in data[0] if isinstance(b, dict)]
        if isinstance(data, list):
            return [b for b in data if isinstance(b, dict)]
    if texts:
        raise ComfyError("SAM 3 returned boxes in an unexpected format")
    return []


def fit_to(img: Image.Image, width: int, height: int, resample=Image.Resampling.LANCZOS) -> Image.Image:
    """Same geometry as ingest.normalize (scale to cover, center crop) so masks line up
    with the normalized video."""
    return ImageOps.fit(img, (width, height), method=resample, centering=(0.5, 0.5))


def binary_mask(mask_path: Path, width: int, height: int, grow: int = 6) -> Image.Image:
    """Load a subject mask, map it onto the normalized frame and dilate slightly so the
    replacement fully covers the original subject's silhouette."""
    m = Image.open(mask_path).convert("L")
    m = fit_to(m, width, height, Image.Resampling.BILINEAR).point(lambda v: 255 if v > 127 else 0)
    if grow > 0:
        from PIL import ImageFilter

        m = m.filter(ImageFilter.MaxFilter(grow * 2 + 1))
    return m


def annotate(image: Image.Image, subjects: list[Subject]) -> Image.Image:
    """Draw numbered boxes (and a translucent mask tint) for the user to pick from."""
    canvas = image.convert("RGB").copy()
    overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    palette = [(255, 64, 64), (64, 160, 255), (80, 220, 100), (255, 190, 40), (200, 90, 255), (0, 220, 220)]
    size = max(18, canvas.width // 28)
    font = _font(size)
    for s in subjects:
        color = palette[(s.id - 1) % len(palette)]
        try:
            mask = Image.open(s.mask_path).convert("L").resize(canvas.size)
            overlay.paste((*color, 70), mask=mask)
        except OSError:
            pass
        x1, y1, x2, y2 = s.bbox
        draw.rectangle([x1, y1, x2, y2], outline=(*color, 255), width=max(3, size // 6))
        tag = f"{s.id} {s.label}"
        tw = draw.textlength(tag, font=font)
        draw.rectangle([x1, y1, x1 + tw + 12, y1 + size + 10], fill=(*color, 230))
        draw.text((x1 + 6, y1 + 4), tag, font=font, fill=(0, 0, 0, 255))
    out = Image.alpha_composite(canvas.convert("RGBA"), overlay).convert("RGB")
    if out.width > 1280:
        out = out.resize((1280, round(out.height * 1280 / out.width)))
    return out


def _font(size: int):
    for path in ("/System/Library/Fonts/AppleSDGothicNeo.ttc", "/System/Library/Fonts/Helvetica.ttc",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


async def clean_reference(client: ComfyClient, image_path: Path, out_dir: Path, *, profile: str) -> Path:
    """Put the main subject of a reference photo on a white background (MoCha works best
    with clean references). Falls back to the original image if nothing is detected."""
    with tempfile.TemporaryDirectory(prefix="mm-ref-") as tmp:
        subjects = await detect_in_image(client, image_path, "person:1, animal:1", Path(tmp), profile=profile)
        if not subjects:
            return image_path
        main = subjects[0]
        img = ImageOps.exif_transpose(Image.open(image_path)).convert("RGB")
        mask = Image.open(main.mask_path).convert("L").resize(img.size)
        white = Image.new("RGB", img.size, (255, 255, 255))
        white.paste(img, mask=mask)
        x1, y1, x2, y2 = main.bbox
        pad_x, pad_y = (x2 - x1) // 10, (y2 - y1) // 10
        crop = white.crop((max(0, x1 - pad_x), max(0, y1 - pad_y), min(img.width, x2 + pad_x), min(img.height, y2 + pad_y)))
        out_dir.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha1(str(image_path.resolve()).encode()).hexdigest()[:8]
        dest = out_dir / f"ref_clean_{image_path.stem}_{digest}.png"
        crop.save(dest)
        return dest


async def head_reference(client: ComfyClient, image_path: Path, out_dir: Path, *, profile: str) -> Path | None:
    """Crop the head of the main subject as a close-up second reference (MoCha's ref2
    improves identity; its authors suggest zooming into the first reference when no
    separate face photo exists). 'head' works for people and animals alike."""
    with tempfile.TemporaryDirectory(prefix="mm-head-") as tmp:
        found = await detect_in_image(client, image_path, "head:1", Path(tmp), profile=profile, min_area_frac=0.003)
    if not found:
        return None
    img = ImageOps.exif_transpose(Image.open(image_path)).convert("RGB")
    x1, y1, x2, y2 = found[0].bbox
    side = int(max(x2 - x1, y2 - y1) * 1.3)
    cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
    box = (max(0, cx - side // 2), max(0, cy - side // 2), min(img.width, cx + side // 2), min(img.height, cy + side // 2))
    crop = img.crop(box)
    if min(crop.size) < 64:
        return None
    out_dir.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha1(str(image_path.resolve()).encode()).hexdigest()[:8]
    dest = out_dir / f"ref_head_{image_path.stem}_{digest}.png"
    crop.save(dest)
    return dest


async def head_mask_within(client: ComfyClient, frame_path: Path, subject: Subject, out_dir: Path, *,
                           profile: str, neck: float = 0.15) -> Path | None:
    """Mask of just the head of `subject` (SAM 3 'head' inside its box), in full-frame
    coordinates, extended a little downward so the replacement blends into the neck.
    Returns None if no head is found (caller falls back to the full-body mask)."""
    frame = Image.open(frame_path).convert("RGB")
    x1, y1, x2, y2 = subject.bbox
    pad = int(0.1 * max(x2 - x1, y2 - y1))
    box = (max(0, x1 - pad), max(0, y1 - pad), min(frame.width, x2 + pad), min(frame.height, y2 + pad))
    out_dir.mkdir(parents=True, exist_ok=True)
    crop_path = out_dir / f"subject{subject.id}_crop.png"
    frame.crop(box).save(crop_path)
    with tempfile.TemporaryDirectory(prefix="mm-headmask-") as tmp:
        found = await detect_in_image(client, crop_path, "head:1", Path(tmp), profile=profile, min_area_frac=0.002)
        if not found:
            return None
        head = Image.open(found[0].mask_path).convert("L").resize((box[2] - box[0], box[3] - box[1]))
        hx1, hy1, hx2, hy2 = found[0].bbox
    full = Image.new("L", frame.size, 0)
    full.paste(head, box[:2])
    # extend into the neck: a rectangle under the head, narrower than the head
    hw, hh = hx2 - hx1, hy2 - hy1
    nx1, nx2 = box[0] + hx1 + int(hw * 0.2), box[0] + hx2 - int(hw * 0.2)
    ny1, ny2 = box[1] + hy2 - int(hh * 0.1), box[1] + hy2 + int(hh * neck * 2)
    ImageDraw.Draw(full).rectangle([nx1, ny1, nx2, ny2], fill=255)
    if subject.mask_path and Path(subject.mask_path).is_file():  # stay inside the person
        body = Image.open(subject.mask_path).convert("L").resize(frame.size)
        full = Image.fromarray(np.minimum(np.asarray(full), np.asarray(body.point(lambda v: 255 if v > 127 else 0))))
        full.paste(head, box[:2], mask=head)  # but keep the whole head (hair may exceed the body mask)
    dest = out_dir / f"subject{subject.id}_head_mask.png"
    full.save(dest)
    return dest
