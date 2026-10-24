"""One bounded official attention-component smoke; no video or full model."""
from __future__ import annotations
import functools
import hashlib
import importlib
import json
from pathlib import Path
import sys
import time
import traceback
import torch
from torch import nn
from safetensors import safe_open
from safetensors.torch import save_file
from lora_component import LowRankLinear, save_adapters, load_adapters

PREFIX = 'blocks.39.self_attn.'

def runtime_dtype(name: str) -> torch.dtype:
    return torch.float32 if name.startswith(('norm_q.','norm_k.')) else torch.bfloat16

def digest(tensor: torch.Tensor) -> str:
    return hashlib.sha256(tensor.detach().cpu().contiguous().view(torch.uint8).numpy().tobytes()).hexdigest()

def frozen_hashes(module: nn.Module) -> dict[str, str]:
    return {name:digest(p) for name,p in module.named_parameters() if not p.requires_grad}

def memory() -> dict[str, int]:
    return {'cuda_allocated':torch.cuda.memory_allocated(), 'cuda_reserved':torch.cuda.memory_reserved(),
            'cuda_peak_allocated':torch.cuda.max_memory_allocated()}

def run(root: Path) -> None:
    started=time.monotonic(); reports=root/'reports'; outputs=root/'outputs'; outputs.mkdir(exist_ok=True)
    config=json.loads((root/'configs/smoke.json').read_text())
    runtime=json.loads((root/'configs/runtime-private.json').read_text())
    assert config['maximum_updates']==3 and config['maximum_attention_forwards']==8
    assert config['rank']==config['alpha']==4 and config['lr']==1e-4 and config['weight_decay']==0
    checkpoint_stat=Path(runtime['checkpoint']).stat()
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
        assert Path(official.__file__).resolve()==Path(runtime['upstream'])/'wan/modules/model_scail2.py'
        assert official.WanSelfAttention.forward.__globals__['flash_attention'] is attention.flash_attention
        (reports/'runtime-contract.json').write_text(json.dumps({'torch':torch.__version__,'cuda':torch.version.cuda,'fa2_available':attention.FLASH_ATTN_2_AVAILABLE,'fa3_available':attention.FLASH_ATTN_3_AVAILABLE,'module_path':official.__file__,'source_hashes':discovery['sources'],'config':config,'code_hashes':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (root/'code').glob('*.py')}},indent=2))
        selected:dict[str,torch.Tensor]={}; tensor_manifest=[]
        with safe_open(runtime['checkpoint'],framework='pt',device='cpu') as reader:
            for key,entry in discovery['selected'].items():
                tensor=reader.get_tensor(key)
                assert tensor.dtype==torch.float32 and list(tensor.shape)==entry['shape']
                selected[key.removeprefix(PREFIX)]=tensor
                tensor_manifest.append({'key':key,'shape':list(tensor.shape),'stored_dtype':str(tensor.dtype),'bytes':tensor.numel()*tensor.element_size(),'stored_sha256':digest(tensor)})
        assert sum(row['bytes'] for row in tensor_manifest)<=2**30
        (reports/'selected-tensors-read.json').write_text(json.dumps(tensor_manifest,indent=2))
        def component() -> nn.Module:
            with torch.device('meta'):
                module=official.WanSelfAttention(5120,40,qk_norm=True,eps=1e-6)
            runtime_state={name:value.to(device='cuda',dtype=runtime_dtype(name)) for name,value in selected.items()}
            result=module.load_state_dict(runtime_state,strict=True,assign=True)
            assert not result.missing_keys and not result.unexpected_keys
            module.requires_grad_(False)
            assert digest(module.norm_q.weight)==digest(selected['norm_q.weight'])
            assert digest(module.norm_k.weight)==digest(selected['norm_k.weight'])
            return module
        model=component(); before=frozen_hashes(model)
        cpu_rng=torch.Generator(device='cpu').manual_seed(config['seed'])
        x=torch.randn((1,36,5120),generator=cpu_rng,dtype=torch.float32).to(device='cuda',dtype=torch.bfloat16)
        target=torch.randn((1,36,5120),generator=cpu_rng,dtype=torch.float32).to('cuda')
        freqs=torch.cat([official.rope_params(8192,44),official.rope_params(8192,42),official.rope_params(8192,42)],dim=1).to('cuda')
        rope_kwargs=dict(freqs=freqs,ref_length=16,seq_length=16,pose_length=4,additional_ref_length=0,rope_T=1,rope_H=4,rope_W=4,rope_T_shift={'ref':0,'video':1,'pose':1},rope_H_shift={'ref':0,'video':0,'pose':0},rope_W_shift={'ref':0,'video':0,'pose':120})
        save_file({'x':x.cpu().contiguous(),'target':target.cpu().contiguous(),'cpu_rng_after_fixture':cpu_rng.get_state()},str(outputs/'synthetic-fixture.safetensors'))
        rope=functools.partial(official.rope_apply_scail,**rope_kwargs)
        lengths=torch.tensor([36],dtype=torch.int64,device='cuda')
        def forward(module: nn.Module) -> torch.Tensor:
            nonlocal forwards, completed_forwards
            forwards+=1
            with torch.autocast('cuda',dtype=torch.bfloat16):
                result=module(x,lengths,rope)
            completed_forwards+=1; assert torch.isfinite(result).all()
            return result
        with torch.no_grad(): baseline=forward(model)
        adapters={'q':LowRankLinear(model.q,rank=4,alpha=4.0),'v':LowRankLinear(model.v,rank=4,alpha=4.0)}
        model.q=adapters['q'];model.v=adapters['v']
        with torch.no_grad(): zero=forward(model)
        zero_error=float((zero.float()-baseline.float()).abs().max())
        assert torch.allclose(zero,baseline,rtol=config['rtol'],atol=config['atol'])
        params=[p for layer in adapters.values() for p in layer.adapter_parameters()]
        assert {id(p) for p in params}=={id(p) for p in model.parameters() if p.requires_grad}
        optimizer=torch.optim.AdamW(params,lr=1e-4,weight_decay=0)
        assert {id(p) for group in optimizer.param_groups for p in group['params']}=={id(p) for p in params}
        cast_base=frozen_hashes(model)
        provenance={'classification':'TEST_ONLY_NOT_FOR_INFERENCE','prefix':PREFIX,'source_revision':config['source_revision']}
        save_adapters(outputs/'adapter-initial.safetensors',adapters,provenance)
        history=[]
        for index in range(3):
            step_started=time.monotonic()
            optimizer.zero_grad(set_to_none=True)
            old=[p.detach().clone() for p in params]
            prediction=forward(model);loss=(prediction.float()-target).square().mean()
            assert torch.isfinite(loss)
            graph_names:set[str]=set();seen:set[int]=set();pending=[loss.grad_fn];graph_refs=[]
            while pending:
                node=pending.pop()
                if node is None or id(node) in seen:continue
                seen.add(id(node));graph_refs.append(node);graph_names.add(type(node).__name__)
                pending.extend(child for child,_ in node.next_functions)
            assert any('FlashAttn' in name and 'Backward' in name for name in graph_names),sorted(graph_names)
            loss.backward();torch.cuda.synchronize()
            grads={f'{name}.{part}':{'present':p.grad is not None,'finite':bool(torch.isfinite(p.grad).all()) if p.grad is not None else False,'norm':float(p.grad.norm()) if p.grad is not None else None,'dtype':str(p.grad.dtype) if p.grad is not None else None} for name,layer in adapters.items() for part,p in zip(('A','B'),layer.adapter_parameters())}
            assert all(row['present'] and row['finite'] for row in grads.values())
            assert grads['q.B']['norm']>0 and grads['v.B']['norm']>0
            assert all(p.grad is None for p in model.parameters() if not p.requires_grad)
            optimizer.step();updates+=1
            deltas=[float((p.detach()-previous).norm()) for p,previous in zip(params,old)]
            assert any(delta>0 for delta in deltas)
            assert frozen_hashes(model)==cast_base
            history.append({'update':updates,'loss':float(loss.detach()),'gradients':grads,'adapter_delta_norms':deltas,'step_seconds':time.monotonic()-step_started,'autograd_nodes':sorted(graph_names),'optimizer_state_dtypes':sorted({str(value.dtype) for state in optimizer.state.values() for value in state.values() if isinstance(value,torch.Tensor)}),'elapsed_seconds':time.monotonic()-started,**memory()})
            (reports/'updates.json').write_text(json.dumps(history,indent=2))
        assert any(row['gradients']['q.A']['norm']>0 for row in history[1:])
        assert any(row['gradients']['v.A']['norm']>0 for row in history[1:])
        save_adapters(outputs/'adapter-final.safetensors',adapters,provenance)
        with torch.no_grad(): trained=forward(model).detach()
        final_adapter={name:{'A':digest(layer.lora_A),'B':digest(layer.lora_B)} for name,layer in adapters.items()}
        del model,adapters,optimizer,params,prediction,loss,graph_refs,pending,node,old
        torch.cuda.empty_cache()
        fresh=component();assert frozen_hashes(fresh)==before
        fresh_adapters={'q':LowRankLinear(fresh.q,rank=4,alpha=4.0),'v':LowRankLinear(fresh.v,rank=4,alpha=4.0)}
        fresh.q=fresh_adapters['q'];fresh.v=fresh_adapters['v']
        load_adapters(outputs/'adapter-final.safetensors',fresh_adapters)
        assert {name:{'A':digest(layer.lora_A),'B':digest(layer.lora_B)} for name,layer in fresh_adapters.items()}==final_adapter
        with torch.no_grad(): reloaded=forward(fresh)
        assert torch.allclose(reloaded,trained,rtol=config['rtol'],atol=config['atol'])
        for layer in fresh_adapters.values():layer.enabled=False
        with torch.no_grad(): disabled=forward(fresh)
        assert torch.allclose(disabled,baseline,rtol=config['rtol'],atol=config['atol'])
        assert forwards==completed_forwards==8 and updates==3
        assert frozen_hashes(fresh)==cast_base
        assert all(digest(selected[row['key'].removeprefix(PREFIX)])==row['stored_sha256'] for row in tensor_manifest)
        after_stat=Path(runtime['checkpoint']).stat()
        assert after_stat.st_size==checkpoint_stat.st_size and after_stat.st_mtime_ns==checkpoint_stat.st_mtime_ns
        result={'status':'COMPONENT_UPDATE_RELOAD_PASS','optimizer_updates':updates,'attention_forwards':forwards,'completed_attention_forwards':completed_forwards,'zero_error_max':zero_error,'reload_error_max':float((reloaded-trained).abs().max()),'off_error_max':float((disabled-baseline).abs().max()),'input_sha256':digest(x),'target_sha256':digest(target),'shape':list(x.shape),'base_runtime_dtype':'projections BF16; norm_q/norm_k parameters FP32 (existing mixed policy); norm internal FP32 unchanged','adapter_dtype':'torch.float32','checkpoint_stat_unchanged':True,'stored_selected_payload_hashes_unchanged':True,'fresh_frozen_base_hashes':frozen_hashes(fresh),'frozen_runtime_hashes':before,'frozen_wrapped_hashes':cast_base,'actual_fa_backend':'FA2 official flash_attention wrapper','elapsed_seconds':time.monotonic()-started,**memory(),'FULL_MODEL_TRAINING':'NOT_RUN','VIDEO_QUALITY':'NOT_RUN','IDENTITY_POSE_DISENTANGLEMENT':'NOT_RUN'}
        (reports/'result.json').write_text(json.dumps(result,indent=2))
    except (Exception, KeyboardInterrupt):
        (reports/'result.json').write_text(json.dumps({'status':'FAILED_COMPONENT','optimizer_updates':updates,'attention_forwards':forwards,'completed_attention_forwards':completed_forwards,'traceback':traceback.format_exc(),'elapsed_seconds':time.monotonic()-started},indent=2))
        raise

if __name__=='__main__':
    run(Path(sys.argv[1]))
