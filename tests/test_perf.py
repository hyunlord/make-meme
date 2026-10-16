"""Tests for make_meme.perf: PerfRecorder and estimate_seconds."""

from __future__ import annotations

import asyncio
import json

import pytest

from make_meme import perf
from make_meme.config import get_settings


async def _noop_poll_loop(self):  # patches PerfRecorder._poll_loop so tests control
    # sampling deterministically instead of racing the real background task.
    await asyncio.Event().wait()


# --------------------------------------------------------------------------
# PerfRecorder
# --------------------------------------------------------------------------


async def test_perf_recorder_tracks_peak_bytes_and_writes_jsonl(monkeypatch):
    monkeypatch.setattr(perf.PerfRecorder, "_poll_loop", _noop_poll_loop)

    responses = [
        {"driver_allocated_bytes": 100, "system_total_bytes": 1000, "system_available_bytes": 900},
        {"driver_allocated_bytes": 300, "system_total_bytes": 1000, "system_available_bytes": 500},
        {"driver_allocated_bytes": 200, "system_total_bytes": 1000, "system_available_bytes": 700},
    ]

    class FakeClient:
        def __init__(self):
            self._responses = list(responses)

        async def stats(self):
            return self._responses.pop(0) if self._responses else None

    meta = {
        "profile": "mps", "recipe": "mocha_swap",
        "width": 512, "height": 288, "frames": 81, "steps": 4, "refs": 1,
    }
    async with perf.PerfRecorder(FakeClient(), "test-job", meta) as recorder:
        await recorder._sample()
        await recorder._sample()
        await recorder._sample()

    summary = recorder.summary()
    assert summary["peak_bytes"] == 300
    assert summary["peak_system_used_bytes"] == 500
    assert summary["ok"] is True
    assert summary["profile"] == "mps"
    assert summary["recipe"] == "mocha_swap"
    assert summary["seconds"] >= 0

    perf_path = get_settings().home / "perf.jsonl"
    lines = perf_path.read_text().splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0]) == summary


async def test_perf_recorder_marks_ok_false_and_still_writes_on_exception(monkeypatch):
    monkeypatch.setattr(perf.PerfRecorder, "_poll_loop", _noop_poll_loop)

    class FakeClient:
        async def stats(self):
            return None

    recorder = perf.PerfRecorder(FakeClient(), "job", {"profile": "mps", "recipe": "mocha_swap"})
    with pytest.raises(RuntimeError, match="boom"):
        async with recorder:
            raise RuntimeError("boom")

    assert recorder.summary()["ok"] is False
    perf_path = get_settings().home / "perf.jsonl"
    assert len(perf_path.read_text().splitlines()) == 1


async def test_perf_recorder_polls_automatically_in_the_background(monkeypatch):
    monkeypatch.setattr(perf.PerfRecorder, "POLL_INTERVAL_SEC", 0.01)
    calls = {"n": 0}

    class FakeClient:
        async def stats(self):
            calls["n"] += 1
            return {"driver_allocated_bytes": calls["n"] * 10}

    async with perf.PerfRecorder(FakeClient(), "job", {"profile": "mps", "recipe": "mocha_swap"}):
        await asyncio.sleep(0.05)

    assert calls["n"] >= 2


async def test_perf_recorder_missing_stats_fields_stay_null(monkeypatch):
    monkeypatch.setattr(perf.PerfRecorder, "_poll_loop", _noop_poll_loop)

    class FakeClient:
        async def stats(self):
            return None  # e.g. companion node pack not installed

    async with perf.PerfRecorder(FakeClient(), "job", {"profile": "cpu", "recipe": "mocha_swap"}) as recorder:
        await recorder._sample()

    summary = recorder.summary()
    assert summary["peak_bytes"] is None
    assert summary["peak_system_used_bytes"] is None


# --------------------------------------------------------------------------
# estimate_seconds
# --------------------------------------------------------------------------


def test_tokens_for_matches_formula():
    assert perf._tokens_for(512, 288, 81) == (81 // 4 * 2 + 3) * (512 // 16) * (288 // 16)


def test_estimate_seconds_uses_mps_default_anchors_when_no_samples():
    result = perf.estimate_seconds("mps", "mocha_swap", width=512, height=288, frames=81, steps=4)
    assert result["basis"] == "default"
    assert result["samples"] == 0
    assert result["seconds"] > 0


def test_estimate_seconds_cuda_lowvram_is_default_guess():
    result = perf.estimate_seconds("cuda_lowvram", "mocha_swap", width=512, height=288, frames=81, steps=4)
    assert result["basis"] == "default-guess"
    assert result["seconds"] > 0


def test_estimate_seconds_cuda_flat_guess():
    result = perf.estimate_seconds("cuda", "mocha_swap", width=512, height=288, frames=81, steps=4)
    assert result["basis"] == "default-guess"
    assert result["seconds"] == pytest.approx(15.0 * 4)


def test_estimate_seconds_unknown_profile_recipe_falls_back_without_crashing():
    result = perf.estimate_seconds("cpu", "some_unknown_recipe", width=256, height=256, frames=17, steps=2)
    assert result["basis"] == "default-guess"
    assert result["seconds"] > 0


def test_estimate_seconds_uses_measured_samples_when_available():
    settings = get_settings()
    settings.home.mkdir(parents=True, exist_ok=True)
    rows = [
        {"profile": "mps", "recipe": "mocha_swap", "width": 512, "height": 288, "frames": 81,
         "steps": 4, "seconds": 200.0, "ok": True},
        {"profile": "mps", "recipe": "mocha_swap", "width": 832, "height": 480, "frames": 81,
         "steps": 4, "seconds": 1440.0, "ok": True},
    ]
    (settings.home / "perf.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")

    result = perf.estimate_seconds("mps", "mocha_swap", width=512, height=288, frames=81, steps=4)
    assert result["basis"] == "measured"
    assert result["samples"] == 2
    assert result["seconds"] > 0


def test_estimate_seconds_ignores_failed_runs():
    settings = get_settings()
    settings.home.mkdir(parents=True, exist_ok=True)
    row = {"profile": "mps", "recipe": "mocha_swap", "width": 512, "height": 288, "frames": 81,
           "steps": 4, "seconds": 200.0, "ok": False}
    (settings.home / "perf.jsonl").write_text(json.dumps(row) + "\n")

    result = perf.estimate_seconds("mps", "mocha_swap", width=512, height=288, frames=81, steps=4)
    assert result["basis"] == "default"  # the only row is ok=False -> ignored -> falls back


def test_estimate_seconds_single_sample_scales_by_tokens_ratio():
    settings = get_settings()
    settings.home.mkdir(parents=True, exist_ok=True)
    row = {"profile": "mps", "recipe": "mocha_swap", "width": 512, "height": 288, "frames": 81,
           "steps": 4, "seconds": 200.0, "ok": True}
    (settings.home / "perf.jsonl").write_text(json.dumps(row) + "\n")

    same = perf.estimate_seconds("mps", "mocha_swap", width=512, height=288, frames=81, steps=4)
    assert same["basis"] == "measured" and same["samples"] == 1
    assert same["seconds"] == pytest.approx(200.0, rel=0.05)

    bigger = perf.estimate_seconds("mps", "mocha_swap", width=832, height=480, frames=81, steps=4)
    assert bigger["seconds"] > same["seconds"]


# --------------------------------------------------------------------------
# precache_prompts
# --------------------------------------------------------------------------


async def test_precache_prompts_dedupes_pairs_and_frees_client(monkeypatch):
    calls: list[tuple[str, str]] = []

    async def fake_run_recipe(client, recipe, *, media, values, profile, **kwargs):
        calls.append((values["prompt"], values["negative_prompt"]))

    class FakeRecipe:
        pass

    monkeypatch.setattr(perf, "run_recipe", fake_run_recipe)
    monkeypatch.setattr(perf, "get_recipe", lambda name: FakeRecipe())

    freed: list[dict] = []

    class FakeClient:
        async def free(self, **kwargs):
            freed.append(kwargs)

    pairs = [("a shiba inu", "blurry"), ("a shiba inu", "blurry"), ("a cat", "blurry")]
    await perf.precache_prompts(FakeClient(), pairs, profile="mps")

    assert calls == [("a shiba inu", "blurry"), ("a cat", "blurry")]
    assert len(freed) == 1
