"""Finite four-tuple real FM regression; only last-block Q/V LoRA trains."""
from pathlib import Path
from types import SimpleNamespace
import functools
import hashlib
import json
import gc
import torch
from torch import nn
from safetensors import safe_open
from artifacts import load_tree,atomic_json
from cuda_probe import tiny
from runtime_observe import phase
from lora_component import LowRankLinear,save_adapters,load_adapters
from fm_contract import fixed_tuples,velocity_mse,check_parity,validate_tail_shapes,CacheBinding,mix_velocity
from torch.autograd.graph import Node
from safetensors.torch import load_file
from budget_contract import prediction_delta,replay_check,save_checkpoint


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


def run(root:Path,cfg:dict) -> None:
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
    assert (consumer['budgets']['updates'],consumer['budgets']['evaluation_forwards'],consumer['budgets']['evaluation_hard_cap'])==(100,18,20)
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
    block,head,adapters=build();base_before=(hashes(block),hashes(head));evals=0;updates=0
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
    head_gradients={}
    def head_hook(_module,grad_input,_grad_output):
        value=grad_input[0];assert value is not None and torch.isfinite(value).all()
        head_gradients['input_norm']=float(value.float().norm())
    head.register_full_backward_hook(head_hook)
    initial=producer/'artifacts/adapter-initial.safetensors'
    consumer=json.loads((root/'configs/consumer.json').read_text())
    assert hashlib.sha256(initial.read_bytes()).hexdigest()==consumer['initial_adapter_sha256']
    initial_meta=load_adapters(initial,adapters)
    assert initial_meta.provenance['experiment']=='B-020'
    assert initial_meta.provenance['code_sha256']==hashlib.sha256((producer/'PREREGISTERED_CODE.json').read_bytes()).hexdigest()
    initial_values=load_file(str(initial),device='cpu')
    assert all(torch.count_nonzero(initial_values[key+'.lora_B'])==0 for key in ('q','v'))
    assert all(torch.equal(getattr(layer,name).detach().cpu(),initial_values[key+'.'+name]) for key,layer in adapters.items() for name in ('lora_A','lora_B'))
    before={}
    for spec in fixed_tuples():
        with torch.no_grad():pred,target=predict(spec.tuple_id)
        evals+=1
        parity=check_parity(pred,cpu[spec.tuple_id]['baseline_velocity'].to('cuda'))
        assert parity['passed'],'SPLIT_PARITY_BLOCKED'
        before[spec.tuple_id]={'loss':float(velocity_mse(pred,target)),'parity':parity,'delta':prediction_delta(pred,cpu[spec.tuple_id]['baseline_velocity'])}
    atomic_json(root/'reports/parity-before.json',before)
    parameters=[p for layer in adapters.values() for p in layer.adapter_parameters()]
    assert {id(p) for p in parameters}=={id(p) for p in block.parameters() if p.requires_grad}
    optimizer=torch.optim.AdamW(parameters,lr=1e-4,weight_decay=0)
    assert {id(p) for group in optimizer.param_groups for p in group['params']}=={id(p) for p in parameters}
    provenance={'experiment':'B-021','label':'PRIVATE_ONE_CLIP_FM_OVERFIT_NOT_PRODUCTION','code_sha256':hashlib.sha256((root/'PREREGISTERED_CODE.json').read_bytes()).hexdigest(),'producer':'B-020','producer_code_sha256':hashlib.sha256((producer/'PREREGISTERED_CODE.json').read_bytes()).hexdigest(),'prefix_receipt_sha256':hashlib.sha256((producer/'artifacts/prefix_receipt.json').read_bytes()).hexdigest(),'initial_adapter_sha256':hashlib.sha256(initial.read_bytes()).hexdigest()}
    atomic_adapter(root/'artifacts/adapter-initial.safetensors',adapters,provenance)
    optimizer_options={k:v for k,v in optimizer.param_groups[0].items() if k!='params'}
    assert json.loads(json.dumps(optimizer_options))==consumer['optimizer_options']
    atomic_json(root/'reports/optimizer-options.json',optimizer_options)
    save_checkpoint(root/'artifacts',adapters,optimizer,0,provenance)
    snapshots={'0':{k:{'loss':v['loss'],'delta':v['delta']} for k,v in before.items()}}
    original_receipt=json.loads((producer/'artifacts/training_receipt.json').read_text())
    holdout_prediction=None
    rows=[]
    for index in range(100):
        optimizer.zero_grad(set_to_none=True);spec=fixed_tuples()[index%3]
        old=[p.detach().clone() for p in parameters]
        pred,target=predict(spec.tuple_id);loss=velocity_mse(pred,target)
        assert torch.isfinite(loss)
        observed_fa=fa_nodes(loss);assert observed_fa==3
        loss.backward();torch.cuda.synchronize()
        assert head_gradients['input_norm']>0
        gradients={name:float(p.grad.float().norm()) for name,p in block.named_parameters() if p.requires_grad and p.grad is not None}
        assert len(gradients)==4 and all(torch.isfinite(p.grad).all() for p in parameters if p.grad is not None)
        assert all(p.grad is None for p in list(block.parameters())+list(head.parameters()) if not p.requires_grad)
        optimizer.step();updates+=1
        assert all(torch.isfinite(p).all() for p in parameters)
        atomic_adapter(root/'artifacts/adapter-last-completed.safetensors',adapters,{**provenance,'completed_updates':str(updates)})
        assert any(not torch.equal(a,p) for a,p in zip(old,parameters))
        rows.append({'update':updates,'tuple_id':spec.tuple_id,'loss':float(loss.detach()),'gradient_norms':gradients,'parameter_delta':{name:prediction_delta(parameter,previous) for (name,parameter),previous in zip(((name,p) for name,p in block.named_parameters() if p.requires_grad),old)},'base_grad_none':True,'fa_backward_nodes':observed_fa,'head_input_gradient_norm':head_gradients['input_norm'],'cuda_allocated':torch.cuda.memory_allocated(),'cuda_peak':torch.cuda.max_memory_allocated()})
        if updates in (20,50,100):
            atomic_adapter(root/'artifacts'/f'adapter-{updates:03d}.safetensors',adapters,{**provenance,'completed_updates':str(updates)})
            save_checkpoint(root/'artifacts',adapters,optimizer,updates,provenance)
            snapshot={}
            for evaluation_spec in fixed_tuples():
                with torch.no_grad():evaluation,truth=predict(evaluation_spec.tuple_id)
                evals+=1
                snapshot[evaluation_spec.tuple_id]={'loss':float(velocity_mse(evaluation,truth)),'delta':prediction_delta(evaluation,cpu[evaluation_spec.tuple_id]['baseline_velocity'])}
                if evaluation_spec.tuple_id=='holdout':holdout_prediction=evaluation.cpu()
            snapshots[str(updates)]=snapshot
            atomic_json(root/'reports/evaluation-snapshots.json',snapshots)
            del evaluation,truth
            if updates==20:
                old_final=producer/'artifacts/adapter-final.safetensors'
                assert hashlib.sha256(old_final.read_bytes()).hexdigest()==original_receipt['adapter_sha256']==consumer['assets']['adapter-final.safetensors']
                old_values=load_file(str(old_final),device='cpu')
                replay={'adapter':{key+'.'+name:replay_check(getattr(layer,name),old_values[key+'.'+name]) for key,layer in adapters.items() for name in ('lora_A','lora_B')},'loss':{key:{**replay_check(torch.tensor(row['loss'],dtype=torch.float64),torch.tensor(original_receipt['after'][key],dtype=torch.float64)),'b020_improvement':original_receipt['before'][key]['loss']-original_receipt['after'][key]} for key,row in snapshot.items()}}
                replay['passed']=all(row['passed'] for group in ('adapter','loss') for row in replay[group].values())
                atomic_json(root/'reports/replay20.json',replay)
                assert replay['passed'],'REPLAY_MISMATCH_STOP_BEFORE_UPDATE21'
        atomic_json(root/'reports/train-progress.json',{'updates':rows,'tail_evaluations':evals});phase('train_update_'+str(updates))
        del pred,target,loss,old
    assert (hashes(block),hashes(head))==base_before
    atomic_adapter(root/'artifacts/adapter-final.safetensors',adapters,provenance)
    after={key:row['loss'] for key,row in snapshots['100'].items()}
    del block,head,adapters,parameters,optimizer
    gc.collect();torch.cuda.empty_cache()
    block,head,adapters=build();load_adapters(root/'artifacts/adapter-final.safetensors',adapters)
    with torch.no_grad():pred,_=predict('holdout')
    evals+=1;assert holdout_prediction is not None
    reload=check_parity(pred,holdout_prediction.to('cuda'));assert reload['passed']
    for layer in adapters.values():layer.enabled=False
    with torch.no_grad():pred,_=predict('holdout')
    evals+=1;off=check_parity(pred,cpu['holdout']['baseline_velocity'].to('cuda'));assert off['passed']
    assert (hashes(block),hashes(head))==base_before
    assert all(digest(v)==stored[k] for k,v in selected.items())
    assert updates==100 and evals==18
    atomic_json(root/'artifacts/training_receipt.json',{'status':'FM_TAIL_UPDATE_RELOAD_PASS','updates':updates,'tail_evaluations':evals,'before':before,'after':after,'reload':reload,'off':off,'base_unchanged':True,'adapter_sha256':hashlib.sha256((root/'artifacts/adapter-final.safetensors').read_bytes()).hexdigest(),'prefix_receipt_sha256':hashlib.sha256((producer/'artifacts/prefix_receipt.json').read_bytes()).hexdigest(),'code_sha256':provenance['code_sha256'],'producer':'B-020','consumer':'B-021','initial_sha256':hashlib.sha256(initial.read_bytes()).hexdigest(),'snapshots':snapshots,'optimizer_options':optimizer_options,'replay20':replay})
