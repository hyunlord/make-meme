"""Offline tests for make_meme.pipelines.photos (no network/GPU).

``detect_in_image`` is monkeypatched with a fake "SAM 3" that finds solid-colour
rectangular blobs on a white background by nearest-colour classification --
enough to exercise the whole organize_photos pipeline deterministically against
synthetic photos, without a real ComfyUI/SAM 3 call.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from PIL import Image, ImageDraw, ImageFilter

from make_meme.comfy.client import ComfyError
from make_meme.pipelines import photos
from make_meme.pipelines.detect import Subject
from make_meme.pipelines.photos import (
    Identity,
    Instance,
    _compute_quality,
    _identity_id,
    choose_refs,
    contact_sheet,
    describe_coat,
    group_instances,
    organize_photos,
)

# ---------------------------------------------------------------------------
# Fake SAM 3: finds solid-colour blobs on a white background by nearest colour
# ---------------------------------------------------------------------------

_PALETTE = {
    "black": np.array([20, 20, 20]),
    "grey": np.array([130, 130, 130]),
    "blue": np.array([30, 30, 200]),  # used only by the subject_kind tests' fake "person" blobs
}


def _classify_pixels(colors: np.ndarray) -> np.ndarray:
    dists = np.stack(
        [np.abs(colors.astype(int) - ref).sum(axis=1) for ref in _PALETTE.values()], axis=1
    )
    idx = dists.argmin(axis=1)
    names = list(_PALETTE.keys())
    return np.array([names[i] for i in idx])


async def fake_detect_in_image(
    client, image_path, query, out_dir, *, profile, threshold=0.5, min_area_frac=0.02
):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    img = Image.open(image_path).convert("RGB")
    w, h = img.size

    if "head" in query:
        bbox = (int(w * 0.1), 0, int(w * 0.9), int(h * 0.45))
        mask = Image.new("L", (w, h), 0)
        ImageDraw.Draw(mask).rectangle(bbox, fill=255)
        mask_path = out_dir / "mask_head.png"
        mask.save(mask_path)
        return [Subject(1, "head", 0.9, bbox, str(mask_path))]

    arr = np.asarray(img)
    non_white = np.any(arr < 240, axis=-1)
    if not non_white.any():
        return []
    ys, xs = np.where(non_white)
    names = _classify_pixels(arr[ys, xs])

    found = []
    for name in sorted(set(names)):
        sel = names == name
        cys, cxs = ys[sel], xs[sel]
        bbox = (int(cxs.min()), int(cys.min()), int(cxs.max()) + 1, int(cys.max()) + 1)
        area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
        if area < min_area_frac * w * h:
            continue
        mask_arr = np.zeros((h, w), dtype=np.uint8)
        mask_arr[cys, cxs] = 255
        mask_path = out_dir / f"mask_{name}.png"
        Image.fromarray(mask_arr).save(mask_path)
        found.append((area, Subject(0, "animal", 0.95, bbox, str(mask_path))))

    found.sort(key=lambda t: t[0], reverse=True)
    subjects = [s for _, s in found]
    for i, s in enumerate(subjects, start=1):
        s.id = i
    return subjects


async def fake_embed_crop(client, image_path, mask_path, *, profile):
    """Deterministic fake DINOv2 embedding: the (masked) mean RGB, broadcast into a
    384-d vector and L2-normalized. Keeps the pre-embedding tests' colour-based
    separation working (same signal the histogram already carried) while exercising
    the real embedding code path end to end.
    """

    img = Image.open(image_path).convert("RGB")
    arr = np.asarray(img, dtype=np.float64)
    if mask_path is not None:
        mask = np.asarray(Image.open(mask_path).convert("L").resize(img.size))
        sel = mask > 127
        mean_rgb = arr[sel].mean(axis=0) if sel.sum() > 0 else arr.reshape(-1, 3).mean(axis=0)
    else:
        mean_rgb = arr.reshape(-1, 3).mean(axis=0)
    vec = np.zeros(384, dtype=np.float64)
    vec[:3] = mean_rgb / 255.0
    norm = np.linalg.norm(vec)
    return vec / norm if norm > 0 else vec


@pytest.fixture(autouse=True)
def _patch_detector(monkeypatch):
    monkeypatch.setattr(photos, "detect_in_image", fake_detect_in_image)
    monkeypatch.setattr(photos, "_embed_crop", fake_embed_crop)


def _make_photo(
    path: Path, blobs: list[tuple[str, tuple[int, int, int, int]]], size=(400, 300), blur=False
):
    img = Image.new("RGB", size, (255, 255, 255))
    draw = ImageDraw.Draw(img)
    for color, bbox in blobs:
        rgb = tuple(int(v) for v in _PALETTE[color])
        draw.rectangle(bbox, fill=rgb)
    if blur:
        img = img.filter(ImageFilter.GaussianBlur(radius=6))
    path.parent.mkdir(parents=True, exist_ok=True)
    # Always lossless, regardless of the given filename's extension (PIL detects actual
    # format from content when reopening, not the extension): JPEG's ringing artifacts at
    # a hard colour edge can otherwise fool the fake detector's nearest-colour classifier
    # into seeing a third, spurious blob at the boundary.
    img.save(path, format="PNG")
    return path


UPRIGHT_BOX = (140, 50, 260, 260)  # 120x210, aspect 1.75 -> upright
LEFT_BOX = (20, 50, 140, 260)
RIGHT_BOX = (260, 50, 380, 260)


# ---------------------------------------------------------------------------
# describe_coat
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "rgb,expected",
    [
        ((20, 20, 20), "black"),
        ((245, 245, 245), "white"),
        ((128, 128, 128), "grey"),
        ((100, 110, 120), "blue-grey"),
        ((90, 60, 30), "brown"),
        ((210, 160, 40), "golden"),
        ((180, 30, 30), "red"),
        ((200, 170, 120), "tan/fawn"),
        ((230, 215, 180), "cream"),
    ],
)
def test_describe_coat_solid_colors(rgb, expected):
    img = Image.new("RGB", (20, 20), rgb)
    assert describe_coat(img) == expected


def test_describe_coat_accepts_histogram_shape():
    from make_meme.pipelines.assign import color_hist

    img = Image.new("RGB", (40, 40), (20, 20, 20))
    hist = color_hist(img)
    assert describe_coat(hist) == "black"
    assert describe_coat(hist.reshape(8, 4, 4)) == "black"


def test_describe_coat_accepts_raw_pixel_array():
    pixels = np.array([[0, 0, 20]] * 50)  # H,S,V already 0-255 scaled, near-black
    assert describe_coat(pixels) == "black"


def test_describe_coat_empty_histogram_is_unknown():
    assert describe_coat(np.zeros(128)) == "unknown"


# ---------------------------------------------------------------------------
# group_instances
# ---------------------------------------------------------------------------


def _fake_instance(
    photo: Path, label: str, hist, head_hist=None, pose="upright", embedding=None, head_path=None
) -> Instance:
    return Instance(
        photo=photo,
        index=1,
        label=label,
        score=0.9,
        bbox=(0, 0, 100, 100),
        mask_path=Path("/dummy/mask.png"),
        crop_path=Path("/dummy/crop.png"),
        head_path=head_path,
        quality={
            "pose": pose,
            "area_frac": 0.1,
            "sharpness": 100.0,
            "cut_off": False,
            "resolution": 600,
            "head_frac": 0.0,
        },
        hist=np.asarray(hist, dtype=np.float64),
        head_hist=None if head_hist is None else np.asarray(head_hist, dtype=np.float64),
        embedding=None if embedding is None else np.asarray(embedding, dtype=np.float64),
    )


def _hist_for(rgb) -> np.ndarray:
    from make_meme.pipelines.assign import color_hist

    return color_hist(Image.new("RGB", (40, 40), rgb))


def test_group_instances_separates_two_colors_same_label():
    black_hist = _hist_for((20, 20, 20))
    grey_hist = _hist_for((160, 160, 160))
    instances = [
        _fake_instance(Path("p1.jpg"), "animal", black_hist),
        _fake_instance(Path("p2.jpg"), "animal", black_hist),
        _fake_instance(Path("p3.jpg"), "animal", grey_hist),
        _fake_instance(Path("p4.jpg"), "animal", grey_hist),
    ]
    groups = group_instances(instances)
    assert len(groups) == 2
    sizes = sorted(len(g) for g in groups)
    assert sizes == [2, 2]


def test_group_instances_never_merges_different_labels():
    hist = _hist_for((20, 20, 20))
    instances = [
        _fake_instance(Path("p1.jpg"), "person", hist),
        _fake_instance(Path("p2.jpg"), "animal", hist),
    ]
    groups = group_instances(instances)
    assert len(groups) == 2


def test_group_instances_cannot_link_same_photo():
    """Two instances from the same photo must never end up in one identity,
    even if their appearance is identical (forcing the algorithm to *want* to merge)."""

    hist = _hist_for((20, 20, 20))
    same_photo = Path("both.jpg")
    instances = [
        _fake_instance(same_photo, "animal", hist),
        _fake_instance(same_photo, "animal", hist),
    ]
    groups = group_instances(instances)
    assert len(groups) == 2
    assert all(len(g) == 1 for g in groups)


def test_group_instances_respects_threshold():
    black_hist = _hist_for((20, 20, 20))
    grey_hist = _hist_for((160, 160, 160))
    instances = [
        _fake_instance(Path("p1.jpg"), "animal", black_hist),
        _fake_instance(Path("p2.jpg"), "animal", grey_hist),
    ]
    # distance between black and grey (maximally disjoint, solid-colour) histograms is 1.0:
    # stays split under any threshold below that, merges once the threshold reaches it.
    assert len(group_instances(instances, threshold=0.01)) == 2
    assert len(group_instances(instances, threshold=1.0)) == 1


def test_group_instances_empty():
    assert group_instances([]) == []


# ---------------------------------------------------------------------------
# _pairwise_distance: DINOv2 embedding (primary) + histogram (tie-breaker)
# ---------------------------------------------------------------------------


def test_pairwise_distance_embedding_dominates_conflicting_histogram():
    """With embeddings present, the 0.8-weighted embedding distance should dominate a
    conflicting histogram signal -- exactly the real-world failure mode that motivated
    switching from histogram-only distance (same dog, different lighting -> histograms
    disagree; DINOv2 embeddings of the same real subject stay close)."""

    from make_meme.pipelines.photos import _pairwise_distance

    black_hist, grey_hist = _hist_for((20, 20, 20)), _hist_for((160, 160, 160))
    same_embedding = [1.0, 0.0, 0.0] + [0.0] * 381
    a = _fake_instance(Path("p1.jpg"), "animal", black_hist, embedding=same_embedding)
    b = _fake_instance(Path("p2.jpg"), "animal", grey_hist, embedding=same_embedding)
    # Histograms are maximally disjoint (distance 1.0) but embeddings are identical
    # (distance 0.0); the blend (0.8*0 + 0.2*1.0 = 0.2) should land well under 0.5.
    assert _pairwise_distance(a, b) == pytest.approx(0.2)


def test_pairwise_distance_falls_back_to_histogram_without_embeddings():
    from make_meme.pipelines.photos import _hist_distance, _pairwise_distance

    black_hist, grey_hist = _hist_for((20, 20, 20)), _hist_for((160, 160, 160))
    a = _fake_instance(Path("p1.jpg"), "animal", black_hist, embedding=None)
    b = _fake_instance(Path("p2.jpg"), "animal", grey_hist, embedding=None)
    assert _pairwise_distance(a, b) == pytest.approx(_hist_distance(a, b))


def test_pairwise_distance_falls_back_when_only_one_side_has_an_embedding():
    from make_meme.pipelines.photos import _hist_distance, _pairwise_distance

    black_hist, grey_hist = _hist_for((20, 20, 20)), _hist_for((160, 160, 160))
    a = _fake_instance(Path("p1.jpg"), "animal", black_hist, embedding=[1.0] + [0.0] * 383)
    b = _fake_instance(Path("p2.jpg"), "animal", grey_hist, embedding=None)
    assert _pairwise_distance(a, b) == pytest.approx(_hist_distance(a, b))


def test_cosine_distance_identical_and_orthogonal_and_opposite():
    from make_meme.pipelines.photos import _cosine_distance

    assert _cosine_distance(np.array([1.0, 0.0]), np.array([1.0, 0.0])) == pytest.approx(0.0)
    assert _cosine_distance(np.array([1.0, 0.0]), np.array([0.0, 1.0])) == pytest.approx(0.5)
    assert _cosine_distance(np.array([1.0, 0.0]), np.array([-1.0, 0.0])) == pytest.approx(1.0)


def test_cosine_distance_zero_vector_is_max_distance():
    from make_meme.pipelines.photos import _cosine_distance

    assert _cosine_distance(np.zeros(4), np.array([1.0, 0.0, 0.0, 0.0])) == 1.0


# ---------------------------------------------------------------------------
# choose_refs
# ---------------------------------------------------------------------------


def _instance_with_quality(photo, quality, head_path=None) -> Instance:
    return Instance(
        photo=photo,
        index=1,
        label="animal",
        score=0.9,
        bbox=(0, 0, 100, 100),
        mask_path=Path("/dummy/mask.png"),
        crop_path=Path("/dummy/crop.png"),
        head_path=head_path,
        quality=quality,
        hist=np.zeros(128),
    )


def test_choose_refs_prefers_upright_over_lying():
    upright = _instance_with_quality(
        Path("a.jpg"),
        {
            "pose": "upright",
            "area_frac": 0.2,
            "sharpness": 200.0,
            "cut_off": False,
            "resolution": 600,
            "head_frac": 0.0,
        },
    )
    lying = _instance_with_quality(
        Path("b.jpg"),
        {
            "pose": "lying",
            "area_frac": 0.2,
            "sharpness": 200.0,
            "cut_off": False,
            "resolution": 600,
            "head_frac": 0.0,
        },
    )
    ref_full, _ = choose_refs([upright, lying])
    assert ref_full is upright


def test_choose_refs_prefers_sharper():
    sharp = _instance_with_quality(
        Path("a.jpg"),
        {
            "pose": "upright",
            "area_frac": 0.2,
            "sharpness": 900.0,
            "cut_off": False,
            "resolution": 600,
            "head_frac": 0.0,
        },
    )
    blurry = _instance_with_quality(
        Path("b.jpg"),
        {
            "pose": "upright",
            "area_frac": 0.2,
            "sharpness": 5.0,
            "cut_off": False,
            "resolution": 600,
            "head_frac": 0.0,
        },
    )
    ref_full, _ = choose_refs([sharp, blurry])
    assert ref_full is sharp


def test_choose_refs_avoids_cut_off():
    clean = _instance_with_quality(
        Path("a.jpg"),
        {
            "pose": "upright",
            "area_frac": 0.2,
            "sharpness": 200.0,
            "cut_off": False,
            "resolution": 600,
            "head_frac": 0.0,
        },
    )
    cut = _instance_with_quality(
        Path("b.jpg"),
        {
            "pose": "upright",
            "area_frac": 0.2,
            "sharpness": 200.0,
            "cut_off": True,
            "resolution": 600,
            "head_frac": 0.0,
        },
    )
    ref_full, _ = choose_refs([clean, cut])
    assert ref_full is clean


def test_choose_refs_head_requires_head_path():
    no_head = _instance_with_quality(
        Path("a.jpg"),
        {
            "pose": "upright",
            "area_frac": 0.2,
            "sharpness": 200.0,
            "cut_off": False,
            "resolution": 600,
            "head_frac": 0.0,
        },
    )
    with_head = _instance_with_quality(
        Path("b.jpg"),
        {
            "pose": "upright",
            "area_frac": 0.2,
            "sharpness": 200.0,
            "cut_off": False,
            "resolution": 600,
            "head_frac": 0.3,
        },
        head_path=Path("/dummy/head.png"),
    )
    _ref_full, ref_head = choose_refs([no_head, with_head])
    assert ref_head is with_head


def test_choose_refs_no_head_candidates_returns_none():
    only = _instance_with_quality(
        Path("a.jpg"),
        {
            "pose": "upright",
            "area_frac": 0.2,
            "sharpness": 200.0,
            "cut_off": False,
            "resolution": 600,
            "head_frac": 0.0,
        },
    )
    _, ref_head = choose_refs([only])
    assert ref_head is None


def test_choose_refs_empty_raises():
    with pytest.raises(ValueError):
        choose_refs([])


# ---------------------------------------------------------------------------
# _compute_quality
# ---------------------------------------------------------------------------


def test_compute_quality_basic_properties(tmp_path):
    crop_path = tmp_path / "crop.png"
    Image.new("RGB", (300, 400), (0, 0, 0)).save(crop_path)  # sharp hard edges == whole image
    q = _compute_quality(
        (10, 10, 110, 310), img_w=400, img_h=400, crop_path=crop_path, head_frac=0.25
    )
    assert q["pose"] == "upright"  # h=300,w=100 -> aspect 3.0
    assert q["cut_off"] is False
    assert q["resolution"] == min(300, 400)
    assert q["head_frac"] == 0.25
    assert 0.0 < q["area_frac"] < 1.0


def test_compute_quality_detects_cut_off_at_border():
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        crop_path = Path(tmp) / "crop.png"
        Image.new("RGB", (100, 100), (0, 0, 0)).save(crop_path)
        # touches left and bottom of a 400x400 frame
        q = _compute_quality(
            (0, 150, 100, 400), img_w=400, img_h=400, crop_path=crop_path, head_frac=0.0
        )
        assert q["cut_off"] is True


def test_compute_quality_pose_lying():
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        crop_path = Path(tmp) / "crop.png"
        Image.new("RGB", (200, 80), (0, 0, 0)).save(crop_path)
        q = _compute_quality(
            (50, 50, 250, 130), img_w=400, img_h=400, crop_path=crop_path, head_frac=0.0
        )
        assert q["pose"] == "lying"


# ---------------------------------------------------------------------------
# _identity_id
# ---------------------------------------------------------------------------


def test_identity_id_sequence():
    assert [_identity_id(i) for i in range(4)] == ["A", "B", "C", "D"]
    assert _identity_id(25) == "Z"
    assert _identity_id(26) == "AA"


# ---------------------------------------------------------------------------
# organize_photos end to end (synthetic photos, fake detector)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_organize_photos_end_to_end(tmp_path):
    photos_dir = tmp_path / "photos"
    out_dir = tmp_path / "out"

    paths = []
    for i in range(5):
        p = _make_photo(photos_dir / f"black_{i}.jpg", [("black", UPRIGHT_BOX)])
        paths.append(p)
    for i in range(5):
        p = _make_photo(photos_dir / f"grey_{i}.jpg", [("grey", UPRIGHT_BOX)])
        paths.append(p)
    both = _make_photo(photos_dir / "both.jpg", [("black", LEFT_BOX), ("grey", RIGHT_BOX)])
    paths.append(both)

    identities = await organize_photos(client=None, photos=paths, out_dir=out_dir, profile="cpu")

    assert len(identities) == 2
    sizes = sorted(len(ident.instances) for ident in identities)
    assert sizes == [6, 6]  # 5 solo photos + 1 shared photo each

    coats = {ident.coat for ident in identities}
    assert "black" in coats
    assert any("grey" in c for c in coats)  # "grey" or "blue-grey"

    for ident in identities:
        assert ident.ref_full in ident.instances
        assert 0.0 <= ident.confidence <= 1.0
        assert isinstance(ident.advice, list)
        # Every instance came from a photo actually in this identity's group, and no two
        # instances in the same identity share a photo (cannot-link holds end to end).
        photo_counts: dict[Path, int] = {}
        for inst in ident.instances:
            photo_counts[inst.photo] = photo_counts.get(inst.photo, 0) + 1
        assert all(c == 1 for c in photo_counts.values())

    # Both the two-dog photo's instances landed in different identities.
    both_instances = [
        inst for ident in identities for inst in ident.instances if inst.photo == both
    ]
    assert len(both_instances) == 2
    assert both_instances[0].label == both_instances[1].label == "animal"

    # JSON-serializable.
    dumped = json.dumps([ident.to_json() for ident in identities])
    reloaded = json.loads(dumped)
    assert len(reloaded) == 2

    # Contact sheet renders.
    sheet = contact_sheet(identities)
    assert isinstance(sheet, Image.Image)
    assert sheet.width > 0 and sheet.height > 0


@pytest.mark.asyncio
async def test_organize_photos_advice_no_upright_photo(tmp_path):
    photos_dir = tmp_path / "photos"
    out_dir = tmp_path / "out"
    lying_box = (40, 150, 360, 230)  # wide, short -> lying
    paths = [_make_photo(photos_dir / f"lying_{i}.jpg", [("black", lying_box)]) for i in range(2)]

    identities = await organize_photos(client=None, photos=paths, out_dir=out_dir, profile="cpu")
    assert len(identities) == 1
    assert any("upright" in a for a in identities[0].advice)


@pytest.mark.asyncio
async def test_organize_photos_advice_single_photo(tmp_path):
    photos_dir = tmp_path / "photos"
    out_dir = tmp_path / "out"
    paths = [_make_photo(photos_dir / "solo.jpg", [("black", UPRIGHT_BOX)])]

    identities = await organize_photos(client=None, photos=paths, out_dir=out_dir, profile="cpu")
    assert len(identities) == 1
    assert any("Only one photo" in a for a in identities[0].advice)


@pytest.mark.asyncio
async def test_organize_photos_no_detections_returns_empty(tmp_path):
    photos_dir = tmp_path / "photos"
    out_dir = tmp_path / "out"
    blank = photos_dir / "blank.jpg"
    photos_dir.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (200, 150), (255, 255, 255)).save(blank)

    identities = await organize_photos(client=None, photos=[blank], out_dir=out_dir, profile="cpu")
    assert identities == []


@pytest.mark.asyncio
async def test_organize_photos_survives_head_detection_crash(tmp_path, monkeypatch):
    """Regression: SAM 3's own 'head' sub-workflow can error out (not just return zero
    matches) on some crops -- confirmed live against a real ComfyUI instance. Head
    detection is best-effort, so this must degrade to head_path=None, not crash the run."""

    async def flaky_detect(
        client, image_path, query, out_dir, *, profile, threshold=0.5, min_area_frac=0.02
    ):
        if "head" in query:
            raise ComfyError(
                "ComfyUI execution failed in SaveImage (node 6): index 0 is out of bounds"
            )
        return await fake_detect_in_image(
            client,
            image_path,
            query,
            out_dir,
            profile=profile,
            threshold=threshold,
            min_area_frac=min_area_frac,
        )

    monkeypatch.setattr(photos, "detect_in_image", flaky_detect)

    photos_dir = tmp_path / "photos"
    out_dir = tmp_path / "out"
    paths = [_make_photo(photos_dir / f"black_{i}.jpg", [("black", UPRIGHT_BOX)]) for i in range(2)]

    identities = await organize_photos(client=None, photos=paths, out_dir=out_dir, profile="cpu")
    assert len(identities) == 1
    assert identities[0].ref_head is None
    assert all(inst.head_path is None for inst in identities[0].instances)
    assert any("ref2" in a for a in identities[0].advice)


@pytest.mark.asyncio
async def test_organize_photos_advice_notes_embedding_fallback(tmp_path, monkeypatch):
    """When the DINOv2 embedding recipe/node is unavailable, organize_photos must still
    complete (histogram-only) and say so in the identity's advice."""

    async def no_embeddings(client, image_path, mask_path, *, profile):
        return None

    monkeypatch.setattr(photos, "_embed_crop", no_embeddings)

    photos_dir = tmp_path / "photos"
    out_dir = tmp_path / "out"
    paths = [_make_photo(photos_dir / f"black_{i}.jpg", [("black", UPRIGHT_BOX)]) for i in range(2)]

    identities = await organize_photos(client=None, photos=paths, out_dir=out_dir, profile="cpu")
    assert len(identities) == 1
    assert all(inst.embedding is None for inst in identities[0].instances)
    assert any("DINOv2 embedding unavailable" in a for a in identities[0].advice)


# ---------------------------------------------------------------------------
# subject_kind: pet-set detection / filtering stray "person" detections
# ---------------------------------------------------------------------------

_KIND_LABELS = {"black": "animal", "grey": "animal", "blue": "person"}


def _classify_pixels_kind(colors: np.ndarray) -> np.ndarray:
    names = list(_PALETTE.keys())
    refs = list(_PALETTE.values())
    dists = np.stack([np.abs(colors.astype(int) - ref).sum(axis=1) for ref in refs], axis=1)
    idx = dists.argmin(axis=1)
    return np.array([names[i] for i in idx])


async def fake_detect_with_person(
    client, image_path, query, out_dir, *, profile, threshold=0.5, min_area_frac=0.02, no_head=False
):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    img = Image.open(image_path).convert("RGB")
    w, h = img.size

    if "head" in query:
        if no_head:
            return []
        bbox = (int(w * 0.1), 0, int(w * 0.9), int(h * 0.45))
        mask = Image.new("L", (w, h), 0)
        ImageDraw.Draw(mask).rectangle(bbox, fill=255)
        mask_path = out_dir / "mask_head.png"
        mask.save(mask_path)
        return [Subject(1, "head", 0.9, bbox, str(mask_path))]

    arr = np.asarray(img)
    non_white = np.any(arr < 240, axis=-1)
    if not non_white.any():
        return []
    ys, xs = np.where(non_white)
    names = _classify_pixels_kind(arr[ys, xs])

    found = []
    for name in sorted(set(names)):
        sel = names == name
        cys, cxs = ys[sel], xs[sel]
        bbox = (int(cxs.min()), int(cys.min()), int(cxs.max()) + 1, int(cys.max()) + 1)
        area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
        if area < min_area_frac * w * h:
            continue
        mask_arr = np.zeros((h, w), dtype=np.uint8)
        mask_arr[cys, cxs] = 255
        mask_path = out_dir / f"mask_{name}.png"
        Image.fromarray(mask_arr).save(mask_path)
        label = _KIND_LABELS[name]
        found.append((area, Subject(0, label, 0.95, bbox, str(mask_path))))

    found.sort(key=lambda t: t[0], reverse=True)
    subjects = [s for _, s in found]
    for i, s in enumerate(subjects, start=1):
        s.id = i
    return subjects


def test_should_drop_persons_animal_mode_always_true():
    from make_meme.pipelines.photos import _should_drop_persons

    assert _should_drop_persons("animal", []) is True
    assert _should_drop_persons("animal", [[]]) is True


def test_should_drop_persons_person_mode_always_false():
    from make_meme.pipelines.photos import _should_drop_persons

    assert _should_drop_persons("person", []) is False


def test_should_drop_persons_auto_majority_animal(tmp_path):
    from make_meme.pipelines.photos import _should_drop_persons

    animal = Subject(1, "animal", 0.9, (0, 0, 10, 10), "/dummy.png")
    person = Subject(1, "person", 0.9, (0, 0, 10, 10), "/dummy.png")
    # 2 of 3 photos have an animal -> pet set -> drop persons.
    per_photo = [[animal], [animal, person], [person]]
    assert _should_drop_persons("auto", per_photo) is True


def test_should_drop_persons_auto_minority_animal():
    from make_meme.pipelines.photos import _should_drop_persons

    animal = Subject(1, "animal", 0.9, (0, 0, 10, 10), "/dummy.png")
    person = Subject(1, "person", 0.9, (0, 0, 10, 10), "/dummy.png")
    # 1 of 3 photos has an animal -> not a pet set -> keep (filtered) persons.
    per_photo = [[person], [person], [animal]]
    assert _should_drop_persons("auto", per_photo) is False


def test_should_drop_persons_auto_empty_is_false():
    from make_meme.pipelines.photos import _should_drop_persons

    assert _should_drop_persons("auto", []) is False


def test_passes_geometric_person_filter():
    from make_meme.pipelines.photos import _passes_geometric_person_filter

    big_centered = (100, 100, 300, 300)  # 200x200 of 400x400 = 0.25 area_frac, not cut off
    assert _passes_geometric_person_filter(big_centered, 400, 400) is True

    too_small = (190, 190, 210, 210)  # 20x20 of 400x400 = 0.0025 area_frac
    assert _passes_geometric_person_filter(too_small, 400, 400) is False

    cut_off_two_sides = (0, 0, 200, 200)  # touches left and top
    assert _passes_geometric_person_filter(cut_off_two_sides, 400, 400) is False


@pytest.mark.asyncio
async def test_organize_photos_subject_kind_animal_drops_persons(tmp_path, monkeypatch):
    monkeypatch.setattr(photos, "detect_in_image", fake_detect_with_person)

    photos_dir = tmp_path / "photos"
    out_dir = tmp_path / "out"
    # A big, otherwise-qualifying person next to (not overlapping) the dog -- still
    # dropped outright in "animal" mode.
    person_box = (20, 20, 130, 280)
    paths = [_make_photo(photos_dir / "both.jpg", [("black", UPRIGHT_BOX), ("blue", person_box)])]

    identities = await organize_photos(
        client=None, photos=paths, out_dir=out_dir, profile="cpu", subject_kind="animal"
    )
    assert len(identities) == 1
    assert identities[0].label == "animal"


@pytest.mark.asyncio
async def test_organize_photos_auto_drops_persons_when_pet_set(tmp_path, monkeypatch):
    monkeypatch.setattr(photos, "detect_in_image", fake_detect_with_person)

    photos_dir = tmp_path / "photos"
    out_dir = tmp_path / "out"
    person_box = (20, 20, 130, 280)
    paths = [
        _make_photo(photos_dir / "dog_only_1.jpg", [("black", UPRIGHT_BOX)]),
        _make_photo(photos_dir / "dog_only_2.jpg", [("black", UPRIGHT_BOX)]),
        # minority of photos also show a (otherwise-qualifying) person
        _make_photo(
            photos_dir / "dog_and_owner.jpg", [("black", UPRIGHT_BOX), ("blue", person_box)]
        ),
    ]

    identities = await organize_photos(client=None, photos=paths, out_dir=out_dir, profile="cpu")
    assert all(ident.label != "person" for ident in identities)


@pytest.mark.asyncio
async def test_organize_photos_person_mode_filters_weak_persons(tmp_path, monkeypatch):
    """subject_kind='person' keeps persons but still screens out ones too small/cut off
    to be a real subject (owners' stray limbs/sleeves), per the geometric pre-filter."""

    monkeypatch.setattr(photos, "detect_in_image", fake_detect_with_person)

    photos_dir = tmp_path / "photos"
    out_dir = tmp_path / "out"
    tiny_person_box = (190, 190, 210, 210)  # well under MIN_PERSON_AREA_FRAC
    real_person_box = (20, 20, 380, 280)
    paths = [
        _make_photo(photos_dir / "tiny.jpg", [("blue", tiny_person_box)]),
        _make_photo(photos_dir / "real.jpg", [("blue", real_person_box)]),
    ]

    identities = await organize_photos(
        client=None, photos=paths, out_dir=out_dir, profile="cpu", subject_kind="person"
    )
    assert len(identities) == 1
    assert len(identities[0].instances) == 1
    assert identities[0].instances[0].photo.name == "real.jpg"


@pytest.mark.asyncio
async def test_organize_photos_person_without_head_is_filtered(tmp_path, monkeypatch):
    """A person detection that's big enough and not cut off still needs a detected head
    to count as a "real subject" outside drop-persons mode."""

    async def detect_no_head(
        client, image_path, query, out_dir, *, profile, threshold=0.5, min_area_frac=0.02
    ):
        return await fake_detect_with_person(
            client,
            image_path,
            query,
            out_dir,
            profile=profile,
            threshold=threshold,
            min_area_frac=min_area_frac,
            no_head=True,
        )

    monkeypatch.setattr(photos, "detect_in_image", detect_no_head)

    photos_dir = tmp_path / "photos"
    out_dir = tmp_path / "out"
    real_person_box = (20, 20, 380, 280)
    paths = [_make_photo(photos_dir / "headless.jpg", [("blue", real_person_box)])]

    identities = await organize_photos(
        client=None, photos=paths, out_dir=out_dir, profile="cpu", subject_kind="person"
    )
    assert identities == []


@pytest.mark.asyncio
async def test_organize_photos_invalid_subject_kind_raises():
    with pytest.raises(ValueError, match="subject_kind"):
        await organize_photos(
            client=None, photos=[], out_dir=Path("/tmp/x"), profile="cpu", subject_kind="dog"
        )


# ---------------------------------------------------------------------------
# contact_sheet edge cases
# ---------------------------------------------------------------------------


def test_contact_sheet_empty_list():
    sheet = contact_sheet([])
    assert isinstance(sheet, Image.Image)
    assert sheet.width > 0 and sheet.height > 0


def test_contact_sheet_single_identity(tmp_path):
    crop_path = tmp_path / "crop.png"
    Image.new("RGB", (100, 100), (20, 20, 20)).save(crop_path)
    inst = Instance(
        photo=Path("a.jpg"),
        index=1,
        label="animal",
        score=0.9,
        bbox=(0, 0, 100, 100),
        mask_path=Path("/dummy/mask.png"),
        crop_path=crop_path,
        head_path=None,
        quality={
            "pose": "upright",
            "area_frac": 0.1,
            "sharpness": 100.0,
            "cut_off": False,
            "resolution": 100,
            "head_frac": 0.0,
        },
        hist=np.zeros(128),
    )
    ident = Identity(
        id="A",
        label="animal",
        instances=[inst],
        ref_full=inst,
        ref_head=None,
        description="an animal with a black coat",
        coat="black",
        confidence=1.0,
        advice=[],
    )
    sheet = contact_sheet([ident])
    assert isinstance(sheet, Image.Image)


def test_choose_refs_avoids_a_colour_cast_photo():
    # Warm indoor light turned the blue-grey greyhound tan in its sharpest photo (NEON test).
    from make_meme.pipelines.assign import color_hist

    rng = np.random.default_rng(0)

    def inst(name, rgb, sharp):
        noise = rng.normal(0, 18, (64, 64, 3))
        img = Image.fromarray(np.clip(np.array(rgb) + noise, 0, 255).astype(np.uint8))
        q = {"pose": "upright", "area_frac": 0.3, "sharpness": sharp, "cut_off": False, "resolution": 512,
             "head_frac": 0.3}
        i = _instance_with_quality(Path(name), q, head_path=Path(f"/dummy/{name}_head.png"))
        i.hist = color_hist(img)
        return i

    greys = [inst(f"g{k}.jpg", (105 + 4 * k, 112 + 4 * k, 125 + 4 * k), 150.0) for k in range(3)]
    warm = inst("warm.jpg", (190, 150, 105), 900.0)  # much sharper, wrong colour
    ref_full, ref_head = choose_refs([*greys, warm])
    assert ref_full is not warm and ref_head is not warm
    # with fewer than 3 photos there is no "usual look" to compare against
    assert choose_refs([greys[0], warm])[0] is warm
