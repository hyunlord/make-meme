# /// script
# requires-python = ">=3.12"
# dependencies = ["torch", "pytest", "safetensors", "pydantic"]
# ///
"""Run: existing environment python -m pytest code/test_budget.py."""
import torch
import pytest
from pathlib import Path

def test_replay_rejects_meaningful_change():
    from budget_contract import replay_check
    baseline=torch.tensor([1.,2.])
    assert replay_check(baseline,baseline)['passed']
    assert not replay_check(baseline+0.01,baseline)['passed']

def test_checkpoint_preserves_optimizer_rng_cursor(tmp_path:Path):
    from budget_contract import save_checkpoint,load_checkpoint
    from lora_component import LowRankLinear
    layer=LowRankLinear(torch.nn.Linear(4,3),4,4.)
    adapters={'q':layer}
    optimizer=torch.optim.AdamW(layer.adapter_parameters(),lr=1e-4,weight_decay=0)
    layer(torch.ones(2,4)).square().mean().backward();optimizer.step()
    rng=torch.get_rng_state().clone()
    save_checkpoint(tmp_path,adapters,optimizer,1,{'experiment':'fixture'})
    restored=load_checkpoint(tmp_path,1)
    assert restored['step']==1 and restored['tuple_cursor']==1
    assert torch.equal(restored['cpu_rng'],rng)
    assert restored['optimizer']['groups'][0]['lr']==1e-4
    assert restored['optimizer']['state']['0']['step'].item()==1

def test_off_delta_uses_same_prediction():
    from budget_contract import prediction_delta
    out=prediction_delta(torch.tensor([2.,4.]),torch.tensor([1.,2.]))
    assert out['max_abs']==2. and out['relative_l2']==1.

def test_zero_baseline_relative_delta_is_undefined():
    from budget_contract import prediction_delta
    assert prediction_delta(torch.ones(2),torch.zeros(2))['relative_l2'] is None

def test_checkpoint_zero_has_no_optimizer_moments(tmp_path:Path):
    from budget_contract import save_checkpoint,load_checkpoint
    from lora_component import LowRankLinear
    layer=LowRankLinear(torch.nn.Linear(4,3),4,4.)
    optimizer=torch.optim.AdamW(layer.adapter_parameters(),lr=1e-4,weight_decay=0)
    save_checkpoint(tmp_path,{'q':layer},optimizer,0,{'experiment':'fixture'})
    restored=load_checkpoint(tmp_path,0)
    assert restored['optimizer']['state']=={} and restored['tuple_cursor']==0
