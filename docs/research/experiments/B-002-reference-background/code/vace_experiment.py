# /// script
# requires-python = ">=3.11"
# dependencies = ["torch", "pydantic", "pillow", "safetensors"]
# ///
# Run in the isolated pinned DiffSynth environment: python scripts/vace_experiment.py config.json
"""One bounded local VACE inference or LoRA experiment; never downloads models."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Literal

import torch
from PIL import Image, ImageDraw, ImageOps
from pydantic import BaseModel, ConfigDict, Field, model_validator


class RunConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    mode: Literal["inference"]
    upstream: Path
    weights: Path
    tokenizer: Path
    output: Path
    source_video: Path
    condition_video: Path | None = None
    reference: Path | None = None
    adapter: Path | None = None
    optimizer_checkpoint: Path | None = None
    prompt: str
    negative_prompt: str = "blurry, distorted, deformed, watermark"
    width: int = 512
    height: int = 288
    frames: int = 17
    fps: float = Field(default=24, gt=0)
    seed: int = 20261022
    sampling_steps: int = Field(default=20, ge=1, le=50)
    cfg: float = 5
    max_updates: int = Field(default=3, ge=1, le=300)
    max_seconds: int = Field(default=10800, ge=1, le=10800)
    deadline: datetime

    @model_validator(mode="after")
    def check_paths(self) -> RunConfig:
        assert self.condition_video is not None and self.reference is not None
        assert self.adapter is None and self.optimizer_checkpoint is None, "B002 forbids adapters"
        assert (self.width, self.height, self.frames, self.fps) == (512, 288, 17, 24)
        assert self.seed in (20261022, 20261023)
        assert self.sampling_steps == 20 and self.cfg == 5
        assert self.width % 16 == self.height % 16 == 0
        assert self.frames % 4 == 1 and self.frames >= 5
        for path in (self.upstream, self.weights, self.tokenizer, self.source_video):
            assert path.exists(), str(path)
        for path in (self.condition_video, self.reference, self.adapter, self.optimizer_checkpoint):
            assert path is None or path.exists(), str(path)
        assert self.deadline.tzinfo is not None
        return self


def main() -> None:
    config = RunConfig.model_validate_json(Path(sys.argv[1]).read_text())
    config.output.mkdir(parents=True, exist_ok=False)
    (config.output / "config.json").write_text(config.model_dump_json(indent=2))
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    sys.path.insert(0, str(config.upstream))
    from diffsynth.models import wan_video_dit
    from diffsynth.pipelines.wan_video import ModelConfig, WanVideoPipeline
    from diffsynth.utils.data import VideoData
    from vace_observe import install_input_observer, install_observers, save_initial_noise
    wan_video_dit.FLASH_ATTN_3_AVAILABLE = False
    wan_video_dit.FLASH_ATTN_2_AVAILABLE = False
    wan_video_dit.SAGE_ATTN_AVAILABLE = False

    started = time.monotonic()
    deadline = min(config.deadline.timestamp(), time.time() + config.max_seconds)
    assert time.time() < deadline
    (config.output / "pid.txt").write_text(str(os.getpid()))
    source = VideoData(image_folder=str(config.source_video), height=config.height, width=config.width) if config.source_video.is_dir() else VideoData(video_file=str(config.source_video), height=config.height, width=config.width)
    assert len(source) >= config.frames
    target = [source[i] for i in range(config.frames)]
    mask = None
    if config.condition_video:
        control = VideoData(image_folder=str(config.condition_video), height=config.height, width=config.width) if config.condition_video.is_dir() else VideoData(video_file=str(config.condition_video), height=config.height, width=config.width)
        assert len(control) >= config.frames
        condition = [control[i] for i in range(config.frames)]
        mask = [Image.new("RGB", (config.width, config.height), "white") for _ in target]
    else:
        # Explicit neutral erasure prevents the reactive VACE branch seeing target RGB.
        box = (config.width * 3 // 8, config.height // 4, config.width * 5 // 8, config.height * 3 // 4)
        condition = [frame.copy() for frame in target]
        for frame in condition:
            ImageDraw.Draw(frame).rectangle(box, fill=(128, 128, 128))
        mask_frame = Image.new("RGB", (config.width, config.height))
        ImageDraw.Draw(mask_frame).rectangle(box, fill="white")
        mask = [mask_frame.copy() for _ in target]
    reference = None
    if config.reference:
        with Image.open(config.reference) as image:
            reference = ImageOps.pad(image.convert("RGB"), (config.width, config.height), color=(128, 128, 128))
    for name, frames in (("target", target), ("condition", condition), ("mask", mask)):
        if frames is not None:
            folder = config.output / name
            folder.mkdir()
            for index, frame in enumerate(frames):
                frame.save(folder / f"{index:03d}.png")
    if reference:
        reference.save(config.output / "reference.png")
    assert shutil.which("ffmpeg"), "ffmpeg executable required before model loading"
    checkpoints = sorted(config.weights.glob("diffusion_pytorch_model*.safetensors"))
    assert checkpoints
    paths = [list(map(str, checkpoints)), str(config.weights / "models_t5_umt5-xxl-enc-bf16.pth"), str(config.weights / "Wan2.1_VAE.pth")]
    pipe = WanVideoPipeline.from_pretrained(
        torch_dtype=torch.bfloat16, device="cuda",
        model_configs=[ModelConfig(path=p, skip_download=True) for p in paths],
        tokenizer_config=ModelConfig(path=str(config.tokenizer), skip_download=True),
    )
    (config.output / "resolved_runtime.json").write_text(json.dumps({"vram_management_enabled": pipe.vram_management_enabled, "torch_dtype": str(pipe.torch_dtype), "device": str(pipe.device), "attention": "upstream SDPA fallback", "adapter": None}, indent=2))
    install_observers(pipe, config.output)
    save_initial_noise(pipe, config)
    install_input_observer(pipe, config.output)
    torch.manual_seed(config.seed)
    torch.cuda.reset_peak_memory_stats()
    params = {name: sum(p.numel() for p in model.parameters()) for name, model in pipe.named_children()}
    (config.output / "parameter_counts.json").write_text(json.dumps(params, indent=2))
    sampler_started = time.monotonic()
    video = pipe(prompt=config.prompt, negative_prompt=config.negative_prompt,
                 vace_video=condition, vace_video_mask=mask, vace_reference_image=reference,
                 height=config.height, width=config.width, num_frames=config.frames,
                 seed=config.seed, rand_device="cpu", tiled=True,
                 cfg_scale=config.cfg, num_inference_steps=config.sampling_steps)
    pipeline_seconds = time.monotonic() - sampler_started
    for i, frame in enumerate(video):
        frame.save(config.output / f"output-{i:03d}.png")
    assert len(video) == config.frames
    command = ["ffmpeg", "-v", "error", "-n", "-framerate", str(config.fps),
               "-i", str(config.output / "output-%03d.png"), "-frames:v", str(config.frames),
               "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", str(config.output / "result.mp4")]
    (config.output / "encode_command.json").write_text(json.dumps(command, indent=2))
    subprocess.run(command, check=True, timeout=max(1, deadline - time.time()))
    summary = {"status": "COMPLETED", "pipeline_seconds_includes_preprocess_decode": pipeline_seconds, "elapsed_seconds": time.monotonic() - started,
               "cuda_peak_allocated": torch.cuda.max_memory_allocated(),
               "cuda_peak_reserved": torch.cuda.max_memory_reserved()}
    (config.output / "summary.json").write_text(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
