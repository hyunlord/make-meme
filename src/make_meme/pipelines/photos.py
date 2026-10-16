"""Photo organizer: split an unsorted pile of photos into identities.

Users dump a mixed folder of photos (e.g. 5 of one dog, 5 of another, 1 photo
with both) and want make-meme to figure out who's who, pick the best 1-2
reference photos per identity (MoCha accepts at most a full-body ref1 and a
head close-up ref2), describe each identity, and flag anything that will
hurt swap quality (no upright photo, low resolution, dark photos, ...).

Pipeline: detect every person/animal in every photo (SAM 3, reusing
:func:`make_meme.pipelines.detect.detect_in_image`) -> build an
:class:`Instance` per detection (crop, head crop, colour histogram, quality
metrics) -> cluster instances into :class:`Identity` groups by appearance
(reusing the colour-histogram approach from
:mod:`make_meme.pipelines.assign`) -> pick references and describe each
identity.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps

from make_meme.comfy.client import ComfyClient, ComfyError
from make_meme.pipelines.assign import color_hist, hist_dist
from make_meme.pipelines.detect import Subject, detect_in_image
from make_meme.pipelines.runtime import ensure_ready, run_recipe
from make_meme.recipes.loader import RecipeError, get_recipe

logger = logging.getLogger(__name__)

DEFAULT_QUERY = "person:5, animal:5"
# Combined (embedding, histogram)-distance threshold above which identities stop merging.
# Tuned against a real 11-photo set (2 dogs, one shared "both" photo) after switching to
# DINOv2 embeddings: the resulting clustering is identical for every threshold in
# [0.32, 0.4] (stable plateau -- see the live-tuning report for the full pairwise
# matrix), so 0.35 sits in the middle of that stable range rather than at an edge.
IDENTITY_MAX_DIST = 0.35
EMBED_WEIGHT = 0.8  # weight of the DINOv2 cosine distance in the combined distance
HIST_WEIGHT = 0.2  # weight of the colour-histogram distance (weak tie-breaker)
HEAD_MIN_AREA_FRAC = 0.003  # SAM 3 "head" search is relative to the (small) subject crop
WORKING_MAX_LONG_SIDE = 1600  # downscale before sending to SAM 3 (upload size + speed)
LOW_RES_PX = 512
MIN_PERSON_AREA_FRAC = 0.08  # below this, a "person" detection is probably a stray limb/sleeve
EMBED_RECIPE_NAME = "image_embed"


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class Instance:
    """One detected person/animal in one photo."""

    photo: Path
    index: int
    label: str
    score: float
    bbox: tuple[int, int, int, int]
    mask_path: Path
    crop_path: Path
    head_path: Path | None
    quality: dict[str, Any]
    hist: np.ndarray = field(repr=False)
    head_hist: np.ndarray | None = field(default=None, repr=False)
    embedding: np.ndarray | None = field(default=None, repr=False)

    def to_json(self) -> dict[str, Any]:
        return {
            "photo": str(self.photo),
            "index": self.index,
            "label": self.label,
            "score": self.score,
            "bbox": list(self.bbox),
            "mask_path": str(self.mask_path),
            "crop_path": str(self.crop_path),
            "head_path": str(self.head_path) if self.head_path else None,
            "quality": dict(self.quality),
        }


@dataclass
class Identity:
    """A cluster of :class:`Instance` objects believed to be the same person/animal."""

    id: str
    label: str
    instances: list[Instance]
    ref_full: Instance
    ref_head: Instance | None
    description: str
    coat: str
    confidence: float
    advice: list[str]

    def to_json(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "instances": [i.to_json() for i in self.instances],
            "ref_full": self.ref_full.to_json(),
            "ref_head": self.ref_head.to_json() if self.ref_head else None,
            "description": self.description,
            "coat": self.coat,
            "confidence": self.confidence,
            "advice": list(self.advice),
        }


# ---------------------------------------------------------------------------
# Working-copy preparation
# ---------------------------------------------------------------------------


def _register_heic() -> None:
    try:
        import pillow_heif

        pillow_heif.register_heif_opener()
    except ImportError:  # optional at runtime; HEIC then fails with a clear OSError below
        pass


def _prepare_working_copy(
    photo: Path, dest_path: Path, max_long_side: int = WORKING_MAX_LONG_SIDE
) -> tuple[Path, int, int, float]:
    """EXIF-transpose ``photo`` and downscale a working copy to <=``max_long_side``.

    Returns ``(working_path, working_width, working_height, scale_to_original)`` where
    multiplying a working-copy coordinate by ``scale_to_original`` maps it back onto
    the original (EXIF-transposed) photo -- a pure scale, since downscaling never crops.
    """

    _register_heic()
    with Image.open(photo) as im:
        img = ImageOps.exif_transpose(im).convert("RGB")
    orig_w = img.width
    long_side = max(img.size)
    if long_side > max_long_side:
        scale_down = max_long_side / long_side
        img = img.resize(
            (max(1, round(img.width * scale_down)), max(1, round(img.height * scale_down))),
            Image.Resampling.LANCZOS,
        )
    dest_path = dest_path.with_suffix(".png")
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(dest_path)
    scale_to_original = orig_w / img.width
    return dest_path, img.width, img.height, scale_to_original


# ---------------------------------------------------------------------------
# Quality metrics
# ---------------------------------------------------------------------------


def _laplacian_variance(path: Path) -> float:
    """Variance of the Laplacian of ``path`` (grayscale) -- a standard blur metric:
    low variance = few sharp edges = blurry.

    Computed directly with numpy (no opencv dependency): convolving with the
    discrete Laplacian kernel ``[[0,1,0],[1,-4,1],[0,1,0]]`` is just a sum of
    four shifted views minus four times the center, at full float precision
    (unlike Pillow's 8-bit ``ImageFilter.Kernel``, which would clip negative
    responses).
    """

    try:
        with Image.open(path) as im:
            gray = np.asarray(im.convert("L"), dtype=np.float64)
    except OSError:
        return 0.0
    if gray.shape[0] < 3 or gray.shape[1] < 3:
        return 0.0
    center = gray[1:-1, 1:-1]
    laplacian = gray[:-2, 1:-1] + gray[2:, 1:-1] + gray[1:-1, :-2] + gray[1:-1, 2:] - 4 * center
    return float(laplacian.var())


def _compute_quality(
    bbox: tuple[int, int, int, int], img_w: int, img_h: int, crop_path: Path, head_frac: float
) -> dict[str, Any]:
    x1, y1, x2, y2 = bbox
    w, h = max(1, x2 - x1), max(1, y2 - y1)
    area_frac = (w * h) / max(1, img_w * img_h)

    touches = sum((x1 <= 1, y1 <= 1, x2 >= img_w - 1, y2 >= img_h - 1))
    touches_bottom = y2 >= img_h - 1
    cut_off = bool(touches >= 2 or touches_bottom)

    aspect = h / w
    if aspect >= 1.15:
        pose = "upright"
    elif aspect <= 0.8:
        pose = "lying"
    else:
        pose = "unknown"

    try:
        with Image.open(crop_path) as im:
            resolution = min(im.size)
    except OSError:
        resolution = 0

    return {
        "sharpness": _laplacian_variance(crop_path),
        "area_frac": area_frac,
        "cut_off": cut_off,
        "pose": pose,
        "head_frac": head_frac,
        "resolution": resolution,
    }


# ---------------------------------------------------------------------------
# Appearance embedding (DINOv2, run inside ComfyUI via the image_embed recipe)
# ---------------------------------------------------------------------------


def _node_embeddings(result, node_id: str) -> list[list[float]]:
    out = result.raw.get("outputs", {}).get(node_id, {})
    embeddings = out.get("embeddings", [])
    return [list(e) for e in embeddings if isinstance(e, list)]


async def _embed_crop(
    client: ComfyClient, image_path: Path, mask_path: Path | None, *, profile: str
) -> np.ndarray | None:
    """DINOv2 embedding of ``image_path`` (composited onto grey via ``mask_path`` if
    given), or None if the image_embed recipe/node isn't available right now.

    Appearance clustering falls back to colour-histogram-only for any instance this
    returns None for (see :func:`_pairwise_distance`); it never raises.
    """

    try:
        recipe = get_recipe(EMBED_RECIPE_NAME)
        await ensure_ready(client, recipe, profile)
        media: dict[str, Path] = {"image": image_path}
        if mask_path is not None:
            media["mask"] = mask_path
        result = await run_recipe(
            client, recipe, media=media, values={}, profile=profile, stage="embedding"
        )
    except (ComfyError, RecipeError) as e:
        logger.warning(
            "DINOv2 embedding unavailable (%s); falling back to colour histogram only", e
        )
        return None
    embeddings = _node_embeddings(result, recipe.outputs["embeddings"])
    if not embeddings:
        return None
    return np.asarray(embeddings[0], dtype=np.float64)


# ---------------------------------------------------------------------------
# Building instances
# ---------------------------------------------------------------------------


async def _build_instance(
    client: ComfyClient,
    photo: Path,
    working_img: Image.Image,
    img_w: int,
    img_h: int,
    scale_to_original: float,
    subj: Subject,
    photo_out: Path,
    *,
    profile: str,
) -> Instance:
    x1, y1, x2, y2 = subj.bbox
    pad_x, pad_y = max(1, (x2 - x1) // 10), max(1, (y2 - y1) // 10)
    crop_box = (
        max(0, x1 - pad_x),
        max(0, y1 - pad_y),
        min(img_w, x2 + pad_x),
        min(img_h, y2 + pad_y),
    )

    mask_img = Image.open(subj.mask_path).convert("L").resize(working_img.size)

    # ref1-style crop: subject on white, like detect.clean_reference.
    white = Image.new("RGB", working_img.size, (255, 255, 255))
    white.paste(working_img, mask=mask_img)
    crop = white.crop(crop_box)
    photo_out.mkdir(parents=True, exist_ok=True)
    crop_path = photo_out / f"crop_{subj.id:02d}.png"
    crop.save(crop_path)

    # Unmasked crop (still has background) -- input to head detection, to the embedding
    # (which composites it onto grey using mask_crop_path itself), and to the colour
    # histogram (which does its own mask+box selection).
    raw_crop = working_img.crop(crop_box)
    raw_crop_path = photo_out / f"raw_{subj.id:02d}.png"
    raw_crop.save(raw_crop_path)

    mask_crop_path = photo_out / f"maskcrop_{subj.id:02d}.png"
    mask_img.crop(crop_box).save(mask_crop_path)

    hist = color_hist(working_img, mask_img, subj.bbox)
    embedding = await _embed_crop(client, raw_crop_path, mask_crop_path, profile=profile)

    head_path: Path | None = None
    head_hist: np.ndarray | None = None
    head_frac = 0.0

    try:
        heads = await detect_in_image(
            client,
            raw_crop_path,
            "head:1",
            photo_out / f"head_{subj.id:02d}",
            profile=profile,
            min_area_frac=HEAD_MIN_AREA_FRAC,
        )
    except ComfyError:
        # Head detection is best-effort: on some crops SAM 3's own workflow errors out
        # (e.g. nothing passed its mask/crop node) instead of cleanly returning zero
        # matches. Either way, no head_path for this instance is a safe degradation.
        logger.warning(
            "head detection failed for %s subject %d; continuing without a head ref", photo, subj.id
        )
        heads = []
    if heads:
        head_subj = heads[0]
        hx1, hy1, hx2, hy2 = head_subj.bbox  # local to raw_crop
        bbox_area = max(1, (x2 - x1) * (y2 - y1))
        head_frac = ((hx2 - hx1) * (hy2 - hy1)) / bbox_area

        head_mask = Image.open(head_subj.mask_path).convert("L").resize(raw_crop.size)
        head_hist = color_hist(raw_crop, head_mask, head_subj.bbox)

        # Map local (raw_crop) -> working-copy global -> original (full-res) photo coords.
        gx1, gy1 = crop_box[0] + hx1, crop_box[1] + hy1
        gx2, gy2 = crop_box[0] + hx2, crop_box[1] + hy2
        ox1, oy1, ox2, oy2 = (round(v * scale_to_original) for v in (gx1, gy1, gx2, gy2))
        side = max(1, int(max(ox2 - ox1, oy2 - oy1) * 1.3))
        cx, cy = (ox1 + ox2) // 2, (oy1 + oy2) // 2
        half = max(1, side // 2)

        with Image.open(photo) as orig:
            orig_img = ImageOps.exif_transpose(orig).convert("RGB")
        box = (
            max(0, cx - half),
            max(0, cy - half),
            min(orig_img.width, cx + half),
            min(orig_img.height, cy + half),
        )
        head_crop = orig_img.crop(box)
        if min(head_crop.size) >= 64:
            head_path = photo_out / f"head_crop_{subj.id:02d}.png"
            head_crop.save(head_path)

    quality = _compute_quality(subj.bbox, img_w, img_h, crop_path, head_frac)

    return Instance(
        photo=photo,
        index=subj.id,
        label=subj.label,
        score=subj.score,
        bbox=subj.bbox,
        mask_path=Path(subj.mask_path),
        crop_path=crop_path,
        head_path=head_path,
        quality=quality,
        hist=hist,
        head_hist=head_hist,
        embedding=embedding,
    )


# ---------------------------------------------------------------------------
# Grouping into identities
# ---------------------------------------------------------------------------


def _cosine_distance(a: np.ndarray, b: np.ndarray) -> float:
    """0 = identical direction, 1 = orthogonal, 2 = opposite -- clamped to [0, 1] in
    practice since DINOv2 CLS tokens for any two real photos are never anti-correlated."""

    a, b = np.asarray(a, dtype=np.float64), np.asarray(b, dtype=np.float64)
    na, nb = float(np.linalg.norm(a)), float(np.linalg.norm(b))
    if na == 0.0 or nb == 0.0:
        return 1.0
    cos_sim = float(np.dot(a, b) / (na * nb))
    return max(0.0, min(1.0, (1.0 - cos_sim) / 2.0))


def _hist_distance(a: Instance, b: Instance) -> float:
    """Combined body+head colour-histogram distance."""

    body_d = hist_dist(a.hist, b.hist)
    if a.head_hist is not None and b.head_hist is not None:
        head_d = hist_dist(a.head_hist, b.head_hist)
        return body_d * 0.6 + head_d * 0.4
    return body_d


def _pairwise_distance(a: Instance, b: Instance) -> float:
    """Appearance distance: DINOv2 embedding cosine distance (primary) blended with a
    colour-histogram distance (weak tie-breaker), falling back to histogram-only when
    either instance has no embedding (e.g. the image_embed recipe/node wasn't available).
    Different labels (person vs animal) are never comparable.
    """

    if a.label != b.label:
        return 1.0
    hist_d = _hist_distance(a, b)
    if a.embedding is not None and b.embedding is not None:
        emb_d = _cosine_distance(a.embedding, b.embedding)
        return EMBED_WEIGHT * emb_d + HIST_WEIGHT * hist_d
    return hist_d


def group_instances(
    instances: list[Instance], threshold: float = IDENTITY_MAX_DIST
) -> list[list[Instance]]:
    """Agglomerative average-linkage clustering by appearance.

    Never merges across labels (person vs animal), and never merges two
    clusters that would put two instances from the *same photo* together
    (cannot-link: two subjects in one photo are never the same identity).
    Stops once the closest remaining pair of clusters is farther apart than
    ``threshold``.
    """

    n = len(instances)
    if n == 0:
        return []

    dist = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            dist[i][j] = dist[j][i] = _pairwise_distance(instances[i], instances[j])

    clusters: list[list[int]] = [[i] for i in range(n)]

    def conflicts(c1: list[int], c2: list[int]) -> bool:
        photos1 = {instances[i].photo for i in c1}
        photos2 = {instances[i].photo for i in c2}
        return bool(photos1 & photos2)

    def avg_linkage(c1: list[int], c2: list[int]) -> float:
        total = sum(dist[i][j] for i in c1 for j in c2)
        return total / (len(c1) * len(c2))

    while len(clusters) > 1:
        best_dist: float | None = None
        best_pair: tuple[int, int] | None = None
        for a in range(len(clusters)):
            for b in range(a + 1, len(clusters)):
                c1, c2 = clusters[a], clusters[b]
                if instances[c1[0]].label != instances[c2[0]].label:
                    continue
                if conflicts(c1, c2):
                    continue
                d = avg_linkage(c1, c2)
                if best_dist is None or d < best_dist:
                    best_dist, best_pair = d, (a, b)
        if best_pair is None or (best_dist is not None and best_dist > threshold):
            break
        a, b = best_pair
        merged = clusters[a] + clusters[b]
        clusters = [c for k, c in enumerate(clusters) if k not in (a, b)]
        clusters.append(merged)

    return [[instances[i] for i in c] for c in clusters]


# ---------------------------------------------------------------------------
# Reference selection
# ---------------------------------------------------------------------------


def _normalize_sharpness(value: float) -> float:
    """Saturating 0..1 normalization; variance-of-Laplacian has no fixed upper bound."""

    value = max(0.0, value)
    return value / (value + 300.0)


def _ref_full_score(inst: Instance) -> float:
    q = inst.quality
    pose_score = {"upright": 1.0, "unknown": 0.5, "lying": 0.2}.get(q.get("pose", "unknown"), 0.5)
    area_norm = min(1.0, q.get("area_frac", 0.0) / 0.5)
    sharp_norm = _normalize_sharpness(q.get("sharpness", 0.0))
    cutoff_bonus = 0.0 if q.get("cut_off") else 1.0
    return pose_score * 0.35 + area_norm * 0.2 + sharp_norm * 0.25 + cutoff_bonus * 0.2


def _ref_head_score(inst: Instance) -> float:
    q = inst.quality
    res_norm = min(1.0, q.get("resolution", 0) / 256.0)
    sharp_norm = _normalize_sharpness(q.get("sharpness", 0.0))
    head_frac_norm = min(1.0, q.get("head_frac", 0.0) / 0.5)
    return res_norm * 0.4 + sharp_norm * 0.3 + head_frac_norm * 0.3


def choose_refs(instances: list[Instance]) -> tuple[Instance, Instance | None]:
    """Pick the best full-body reference (ref1) and head close-up (ref2, if any)."""

    if not instances:
        raise ValueError("choose_refs requires at least one instance")
    ref_full = max(instances, key=_ref_full_score)
    head_candidates = [i for i in instances if i.head_path is not None]
    ref_head = max(head_candidates, key=_ref_head_score) if head_candidates else None
    return ref_full, ref_head


# ---------------------------------------------------------------------------
# Colour description
# ---------------------------------------------------------------------------


def _name_hsv(h_deg: float, s: float, v: float) -> str:
    """Map one HSV sample (hue in degrees 0-360, saturation/value in 0-1) to a colour word."""

    if v < 0.15:
        return "black"
    if s < 0.12 and v > 0.85:
        return "white"
    if s < 0.18:
        return "blue-grey" if 170 <= h_deg <= 260 else "grey"
    if h_deg < 20 or h_deg >= 340:
        return "red" if (v > 0.5 and s > 0.5) else "brown"
    if h_deg < 45:
        if s > 0.6 and v > 0.6:
            return "golden"
        if v < 0.45:
            return "brown"
        if s < 0.3:
            return "cream"
        return "tan/fawn"
    if h_deg < 70:
        return "cream" if (v > 0.75 and s < 0.45) else "golden"
    if 170 <= h_deg <= 260:
        return "blue-grey"
    return "brown"


def _describe_weighted(h_frac: np.ndarray, s: np.ndarray, v: np.ndarray, weight: np.ndarray) -> str:
    totals: dict[str, float] = {}
    for h, si, vi, w in zip(h_frac, s, v, weight, strict=True):
        name = _name_hsv(float(h) * 360.0, float(si), float(vi))
        totals[name] = totals.get(name, 0.0) + float(w)
    total_weight = sum(totals.values()) or 1.0
    ranked = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)
    words = [ranked[0][0]]
    if len(ranked) > 1 and ranked[1][1] / total_weight >= 0.2 and ranked[1][0] != ranked[0][0]:
        words.append(ranked[1][0])
    return " and ".join(words)


def describe_coat(hist_or_pixels: Any) -> str:
    """Up to 2 colour words (e.g. "black", "blue-grey and white") describing ``hist_or_pixels``.

    Accepts a :func:`make_meme.pipelines.assign.color_hist` histogram (shape
    ``(8, 4, 4)`` or flattened to 128), a PIL Image (its HSV pixels are used
    directly), or a raw array of HSV pixels/triples (shape ``(N, 3)``, values
    either 0-1 or 0-255).
    """

    if isinstance(hist_or_pixels, Image.Image):
        arr = np.asarray(hist_or_pixels.convert("HSV"), dtype=np.float64).reshape(-1, 3)
        h, s, v = arr[:, 0] / 255.0, arr[:, 1] / 255.0, arr[:, 2] / 255.0
        return _describe_weighted(h, s, v, np.ones(len(h)))

    arr = np.asarray(hist_or_pixels, dtype=np.float64)
    if arr.size == 128:
        arr = arr.reshape(8, 4, 4)
    if arr.ndim == 3 and arr.shape == (8, 4, 4):
        h_idx, s_idx, v_idx = (a.ravel() for a in np.indices(arr.shape))
        weight = arr.ravel()
        mask = weight > 1e-9
        if not mask.any():
            return "unknown"
        h = (h_idx[mask] + 0.5) / 8.0
        s = (s_idx[mask] + 0.5) / 4.0
        v = (v_idx[mask] + 0.5) / 4.0
        return _describe_weighted(h, s, v, weight[mask])

    pixels = arr.reshape(-1, 3)
    if pixels.size == 0:
        return "unknown"
    scale = 255.0 if pixels.max() > 1.5 else 1.0
    h, s, v = pixels[:, 0] / scale, pixels[:, 1] / scale, pixels[:, 2] / scale
    return _describe_weighted(h, s, v, np.ones(len(h)))


def _describe(label: str, coat: str) -> str:
    if label == "person":
        return f"a person wearing mostly {coat}"
    return f"an animal with a {coat} coat"


# ---------------------------------------------------------------------------
# Confidence + advice
# ---------------------------------------------------------------------------


def _mean_intra_distance(members: list[Instance]) -> float:
    if len(members) <= 1:
        return 0.0
    dists = [
        _pairwise_distance(members[i], members[j])
        for i in range(len(members))
        for j in range(i + 1, len(members))
    ]
    return sum(dists) / len(dists)


def _confidence_for(members: list[Instance], all_groups: list[list[Instance]]) -> float:
    intra = _mean_intra_distance(members)
    other_groups = [g for g in all_groups if g is not members]
    if not other_groups:
        return max(0.0, min(1.0, 1.0 - intra))
    nearest = min(
        sum(_pairwise_distance(a, b) for a in members for b in other) / (len(members) * len(other))
        for other in other_groups
    )
    margin = nearest - intra
    return max(0.0, min(1.0, 0.5 + margin / 0.6))


def _mean_value_from_hist(hist: np.ndarray) -> float:
    h = np.asarray(hist).reshape(8, 4, 4)
    v_centers = (np.arange(4) + 0.5) / 4.0
    v_weight = h.sum(axis=(0, 1))
    total = v_weight.sum()
    if total <= 0:
        return 0.5
    return float((v_weight * v_centers).sum() / total)


def _advice_for(
    ident_id: str, members: list[Instance], ref_full: Instance, ref_head: Instance | None
) -> list[str]:
    advice: list[str] = []
    if len(members) == 1:
        advice.append(f"Only one photo of {ident_id}; more angles would help the model generalize.")
    if not any(m.quality.get("pose") == "upright" for m in members):
        advice.append(
            f"No standing/sitting-upright photo of {ident_id}; full-body styles will invent the body. "
            "Add one if you can."
        )
    if ref_full.quality.get("resolution", 0) < LOW_RES_PX:
        advice.append(
            f"The chosen full-body reference for {ident_id} is low resolution (<{LOW_RES_PX}px)."
        )
    if ref_head is None:
        advice.append(
            f"No clear head close-up found for {ident_id}; MoCha's ref2 (identity boost) will be skipped."
        )
    elif ref_head.quality.get("resolution", 0) < LOW_RES_PX:
        advice.append(
            f"The chosen head close-up for {ident_id} is low resolution (<{LOW_RES_PX}px)."
        )
    mean_v = sum(_mean_value_from_hist(m.hist) for m in members) / len(members)
    if mean_v < 0.25:
        advice.append(f"{ident_id}'s photos are dark; a well-lit photo keeps fur/clothing detail.")
    return advice


def _identity_id(index: int) -> str:
    """0 -> "A", 25 -> "Z", 26 -> "AA", ... (spreadsheet-style column naming)."""

    letters = []
    n = index
    while True:
        letters.append(chr(ord("A") + n % 26))
        n = n // 26 - 1
        if n < 0:
            break
    return "".join(reversed(letters))


# ---------------------------------------------------------------------------
# Pet-set detection: drop/filter spurious "person" detections (owners' limbs, sleeves)
# ---------------------------------------------------------------------------

SUBJECT_KINDS = ("auto", "animal", "person")


def _passes_geometric_person_filter(
    bbox: tuple[int, int, int, int], img_w: int, img_h: int
) -> bool:
    """Cheap, pre-instance-building screen for a "person" detection that's probably a
    real subject: big enough, and not cut off on 2+ frame edges. (The other half of the
    "looks like a real subject" rule -- a detected head -- needs the built Instance, so
    it's checked by the caller after :func:`_build_instance` runs.)
    """

    x1, y1, x2, y2 = bbox
    area_frac = max(0, x2 - x1) * max(0, y2 - y1) / max(1, img_w * img_h)
    if area_frac < MIN_PERSON_AREA_FRAC:
        return False
    touches = sum((x1 <= 1, y1 <= 1, x2 >= img_w - 1, y2 >= img_h - 1))
    return touches < 2


def _should_drop_persons(subject_kind: str, per_photo_subjects: list[list[Subject]]) -> bool:
    if subject_kind == "animal":
        return True
    if subject_kind == "person":
        return False
    # auto: a "pet set" (animals in at least half the photos) means stray person
    # detections (owners' arms, legs, sleeves) are noise, not a second set of identities.
    if not per_photo_subjects:
        return False
    with_animal = sum(1 for subs in per_photo_subjects if any(s.label == "animal" for s in subs))
    return with_animal >= len(per_photo_subjects) / 2


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


async def organize_photos(
    client: ComfyClient,
    photos: list[Path],
    out_dir: Path,
    *,
    profile: str,
    query: str = DEFAULT_QUERY,
    min_area_frac: float = 0.02,
    subject_kind: str = "auto",
) -> list[Identity]:
    """Detect every person/animal across ``photos`` and group them into identities.

    ``subject_kind``: ``"auto"`` (default) treats the whole set as a pet set -- and
    drops all "person" detections -- when animals were found in at least half the
    photos (SAM 3's "person" query also catches owners' arms/legs/sleeves, which are
    noise once we know this is really about the pets); otherwise persons are kept, but
    only ones that look like a real subject (big enough, not cut off, a head found in
    them). ``"animal"``/``"person"`` force dropping the other label outright (e.g.
    plan_meme passes ``"animal"`` for pet_* styles, which already know the answer).
    """

    if subject_kind not in SUBJECT_KINDS:
        raise ValueError(f"subject_kind must be one of {SUBJECT_KINDS}, got {subject_kind!r}")

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Pass 1: detect raw subjects per photo. Collected up front because the "auto"
    # pet-set decision needs to see every photo's subjects before any instance is built.
    detected: list[tuple[Path, Path, Path, int, int, float, list[Subject]]] = []
    for p_index, photo in enumerate(photos):
        photo_out = out_dir / f"photo_{p_index:03d}"
        working_path, w, h, scale_to_original = _prepare_working_copy(photo, photo_out / "work")
        subjects = await detect_in_image(
            client,
            working_path,
            query,
            photo_out / "detect",
            profile=profile,
            min_area_frac=min_area_frac,
        )
        detected.append((photo, photo_out, working_path, w, h, scale_to_original, subjects))

    drop_persons = _should_drop_persons(subject_kind, [subs for *_, subs in detected])

    # Pass 2: build instances, applying the person filter (cheap geometric screen
    # before building, "has a head" after -- that needs the built Instance).
    instances: list[Instance] = []
    embed_total = 0
    embed_missing = 0
    for photo, photo_out, working_path, w, h, scale_to_original, subjects in detected:
        if not subjects:
            continue
        with Image.open(working_path) as wim:
            working_img = wim.convert("RGB").copy()
        for subj in subjects:
            if subj.label == "person":
                if drop_persons:
                    continue
                if not _passes_geometric_person_filter(subj.bbox, w, h):
                    continue
            inst = await _build_instance(
                client,
                photo,
                working_img,
                w,
                h,
                scale_to_original,
                subj,
                photo_out,
                profile=profile,
            )
            if subj.label == "person" and not drop_persons and inst.head_path is None:
                continue  # "looks like a real subject" requires a detected head
            embed_total += 1
            if inst.embedding is None:
                embed_missing += 1
            instances.append(inst)

    groups = group_instances(instances)
    groups.sort(key=len, reverse=True)

    embed_fallback_note = (
        f"Appearance clustering used colour only (DINOv2 embedding unavailable) for "
        f"{embed_missing}/{embed_total} detected subjects."
        if embed_missing
        else None
    )

    identities: list[Identity] = []
    for g_index, members in enumerate(groups):
        ident_id = _identity_id(g_index)
        label = members[0].label
        ref_full, ref_head = choose_refs(members)
        mean_hist = np.mean([m.hist for m in members], axis=0)
        coat = describe_coat(mean_hist)
        advice = _advice_for(ident_id, members, ref_full, ref_head)
        if embed_fallback_note and any(m.embedding is None for m in members):
            advice.append(embed_fallback_note)
        identities.append(
            Identity(
                id=ident_id,
                label=label,
                instances=members,
                ref_full=ref_full,
                ref_head=ref_head,
                description=_describe(label, coat),
                coat=coat,
                confidence=_confidence_for(members, groups),
                advice=advice,
            )
        )
    return identities


# ---------------------------------------------------------------------------
# Contact sheet
# ---------------------------------------------------------------------------


def _load_font(size: int) -> ImageFont.ImageFont:
    for path in (
        "/System/Library/Fonts/AppleSDGothicNeo.ttc",
        "/System/Library/Fonts/Helvetica.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def contact_sheet(identities: list[Identity]) -> Image.Image:
    """One row per identity: thumbnails of every instance, chosen refs outlined + labeled."""

    cell = 140
    pad = 8
    label_w = 28
    caption_h = 20

    if not identities:
        img = Image.new("RGB", (400, 100), (30, 30, 30))
        draw = ImageDraw.Draw(img)
        draw.text((10, 40), "No identities", fill=(255, 255, 255), font=_load_font(16))
        return img

    max_instances = max(len(ident.instances) for ident in identities)
    row_h = cell + caption_h
    width = label_w + max_instances * (cell + pad) + pad
    height = len(identities) * (row_h + pad) + pad

    canvas = Image.new("RGB", (width, height), (15, 15, 15))
    draw = ImageDraw.Draw(canvas)
    font = _load_font(14)

    for row, ident in enumerate(identities):
        y = pad + row * (row_h + pad)
        draw.text((4, y + row_h // 2 - 7), ident.id, fill=(255, 255, 255), font=font)
        for col, inst in enumerate(ident.instances):
            x = label_w + col * (cell + pad)
            try:
                with Image.open(inst.crop_path) as im:
                    thumb = ImageOps.fit(im.convert("RGB"), (cell, cell))
            except OSError:
                thumb = Image.new("RGB", (cell, cell), (80, 80, 80))
            canvas.paste(thumb, (x, y))

            is_full = inst is ident.ref_full
            is_head = ident.ref_head is not None and inst is ident.ref_head
            if is_full or is_head:
                color = (255, 215, 0)
                draw.rectangle([x, y, x + cell - 1, y + cell - 1], outline=color, width=4)
                if is_full and is_head:
                    tag = f"{ident.id} ref1+ref2"
                else:
                    tag = f"{ident.id} ref1" if is_full else f"{ident.id} ref2"
                draw.text((x + 2, y + cell + 2), tag, fill=color, font=font)

    return canvas
