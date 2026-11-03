#!/usr/bin/env python3
"""Run the frozen official E2 CLI; --cpu-only never imports model packages.

Usage: python e2_entry.py --config PRIVATE.json [--cpu-only]
Private keys: python, engine_root, model_root, case, output, receipt, ffprobe,
mode (probe|generate), seed (20261103|20261104), num_frames (73|49).
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import resource
import runpy
import subprocess
import sys
import tempfile
import time

PROMPT = ("Replace the two dogs in the video with the two dogs in the reference image: "
          "the large black Labrador Retriever and the slender grey Italian Greyhound, "
          "matching their positions. Keep the dance motion, timing, background, lighting "
          "and camera exactly.")


class ProbeComplete(Exception):
    """One complete scheduler step, interrupted before decode or another forward."""


def atomic_json(path: Path, data: dict) -> None:
    with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as handle:
        temporary = Path(handle.name)
        json.dump(data, handle, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def media_info(ffprobe: str, path: str) -> dict:
    result = subprocess.run(
        [ffprobe, "-v", "error", "-select_streams", "v:0", "-count_frames",
         "-show_entries", "stream=width,height,nb_read_frames,r_frame_rate",
         "-of", "json", path], check=True, capture_output=True, text=True)
    return json.loads(result.stdout)["streams"][0]


def validate(config: dict) -> list[str]:
    expected = {"python", "engine_root", "model_root", "case", "output", "receipt",
                "ffprobe", "mode", "seed", "num_frames"}
    if set(config) != expected:
        raise ValueError(f"Config keys must be exactly {sorted(expected)}")
    if config["mode"] not in ("probe", "generate"):
        raise ValueError("Invalid mode")
    if config["seed"] not in (20261103, 20261104) or config["num_frames"] not in (49, 73):
        raise ValueError("Unapproved seed or frame count")
    for key in expected - {"mode", "seed", "num_frames"}:
        path = Path(config[key])
        if not path.is_absolute():
            raise ValueError(f"{key} must be absolute")
        if key in ("output", "receipt"):
            if path.exists() or not path.parent.is_dir():
                raise ValueError(f"{key} already exists or its parent is absent")
        elif not path.exists():
            raise FileNotFoundError(f"Missing {key}")
    if os.path.abspath(sys.executable) != os.path.abspath(config["python"]):
        raise ValueError("Use the declared research executable")
    engine = Path(config["engine_root"])
    if not (engine / "infer_single_gpu.py").is_file():
        raise FileNotFoundError("Official entry absent")
    model_config = json.loads((Path(config["model_root"]) / "config.json").read_text())
    if model_config.get("model_type") != "bernini_renderer":
        raise ValueError("E2 requires renderer-only checkpoint")
    case = json.loads(Path(config["case"]).read_text())
    if set(case) != {"task_type", "guidance_mode", "prompt", "video", "images", "output"}:
        raise ValueError("Case contains unexpected configuration overrides")
    if case["task_type"] != "rv2v" or case["guidance_mode"] != "rv2v":
        raise ValueError("RV2V required")
    if case["prompt"] != PROMPT or case["output"] != config["output"]:
        raise ValueError("Prompt/output mismatch")
    videos = case["video"] if isinstance(case["video"], list) else [case["video"]]
    if len(videos) != 1 or len(case["images"]) != 1:
        raise ValueError("One source clip and one fixed anchor required")
    for path in videos + case["images"]:
        if not Path(path).is_absolute() or not Path(path).is_file():
            raise FileNotFoundError("Missing absolute media input")
        info = media_info(config["ffprobe"], path)
        if (info["width"], info["height"]) != (832, 480):
            raise ValueError("E2 media must be 832x480")
        if path in videos:
            if int(info["nb_read_frames"]) != config["num_frames"]:
                raise ValueError("Source frame count mismatch")
            numerator, denominator = map(int, info["r_frame_rate"].split("/"))
            if numerator != 24 * denominator:
                raise ValueError("Source must be 24fps")
    return [str(engine / "infer_single_gpu.py"), "--config", config["model_root"],
            "--case", config["case"], "--seed", str(config["seed"]),
            "--num_frames", str(config["num_frames"]), "--width", "832", "--height", "480",
            "--fps", "24", "--max_image_size", "832"]


def run_heavy(config: dict, argv: list[str]) -> None:
    # Deliberately imported only after the CPU-only branch has returned.
    sys.path.insert(0, config["engine_root"])
    import torch
    from bernini.models.wan_diffusion import GEN_Wanx22

    started = time.perf_counter()
    receipt = {"mode": config["mode"], "seed": config["seed"],
               "num_frames": config["num_frames"], "scheduler_steps": 0,
               "dit_forward_calls": 0, "status": "STARTED"}
    output = Path(config["receipt"])
    atomic_json(output, receipt)
    original_sample = GEN_Wanx22.sample

    def instrumented_sample(model, *args, **kwargs):
        original_step = model.scheduler.step
        original_forward = model.shared_step
        first_forward = None

        def forward(*forward_args, **forward_kwargs):
            nonlocal first_forward
            if config["mode"] == "probe" and receipt["scheduler_steps"]:
                raise RuntimeError("Probe attempted a second step")
            if first_forward is None:
                torch.cuda.synchronize()
                first_forward = time.perf_counter()
                receipt["timesteps"] = model.scheduler.timesteps.detach().cpu().tolist()
                receipt["sigmas"] = model.scheduler.sigmas.detach().cpu().tolist()
                if len(receipt["timesteps"]) != 40:
                    raise RuntimeError("Official 40-step grid changed")
            receipt["dit_forward_calls"] += 1
            return original_forward(*forward_args, **forward_kwargs)

        def step(*step_args, **step_kwargs):
            if config["mode"] == "probe" and receipt["scheduler_steps"]:
                raise RuntimeError("Probe attempted a second scheduler step")
            result = original_step(*step_args, **step_kwargs)
            receipt["scheduler_steps"] += 1
            if receipt["scheduler_steps"] == 1:
                torch.cuda.synchronize()
                if first_forward is None:
                    raise RuntimeError("No observed DiT forward")
                receipt["first_step_seconds"] = time.perf_counter() - first_forward
                receipt["first_step_dit_calls"] = receipt["dit_forward_calls"]
                if config["mode"] == "probe":
                    raise ProbeComplete()
            return result

        model.shared_step = forward
        model.scheduler.step = step
        try:
            return original_sample(model, *args, **kwargs)
        finally:
            model.shared_step = original_forward
            model.scheduler.step = original_step

    GEN_Wanx22.sample = instrumented_sample
    old_argv = sys.argv
    sys.argv = argv
    try:
        try:
            runpy.run_path(argv[0], run_name="__main__")
        except ProbeComplete:
            if config["mode"] != "probe" or receipt["scheduler_steps"] != 1:
                raise RuntimeError("Invalid probe completion")
            receipt["status"] = "PROBE_COMPLETE_NO_DECODE"
        else:
            if config["mode"] == "probe":
                raise RuntimeError("Probe hook was not reached")
            if receipt["scheduler_steps"] != 40:
                raise RuntimeError("Generation did not complete 40 steps")
            if not Path(config["output"]).is_file():
                raise RuntimeError("Official output absent")
            receipt["status"] = "GENERATION_COMPLETE"
    except BaseException as error:
        receipt["status"] = "FAILED"
        receipt["error_type"] = type(error).__name__
        raise
    finally:
        GEN_Wanx22.sample = original_sample
        sys.argv = old_argv
        receipt["elapsed_seconds"] = time.perf_counter() - started
        receipt["peak_cuda_allocated_bytes"] = torch.cuda.max_memory_allocated()
        receipt["peak_cuda_reserved_bytes"] = torch.cuda.max_memory_reserved()
        receipt["peak_rss_native_units"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        receipt["rss_units"] = "KiB on Linux; bytes on macOS"
        atomic_json(output, receipt)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--cpu-only", action="store_true")
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    argv = validate(config)
    if args.cpu_only:
        if "torch" in sys.modules or "bernini" in sys.modules:
            raise RuntimeError("CPU path imported model code")
        print(json.dumps({"status": "CPU_VALIDATED", "torch_imported": False,
                          "mode": config["mode"], "frames": config["num_frames"]}))
        return
    run_heavy(config, argv)


if __name__ == "__main__":
    main()
