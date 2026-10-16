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

_PALETTE = {"black": np.array([20, 20, 20]), "grey": np.array([130, 130, 130])}


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


@pytest.fixture(autouse=True)
def _patch_detector(monkeypatch):
    monkeypatch.setattr(photos, "detect_in_image", fake_detect_in_image)


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
    img.save(path)
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


def _fake_instance(photo: Path, label: str, hist, head_hist=None, pose="upright") -> Instance:
    return Instance(
        photo=photo,
        index=1,
        label=label,
        score=0.9,
        bbox=(0, 0, 100, 100),
        mask_path=Path("/dummy/mask.png"),
        crop_path=Path("/dummy/crop.png"),
        head_path=None,
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
