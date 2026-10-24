"""Synthetic CPU-only adapter wiring checks; not animal/model quality tests."""
import copy
from pathlib import Path

import pytest
import torch
from torch import nn

from lora_component import LowRankLinear, load_adapters, save_adapters


def fixture(dtype: torch.dtype = torch.float32) -> tuple[LowRankLinear, torch.Tensor, torch.Tensor]:
    _ = torch.manual_seed(18)
    base = nn.Linear(8, 6, dtype=dtype)
    model = LowRankLinear(base)
    x = torch.randn(2, 3, 8, dtype=dtype)
    y = torch.randn(2, 3, 6, dtype=torch.float32)
    return model, x, y


def test_zero_init_and_off_exact() -> None:
    model, x, _ = fixture()
    baseline = model.base.forward(x)
    assert torch.equal(model.forward(x), baseline)
    assert all(not p.requires_grad for p in model.base.parameters())
    with torch.no_grad():
        _ = model.lora_B.fill_(.1)
    assert not torch.equal(model.forward(x), baseline)
    model.enabled = False
    assert torch.equal(model.forward(x), baseline)


def test_membership_backward_three_steps_and_frozen_base() -> None:
    model, x, y = fixture()
    before = {name: value.detach().clone() for name, value in model.base.state_dict().items()}
    parameters = model.adapter_parameters()
    optimizer = torch.optim.AdamW(parameters, lr=1e-4, weight_decay=0)
    assert {id(p) for group in optimizer.param_groups for p in group['params']} == {id(model.lora_A), id(model.lora_B)}
    a_before, b_before = model.lora_A.detach().clone(), model.lora_B.detach().clone()
    for step in range(3):
        optimizer.zero_grad(set_to_none=True)
        loss = (model.forward(x).float() - y).square().mean()
        loss.backward()
        assert torch.isfinite(loss)
        a_grad, b_grad = model.lora_A.grad, model.lora_B.grad
        assert a_grad is not None and b_grad is not None
        assert torch.isfinite(a_grad).all() and torch.isfinite(b_grad).all()
        assert b_grad.abs().sum() > 0
        if step == 0:
            assert torch.count_nonzero(a_grad) == 0
        else:
            assert a_grad.abs().sum() > 0
        _ = optimizer.step()
    assert not torch.equal(a_before, model.lora_A)
    assert not torch.equal(b_before, model.lora_B)
    assert all(p.grad is None for p in model.base.parameters())
    assert all(torch.equal(before[name], value) for name, value in model.base.state_dict().items())


def test_eval_is_not_no_grad_or_merge() -> None:
    model, x, y = fixture()
    before = model.base.weight.detach().clone()
    _ = model.eval()
    (model.forward(x) - y).square().mean().backward()
    assert model.lora_B.grad is not None and model.lora_B.grad.abs().sum() > 0
    _ = model.train()
    assert torch.equal(before, model.base.weight)


def test_bf16_input_fp32_masters_even_under_autocast() -> None:
    model, x, y = fixture(torch.bfloat16)
    with torch.autocast('cpu', dtype=torch.bfloat16):
        result = model.forward(x)
        loss = (result.float() - y).square().mean()
    loss.backward()
    assert result.dtype == torch.bfloat16
    assert model.lora_A.dtype == model.lora_B.dtype == torch.float32
    assert model.lora_B.grad is not None and model.lora_B.grad.dtype == torch.float32
    assert torch.isfinite(model.lora_B.grad).all()


def test_save_reload_off_and_no_base_mutation(tmp_path: Path) -> None:
    model, x, _ = fixture()
    fresh = LowRankLinear(copy.deepcopy(model.base))
    base_before = fresh.base.weight.detach().clone()
    with torch.no_grad():
        _ = model.lora_B.normal_()
    path = tmp_path / 'adapter.safetensors'
    save_adapters(path, {'q': model}, {'fixture': 'SYNTHETIC_TENSOR_CONTRACT_TEST'})
    _ = load_adapters(path, {'q': fresh})
    assert torch.equal(model.forward(x), fresh.forward(x))
    assert torch.equal(base_before, fresh.base.weight)
    fresh.enabled = False
    assert torch.equal(fresh.forward(x), model.base.forward(x))
    assert all(p.requires_grad for p in fresh.adapter_parameters())


def test_bad_save_hash_rejected_before_mutation(tmp_path: Path) -> None:
    model, _, _ = fixture()
    path = tmp_path / 'adapter.safetensors'
    save_adapters(path, {'q': model}, {})
    before = model.lora_A.detach().clone()
    with path.open('ab') as handle:
        _ = handle.write(b'bad')
    with pytest.raises(ValueError, match='hash'):
        _ = load_adapters(path, {'q': model})
    assert torch.equal(before, model.lora_A)


def test_metadata_mismatch_rejected_before_copy(tmp_path: Path) -> None:
    from lora_component import AdapterSchema

    model, _, _ = fixture()
    path = tmp_path / 'adapter.safetensors'
    save_adapters(path, {'q': model}, {})
    schema = AdapterSchema.model_validate_json(path.with_suffix('.json').read_text())
    bad = schema.model_copy(update={'modules': {'v': schema.modules['q']}})
    _ = path.with_suffix('.json').write_text(bad.model_dump_json())
    before = model.lora_A.detach().clone()
    with pytest.raises(ValueError, match='specification'):
        _ = load_adapters(path, {'q': model})
    assert torch.equal(before, model.lora_A)
