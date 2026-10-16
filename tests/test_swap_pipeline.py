"""End-to-end swap pipeline against a fake ComfyUI (no GPU): checks normalization,
chunking, upload/patch plumbing, frame download/encode and stitching."""

from __future__ import annotations

import asyncio
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from make_meme import ingest
from make_meme.comfy.client import ExecutionResult, OutputFile
from make_meme.pipelines import swap as swap_mod
from make_meme.pipelines.detect import Subject, dedupe, iou, parse_query
from make_meme.pipelines.swap import SwapMapping, SwapPlan, _scale_bbox, preset_size, run_swap
from make_meme.recipes.loader import get_recipe

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg required")


def _make_video(path: Path, seconds: float, size: str = "640x360", fps: int = 30) -> Path:
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"testsrc=size={size}:rate={fps}",
         "-t", str(seconds), "-pix_fmt", "yuv420p", str(path)],
        check=True,
    )
    return path


class FakeComfy:
    """Implements the subset of ComfyClient used by run_swap; 'generates' by echoing the
    input chunk's frames (inverted, so we can tell they went through the fake)."""

    def __init__(self, tmp: Path) -> None:
        self.tmp = tmp
        self.uploads: dict[str, Path] = {}
        self.workflows: list[dict] = []
        self.base_url = "fake://"

    async def upload(self, path: Path) -> str:
        name = f"up_{len(self.uploads)}{path.suffix}"
        self.uploads[name] = path
        return name

    async def run(self, workflow, *, on_progress=None, cancelled=None, stage="generating", **_kw):
        self.workflows.append(workflow)
        video = self.uploads[workflow["1"]["inputs"]["file"]]
        out_dir = self.tmp / f"gen{len(self.workflows)}"
        out_dir.mkdir()
        await asyncio.to_thread(subprocess.run, ["ffmpeg", "-y", "-loglevel", "error", "-i", str(video),
                                "-vf", "negate", str(out_dir / "f_%05d_.png")], check=True)
        if on_progress:
            await on_progress(stage, 1.0, "step 4/4")
        files = sorted(out_dir.glob("*.png"))
        return ExecutionResult(
            prompt_id="p", outputs=[OutputFile(f.name, str(out_dir), "output", "17", "images") for f in files]
        )

    async def download(self, out: OutputFile, dest: Path) -> Path:
        shutil.copyfile(Path(out.subfolder) / out.filename, dest)
        return dest


async def _noop_ready(*a, **k):
    return None


@pytest.mark.parametrize("seconds,expected_chunks", [(2.0, 1), (7.0, 2)])
async def test_run_swap_with_fake_comfy(tmp_path, monkeypatch, seconds, expected_chunks):
    monkeypatch.setattr(swap_mod, "ensure_ready", _noop_ready)

    async def fake_relocate(client, chunk_video, label, prev_bbox, chunk_dir, profile, w, h, **_kw):
        return Image.new("L", (w, h), 255), prev_bbox

    monkeypatch.setattr(swap_mod, "_relocate", fake_relocate)
    src = _make_video(tmp_path / "src.mp4", seconds)
    mask = tmp_path / "mask.png"
    Image.new("L", (640, 360), 0).save(mask)
    ref = tmp_path / "dog.png"
    Image.new("RGB", (300, 400), (200, 150, 90)).save(ref)

    plan = SwapPlan(
        video_path=src, source_size=(640, 360),
        mappings=[SwapMapping(Subject(1, "person", 0.9, (100, 50, 300, 350), str(mask)), [ref], "dancing")],
        recipe=get_recipe("mocha_swap"), profile="mps", quality="draft", prompt="a shiba inu",
        seed=3, clean_refs=False, auto_head_ref=False, work_dir=tmp_path / "work",
    )
    fake = FakeComfy(tmp_path)
    progress: list[float] = []
    out = await run_swap(fake, plan, report=lambda s, p, m: progress.append(p))

    info = ingest.probe(out)
    assert (info["width"], info["height"]) == (512, 288)  # mps draft preset
    assert info["fps"] == pytest.approx(16, abs=0.01)
    assert abs(info["frame_count"] - round(seconds * 16)) <= 1
    assert len(fake.workflows) == expected_chunks
    wf = fake.workflows[0]
    assert wf["13"]["inputs"]["positive_prompt"] == "a shiba inu dancing"
    assert wf["15"]["inputs"]["seed"] == 3 and wf["15"]["inputs"]["steps"] == 4
    assert "ref2" not in wf["14"]["inputs"]
    frames = ingest.probe(fake.uploads[wf["1"]["inputs"]["file"]])["frame_count"]
    assert (frames - 1) % 4 == 0  # every chunk sent to the model is 4n+1 frames
    assert progress and progress[-1] == pytest.approx(1.0)


def test_portrait_sources_flip_preset():
    r = get_recipe("mocha_swap")
    assert preset_size(r, "draft", (1080, 1920), "cuda") == (480, 832)
    assert preset_size(r, "draft", (1920, 1080), "mps") == (512, 288)


def test_scale_bbox_matches_cover_crop():
    # 1920x1080 -> 832x480: scale 0.4444 (height-bound), x offset (853.3-832)/2
    _x1, y1, x2, y2 = _scale_bbox((960, 540, 1920, 1080), (1920, 1080), (832, 480))
    assert (y1, y2) == (240, 480)
    assert x2 == pytest.approx(843, abs=1)


def test_detect_helpers():
    assert parse_query("person, dog:3,, cat") == ["person:5", "dog:3", "cat:5"]
    a = Subject(0, "dog", 0.9, (0, 0, 100, 100), "")
    b = Subject(0, "animal", 0.6, (5, 5, 100, 100), "")
    c = Subject(0, "person", 0.8, (200, 0, 300, 100), "")
    assert iou(a.bbox, b.bbox) > 0.8
    assert [s.label for s in dedupe([b, a, c])] == ["dog", "person"]


def test_dedupe_drops_cross_label_parts_but_keeps_overlapping_people():
    p1 = Subject(0, "person", 0.97, (233, 422, 466, 831), "")
    p2 = Subject(0, "person", 0.94, (106, 428, 307, 830), "")
    hair = Subject(0, "animal", 0.6, (116, 428, 251, 604), "")  # inside p2
    torso = Subject(0, "animal", 0.55, (265, 495, 407, 650), "")  # inside p1
    front = Subject(0, "person", 0.9, (300, 500, 420, 800), "")  # a person in front of p1
    labels = [(s.label, s.bbox) for s in dedupe([hair, p1, torso, p2, front])]
    assert ("animal", hair.bbox) not in labels and ("animal", torso.bbox) not in labels
    assert ("person", front.bbox) in labels and len(labels) == 3


async def test_detect_treats_empty_sam3_failure_as_no_subjects(tmp_path, monkeypatch):
    from make_meme.comfy.client import ComfyError
    from make_meme.pipelines import detect as detect_mod

    async def noop(*a, **k):
        return None

    async def failing_run_recipe(*a, **k):
        raise ComfyError("ComfyUI execution failed in SaveImage (node 6): index 0 is out of bounds for dimension 0 "
                         "with size 0")

    monkeypatch.setattr(detect_mod, "ensure_ready", noop)
    monkeypatch.setattr(detect_mod, "run_recipe", failing_run_recipe)
    img = tmp_path / "x.png"
    Image.new("RGB", (64, 64)).save(img)
    assert await detect_mod.detect_in_image(None, img, "person, animal", tmp_path / "d", profile="mps") == []

    async def other_error(*a, **k):
        raise ComfyError("ComfyUI execution failed in WanVideoSampler (node 15): OOM")

    monkeypatch.setattr(detect_mod, "run_recipe", other_error)
    with pytest.raises(ComfyError, match="OOM"):
        await detect_mod.detect_in_image(None, img, "person", tmp_path / "d2", profile="mps")


def _two_subject_plan(tmp_path: Path, src: Path) -> SwapPlan:
    mask = tmp_path / "mask.png"
    Image.new("L", (640, 360), 0).save(mask)
    ref = tmp_path / "dog.png"
    Image.new("RGB", (300, 400), (200, 150, 90)).save(ref)
    return SwapPlan(
        video_path=src, source_size=(640, 360),
        mappings=[SwapMapping(Subject(1, "person", 0.9, (40, 50, 200, 350), str(mask)), [ref], "left"),
                  SwapMapping(Subject(2, "person", 0.9, (420, 50, 600, 350), str(mask)), [ref], "right")],
        recipe=get_recipe("mocha_swap"), profile="mps", quality="draft", prompt=None,
        seed=3, clean_refs=False, auto_head_ref=False, work_dir=tmp_path / "work",
    )


async def test_every_subject_is_swapped_from_the_original_then_composited(tmp_path, monkeypatch):
    # Chaining passes let the second swap repaint the first (seen in the NEON test).
    monkeypatch.setattr(swap_mod, "ensure_ready", _noop_ready)
    src = _make_video(tmp_path / "src.mp4", 1.0)
    plan = _two_subject_plan(tmp_path, src)
    fake = FakeComfy(tmp_path)
    out = await run_swap(fake, plan)

    assert out.name == "swapped.mp4"
    assert len(fake.workflows) == 2
    base = np.asarray(ingest.extract_frame(plan.work_dir / "pass0.mp4", 0.0).convert("L"), np.float32)
    for wf in fake.workflows:
        sent = np.asarray(ingest.extract_frame(fake.uploads[wf["1"]["inputs"]["file"]], 0.0).convert("L"), np.float32)
        assert np.abs(sent - base).mean() < 8  # the original, not the (inverted) first pass
    assert ingest.probe(out)["frame_count"] == ingest.probe(plan.work_dir / "pass0.mp4")["frame_count"]


async def test_rerun_reuses_finished_chunks(tmp_path, monkeypatch):
    monkeypatch.setattr(swap_mod, "ensure_ready", _noop_ready)
    src = _make_video(tmp_path / "src.mp4", 1.0)
    fake = FakeComfy(tmp_path)
    await run_swap(fake, _two_subject_plan(tmp_path, src))
    assert len(fake.workflows) == 2
    messages: list[str] = []
    await run_swap(fake, _two_subject_plan(tmp_path, src), report=lambda s, p, m: messages.append(m))
    assert len(fake.workflows) == 2  # nothing regenerated
    assert any("reused" in m for m in messages)

    changed = _two_subject_plan(tmp_path, src)
    changed.mappings[1].prompt = "a different prompt"
    await run_swap(fake, changed)
    assert len(fake.workflows) == 3  # only the changed subject re-ran
