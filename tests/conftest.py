"""Shared pytest fixtures: isolated MAKE_MEME_HOME, synthetic ffmpeg test videos.

These fixtures are used by core-builder's own tests (ingest/assets/jobs/
chunking/post/server). They don't touch anything under tests/sources/.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from make_meme import config


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    """Point MAKE_MEME_HOME at a throwaway directory for every test.

    Also resets the config cache and the server module's asset/job singletons
    so each test starts with a clean, isolated store.
    """

    home = tmp_path / "make-meme-home"
    monkeypatch.setenv("MAKE_MEME_HOME", str(home))
    config.reset_settings_cache()

    import make_meme.server as server_module

    server_module._assets = None
    server_module._jobs = None

    yield config.get_settings()

    server_module._assets = None
    server_module._jobs = None
    config.reset_settings_cache()


def _make_testsrc_video(
    path: Path,
    duration: float = 3.0,
    color: str = "red",
    with_audio: bool = True,
    size: str = "320x240",
    fps: int = 24,
) -> Path:
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"color=c={color}:size={size}:rate={fps}:duration={duration}",
    ]
    if with_audio:
        cmd += ["-f", "lavfi", "-i", f"sine=frequency=440:duration={duration}"]
    cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p"]
    if with_audio:
        cmd += ["-c:a", "aac", "-shortest"]
    cmd += [str(path)]
    subprocess.run(cmd, check=True, capture_output=True)
    return path


@pytest.fixture
def video_with_audio(tmp_path) -> Path:
    return _make_testsrc_video(tmp_path / "with_audio.mp4", duration=3.0, with_audio=True)


@pytest.fixture
def video_no_audio(tmp_path) -> Path:
    return _make_testsrc_video(tmp_path / "no_audio.mp4", duration=3.0, with_audio=False)


@pytest.fixture
def video_with_hard_cuts(tmp_path) -> Path:
    """A ~6s video made of three 2s segments with abrupt color changes (hard scene cuts)."""

    parts = []
    for i, color in enumerate(["red", "blue", "green"]):
        part = tmp_path / f"part_{i}.mp4"
        _make_testsrc_video(part, duration=2.0, color=color, with_audio=False)
        parts.append(part)

    concat_list = tmp_path / "concat.txt"
    concat_list.write_text("\n".join(f"file '{p}'" for p in parts))
    out = tmp_path / "hard_cuts.mp4"
    subprocess.run(
        [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list),
            "-c:v", "libx264", "-pix_fmt", "yuv420p", str(out),
        ],
        check=True, capture_output=True,
    )
    return out


@pytest.fixture
def sample_image(tmp_path) -> Path:
    from PIL import Image

    path = tmp_path / "photo.jpg"
    Image.new("RGB", (200, 150), color=(10, 20, 30)).save(path)
    return path
