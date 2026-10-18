"""The `animate` engine around the model: masks, character design inputs, shot caching."""

from __future__ import annotations

import itertools
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
    assert design_photo(get_style("pet_idol_outfit"), ident).endswith("full.png")
    assert design_photo(get_style("pet_idol_fur"), _ident(tmp_path)).endswith("full.png")
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


def test_performer_crop_whites_out_other_people(tmp_path):
    frame = tmp_path / "f.png"
    Image.new("RGB", (200, 300), (200, 30, 30)).save(frame)  # everything "red outfit"
    mask = tmp_path / "m.png"
    m = Image.new("L", (200, 300), 0)
    m.paste(255, (60, 50, 140, 270))
    m.save(mask)
    out = performer_crop(frame, Subject(1, "person", 0.9, (50, 40, 150, 280), str(mask)), tmp_path / "c.png")
    with Image.open(out) as im:
        px = im.convert("RGB")
        assert px.getpixel((2, 2)) == (255, 255, 255)  # outside the performer: white
        assert px.getpixel((im.width // 2, im.height // 2)) == (200, 30, 30)


def test_blockify_covers_whole_cells():
    from make_meme.pipelines.animate import blockify

    m = np.zeros((70, 70), bool)
    m[33, 5] = True
    b = blockify(m, 32)
    assert b[32:64, 0:32].all() and b.sum() == 32 * 32
    assert blockify(np.zeros((10, 10), bool)).sum() == 0
    assert blockify(np.ones((70, 70), bool)).all()


def test_window_ranges_stay_out_of_the_looping_mode():
    from make_meme.pipelines.animate import OVERLAP, WINDOW, window_ranges

    assert window_ranges(73) == [(0, 73)]
    wins = window_ranges(199)
    assert all(b - a <= WINDOW for a, b in wins)
    assert wins[0][0] == 0 and wins[-1][1] == 199
    assert all(prev[1] - nxt[0] == OVERLAP for prev, nxt in itertools.pairwise(wins))


def test_assign_everyone_leaves_nobody_original():
    from make_meme.pipelines.animate import assign_everyone

    labels = []
    for _ in range(4):
        lab = np.zeros((100, 100), np.uint8)
        lab[20:90, 5:30] = 1  # P2, matched by its box
        lab[20:90, 60:90] = 2  # a second dancer nobody matched (NEON shot 9)
        lab[40:46, 32:38] = 3  # a stray fragment (an arm) next to P2
        labels.append(lab)
    out = assign_everyone(labels, {"P2": (5, 20, 30, 90)}, spare=["P1"])
    assert set(out) == {"P1", "P2"}
    assert all(m is not None and m[50, 75] for m in out["P1"])  # the unmatched dancer -> the spare cast member
    assert all(m[43, 35] for m in out["P2"])  # the fragment joined the nearest performer
    only = assign_everyone(labels, {"P2": (5, 20, 30, 90)}, spare=[])
    assert set(only) == {"P2"}  # no spare cast member: nothing to give the extra dancer
    assert not any(m[50, 75] for m in only["P2"])  # ...and they aren't merged into P2 as a "fragment"


def test_recipe_retarget_input_is_optional():
    from make_meme.recipes.loader import get_recipe

    r = get_recipe("wan_animate_replace")
    base = {"pose_video": "p.mp4", "bg_video": "b.mp4", "mask_video": "m.mp4", "ref": "r.png"}
    wf = r.build(base, profile="cuda", preset="high")
    assert "retarget_image" not in wf["10"]["inputs"] and "22" not in wf
    wf = r.build({**base, "retarget": "c.png"}, profile="cuda", preset="max")
    assert wf["10"]["inputs"]["retarget_image"] == ["22", 0] and wf["19"]["inputs"]["steps"] == 8


def test_generation_never_exceeds_the_clip_resolution():
    from make_meme.pipelines.render import cap_to_source

    assert cap_to_source((720, 1280), (608, 1080)) == (608, 1072)
    assert cap_to_source((480, 832), (608, 1080)) == (480, 832)
    assert cap_to_source((1280, 720), (1920, 1080)) == (1280, 720)


def test_composite_alpha_follows_the_silhouette_and_new_parts():
    from make_meme.pipelines.animate import composite_alpha

    h, w = 140, 100
    region = np.zeros((h, w), bool)
    region[40:100, 40:60] = True  # the performer
    blocks = np.zeros((h, w), bool)
    blocks[32:136, 32:72] = True  # the coarse region the model regenerated
    original = np.full((h, w, 3), 200, np.float32)
    generated = original.copy()
    generated[40:100, 40:60] = 30  # the dog's body
    generated[20:40, 50:56] = 30  # an ear above the silhouette, inside the blocks? (rows 32-40 only)
    a = composite_alpha(region, original, generated, blocks)[..., 0]
    assert a[70, 50] > 0.95  # body
    assert a[35, 53] > 0.5  # changed pixels inside the blocks are kept (the ear)
    assert a[130, 33] < 0.05  # unchanged block corner, beyond the grown silhouette: original kept
    assert a[10, 53] == 0  # never outside the blocks


def test_merge_fragments_gives_hair_to_the_nearest_performer():
    from make_meme.pipelines.animate import merge_fragments

    body = np.zeros((100, 100), bool)
    body[40:90, 10:30] = True
    other = np.zeros((100, 100), bool)
    other[40:90, 70:90] = True
    hair = np.zeros((100, 100), np.uint8)
    hair[30:45, 30:40] = 1  # swinging off P1's head
    out = merge_fragments({"P1": [body.copy()], "P2": [other.copy()]}, [hair])
    assert out["P1"][0][35, 35] and not out["P2"][0][35, 35]


def test_far_changes_are_not_pasted():
    from make_meme.pipelines.animate import composite_alpha

    region = np.zeros((200, 200), bool)
    region[60:140, 90:110] = True
    blocks = np.ones((200, 200), bool)
    original = np.full((200, 200, 3), 220, np.float32)
    generated = original.copy()
    generated[10:40, 10:40] = 0  # a black block the model left unpainted, far from the performer
    a = composite_alpha(region, original, generated, blocks)[..., 0]
    assert a[25, 25] == 0


def test_clean_plate_recovers_the_background_behind_moving_people():
    from make_meme.pipelines.animate import clean_plate

    frames, masks = [], []
    for x in range(0, 60, 6):
        f = np.full((40, 80, 3), 200, np.uint8)
        f[10:30, x:x + 10] = 20  # a dancer crossing
        m = np.zeros((40, 80), bool)
        m[10:30, x:x + 10] = True
        frames.append(f)
        masks.append(m)
    plate = clean_plate(frames, masks)
    assert np.abs(plate - 200).max() < 1  # the dancer is gone from the plate
