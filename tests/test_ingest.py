"""Tests for make_meme.ingest: probe, trim, normalize, extract_frame, storyboard, suggest_segments."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from make_meme import ingest
from make_meme.ingest import _display_rotation_degrees


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


def test_normalize_does_not_poison_cache_on_failure(video_with_audio, monkeypatch):
    asset = ingest.prepare_clip(video_with_audio, 0.0, 1.0)
    original_run = ingest._run

    def failing_run(cmd):
        raise RuntimeError("simulated ffmpeg crash")

    monkeypatch.setattr(ingest, "_run", failing_run)
    with pytest.raises(RuntimeError):
        ingest.normalize(asset.path, 64, 48, fps=8)

    out_path = asset.path.parent / "normalized_64x48_8fps.mp4"
    tmp_path = asset.path.parent / "normalized_64x48_8fps.tmp.mp4"
    assert not out_path.exists(), "a failed encode must not leave a truncated 'cached' output"
    assert not tmp_path.exists(), "the temp file must be cleaned up on failure"

    # and a subsequent real call must still work (no corrupted state left behind)
    monkeypatch.setattr(ingest, "_run", original_run)
    out = ingest.normalize(asset.path, 64, 48, fps=8)
    assert out.is_file()


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


# --------------------------------------------------------------------------
# Rotated phone video handling (probe() must report *display* dims, not coded
# ones, since ffmpeg auto-rotates on decode by default).
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("stream", "expected"),
    [
        ({}, 0),
        ({"tags": {"rotate": "90"}}, 90),
        ({"tags": {"rotate": "-90"}}, 270),
        ({"tags": {"rotate": "180"}}, 180),
        ({"tags": {"rotate": "270"}}, 270),
        ({"tags": {"rotate": "0"}}, 0),
        ({"tags": {"rotate": "not-a-number"}}, 0),
        ({"side_data_list": [{"side_data_type": "Display Matrix", "rotation": -90}]}, 270),
        ({"side_data_list": [{"side_data_type": "Display Matrix", "rotation": 90.0}]}, 90),
        ({"side_data_list": [{"side_data_type": "Display Matrix", "rotation": 180}]}, 180),
        ({"side_data_list": [{"side_data_type": "Other"}]}, 0),
        (
            # tags.rotate takes priority over side_data when both are present
            {
                "tags": {"rotate": "90"},
                "side_data_list": [{"side_data_type": "Display Matrix", "rotation": 180}],
            },
            90,
        ),
    ],
)
def test_display_rotation_degrees(stream, expected):
    assert _display_rotation_degrees(stream) == expected


def _fake_ffprobe_run(fake_json: dict):
    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, 0, stdout=json.dumps(fake_json), stderr="")

    return fake_run


def test_probe_swaps_width_height_for_90_degree_rotation(tmp_path, monkeypatch):
    """A phone video shot landscape (coded 1920x1080) with a rotate=90 tag should report
    *display* dims (1080x1920) -- what ffmpeg will actually output when it auto-rotates on
    decode -- not the raw coded dims. My own ffmpeg build won't actually write a rotate tag
    into an mp4 via any CLI incantation I could find, so this exercises probe()'s JSON
    parsing directly against a hand-built (but schema-accurate) ffprobe payload."""

    fake_json = {
        "format": {"duration": "5.0"},
        "streams": [
            {
                "codec_type": "video",
                "width": 1920,
                "height": 1080,
                "r_frame_rate": "30/1",
                "duration": "5.0",
                "tags": {"rotate": "90"},
            }
        ],
    }
    monkeypatch.setattr(ingest.subprocess, "run", _fake_ffprobe_run(fake_json))
    meta = ingest.probe(tmp_path / "phone.mp4")
    assert meta["width"] == 1080
    assert meta["height"] == 1920


def test_probe_swaps_width_height_for_side_data_rotation(tmp_path, monkeypatch):
    fake_json = {
        "format": {"duration": "5.0"},
        "streams": [
            {
                "codec_type": "video",
                "width": 1920,
                "height": 1080,
                "r_frame_rate": "30/1",
                "duration": "5.0",
                "side_data_list": [{"side_data_type": "Display Matrix", "rotation": -90}],
            }
        ],
    }
    monkeypatch.setattr(ingest.subprocess, "run", _fake_ffprobe_run(fake_json))
    meta = ingest.probe(tmp_path / "phone.mp4")
    assert meta["width"] == 1080
    assert meta["height"] == 1920


def test_probe_does_not_swap_dims_for_180_degree_rotation(tmp_path, monkeypatch):
    fake_json = {
        "format": {"duration": "5.0"},
        "streams": [
            {
                "codec_type": "video",
                "width": 1920,
                "height": 1080,
                "r_frame_rate": "30/1",
                "duration": "5.0",
                "tags": {"rotate": "180"},
            }
        ],
    }
    monkeypatch.setattr(ingest.subprocess, "run", _fake_ffprobe_run(fake_json))
    meta = ingest.probe(tmp_path / "phone.mp4")
    assert meta["width"] == 1920
    assert meta["height"] == 1080


# --------------------------------------------------------------------------
# ffmpeg failure messages: tail-only stderr (full logs can be enormous and
# aren't useful to an LLM reading a job's error field).
# --------------------------------------------------------------------------


def test_run_truncates_stderr_to_last_lines(monkeypatch):
    many_lines = "\n".join(f"line {i}" for i in range(50))

    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, 1, stdout="", stderr=many_lines)

    monkeypatch.setattr(ingest.subprocess, "run", fake_run)
    with pytest.raises(RuntimeError) as exc_info:
        ingest._run(["ffmpeg", "-fake"])

    message = str(exc_info.value)
    assert "line 49" in message
    assert "line 0" not in message
    assert message.count("line ") == ingest._STDERR_TAIL_LINES
