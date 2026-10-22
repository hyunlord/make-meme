"""Single frozen SCAIL inference; standard FFmpeg reader replaces optional decord."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback
import numpy as np
import torch
from PIL import Image


def describe(value: object) -> object:
    if isinstance(value, torch.Tensor):
        return {"shape": list(value.shape), "dtype": str(value.dtype), "device": str(value.device)}
    if isinstance(value, (tuple, list)):
        return [describe(item) for item in value]
    if isinstance(value, dict):
        return {str(key): describe(item) for key, item in value.items()}
    return value if isinstance(value, (int, float, str, bool, type(None))) else type(value).__name__


def main() -> None:
    root, config_path = map(Path, sys.argv[1:3])
    cfg = json.loads(config_path.read_text())
    assert cfg["adapter"] is None and cfg["frames"] == 17 and cfg["steps"] == 40
    assert (cfg["solver"], cfg["shift"], cfg["guide_scale"], cfg["segment_overlap"]) == ("unipc", 3.0, 5.0, 5)
    out = root / "outputs" / cfg["name"]
    out.mkdir(parents=True, exist_ok=False)
    run_started = time.monotonic()
    record: dict = {"config": cfg, "observations": {}, "phases": []}
    def save() -> None:
        (out / "run.json").write_text(json.dumps(record, indent=2))
    def phase(name: str) -> None:
        record["phases"].append({"name": name, "epoch": time.time(), "elapsed_seconds": time.monotonic() - run_started, "proc_status_memory": [line for line in Path("/proc/self/status").read_text().splitlines() if line.startswith(("VmRSS:", "VmHWM:"))], "system_mem_available": next(line for line in Path("/proc/meminfo").read_text().splitlines() if line.startswith("MemAvailable:")), "cuda_allocated": torch.cuda.memory_allocated(), "cuda_reserved": torch.cuda.memory_reserved(), "cuda_peak": torch.cuda.max_memory_allocated()})
        save()
    sys.path.insert(0, str(root / "upstream"))
    from wan import SCAIL2Pipeline
    from wan.configs import SCAIL_CONFIGS
    from wan.utils.scail_utils import load_image_to_tensor_chw_normalized, resize_for_rectangle_crop
    from wan.utils.utils import cache_video
    import wan.modules.model_scail2 as model_module
    import wan.scail as pipeline_module
    def image(name: str) -> torch.Tensor:
        path = root / cfg[name]
        value = load_image_to_tensor_chw_normalized(Image.open(path).convert("RGB"))
        return resize_for_rectangle_crop(value, (cfg["height"], cfg["width"]), reshape_mode="center").squeeze(0)
    def video(name: str) -> torch.Tensor:
        path = root / cfg[name]
        probe = json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,avg_frame_rate,nb_frames", "-of", "json", str(path)]))["streams"][0]
        assert int(probe["nb_frames"]) == 17
        a, b = map(int, probe["avg_frame_rate"].split("/"))
        assert a / b == cfg["fps"]
        raw = subprocess.check_output(["ffmpeg", "-v", "error", "-i", str(path), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"])
        array = np.frombuffer(raw, dtype=np.uint8).copy().reshape(17, probe["height"], probe["width"], 3)
        record["observations"][name + "_decoded"] = {"shape": list(array.shape), "sha256": hashlib.sha256(raw).hexdigest(), "reader": "ffmpeg RGB24, no fps conversion"}
        value = torch.from_numpy(array).permute(0, 3, 1, 2)
        return (resize_for_rectangle_crop(value, (cfg["height"], cfg["width"]), reshape_mode="center") - 127.5) / 127.5
    try:
        inputs = {"img": image("reference"), "ref_mask_img": image("reference_mask"), "pose_video": video("driver"), "driving_mask_video": video("driver_mask").permute(1, 0, 2, 3)}
        record["inputs"] = {key: {**describe(value), "sha256": hashlib.sha256(value.contiguous().numpy().tobytes()).hexdigest()} for key, value in inputs.items()}
        record["input_file_hashes"] = {key: hashlib.sha256((root / cfg[key]).read_bytes()).hexdigest() for key in ("reference", "reference_mask", "driver", "driver_mask")}
        phase("preprocessed")
        os.environ["B007B_LOADER_REPORT"] = str(out / "loader.json")
        pipeline = SCAIL2Pipeline(SCAIL_CONFIGS["SCAIL-14B"], str(root / "models"), str(root / "models/SCAIL.safetensors"), str(root / "upstream/configs/config-14b.json"), t5_cpu=True, init_on_cpu=True, lora_path=None)
        phase("pipeline_loaded")
        record["model_parameters"] = sum(p.numel() for p in pipeline.model.parameters())
        record["forward_calls"] = 0
        def before(module: torch.nn.Module, args: tuple, kwargs: dict) -> None:
            record["forward_calls"] += 1
            if record["forward_calls"] == 1:
                record["observations"]["dit_forward"] = {"args": describe(args), "kwargs": describe(kwargs)}
                phase("first_dit_forward")
        pipeline.model.register_forward_pre_hook(before, with_kwargs=True)
        original_attention = model_module.flash_attention
        def attention(q: torch.Tensor, k: torch.Tensor, v: torch.Tensor, *args: object, **kwargs: object) -> torch.Tensor:
            if "attention" not in record["observations"]:
                record["observations"]["attention"] = {"q": describe(q), "k": describe(k), "v": describe(v)}
                save()
            return original_attention(q, k, v, *args, **kwargs)
        model_module.flash_attention = attention
        for name, module in pipeline.model.named_modules():
            if name in ("patch_embedding", "patch_embedding_pose", "patch_embedding_mask"):
                def hook(mod: torch.nn.Module, args: tuple, result: object, label: str = name) -> None:
                    record["observations"].setdefault(label, describe(result))
                module.register_forward_hook(hook)
        record["resolved_sampling"] = {"negative_prompt": "", "scheduler": "FlowUniPCMultistepScheduler", "constructor_shift": 1, "use_dynamic_shifting": False, "num_train_timesteps": pipeline.num_train_timesteps, "set_timesteps_shift": 3.0, "param_dtype": str(pipeline.param_dtype), "t5_cpu": True, "offload_model": True}
        scheduler_class = pipeline_module.FlowUniPCMultistepScheduler
        original_set_timesteps = scheduler_class.set_timesteps
        def observed_timesteps(scheduler: object, *args: object, **kwargs: object) -> object:
            result = original_set_timesteps(scheduler, *args, **kwargs)
            record["observations"]["scheduler"] = {"config": dict(scheduler.config), "timesteps": scheduler.timesteps.detach().cpu().tolist(), "sigmas": scheduler.sigmas.detach().cpu().tolist()}
            save()
            return result
        scheduler_class.set_timesteps = observed_timesteps
        original_randn = torch.randn
        def observed_randn(*args: object, **kwargs: object) -> torch.Tensor:
            value = original_randn(*args, **kwargs)
            if len(args) == 4 and kwargs.get("generator") is not None and "initial_noise" not in record:
                cpu = value.detach().cpu()
                record["initial_noise"] = {**describe(value), "sha256": hashlib.sha256(cpu.contiguous().numpy().tobytes()).hexdigest()}
                torch.save(cpu, out / "initial_noise.pt")
                save()
            return value
        torch.randn = observed_randn
        started = time.monotonic()
        result = pipeline.generate(input_prompt=cfg["prompt"], **inputs, replace_flag=False, segment_len=17, segment_overlap=5, shift=3.0, sample_solver="unipc", sampling_steps=40, guide_scale=5.0, seed=cfg["seed"], offload_model=True)
        torch.randn = original_randn
        scheduler_class.set_timesteps = original_set_timesteps
        record["sampling_seconds"] = time.monotonic() - started
        record["output"] = describe(result)
        record["output_finite"] = bool(torch.isfinite(result).all())
        assert result.shape[1] == 17 and record["output_finite"]
        phase("decoded")
        torch.save(result.cpu(), out / "raw_output.pt")
        cache_video(tensor=result[None], save_file=str(out / "output.mp4"), fps=cfg["fps"], nrow=1, normalize=True, value_range=(-1, 1))
        record["status"] = "COMPLETED"
        phase("encoded")
    except BaseException as error:
        if "original_set_timesteps" in locals():
            scheduler_class.set_timesteps = original_set_timesteps
        if "original_randn" in locals():
            torch.randn = original_randn
        record["status"] = "FAILED"
        record["error"] = repr(error)
        record["traceback"] = traceback.format_exc()
        save()
        raise


if __name__ == "__main__":
    main()
