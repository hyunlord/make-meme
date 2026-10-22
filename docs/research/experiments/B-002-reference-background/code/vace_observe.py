# /// script
# requires-python = ">=3.11"
# dependencies = ["torch"]
# ///
# Imported by the bounded VACE runner, not a standalone model launcher.
"""Read-only runtime shape and noise observations."""
from __future__ import annotations
import hashlib
import json
import time
from pathlib import Path
from typing import TYPE_CHECKING
import torch
if TYPE_CHECKING:
    from diffsynth.pipelines.wan_video import WanVideoPipeline
    from vace_experiment import RunConfig


def install_observers(pipe: WanVideoPipeline, output: Path) -> None:
    """Persist first real tensor output at selected model boundaries."""
    observed = set()
    def hook_for(name: str):
        def record(module, inputs, result) -> None:
            if name in observed or not torch.is_tensor(result):
                return
            observed.add(name)
            row = {"module": name, "output_shape": list(result.shape), "dtype": str(result.dtype),
                   "tensor_input_shapes": [list(value.shape) for value in inputs if torch.is_tensor(value)]}
            with (output / "observed_shapes.jsonl").open("a") as handle:
                handle.write(json.dumps(row) + "\n")
        return record
    selected = ("patch_embedding", "vace_patch_embedding", "blocks.0.self_attn.q", "blocks.0.self_attn.k", "blocks.0.self_attn.v", "blocks.0.cross_attn.q", "blocks.0.cross_attn.k", "blocks.0.cross_attn.v")
    for name, module in pipe.named_modules():
        if name == "text_encoder" or any(name.endswith(suffix) for suffix in selected):
            module.register_forward_hook(hook_for(name))


def save_initial_noise(pipe: WanVideoPipeline, config: RunConfig) -> None:
    """Recreate upstream NoiseInitializer exactly using its local seeded CPU RNG."""
    from diffsynth.pipelines.wan_video import WanVideoUnit_NoiseInitializer
    reference_sentinel = [None] if config.reference else None
    noise = WanVideoUnit_NoiseInitializer().process(
        pipe, config.height, config.width, config.frames, config.seed, "cpu", reference_sentinel, None
    )["noise"]
    torch.save(noise.cpu(), config.output / "initial_noise.pt")
    digest = hashlib.sha256(noise.detach().cpu().contiguous().view(torch.uint8).numpy().tobytes()).hexdigest()
    (config.output / "initial_noise.json").write_text(json.dumps({"shape": list(noise.shape), "dtype": str(noise.dtype), "tensor_bytes_sha256": digest, "method": "Upstream NoiseInitializer with same explicit seed; pipeline independently invokes identical initializer."}, indent=2))


def install_input_observer(pipe: WanVideoPipeline, output: Path) -> None:
    """Read actual sampler-boundary tensors without changing data or RNG."""
    original = pipe.unit_runner
    model_fn = pipe.model_fn
    sampler_timing = {"calls": 0, "model_seconds": 0.0}
    def observed_model_fn(*args, **kwargs):
        torch.cuda.synchronize()
        started = time.monotonic()
        result = model_fn(*args, **kwargs)
        torch.cuda.synchronize()
        sampler_timing["calls"] += 1
        sampler_timing["model_seconds"] += time.monotonic() - started
        (output / "sampler_timing.json").write_text(json.dumps(sampler_timing, indent=2))
        return result
    pipe.model_fn = observed_model_fn
    def observed_runner(unit, pipeline, *inputs):
        before = hashlib.sha256(torch.get_rng_state().numpy().tobytes()).hexdigest()
        result = original(unit, pipeline, *inputs)
        name = type(unit).__name__
        if name in ("WanVideoUnit_NoiseInitializer", "WanVideoUnit_PromptEmbedder", "WanVideoUnit_VACE"):
            tensors = {}
            for group, values in zip(("shared", "positive", "negative"), result):
                for key in ("noise", "context", "vace_context"):
                    value = values.get(key)
                    if torch.is_tensor(value):
                        tensors[f"{group}.{key}"] = {"shape":list(value.shape), "dtype":str(value.dtype), "device":str(value.device), "sha256":hashlib.sha256(value.detach().cpu().contiguous().view(torch.uint8).numpy().tobytes()).hexdigest()}
            row = {"unit":name,"tensors":tensors,"cpu_rng_before":before,"cpu_rng_after":hashlib.sha256(torch.get_rng_state().numpy().tobytes()).hexdigest()}
            with (output / "actual_input_hashes.jsonl").open("a") as handle:
                handle.write(json.dumps(row)+"\n")
        return result
    pipe.unit_runner = observed_runner
