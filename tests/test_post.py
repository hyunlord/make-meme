"""Tests for make_meme.post: concat, mux_audio, retime, make_preview."""

from __future__ import annotations

import asyncio
import subprocess

import pytest
from PIL import Image

from make_meme import ingest, post


async def test_concat_videos_sums_chunk_durations(video_no_audio, tmp_path):
    chunk_a = tmp_path / "chunk_a.mp4"
    chunk_b = tmp_path / "chunk_b.mp4"
    chunk_a.write_bytes(video_no_audio.read_bytes())
    chunk_b.write_bytes(video_no_audio.read_bytes())

    out = tmp_path / "concat.mp4"
    await post.concat_videos([chunk_a, chunk_b], out, overlap=0)

    meta_a = ingest.probe(chunk_a)
    meta_out = ingest.probe(out)
    assert meta_out["duration"] == pytest.approx(meta_a["duration"] * 2, rel=0.15)


async def test_concat_videos_drops_overlap_frames(video_no_audio, tmp_path):
    meta_in = ingest.probe(video_no_audio)
    chunk_a = tmp_path / "chunk_a.mp4"
    chunk_b = tmp_path / "chunk_b.mp4"
    chunk_a.write_bytes(video_no_audio.read_bytes())
    chunk_b.write_bytes(video_no_audio.read_bytes())

    overlap_frames = 5
    out = tmp_path / "concat_overlap.mp4"
    await post.concat_videos([chunk_a, chunk_b], out, overlap=overlap_frames)

    meta_out = ingest.probe(out)
    expected_frames = meta_in["frame_count"] * 2 - overlap_frames
    assert meta_out["frame_count"] == pytest.approx(expected_frames, abs=3)


async def test_concat_single_video_preserves_duration(video_no_audio, tmp_path):
    out = tmp_path / "concat_single.mp4"
    await post.concat_videos([video_no_audio], out, overlap=1)

    meta_in = ingest.probe(video_no_audio)
    meta_out = ingest.probe(out)
    assert meta_out["duration"] == pytest.approx(meta_in["duration"], rel=0.1)


async def test_mux_audio_attaches_track_trims_to_video_and_tags_metadata(video_with_audio, tmp_path):
    asset = ingest.prepare_clip(video_with_audio, 0.0, 1.0)
    silent = tmp_path / "silent.mp4"
    await asyncio.to_thread(
        subprocess.run,
        [
            "ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=gray:size=64x48:rate=8:duration=0.5",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", str(silent),
        ],
        check=True, capture_output=True,
    )
    out = tmp_path / "muxed.mp4"
    await post.mux_audio(silent, asset.meta["audio_path"], out)

    out_meta = ingest.probe(out)
    assert out_meta["has_audio"] is True
    assert out_meta["duration"] == pytest.approx(0.5, abs=0.2)

    probe = await asyncio.to_thread(
        subprocess.run,
        ["ffprobe", "-v", "error", "-show_entries", "format_tags=comment", "-of", "default=nw=1", str(out)],
        capture_output=True, text=True, check=True,
    )
    assert "AI-generated" in probe.stdout


async def test_retime_changes_fps(video_no_audio, tmp_path):
    out = tmp_path / "retimed.mp4"
    await post.retime(video_no_audio, 30, out)
    meta = ingest.probe(out)
    assert meta["fps"] == pytest.approx(30.0, abs=1.0)


async def test_make_preview_extracts_a_frame(video_no_audio, tmp_path):
    out = tmp_path / "preview.jpg"
    await post.make_preview(video_no_audio, out, at=0.5)
    assert out.is_file()
    with Image.open(out) as im:
        assert im.size == (320, 240)


# --------------------------------------------------------------------------
# _run internals: tail-only stderr on failure, and killing the ffmpeg
# subprocess if the awaiting task itself gets cancelled.
# --------------------------------------------------------------------------


class _FakeProcess:
    def __init__(self, returncode: int, stderr: bytes = b"", stdout: bytes = b""):
        self.returncode = returncode
        self._stdout = stdout
        self._stderr = stderr
        self.killed = False

    async def communicate(self):
        return self._stdout, self._stderr

    def kill(self):
        self.killed = True

    async def wait(self):
        return self.returncode


async def test_run_truncates_stderr_to_last_lines(monkeypatch):
    many_lines = "\n".join(f"line {i}" for i in range(50)).encode()
    fake = _FakeProcess(1, stderr=many_lines)

    async def fake_create_subprocess_exec(*cmd, **kwargs):
        return fake

    monkeypatch.setattr(post.asyncio, "create_subprocess_exec", fake_create_subprocess_exec)
    with pytest.raises(RuntimeError) as exc_info:
        await post._run(["ffmpeg", "-fake"])

    message = str(exc_info.value)
    assert "line 49" in message
    assert "line 0" not in message
    assert message.count("line ") == post._STDERR_TAIL_LINES


async def test_run_kills_subprocess_when_cancelled(monkeypatch):
    fake = _FakeProcess(0)

    async def hanging_communicate():
        await asyncio.sleep(10)
        return b"", b""

    fake.communicate = hanging_communicate

    async def fake_create_subprocess_exec(*cmd, **kwargs):
        return fake

    monkeypatch.setattr(post.asyncio, "create_subprocess_exec", fake_create_subprocess_exec)

    task = asyncio.ensure_future(post._run(["ffmpeg", "-fake"]))
    await asyncio.sleep(0.05)  # let it reach the communicate() await point
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    assert fake.killed is True
