# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# Run with existing research Python: train_capability.py /abs/config.json [--cpu-only]
"""C-012 TRAIN_PAIR_MEMORIZATION / CAPABILITY_TEST of the unchanged PointAnchorAdapter.

Same adapter, injection, kernel, grouping, optimizer, loss and Wan shift5 1000-step grid as C-006.
Intentional changes for the capability test only: data = the two clips A/B, NULL dropout 0,
negative-text dropout 0, up to 2048 updates. Run as segments (0->256->1024->2048); each segment
resumes the exact adapter/optimizer/generator/order/cursor/RNG state and ends with a checkpoint and
8 auxiliary probe forwards (sigma 1.0/0.95/0.50/0.05 x point A/B on one shared noise).
"""
from pathlib import Path
import hashlib
import json
import os
import sys
import time

from pydantic import BaseModel, ConfigDict

CLIPS = ('path_A', 'path_B')
SEGMENTS = (256, 1024, 2048)


class Config(BaseModel):
    model_config = ConfigDict(frozen=True, extra='forbid')
    upstream: Path
    weights: Path
    cache_root: Path
    output: Path
    init_checkpoint: Path          # C-006 step000 (same structure, zero projections)
    resume: Path | None = None     # previous C-012 segment checkpoint
    stop_at: int
    train_seed: int = 20261104
    probe_seed: int = 20261105
    total_train_seconds: int = 5400
    deadline_epoch: float


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    config = Config.model_validate_json(Path(sys.argv[1]).read_text())
    assert config.stop_at in SEGMENTS
    sys.path.insert(0, str(Path(__file__).resolve().parent / 'gen'))
    manifest = json.loads((config.cache_root / 'CACHE_MANIFEST.json').read_text())
    assert manifest['mask_contract'].startswith('white_v1') and manifest['condition_family'] == 'endpoint_gray127_v1'
    for clip in CLIPS:
        name = f'{clip}.train.pt'
        assert digest((config.cache_root / name).read_bytes()) == manifest['files'][name], name
    os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', TOKENIZERS_PARALLELISM='false')
    sys.path.insert(0, str(config.upstream))
    import torch
    from point_adapter import PointAnchorAdapter
    from training_state import condition_from_cache, balanced_loss, save_checkpoint
    from wan_adapter_forward import ForwardInput, adapted_forward
    from runtime_common import tensor_summary
    cache = {c: torch.load(config.cache_root / f'{c}.train.pt', map_location='cpu', weights_only=True) for c in CLIPS}
    a, b = cache['path_A'], cache['path_B']
    for key in ('vace_context', 'context', 'patches', 'anchor_valid', 'visible', 'valid', 'box_wh'):
        assert torch.equal(a[key], b[key]), key
    assert not torch.equal(a['positions'], b['positions'])
    if '--cpu-only' in sys.argv[2:]:
        print(json.dumps({'status': 'CPU_PASS', 'stop_at': config.stop_at, 'resume': str(config.resume),
                          'cuda_initialized': torch.cuda.is_initialized()}))
        return
    config.output.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    from diffsynth.models import wan_video_dit
    for flag in ('FLASH_ATTN_3_AVAILABLE', 'FLASH_ATTN_2_AVAILABLE', 'SAGE_ATTN_AVAILABLE'):
        setattr(wan_video_dit, flag, False)
    from diffsynth.pipelines.wan_video import WanVideoPipeline, ModelConfig
    pipe = WanVideoPipeline.from_pretrained(torch_dtype=torch.bfloat16, device='cuda',
        model_configs=[ModelConfig(path=str(config.weights / 'diffusion_pytorch_model.safetensors'), skip_download=True)],
        tokenizer_config=ModelConfig(path=str(config.weights / 'google/umt5-xxl'), skip_download=True))
    for module in (pipe.dit, pipe.vace):
        module.eval().requires_grad_(False)
    models = (pipe.dit, pipe.vace)
    pipe.scheduler.set_timesteps(1000, training=True, shift=5)
    base = [p for m in models for p in m.parameters()]
    versions = [p._version for p in base]
    sampled = [p.detach().flatten()[:16].clone() for p in base]
    adapter = PointAnchorAdapter().to('cuda')
    optimizer = torch.optim.AdamW(adapter.parameters(), lr=1e-4, betas=(.9, .999), weight_decay=.01)
    if config.resume is None:
        init = torch.load(config.init_checkpoint, map_location='cpu', weights_only=True)
        adapter.load_state_dict(init['adapter'], strict=True)          # step000 values only; no optimizer/RNG/cursor
        assert all(float(p.abs().max()) == 0 for p in adapter.projections.parameters())
        generator = torch.Generator(device='cpu').manual_seed(config.train_seed)
        torch.manual_seed(config.train_seed)
        torch.cuda.manual_seed_all(config.train_seed)
        order, cursor, done, prior_active = torch.randperm(2, generator=generator).tolist(), 0, 0, 0.0
        counts = {'training_forwards': 0, 'backwards': 0, 'updates': 0, 'diagnostic_forwards': 0, 'probe_forwards': 0}
        origin = {'init_checkpoint_sha256': digest(config.init_checkpoint.read_bytes()), 'fresh_optimizer_rng_cursor': True}
    else:
        state = torch.load(config.resume, map_location='cpu', weights_only=True)
        adapter.load_state_dict(state['adapter'], strict=True)
        optimizer.load_state_dict(state['optimizer'])
        generator = torch.Generator(device='cpu'); generator.set_state(state['generator_state'])
        order, cursor, done = state['order'], state['cursor'], state['completed_updates']
        counts, prior_active = state['counts'].copy(), state['active_seconds']
        torch.set_rng_state(state['cpu_rng']); torch.cuda.set_rng_state_all(state['cuda_rng'])
        origin = {'resume_sha256': digest(config.resume.read_bytes()), 'resumed_updates': done}
    assert done < config.stop_at
    active_start = time.monotonic() - prior_active
    condition = {c: condition_from_cache(cache[c]) for c in CLIPS}

    def state_for(step: int) -> dict:
        return {'completed_updates': step, 'order': order, 'cursor': cursor, 'generator_state': generator.get_state(),
                'config': config.model_dump(mode='json'), 'counts': counts.copy(),
                'active_seconds': time.monotonic() - active_start}

    if done == 0:
        save_checkpoint(config.output / 'checkpoint-0000.pt', adapter, optimizer, state_for(0))
    rows, first = [], None
    stopped = 'stop_at'
    for step in range(done + 1, config.stop_at + 1):
        if time.monotonic() - active_start >= config.total_train_seconds:
            stopped = 'train_wall_clock_cap'; break
        if time.time() >= config.deadline_epoch - 600:
            stopped = 'stage_deadline'; break
        tick = time.monotonic()
        name = CLIPS[order[cursor]]
        cursor += 1
        if cursor == len(order):
            cursor, order = 0, torch.randperm(2, generator=generator).tolist()
        item = cache[name]
        z0 = item['clean_latent'].to('cuda')
        noise = torch.randn(z0.shape, generator=generator).to('cuda', dtype=torch.bfloat16)
        index = int(torch.randint(0, 1000, (), generator=generator))
        timestep = pipe.scheduler.timesteps[index]
        inputs = ForwardInput(pipe.scheduler.add_noise(z0, noise, timestep), timestep.reshape(1).to('cuda', dtype=torch.bfloat16),
                              item['context'].to('cuda'), item['vace_context'].to('cuda'), pipe.scheduler.sigmas[index])
        target = pipe.scheduler.training_target(z0, noise, timestep)
        if step == 1:
            with torch.no_grad():
                native = pipe.model_fn(dit=pipe.dit, vace=pipe.vace, latents=inputs.latents, timestep=inputs.timestep,
                                       context=inputs.context, vace_context=inputs.vace_context, vace_scale=1.0)
                bypass = adapted_forward(models, inputs, None)
                zero = adapted_forward(models, inputs, (adapter, condition[name]))
                counts['diagnostic_forwards'] += 3
                assert torch.allclose(native, bypass, atol=1e-3, rtol=1e-3) and torch.allclose(native, zero, atol=1e-3, rtol=1e-3)
                first = {'native_bypass_max_abs': float((native - bypass).abs().max()), 'native_zero_max_abs': float((native - zero).abs().max())}
        optimizer.zero_grad(set_to_none=True)
        prediction = adapted_forward(models, inputs, (adapter, condition[name]), training=True)
        counts['training_forwards'] += 1
        loss = balanced_loss(prediction, target, item['loss_mask'].to('cuda'))
        assert torch.isfinite(loss)
        loss.backward()
        counts['backwards'] += 1
        assert all(p.grad is None and p._version == v for p, v in zip(base, versions))
        grad_norm = torch.nn.utils.clip_grad_norm_(adapter.parameters(), 1.0)
        optimizer.step()
        counts['updates'] += 1
        row = {'step': step, 'clip': name, 'grid_index': index, 'sigma': float(inputs.sigma), 'loss': float(loss.detach()),
               'grad_norm': float(grad_norm), 'seconds': time.monotonic() - tick}
        rows.append(row)
        with (config.output / 'updates.jsonl').open('a') as stream:
            stream.write(json.dumps(row) + '\n')
        if step % 32 == 0:
            print(json.dumps({'step': step, 'loss': row['loss'], 'active': time.monotonic() - active_start}), flush=True)
    completed = counts['updates']
    path = config.output / f'checkpoint-{completed:04d}.pt'
    receipt = save_checkpoint(path, adapter, optimizer, state_for(completed))
    probes = []
    with torch.no_grad():
        sigmas = pipe.scheduler.sigmas
        z = {c: cache[c]['clean_latent'].to('cuda') for c in CLIPS}
        noise = torch.randn(z['path_A'].shape, generator=torch.Generator(device='cpu').manual_seed(config.probe_seed)).to('cuda', dtype=torch.bfloat16)
        for want in (1.0, 0.95, 0.50, 0.05):
            index = int((sigmas - want).abs().argmin())
            pred, tgt, lat = {}, {}, {}
            for c in CLIPS:
                lat[c] = pipe.scheduler.add_noise(z[c], noise, pipe.scheduler.timesteps[index])
                inputs = ForwardInput(lat[c], pipe.scheduler.timesteps[index].reshape(1).to('cuda', dtype=torch.bfloat16),
                                      cache[c]['context'].to('cuda'), cache[c]['vace_context'].to('cuda'), sigmas[index])
                pred[c] = adapted_forward(models, inputs, (adapter, condition[c])).float()
                tgt[c] = pipe.scheduler.training_target(z[c], noise, pipe.scheduler.timesteps[index]).float()
                counts['probe_forwards'] += 1
            delta, wanted = pred['path_A'] - pred['path_B'], tgt['path_A'] - tgt['path_B']
            mask = cache['path_A']['loss_mask'].to('cuda')
            probes.append({'sigma_requested': want, 'grid_index': index, 'sigma': float(sigmas[index]),
                           'same_input_state': bool(torch.equal(lat['path_A'], lat['path_B'])),
                           'cos_delta_target_delta': float(torch.nn.functional.cosine_similarity(delta.flatten(), wanted.flatten(), dim=0)),
                           'delta_norm': float(delta.norm()), 'target_delta_norm': float(wanted.norm()),
                           'loss_A_matched': float(balanced_loss(pred['path_A'], tgt['path_A'], mask)),
                           'loss_A_swapped': float(balanced_loss(pred['path_A'], tgt['path_B'], cache['path_B']['loss_mask'].to('cuda'))),
                           'loss_B_matched': float(balanced_loss(pred['path_B'], tgt['path_B'], cache['path_B']['loss_mask'].to('cuda'))),
                           'loss_B_swapped': float(balanced_loss(pred['path_B'], tgt['path_A'], mask))})
    assert all(torch.equal(p.detach().flatten()[:16], v) for p, v in zip(base, sampled))
    result = {'status': 'SEGMENT_COMPLETE' if completed == config.stop_at else 'SEGMENT_STOPPED', 'stopped_by': stopped,
              **counts, 'checkpoint': path.name, 'checkpoint_sha256': digest(path.read_bytes()), 'readback': receipt,
              'origin': origin, 'initial_diagnostic': first, 'probes': probes,
              'mean_loss_last_64': sum(r['loss'] for r in rows[-64:]) / max(1, len(rows[-64:])),
              'active_seconds_total': time.monotonic() - active_start, 'elapsed_seconds': time.monotonic() - started,
              'cuda_peak_allocated': torch.cuda.max_memory_allocated(), 'backbone_unchanged': True,
              'null_dropout': 0.0, 'negative_text_dropout': 0.0,
              'final_adapter': {k: tensor_summary(v) for k, v in adapter.state_dict().items()}}
    (config.output / 'result.json').write_text(json.dumps(result, indent=2))
    print(json.dumps({k: result[k] for k in ('status', 'updates', 'checkpoint', 'active_seconds_total')}))


if __name__ == '__main__':
    main()
