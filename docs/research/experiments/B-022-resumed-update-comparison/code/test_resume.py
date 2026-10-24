# /// script
# requires-python = ">=3.12"
# dependencies = ["pytest", "torch", "safetensors"]
# ///
"""Run existing Python -m pytest code/test_resume.py, CPU only."""
import hashlib
from pathlib import Path
import torch
from torch import nn
from budget_contract import save_checkpoint
from resume_contract import checkpoint,restore,named_parameters,lowrank_action
from lora_component import LowRankLinear


def test_resume_moments_parameter_identity_and_rng(tmp_path:Path)->None:
    torch.manual_seed(7)
    adapters={key:LowRankLinear(nn.Linear(8,8),4,4) for key in ('q','v')}
    params=list(named_parameters(adapters).values())
    optimizer=torch.optim.AdamW(params,lr=1e-4,weight_decay=0)
    for _ in range(20):
        optimizer.zero_grad(set_to_none=True)
        sum(p.square().sum() for p in params).backward();optimizer.step()
    save_checkpoint(tmp_path,adapters,optimizer,20,{'experiment':'fixture'})
    path=tmp_path/'restart-020.safetensors'
    tree,_=checkpoint(path,hashlib.sha256(path.read_bytes()).hexdigest())
    fresh={key:LowRankLinear(nn.Linear(8,8),4,4) for key in ('v','q')}
    fresh_optimizer=torch.optim.AdamW(list(named_parameters(fresh).values()),lr=1e-4,weight_decay=0)
    records=restore(tree,fresh,fresh_optimizer)
    assert [row['name'] for row in records]==['q.A','q.B','v.A','v.B']
    assert all(row['step']==20 for row in records)
    assert tree['tuple_cursor']==2
    for old,new in zip(params,named_parameters(fresh).values()):assert torch.equal(old,new)
    assert torch.equal(torch.get_rng_state(),tree['cpu_rng'])
    fresh_optimizer.zero_grad(set_to_none=True)
    sum(p.square().sum() for p in named_parameters(fresh).values()).backward();fresh_optimizer.step()
    assert all(float(state['step'])==21 for state in fresh_optimizer.state.values())


def test_fixed_action_identity()->None:
    values={key+'.'+name:torch.zeros(shape) for key in ('q','v') for name,shape in [('lora_A',(4,5120)),('lora_B',(5120,4))]}
    result=lowrank_action(values,values)
    assert all(row['action']['max_abs']==0 for row in result.values())
