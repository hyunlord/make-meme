# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Bounded actual FM training, existing research Python; no full-pipeline no_grad wrapper."""
from pathlib import Path
import json
import sys
import time
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from runtime_common import parse_config, setup, load_pipeline, atomic_json, tensor_summary
from point_adapter import PointAnchorAdapter
from point_features import make_null
from training_state import condition_from_cache, balanced_loss, save_checkpoint, load_cache
from wan_adapter_forward import ForwardInput, adapted_forward


def main() -> None:
    config = parse_config()
    setup(config)
    clips = json.loads(config.split_manifest.read_text())['clips']
    train = [row['sequence'] for row in clips if row['split'] == 'train']
    validation = [row['sequence'] for row in clips if row['split'] == 'validation']
    assert len(train) >= 4 and len(validation) >= 1
    assert 1 <= config.max_updates <= 256 and config.train_seconds <= 9000
    assert config.point_exclusions is not None and config.point_exclusions.is_file()
    for name in train + validation:
        data = torch.load(config.cache_root / f'{name}.pt', map_location='cpu', weights_only=True)
        assert data['clean_latent'].shape == (1, 16, 9, 30, 52)
    if '--cpu-only' in sys.argv:
        print(json.dumps({'status': 'CPU_PASS', 'train': train, 'validation': validation,
                          'cuda_initialized': torch.cuda.is_initialized()}))
        return
    config.output.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    pipe = load_pipeline(config)
    models = (pipe.dit, pipe.vace)
    pipe.scheduler.set_timesteps(1000, training=True, shift=5)
    torch.manual_seed(config.train_seed)
    adapter = PointAnchorAdapter().to('cuda')
    optimizer = torch.optim.AdamW(adapter.parameters(), lr=1e-4, betas=(.9, .999), weight_decay=.01)
    assert sum(p.numel() for p in adapter.parameters()) <= 3_000_000
    assert {id(p) for group in optimizer.param_groups for p in group['params']} == {id(p) for p in adapter.parameters()}
    base = [parameter for model in models for parameter in model.parameters()]
    assert all(not parameter.requires_grad for parameter in base)
    versions = [parameter._version for parameter in base]
    sampled = [parameter.detach().flatten()[:16].clone() for parameter in base]
    generator = torch.Generator(device='cpu').manual_seed(config.train_seed)
    order = torch.randperm(len(train), generator=generator).tolist()
    cursor = 0
    counts = {'training_forwards': 0, 'backwards': 0, 'updates': 0, 'validation_forwards': 0, 'diagnostic_forwards': 0}
    cache = {name: load_cache(config.cache_root / f'{name}.pt', config.point_exclusions) for name in train + validation}

    def checkpoint_state(step: int) -> dict:
        return {'completed_updates': step, 'order': order, 'cursor': cursor,
                'generator_state': generator.get_state(), 'config': config.model_dump(mode='json'),
                'counts': counts.copy(), 'active_seconds': time.monotonic()-active_start}

    def evaluate(step: int) -> None:
        rows = []
        with torch.no_grad():
            for clip_index, name in enumerate(validation):
                item = cache[name]
                z0 = item['clean_latent'].to('cuda')
                condition = condition_from_cache(item)
                for index in (200, 500, 800):
                    probe = torch.Generator(device='cpu').manual_seed(20261031 + clip_index*1000 + index)
                    noise = torch.randn(z0.shape, generator=probe).to('cuda', dtype=torch.bfloat16)
                    timestep = pipe.scheduler.timesteps[index]
                    latent = pipe.scheduler.add_noise(z0, noise, timestep)
                    inputs = ForwardInput(latent, timestep.reshape(1).to('cuda', dtype=torch.bfloat16),
                        item['context'].to('cuda'), item['vace_context'].to('cuda'), pipe.scheduler.sigmas[index])
                    prediction = adapted_forward(models, inputs, (adapter, condition))
                    target = pipe.scheduler.training_target(z0, noise, timestep)
                    loss = balanced_loss(prediction, target, item['loss_mask'].to('cuda'))
                    counts['validation_forwards'] += 1
                    rows.append({'clip': name, 'grid_index': index, 'sigma': float(pipe.scheduler.sigmas[index]), 'loss': float(loss)})
        atomic_json(config.output / f'validation-{step:03d}.json', rows)

    active_start = time.monotonic()
    save_checkpoint(config.output / 'checkpoint-000.pt', adapter, optimizer, checkpoint_state(0))
    evaluate(0)
    first_diagnostic = None
    for step in range(1, config.max_updates+1):
        if time.monotonic()-active_start >= config.train_seconds or time.time() >= config.deadline_epoch-600:
            break
        tick = time.monotonic()
        name = train[order[cursor]]
        cursor += 1
        if cursor == len(order):
            cursor = 0
            order = torch.randperm(len(train), generator=generator).tolist()
        item = cache[name]
        z0 = item['clean_latent'].to('cuda')
        noise = torch.randn(z0.shape, generator=generator).to('cuda', dtype=torch.bfloat16)
        index = int(torch.randint(0, 1000, (), generator=generator))
        null = bool(torch.rand((), generator=generator) < .25)
        negative = bool(torch.rand((), generator=generator) < .10)
        condition = condition_from_cache(item)
        if null:
            condition = make_null(condition)
        timestep = pipe.scheduler.timesteps[index]
        latent = pipe.scheduler.add_noise(z0, noise, timestep)
        inputs = ForwardInput(latent, timestep.reshape(1).to('cuda', dtype=torch.bfloat16),
            item['negative_context' if negative else 'context'].to('cuda'),
            item['vace_context'].to('cuda'), pipe.scheduler.sigmas[index])
        target = pipe.scheduler.training_target(z0, noise, timestep)
        torch.cuda.reset_peak_memory_stats()
        if step == 1:
            with torch.no_grad():
                native = pipe.model_fn(dit=pipe.dit, vace=pipe.vace, latents=inputs.latents,
                    timestep=inputs.timestep, context=inputs.context, vace_context=inputs.vace_context, vace_scale=1.0)
                bypass = adapted_forward(models, inputs, None)
                zero = adapted_forward(models, inputs, (adapter, condition))
                counts['diagnostic_forwards'] += 3
                assert torch.allclose(native, bypass, atol=1e-3, rtol=1e-3)
                assert torch.allclose(native, zero, atol=1e-3, rtol=1e-3)
                first_diagnostic = {'native_bypass_max_abs': float((native-bypass).abs().max()),
                    'native_zero_max_abs': float((native-zero).abs().max()), 'atol': 1e-3, 'rtol': 1e-3}
        graph_inputs = {}
        handles = []
        if step == 1:
            def retain_input(label):
                def observe(module, args):
                    if label not in graph_inputs:
                        assert args[0].requires_grad
                        args[0].retain_grad()
                        graph_inputs[label] = args[0]
                return observe
            for block_index in range(26, 30):
                handles.append(pipe.dit.blocks[block_index].register_forward_pre_hook(retain_input(f'block_{block_index}')))
            handles.append(pipe.dit.head.register_forward_pre_hook(retain_input('head')))
        optimizer.zero_grad(set_to_none=True)
        prediction = adapted_forward(models, inputs, (adapter, condition), training=True)
        counts['training_forwards'] += 1
        assert prediction.requires_grad
        loss = balanced_loss(prediction, target, item['loss_mask'].to('cuda'))
        assert torch.isfinite(loss)
        loss.backward()
        counts['backwards'] += 1
        if step == 1:
            graph_gradient = {key: float(value.grad.float().norm()) for key, value in graph_inputs.items()}
            assert len(graph_gradient) == 5 and all(value > 0 for value in graph_gradient.values())
            first_diagnostic['late_block_and_head_input_gradient_norms'] = graph_gradient
            for handle in handles:
                handle.remove()
        gradients = {key: float(parameter.grad.float().norm()) for key, parameter in adapter.named_parameters() if parameter.grad is not None}
        assert all(torch.isfinite(parameter.grad).all() for parameter in adapter.parameters() if parameter.grad is not None)
        assert all(parameter.grad is None and parameter._version == version for parameter, version in zip(base, versions))
        assert sum(value for key, value in gradients.items() if key.startswith('projections')) > 0
        if step == 1:
            assert sum(value for key, value in gradients.items() if key.startswith('mlp')) == 0
        if step == 2:
            assert sum(value for key, value in gradients.items() if key.startswith('mlp')) > 0
        grad_norm = torch.nn.utils.clip_grad_norm_(adapter.parameters(), 1.0)
        optimizer.step()
        counts['updates'] += 1
        torch.cuda.synchronize()
        row = {'step': step, 'clip': name, 'grid_index': index, 'sigma': float(inputs.sigma),
               'null': null, 'negative_text': negative, 'loss': float(loss.detach()),
               'grad_norm': float(grad_norm), 'gradients': gradients if step <= 2 else None,
               'seconds': time.monotonic()-tick, 'cuda_peak_allocated': torch.cuda.max_memory_allocated(),
               'cuda_peak_reserved': torch.cuda.max_memory_reserved()}
        with (config.output / 'updates.jsonl').open('a') as stream:
            stream.write(json.dumps(row)+'\n')
        atomic_json(config.output / 'progress.json', {**counts, 'active_seconds': time.monotonic()-active_start})
        if step in (128, 256):
            save_checkpoint(config.output / f'checkpoint-{step:03d}.pt', adapter, optimizer, checkpoint_state(step))
            evaluate(step)
        print(json.dumps({'step': step, 'loss': row['loss'], 'seconds': row['seconds']}), flush=True)
    completed = counts['updates']
    assert completed > 0
    final_path = config.output / f'checkpoint-{completed:03d}.pt'
    receipt = save_checkpoint(final_path, adapter, optimizer, checkpoint_state(completed))
    if completed not in (128, 256):
        evaluate(completed)
    with torch.no_grad():
        before = adapted_forward(models, inputs, (adapter, condition))
        restored = torch.load(final_path, map_location='cpu', weights_only=True)
        fresh = PointAnchorAdapter().to('cuda')
        fresh.load_state_dict(restored['adapter'], strict=True)
        after = adapted_forward(models, inputs, (fresh, condition))
        counts['diagnostic_forwards'] += 2
        assert torch.allclose(before, after, atol=1e-3, rtol=1e-3)
        assert all(torch.equal(parameter.detach().flatten()[:16], value) for parameter, value in zip(base, sampled))
    atomic_json(config.output / 'result.json', {'status': 'TRAIN_COMPLETE' if completed == 256 else 'UNDER_TRAINED',
        **counts, 'checkpoint': final_path.name, 'checkpoint_readback': receipt,
        'gradient_connected': True, 'base_versions_and_samples_unchanged': True,
        'reloaded_prediction_max_abs': float((before-after).abs().max()), 'initial': first_diagnostic,
        'active_seconds': time.monotonic()-active_start, 'elapsed_seconds': time.monotonic()-started,
        'final_adapter': {key: tensor_summary(value) for key, value in adapter.state_dict().items()}})


if __name__ == '__main__':
    main()
