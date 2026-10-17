"""The `paste` engine: head pose from masks, smoothing, pasting, and a full render with fakes."""

from __future__ import annotations

import shutil
import subprocess

import numpy as np
import pytest
from PIL import Image, ImageDraw

from make_meme import ingest
from make_meme.pipelines import paste as paste_mod
from make_meme.pipelines import render as render_mod
from make_meme.pipelines.detect import Subject
from make_meme.pipelines.paste import HeadPose, head_pose, paste_head, smooth_poses
from make_meme.pipelines.render import render_plan
from make_meme.pipelines.shots import Shot
from make_meme.plan import IdentityRef, MemePlan, new_plan_id
from make_meme.styles import get_style

needs_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg required")


def _ellipse_mask(w, h, cx, cy, rx, ry, angle):
    im = Image.new("L", (w * 2, h * 2), 0)
    ImageDraw.Draw(im).ellipse([cx * 2 - rx * 2, cy * 2 - ry * 2, cx * 2 + rx * 2, cy * 2 + ry * 2], fill=255)
    im = im.rotate(-angle, center=(cx * 2, cy * 2))  # clockwise by `angle`
    return np.asarray(im.resize((w, h))) > 127


def test_head_pose_position_size_and_tilt():
    upright = head_pose(_ellipse_mask(200, 200, 100, 80, 20, 30, 0))
    assert upright is not None
    assert upright.cx == pytest.approx(100, abs=1.5) and upright.cy == pytest.approx(80, abs=1.5)
    assert upright.size == pytest.approx(40, rel=0.1)  # full width of the ellipse (hair doesn't widen a head)
    assert abs(upright.angle) < 3
    tilted = head_pose(_ellipse_mask(200, 200, 100, 80, 20, 30, 25))
    assert tilted.angle == pytest.approx(25, abs=4)  # top leaning right = positive
    assert head_pose(_ellipse_mask(200, 200, 100, 80, 20, 30, -25)).angle == pytest.approx(-25, abs=4)
    assert head_pose(np.zeros((50, 50), bool)) is None
    scaled = head_pose(_ellipse_mask(200, 200, 100, 80, 20, 30, 0), scale=2.0)
    assert scaled.cx == pytest.approx(200, abs=3) and scaled.size == pytest.approx(80, rel=0.1)
    long_hair = head_pose(_ellipse_mask(200, 300, 100, 120, 20, 70, 0))
    assert long_hair.size == pytest.approx(upright.size, rel=0.1)


def test_smoothing_holds_briefly_then_hides():
    p = HeadPose(100, 100, 50, 0)
    poses = [p, p, None, None, None, None, p]
    out = smooth_poses(poses, fps=24, hold_frames=2)
    assert out[2] is not None and out[3] is not None  # held
    assert out[4] is None and out[5] is None  # hidden after the hold
    assert out[6] is not None and out[6][1] < 1.0  # fades back in
    jitter = [HeadPose(100 + (5 if i % 2 else -5), 100, 50, 0) for i in range(40)]
    xs = [o[0].cx for o in smooth_poses(jitter, fps=24, hold_frames=2)[10:]]
    assert max(xs) - min(xs) < 6  # 10 px of jitter is damped


def test_paste_head_follows_pose_and_tilt():
    cutout = Image.new("RGBA", (40, 60), (0, 0, 0, 0))
    ImageDraw.Draw(cutout).rectangle([0, 0, 39, 59], fill=(0, 0, 255, 255))
    ImageDraw.Draw(cutout).rectangle([15, 0, 24, 9], fill=(255, 0, 0, 255))  # red marker on top
    frame = Image.new("RGB", (300, 300), (255, 255, 255))
    paste_head(frame, cutout, HeadPose(150, 150, 60, 30), 1.0, scale=1.5, lift=0.0)
    a = np.asarray(frame).astype(int)
    blue = (a[..., 2] > 200) & (a[..., 0] < 60)
    ys, xs = np.nonzero(blue)
    assert abs(xs.mean() - 150) < 6 and abs(ys.mean() - 150) < 6  # centred on the head
    assert xs.max() - xs.min() > 85  # scaled to 1.5x the head width (90 px before rotation)
    red = (a[..., 0] > 200) & (a[..., 1] < 60) & (a[..., 2] < 60)
    ry, rx = np.nonzero(red)
    assert rx.mean() > 155 and ry.mean() < 130  # tilted clockwise: the top moved right


def _plan(shots, cast, refs):
    idents = [IdentityRef(id=i, label="animal", description=f"dog {i}", coat="black", photos=1, confidence=0.9,
                          ref_full=path, ref_head=path) for i, path in refs.items()]
    return MemePlan(
        id=new_plan_id(), intent="t", source_asset="vid_x", source_title=None, segment={"start": 0, "end": 2},
        clip_asset="vid_y", aspect="source", style="pet_head_paste", style_candidates=["pet_head_paste"],
        quality="draft", seed=1, shots=[s.to_json() for s in shots], performers=[], identities=idents,
        cast=cast, prompts={}, negative_prompt="",
    )


def _white_clip(path):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "color=c=white:size=360x640:rate=24",
                    "-t", "2", "-pix_fmt", "yuv420p", str(path)], check=True)
    return path


@needs_ffmpeg
async def test_render_paste_full_resolution_with_fakes(tmp_path, monkeypatch):
    clip = _white_clip(tmp_path / "clip.mp4")
    body = tmp_path / "body.png"
    Image.new("L", (360, 640), 255).save(body)
    subj = Subject(1, "person", 0.9, (100, 100, 260, 600), str(body))
    shots = [Shot(0, 0.0, 1.0, [subj], None, {"P1": 1}), Shot(1, 1.0, 2.0, [], None, {})]
    dog = tmp_path / "dog.png"
    Image.new("RGB", (80, 100), (139, 69, 19)).save(dog)
    plan = _plan(shots, {"P1": "A"}, {"A": str(dog)})
    calls = {"track": 0}

    async def fake_cutout(client, photo, *, profile):
        return Image.open(photo).convert("RGBA")

    async def fake_head_mask(client, frame_path, subject, out_dir, *, profile, neck=0.15):
        out_dir.mkdir(parents=True, exist_ok=True)
        with Image.open(frame_path) as f:
            m = Image.new("L", f.size, 0)
        ImageDraw.Draw(m).ellipse([120, 60, 180, 140], fill=255)
        dest = out_dir / "head.png"
        m.save(dest)
        return dest

    async def fake_track(client, video, first_mask, out_dir, *, profile, cancelled=None):
        calls["track"] += 1
        n = ingest.probe(video)["frame_count"]
        with Image.open(first_mask) as m:
            base = np.asarray(m.convert("L")) > 127
        return [np.roll(base, i, axis=1) for i in range(n)]  # head drifts right

    monkeypatch.setattr(render_mod, "head_cutout", fake_cutout)
    monkeypatch.setattr(paste_mod, "head_mask_within", fake_head_mask)
    monkeypatch.setattr(paste_mod, "track_masks", fake_track)

    out = await render_plan(object(), plan, get_style("pet_head_paste"), clip, tmp_path / "work", profile="mps")
    info = ingest.probe(out)
    assert (info["width"], info["height"]) == (360, 640)  # the clip's own resolution
    assert info["fps"] == pytest.approx(24, abs=0.1)
    assert info["duration"] == pytest.approx(2.0, abs=0.15)
    assert calls["track"] == 1  # shot 2 has no cast performer: passed through
    first = np.asarray(ingest.extract_frame(out, 0.1)).astype(int)
    brown = (abs(first[..., 0] - 139) < 30) & (abs(first[..., 1] - 69) < 30) & (abs(first[..., 2] - 19) < 30)
    ys, xs = np.nonzero(brown)
    assert len(xs) > 500 and ys.mean() < 200  # pasted where the head is (top of the frame)
    last = np.asarray(ingest.extract_frame(out, 1.6)).astype(int)
    assert ((abs(last[..., 0] - 139) < 30) & (abs(last[..., 1] - 69) < 30)).sum() < 50  # untouched shot
