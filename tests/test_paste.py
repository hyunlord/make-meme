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
from make_meme.pipelines.paste import HeadPose, assign_heads, head_pose, paste_head, smooth_poses
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
    # sqrt(w*h) of the 40x60 cut-out becomes 1.5 x 60 = 90 px: 73 x 110 before rotation
    assert 70 < xs.max() - xs.min() < 125
    red = (a[..., 0] > 200) & (a[..., 1] < 60) & (a[..., 2] < 60)
    ry, rx = np.nonzero(red)
    assert rx.mean() > 155 and ry.mean() < 130  # tilted clockwise: the top moved right


def _labels(n, heads):
    """n frames of 200x300 label maps; heads: {label: [(frame, cx, cy)]}."""
    frames = [np.zeros((300, 200), np.uint8) for _ in range(n)]
    for k, spots in heads.items():
        for f, cx, cy in spots:
            frames[f][cy - 8:cy + 8, cx - 7:cx + 7] = k
    return frames


def test_assign_heads_claims_relinks_and_ignores_strangers():
    bodies = {"P1": (20, 40, 80, 290), "P2": (120, 40, 180, 290)}
    heads = {
        1: [(f, 50, 60) for f in range(5)],             # P1's head, then lost
        2: [(f, 150 - f, 60) for f in range(10)],       # P2's head, drifting left
        3: [(f, 100, 200) for f in range(10)],          # someone else's head, mid-frame low
        4: [(f, 53, 62) for f in range(7, 10)],         # P1's head re-detected as a new object
    }
    out = assign_heads(_labels(10, heads), bodies)
    p1 = [m is not None for m in out["P1"]]
    assert p1 == [True] * 5 + [False, False] + [True] * 3
    assert all(m is not None for m in out["P2"])
    assert not out["P2"][9][200, 100] and not out["P1"][9][200, 100]  # the stranger is never pasted over


def test_assign_heads_needs_a_head_inside_the_body_at_first():
    out = assign_heads(_labels(3, {1: [(f, 190, 20) for f in range(3)]}), {"P1": (20, 40, 80, 290)})
    assert all(m is None for m in out["P1"])


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

    async def fake_track(client, video, out_dir, *, profile, cancelled=None, **_kw):
        calls["track"] += 1
        info = ingest.probe(video)
        m = Image.new("L", (int(info["width"]), int(info["height"])), 0)
        ImageDraw.Draw(m).ellipse([120, 60, 180, 140], fill=1)  # label 1 = a head on top of the body
        base = np.asarray(m)
        return [np.roll(base, i, axis=1) for i in range(info["frame_count"])]  # head drifts right

    monkeypatch.setattr(render_mod, "head_cutout", fake_cutout)
    monkeypatch.setattr(paste_mod, "track_labels", fake_track)

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


def test_expand_poses_interpolates_skipped_frames():
    from make_meme.pipelines.paste import expand_poses

    a, b = HeadPose(0, 0, 10, 0), HeadPose(10, 20, 30, 10)
    out = expand_poses([a, b, None], 6, 2)
    assert out[0] == a and out[2] == b
    assert out[1] == HeadPose(5, 10, 20, 5)  # halfway
    assert out[3] == b  # next tracked frame is missing: hold the nearer known pose
    assert out[4] is None and out[5] is None


@needs_ffmpeg
def test_downscale_with_stride_keeps_every_other_frame(tmp_path):
    from make_meme.pipelines.track import downscale

    clip = _white_clip(tmp_path / "c.mp4")  # 360x640, 48 frames
    small, factor = downscale(clip, tmp_path / "s.mp4", width=180, stride=2)
    info = ingest.probe(small)
    assert (info["width"], info["height"]) == (180, 320) and factor == 2.0
    assert info["frame_count"] == 24


def test_assign_bodies_and_inputs(tmp_path):
    from make_meme.pipelines.animate import assign_bodies, build_inputs, fill_masks, padded_length

    labels = []
    for f in range(6):
        lab = np.zeros((100, 120), np.uint8)
        lab[20:90, 10:40] = 1  # P1
        if f < 3:
            lab[20:90, 70:100] = 2  # P2 ...
        elif f > 3:
            lab[22:92, 72:102] = 5  # ... re-detected under a new number after a gap
        lab[5:15, 50:60] = 3 if f == 0 else 0  # tiny: ignored
        labels.append(lab)
    out = assign_bodies(labels, {"P1": (10, 20, 40, 90), "P2": (70, 20, 100, 90)})
    assert all(m is not None for m in out["P1"])
    assert [m is not None for m in out["P2"]] == [True, True, True, False, True, True]
    filled = fill_masks(out["P2"])
    assert filled[3] is not None
    assert padded_length(6) == 9 and padded_length(9) == 9 and padded_length(1) == 1
    frames = [np.full((100, 120, 3), 200, np.uint8) for _ in range(6)]
    media = build_inputs(frames, filled, tmp_path, 16)
    assert ingest.probe(media["bg_video"])["frame_count"] == 9
    bg = np.asarray(ingest.extract_frame(media["bg_video"], 0.0))
    assert bg[50, 85].max() < 30 and bg[50, 10].min() > 170  # performer (blockified) blanked, rest kept
