# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# Run with existing research Python: probe_families.py /absolute/config.json [--cpu-only]
"""C-011 matched one-step probes: L (C-009 layout cache + C-009 ckpt256) vs E (endpoint cache + C-011 ckpt256).

Same clean latent, noise, sigma and target in both families; only the family's own vace_context and checkpoint differ.
72 forwards (4 cases x 3 sigma x 2 families x BASE/ON/NULL) + 16 forward/VJP gradient summaries. No optimizer.
"""
from pathlib import Path
import hashlib
import json
import sys
import time

from pydantic import BaseModel, ConfigDict


class Config(BaseModel):
    model_config = ConfigDict(frozen=True, extra='forbid')
    c006_code: Path
    c010_code: Path
    runtime: Path
    probe_manifest: Path
    caches: dict[str, Path]
    checkpoints: dict[str, Path]
    checkpoint_sha256: dict[str, str]
    output: Path


def main() -> None:
    config = Config.model_validate_json(Path(sys.argv[1]).read_text())
    sys.path.insert(0, str(config.c010_code))
    sys.path.insert(1, str(config.c006_code))
    import torch
    from runtime_common import RuntimeConfig, setup, load_pipeline
    from training_state import load_cache, condition_from_cache, balanced_loss
    from point_adapter import PointAnchorAdapter
    from point_features import make_null
    from wan_adapter_forward import ForwardInput, adapted_forward
    from signal_common import CASES, NOISE_SEED, TARGET_SIGMAS, decompose, rms, cosine, tensor_sha, write_json
    runtime = RuntimeConfig.model_validate_json(config.runtime.read_text())
    setup(runtime)
    families = {'L': 'white_v1', 'E': 'endpoint_gray127_v1'}
    for fam, root in config.caches.items():
        m = json.loads((root / 'CACHE_MANIFEST.json').read_text())
        assert m['mask_contract'].startswith('white_v1')
        assert m.get('condition_family', 'white_v1') == families[fam], (fam, m.get('condition_family'))
    states = {}
    for fam, path in config.checkpoints.items():
        assert hashlib.sha256(path.read_bytes()).hexdigest() == config.checkpoint_sha256[fam]
        states[fam] = torch.load(path, map_location='cpu', weights_only=True)['adapter']
    grid_points = {p['target_sigma']: p for p in json.loads(config.probe_manifest.read_text())['probe_grid']}
    if '--cpu-only' in sys.argv[2:]:
        print(json.dumps({'status': 'CPU_PASS', 'cuda_initialized': torch.cuda.is_initialized()}))
        return
    config.output.mkdir(parents=True, exist_ok=False)
    tick = time.monotonic()
    pipe = load_pipeline(runtime)
    models = (pipe.dit, pipe.vace)
    backbone = [p for m in models for p in m.parameters()]
    sampled = [p.detach().flatten()[:16].clone() for p in backbone]
    from diffsynth.diffusion.flow_match import FlowMatchScheduler
    grid = FlowMatchScheduler('Wan')
    grid.set_timesteps(1000, training=True, shift=5)
    with torch.random.fork_rng(devices=[]):
        adapter = PointAnchorAdapter().to('cuda').eval().requires_grad_(False)
    counts = {'probe_forward': 0, 'gradient_forward': 0, 'vjp': 0, 'optimizer_steps': 0}
    results = {'probes': {}, 'gradients': {}}
    items = {}
    for name, split in CASES:
        items[name] = {}
        for fam, root in config.caches.items():
            item = load_cache(root / f'{name}.pt', runtime.point_exclusions)
            items[name][fam] = item
        a, b = items[name]['L'], items[name]['E']
        for key in ('clean_latent', 'loss_mask', 'context', 'patches', 'positions', 'visible', 'valid', 'anchor_valid', 'box_wh'):
            assert torch.equal(a[key], b[key]), f'{name}:{key} must be shared by L and E'
        assert not torch.equal(a['vace_context'], b['vace_context'])

    def inputs_for(name, fam, ts):
        item = items[name][fam]
        z0 = item['clean_latent'].to('cuda')
        noise = torch.randn(z0.shape, generator=torch.Generator(device='cpu').manual_seed(NOISE_SEED[name])).to('cuda', dtype=torch.bfloat16)
        point = grid_points[ts]
        index = point['index']
        sigma, timepoint = grid.sigmas[index], grid.timesteps[index]
        assert float(sigma) == point['sigma']
        z = grid.add_noise(z0, noise, timepoint)
        target = grid.training_target(z0, noise, timepoint)
        model_t = timepoint.reshape(1).to('cuda', dtype=torch.bfloat16)
        inputs = ForwardInput(z, model_t, item['context'].to('cuda'), item['vace_context'].to('cuda'), sigma)
        meta = {'grid_index': index, 'sigma': float(sigma), 'timestep_fp32': float(timepoint), 'model_timestep_bf16': float(model_t),
                'clean': tensor_sha(z0), 'noise': tensor_sha(noise), 'noisy': tensor_sha(z), 'target': tensor_sha(target),
                'vace_context': tensor_sha(item['vace_context'])}
        return inputs, target, item['loss_mask'].to('cuda'), meta

    with torch.no_grad():
        for name, split in CASES:
            on = condition_from_cache(items[name]['L'])
            null = make_null(on)
            for ts in TARGET_SIGMAS:
                cell = {'split': split}
                for fam in ('L', 'E'):
                    inputs, target, mask, meta = inputs_for(name, fam, ts)
                    adapter.load_state_dict(states[fam], strict=True)
                    v = {'BASE': pipe.model_fn(dit=pipe.dit, vace=pipe.vace, latents=inputs.latents, timestep=inputs.timestep,
                                               context=inputs.context, vace_context=inputs.vace_context, vace_scale=1.0),
                         'ON': adapted_forward(models, inputs, (adapter, on)),
                         'NULL': adapted_forward(models, inputs, (adapter, null))}
                    counts['probe_forward'] += 3
                    assert all(torch.isfinite(x).all() for x in v.values())
                    loss = {k: decompose(x, x, target, mask) for k, x in v.items()}
                    cell[fam] = {'meta': meta,
                                 'loss': {k: {p: loss[k][p]['L_A'] for p in ('obj', 'bg', 'W')} for k in v},
                                 'ON_vs_BASE': decompose(v['ON'], v['BASE'], target, mask),
                                 'NULL_vs_BASE': decompose(v['NULL'], v['BASE'], target, mask),
                                 'ON_vs_NULL': decompose(v['ON'], v['NULL'], target, mask),
                                 'rms': {'base': rms(v['BASE']), 'on_minus_null': rms(v['ON'].float() - v['NULL'].float()),
                                         'on_minus_base': rms(v['ON'].float() - v['BASE'].float())}}
                assert cell['L']['meta']['noisy'] == cell['E']['meta']['noisy'] and cell['L']['meta']['target'] == cell['E']['meta']['target']
                cell['delta_L'] = cell['L']['ON_vs_NULL']['W']['direct_diff']
                cell['delta_E'] = cell['E']['ON_vs_NULL']['W']['direct_diff']
                cell['I'] = cell['delta_E'] - cell['delta_L']
                results['probes'][f'{name}/{ts}'] = cell
                write_json(config.output / 'PROBES.partial.json', results)

    grad_adapter = PointAnchorAdapter().to('cuda')
    for name in ('elephant', 'goat'):
        on = condition_from_cache(items[name]['L'])
        null = make_null(on)
        for ts in (0.50, 0.05):
            for fam in ('L', 'E'):
                grad_adapter.load_state_dict(states[fam], strict=True)
                before = {k: v.detach().clone() for k, v in grad_adapter.state_dict().items()}
                inputs, target, mask, meta = inputs_for(name, fam, ts)
                g = {}
                for label, cond in (('ON', on), ('NULL', null)):
                    captured = {}
                    def keep(module, args, out, captured=captured):
                        out.retain_grad()
                        captured['motion'] = out
                    handle = grad_adapter.register_forward_hook(keep)
                    pred = adapted_forward(models, inputs, (grad_adapter, cond), training=True); counts['gradient_forward'] += 1
                    handle.remove()
                    loss = balanced_loss(pred, target, mask)
                    loss.backward(); counts['vjp'] += 1
                    assert all(p.grad is None for p in backbone)
                    g[label] = {'params': {k: p.grad.detach().clone() for k, p in grad_adapter.named_parameters()},
                                'motion': captured['motion'].grad.detach()[0].clone(), 'loss': float(loss)}
                    grad_adapter.zero_grad(set_to_none=True)
                    del pred, loss
                assert all(torch.equal(grad_adapter.state_dict()[k], v) for k, v in before.items())
                row = {'loss_on': g['ON']['loss'], 'loss_null': g['NULL']['loss'], 'modules': {}}
                for k in g['ON']['params']:
                    a, b = g['ON']['params'][k], g['NULL']['params'][k]
                    row['modules'][k] = {'norm_on': float(a.double().norm()), 'norm_null': float(b.double().norm()),
                                         'norm_on_minus_null': float((a.double() - b.double()).norm()), 'cosine': cosine(a, b)}
                a, b = g['ON']['motion'], g['NULL']['motion']
                row['motion_context'] = {'norm_on': float(a.double().norm()), 'norm_null': float(b.double().norm()),
                                         'norm_on_minus_null': float((a.double() - b.double()).norm()), 'cosine': cosine(a, b)}
                results['gradients'][f'{name}/{ts}/{fam}'] = row
                del g
    results['counts'] = counts
    results['backbone_samples_unchanged'] = all(torch.equal(p.detach().flatten()[:16], s) for p, s in zip(backbone, sampled))
    results['elapsed_seconds'] = time.monotonic() - tick
    write_json(config.output / 'PROBES.json', results)
    print(json.dumps({'status': 'COMPLETE', **counts}))


if __name__ == '__main__':
    main()
