"""The `animate` engine around the model: masks, character design inputs, shot caching."""

from __future__ import annotations

import shutil
import subprocess

import numpy as np
import pytest
from PIL import Image

from make_meme import ingest
from make_meme.pipelines import render as render_mod
from make_meme.pipelines.animate import head_and_neck, resize_mask
from make_meme.pipelines.design import design_photo, performer_crop
from make_meme.pipelines.detect import Subject
from make_meme.pipelines.shots import Shot
from make_meme.plan import IdentityRef, MemePlan, load_plan, new_plan_id, save_plan
from make_meme.styles import StyleError, get_style, load_style


def test_head_and_neck_adds_a_strip_inside_the_body():
    head = np.zeros((100, 80), bool)
    head[10:40, 25:55] = True
    body = np.zeros_like(head)
    body[30:100, 15:65] = True
    m = head_and_neck(head, body)
    assert m[10:40, 25:55].all()  # the head is kept
    assert m[45, 40]  # a neck below it
    assert not m[45, 26]  # narrower than the head
    assert not m[70, 40]  # not the whole torso
    assert not head_and_neck(head, np.zeros_like(body))[45, 40]  # never outside the body


def test_resize_mask_keeps_shape():
    m = np.zeros((10, 20), bool)
    m[2:8, 5:15] = True
    r = resize_mask(m, 40, 20)
    assert r.shape == (20, 40) and r[10, 20] and not r[0, 0]


def _ident(tmp_path, with_head=True):
    full = tmp_path / "full.png"
    Image.new("RGB", (40, 60), (90, 90, 100)).save(full)
    head = tmp_path / "head.png"
    Image.new("RGB", (30, 30), (90, 90, 100)).save(head)
    return IdentityRef(id="A", label="animal", description="an Italian greyhound", coat="blue-grey", photos=3,
                       confidence=0.9, ref_full=str(full), ref_head=str(head) if with_head else None)


def test_design_starts_from_the_photo_the_style_needs(tmp_path):
    ident = _ident(tmp_path)
    assert design_photo(get_style("pet_head_animate"), ident).endswith("head.png")
    assert design_photo(get_style("pet_idol_outfit"), ident).endswith("full.png")
    assert design_photo(get_style("pet_head_animate"), _ident(tmp_path, with_head=False)).endswith("full.png")
    prompt = get_style("pet_idol_outfit").render_design_prompt(subject_desc="an Italian greyhound")
    assert "(an Italian greyhound)" in prompt and "image 2" in prompt


def test_performer_crop(tmp_path):
    frame = tmp_path / "f.png"
    Image.new("RGB", (200, 300), "white").save(frame)
    out = performer_crop(frame, Subject(1, "person", 0.9, (50, 40, 150, 280), None), tmp_path / "c.png")
    with Image.open(out) as im:
        assert im.size == (116, 278)  # box + 8 % padding, clamped to the frame


def test_animate_styles_need_a_design_prompt(tmp_path):
    bad = tmp_path / "style.yaml"
    bad.write_text("name: x\nengine: animate\nrecipe: wan_animate_replace\nprompt: p\n")
    with pytest.raises(StyleError):
        load_style(bad)


def _clip(path):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "color=c=white:size=144x256:rate=24",
                    "-t", "2", "-pix_fmt", "yuv420p", str(path)], check=True)
    return path


def _plan(shots, cast, ident):
    return MemePlan(
        id=new_plan_id(), intent="t", source_asset="vid_x", source_title=None, segment={"start": 0, "end": 2},
        clip_asset="vid_y", aspect="source", style="pet_idol_fur", style_candidates=["pet_idol_fur"],
        quality="draft", seed=1, shots=[s.to_json() for s in shots], performers=[], identities=[ident],
        cast=cast, prompts={"P1": "a dog dancing"}, negative_prompt="clothes",
    )


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg required")
async def test_render_animate_designs_once_caches_shots_and_keeps_timing(tmp_path, monkeypatch):
    monkeypatch.setenv("MAKE_MEME_HOME", str(tmp_path / "home"))
    from make_meme.config import reset_settings_cache

    reset_settings_cache()
    clip = _clip(tmp_path / "clip.mp4")
    subj = Subject(1, "person", 0.9, (20, 20, 120, 240), None)
    shots = [Shot(0, 0.0, 1.0, [subj], None, {"P1": 1}), Shot(1, 1.0, 2.0, [], None, {})]
    plan = _plan(shots, {"P1": "A"}, _ident(tmp_path))
    save_plan(plan)
    calls = {"design": 0, "animate": 0}

    async def fake_design(client, style, ident, out_dir, *, profile, seed, outfit=None, extra=""):
        calls["design"] += 1
        out_dir.mkdir(parents=True, exist_ok=True)
        dest = out_dir / "char.png"
        Image.new("RGB", (64, 112), "brown").save(dest)
        return dest

    async def fake_animate(client, recipe, piece, performers, refs, prompts, work, *, gen_size, mask_mode, **kw):
        calls["animate"] += 1
        assert mask_mode == "full_body" and set(performers) == {"P1"} and refs["P1"].name == "char.png"
        out = work / "out.mp4"
        shutil.copyfile(piece, out)
        return out, []

    monkeypatch.setattr("make_meme.pipelines.design.design_character", fake_design)
    monkeypatch.setattr("make_meme.pipelines.animate.animate_shot", fake_animate)
    style = get_style("pet_idol_fur")
    out = await render_mod.render_plan(object(), plan, style, clip, tmp_path / "work", profile="mps")
    assert calls == {"design": 1, "animate": 1}
    info = ingest.probe(out)
    assert (info["width"], info["height"]) == (144, 256) and info["frame_count"] == 48  # clip size and timing
    assert plan.identity("A").characters["pet_idol_fur"].endswith("char.png")

    await render_mod.render_plan(object(), plan, style, clip, tmp_path / "work", profile="mps")
    assert calls == {"design": 1, "animate": 1}  # character and finished shot reused

    from make_meme.tools_plan import _save_characters

    _save_characters(plan)
    assert load_plan(plan.id).identity("A").characters["pet_idol_fur"].endswith("char.png")
    reset_settings_cache()
