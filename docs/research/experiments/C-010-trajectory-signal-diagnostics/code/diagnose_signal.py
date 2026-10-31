# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# Run with existing research Python: diagnose_signal.py /absolute/config.json [--cpu-only]
"""C-010 stages B-E (+ optional stored-rollout replay) on frozen C-009 white-condition checkpoints.

No optimizer, no parameter update, no sampler, no VAE. Observers only read values.
"""
from dataclasses import replace
from pathlib import Path
import hashlib
import json
import math
import sys
import time

from pydantic import BaseModel, ConfigDict


class Config(BaseModel):
    model_config = ConfigDict(frozen=True, extra='forbid')
    c006_code: Path
    runtime: Path
    probe_manifest: Path
    checkpoint_root: Path
    checkpoint_sha256: dict[str, str]
    input_contrast: Path
    rollout_trace: Path
    rollout_sidecar: Path
    output: Path


COUNTS = {'full_forward': {}, 'backward_vjp': 0, 'adapter_only_calls': 0, 'optimizer_steps': 0}


def count(kind: str) -> None:
    COUNTS['full_forward'][kind] = COUNTS['full_forward'].get(kind, 0) + 1


def main() -> None:
    config = Config.model_validate_json(Path(sys.argv[1]).read_text())
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    sys.path.insert(1, str(config.c006_code))
    import torch
    from runtime_common import RuntimeConfig, setup, load_pipeline
    from training_state import load_cache, condition_from_cache, balanced_loss
    from point_adapter import PointAnchorAdapter
    from point_features import make_null
    from wan_adapter_forward import ForwardInput, adapted_forward
    from signal_common import (CASES, NOISE_SEED, TARGET_SIGMAS, adapter_trace, frame_support, group_support, eta,
                               pair, rms, cosine, token_mask, decompose, tensor_sha, write_json)
    runtime = RuntimeConfig.model_validate_json(config.runtime.read_text())
    setup(runtime)
    manifest = json.loads((runtime.cache_root / 'CACHE_MANIFEST.json').read_text())
    assert manifest['mask_contract'].startswith('white_v1')
    contrast = json.loads(config.input_contrast.read_text())
    states = {}
    for step, sha in config.checkpoint_sha256.items():
        path = config.checkpoint_root / f'checkpoint-{step}.pt'
        assert hashlib.sha256(path.read_bytes()).hexdigest() == sha, f'checkpoint {step} is not the C-009 white checkpoint'
        states[step] = torch.load(path, map_location='cpu', weights_only=True)['adapter']
    grid_points = {p['target_sigma']: p for p in json.loads(config.probe_manifest.read_text())['probe_grid']}
    if '--cpu-only' in sys.argv[2:]:
        print(json.dumps({'status': 'CPU_PASS', 'cuda_initialized': torch.cuda.is_initialized()}))
        return
    config.output.mkdir(parents=True, exist_ok=False)
    tick = time.monotonic()
    pipe = load_pipeline(runtime)
    models = (pipe.dit, pipe.vace)
    dit, vace = models
    backbone = [p for m in models for p in m.parameters()]
    assert all(not p.requires_grad for p in backbone)
    sampled = [p.detach().flatten()[:16].clone() for p in backbone]
    from diffsynth.diffusion.flow_match import FlowMatchScheduler
    from diffsynth.models.wan_video_dit import sinusoidal_embedding_1d
    grid = FlowMatchScheduler('Wan')
    grid.set_timesteps(1000, training=True, shift=5)
    with torch.random.fork_rng(devices=[]):
        adapter = PointAnchorAdapter().to('cuda').eval().requires_grad_(False)

    def load(step: str) -> None:
        adapter.load_state_dict(states[step], strict=True)

    def observed_forward(inputs, adapter_state):
        """adapted_forward(training=False) with read-only taps; same ops, order and dtypes."""
        rec = {'blocks': []}
        with torch.no_grad():
            t = dit.time_embedding(sinusoidal_embedding_1d(dit.freq_dim, inputs.timestep))
            modulation = dit.time_projection(t).unflatten(1, (6, dit.dim))
            context = dit.text_embedding(inputs.context)
            patches = dit.patchify(inputs.latents, None)
            frames, height, width = patches.shape[2:]
            hidden = patches.flatten(2).transpose(1, 2).contiguous()
            freqs = torch.cat([
                dit.freqs[0][:frames].view(frames, 1, 1, -1).expand(frames, height, width, -1),
                dit.freqs[1][:height].view(1, height, 1, -1).expand(frames, height, width, -1),
                dit.freqs[2][:width].view(1, 1, width, -1).expand(frames, height, width, -1),
            ], dim=-1).reshape(frames * height * width, 1, -1).to(hidden.device)
            hints = vace(hidden, inputs.vace_context, context, modulation, freqs,
                         use_gradient_checkpointing=False, use_gradient_checkpointing_offload=False)
            for index in range(26):
                hidden = dit.blocks[index](hidden, context, modulation, freqs)
                if index in vace.vace_layers_mapping:
                    hidden = hidden + hints[vace.vace_layers_mapping[index]]
            motion = None
            if adapter_state is not None:
                ad, condition = adapter_state
                motion = ad(condition, inputs.sigma)
            for index in range(26, 30):
                row = {}
                if adapter_state is not None:
                    h_l = hidden.detach().clone()
                    with torch.autocast(device_type='cuda', enabled=False):
                        r_l = ad.projections[index - 26](motion.float())
                    hidden = ad.residual(motion, index - 26, hidden)
                    row.update(h_l=h_l, r_l=r_l.detach().clone(), r_cast=r_l.to(h_l.dtype), h_plus=hidden.detach().clone())
                hidden = dit.blocks[index](hidden, context, modulation, freqs)
                row['post_block'] = hidden.detach().clone()
                if index in vace.vace_layers_mapping:
                    hidden = hidden + hints[vace.vace_layers_mapping[index]]
                row['post_hint'] = hidden.detach().clone()
                rec['blocks'].append(row)
            rec['pre_head'] = hidden.detach().clone()
            prediction = dit.unpatchify(dit.head(hidden, t), (frames, height, width))
        rec['prediction'] = prediction
        return prediction, rec

    def residual_stats(rec, support):
        out = []
        for row in rec['blocks']:
            h, r, rc, hp = row['h_l'].float(), row['r_l'], row['r_cast'].float(), row['h_plus'].float()
            d_eff = hp - h
            nz = r != 0
            s = support[None, :, None].expand_as(r)
            out.append({
                'hidden_rms': rms(h), 'residual_rms': rms(r), 'residual_over_hidden': rms(r) / rms(h),
                'residual_over_hidden_support': rms(r[s]) / rms(h[s]) if s.any() else None,
                'cast_rel_error': rms(rc - r) / rms(r) if rms(r) > 0 else None,
                'addition_rel_error': rms(d_eff - rc) / rms(rc) if rms(rc) > 0 else None,
                'effective_over_intended': rms(d_eff) / rms(r) if rms(r) > 0 else None,
                'cosine_effective_intended': cosine(d_eff, r),
                'structural_zero_fraction': float((~nz).double().mean()),
                'cast_underflow_fraction_of_nonzero': float(((rc == 0) & nz).double().sum() / nz.double().sum()) if nz.any() else None,
                'unchanged_hidden_fraction_of_nonzero': float(((hp == h) & nz).double().sum() / nz.double().sum()) if nz.any() else None,
                'nonzero_outside_support': bool((nz & ~s).any())})
        return out

    def hidden_pairs(rec_a, rec_b, sup, obj_tok):
        out = {}
        sel = {'all': None, 'support': sup, 'object_tokens': obj_tok, 'background_tokens': ~obj_tok}
        points = [(f'block{26 + i}_{k}', i, k) for i in range(4) for k in ('h_plus', 'post_block', 'post_hint')]
        for label, i, k in points + [('pre_head', None, None)]:
            a = rec_a['pre_head'] if i is None else rec_a['blocks'][i].get(k)
            b = rec_b['pre_head'] if i is None else rec_b['blocks'][i].get(k)
            if a is None or b is None:
                continue
            a, b = a[0].float(), b[0].float()
            out[label] = {name: (pair(a, b) if m is None else (pair(a[m], b[m]) if m.any() else None)) for name, m in sel.items()}
        return out

    def prediction_time(a, b):
        d = (a.double() - b.double())
        return [rms(d[:, :, t]) for t in range(d.shape[2])]

    results = {'cases': {}, 'adapter_only': {}, 'gradients': {}, 'finite_difference': {}, 'rollout': None,
               'non_interference': {}, 'repeat_floor': {}, 'checks': {}}
    probes = {}
    for name, split in CASES:
        item = load_cache(runtime.cache_root / f'{name}.pt', runtime.point_exclusions)
        on = condition_from_cache(item)
        null = make_null(on)
        z0 = item['clean_latent'].to('cuda')
        mask = item['loss_mask'].to('cuda')
        generator = torch.Generator(device='cpu').manual_seed(NOISE_SEED[name])
        noise = torch.randn(z0.shape, generator=generator).to('cuda', dtype=torch.bfloat16)
        trace_on, trace_null = adapter_trace(adapter, on, 0.5), adapter_trace(adapter, null, 0.5)
        sup_on, sup_null = group_support(frame_support(trace_on)), group_support(frame_support(trace_null))
        tm = token_mask(item['loss_mask']).to('cuda')
        probes[name] = dict(item=item, on=on, null=null, z0=z0, mask=mask, noise=noise,
                            sup_union=sup_on | sup_null, sup_inter=sup_on & sup_null, obj_tok=tm >= .5)
        results['cases'][name] = {'split': split, 'noise': tensor_sha(noise), 'support_tokens_on': int(sup_on.sum()),
                                  'support_tokens_null': int(sup_null.sum()), 'support_union': int((sup_on | sup_null).sum()),
                                  'support_intersection': int((sup_on & sup_null).sum()), 'object_tokens': int((tm >= .5).sum()),
                                  'probes': {}}

    def make_inputs(p, target_sigma):
        point = grid_points[target_sigma]
        index = point['index']
        sigma, timepoint = grid.sigmas[index], grid.timesteps[index]
        assert float(sigma) == point['sigma']
        z = grid.add_noise(p['z0'], p['noise'], timepoint)
        target = grid.training_target(p['z0'], p['noise'], timepoint)
        model_t = timepoint.reshape(1).to('cuda', dtype=torch.bfloat16)
        inputs = ForwardInput(z, model_t, p['item']['context'].to('cuda'), p['item']['vace_context'].to('cuda'), sigma)
        meta = {'grid_index': index, 'sigma': float(sigma), 'timestep_fp32': float(timepoint),
                'model_timestep_bf16': float(model_t), 'z_sigma': tensor_sha(z), 'target': tensor_sha(target)}
        return inputs, target, meta

    # ---- Stage B: adapter-only ON/NULL boundaries (72 calls) ----
    for name, _ in CASES:
        p = probes[name]
        for step in ('000', '128', '256'):
            load(step)
            for ts in TARGET_SIGMAS:
                sigma = grid.sigmas[grid_points[ts]['index']]
                with torch.no_grad():
                    tr = {}
                    for label, cond in (('on', p['on']), ('null', p['null'])):
                        tr[label] = adapter_trace(adapter, cond, sigma)
                        assert torch.equal(tr[label]['grouped'], adapter(cond, sigma)), 'diagnostic copy differs'
                        COUNTS['adapter_only_calls'] += 1
                    a, b = tr['on'], tr['null']
                    pts = a['gate'] | b['gate']
                    fs = frame_support(a) | frame_support(b)
                    gs = p['sup_union']
                    row = {'P1_features_gated_points': pair(a['features'], b['features'], pts),
                           'P1_features_all': pair(a['features'], b['features']),
                           'P2_point_features_gated_points': pair(a['point_features'], b['point_features'], pts),
                           'P3_support_frames_tokens': {'on': int(frame_support(a).sum()), 'null': int(frame_support(b).sum()),
                                                        'union': int(fs.sum()), 'intersection': int((frame_support(a) & frame_support(b)).sum())},
                           'P4_splat_all': pair(a['splats'], b['splats']),
                           'P4_splat_support': pair(a['splats'], b['splats'], fs),
                           'P4_eta': eta(a['splats'], b['splats']),
                           'P5_grouped_all': pair(a['grouped'][0], b['grouped'][0]),
                           'P5_grouped_support_union': pair(a['grouped'][0], b['grouped'][0], gs),
                           'P5_grouped_support_intersection': pair(a['grouped'][0], b['grouped'][0], p['sup_inter']),
                           'P5_per_group_diff_rms': [rms(a['grouped'][0].reshape(9, 390, 192)[g] - b['grouped'][0].reshape(9, 390, 192)[g]) for g in range(9)]}
                    for i, proj in enumerate(adapter.projections):
                        ra, rb = proj(a['grouped'][0]), proj(b['grouped'][0])
                        row[f'P6_residual_block{26 + i}_support_union'] = pair(ra, rb, gs)
                        row[f'P6_residual_block{26 + i}_all'] = pair(ra, rb)
                    if step == '000':
                        row['zero_init_projection'] = all(bool((proj.weight == 0).all()) for proj in adapter.projections)
                results['adapter_only'][f'{name}/{step}/{ts}'] = row
    write_json(config.output / 'METRICS.partial.json', results)

    # ---- Stage C: main 12 probes x 7 predictions = 84 ----
    keep = {}
    for name, _ in CASES:
        p = probes[name]
        for ts in TARGET_SIGMAS:
            inputs, target, meta = make_inputs(p, ts)
            entry = {**meta}
            with torch.no_grad():
                v_base = pipe.model_fn(dit=dit, vace=vace, latents=inputs.latents, timestep=inputs.timestep,
                                       context=inputs.context, vace_context=inputs.vace_context, vace_scale=1.0); count('main_native')
                v_bypass = adapted_forward(models, inputs, None); count('main_bypass')
            load('000')
            v_zero, rec_zero = observed_forward(inputs, (adapter, p['on'])); count('main_zero')
            entry['native_bypass'] = {'exact': bool(torch.equal(v_base, v_bypass)), 'max_abs': float((v_base.float() - v_bypass.float()).abs().max()),
                                      'allclose_1e-3': bool(torch.allclose(v_base, v_bypass, atol=1e-3, rtol=1e-3))}
            entry['native_zero'] = {'exact': bool(torch.equal(v_base, v_zero)), 'max_abs': float((v_base.float() - v_zero.float()).abs().max()),
                                    'allclose_1e-3': bool(torch.allclose(v_base, v_zero, atol=1e-3, rtol=1e-3))}
            assert entry['native_bypass']['allclose_1e-3'] and entry['native_zero']['allclose_1e-3']
            del rec_zero
            entry['loss'] = {'BASE': decompose(v_base, v_base, target, p['mask'])['W']['L_A']}
            for step in ('128', '256'):
                load(step)
                v_on, rec_on = observed_forward(inputs, (adapter, p['on'])); count('main_on')
                v_null, rec_null = observed_forward(inputs, (adapter, p['null'])); count('main_null')
                assert torch.isfinite(v_on).all() and torch.isfinite(v_null).all()
                entry[step] = {
                    'residual_on': residual_stats(rec_on, p['sup_union']),
                    'residual_null': residual_stats(rec_null, p['sup_union']),
                    'hidden_on_vs_null': hidden_pairs(rec_on, rec_null, p['sup_union'], p['obj_tok']),
                    'prediction_on_vs_null_rms': rms(v_on.float() - v_null.float()),
                    'prediction_on_vs_base_rms': rms(v_on.float() - v_base.float()),
                    'prediction_base_rms': rms(v_base.float()),
                    'prediction_on_vs_null_per_latent_t': prediction_time(v_on, v_null),
                    'ON_vs_BASE': decompose(v_on, v_base, target, p['mask']),
                    'NULL_vs_BASE': decompose(v_null, v_base, target, p['mask']),
                    'ON_vs_NULL': decompose(v_on, v_null, target, p['mask'])}
                if step == '256' and ts == 0.5 and name in ('bear', 'elephant'):
                    keep[name] = {'on': v_on.detach().clone(), 'null': v_null.detach().clone(), 'inputs': inputs, 'target': target}
                del rec_on, rec_null
            results['cases'][name]['probes'][str(ts)] = entry
            torch.cuda.empty_cache()
            write_json(config.output / 'METRICS.partial.json', results)

    # ---- Observer non-interference (4) and same-path repeat floor (2) ----
    load('256')
    for name in ('bear', 'elephant'):
        k = keep[name]
        for label in ('on', 'null'):
            with torch.no_grad():
                plain = adapted_forward(models, k['inputs'], (adapter, probes[name][label])); count('observer_off')
            results['non_interference'][f'{name}/{label}'] = {'exact': bool(torch.equal(plain, k[label])),
                                                               'max_abs': float((plain.float() - k[label].float()).abs().max())}
        again, _ = observed_forward(k['inputs'], (adapter, probes[name]['on'])); count('repeat')
        results['repeat_floor'][name] = {'exact': bool(torch.equal(again, k['on'])), 'diff_rms': rms(again.float() - k['on'].float())}
        del _

    # ---- Stage D: parameter gradients, ckpt256, sigma 0.50/0.05, ON/NULL (16 + 16 VJP) ----
    before = {k: v.clone() for k, v in states['256'].items()}
    grad_adapter = PointAnchorAdapter().to('cuda')
    grad_adapter.load_state_dict(states['256'], strict=True)
    groups = {'patches': (0, 288), 'anchor_valid': (288, 290), 'q': (290, 292), 'delta_q': (292, 294),
              'endpoint_offsets': (294, 298), 'time': (298, 299), 'visible_valid': (299, 301),
              'motion_bit': (301, 302), 'sigma': (302, 303)}
    for name, _ in CASES:
        p = probes[name]
        for ts in (0.50, 0.05):
            inputs, target, meta = make_inputs(p, ts)
            grads = {}
            for label in ('on', 'null'):
                captured = {}
                def keep_motion(module, args, out, captured=captured):
                    out.retain_grad()
                    captured['motion'] = out  # returns None: output unchanged
                handle = grad_adapter.register_forward_hook(keep_motion)
                pred = adapted_forward(models, inputs, (grad_adapter, p[label]), training=True); count('gradient_forward')
                handle.remove()
                loss = balanced_loss(pred, target, p['mask'])
                loss.backward(); COUNTS['backward_vjp'] += 1
                assert all(prm.grad is None for prm in backbone)
                g = {k: prm.grad.detach().clone() for k, prm in grad_adapter.named_parameters()}
                motion_grad = captured['motion'].grad.detach()[0]
                feats = adapter_trace(grad_adapter, p[label], inputs.sigma)['features'].detach()
                gate = adapter_trace(grad_adapter, p[label], inputs.sigma)['gate']
                COUNTS['adapter_only_calls'] += 2
                w0 = g['mlp.0.weight']
                grads[label] = {
                    'loss': float(loss), 'g': g, 'motion_grad': motion_grad,
                    'params': {k: {'norm': float(v.double().norm()), 'rms': rms(v),
                                   'rms_grad_times_param': rms(v.double() * dict(grad_adapter.named_parameters())[k].detach().double())}
                               for k, v in g.items()},
                    'first_linear_columns': {gname: {'dims': hi - lo, 'grad_norm': float(w0[:, lo:hi].double().norm()),
                                                     'grad_rms_per_element': rms(w0[:, lo:hi]),
                                                     'input_rms_gated_points': rms(feats[gate][:, lo:hi]) if gate.any() else None}
                                             for gname, (lo, hi) in groups.items()},
                    'motion_grad_rms_support': rms(motion_grad[p['sup_union']]),
                    'motion_grad_rms_outside': rms(motion_grad[~p['sup_union']])}
                ref = results['cases'][name]['probes'][str(ts)]['256']
                grads[label]['prediction_vs_main_loss_abs_diff'] = abs(float(loss) - (ref['ON_vs_BASE' if label == 'on' else 'NULL_vs_BASE']['W']['L_A']))
                grad_adapter.zero_grad(set_to_none=True)
                del pred, loss
            results['gradients'][f'{name}/{ts}'] = {
                label: {k: v for k, v in grads[label].items() if k not in ('g', 'motion_grad')} for label in ('on', 'null')}
            results['gradients'][f'{name}/{ts}']['on_null_cosine'] = {k: cosine(grads['on']['g'][k], grads['null']['g'][k]) for k in grads['on']['g']}
            results['gradients'][f'{name}/{ts}']['motion_grad_on_null_cosine_support'] = cosine(
                grads['on']['motion_grad'][p['sup_union']], grads['null']['motion_grad'][p['sup_union']])
            del grads
    results['checks']['gradient_parameters_unchanged'] = all(torch.equal(grad_adapter.state_dict()[k].cpu(), v) for k, v in before.items())
    results['checks']['backbone_samples_unchanged'] = all(torch.equal(prm.detach().flatten()[:16], s) for prm, s in zip(backbone, sampled))
    del grad_adapter

    # ---- Stage E: coordinate finite differences, ckpt256 ON, sigma 0.50 ----
    load('256')
    for name, _ in CASES:
        track = contrast[name]['fd_track']
        if track is None:
            results['finite_difference'][name] = 'FD_NOT_AVAILABLE'
            continue
        p = probes[name]
        inputs, target, meta = make_inputs(p, 0.50)
        base_trace = adapter_trace(adapter, p['on'], inputs.sigma)
        tvec = torch.arange(33, device='cuda', dtype=torch.float32)
        bump = torch.sin(math.pi * tvec / 32) ** 2
        bump[0] = 0.0; bump[32] = 0.0
        gated = base_trace['gate'][:, track]
        row = {'track': track, 'gated_frames': int(gated.sum())}
        preds, traces = {}, {}
        for eps in (4, 8):
            for sign in (1, -1):
                q = p['on'].positions.clone()
                q[:, track, 0] = q[:, track, 0] + sign * (eps / 416) * bump
                if not bool(((q[:, track] >= 0) & (q[:, track] <= 1)).all(-1)[gated].all()):
                    row[f'{eps}px_{sign:+d}'] = 'OUT_OF_RANGE_INVALID'
                    continue
                cond = replace(p['on'], positions=q)
                with torch.no_grad():
                    traces[eps, sign] = adapter_trace(adapter, cond, inputs.sigma); COUNTS['adapter_only_calls'] += 1
                    preds[eps, sign] = adapted_forward(models, inputs, (adapter, cond)); count('finite_difference')
                row[f'{eps}px_{sign:+d}_gate_changed'] = bool(not torch.equal(traces[eps, sign]['gate'], base_trace['gate']))
                row[f'{eps}px_{sign:+d}_support_changed'] = bool(not torch.equal(frame_support(traces[eps, sign]), frame_support(base_trace)))
        diffs = {}
        for eps in (4, 8):
            if (eps, 1) in preds and (eps, -1) in preds:
                d = (preds[eps, 1].double() - preds[eps, -1].double()) / (2 * eps)
                diffs[eps] = d
                w = decompose(preds[eps, 1], preds[eps, -1], target, p['mask'])
                row[f'D{eps}'] = {'rms_velocity_per_px': rms(d), 'object_rms_per_px': math.sqrt(max(w['obj']['delta_sq'], 0)) / (2 * eps),
                                  'background_rms_per_px': math.sqrt(max(w['bg']['delta_sq'], 0)) / (2 * eps),
                                  'plus_minus_pred_diff_rms': rms(preds[eps, 1].float() - preds[eps, -1].float()),
                                  'grouped_context_diff_rms': rms(traces[eps, 1]['grouped'] - traces[eps, -1]['grouped']),
                                  'residual256_block26_diff_rms': rms(adapter.projections[0](traces[eps, 1]['grouped'][0]) - adapter.projections[0](traces[eps, -1]['grouped'][0]))}
        if 4 in diffs and 8 in diffs:
            row['D4_D8_cosine'] = cosine(diffs[4], diffs[8])
            row['D8_over_D4_rms'] = rms(diffs[8]) / rms(diffs[4]) if rms(diffs[4]) > 0 else None
        floor = results['repeat_floor'].get(name)
        row['repeat_floor_diff_rms'] = floor['diff_rms'] if floor else None
        row['on_vs_null_pred_rms_same_probe'] = results['cases'][name]['probes']['0.5']['256']['prediction_on_vs_null_rms']
        results['finite_difference'][name] = row
        del preds, traces

    # ---- Optional: stored C-009 NEW_ON_5 rollout states (<= 9) ----
    steps = sorted(config.rollout_trace.glob('step-*.pt'))
    contexts = torch.load(config.rollout_trace / 'contexts.pt', map_location='cpu', weights_only=True)
    if steps and 'vace_context' in contexts:
        stored = {s.stem: torch.load(s, map_location='cpu', weights_only=True) for s in steps}
        side = load_cache(config.rollout_sidecar, runtime.point_exclusions)
        r_on = condition_from_cache(side)
        r_null = make_null(r_on)
        elephant_mask = probes['elephant']['mask']
        rollout = {'source': 'C-009 NEW_ON_5 (white checkpoint-256, CFG5) pre-step latents', 'states': {}}
        assert torch.equal(contexts['vace_context'], probes['elephant']['item']['vace_context'])
        for ts in TARGET_SIGMAS:
            key = min(stored, key=lambda k: abs(stored[k]['sigma'] - ts))
            if key in rollout['states']:
                continue
            s = stored[key]
            inputs = ForwardInput(s['latent'].to('cuda'), s['model_timestep'].to('cuda'), contexts['positive'].to('cuda'),
                                  contexts['vace_context'].to('cuda'), torch.tensor(s['sigma']))
            with torch.no_grad():
                vb = pipe.model_fn(dit=dit, vace=vace, latents=inputs.latents, timestep=inputs.timestep, context=inputs.context,
                                   vace_context=inputs.vace_context, vace_scale=1.0); count('rollout')
                vo = adapted_forward(models, inputs, (adapter, r_on)); count('rollout')
                vn = adapted_forward(models, inputs, (adapter, r_null)); count('rollout')
            zero = torch.zeros_like(vb)
            rollout['states'][key] = {'target_sigma': ts, 'sigma': s['sigma'], 'timestep': s['timestep'],
                'pre_step_latent': True, 'base_rms': rms(vb.float()),
                'on_minus_base_rms': rms(vo.float() - vb.float()), 'on_minus_null_rms': rms(vo.float() - vn.float()),
                'on_minus_base_obj_bg': {k: v['delta_sq'] for k, v in decompose(vo, vb, zero, elephant_mask).items()},
                'on_minus_null_obj_bg': {k: v['delta_sq'] for k, v in decompose(vo, vn, zero, elephant_mask).items()}}
        results['rollout'] = rollout
    else:
        results['rollout'] = 'ROLLOUT_NOT_AVAILABLE'

    results['counts'] = {**COUNTS, 'full_forward_total': sum(COUNTS['full_forward'].values())}
    results['checks']['backbone_samples_unchanged_end'] = all(torch.equal(prm.detach().flatten()[:16], s) for prm, s in zip(backbone, sampled))
    results['elapsed_seconds'] = time.monotonic() - tick
    write_json(config.output / 'METRICS.json', results)
    print(json.dumps({'status': 'COMPLETE', **results['counts']}))


if __name__ == '__main__':
    main()
