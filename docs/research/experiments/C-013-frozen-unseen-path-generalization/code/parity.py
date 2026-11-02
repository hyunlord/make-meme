# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# Run: existing-python parity.py PARENT_ROOT NEW_ROOT RUN_ID
"""Compare existing input receipts without model imports or additional forwards."""
from pathlib import Path
import hashlib
import json
import sys


def main() -> None:
    parent, root, name = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
    output = root / 'outputs' / name
    reference = parent / 'outputs' / ('ON2048_S2_A' if name == 'BASE_S2' else 'ON2048_A')
    read = lambda folder, file: json.loads((folder / file).read_text())
    actual, expected = read(output, 'first-model-input.json'), read(reference, 'first-model-input.json')
    for key in ('latents', 'vace_context', 'vace_mask_context'):
        assert actual[key] == expected[key], key
    assert actual['vace_context']['sha256'] == '2c7a6691c209d2b3a9465f9dcbd9866721f0af8f77db68724ada79325eabbf2d'
    a, b = read(output, 'condition.json'), read(reference, 'condition.json')
    assert a == b, 'RGB and full three-channel G receipts must agree'
    for folder in ('condition', 'mask'):
        for t in range(33):
            assert (output / folder / f'{t:03d}.png').read_bytes() == (reference / folder / f'{t:03d}.png').read_bytes()
    trace = [json.loads(line) for line in (output / 'ROLLOUT_STATS.jsonl').read_text().splitlines()]
    prior = [json.loads(line) for line in (reference / 'ROLLOUT_STATS.jsonl').read_text().splitlines()]
    assert len(trace) == len(prior) == 50
    for a, b in zip(trace, prior, strict=True):
        for key in ('sampler_step', 'sigma', 'next_sigma', 'timestep', 'model_timestep_bf16', 'effective_cfg', 'context_hashes'):
            assert a[key] == b[key], key
    point = None
    if name != 'BASE_S2':
        point, old = read(output, 'point-model-input.json'), read(reference, 'point-model-input.json')
        for key in ('valid', 'visible', 'endpoint_patches', 'source_motion_available', 'adapter_checkpoint_sha256'):
            assert point[key] == old[key], key
        assert point['positions']['sha256'] != old['positions']['sha256']
    else:
        assert not (output / 'point-model-input.json').exists()
    result = read(output, 'result.json')
    assert result['model_fn_calls'] == result['scheduler_steps'] == 50
    assert result['branch_counts'] == {'positive': 50, 'negative': 0}
    assert read(output, 'latent.json')['readback_exact']
    assert len(list((output / 'frames').glob('*.png'))) == 33
    receipt = {'run': name, 'status': 'INPUT_PARITY_PASS', 'reference': reference.name,
               'initial_latent_sha256': actual['latents']['sha256'], 'vace_context_sha256': actual['vace_context']['sha256'],
               'text_sha256': trace[0]['context_hashes'], 'full_rgb_and_three_channel_mask_png_exact': True,
               'scheduler_grid_exact': True, 'point': point, 'result': result,
               'mp4_sha256': hashlib.sha256((output / 'generated.mp4').read_bytes()).hexdigest()}
    (output / 'PARITY.json').write_text(json.dumps(receipt, indent=2))
    print(json.dumps({'run': name, 'status': receipt['status']}))


if __name__ == '__main__':
    main()
