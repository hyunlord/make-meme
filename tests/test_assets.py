"""Tests for make_meme.assets: AssetStore add/get/list/resolve."""

from __future__ import annotations

import pytest

from make_meme.assets import AssetStore


def test_add_video_copies_file_and_probes_metadata(video_with_audio):
    store = AssetStore()
    asset = store.add(video_with_audio, "video", origin={"source": "test"})
    assert asset.id.startswith("vid_")
    assert asset.path.is_file()
    assert asset.path != video_with_audio  # copied into its own managed directory
    assert asset.meta["width"] == 320
    assert asset.meta["height"] == 240
    assert asset.meta["has_audio"] is True
    assert asset.origin == {"source": "test"}


def test_add_image_copies_file_and_probes_dimensions(sample_image):
    store = AssetStore()
    asset = store.add(sample_image, "image")
    assert asset.id.startswith("img_")
    assert asset.meta["width"] == 200
    assert asset.meta["height"] == 150


def test_add_with_move_removes_source_file(video_no_audio):
    store = AssetStore()
    asset = store.add(video_no_audio, "video", move=True)
    assert asset.path.is_file()
    assert not video_no_audio.exists()


def test_add_does_not_override_explicitly_passed_meta(video_with_audio):
    store = AssetStore()
    asset = store.add(video_with_audio, "video", meta={"width": 999})
    assert asset.meta["width"] == 999  # explicit meta wins over probed value


def test_get_returns_none_for_unknown_id():
    store = AssetStore()
    assert store.get("vid_deadbeef") is None


def test_resolve_raises_keyerror_for_unknown_id():
    store = AssetStore()
    with pytest.raises(KeyError):
        store.resolve("vid_deadbeef")


def test_resolve_returns_asset_for_known_id(video_no_audio):
    store = AssetStore()
    asset = store.add(video_no_audio, "video")
    assert store.resolve(asset.id).id == asset.id


def test_list_filters_by_kind_and_sorts_newest_first(video_no_audio, sample_image):
    store = AssetStore()
    vid = store.add(video_no_audio, "video")
    img = store.add(sample_image, "image")

    videos = store.list(kind="video")
    assert [a.id for a in videos] == [vid.id]

    images = store.list(kind="image")
    assert [a.id for a in images] == [img.id]

    all_assets = store.list()
    assert {a.id for a in all_assets} == {vid.id, img.id}


def test_list_respects_limit(video_no_audio):
    store = AssetStore()
    for _ in range(3):
        store.add(video_no_audio, "video")
    assert len(store.list(limit=2)) == 2


def test_list_unlimited_returns_more_than_default_limit(video_no_audio):
    store = AssetStore()
    for _ in range(3):
        store.add(video_no_audio, "video")
    assert len(store.list(limit=None)) == 3


def test_find_by_url_returns_matching_asset(video_no_audio, sample_image):
    store = AssetStore()
    store.add(video_no_audio, "video", origin={"url": "https://example.com/other"})
    target = store.add(video_no_audio, "video", origin={"url": "https://example.com/target"})

    found = store.find_by_url("https://example.com/target")
    assert found is not None
    assert found.id == target.id


def test_find_by_url_returns_none_when_no_match(video_no_audio):
    store = AssetStore()
    store.add(video_no_audio, "video", origin={"url": "https://example.com/other"})
    assert store.find_by_url("https://example.com/nope") is None
    assert store.find_by_url("") is None


def test_parent_ids_and_meta_round_trip_through_persistence(video_no_audio):
    store = AssetStore()
    parent = store.add(video_no_audio, "video")
    child = store.add(video_no_audio, "video", parent_ids=[parent.id], meta={"note": "trimmed"})

    reloaded = AssetStore().get(child.id)
    assert reloaded.parent_ids == [parent.id]
    assert reloaded.meta["note"] == "trimmed"


def test_heic_and_rotated_images_are_normalized(tmp_path, monkeypatch):
    """Phone photos (HEIC, EXIF-rotated JPEG) become upright PNGs ComfyUI can read."""
    import pillow_heif
    from PIL import Image

    from make_meme.assets import AssetStore

    pillow_heif.register_heif_opener()
    heic = tmp_path / "dog.heic"
    Image.new("RGB", (40, 30), (200, 120, 40)).save(heic, format="HEIF")
    rotated = tmp_path / "phone.jpg"
    exif = Image.Exif()
    exif[0x0112] = 6  # rotate 90° CW on display
    Image.new("RGB", (40, 30), (10, 20, 30)).save(rotated, exif=exif)

    store = AssetStore(root=tmp_path / "assets")
    a = store.add(heic, "image")
    assert a.path.suffix == ".png" and a.path.is_file()
    assert (a.meta["width"], a.meta["height"]) == (40, 30)
    b = store.add(rotated, "image")
    assert b.path.suffix == ".png"
    assert (b.meta["width"], b.meta["height"]) == (30, 40)
    plain = tmp_path / "plain.png"
    Image.new("RGB", (8, 8)).save(plain)
    assert store.add(plain, "image").path.name == "plain.png"
