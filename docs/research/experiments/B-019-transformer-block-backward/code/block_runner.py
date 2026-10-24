"""One bounded official full-block backward; synthetic inputs only."""
from __future__ import annotations
import functools
import hashlib
import importlib
import json
from pathlib import Path
import sys
import time
import traceback
from typing import TypedDict, NotRequired
from types import ModuleType
from collections.abc import Callable
from torch.autograd.graph import Node
import torch
from torch import nn
from safetensors import safe_open
from safetensors.torch import load_file
from block_contract import runtime_dtype, token_layout, validate_conditions, validate_fixture
from lora_component import LowRankLinear, save_adapters, load_adapters

PREFIX = 'blocks.39.'

def digest(tensor: torch.Tensor) -> str:
    return hashlib.sha256(tensor.detach().cpu().contiguous().view(torch.uint8).numpy().tobytes()).hexdigest()

def frozen_hashes(module: nn.Module) -> dict[str, str]:
    return {name:digest(p) for name,p in module.named_parameters() if not p.requires_grad}

def memory() -> dict[str, int]:
    metrics={'unix_time_ns':time.time_ns(),'cuda_allocated':torch.cuda.memory_allocated(),
             'cuda_reserved':torch.cuda.memory_reserved(),'cuda_peak_allocated':torch.cuda.max_memory_allocated(),
             'cuda_peak_reserved':torch.cuda.max_memory_reserved()}
    for line in Path('/proc/self/status').read_text().splitlines():
        key=line.split(':',1)[0]
        if key in ('VmRSS','VmHWM','RssAnon','RssFile'):
            metrics[key+'_bytes']=int(line.split()[1])*1024
    for line in Path('/proc/meminfo').read_text().splitlines():
        key=line.split(':',1)[0]
        if key in ('MemAvailable','SwapFree','SwapTotal'):
            metrics[key+'_bytes']=int(line.split()[1])*1024
    relative=next(line.split(':',2)[2] for line in Path('/proc/self/cgroup').read_text().splitlines() if line.startswith('0::'))
    cgroup=Path('/sys/fs/cgroup')/relative.lstrip('/')
    for name in ('memory.current','memory.peak'):
        value=(cgroup/name).read_text().strip()
        if value.isdigit(): metrics['cgroup_'+name]=int(value)
    return metrics


class GradientRecord(TypedDict):
    present: bool
    finite: bool
    norm: float
    dtype: str

class LongReport(TypedDict):
    status: str
    forwards: int
    completed_forwards: int
    backwards: int
    completed_backwards: int
    optimizer_updates: int
    estimated_bytes: int
    estimate_is_upper_bound: bool
    system_available_before: int
    cuda_before: dict[str,int]
    reason: NotRequired[str]
    x_sha256: NotRequired[str]
    target_sha256: NotRequired[str]
    after_forward: NotRequired[dict[str,int]]
    after_backward: NotRequired[dict[str,int]]
    gradient_norms: NotRequired[dict[str,float]]
    input_gradient_norm: NotRequired[float]
    adapter_unchanged: NotRequired[bool]
    base_unchanged: NotRequired[bool]
    fa_backward_nodes: NotRequired[int]
    seconds: NotRequired[float]
    traceback: NotRequired[str]
    branch_gradients: NotRequired[dict[str,dict[str,float|bool]]]
    context_partitions: NotRequired[dict[str,float]]


def graph_fa_nodes(loss:torch.Tensor) -> int:
    pending:list[Node|None]=[loss.grad_fn]; seen:set[Node]=set()
    while pending:
        node=pending.pop()
        if node is None or node in seen: continue
        seen.add(node);pending.extend(child for child,_ in node.next_functions)
    return sum('FlashAttn' in type(node).__name__ and 'Backward' in type(node).__name__ for node in seen)


def partition_gradients(context:torch.Tensor) -> dict[str,float]:
    assert context.grad is not None and bool(torch.isfinite(context.grad).all())
    result={'image_norm':float(torch.linalg.vector_norm(context.grad[:,:257].float())),
            'text_norm':float(torch.linalg.vector_norm(context.grad[:,257:].float()))}
    assert all(value>0 for value in result.values())
    return result


def atomic_adapters(path:Path, modules:dict[str,LowRankLinear],provenance:dict[str,str]) -> None:
    import os
    temporary=path.with_name(path.stem+'.pending.safetensors')
    save_adapters(temporary,modules,provenance)
    for artifact in (temporary,temporary.with_suffix('.json')):
        with artifact.open('rb') as stream: os.fsync(stream.fileno())
    temporary.replace(path);temporary.with_suffix('.json').replace(path.with_suffix('.json'))
    directory=os.open(path.parent,os.O_RDONLY)
    try: os.fsync(directory)
    finally: os.close(directory)


def atomic_json(path: Path, value) -> None:
    import os
    temporary=path.with_suffix('.tmp')
    with temporary.open('w') as stream:
        json.dump(value,stream,indent=2);stream.flush();os.fsync(stream.fileno())
    temporary.replace(path)
    directory=os.open(path.parent,os.O_RDONLY)
    try: os.fsync(directory)
    finally: os.close(directory)


def wrap(module: nn.Module) -> dict[str,LowRankLinear]:
    adapters:dict[str,LowRankLinear]={}
    for name in ('q','v'):
        base=module.get_submodule('self_attn.'+name)
        assert isinstance(base,nn.Linear)
        adapters[name]=LowRankLinear(base,rank=4,alpha=4.0)
        module.set_submodule('self_attn.'+name,adapters[name])
    return adapters


def install_hooks(module: nn.Module, observations:dict[str,dict[str,float|bool]]) -> None:
    def hook_for(name:str) -> Callable[[nn.Module,torch.Tensor|tuple[torch.Tensor|None,...],torch.Tensor|tuple[torch.Tensor|None,...]],None]:
        def hook(_module:nn.Module, grad_input:torch.Tensor|tuple[torch.Tensor|None,...], grad_output:torch.Tensor|tuple[torch.Tensor|None,...]) -> None:
            assert isinstance(grad_input,tuple) and isinstance(grad_output,tuple)
            value=grad_input[0]; output=grad_output[0]
            assert isinstance(value,torch.Tensor) and isinstance(output,torch.Tensor)
            observations[name]={'input_norm':float(value.float().norm()),'input_finite':bool(torch.isfinite(value).all()),'output_norm':float(output.float().norm()),'output_finite':bool(torch.isfinite(output).all())}
            assert observations[name]['input_finite'] and observations[name]['output_finite']
        return hook
    for name in ('self_attn','cross_attn','ffn'):
        module.get_submodule(name).register_full_backward_hook(hook_for(name))


def run_long(module: nn.Module,context:torch.Tensor,e:torch.Tensor,freqs:torch.Tensor,official:ModuleType,config:dict[str,int],reports:Path) -> LongReport:
    import gc
    gc.collect()
    for name in ('q','v'):
        layer=module.get_submodule('self_attn.'+name)
        assert isinstance(layer,LowRankLinear);layer.enabled=True
    before={name:digest(p) for name,p in module.named_parameters() if p.requires_grad}
    base_before=frozen_hashes(module)
    branches:dict[str,dict[str,float|bool]]={}
    install_hooks(module,branches)
    layout=token_layout(True); nd=layout.total*5120*4; nf=layout.total*13824*4
    # Saved/temporary tensor inventory heuristic, not a proven allocator upper bound.
    activation_estimate=16*nd+4*nf+4*(2*nd)
    host_selected=config['selected_bytes']; runtime_base=sum(p.numel()*p.element_size() for p in module.parameters())
    estimate=activation_estimate+host_selected+runtime_base+2*1024**3
    available=int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:')))*1024
    report:LongReport={'status':'LONG_NOT_RUN','forwards':0,'completed_forwards':0,'backwards':0,'completed_backwards':0,'optimizer_updates':0,'estimated_bytes':estimate,'estimate_is_upper_bound':False,'system_available_before':available,'cuda_before':memory()}
    atomic_json(reports/'long-admission.json',report)
    if estimate>16*1024**3 or available<estimate+24*1024**3:
        report['reason']='Conservative preregistered estimate exceeds cap/headroom';return report
    started=time.monotonic()
    try:
        generator=torch.Generator(device='cpu').manual_seed(config['long_seed'])
        x=torch.randn((1,layout.total,5120),generator=generator,dtype=torch.float32).to(device='cuda',dtype=torch.bfloat16).requires_grad_(True)
        target=torch.randn((1,layout.total,5120),generator=generator,dtype=torch.float32).to('cuda')
        report['x_sha256']=digest(x);report['target_sha256']=digest(target)
        rope=functools.partial(official.rope_apply_scail,freqs=freqs,ref_length=layout.ref,seq_length=layout.video,pose_length=layout.pose,additional_ref_length=0,rope_T=layout.t,rope_H=layout.h,rope_W=layout.w,rope_T_shift={'ref':0,'video':1,'pose':1},rope_H_shift={'ref':0,'video':0,'pose':0},rope_W_shift={'ref':0,'video':0,'pose':120})
        lengths=torch.tensor([layout.total],device='cuda',dtype=torch.int64)
        report['forwards']=1;atomic_json(reports/'long-progress.json',report)
        with torch.autocast('cuda',dtype=torch.bfloat16):prediction=module(x,e,lengths,context,None,rope_apply_func=rope)
        torch.cuda.synchronize();assert torch.isfinite(prediction).all()
        report['completed_forwards']=1
        report['after_forward']=memory()
        loss=(prediction.float()-target).square().mean();assert torch.isfinite(loss)
        report['fa_backward_nodes']=graph_fa_nodes(loss);assert report['fa_backward_nodes']==3
        report['backwards']=1;atomic_json(reports/'long-progress.json',report)
        loss.backward();torch.cuda.synchronize()
        report['completed_backwards']=1
        report['context_partitions']=partition_gradients(context)
        report['branch_gradients']=dict(branches)
        assert all(branches[name]['input_norm']>0 for name in ('cross_attn','ffn'))
        assert frozen_hashes(module)==base_before
        report['base_unchanged']=True
        assert x.grad is not None and torch.isfinite(x.grad).all()
        grads={name:float(p.grad.float().norm()) for name,p in module.named_parameters() if p.requires_grad and p.grad is not None}
        assert len(grads)==4 and all(torch.isfinite(p.grad).all() for p in module.parameters() if p.grad is not None)
        assert all(p.grad is None for p in module.parameters() if not p.requires_grad)
        assert before=={name:digest(p) for name,p in module.named_parameters() if p.requires_grad}
        report.update(status='LONG_BLOCK_BACKWARD_PASS',gradient_norms=grads,input_gradient_norm=float(x.grad.float().norm()),adapter_unchanged=True,after_backward=memory(),seconds=time.monotonic()-started)
    except (Exception,KeyboardInterrupt):
        report.update(status='LONG_CAPACITY_BLOCKED',traceback=traceback.format_exc(),seconds=time.monotonic()-started)
    atomic_json(reports/'long-result.json',report)
    return report


def run(root: Path) -> None:
    started=time.monotonic(); reports=root/'reports'; outputs=root/'outputs'; outputs.mkdir(exist_ok=True)
    config=json.loads((root/'configs/smoke.json').read_text())
    runtime=json.loads((root/'configs/runtime-private.json').read_text())
    assert config['maximum_updates']==3 and config['maximum_block_forwards']==9
    assert config['rank']==config['alpha']==4 and config['lr']==1e-4 and config['weight_decay']==0
    checkpoint_stat=Path(runtime['checkpoint']).stat()
    fixture_manifest=json.loads((root/'configs/fixtures.json').read_text())
    for name,expected in fixture_manifest['files'].items():
        assert hashlib.sha256((root/'inputs'/name).read_bytes()).hexdigest()==expected
    assert len(json.loads((root/'configs/selected-tensors.json').read_text())['selected'])==32
    with (reports/'worker-attempt.json').open('x') as stream:
        json.dump({'status':'STARTED','maximum_updates':3,'maximum_workers':1,'classification':'SYNTHETIC_TENSOR_CONTRACT_TEST'},stream)
    updates=0; forwards=0; completed_forwards=0
    try:
        torch.manual_seed(config['seed'])
        tiny=torch.arange(16,dtype=torch.float32).to('cuda'); tiny=tiny+1; torch.cuda.synchronize()
        assert torch.equal(tiny.cpu(),torch.arange(16,dtype=torch.float32)+1)
        del tiny
        sys.path.insert(0,runtime['upstream'])
        official=importlib.import_module('wan.modules.model_scail2')
        attention=importlib.import_module('wan.modules.attention')
        assert attention.FLASH_ATTN_2_AVAILABLE and not attention.FLASH_ATTN_3_AVAILABLE
        discovery=json.loads((root/'configs/selected-tensors.json').read_text())
        for relative,expected in discovery['sources'].items():
            assert hashlib.sha256((Path(runtime['upstream'])/relative).read_bytes()).hexdigest()==expected
        assert official.__file__ is not None
        assert Path(official.__file__).resolve()==Path(runtime['upstream'])/'wan/modules/model_scail2.py'
        assert official.WanSelfAttention.forward.__globals__['flash_attention'] is attention.flash_attention
        assert official.WanI2VCrossAttention.forward.__globals__['flash_attention'] is attention.flash_attention
        (reports/'runtime-contract.json').write_text(json.dumps({'torch':torch.__version__,'cuda':torch.version.cuda,'fa2_available':attention.FLASH_ATTN_2_AVAILABLE,'fa3_available':attention.FLASH_ATTN_3_AVAILABLE,'module_path':official.__file__,'source_hashes':discovery['sources'],'config':config,'code_hashes':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (root/'code').glob('*.py')}},indent=2))
        selected:dict[str,torch.Tensor]={}; tensor_manifest=[]
        tensor=torch.empty(0)
        with safe_open(runtime['checkpoint'],framework='pt',device='cpu') as reader:
            for key,entry in discovery['selected'].items():
                tensor=reader.get_tensor(key)
                assert tensor.dtype==torch.float32 and list(tensor.shape)==entry['shape']
                selected[key.removeprefix(PREFIX)]=tensor
                tensor_manifest.append({'key':key,'shape':list(tensor.shape),'stored_dtype':str(tensor.dtype),'bytes':tensor.numel()*tensor.element_size(),'stored_sha256':digest(tensor)})
        assert sum(row['bytes'] for row in tensor_manifest)==discovery['selected_bytes']
        (reports/'selected-tensors-read.json').write_text(json.dumps(tensor_manifest,indent=2))
        def component() -> nn.Module:
            with torch.device('meta'):
                module=official.WanAttentionBlock('i2v_cross_attn',5120,13824,40,qk_norm=True,cross_attn_norm=True,eps=1e-6)
            runtime_state={name:value.to(device='cuda',dtype=runtime_dtype(name)) for name,value in selected.items()}
            result=module.load_state_dict(runtime_state,strict=True,assign=True)
            assert not result.missing_keys and not result.unexpected_keys
            module.requires_grad_(False)
            for name,parameter in module.named_parameters():
                if runtime_dtype(name)==torch.float32:
                    assert digest(parameter)==digest(selected[name])
            return module
        phases=[]
        model=component(); before=frozen_hashes(model)
        phases.append({'phase':'loaded',**memory()})
        fixture=load_file(str(root/'inputs/synthetic-fixture.safetensors'))
        validate_fixture(fixture['x'],fixture['target'],config['x_hash'],config['target_hash'])
        x=fixture['x'].to('cuda').requires_grad_(True); target=fixture['target'].to('cuda')
        conditions=load_file(str(root/'inputs/conditions.safetensors'))
        context=conditions['context'].to('cuda').requires_grad_(True); e=conditions['e'].to('cuda')
        validate_conditions(context,e)
        assert torch.isfinite(selected['modulation']+conditions['e']).all()
        assert ((selected['modulation']+conditions['e'])[:,(2,5)].abs()>0).all()
        freqs=torch.cat([official.rope_params(8192,44),official.rope_params(8192,42),official.rope_params(8192,42)],dim=1).to('cuda')
        rope_kwargs=dict(freqs=freqs,ref_length=16,seq_length=16,pose_length=4,additional_ref_length=0,rope_T=1,rope_H=4,rope_W=4,rope_T_shift={'ref':0,'video':1,'pose':1},rope_H_shift={'ref':0,'video':0,'pose':0},rope_W_shift={'ref':0,'video':0,'pose':120})
        rope=functools.partial(official.rope_apply_scail,**rope_kwargs)
        lengths=torch.tensor([36],dtype=torch.int64,device='cuda')
        def forward(module: nn.Module) -> torch.Tensor:
            nonlocal forwards, completed_forwards
            forwards+=1
            with torch.autocast('cuda',dtype=torch.bfloat16):
                result=module(x,e,lengths,context,None,rope_apply_func=rope)
            completed_forwards+=1; assert torch.isfinite(result).all()
            return result
        with torch.no_grad(): baseline=forward(model)
        adapters=wrap(model)
        load_adapters(root/'inputs/adapter-initial.safetensors',adapters)
        with torch.no_grad(): zero=forward(model)
        zero_error=float((zero.float()-baseline.float()).abs().max())
        assert torch.allclose(zero,baseline,rtol=config['rtol'],atol=config['atol'])
        params=[p for layer in adapters.values() for p in layer.adapter_parameters()]
        assert {id(p) for p in params}=={id(p) for p in model.parameters() if p.requires_grad}
        optimizer=torch.optim.AdamW(params,lr=1e-4,weight_decay=0)
        assert {id(p) for group in optimizer.param_groups for p in group['params']}=={id(p) for p in params}
        cast_base=frozen_hashes(model)
        provenance={'classification':'TEST_ONLY_NOT_FOR_INFERENCE','prefix':PREFIX,'source_revision':config['source_revision']}
        atomic_adapters(outputs/'adapter-initial.safetensors',adapters,provenance)
        branch_gradients:dict[str,dict[str,float|bool]]={}
        install_hooks(model,branch_gradients)
        history=[]
        for index in range(3):
            step_started=time.monotonic()
            optimizer.zero_grad(set_to_none=True); x.grad=None; context.grad=None; branch_gradients.clear()
            old=[p.detach().clone() for p in params]
            prediction=forward(model);loss=(prediction.float()-target).square().mean()
            assert torch.isfinite(loss)
            phases.append({'phase':f'update{index+1}_forward',**memory()})
            fa_nodes=graph_fa_nodes(loss)
            assert fa_nodes==3,fa_nodes
            loss.backward();torch.cuda.synchronize()
            assert x.grad is not None and context.grad is not None
            assert torch.isfinite(x.grad).all() and torch.isfinite(context.grad).all()
            assert all(branch_gradients[name]['input_norm']>0 for name in ('cross_attn','ffn'))
            phases.append({'phase':f'update{index+1}_backward',**memory()})
            grads:dict[str,GradientRecord]={f'{name}.{part}':{'present':p.grad is not None,'finite':bool(torch.isfinite(p.grad).all()) if p.grad is not None else False,'norm':float(torch.linalg.vector_norm(p.grad)) if p.grad is not None else 0.0,'dtype':str(p.grad.dtype) if p.grad is not None else 'missing'} for name,layer in adapters.items() for part,p in zip(('A','B'),layer.adapter_parameters())}
            assert all(row['present'] and row['finite'] for row in grads.values())
            assert grads['q.B']['norm']>0 and grads['v.B']['norm']>0
            assert all(p.grad is None for p in model.parameters() if not p.requires_grad)
            optimizer.step();updates+=1
            phases.append({'phase':f'update{index+1}_optimizer',**memory()})
            atomic_json(reports/'memory-phases.json',phases)
            deltas=[float((p.detach()-previous).norm()) for p,previous in zip(params,old)]
            assert any(delta>0 for delta in deltas)
            assert frozen_hashes(model)==cast_base
            history.append({'update':updates,'fa_backward_nodes':fa_nodes,'branch_gradients':dict(branch_gradients),'input_gradient_norm':float(x.grad.norm()),'context_gradient_norm':float(context.grad.norm()),'loss':float(loss.detach()),'gradients':grads,'adapter_delta_norms':deltas,'step_seconds':time.monotonic()-step_started,'context_partitions':partition_gradients(context),'optimizer_state_dtypes':sorted({str(value.dtype) for state in optimizer.state.values() for value in state.values() if isinstance(value,torch.Tensor)}),'elapsed_seconds':time.monotonic()-started,**memory()})
            atomic_json(reports/'updates.json',history)
            del prediction,loss,old
        assert any(row['gradients']['q.A']['norm']>0 for row in history[1:])
        assert any(row['gradients']['v.A']['norm']>0 for row in history[1:])
        atomic_adapters(outputs/'adapter-final.safetensors',adapters,provenance)
        with torch.no_grad(): trained=forward(model).detach()
        final_adapter={name:{'A':digest(layer.lora_A),'B':digest(layer.lora_B)} for name,layer in adapters.items()}
        del model,adapters,optimizer,params
        torch.cuda.empty_cache()
        fresh=component();assert frozen_hashes(fresh)==before
        fresh_adapters=wrap(fresh)
        load_adapters(outputs/'adapter-final.safetensors',fresh_adapters)
        assert {name:{'A':digest(layer.lora_A),'B':digest(layer.lora_B)} for name,layer in fresh_adapters.items()}==final_adapter
        with torch.no_grad(): reloaded=forward(fresh)
        assert torch.allclose(reloaded,trained,rtol=config['rtol'],atol=config['atol'])
        for layer in fresh_adapters.values():layer.enabled=False
        with torch.no_grad(): disabled=forward(fresh)
        assert torch.allclose(disabled,baseline,rtol=config['rtol'],atol=config['atol'])
        phases.append({'phase':'fresh_reload_off',**memory()})
        atomic_json(reports/'memory-phases.json',phases)
        assert forwards==completed_forwards==8 and updates==3
        assert frozen_hashes(fresh)==cast_base
        assert all(digest(selected[row['key'].removeprefix(PREFIX)])==row['stored_sha256'] for row in tensor_manifest)
        after_stat=Path(runtime['checkpoint']).stat()
        assert after_stat.st_size==checkpoint_stat.st_size and after_stat.st_mtime_ns==checkpoint_stat.st_mtime_ns
        result={'status':'SMALL_BLOCK_UPDATE_RELOAD_PASS','optimizer_updates':updates,'block_forwards':forwards,'completed_block_forwards':completed_forwards,'zero_error_max':zero_error,'reload_error_max':float((reloaded-trained).abs().max()),'off_error_max':float((disabled-baseline).abs().max()),'input_sha256':digest(x),'target_sha256':digest(target),'shape':list(x.shape),'base_runtime_dtype':'Linear BF16; all norm and modulation parameters original FP32','adapter_dtype':'torch.float32','checkpoint_stat_unchanged':True,'stored_selected_payload_hashes_unchanged':True,'fresh_frozen_base_hashes':frozen_hashes(fresh),'frozen_runtime_hashes':before,'frozen_wrapped_hashes':cast_base,'actual_fa_backend':'FA2 official flash_attention wrapper','elapsed_seconds':time.monotonic()-started,**memory(),'FULL_MODEL_TRAINING':'NOT_RUN','VIDEO_QUALITY':'NOT_RUN','IDENTITY_POSE_DISENTANGLEMENT':'NOT_RUN'}
        atomic_json(reports/'small-result.json',result)
        atomic_json(reports/'result.json',result)
        # The complete small result is durable before resource-only admission.
        del baseline,zero,trained,reloaded,disabled,target,component,fixture,conditions
        selected.clear();del tensor
        x=torch.empty(0)
        for parameter in fresh.parameters(): parameter.grad=None
        context.grad=None
        torch.cuda.empty_cache();torch.cuda.reset_peak_memory_stats()
        long_report=run_long(fresh,context,e,freqs,official,{'selected_bytes':config['selected_bytes'],'long_seed':config['long_seed']},reports)
        combined=dict(status='SMALL_BLOCK_UPDATE_RELOAD_PASS',small=result,long=long_report,block_forwards=8+long_report['forwards'],completed_block_forwards=8+long_report['completed_forwards'],backwards=3+long_report['backwards'],completed_backwards=3+long_report['completed_backwards'])
        atomic_json(reports/'result.json',combined)
    except (Exception, KeyboardInterrupt):
        (reports/'result.json').write_text(json.dumps({'status':'FAILED_BLOCK','optimizer_updates':updates,'block_forwards':forwards,'completed_block_forwards':completed_forwards,'traceback':traceback.format_exc(),'elapsed_seconds':time.monotonic()-started},indent=2))
        raise

if __name__=='__main__':
    run(Path(sys.argv[1]))
