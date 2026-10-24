# /// script
# requires-python = ">=3.12"
# dependencies = ["torch", "safetensors", "pydantic"]
# ///
"""Run via phase_train.py; finite-budget comparisons and lossless restart state."""
from collections.abc import Mapping
from pathlib import Path
from typing import TypedDict
import torch
from torch import Tensor
from artifacts import save_tree,load_tree
from lora_component import LowRankLinear

class Delta(TypedDict):
    max_abs:float
    rms:float
    relative_l2:float|None

class Replay(Delta):
    passed:bool
    atol:float
    rtol:float


def prediction_delta(value:Tensor,baseline:Tensor)->Delta:
    """Summarize already computed predictions, without additional model work."""
    delta=value.detach().float().cpu()-baseline.detach().float().cpu()
    norm=float(baseline.detach().float().norm())
    return {'max_abs':float(delta.abs().max()),'rms':float(delta.square().mean().sqrt()),'relative_l2':float(delta.norm())/norm if norm>0 else None}


def replay_check(value:Tensor,baseline:Tensor)->Replay:
    """Strict predeclared replay bound; not the looser split-parity tolerance."""
    return {**prediction_delta(value,baseline),'passed':bool(torch.allclose(value.detach().cpu(),baseline.detach().cpu(),atol=1e-7,rtol=1e-5)),'atol':1e-7,'rtol':1e-5}


def save_checkpoint(root:Path,adapters:Mapping[str,LowRankLinear],optimizer:torch.optim.AdamW,step:int,provenance:dict[str,str])->None:
    """Save safe tensor/primitive state, verify readback, and restore optimizer structure."""
    state=optimizer.state_dict()
    groups=[{key:list(value) if key=='betas' else value for key,value in group.items()} for group in state['param_groups']]
    tree={'step':step,'tuple_cursor':step%3,'adapter':{f'{key}.{name}':tensor for key,layer in adapters.items() for name,tensor in zip(('A','B'),layer.adapter_parameters())},'optimizer':{'state':{str(key):value for key,value in state['state'].items()},'groups':groups},'cpu_rng':torch.get_rng_state(),'cuda_rng':torch.cuda.get_rng_state_all() if torch.cuda.is_initialized() else []}
    path=root/f'restart-{step:03d}.safetensors'
    save_tree(path,tree,provenance)
    restored,_=load_tree(path,device='cpu')
    assert restored['step']==step and restored['tuple_cursor']==step%3
    assert torch.equal(restored['cpu_rng'],tree['cpu_rng'])
    assert len(restored['cuda_rng'])==len(tree['cuda_rng'])
    assert all(torch.equal(a,b) for a,b in zip(restored['cuda_rng'],tree['cuda_rng']))
    parameter_list=[p for layer in adapters.values() for p in layer.adapter_parameters()]
    fresh=torch.optim.AdamW(parameter_list,lr=1e-4,weight_decay=0)
    reconstituted={'state':{int(key):value for key,value in restored['optimizer']['state'].items()},'param_groups':[{key:tuple(value) if key=='betas' else value for key,value in group.items()} for group in restored['optimizer']['groups']]}
    fresh.load_state_dict(reconstituted)
    assert len(fresh.param_groups)==len(optimizer.param_groups)
    assert len(fresh.state)==len(optimizer.state)
    assert restored['adapter'].keys()==tree['adapter'].keys()
    assert all(torch.equal(restored['adapter'][key],value.detach().cpu()) and restored['adapter'][key].dtype==value.dtype for key,value in tree['adapter'].items())
    for loaded_group,original_group in zip(fresh.param_groups,optimizer.param_groups):
        assert loaded_group.keys()==original_group.keys()
        assert all(loaded_group[key]==value for key,value in original_group.items() if key!='params')
        assert [id(p) for p in loaded_group['params']]==[id(p) for p in original_group['params']]
    for original,loaded in zip(optimizer.state.values(),fresh.state.values()):
        assert original.keys()==loaded.keys()
        for key in original:
            assert torch.equal(original[key].cpu(),loaded[key].cpu())
    del fresh


def load_checkpoint(root:Path,step:int):
    """Return verified CPU restart material; no execution or automatic training resume."""
    tree,_=load_tree(root/f'restart-{step:03d}.safetensors',device='cpu')
    return tree
