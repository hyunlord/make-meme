# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# Run with existing research Python: probe_white.py /absolute/config.json [--cpu-only]
"""C-009: BASE / OLD_ON_256 (red-mask trained) / NEW_ON_256 one-step probes on the same white-mask inputs.

Reuses the C-007 probe construction (grid, noise seed 20261101+clip_index, metrics) unchanged.
"""
from pathlib import Path
import json
import sys
import time

from pydantic import BaseModel, ConfigDict


class Config(BaseModel):
    model_config = ConfigDict(frozen=True, extra='forbid')
    c007_code: Path
    runtime: Path
    input_manifest: Path
    old_checkpoint: Path
    new_checkpoint: Path
    output: Path


def append(path: Path, row: dict) -> None:
    with path.open('a') as stream:
        stream.write(json.dumps(row, allow_nan=False) + '\n')


def main() -> None:
    config = Config.model_validate_json(Path(sys.argv[1]).read_text())
    sys.path.insert(0, str(config.c007_code))
    import torch
    from runtime_common import RuntimeConfig, setup, load_pipeline, atomic_json, tensor_summary
    from training_state import load_cache, condition_from_cache
    from point_adapter import PointAnchorAdapter
    from wan_adapter_forward import ForwardInput, adapted_forward
    from diagnostic_metrics import branch_metrics, cfg_metrics
    runtime = RuntimeConfig.model_validate_json(config.runtime.read_text())
    setup(runtime)
    manifest = json.loads((runtime.cache_root / 'CACHE_MANIFEST.json').read_text())
    assert manifest['mask_contract'].startswith('white_v1')
    grid_points = json.loads(config.input_manifest.read_text())['probe_grid']
    assert len(grid_points) == 5
    if '--cpu-only' in sys.argv[2:]:
        print(json.dumps({'status': 'CPU_PASS', 'cuda_initialized': torch.cuda.is_initialized()}))
        return
    config.output.mkdir(parents=True, exist_ok=False)
    tick = time.monotonic()
    pipe = load_pipeline(runtime)
    models = (pipe.dit, pipe.vace)
    from diffsynth.diffusion.flow_match import FlowMatchScheduler
    grid = FlowMatchScheduler('Wan')
    grid.set_timesteps(1000, training=True, shift=5)
    with torch.random.fork_rng(devices=[]):
        adapter = PointAnchorAdapter().to('cuda').eval().requires_grad_(False)
    weights = {'OLD_ON_256': torch.load(config.old_checkpoint, map_location='cpu', weights_only=True)['adapter'],
               'NEW_ON_256': torch.load(config.new_checkpoint, map_location='cpu', weights_only=True)['adapter']}
    forwards = 0
    with torch.no_grad():
        for clip_index, name in enumerate(('elephant', 'goat')):
            path = runtime.cache_root / f'{name}.pt'
            assert manifest['files'][name]['sha256'] == __import__('hashlib').sha256(path.read_bytes()).hexdigest()
            item = load_cache(path, runtime.point_exclusions)
            z0 = item['clean_latent'].to('cuda')
            mask = item['loss_mask'].to('cuda')
            condition = condition_from_cache(item)
            generator = torch.Generator(device='cpu').manual_seed(20261101 + clip_index)
            noise = torch.randn(z0.shape, generator=generator).to('cuda', dtype=torch.bfloat16)
            for point in grid_points:
                index = point['index']
                sigma, timepoint = grid.sigmas[index], grid.timesteps[index]
                assert float(sigma) == point['sigma'] and float(timepoint) == point['timestep']
                z = grid.add_noise(z0, noise, timepoint)
                target = grid.training_target(z0, noise, timepoint)
                model_timestep = timepoint.reshape(1).to('cuda', dtype=torch.bfloat16)
                shared = {'clip': name, **point, 'model_timestep_bf16': float(model_timestep), 'state': tensor_summary(z),
                          'noise': tensor_summary(noise), 'vace_context': tensor_summary(item['vace_context'])}
                predictions, base = {}, {}
                for label in ('BASE', 'OLD_ON_256', 'NEW_ON_256'):
                    for branch, key in (('positive', 'context'), ('negative', 'negative_context')):
                        inputs = ForwardInput(z, model_timestep, item[key].to('cuda'), item['vace_context'].to('cuda'), sigma)
                        if label == 'BASE':
                            pred = pipe.model_fn(dit=pipe.dit, vace=pipe.vace, latents=inputs.latents, timestep=inputs.timestep,
                                                 context=inputs.context, vace_context=inputs.vace_context, vace_scale=1.0)
                        else:
                            adapter.load_state_dict(weights[label], strict=True)
                            pred = adapted_forward(models, inputs, (adapter, condition))
                        assert torch.isfinite(pred).all()
                        forwards += 1
                        predictions[label, branch] = pred
                        metrics = branch_metrics(pred, target, z, sigma, z0, mask)
                        if label == 'BASE':
                            base[branch] = metrics.copy()
                        else:
                            metrics['change_from_base'] = {k: metrics[k] - base[branch][k]
                                                           for k in ('mse', 'object_mse', 'background_mse', 'balanced_loss')}
                        append(config.output / 'PROBES.jsonl', {**shared, 'predictor': label, 'branch': branch, **metrics})
                    if label != 'BASE':
                        append(config.output / 'CFG_STATS.jsonl', {**shared, 'predictor': label,
                            **cfg_metrics(predictions['BASE', 'positive'], predictions['BASE', 'negative'],
                                          predictions[label, 'positive'], predictions[label, 'negative'])})
                atomic_json(config.output / 'progress.json', {'forwards': forwards})
    assert forwards == 60
    atomic_json(config.output / 'result.json', {'status': 'COMPLETE', 'dit_forwards': forwards,
                'elapsed_seconds': time.monotonic() - tick})


if __name__ == '__main__':
    main()
