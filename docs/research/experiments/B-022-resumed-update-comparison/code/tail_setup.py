"""Finite four-tuple real FM regression; only last-block Q/V LoRA trains."""
from pathlib import Path
from types import SimpleNamespace
import functools
import hashlib
import json
import torch
from torch import nn
from safetensors import safe_open
from artifacts import load_tree
from cuda_probe import tiny
from lora_component import LowRankLinear,save_adapters
from fm_contract import fixed_tuples,validate_tail_shapes,CacheBinding,mix_velocity
from torch.autograd.graph import Node



def digest(value:torch.Tensor) -> str:
    return hashlib.sha256(value.detach().cpu().contiguous().view(torch.uint8).numpy().tobytes()).hexdigest()


def hashes(module:nn.Module) -> dict[str,str]:
    return {name:digest(p) for name,p in module.named_parameters() if not p.requires_grad}


def atomic_adapter(path:Path,adapters:dict[str,LowRankLinear],provenance:dict[str,str]) -> None:
    import os
    temporary=path.with_name(path.stem+'.pending.safetensors')
    save_adapters(temporary,adapters,provenance)
    for item in (temporary,temporary.with_suffix('.json')):
        with item.open('rb') as stream:os.fsync(stream.fileno())
    temporary.replace(path);temporary.with_suffix('.json').replace(path.with_suffix('.json'))
    directory=os.open(path.parent,os.O_RDONLY)
    try:os.fsync(directory)
    finally:os.close(directory)


def fa_nodes(loss:torch.Tensor) -> int:
    pending:list[Node|None]=[loss.grad_fn];seen:set[Node]=set()
    while pending:
        node=pending.pop()
        if node is None or node in seen:continue
        seen.add(node);pending.extend(child for child,_ in node.next_functions)
    return sum('FlashAttn' in type(node).__name__ and 'Backward' in type(node).__name__ for node in seen)


def prepare(root:Path,cfg:dict):
    producer=(root/"producer").resolve()
    producer_code=json.loads((producer/"PREREGISTERED_CODE.json").read_text())
    producer_cfg=json.loads((producer/"configs/real.json").read_text())
    assert cfg==producer_cfg
    _anchor=tiny(root)
    torch.manual_seed(20261024)
    import wan.modules.model_scail2 as official
    selected={}
    with safe_open(str(root/'models/SCAIL.safetensors'),framework='pt',device='cpu') as reader:
        for key in reader.keys():
            if key.startswith(('blocks.39.','head.')):selected[key]=reader.get_tensor(key)
    stored={k:digest(v) for k,v in selected.items()}
    def build():
        with torch.device('meta'):
            block=official.WanAttentionBlock('i2v_cross_attn',5120,13824,40,qk_norm=True,cross_attn_norm=True,eps=1e-6)
            head=official.Head(5120,16,(1,2,2),eps=1e-6)
        for module,prefix in ((block,'blocks.39.'),(head,'head.')):
            state={key.removeprefix(prefix):value.to('cuda',dtype=torch.float32 if prefix=='head.' or 'norm' in key or key.endswith('modulation') else torch.bfloat16) for key,value in selected.items() if key.startswith(prefix)}
            result=module.load_state_dict(state,strict=True,assign=True)
            assert not result.missing_keys and not result.unexpected_keys
            module.requires_grad_(False)
        adapters={}
        for key in ('q','v'):
            base=block.get_submodule('self_attn.'+key);assert isinstance(base,nn.Linear)
            adapters[key]=LowRankLinear(base,4,4.0);block.set_submodule('self_attn.'+key,adapters[key])
        return block,head,adapters
    receipt=json.loads((producer/'artifacts/prefix_receipt.json').read_text());assert receipt['status']=='PASS' and receipt['full_positive_forwards']==4
    target_tree,target_meta=load_tree(producer/'artifacts/target.safetensors',device='cpu')
    target_hash=digest(target_tree['z_y'])
    fm=json.loads((root/'configs/fm.json').read_text())
    consumer=json.loads((root/'configs/consumer.json').read_text())
    assert consumer['budgets']['additional_updates']==80 and consumer['budgets']['evaluation_hard_cap']==40
    geometry_hash=hashlib.sha256(json.dumps([cfg['height'],cfg['width'],cfg['frames'],cfg['fps']],separators=(',',':')).encode()).hexdigest()
    assert target_meta['file_sha256']==receipt['target_sha256']
    assert [row['tuple_id'] for row in receipt['tuples']]==[spec.tuple_id for spec in fixed_tuples()]
    cpu={}
    for row in receipt['tuples']:
        path=producer/'artifacts'/('prefix-'+row['tuple_id']+'.safetensors')
        assert hashlib.sha256(path.read_bytes()).hexdigest()==row['file_sha256']
        assert hashlib.sha256(path.with_suffix('.json').read_bytes()).hexdigest()==row['sidecar_sha256']
        cpu[row['tuple_id']],meta=load_tree(path,device='cpu')
        assert meta['provenance']['code']==producer_code
        assert meta['provenance']['config']==cfg
        assert meta['provenance']['conditions_sha256']==receipt['conditions_sha256']
        assert meta['provenance']['target_sha256']==receipt['target_sha256']
        spec=next(item for item in fixed_tuples() if item.tuple_id==row['tuple_id'])
        assert meta['provenance']['sigma']==spec.sigma and meta['provenance']['seed']==spec.seed
        expected=CacheBinding(tuple_id=spec.tuple_id,sigma=spec.sigma,seed=spec.seed,noise_hash=fm['noise_hashes'][spec.tuple_id],z_y_hash=target_hash,conditions_hash=receipt['conditions_sha256'],model_hash=fm['model_sha256'],geometry_hash=geometry_hash,code_hash=hashlib.sha256((producer/'PREREGISTERED_CODE.json').read_bytes()).hexdigest())
        CacheBinding.model_validate(meta['provenance']['binding']).require_same(expected)
        data=cpu[row['tuple_id']]
        assert digest(data['epsilon'])==expected.noise_hash
        mixed=mix_velocity(target_tree['z_y'],data['epsilon'],spec.sigma)
        assert torch.equal(data['target'],mixed.target) and torch.equal(data['z_sigma'],mixed.z_sigma)
        assert data['block_kwargs']['additional_ref_length']==0
        validate_tail_shapes(data['h38'],data['block_kwargs']['e'],data['head_e'],12992)
    del target_tree,mixed
    def make_predict(block,head):
      def predict(tuple_id):
          data=cpu[tuple_id]
          kwargs={key:(value.to('cuda') if isinstance(value,torch.Tensor) and key!='seq_lens' and key!='grid_sizes' else value) for key,value in data['block_kwargs'].items()}
          kwargs['freqs']=torch.view_as_complex(data['freqs_real'].to('cuda').contiguous())
          kwargs['rope_apply_func']=functools.partial(official.rope_apply_scail,**{k:v for k,v in kwargs.items() if k!='rope_apply_func'})
          with torch.autocast('cuda',dtype=torch.bfloat16):
              hidden=block(data['h38'].to('cuda'),**kwargs)
              projected=head(hidden,data['head_e'].to('cuda'))
              prediction=official.SCAIL2Model.unpatchify(SimpleNamespace(out_dim=16,patch_size=(1,2,2)),projected,kwargs['grid_sizes'],offset=kwargs['ref_length'])[0].float()
          return prediction,data['target'].to('cuda')
      return predict
    return SimpleNamespace(anchor=_anchor,build=build,make_predict=make_predict,cpu=cpu,selected=selected,stored=stored,producer=producer)
