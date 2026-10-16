"""Decide how reference photos map onto subjects in a video.

Several photos can mean two different things:
  * several angles of ONE replacement (e.g. full body + face close-up of my dog), or
  * one photo per DIFFERENT replacement (e.g. dog A for member 1, dog B for member 2).
The result is always a single video; this only decides which subject gets which photos.

Photos are grouped by what their main subject is (SAM 3: person vs animal) and by
appearance (masked HSV colour histogram). Different groups are paired with the
on-screen subjects that look most alike (hair/head colour vs fur colour), falling back
to size order. Every decision is explained so the caller can confirm it with the user.
"""

from __future__ import annotations

import itertools
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

from make_meme.comfy.client import ComfyClient
from make_meme.pipelines.detect import Subject, detect_in_image

SAME_SUBJECT_MAX_DIST = 0.45  # histogram distance (0 = identical colours, 1 = disjoint)


@dataclass
class RefInfo:
    path: Path
    label: str | None  # "person" | "animal" | None (nothing found)
    hist: np.ndarray


@dataclass
class Assignment:
    groups: list[list[int]]  # indices into the image list, one group per replacement
    mappings: list[tuple[int, list[int]]]  # (subject id, image indices)
    reasons: list[str] = field(default_factory=list)


def color_hist(img: Image.Image, mask: Image.Image | None = None, box: tuple[int, int, int, int] | None = None) -> np.ndarray:
    """Normalized 8x4x4 HSV histogram of the masked (and optionally boxed) pixels."""
    img = img.convert("RGB")
    if box is not None:
        img = img.crop(box)
        mask = mask.crop(box) if mask is not None else None
    img.thumbnail((256, 256))
    hsv = np.asarray(img.convert("HSV"), dtype=np.int32)
    sel = np.ones(hsv.shape[:2], dtype=bool)
    if mask is not None:
        m = np.asarray(mask.convert("L").resize(img.size)) > 127
        sel = m if m.sum() > 50 else sel
    px = hsv[sel].copy()
    # hue is meaningless for near-grey/near-black pixels (black fur, dark hair): pool them
    px[(px[:, 1] < 48) | (px[:, 2] < 40), 0] = 0
    h = np.zeros((8, 4, 4), dtype=np.float64)
    np.add.at(h, (px[:, 0] * 8 // 256, px[:, 1] * 4 // 256, px[:, 2] * 4 // 256), 1)
    return (h / max(1.0, h.sum())).ravel()


def hist_dist(a: np.ndarray, b: np.ndarray) -> float:
    """1 - histogram intersection: 0 identical, 1 nothing in common."""
    return float(1.0 - np.minimum(a, b).sum())


def group_refs(refs: list[RefInfo], max_dist: float = SAME_SUBJECT_MAX_DIST) -> list[list[int]]:
    """Single-linkage grouping: same kind of subject AND similar colours => same subject."""
    groups: list[list[int]] = []
    for i, r in enumerate(refs):
        for g in groups:
            if any(refs[j].label == r.label and hist_dist(refs[j].hist, r.hist) <= max_dist for j in g):
                g.append(i)
                break
        else:
            groups.append([i])
    return groups


def pair_groups(groups: list[list[int]], refs: list[RefInfo], subjects: list[Subject],
                subject_hists: dict[int, np.ndarray]) -> tuple[list[tuple[int, list[int]]], str]:
    """Pair each replacement group with a distinct on-screen subject (largest subjects
    first), minimizing total colour distance; ties keep size order."""
    candidates = subjects[: max(len(groups), 1)]
    if len(groups) == 1:
        return [(candidates[0].id, groups[0])], "one replacement -> the largest subject"
    group_hist = [np.mean([refs[i].hist for i in g], axis=0) for g in groups]
    best: tuple[float, tuple[int, ...]] | None = None
    for perm in itertools.permutations(range(len(candidates)), len(groups)):
        cost = sum(hist_dist(group_hist[g], subject_hists[candidates[s].id]) for g, s in enumerate(perm))
        if best is None or cost < best[0] - 1e-9:
            best = (cost, perm)
    assert best is not None
    order_cost = sum(hist_dist(group_hist[g], subject_hists[candidates[g].id]) for g in range(len(groups)))
    if best[0] < order_cost - 0.05:  # only reorder when appearance clearly suggests it
        perm, why = best[1], "paired by appearance (head/hair colour vs. subject colour)"
    else:
        perm, why = tuple(range(len(groups))), "paired by size order (appearance gave no clear preference)"
    return [(candidates[s].id, groups[g]) for g, s in enumerate(perm)], why


async def describe_ref(client: ComfyClient, path: Path, *, profile: str) -> RefInfo:
    img = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    with tempfile.TemporaryDirectory(prefix="mm-ref-") as tmp:
        found = await detect_in_image(client, path, "person:1, animal:1", Path(tmp), profile=profile,
                                      min_area_frac=0.01)
        if not found:
            return RefInfo(path, None, color_hist(img))
        main = found[0]
        mask = Image.open(main.mask_path).convert("L").resize(img.size)
        return RefInfo(path, main.label, color_hist(img, mask))


def subject_head_hist(frame: Image.Image, subject: Subject) -> np.ndarray:
    """Colour of the subject's upper third (hair/head) — what tells performers apart
    when they wear matching outfits."""
    mask = Image.open(subject.mask_path).convert("L").resize(frame.size)
    x1, y1, x2, y2 = subject.bbox
    return color_hist(frame, mask, (x1, y1, x2, y1 + max(1, (y2 - y1) // 3)))


async def assign(
    client: ComfyClient,
    images: list[Path],
    subjects: list[Subject],
    frame: Image.Image,
    *,
    profile: str,
    images_are: str = "auto",
) -> Assignment:
    if not subjects:
        raise ValueError("No people or animals were found in the video's first frame.")
    reasons: list[str] = []
    if images_are == "same_subject" or len(images) == 1:
        groups = [list(range(len(images)))]
        reasons.append("all photos treated as the same replacement" + (" (as requested)" if images_are != "auto" else ""))
        refs: list[RefInfo] = []
    else:
        refs = [await describe_ref(client, p, profile=profile) for p in images]
        if images_are == "different_subjects":
            groups = [[i] for i in range(len(images))]
            reasons.append("each photo is a different replacement (as requested)")
        else:
            groups = group_refs(refs)
            labels = [r.label or "unknown" for r in refs]
            if len(groups) == 1:
                reasons.append(f"photos look like the same {labels[0]} -> used together as angles of one replacement")
            else:
                reasons.append(f"photos show {len(groups)} different subjects ({', '.join(labels)}) -> one per on-screen subject")
    if len(groups) > len(subjects):
        raise ValueError(
            f"{len(groups)} different replacements but only {len(subjects)} subject(s) on screen; "
            "pass images_are='same_subject' if the photos show the same one, or use fewer photos."
        )
    if len(groups) == 1:
        return Assignment(groups, [(subjects[0].id, groups[0])], reasons + ["-> the largest subject on screen"])
    hists = {s.id: subject_head_hist(frame, s) for s in subjects[: len(groups)]}
    mappings, why = pair_groups(groups, refs, subjects, hists)
    return Assignment(groups, mappings, reasons + [why])
