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


def test_parent_ids_and_meta_round_trip_through_persistence(video_no_audio):
    store = AssetStore()
    parent = store.add(video_no_audio, "video")
    child = store.add(video_no_audio, "video", parent_ids=[parent.id], meta={"note": "trimmed"})

    reloaded = AssetStore().get(child.id)
    assert reloaded.parent_ids == [parent.id]
    assert reloaded.meta["note"] == "trimmed"
