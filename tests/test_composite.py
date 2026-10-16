"""Tests for make_meme.pipelines.composite (merging independent single-subject swaps)."""

from __future__ import annotations

import shutil
import subprocess

import numpy as np
import pytest

from make_meme import ingest
from make_meme.pipelines.composite import composite_frame, composite_swaps


def _frame(fill=(120, 120, 120)):
    return np.full((64, 96, 3), fill, np.uint8)


def test_each_layer_contributes_only_where_it_changed():
    base = _frame()
    left, right = base + 1, base.copy()  # +1: model noise on the untouched background must not leak
    left[10:50, 5:35] = (20, 20, 20)
    right[10:50, 60:90] = (240, 200, 10)
    out = composite_frame(base, [left, right])
    assert tuple(out[30, 20]) == (20, 20, 20)
    assert tuple(out[30, 75]) == (240, 200, 10)
    assert np.abs(out[0:5, 40:55].astype(int) - 120).max() <= 1  # background stays original


def test_overlap_goes_to_the_stronger_change():
    base = _frame()
    weak, strong = base.copy(), base.copy()
    weak[10:50, 20:70] = (160, 160, 160)
    strong[10:50, 40:90] = (0, 0, 0)
    out = composite_frame(base, [weak, strong])
    assert tuple(out[30, 55]) == (0, 0, 0)  # contested: strong wins
    assert tuple(out[30, 25]) == (160, 160, 160)  # weak-only area kept


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg required")
def test_composite_swaps_streams_videos(tmp_path):
    def make(name, extra):
        path = tmp_path / name
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                        "color=c=gray:size=96x64:rate=16:duration=0.5", "-vf", extra or "null",
                        "-pix_fmt", "yuv420p", str(path)], check=True)
        return path

    base = make("base.mp4", "")
    a = make("a.mp4", "drawbox=x=5:y=10:w=30:h=40:color=black:t=fill")
    b = make("b.mp4", "drawbox=x=60:y=10:w=30:h=40:color=white:t=fill")
    out = composite_swaps(base, [a, b], tmp_path / "out.mp4", fps=16)
    frame = np.asarray(ingest.extract_frame(out, 0.2).convert("L"))
    assert frame[30, 20] < 40 and frame[30, 75] > 215 and abs(int(frame[5, 48]) - 128) < 12
    assert ingest.probe(out)["frame_count"] == ingest.probe(base)["frame_count"]
