# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Safe restart state and point conditioning from frozen cache, existing Python."""
from pathlib import Path
import json
import torch
from torch import Tensor
from point_adapter import PointAnchorAdapter
from point_features import PointCondition
from runtime_common import atomic_torch


def condition_from_cache(cache: dict) -> PointCondition:
    return PointCondition(**{key: cache[key] for key in (
        'patches', 'anchor_valid', 'positions', 'visible', 'valid', 'box_wh')}).to('cuda')


def load_cache(path: Path, exclusions_path: Path) -> dict:
    """Apply separately reviewed whole-track exclusions without modifying raw cache/NPZ."""
    cache = torch.load(path, map_location='cpu', weights_only=True)
    exclusions = json.loads(exclusions_path.read_text())['clips'][cache['sequence']]['excluded_point_ids']
    cache['valid'] = cache['valid'].clone()
    cache['anchor_valid'] = cache['anchor_valid'].clone()
    cache['patches'] = cache['patches'].clone()
    cache['valid'][:, exclusions] = False
    cache['anchor_valid'][:, exclusions] = False
    cache['patches'][exclusions] = 0
    return cache


def balanced_loss(prediction: Tensor, target: Tensor, mask: Tensor) -> Tensor:
    error = (prediction.float() - target.float()).square().mean(dim=1, keepdim=True)
    assert mask.sum() > 0 and (1-mask).sum() > 0
    return (error*mask).sum()/mask.sum() + (error*(1-mask)).sum()/(1-mask).sum()


def save_checkpoint(path: Path, adapter: PointAnchorAdapter,
                    optimizer: torch.optim.AdamW, state: dict) -> dict:
    """Checkpoint schema contains only tensors/primitives; no executable model objects.

    Explicit adapter/optimizer/cursor arguments make ownership visible, matching
    previous B022 restart evidence without its fixed-tuple cursor contract.
    """
    payload = {**state, 'adapter': {key: value.detach().cpu().clone() for key, value in adapter.state_dict().items()},
               'optimizer': optimizer.state_dict(), 'cpu_rng': torch.get_rng_state(),
               'cuda_rng': torch.cuda.get_rng_state_all()}
    atomic_torch(path, payload)
    restored = torch.load(path, map_location='cpu', weights_only=True)
    assert restored['completed_updates'] == state['completed_updates']
    assert torch.equal(restored['cpu_rng'], payload['cpu_rng'])
    assert all(torch.equal(a, b) for a, b in zip(restored['cuda_rng'], payload['cuda_rng']))
    for key in ('order', 'cursor', 'config'):
        assert restored[key] == payload[key]
    assert torch.equal(restored['generator_state'], payload['generator_state'])
    assert all(torch.equal(restored['adapter'][key], value) for key, value in payload['adapter'].items())
    fresh = PointAnchorAdapter()
    fresh.load_state_dict(restored['adapter'], strict=True)
    fresh_optimizer = torch.optim.AdamW(fresh.parameters(), lr=1e-4, betas=(.9, .999), weight_decay=.01)
    fresh_optimizer.load_state_dict(restored['optimizer'])
    for saved_state, original_state in zip(fresh_optimizer.state.values(), optimizer.state.values()):
        for key, value in original_state.items():
            if isinstance(value, Tensor):
                assert torch.equal(saved_state[key].cpu(), value.cpu())
    torch.set_rng_state(payload['cpu_rng'])
    return {'readback_exact': True, 'optimizer_readback_exact': True,
            'completed_updates': state['completed_updates']}
