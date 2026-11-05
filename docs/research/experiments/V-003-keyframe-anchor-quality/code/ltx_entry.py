"""Config-driven adapter to the pinned official ICLoraPipeline; no upstream edits.

The inherited observer wraps the existing Euler loop, without extra forwards.
K2 removes both LoRAs and reference videos through the official Python API.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import importlib.util
import inspect
import json
from pathlib import Path
import resource
import subprocess
import sys
import time


@dataclass(frozen=True, slots=True)
class Anchor:
    frame: int
    path: Path


@dataclass(frozen=True, slots=True)
class ImagePlan:
    path: str
    frame: int
    source_frame: int
    offset: int
    binding: str
    strength: float


def image_plan(anchors: list[Anchor], binding: str, replace_frames: list[int],
               strength: float, temporal_stride: int) -> list[ImagePlan]:
    """Bind accepted anchors deterministically; nearest ties choose the earlier frame."""
    if not anchors or len({a.frame for a in anchors}) != len(anchors):
        raise ValueError('Empty or duplicate accepted anchor frames')
    if binding not in ('guide', 'replace'):
        raise ValueError('Unsupported image binding')
    anchors = sorted(anchors, key=lambda a: a.frame)
    targets = replace_frames if binding == 'replace' else [a.frame for a in anchors]
    plans = []
    for frame in targets:
        if frame < 0 or (binding == 'replace' and frame and (frame - 1) % temporal_stride):
            raise ValueError('Replacement must start a causal latent')
        source = min(anchors, key=lambda a: (abs(a.frame - frame), a.frame))
        plans.append(ImagePlan(str(source.path), frame, source.frame, source.frame - frame,
                               'auto' if frame == 0 else binding, strength))
    return plans


@dataclass(frozen=True, slots=True)
class RunConfig:
    scene_path: Path
    variant: str
    seed: int
    width: int
    height: int
    frames: int
    fps: int
    prompt: str
    images: list[ImagePlan]
    engine_root: Path
    use_control: bool
    control_strength: float
    checkpoint: Path
    upsampler: Path
    gemma: Path
    lora: Path
    canny: Path
    observer_path: Path
    output: Path
    receipt: Path
    expected_steps: int
    expected_grid_lengths: list[int]


def load_config(path: Path) -> RunConfig:
    """CPU-only validation of scene contract, private paths, and pinned checkout."""
    data = json.loads(path.read_text())
    scene_path = Path(data['scene_config'])
    scene = json.loads(scene_path.read_text())
    generation = scene['generation']
    contract = generation['runtime_contract']
    variant = generation['variants'][data['variant']]
    seed = int(data['seed'])
    width, height = generation['resolution']
    frames, fps = generation['frames'], generation['fps']
    if seed not in generation['seeds'] or width % contract['spatial_multiple'] or height % contract['spatial_multiple']:
        raise ValueError('Seed or spatial geometry violates scene contract')
    if (frames - 1) % contract['temporal_stride']:
        raise ValueError('Frame count violates causal temporal grid')
    anchors = [Anchor(int(a['frame']), Path(a['path'])) for a in data['anchors']]
    if not any(a.frame == 0 for a in anchors):
        raise ValueError('Accepted first-frame anchor required')
    if len(anchors) < scene['anchor_generation']['min_keyframes_to_generate']:
        raise ValueError('ANCHORS_INSUFFICIENT')
    if any(a.frame not in scene['keyframes']['segment_frames'] for a in anchors):
        raise ValueError('Accepted anchor is outside preregistered keyframes')
    images = image_plan(anchors, variant['image_binding'], variant.get('replace_frames', []),
                        variant['strength'], contract['temporal_stride'])
    if any(i.frame >= frames for i in images):
        raise ValueError('Image is outside requested clip')
    engine = Path(data['engine_root'])
    commit = subprocess.check_output(['git', '-C', str(engine), 'rev-parse', 'HEAD'], text=True).strip()
    if commit != contract['engine_commit']:
        raise ValueError('Pinned engine commit mismatch')
    dirty = subprocess.check_output(['git', '-C', str(engine), 'diff', '--name-only', 'HEAD'], text=True)
    if dirty.strip():
        raise ValueError('Pinned engine tracked files modified')
    names = ('checkpoint', 'upsampler', 'gemma', 'lora', 'canny', 'observer_path', 'output', 'receipt')
    paths = {name: Path(data[name]) for name in names}
    for name, item in paths.items():
        if not item.is_absolute():
            raise ValueError('Runtime paths must be absolute')
        if name in ('output', 'receipt'):
            if item.exists() or not item.parent.is_dir():
                raise ValueError('Output must be new with existing parent')
        elif not item.exists():
            raise FileNotFoundError(item)
    probe_paths = [a.path for a in anchors]
    if variant['ic_lora_canny']:
        probe_paths.append(paths['canny'])
    for item in probe_paths:
        if not item.is_absolute() or not item.is_file():
            raise FileNotFoundError(item)
        result = subprocess.check_output([data['ffprobe'], '-v', 'error', '-select_streams', 'v:0',
            '-count_frames', '-show_entries', 'stream=width,height,nb_read_frames,r_frame_rate',
            '-of', 'json', str(item)], text=True)
        info = json.loads(result)['streams'][0]
        if (info['width'], info['height']) != (width, height):
            raise ValueError('Conditioning geometry mismatch')
        if item == paths['canny']:
            numerator, denominator = map(int, info['r_frame_rate'].split('/'))
            if int(info['nb_read_frames']) != frames or numerator != fps * denominator:
                raise ValueError('Canny duration or frame rate mismatch')
    return RunConfig(scene_path, data['variant'], seed, width, height, frames, fps,
        generation['prompt'], images, engine, variant['ic_lora_canny'], generation['canny_control']['strength'],
        **paths, expected_steps=contract['scheduler_steps'], expected_grid_lengths=contract['stage_sigma_lengths'])


def run(config: RunConfig) -> None:
    """Use one unmodified official API path for all variants with inherited accounting."""
    spec = importlib.util.spec_from_file_location('v003_inherited_observer', config.observer_path)
    if spec is None or spec.loader is None:
        raise ImportError('Cannot load inherited E1 observer')
    observer = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = observer
    spec.loader.exec_module(observer)
    receipt = observer.RunReceipt(mode='generate', command=['official ICLoraPipeline API', config.variant])
    observer.write_receipt(config.receipt, receipt)
    import torch
    from ltx_core.loader import LTXV_LORA_COMFY_RENAMING_MAP, LoraPathStrengthAndSDOps
    from ltx_core.model.video_vae import get_video_chunks_number
    from ltx_pipelines.ic_lora import ICLoraPipeline
    from ltx_pipelines.utils.media_io import encode_video
    from ltx_pipelines.utils.model_paths import ModelPaths
    from ltx_pipelines.utils.types import ImageConditioningInput

    if not Path(inspect.getfile(ICLoraPipeline)).resolve().is_relative_to(config.engine_root.resolve()):
        raise RuntimeError('Imported pipeline differs from pinned engine checkout')
    accounting = observer.StepAccounting(False, torch.cuda.synchronize)
    restore = observer.install_observer(accounting, receipt)
    started = time.monotonic()
    start_utc = datetime.now(timezone.utc).isoformat()
    receipt.status = 'FAILED'
    try:
        with torch.inference_mode():
            pipeline = ICLoraPipeline(
                model_paths=ModelPaths.from_monolith(str(config.checkpoint), str(config.gemma)),
                spatial_upsampler_path=str(config.upsampler),
                loras=[LoraPathStrengthAndSDOps(str(config.lora), config.control_strength, LTXV_LORA_COMFY_RENAMING_MAP)] if config.use_control else [])
            images = []
            for item in config.images:
                factory = {'auto': ImageConditioningInput.at, 'guide': ImageConditioningInput.guide,
                           'replace': ImageConditioningInput.replace}[item.binding]
                images.append(factory(item.path, item.frame, item.strength))
            result = pipeline(prompt=config.prompt, seed=config.seed, height=config.height, width=config.width,
                num_frames=config.frames, frame_rate=config.fps, images=images,
                video_conditioning=[(str(config.canny), config.control_strength)] if config.use_control else [])
            encode_video(video=result.video, fps=config.fps, audio=result.audio, output_path=str(config.output),
                         video_chunks_number=get_video_chunks_number(result.num_frames, result.tiling_config))
        if accounting.calls != config.expected_steps or accounting.completed != config.expected_steps:
            raise RuntimeError('Unexpected official denoising count')
        if [len(grid) for grid in receipt.grids] != config.expected_grid_lengths:
            raise RuntimeError('Unexpected official sigma grid lengths')
        if not config.output.is_file() or not config.output.stat().st_size:
            raise RuntimeError('Output absent')
        receipt.status = 'GENERATED'
    finally:
        restore()
        receipt.elapsed_seconds = time.monotonic() - started
        receipt.first_step_seconds = accounting.first_seconds
        receipt.denoiser_calls = accounting.calls
        receipt.scheduler_steps_completed = accounting.completed
        receipt.peak_rss_kib = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        receipt.cuda_peak_allocated_bytes = torch.cuda.max_memory_allocated()
        receipt.cuda_peak_reserved_bytes = torch.cuda.max_memory_reserved()
        observer.write_receipt(config.receipt, receipt)
        record = json.loads(config.receipt.read_text())
        record.update(start_utc=start_utc, end_utc=datetime.now(timezone.utc).isoformat(),
            images=[asdict(item) for item in config.images], control_enabled=config.use_control,
            scene_sha256=hashlib.sha256(config.scene_path.read_bytes()).hexdigest())
        temporary = config.receipt.with_suffix('.tmp')
        temporary.write_text(json.dumps(record, indent=2) + '\n')
        temporary.replace(config.receipt)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--cpu-only', action='store_true')
    args = parser.parse_args()
    config = load_config(args.config)
    if args.cpu_only:
        if 'torch' in sys.modules or 'ltx_pipelines' in sys.modules:
            raise RuntimeError('CPU validation imported model packages')
        print(json.dumps({'status': 'CPU_VALIDATED', 'images': [asdict(x) for x in config.images],
                          'control_enabled': config.use_control, 'torch_imported': False}))
        return
    run(config)


if __name__ == '__main__':
    main()
