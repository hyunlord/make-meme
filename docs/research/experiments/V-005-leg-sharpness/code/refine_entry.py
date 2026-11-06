"""Guarded R1 entry; all scene values resolve from supplied JSON and frozen parent config."""
from __future__ import annotations

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

from refine_schedule import read_official_grids, select_schedule


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f'Cannot load frozen module: {name}')
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@dataclass(frozen=True, slots=True)
class RefineConfig:
    scene_path: Path
    source: Path
    source_sha256: str
    run_id: str
    sigma: float
    expected_steps: int
    expected_grid_lengths: tuple[int, ...]


def load_refine(path: Path):
    data = json.loads(path.read_text())
    parent_path = Path(data['parent_entry'])
    if hashlib.sha256(parent_path.read_bytes()).hexdigest() != data['parent_entry_sha256']:
        raise ValueError('Frozen parent entry hash mismatch')
    parent = load_module(parent_path, 'v005_frozen_parent')
    base = parent.load_config(path)
    scene_path = Path(data['v005_scene_config'])
    scene = json.loads(scene_path.read_text())
    run_id = data['run_id']
    request = float(scene['variants']['R1']['sigmas'][run_id])
    if base.seed != scene['variants']['R1']['seed']:
        raise ValueError('R1 seed differs from preregistration')
    if [base.width, base.height] != scene['common_generation']['resolution'] or base.frames != scene['common_generation']['frames']:
        raise ValueError('Parent geometry differs from V005 contract')
    if sorted(image.source_frame for image in base.images) != scene['anchors']['reused_accepted']:
        raise ValueError('R1 accepted anchor positions differ from preregistration')
    source = Path(data['source_raw'])
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    if source_hash != data['source_raw_sha256']:
        raise ValueError('R1 input RAW hash differs from frozen S2 source')
    probe = subprocess.check_output([data['ffprobe'], '-v', 'error', '-count_frames', '-select_streams', 'v:0',
        '-show_entries', 'stream=width,height,nb_read_frames,r_frame_rate', '-of', 'json', str(source)], text=True)
    video = json.loads(probe)['streams'][0]
    if (video['width'], video['height'], int(video['nb_read_frames'])) != (base.width, base.height, base.frames):
        raise ValueError('R1 input RAW geometry mismatch')
    n, d = map(int, video['r_frame_rate'].split('/'))
    if n != base.fps*d:
        raise ValueError('R1 input RAW fps mismatch')
    selected = [select_schedule(grid, request) for grid in read_official_grids(base.engine_root)]
    refine = RefineConfig(scene_path, source, source_hash, run_id, request,
                          sum(item.steps for item in selected), tuple(len(item.sigmas) for item in selected))
    return base, refine, selected


def run(base, refine: RefineConfig) -> None:
    observer = load_module(base.observer_path, 'v005_inherited_observer')
    receipt = observer.RunReceipt(mode='generate', command=['frozen ICLoraPipeline R1 adapter', refine.run_id])
    observer.write_receipt(base.receipt, receipt)
    import torch
    from ltx_core.loader import LTXV_LORA_COMFY_RENAMING_MAP, LoraPathStrengthAndSDOps
    from ltx_core.model.video_vae import get_video_chunks_number
    from ltx_pipelines.ic_lora import ICLoraPipeline
    from ltx_pipelines.utils.media_io import encode_video
    from ltx_pipelines.utils.model_paths import ModelPaths
    from ltx_pipelines.utils.types import ImageConditioningInput
    from refine_runtime import refinement

    if not Path(inspect.getfile(ICLoraPipeline)).resolve().is_relative_to(base.engine_root.resolve()):
        raise RuntimeError('Imported pipeline differs from frozen engine checkout')
    accounting = observer.StepAccounting(False, torch.cuda.synchronize)
    restore = observer.install_observer(accounting, receipt)
    started = time.monotonic()
    start_utc = datetime.now(timezone.utc).isoformat()
    selections = []
    receipt.status = 'FAILED'
    try:
        with torch.inference_mode():
            pipeline = ICLoraPipeline(
                model_paths=ModelPaths.from_monolith(str(base.checkpoint), str(base.gemma)),
                spatial_upsampler_path=str(base.upsampler),
                loras=[LoraPathStrengthAndSDOps(str(base.lora), base.control_strength, LTXV_LORA_COMFY_RENAMING_MAP)])
            images = [getattr(ImageConditioningInput, 'at' if item.binding == 'auto' else 'guide')(
                item.path, item.frame, item.strength) for item in base.images]
            with refinement(pipeline, refine.source, refine.sigma, selections):
                result = pipeline(prompt=base.prompt, seed=base.seed, height=base.height, width=base.width,
                    num_frames=base.frames, frame_rate=base.fps, images=images,
                    video_conditioning=[(str(base.canny), base.control_strength)])
                encode_video(video=result.video, fps=base.fps, audio=result.audio, output_path=str(base.output),
                    video_chunks_number=get_video_chunks_number(result.num_frames, result.tiling_config))
        if accounting.calls != refine.expected_steps or accounting.completed != refine.expected_steps:
            raise RuntimeError('Unexpected R1 denoising count')
        if tuple(len(grid) for grid in receipt.grids) != refine.expected_grid_lengths:
            raise RuntimeError('Unexpected R1 executed sigma grid lengths')
        if not base.output.is_file() or not base.output.stat().st_size:
            raise RuntimeError('R1 output absent')
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
        observer.write_receipt(base.receipt, receipt)
        record = json.loads(base.receipt.read_text())
        record.update(start_utc=start_utc, end_utc=datetime.now(timezone.utc).isoformat(),
            images=[asdict(item) for item in base.images], control_enabled=True,
            frames=base.frames, fps=base.fps, resolution=[base.width, base.height],
            scene_sha256=hashlib.sha256(refine.scene_path.read_bytes()).hexdigest(),
            input_raw_sha256=refine.source_sha256, requested_sigma=refine.sigma,
            expected_scheduler_steps=refine.expected_steps, expected_grid_lengths=refine.expected_grid_lengths,
            refinement_stages=[dict(asdict(item), remaining_steps=item.steps) for item in selections],
            refinement_initialization=['VAE_ENCODE_S2_RAW_AT_STAGE1_RESOLUTION', 'OFFICIAL_SPATIAL_UPSAMPLE_OF_REFINED_STAGE1'],
            noising='official GaussianNoiser: (1-sigma)*clean + sigma*noise, then original conditioning denoise mask')
        temporary = base.receipt.with_suffix('.tmp')
        temporary.write_text(json.dumps(record, indent=2)+'\n')
        temporary.replace(base.receipt)


def main() -> None:
    args = sys.argv[1:]
    if len(args) not in (2, 3) or args[0] != '--config' or (len(args) == 3 and args[2] != '--cpu-only'):
        raise ValueError('Usage: refine_entry.py --config RUNTIME.json [--cpu-only]')
    base, refine, selections = load_refine(Path(args[1]))
    if '--cpu-only' in args:
        if 'torch' in sys.modules or 'ltx_pipelines' in sys.modules:
            raise RuntimeError('CPU validation imported model packages')
        print(json.dumps({'status':'CPU_VALIDATED', 'run_id':refine.run_id,
            'requested_sigma':refine.sigma, 'stages':[dict(asdict(item), remaining_steps=item.steps) for item in selections],
            'expected_steps':refine.expected_steps, 'source_sha256':refine.source_sha256, 'torch_imported':False}))
        return
    run(base, refine)


if __name__ == '__main__':
    main()
