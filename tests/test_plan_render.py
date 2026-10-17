"""Styles, shots, casting, plan persistence and a multi-shot render against a fake ComfyUI."""

from __future__ import annotations

import itertools
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from make_meme import ingest
from make_meme.pipelines import render as render_mod
from make_meme.pipelines import swap as swap_mod
from make_meme.pipelines.assign import color_hist
from make_meme.pipelines.detect import Subject
from make_meme.pipelines.render import cast_identities, render_plan
from make_meme.pipelines.shots import Shot, match_performers, split_shots
from make_meme.plan import IdentityRef, MemePlan, load_plan, new_plan_id, save_plan
from make_meme.styles import all_styles, get_style, guess_style


def test_builtin_styles_and_prompts():
    styles = all_styles()
    assert {"pet_head_swap", "pet_full_body", "person_swap"} <= set(styles)
    full = get_style("pet_full_body")
    p = full.render_prompt(subject_desc="a dog with a short glossy black coat", coat="black", scene="")
    assert p.startswith("A dog with a short glossy black coat dancing")
    assert "black fur" in p and "{" not in p
    assert "clothes" in full.negative
    head = get_style("pet_head_swap")
    assert head.mask == "head" and head.refs["ref1"] == "head"
    assert "outfit" not in head.render_prompt(subject_desc="a grey dog")


def test_guess_style_from_intent():
    assert guess_style("머리만 강아지로 바꿔줘", "animal")[0] == "pet_head_swap"
    assert guess_style("온몸을 강아지로", "animal")[0] == "pet_full_body"
    name, candidates = guess_style("두 멤버를 우리 강아지로", "animal")
    assert name is None and set(candidates) == {"pet_head_swap", "pet_full_body", "pet_head_paste"}
    assert guess_style("우리 강아지 얼굴 오려서 붙여줘", "animal")[0] is None  # 얼굴 (head swap) + 붙여 (paste)
    assert guess_style("강아지 사진 붙여서 짤 만들어줘", "animal")[0] == "pet_head_paste"
    assert guess_style("replace the singer with my friend", "person")[0] == "person_swap"


def test_split_shots_merges_tiny_shots():
    spans = split_shots([4.88, 5.17, 5.84, 6.38, 6.42, 6.97, 13.47], 18.0)
    assert spans[0] == (0.0, 5.17)  # the 0.29 s shot after the first cut is merged into it
    assert all(b - a >= 0.4 for a, b in spans)
    assert spans[-1][1] == 18.0
    assert (6.97, 13.47) in spans


def _h(rgb):
    return color_hist(Image.new("RGB", (32, 32), rgb))


def test_match_performers_across_shots():
    ref = [("P1", _h((140, 110, 90))), ("P2", _h((15, 15, 15)))]  # P1 brown hair, P2 black hair
    cand = [(1, _h((14, 14, 16))), (2, _h((138, 112, 92)))]  # order swapped in the new shot
    assert match_performers(ref, cand) == {"P2": 1, "P1": 2}
    # a stranger who looks like nobody is not matched
    assert match_performers(ref, [(1, _h((10, 200, 10)))]) == {}


def test_cast_identities_prefers_appearance():
    perf = {"P1": _h((140, 110, 90)), "P2": _h((15, 15, 15))}
    idents = {"A": _h((12, 12, 12)), "B": _h((130, 120, 115))}  # A black lab, B grey-brown greyhound
    cast, why = cast_identities(perf, idents)
    assert cast == {"P2": "A", "P1": "B"} and "appearance" in why
    cast2, _ = cast_identities({"P1": perf["P1"]}, idents)
    assert len(cast2) == 1


def _plan(tmp: Path, shots: list[Shot], cast: dict[str, str], refs: dict[str, str]) -> MemePlan:
    idents = [IdentityRef(id=i, label="animal", description=f"dog {i}", coat="black", photos=1, confidence=0.9,
                          ref_full=path, ref_head=path) for i, path in refs.items()]
    return MemePlan(
        id=new_plan_id(), intent="t", source_asset="vid_x", source_title=None, segment={"start": 0, "end": 3},
        clip_asset="vid_y", aspect="source", style="pet_full_body", style_candidates=["pet_full_body"],
        quality="draft", seed=1, shots=[s.to_json() for s in shots], performers=[], identities=idents,
        cast=cast, prompts={p: f"prompt {p}" for p in cast}, negative_prompt="clothes",
    )


def test_plan_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("MAKE_MEME_HOME", str(tmp_path))
    from make_meme.config import reset_settings_cache

    reset_settings_cache()
    plan = _plan(tmp_path, [Shot(0, 0, 1)], {"P1": "A"}, {"A": "/x.png"})
    save_plan(plan)
    again = load_plan(plan.id)
    assert again is not None and again.identity("A").ref_for("head") == "/x.png"
    assert again.cast == {"P1": "A"}
    reset_settings_cache()


def _make_clip(path: Path) -> Path:
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "testsrc=size=640x360:rate=24",
                    "-t", "3", "-pix_fmt", "yuv420p", str(path)], check=True)
    return path


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg required")
async def test_render_plan_multi_shot(tmp_path, monkeypatch):
    clip = _make_clip(tmp_path / "clip.mp4")
    mask = tmp_path / "m.png"
    Image.new("L", (640, 360), 255).save(mask)
    ref = tmp_path / "ref.png"
    Image.new("RGB", (64, 64), (0, 0, 0)).save(ref)
    s1 = Subject(1, "person", 0.9, (10, 10, 200, 300), str(mask))
    s2 = Subject(2, "person", 0.9, (300, 10, 500, 300), str(mask))
    shots = [Shot(0, 0.0, 1.0, [s1, s2], None, {"P1": 1, "P2": 2}),
             Shot(1, 1.0, 1.6, [], None, {}),  # no people: passthrough
             Shot(2, 1.6, 3.0, [s1], None, {"P2": 1})]
    plan = _plan(tmp_path, shots, {"P1": "A", "P2": "B"}, {"A": str(ref), "B": str(ref)})
    calls: list[tuple[int, list[str], list[str]]] = []

    async def fake_run_swap(client, swap_plan, *, report=None, cancelled=None):
        calls.append((len(swap_plan.mappings), [m.mask_mode for m in swap_plan.mappings],
                      [m.prompt for m in swap_plan.mappings]))
        if report:
            await report("generating", 1.0, "done")
        w, h = swap_mod.preset_size(swap_plan.recipe, swap_plan.quality, swap_plan.source_size, swap_plan.profile)
        out = swap_plan.work_dir / "out.mp4"
        swap_plan.work_dir.mkdir(parents=True, exist_ok=True)
        ingest._run(["ffmpeg", "-y", "-i", str(swap_plan.video_path), "-vf", f"scale={w}:{h},fps=16", "-an",
                     "-pix_fmt", "yuv420p", str(out)])
        return out

    monkeypatch.setattr(render_mod, "run_swap", fake_run_swap)
    progress: list[float] = []

    async def rep(stage, p, m):
        progress.append(p)

    out = await render_plan(None, plan, get_style("pet_head_swap"), clip, tmp_path / "work", profile="mps",
                            report=rep)
    info = ingest.probe(out)
    assert (info["width"], info["height"]) == (512, 288)
    assert info["duration"] == pytest.approx(3.0, abs=0.2)
    assert [c[0] for c in calls] == [2, 1]  # shot 0: both performers, shot 2: only P2, shot 1: passthrough
    assert all(m == "head" for c in calls for m in c[1])
    assert calls[1][2] == ["prompt P2"]
    assert progress and max(progress) == pytest.approx(1.0)
    assert np.isfinite(info["fps"])


def test_render_time_estimate_uses_current_measurements(monkeypatch):
    # The plan's estimate was made before any perf samples existed; render_meme must refresh it.
    from make_meme import perf
    from make_meme.tools_plan import _refresh_estimate

    calls = []

    def fake_estimate(profile, recipe, w, h, frames, steps):
        calls.append(frames)
        return {"seconds": 100.0, "basis": "measured", "samples": 26}

    monkeypatch.setattr(perf, "estimate_seconds", fake_estimate)
    plan = _plan(Path("/tmp"), [Shot(0, 0.0, 6.0, performers={"P1": 1})], {"P1": "A"}, {"A": "/x.png"})
    plan.estimate = {"seconds": 1, "minutes": 0.0, "basis": "default", "profile": "mps", "output_size": [288, 512],
                     "quality": "draft"}
    _refresh_estimate(plan, get_style("pet_full_body"))
    assert plan.estimate["basis"] == "measured" and plan.estimate["output_size"] == [288, 512]
    assert calls and max(calls) <= 49  # 96 frames split into Mac-sized chunks
    assert plan.estimate["seconds"] == 100 * len(calls)


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg required")
def test_cut_segment_shots_tile_the_clip_exactly(tmp_path):
    clip = tmp_path / "clip.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "testsrc=size=160x90:rate=24000/1001",
                    "-frames:v", "120", "-pix_fmt", "yuv420p", str(clip)], check=True)
    fps = 24000 / 1001
    bounds = [0.0, 0.834, 3.17, 3.837, 4.421, 5.005]  # NEON shot boundaries (frame times, rounded to ms)
    pieces = [render_mod.cut_segment(clip, a, b, tmp_path / f"s{i}.mp4")
              for i, (a, b) in enumerate(itertools.pairwise(bounds))]
    counts = [ingest.probe(p)["frame_count"] for p in pieces]
    assert counts == [round(b * fps) - round(a * fps) for a, b in itertools.pairwise(bounds)]
    assert sum(counts) == round(bounds[-1] * fps)
    assert ingest.probe(pieces[0])["fps"] == pytest.approx(fps, abs=0.01)
