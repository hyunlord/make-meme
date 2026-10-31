# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# Run with existing research Python (CPU only): train_replay_check.py <train-v2 dir> <c009 train dir> <out.json>
"""Compare C-009 step000 with train-v2 step000 and the update schedules (step, clip, grid, NULL, negative-text)."""
from pathlib import Path
import json
import sys

import torch


def same(a, b) -> bool:
    if isinstance(a, torch.Tensor):
        return isinstance(b, torch.Tensor) and a.dtype == b.dtype and a.shape == b.shape and torch.equal(a, b)
    if isinstance(a, dict):
        return isinstance(b, dict) and a.keys() == b.keys() and all(same(a[k], b[k]) for k in a)
    if isinstance(a, (list, tuple)):
        return len(a) == len(b) and all(same(x, y) for x, y in zip(a, b))
    return a == b


def main() -> None:
    old_dir, new_dir, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    old = torch.load(old_dir / 'checkpoint-000.pt', map_location='cpu', weights_only=True)
    new = torch.load(new_dir / 'checkpoint-000.pt', map_location='cpu', weights_only=True)
    init = {key: same(old[key], new[key]) for key in
            ('adapter', 'optimizer', 'cpu_rng', 'cuda_rng', 'generator_state', 'order', 'cursor', 'completed_updates', 'counts')}
    init['config_differs_only_in'] = sorted(k for k in old['config'] if old['config'][k] != new['config'][k])
    keys = ('step', 'clip', 'grid_index', 'null', 'negative_text')
    rows = [[json.loads(line) for line in (d / 'updates.jsonl').read_text().splitlines()] for d in (old_dir, new_dir)]
    mismatched = [a['step'] for a, b in zip(*rows) if any(a[k] != b[k] for k in keys)]
    sigma_equal = all(a['sigma'] == b['sigma'] for a, b in zip(*rows))
    result = {'init': init, 'INIT_PARITY_VERIFIED': all(v for k, v in init.items() if k != 'config_differs_only_in'),
              'schedule': {'old_updates': len(rows[0]), 'new_updates': len(rows[1]), 'compared_fields': keys,
                           'mismatched_steps': mismatched, 'sigma_equal': sigma_equal,
                           'null_count': sum(r['null'] for r in rows[1]), 'negative_text_count': sum(r['negative_text'] for r in rows[1])},
              'TRAIN_SCHEDULE_MATCHED': not mismatched and len(rows[0]) == len(rows[1]) == 256,
              'noise_scope': 'per-update noise is drawn from the restored CPU generator in the same call order; past noise tensors were not saved, so bitwise equality is inferred, not observed',
              'loss_by_step': [{'step': a['step'], 'old_red_loss': a['loss'], 'new_white_loss': b['loss']} for a, b in zip(*rows)]}
    out.write_text(json.dumps(result, indent=1))
    print(json.dumps({k: v for k, v in result.items() if k not in ('loss_by_step',)}, indent=1)[:1500])


if __name__ == '__main__':
    main()
