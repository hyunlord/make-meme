from __future__ import annotations

import shutil
import subprocess

import pytest

from make_meme.pipelines.reframe import Keyframe, crop_filter, crop_size, parse_aspect, plan_path


def test_crop_size_vertical_from_landscape():
    assert crop_size(1920, 1080, parse_aspect("9:16")) == (608, 1080)
    assert crop_size(1080, 1920, parse_aspect("16:9")) == (1080, 608)


def test_path_follows_subjects_and_keeps_them_inside():
    keys = [Keyframe(0, (316, 422, 673, 832)), Keyframe(1, (294, 386, 780, 842)), Keyframe(2, None),
            Keyframe(3, (508, 458, 923, 857)), Keyframe(4.9, (634, 341, 1039, 859))]
    path = plan_path(keys, (1920, 1080), (608, 1080))
    assert [p[0] for p in path] == [0, 1, 2, 3, 4.9]
    xs = [p[1] for p in path]
    assert xs == sorted(xs)  # pans right with the dancers
    for k, (_, x, _) in zip(keys, path):
        if k.box:
            assert x <= k.box[0] and x + 608 >= k.box[2]
    assert all(0 <= x <= 1920 - 608 for x in xs)


def test_no_subjects_centers_window():
    assert plan_path([Keyframe(0, None)], (1920, 1080), (608, 1080)) == [(0.0, 656, 0)]


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg required")
def test_crop_filter_is_valid_ffmpeg(tmp_path):
    vf = crop_filter([(0.0, 0, 0), (1.0, 100, 0), (1.9, 200, 10)], (100, 180))
    out = tmp_path / "o.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc=size=320x180:rate=10", "-t", "2",
                    "-vf", vf, str(out)], check=True)
    probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                            "stream=width,height", "-of", "csv=p=0", str(out)], capture_output=True, text=True, check=True)
    assert probe.stdout.strip() == "100,180"
