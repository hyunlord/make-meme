# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# Run: existing research Python wan_refine.py /absolute/runtime.json [--cpu-only]
"""Frozen low-expert DiffSynth video refinement; guard admission is external."""
from __future__ import annotations

import os
from pathlib import Path
import resource
import sys
import time
from typing import TYPE_CHECKING

sys.path.insert(0, str(Path(__file__).resolve().parent))
from v006runtime_config import Runtime, check_contract, projected_seconds
from v006runtime_io import atomic_json, save_tensor, save_video, tensor_summary

if TYPE_CHECKING:
    import torch


class TimeBudgetExceeded(RuntimeError):
    """The first actual denoising step projects beyond the authorized run budget."""


def main() -> None:
    """Read a frozen contract, run once, retain all evidence, and never retry."""
    runtime = Runtime.model_validate_json(Path(sys.argv[1]).read_text())
    frames = check_contract(runtime)
    if "--cpu-only" in sys.argv[2:]:
        print('{"status":"CPU_ENTRY_PASS","model_loads":0,"generations":0}')
        return
    assert os.environ.get("PYTORCH_CUDA_ALLOC_CONF") == "expandable_segments:True"
    os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1",
                      DIFFSYNTH_SKIP_DOWNLOAD="True", TOKENIZERS_PARALLELISM="false")
    runtime.output.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    atomic_json(runtime.output / "config.json", runtime.model_dump(mode="json"))
    atomic_json(runtime.output / "receipt.json", {"status": "STARTED", "run_id": runtime.run_id})
    sys.path.insert(0, str(runtime.upstream))
    import torch
    from diffsynth.pipelines.wan_video import ModelConfig, WanVideoPipeline
    from diffsynth.models import wan_video_dit

    wan_video_dit.FLASH_ATTN_3_AVAILABLE = False
    wan_video_dit.FLASH_ATTN_2_AVAILABLE = False
    wan_video_dit.SAGE_ATTN_AVAILABLE = False
    disk = {"offload_dtype": "disk", "offload_device": "disk", "onload_dtype": "disk",
            "onload_device": "disk", "preparing_dtype": torch.bfloat16,
            "preparing_device": "cuda", "computation_dtype": torch.bfloat16,
            "computation_device": "cuda"}
    cpu = {"offload_dtype": torch.bfloat16, "offload_device": "cpu",
           "onload_dtype": torch.bfloat16, "onload_device": "cpu",
           "preparing_dtype": torch.bfloat16, "preparing_device": "cuda",
           "computation_dtype": torch.bfloat16, "computation_device": "cuda"}
    configs = [ModelConfig(path=[str(p) for p in runtime.checkpoint_paths], skip_download=True, **disk),
               ModelConfig(path=str(runtime.text_encoder), skip_download=True, **cpu),
               ModelConfig(path=str(runtime.vae), skip_download=True, **cpu)]
    atomic_json(runtime.output / "model-load-attempt.json", {"started_unix": time.time()})
    pipe = WanVideoPipeline.from_pretrained(
        torch_dtype=torch.bfloat16, device="cuda", model_configs=configs,
        tokenizer_config=ModelConfig(path=str(runtime.tokenizer), skip_download=True),
        redirect_common_files=False, vram_limit=runtime.vram_limit_gib,
    )
    assert pipe.dit is not None and pipe.dit2 is None
    assert pipe.vace is None and pipe.vace2 is None
    for module in (pipe.dit, pipe.text_encoder, pipe.vae):
        module.eval().requires_grad_(False)
    counts = {"model_fn_calls": 0, "model_fn_completed": 0, "scheduler_steps": 0, "vae_encodes": 0}
    timing = {"first_step_seconds": 0.0, "projected_seconds": 0.0}
    first_model_start = 0.0
    original_model, original_step = pipe.model_fn, pipe.scheduler.step
    original_encode, original_noise = pipe.vae.encode, pipe.scheduler.add_noise

    def observed_encode(*args, **kwargs) -> torch.Tensor:
        result = original_encode(*args, **kwargs)
        counts["vae_encodes"] += 1
        atomic_json(runtime.output / f"encoded-latent-{counts['vae_encodes']}.json", tensor_summary(result))
        return result

    def observed_noise(original_samples, noise, timestep) -> torch.Tensor:
        result = original_noise(original_samples, noise, timestep)
        atomic_json(runtime.output / "v2v-noise.json", {
            "clean_latent": tensor_summary(original_samples), "noise": tensor_summary(noise),
            "initial_latent": tensor_summary(result), "timestep": float(timestep),
            "cpu_rng": tensor_summary(torch.get_rng_state()),
        })
        return result

    def observed_model(**kwargs) -> torch.Tensor:
        nonlocal first_model_start
        if counts["model_fn_calls"] == 0:
            sigmas = pipe.scheduler.sigmas.detach().cpu()
            assert len(sigmas) == runtime.steps
            assert float(sigmas.max()) < runtime.boundary
            assert abs(float(sigmas[0]) - runtime.expected_sigma) <= runtime.sigma_tolerance
            latent = kwargs["latents"]
            patch = tuple(pipe.dit.patch_size)
            latent_shape = tuple(latent.shape)
            tokens = 1
            for size, stride in zip(latent_shape[-3:], patch, strict=True):
                assert size % stride == 0
                tokens *= size // stride
            atomic_json(runtime.output / "first-model-input.json", {
                "latents": tensor_summary(latent), "context": tensor_summary(kwargs["context"]),
                "patch_size": list(patch), "token_count": tokens,
                "timesteps": pipe.scheduler.timesteps.cpu().tolist(), "sigmas": sigmas.tolist(),
                "expert": "low_noise_only", "dit2_present": False,
            })
            torch.cuda.synchronize()
            first_model_start = time.monotonic()
        counts["model_fn_calls"] += 1
        atomic_json(runtime.output / "progress.json", {**counts, **timing})
        result = original_model(**kwargs)
        counts["model_fn_completed"] += 1
        atomic_json(runtime.output / "progress.json", {**counts, **timing})
        return result

    def observed_step(*args, **kwargs) -> torch.Tensor:
        result = original_step(*args, **kwargs)
        torch.cuda.synchronize()
        counts["scheduler_steps"] += 1
        if counts["scheduler_steps"] == 1:
            timing["first_step_seconds"] = time.monotonic() - first_model_start
            timing["projected_seconds"] = projected_seconds(
                first_model_start - started, timing["first_step_seconds"], runtime.steps)
            atomic_json(runtime.output / "first-step-projection.json", timing)
            if timing["projected_seconds"] > runtime.maximum_seconds:
                raise TimeBudgetExceeded(timing["projected_seconds"])
        atomic_json(runtime.output / "progress.json", {**counts, **timing})
        if counts["scheduler_steps"] == runtime.steps:
            save_tensor(result, runtime.output / "final_latent.pt")
        return result

    pipe.model_fn, pipe.scheduler.step = observed_model, observed_step
    pipe.vae.encode, pipe.scheduler.add_noise = observed_encode, observed_noise
    atomic_json(runtime.output / "sampler-attempt.json", {"started_unix": time.time()})
    status = "FAILED"
    try:
        raw = pipe(prompt=runtime.prompt, negative_prompt=runtime.negative_prompt,
                   input_video=frames, denoising_strength=runtime.strength,
                   height=runtime.height, width=runtime.width, num_frames=runtime.frames,
                   seed=runtime.seed, rand_device="cpu", tiled=True,
                   tile_size=runtime.tile_size, tile_stride=runtime.tile_stride,
                   cfg_scale=runtime.guidance, num_inference_steps=runtime.steps,
                   sigma_shift=runtime.sigma_shift, switch_DiT_boundary=runtime.boundary,
                   output_type="floatpoint")
    except TimeBudgetExceeded:
        status = "BLOCKED_TIME"
    else:
        assert counts["scheduler_steps"] == runtime.steps
        expected_calls = runtime.steps * (2 if runtime.guidance != 1 else 1)
        assert counts["model_fn_calls"] == expected_calls and counts["vae_encodes"] == 1
        assert counts["model_fn_completed"] == expected_calls
        assert torch.isfinite(raw).all()
        save_tensor(raw, runtime.output / "raw_output.pt")
        save_video(pipe.vae_output_to_video(raw), runtime)
        status = "GENERATED"
    finally:
        atomic_json(runtime.output / "receipt.json", {
            "status": status, "run_id": runtime.run_id, **counts, **timing,
            "elapsed_seconds": time.monotonic() - started,
            "peak_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
            "cuda_peak_allocated_bytes": torch.cuda.max_memory_allocated(),
            "cuda_peak_reserved_bytes": torch.cuda.max_memory_reserved(),
            "frames": runtime.frames, "width": runtime.width, "height": runtime.height,
            "fps": runtime.fps, "seed": runtime.seed, "training": 0,
            "additional_probe": 0, "endpoint_overwrite": False,
        })


if __name__ == "__main__":
    main()
