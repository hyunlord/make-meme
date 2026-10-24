# /// script
# requires-python = ">=3.12"
# dependencies = ["torch", "safetensors"]
# ///
"""Run through phase_train.py: exact named AdamW/RNG restoration, no update."""
from collections.abc import Mapping
from pathlib import Path
from typing import Final
import hashlib
import torch
from torch import Tensor
from artifacts import load_tree
from lora_component import LowRankLinear

ORDER:Final=('q.A','q.B','v.A','v.B')


def named_parameters(adapters:Mapping[str,LowRankLinear])->dict[str,torch.nn.Parameter]:
    """Use an explicit name order rather than trusting state enumeration."""
    return {'q.A':adapters['q'].lora_A,'q.B':adapters['q'].lora_B,
            'v.A':adapters['v'].lora_A,'v.B':adapters['v'].lora_B}


def checkpoint(path:Path,expected_sha:str):
    """Load existing safe tree after payload/sidecar integrity verification."""
    assert hashlib.sha256(path.read_bytes()).hexdigest()==expected_sha
    tree,meta=load_tree(path,device='cpu')
    assert tree['step']==20 and tree['tuple_cursor']==2
    assert tuple(tree['adapter'])==ORDER
    assert set(tree['optimizer']['state'])=={'0','1','2','3'}
    group=tree['optimizer']['groups'];assert len(group)==1 and group[0]['params']==[0,1,2,3]
    assert not group[0]['capturable'] and not group[0]['differentiable']
    for index,name in enumerate(ORDER):
        value=tree['adapter'][name];state=tree['optimizer']['state'][str(index)]
        assert value.dtype==torch.float32 and torch.isfinite(value).all()
        assert set(state)=={'step','exp_avg','exp_avg_sq'}
        assert state['step'].device.type=='cpu' and float(state['step'])==20
        for key in ('exp_avg','exp_avg_sq'):
            assert state[key].dtype==value.dtype and state[key].shape==value.shape and torch.isfinite(state[key]).all()
    return tree,meta


def restore(tree,adapters:Mapping[str,LowRankLinear],optimizer:torch.optim.AdamW)->list[dict]:
    """Bind names to new parameter objects and restore AdamW plus both RNG states."""
    named=named_parameters(adapters);parameters=list(named.values())
    assert [id(p) for p in optimizer.param_groups[0]['params']]==[id(p) for p in parameters]
    with torch.no_grad():
        for name,parameter in named.items():
            assert parameter.dtype==tree['adapter'][name].dtype and parameter.shape==tree['adapter'][name].shape
            parameter.copy_(tree['adapter'][name].to(parameter.device));parameter.grad=None
    groups=[{key:tuple(value) if key=='betas' else value for key,value in group.items()} for group in tree['optimizer']['groups']]
    state={int(key):{name:value.clone() for name,value in values.items()} for key,values in tree['optimizer']['state'].items()}
    optimizer.load_state_dict({'state':state,'param_groups':groups})
    records=[]
    for index,(name,parameter) in enumerate(named.items()):
        assert torch.equal(parameter.detach().cpu(),tree['adapter'][name])
        restored=optimizer.state[parameter];original=tree['optimizer']['state'][str(index)]
        for key in original:
            assert restored[key].dtype==original[key].dtype and torch.equal(restored[key].cpu(),original[key])
            expected='cpu' if key=='step' else parameter.device.type
            assert restored[key].device.type==expected
        records.append({'name':name,'optimizer_id':index,'parameter_object_id':id(parameter),'shape':list(parameter.shape),'dtype':str(parameter.dtype),'parameter_device':str(parameter.device),'state_devices':{k:str(v.device) for k,v in restored.items()},'step':float(restored['step'])})
    actual={key:list(value) if key=='betas' else value for key,value in optimizer.param_groups[0].items() if key!='params'}
    expected={key:value for key,value in tree['optimizer']['groups'][0].items() if key!='params'}
    assert actual==expected
    torch.set_rng_state(tree['cpu_rng'])
    if tree['cuda_rng']:torch.cuda.set_rng_state_all(tree['cuda_rng'])
    assert torch.equal(torch.get_rng_state(),tree['cpu_rng'])
    assert all(torch.equal(a,b) for a,b in zip(torch.cuda.get_rng_state_all() if tree['cuda_rng'] else [],tree['cuda_rng']))
    assert all(p.grad is None for p in parameters)
    return records


def lowrank_action(old:Mapping[str,Tensor],new:Mapping[str,Tensor]):
    """Fixed nonrandom vectors probe BA without constructing a 5120-square matrix."""
    from budget_contract import prediction_delta
    x=torch.linspace(-1,1,4*5120,dtype=torch.float32).reshape(4,5120)
    result={}
    for key in ('q','v'):
        old_action=(x@old[key+'.lora_A'].T)@old[key+'.lora_B'].T
        new_action=(x@new[key+'.lora_A'].T)@new[key+'.lora_B'].T
        result[key]={'action':prediction_delta(new_action,old_action),'factors':{name:prediction_delta(new[key+'.'+name],old[key+'.'+name]) for name in ('lora_A','lora_B')},'probe':'four fixed linspace vectors; not complete BA equality proof'}
    return result
