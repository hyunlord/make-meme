# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# Run: existing research Python vace_entry.py /absolute/config.json [--cpu-only]
"""V-002 MV2V entry using the verified C-009/C-005 DiffSynth execution paths."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import time
from typing import TYPE_CHECKING, Literal

import numpy as np
from PIL import Image
from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    import torch

NEGATIVE = '色调艳丽，过曝，静态，细节模糊不清，字幕，风格，作品，画作，画面，静止，整体发灰，最差质量，低质量，JPEG压缩残留，丑陋的，残缺的，多余的手指，画得不好的手部，画得不好的脸部，畸形的，毁容的，形态畸形的肢体，手指融合，静止不动的画面，杂乱的背景，三条腿，背景人很多，倒着走'


class Config(BaseModel):
    model_config = ConfigDict(frozen=True, extra='forbid')
    upstream: Path
    weights: Path
    shared_weights: Path
    tokenizer: Path
    condition_dir: Path
    mask_dir: Path
    references: tuple[Path, Path]
    output: Path
    prompt: str
    variant: Literal['M1', 'M2', 'M3']
    model_size: Literal['1.3B', '14B'] = '1.3B'
    mode: Literal['generate', 'probe'] = 'generate'
    width: Literal[832] = 832
    height: Literal[480] = 480
    frames: Literal[73, 49] = 73
    fps: Literal[24] = 24
    seed: Literal[20261103] = 20261103
    steps: Literal[50] = 50
    guidance: Literal[5.0] = 5.0
    sigma_shift: Literal[16.0] = 16.0
    negative_prompt: str = NEGATIVE
    vram_limit: Literal[24.0] = 24.0


class ProbeComplete(Exception):
    """Stop after one full positive/negative scheduler step without decoding."""


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def atomic_json(path: Path, value) -> None:
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')
    temporary.replace(path)


def read_rgb(path: Path) -> Image.Image:
    with Image.open(path) as image:
        assert image.mode == 'RGB' and image.size == (832, 480), str(path)
        return image.copy()


def conditions(config: Config):
    assert config.mode != 'probe' or config.model_size == '14B'
    assert config.frames == 73 or config.model_size == '14B'
    paths = (config.upstream, config.weights, config.shared_weights, config.tokenizer,
             config.condition_dir, config.mask_dir, *config.references)
    assert all(p.is_absolute() and p.exists() for p in paths)
    assert config.output.is_absolute()
    frames = [read_rgb(config.condition_dir / f'{i:03d}.png') for i in range(config.frames)]
    masks = [read_rgb(config.mask_dir / f'{i:03d}.png') for i in range(config.frames)]
    references = [read_rgb(path) for path in config.references]
    areas = []
    for mask in masks:
        pixels = np.asarray(mask)
        assert np.isin(pixels, [0, 255]).all(), 'Non-binary mask'
        assert np.array_equal(pixels[:, :, 0], pixels[:, :, 1])
        assert np.array_equal(pixels[:, :, 1], pixels[:, :, 2]), 'C-008 RGB channel regression'
        areas.append(float((pixels[:, :, 0] == 255).mean()))
    assert (areas[0] == 0) == (config.variant == 'M3')
    assert all(0 < a < 1 for a in areas[1:])
    checkpoints = sorted(config.weights.glob('diffusion_pytorch_model*.safetensors'))
    assert checkpoints
    shared = [config.shared_weights / 'models_t5_umt5-xxl-enc-bf16.pth', config.shared_weights / 'Wan2.1_VAE.pth']
    assert all(p.is_file() for p in shared)
    receipt = {'mask_channels_equal': True, 'mask_values': [0, 255], 'generate_mask': 255,
               'mask_area_fractions': areas, 'frames': config.frames, 'reference_count': 2,
               'rgb_pixel_sha256': [digest(i.tobytes()) for i in frames],
               'mask_pixel_sha256': [digest(i.tobytes()) for i in masks],
               'reference_pixel_sha256': [digest(i.tobytes()) for i in references],
               'reactive_content_preserved': 'VACE encodes RGB*mask; M2 depth is not replaced'}
    return frames, masks, references, checkpoints, shared, receipt


def tensor_summary(tensor: torch.Tensor):
    import torch
    cpu = tensor.detach().to(device='cpu').contiguous()
    return {'shape': list(cpu.shape), 'dtype': str(cpu.dtype),
            'sha256': digest(cpu.view(torch.uint8).numpy().tobytes()),
            'finite': bool(torch.isfinite(cpu).all())}


def main() -> None:
    config = Config.model_validate_json(Path(sys.argv[1]).read_text())
    frames, masks, refs, checkpoints, shared, condition = conditions(config)
    if '--cpu-only' in sys.argv[2:]:
        print(json.dumps({'status': 'CPU_ENTRY_PASS', 'torch_imported': 'torch' in sys.modules,
                          'condition': condition}))
        return
    assert os.environ.get('PYTORCH_CUDA_ALLOC_CONF') == 'expandable_segments:True'
    os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', TOKENIZERS_PARALLELISM='false')
    config.output.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    atomic_json(config.output / 'config.json', config.model_dump(mode='json'))
    atomic_json(config.output / 'condition.json', condition)
    atomic_json(config.output / 'receipt.json', {'status': 'STARTED', 'mode': config.mode})
    sys.path.insert(0, str(config.upstream))
    import torch
    from diffsynth.pipelines.wan_video import WanVideoPipeline, ModelConfig
    from diffsynth.models import wan_video_dit
    wan_video_dit.FLASH_ATTN_3_AVAILABLE = False
    wan_video_dit.FLASH_ATTN_2_AVAILABLE = False
    wan_video_dit.SAGE_ATTN_AVAILABLE = False
    paths = [list(map(str, checkpoints)), *map(str, shared)]
    atomic_json(config.output / 'model-load-attempt.json', {'started': time.time()})
    if config.model_size == '14B':
        disk = {'offload_dtype': 'disk', 'offload_device': 'disk', 'onload_dtype': 'disk',
                'onload_device': 'disk', 'preparing_dtype': torch.bfloat16, 'preparing_device': 'cuda',
                'computation_dtype': torch.bfloat16, 'computation_device': 'cuda'}
        cpu = {'offload_dtype': torch.bfloat16, 'offload_device': 'cpu', 'onload_dtype': torch.bfloat16,
               'onload_device': 'cpu', 'preparing_dtype': torch.bfloat16, 'preparing_device': 'cuda',
               'computation_dtype': torch.bfloat16, 'computation_device': 'cuda'}
        configs = [ModelConfig(path=paths[0], skip_download=True, **disk),
                   *[ModelConfig(path=p, skip_download=True, **cpu) for p in paths[1:]]]
        pipe = WanVideoPipeline.from_pretrained(torch_dtype=torch.bfloat16, device='cuda',
            model_configs=configs, tokenizer_config=ModelConfig(path=str(config.tokenizer), skip_download=True),
            vram_limit=config.vram_limit)
    else:
        pipe = WanVideoPipeline.from_pretrained(torch_dtype=torch.bfloat16, device='cuda',
            model_configs=[ModelConfig(path=p, skip_download=True) for p in paths],
            tokenizer_config=ModelConfig(path=str(config.tokenizer), skip_download=True))
    for module in (pipe.dit, pipe.vace, pipe.text_encoder, pipe.vae):
        module.eval().requires_grad_(False)
    counts = {'model_fn_calls': 0, 'scheduler_steps': 0}
    timing = {'first_model_start': None, 'first_step_seconds': None}
    original_model, original_step = pipe.model_fn, pipe.scheduler.step

    def counted_model(**kwargs):
        if counts['model_fn_calls'] == 0:
            torch.cuda.synchronize()
            timing['first_model_start'] = time.monotonic()
            context = kwargs['vace_context']
            assert tuple(context.shape) == (1, 96, (config.frames + 3) // 4 + 2, 60, 104)
            atomic_json(config.output / 'first-model-input.json', {
                'latents': tensor_summary(kwargs['latents']), 'vace_context': tensor_summary(context),
                'mask_context': tensor_summary(context[:, 32:]), 'reference_prefix_latents': 2,
                'mask_temporal_means': context[:, 32:].detach().float().mean((0, 1, 3, 4)).cpu().tolist(),
                'text_context': tensor_summary(kwargs['context']),
                'timesteps': pipe.scheduler.timesteps.cpu().tolist(),
                'sigmas': pipe.scheduler.sigmas.cpu().tolist(), 'additional_forward_calls': 0})
        counts['model_fn_calls'] += 1
        atomic_json(config.output / 'progress.json', counts)
        return original_model(**kwargs)

    def counted_step(*args, **kwargs):
        result = original_step(*args, **kwargs)
        torch.cuda.synchronize()
        counts['scheduler_steps'] += 1
        if counts['scheduler_steps'] == 1:
            timing['first_step_seconds'] = time.monotonic() - timing['first_model_start']
        atomic_json(config.output / 'progress.json', {**counts, **timing})
        if config.mode == 'probe':
            raise ProbeComplete
        if counts['scheduler_steps'] == config.steps:
            cpu_latent = result.detach().cpu()
            temporary = config.output / 'final_latent.tmp'
            torch.save(cpu_latent, temporary)
            temporary.replace(config.output / 'final_latent.pt')
            restored = torch.load(config.output / 'final_latent.pt', map_location='cpu', weights_only=True)
            assert torch.equal(cpu_latent, restored)
            atomic_json(config.output / 'latent.json', {'readback_exact': True,
                'includes_reference_prefix': 2, **tensor_summary(cpu_latent)})
        return result

    pipe.model_fn, pipe.scheduler.step = counted_model, counted_step
    atomic_json(config.output / 'sampler-attempt.json', {'started': time.time(), 'full_steps': config.steps})
    status = 'GENERATED'
    try:
        raw = pipe(prompt=config.prompt, negative_prompt=config.negative_prompt,
            vace_video=frames, vace_video_mask=masks, vace_reference_image=refs,
            height=config.height, width=config.width, num_frames=config.frames, seed=config.seed,
            rand_device='cpu', tiled=True, cfg_scale=config.guidance,
            num_inference_steps=config.steps, sigma_shift=config.sigma_shift, output_type='floatpoint')
    except ProbeComplete:
        assert counts == {'model_fn_calls': 2, 'scheduler_steps': 1}
        status = 'PROBE_COMPLETE_NO_DECODE'
    else:
        assert counts == {'model_fn_calls': 100, 'scheduler_steps': 50}
        assert torch.isfinite(raw).all()
        torch.save(raw.detach().cpu(), config.output / 'raw_output.pt')
        video = pipe.vae_output_to_video(raw)
        assert len(video) == config.frames
        folder = config.output / 'frames'
        folder.mkdir()
        for i, image in enumerate(video):
            assert image.size == (832, 480)
            image.save(folder / f'{i:03d}.png')
        subprocess.run(['ffmpeg', '-v', 'error', '-n', '-framerate', str(config.fps), '-i',
            str(folder / '%03d.png'), '-c:v', 'libx264', '-crf', '18', '-pix_fmt', 'yuv420p',
            str(config.output / 'output.mp4')], check=True)
        subprocess.run(['ffmpeg', '-v', 'error', '-i', str(config.output / 'output.mp4'), '-f', 'null', '-'], check=True)
    atomic_json(config.output / 'receipt.json', {'status': status, 'mode': config.mode,
        'model_size': config.model_size, 'variant': config.variant, 'seed': config.seed,
        'frames': config.frames, 'width': 832, 'height': 480, 'fps': config.fps,
        'elapsed_seconds': time.monotonic() - started, **counts, **timing,
        'peak_rss_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
        'cuda_peak_allocated_bytes': torch.cuda.max_memory_allocated(),
        'cuda_peak_reserved_bytes': torch.cuda.max_memory_reserved(),
        'guidance': config.guidance, 'sigma_shift': config.sigma_shift,
        'scheduler': 'DiffSynth FlowMatchScheduler native Euler', 'training': 0,
        'endpoint_overwrite': False, 'post_composite': False})


if __name__ == '__main__':
    main()
