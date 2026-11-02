# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# Run: existing-research-python prepare.py PARENT_ROOT NEW_ROOT
"""CPU-only sidecar and private configuration preparation; no model execution."""
from pathlib import Path
import hashlib
import json
import math
import sys
import torch


def main() -> None:
    parent, root = map(Path, sys.argv[1:3])
    assert parent.is_absolute() and root.is_absolute()
    paths = json.loads((root / 'PATHS.json').read_text())
    config = json.loads((parent / 'configs/ON2048_A.json').read_text())
    checkpoint = Path(config['adapter_checkpoint'])
    assert hashlib.sha256(checkpoint.read_bytes()).hexdigest() == 'c246971ad353f78ddb0ff7bbb162f26187f9d5437eb1158e732fd29cd334f977'
    source = torch.load(config['cache_file'], map_location='cpu', weights_only=True)
    keys = {'sequence', 'split', 'prompt', 'patches', 'anchor_valid', 'positions', 'visible', 'valid', 'box_wh'}
    assert set(source) == keys
    assert source['positions'].shape == (33, 9, 2)
    offsets = json.loads((parent / 'task/TASK_MANIFEST.json').read_text())['point_offsets_px']
    exclusions = json.loads(Path(config['point_exclusions']).read_text())
    report = {'source_sidecar_sha256': hashlib.sha256(Path(config['cache_file']).read_bytes()).hexdigest(), 'paths': {}, 'cuda_initialized': False}
    for name, entry in paths['paths'].items():
        centers = entry['center_xy_pixel_index']
        for t, (x, y) in enumerate(centers):
            tau = t / 32
            amplitude = 0.0 if t in (0, 32) else 48 * math.sin(math.pi * tau) ** 2
            factor = math.sin(2 * math.pi * tau) if name == 'S' else 2 * entry['alpha'] - 1
            assert abs(x - (104 + 208 * tau)) < 1e-12
            assert abs(y - (120 + amplitude * factor)) < 1e-12
        pixel = torch.tensor(centers, dtype=torch.float64)[:, None, :] + torch.tensor(offsets, dtype=torch.float64)[None, :, :]
        positions = ((pixel + 0.5) / torch.tensor([416, 240], dtype=torch.float64)).to(source['positions'].dtype)
        positions[0] = source['positions'][0]
        positions[32] = source['positions'][32]
        sidecar = {**source, 'sequence': f'c013_{name}', 'positions': positions}
        output = root / 'cache' / f'{name}.sidecar.pt'
        assert not output.exists()
        temporary = output.with_suffix('.tmp')
        torch.save(sidecar, temporary)
        temporary.replace(output)
        restored = torch.load(output, map_location='cpu', weights_only=True)
        for key in keys - {'sequence', 'positions', 'split', 'prompt'}:
            assert torch.equal(restored[key], source[key])
        assert restored['split'] == source['split'] and restored['prompt'] == source['prompt']
        assert torch.equal(restored['positions'], positions)
        assert torch.equal(positions[[0, 32]], source['positions'][[0, 32]])
        exclusions['clips'][sidecar['sequence']] = exclusions['clips'][source['sequence']]
        report['paths'][name] = {'sidecar_sha256': hashlib.sha256(output.read_bytes()).hexdigest(), 'shared_fields_exact': True, 'endpoints_exact': True, 'positions_shape': list(positions.shape), 'dtype': str(positions.dtype)}
    (root / 'cache/point-exclusions.json').write_text(json.dumps(exclusions, indent=2))
    for run in paths['runs']:
        row = {**config, 'output': str(root / 'outputs' / run['id']), 'seed': run['seed']}
        if run['adapter'] == 'OFF':
            row.update(adapter_mode='BASE', adapter_checkpoint=None)
        else:
            row.update(cache_file=str(root / 'cache' / f"{run['path']}.sidecar.pt"), point_exclusions=str(root / 'cache/point-exclusions.json'))
        (root / 'configs' / f"{run['id']}.json").write_text(json.dumps(row, indent=2))
    assert not torch.cuda.is_initialized()
    (root / 'PREPARE.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report))


if __name__ == '__main__':
    main()
