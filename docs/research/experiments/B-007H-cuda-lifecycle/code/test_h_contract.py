"""CPU mocks only: diagnostic sequencing/value checks and exact frozen policies."""
from pathlib import Path
from unittest.mock import patch
import torch
from cuda_probe import tiny,recheck


def test_tiny_mock_is_non_rng_and_keeps_64_bytes(tmp_path:Path) -> None:
    (tmp_path/'reports').mkdir()
    original=torch.Tensor.to;targets=[]
    def redirected(value,*args,**kwargs):
        if args and args[0]=='cuda:0':targets.append(args[0]);args=('cpu',)+args[1:]
        return original(value,*args,**kwargs)
    before=torch.get_rng_state().clone()
    with patch.object(torch.Tensor,'to',redirected),patch('cuda_probe.diagnostic'),patch('cuda_probe.phase'),patch.object(torch.cuda,'synchronize'):
        value=tiny(tmp_path);recheck(tmp_path,value,'fixture')
    assert targets==['cuda:0'] and value.numel()*value.element_size()==64
    assert torch.equal(before,torch.get_rng_state()) and torch.equal(value,torch.full((16,),5.0))


def test_frozen_math_and_loader_reuse() -> None:
    import os
    previous=Path(os.environ['G_CODE']);current=Path(__file__).parent
    for name in ('staged_loader.py','extract.py','artifacts.py','phase_decode.py','media.py'):
        assert (current/name).read_bytes()==(previous/name).read_bytes(),name
    source=(current/'phase_sample.py').read_text()
    assert source.index('anchor=tiny(root)')<source.index('model=load_model(')<source.index('tree,meta=restore(root)')
    assert "'offload_model':True" in source and "'guide_scale':5.0" in source


def test_probe_budget_and_cpu_leaves_contract() -> None:
    import os,json
    meta=json.loads(Path(os.environ['G_CACHE_METADATA']).read_text())
    leaves=[]
    def visit(node):
        if 'tensor' in node:leaves.append((node['tensor'],node['device']))
        for item in node.get('list',[]):visit(item)
        for item in node.get('dict',{}).values():visit(item)
    visit(meta['structure'])
    assert len(leaves)==16 and dict(leaves)['t13']=='cpu' and dict(leaves)['t15']=='cpu'
    assert dict(leaves)['t14']=='cuda:0'
