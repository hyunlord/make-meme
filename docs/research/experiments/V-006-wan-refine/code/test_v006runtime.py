# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# Run: existing Python -m pytest -q test_v006runtime.py
"""CPU fixtures for low-expert admission and no-model boundary validation."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import struct
import sys

import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from v006runtime_config import Runtime, check_contract, projected_seconds, sigma_start


def fixture_runtime(root: Path) -> Runtime:
    root.mkdir(exist_ok=True)
    tensor = root / "low.safetensors"
    header = json.dumps({"weight": {"dtype": "BF16", "shape": [1], "data_offsets": [0, 2]}}).encode()
    tensor.write_bytes(struct.pack("<Q", len(header)) + header + b"\x00\x00")
    image = Image.new("RGB", (16, 16), (10, 20, 30))
    frame = root / "000.png"
    image.save(frame)
    return Runtime(run_id="fixture", upstream=root, source_hashes={}, checkpoint_paths=(tensor,),
                   text_encoder=tensor, vae=tensor, tokenizer=root, input_paths=(frame,),
                   input_pixel_hashes=(hashlib.sha256(image.tobytes()).hexdigest(),),
                   output=root / "output", width=16, height=16, frames=1, fps=24,
                   seed=1, strength=.35, steps=50, sigma_shift=5, guidance=5,
                   boundary=.875, expected_sigma=.7291666269302368, sigma_tolerance=1e-6,
                   prompt="fixture", negative_prompt="", vram_limit_gib=24,
                   maximum_seconds=3600, tile_size=(30, 52), tile_stride=(15, 26),
                   ffmpeg=tensor)


def test_two_requested_strengths_are_distinct_and_low_only(tmp_path: Path) -> None:
    first = fixture_runtime(tmp_path)
    second = first.model_copy(update={"strength": .55, "expected_sigma": .859375})
    assert sigma_start(first) != sigma_start(second)
    assert max(sigma_start(first), sigma_start(second)) < first.boundary


def test_wan_cli_shift_cannot_silently_use_low_only(tmp_path: Path) -> None:
    runtime = fixture_runtime(tmp_path).model_copy(
        update={"strength": .55, "sigma_shift": 12, "expected_sigma": 6.6 / 7.05})
    with pytest.raises(AssertionError):
        check_contract(runtime)


def test_cpu_contract_does_not_import_torch(tmp_path: Path) -> None:
    before = "torch" in sys.modules
    assert len(check_contract(fixture_runtime(tmp_path))) == 1
    assert ("torch" in sys.modules) == before


def test_rejects_fp32_checkpoint_before_model_load(tmp_path: Path) -> None:
    runtime = fixture_runtime(tmp_path)
    path = runtime.checkpoint_paths[0]
    path.write_bytes(path.read_bytes().replace(b"BF16", b"F32 "))
    with pytest.raises(AssertionError):
        check_contract(runtime)


def test_rejects_input_pixel_mutation(tmp_path: Path) -> None:
    runtime = fixture_runtime(tmp_path)
    Image.new("RGB", (16, 16), "white").save(runtime.input_paths[0])
    with pytest.raises(AssertionError):
        check_contract(runtime)


def test_rejects_duplicate_output_directory(tmp_path: Path) -> None:
    runtime = fixture_runtime(tmp_path)
    runtime.output.mkdir()
    with pytest.raises(AssertionError):
        check_contract(runtime)


def test_first_step_projection_counts_setup_and_all_remaining_steps() -> None:
    assert projected_seconds(100, 60, 50) == 3100
    assert projected_seconds(100, 71, 50) > 3600
