"""Tests for make_meme.ingest: probe, trim, normalize, extract_frame, storyboard, suggest_segments."""

from __future__ import annotations

from pathlib import Path

import pytest

from make_meme import ingest


def test_probe_reports_duration_fps_size_and_audio(video_with_audio):
    meta = ingest.probe(video_with_audio)
    assert meta["duration"] == pytest.approx(3.0, abs=0.2)
    assert meta["fps"] == pytest.approx(24.0, abs=0.5)
    assert meta["width"] == 320
    assert meta["height"] == 240
    assert meta["has_audio"] is True
    assert meta["frame_count"] > 0


def test_probe_detects_missing_audio(video_no_audio):
    meta = ingest.probe(video_no_audio)
    assert meta["has_audio"] is False


def test_prepare_clip_trims_to_requested_duration(video_with_audio):
    asset = ingest.prepare_clip(video_with_audio, start_sec=0.5, end_sec=2.0)
    assert asset.kind == "video"
    assert asset.meta["duration"] == pytest.approx(1.5, abs=0.15)
    assert asset.path.is_file()


def test_prepare_clip_extracts_audio_when_present(video_with_audio):
    asset = ingest.prepare_clip(video_with_audio, start_sec=0.0, end_sec=1.0)
    audio_path = asset.meta.get("audio_path")
    assert audio_path is not None
    assert Path(audio_path).is_file()


def test_prepare_clip_no_audio_path_when_source_silent(video_no_audio):
    asset = ingest.prepare_clip(video_no_audio, start_sec=0.0, end_sec=1.0)
    assert "audio_path" not in asset.meta


def test_prepare_clip_warns_on_long_clips(video_with_audio, monkeypatch):
    monkeypatch.setattr(ingest, "MAX_RECOMMENDED_CLIP_SECONDS", 1.0)
    asset = ingest.prepare_clip(video_with_audio, start_sec=0.0, end_sec=2.5)
    assert asset.meta["warnings"], "expected a long-clip warning"


def test_prepare_clip_each_call_creates_its_own_asset(video_with_audio):
    # Trimming is asset-identity-based now (not path/video_id-keyed): repeated calls with
    # the same args each create a fresh asset, but produce equivalent clips.
    a1 = ingest.prepare_clip(video_with_audio, 0.0, 1.0)
    a2 = ingest.prepare_clip(video_with_audio, 0.0, 1.0)
    assert a1.id != a2.id
    assert a1.meta["duration"] == pytest.approx(a2.meta["duration"], abs=0.1)


def test_prepare_clip_records_parent_ids_and_origin(video_with_audio):
    asset = ingest.prepare_clip(
        video_with_audio,
        0.0,
        1.0,
        parent_ids=["vid_parent"],
        extra_origin={"trimmed_from": "vid_parent"},
    )
    assert asset.parent_ids == ["vid_parent"]
    assert asset.origin["trimmed_from"] == "vid_parent"


def test_normalize_produces_exact_dims_and_fps(video_with_audio):
    asset = ingest.prepare_clip(video_with_audio, 0.0, 1.0)
    out = ingest.normalize(asset.path, 64, 48, fps=8)
    meta = ingest.probe(out)
    assert meta["width"] == 64
    assert meta["height"] == 48
    assert meta["fps"] == pytest.approx(8.0, abs=0.1)
    assert meta["has_audio"] is False


def test_normalize_is_idempotent_by_filename(video_with_audio):
    asset = ingest.prepare_clip(video_with_audio, 0.0, 1.0)
    out1 = ingest.normalize(asset.path, 64, 48, fps=8)
    mtime1 = out1.stat().st_mtime
    out2 = ingest.normalize(asset.path, 64, 48, fps=8)
    assert out1 == out2
    assert out2.stat().st_mtime == mtime1


def test_extract_frame_returns_image_with_source_dimensions(video_with_audio):
    frame = ingest.extract_frame(video_with_audio, 1.0)
    assert frame.size == (320, 240)


def test_storyboard_grid_has_expected_dimensions(video_with_audio):
    board = ingest.storyboard(video_with_audio, frames=4, cols=2)
    assert board.size[0] == 320 * 2  # cell_w (unchanged, source already 320 wide) * cols
    assert board.size[1] > 0


def test_suggest_segments_is_deterministic_and_bounded(video_with_hard_cuts):
    segments_a = ingest.suggest_segments(video_with_hard_cuts, target_len=2.0, max_segments=3)
    segments_b = ingest.suggest_segments(video_with_hard_cuts, target_len=2.0, max_segments=3)
    assert segments_a == segments_b
    assert 1 <= len(segments_a) <= 3
    for seg in segments_a:
        assert 0.0 <= seg["start"] < seg["end"]
        assert seg["end"] <= 6.5  # clip is ~6s; small slack for float rounding
        assert 0.0 <= seg["score"] <= 1.0


def test_suggest_segments_scores_sorted_descending(video_with_hard_cuts):
    segments = ingest.suggest_segments(video_with_hard_cuts, target_len=1.5, max_segments=5)
    scores = [s["score"] for s in segments]
    assert scores == sorted(scores, reverse=True)


def test_suggest_segments_empty_for_zero_duration(tmp_path, monkeypatch):
    monkeypatch.setattr(ingest, "probe", lambda path: {"duration": 0.0})
    assert ingest.suggest_segments(tmp_path / "doesnt-matter.mp4") == []
