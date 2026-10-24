"""CPU-only synthetic full-block input contracts; no checkpoint or GPU required."""
from pathlib import Path

import pytest
import torch

from block_contract import (
    expected_counts,
    make_conditions,
    runtime_dtype,
    tensor_sha256,
    token_layout,
    validate_conditions,
    validate_fixture,
)


def test_exact_context_partition_gates_and_seed() -> None:
    context, e = make_conditions(19)
    validate_conditions(context, e)
    assert context[:, :257].shape == (1, 257, 5120)
    assert context[:, 257:].shape == (1, 512, 5120)
    assert torch.equal(e[:, 2], torch.ones_like(e[:, 2]))
    assert torch.equal(e[:, 5], torch.ones_like(e[:, 5]))
    other_context, other_e = make_conditions(19)
    assert tensor_sha256(context) == tensor_sha256(other_context)
    assert tensor_sha256(e) == tensor_sha256(other_e)


def test_short_context_and_zero_gate_rejected() -> None:
    context, e = make_conditions(19)
    with pytest.raises(ValueError, match='context'):
        validate_conditions(context[:, :36], e)
    bad = e.clone()
    bad[:, 2] = 0
    with pytest.raises(ValueError, match='gate'):
        validate_conditions(context, bad)
    bad = e.clone()
    bad[:, 1] = .5
    with pytest.raises(ValueError, match='bounded'):
        validate_conditions(context, bad)


def test_dtype_policy_preserves_norm_and_modulation() -> None:
    for name in ('modulation', 'norm3.weight', 'cross_attn.norm_q.weight', 'self_attn.norm_k.weight'):
        assert runtime_dtype(name) == torch.float32
    for name in ('ffn.0.weight', 'ffn.2.bias', 'cross_attn.k_img.weight', 'self_attn.q.weight'):
        assert runtime_dtype(name) == torch.bfloat16


def test_grids_and_budget() -> None:
    small, long = token_layout(), token_layout(long=True)
    assert (small.ref, small.video, small.pose, small.total) == (16, 16, 4, 36)
    assert (long.ref, long.video, long.pose, long.total) == (1792, 8960, 2240, 12992)
    assert expected_counts(False) == (8, 3, 3)
    assert expected_counts(True) == (9, 4, 3)


def test_fixture_bytes_not_same_seed_assumption() -> None:
    x = torch.zeros((1, 36, 5120), dtype=torch.bfloat16)
    y = torch.ones((1, 36, 5120), dtype=torch.float32)
    x_hash, y_hash = tensor_sha256(x), tensor_sha256(y)
    validate_fixture(x, y, x_hash, y_hash)
    bad = y.clone()
    bad[0, 0, 0] = 2
    with pytest.raises(ValueError, match='hash'):
        validate_fixture(x, bad, x_hash, y_hash)
    with pytest.raises(ValueError, match='dtype'):
        validate_fixture(x.float(), y, x_hash, y_hash)


def test_actual_branch_hooks_distinguish_residual_only() -> None:
    from block_runner import install_hooks

    for zero_cross in (False, True):
        layers = {name: torch.nn.Linear(4, 4, bias=False) for name in ('self_attn', 'cross_attn', 'ffn')}
        for layer in layers.values():
            _ = layer.requires_grad_(False)
            with torch.no_grad():
                _ = layer.weight.copy_(torch.eye(4))
        if zero_cross:
            with torch.no_grad():
                _ = layers['cross_attn'].weight.zero_()
        observations: dict[str, dict[str, float | bool]] = {}
        install_hooks(torch.nn.ModuleDict(layers), observations)
        x = torch.ones((1, 2, 4), requires_grad=True)
        self_result = layers['self_attn'](x)
        assert isinstance(self_result, torch.Tensor)
        y = x + self_result
        cross_result = layers['cross_attn'](y)
        assert isinstance(cross_result, torch.Tensor)
        z = y + cross_result
        ffn_result = layers['ffn'](z)
        assert isinstance(ffn_result, torch.Tensor)
        _ = (z + ffn_result).square().mean().backward()
        assert x.grad is not None and bool((x.grad > 0).all())
        assert observations['cross_attn']['output_norm'] > 0
        assert (observations['cross_attn']['input_norm'] == 0) == zero_cross
        assert all(isinstance(v, (float, bool)) for row in observations.values() for v in row.values())


def test_actual_atomic_adapter_save_pair(tmp_path: Path) -> None:
    from block_runner import atomic_adapters
    from lora_component import LowRankLinear, load_adapters

    module = LowRankLinear(torch.nn.Linear(8, 6))
    path = tmp_path / 'adapter.safetensors'
    atomic_adapters(path, {'q': module}, {'classification': 'SYNTHETIC_CPU_FIXTURE'})
    assert path.is_file() and path.with_suffix('.json').is_file()
    assert not list(tmp_path.glob('*.pending.*'))
    schema = load_adapters(path, {'q': module})
    assert schema.label == 'TEST_ONLY/NOT_FOR_INFERENCE'
