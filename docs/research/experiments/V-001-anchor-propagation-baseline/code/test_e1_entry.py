"""No Torch import: verify exact stop boundary and ordinary 8+3 accounting."""

import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from e1_entry import PROMPT, ProbeComplete, StepAccounting, validate_config


def test_probe() -> None:
    ticks = iter((10.0, 12.5))
    ledger = StepAccounting(True, lambda: None, lambda: next(ticks))
    ledger.before_step(0)
    original_forward_calls = 1
    try:
        ledger.before_step(1)
    except ProbeComplete:
        stopped = True
    else:
        original_forward_calls += 1
        stopped = False
    assert stopped
    assert original_forward_calls == ledger.calls == ledger.completed == 1
    assert ledger.first_seconds == 2.5


def test_generation() -> None:
    ticks = iter((10.0, 12.5))
    ledger = StepAccounting(False, lambda: None, lambda: next(ticks))
    for length in (8, 3):
        for step_index in range(length):
            ledger.before_step(step_index)
        ledger.finish_stage()
    assert ledger.calls == ledger.completed == 11
    assert ledger.first_seconds == 2.5


def test_cpu_contract() -> None:
    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        for filename in ("distilled", "upscale", "union", "anchor", "depth", "config.json",
                         "tokenizer.json", "tokenizer_config.json", "shard.safetensors"):
            (root / filename).write_text("fixture")
        (root / "model.safetensors.index.json").write_text(json.dumps({"weight_map": {"weight": "shard.safetensors"}}))
        official = [
            "--distilled-checkpoint-path", str(root / "distilled"),
            "--spatial-upsampler-path", str(root / "upscale"),
            "--gemma-root", str(root), "--lora", str(root / "union"), "1.0",
            "--image", str(root / "anchor"), "0", "1.0",
            "--video-conditioning", str(root / "depth"), "1.0",
            "--height", "640", "--width", "1152", "--num-frames", "73",
            "--frame-rate", "24", "--seed", "20261103", "--prompt", PROMPT,
            "--output-path", str(root / "output.mp4"),
        ]
        config = {"mode": "probe", "receipt": str(root / "receipt.json"),
                  "official_args": official, "output": str(root / "output.mp4")}
        path = root / "private.json"
        info = SimpleNamespace(stdout=json.dumps({"streams": [
            {"width": 1152, "height": 640, "nb_read_frames": "73", "r_frame_rate": "24/1"},
        ]}))
        with patch("e1_entry.subprocess.run", return_value=info):
            path.write_text(json.dumps(config))
            assert validate_config(path).mode == "probe"
            official[official.index("--height") + 1] = "576"
            path.write_text(json.dumps(config))
            try:
                validate_config(path)
            except ValueError:
                pass
            else:
                raise AssertionError("Old invalid reference geometry accepted")
            official[official.index("--height") + 1] = "640"
            config["mode"] = "generate"
            official[official.index("--num-frames") + 1] = "49"
            path.write_text(json.dumps(config))
            assert validate_config(path).mode == "generate"
            config["output"] = str(root / "wrong.mp4")
            path.write_text(json.dumps(config))
            try:
                validate_config(path)
            except ValueError:
                rejected = True
            else:
                rejected = False
            assert rejected
    assert "torch" not in sys.modules
    assert "ltx_pipelines" not in sys.modules


if __name__ == "__main__":
    test_probe()
    test_generation()
    test_cpu_contract()
    print("PASS: one-step boundary, 8+3 accounting, stdlib CPU contract, 49/73 prefix, output mismatch")
