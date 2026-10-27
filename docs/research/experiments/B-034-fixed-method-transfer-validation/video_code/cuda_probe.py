"""One bounded non-RNG CUDA operation plus exact original-device cache restore."""
import hashlib
import json
from pathlib import Path
import torch
from safetensors.torch import load_file
from artifacts import load_tree,atomic_json
from runtime_observe import phase
from contracts import verify_cache_receipt


def ancestors() -> dict:
    relative=next(line.split(':',2)[2] for line in Path('/proc/self/cgroup').read_text().splitlines() if line.startswith('0::'))
    current=Path('/sys/fs/cgroup')/relative.lstrip('/');records={}
    while current.is_relative_to('/sys/fs/cgroup'):
        records[str(current.relative_to('/sys/fs/cgroup'))]={name:(current/name).read_text() for name in ('memory.current','memory.high','memory.max','memory.events','memory.pressure') if (current/name).exists()}
        if current==Path('/sys/fs/cgroup'):break
        current=current.parent
    return records


def diagnostic(root:Path,label:str,*,cuda_success:bool=False) -> None:
    phase(label)
    record={'label':label,'is_initialized':torch.cuda.is_initialized(),'ancestors':ancestors(),'primary_context_get_state':'NOT_CALLED: no new driver binding introduced','diagnostic_side_effects':'is_initialized does not establish device allocation; mem_get_info only after tiny copy/kernel success'}
    if cuda_success:
        free,total=torch.cuda.mem_get_info();record['cuda_mem_get_info']={'free':free,'total':total}
    atomic_json(root/'reports'/f'{label}.json',record)


def tiny(root:Path) -> torch.Tensor:
    """64-byte retained anchor, no RNG operations; test allocation/copy/kernel/readback."""
    before=torch.get_rng_state().clone()
    diagnostic(root,'tiny_copy_start')
    cpu=torch.full((16,),3.0,dtype=torch.float32)
    anchor=cpu.to('cuda:0')
    phase('tiny_copy_end');phase('tiny_kernel_start')
    anchor.add_(2.0);torch.cuda.synchronize()
    assert torch.equal(anchor.cpu(),torch.full((16,),5.0))
    assert torch.equal(before,torch.get_rng_state())
    diagnostic(root,'tiny_kernel_complete',cuda_success=True)
    atomic_json(root/'reports/tiny.json',{'status':'PASS','retained_payload_bytes':anchor.numel()*anchor.element_size(),'cpu_rng_unchanged':True,'operations':['constant CPU fill','H2D copy','add_ constant','synchronize','D2H exact equality'],'CUDA_RNG':'No RNG operation invoked; initial CUDA state baseline captured only after successful real work'})
    return anchor


def recheck(root:Path,anchor:torch.Tensor,label:str) -> None:
    assert torch.equal(anchor.cpu(),torch.full((16,),5.0))
    anchor.add_(0.0);torch.cuda.synchronize()
    diagnostic(root,label,cuda_success=True)


def restore(root:Path):
    path=root/'artifacts/conditions.safetensors'
    cpu_tree,meta=load_tree(path,device='cpu');del cpu_tree
    receipt=verify_cache_receipt(root)
    assert meta['file_sha256']==receipt['hashes']['conditions.safetensors']
    values=load_file(str(path));rows=[]
    def inflate(node,location):
        if 'tensor' in node:
            key=node['tensor'];value=values[key];target=node['device']
            phase('cache_'+key+'_restore_start')
            row={'key':key,'location':location,'target_device':target,'bytes':value.numel()*value.element_size(),'shape':list(value.shape),'dtype':str(value.dtype),'status':'STARTED'}
            rows.append(row);atomic_json(root/'reports/cache_leaves.json',{'leaves':rows})
            restored=value.to(target)
            if restored.is_cuda:torch.cuda.synchronize()
            roundtrip=restored.detach().cpu().contiguous()
            if roundtrip.is_floating_point() or roundtrip.is_complex():assert bool(torch.isfinite(roundtrip).all())
            assert list(restored.shape)==meta['tensors'][key]['shape'] and restored.device==torch.device(target)
            digest=hashlib.sha256(roundtrip.view(torch.uint8).numpy().tobytes()).hexdigest()
            assert digest==meta['tensors'][key]['sha256'] and restored.dtype==value.dtype
            row.update(status='PASS',sha256=digest,actual_device=str(restored.device))
            atomic_json(root/'reports/cache_leaves.json',{'leaves':rows});phase('cache_'+key+'_restore_end')
            return restored
        if 'list' in node:return [inflate(item,location+f'[{i}]') for i,item in enumerate(node['list'])]
        if 'dict' in node:return {key:inflate(item,location+'.'+key) for key,item in node['dict'].items()}
        return node['scalar']
    tree=inflate(meta['structure'],'root')
    assert len(rows)==16
    return tree,meta


def run(root:Path,cfg:dict) -> None:
    # Same imports as S before its first large model construction.
    diagnostic(root,'before_official_import')
    from wan.utils.fm_solvers_unipc import FlowUniPCMultistepScheduler
    from wan.configs import SCAIL_CONFIGS
    assert callable(FlowUniPCMultistepScheduler) and SCAIL_CONFIGS['SCAIL-14B'].num_train_timesteps==1000
    diagnostic(root,'after_official_import')
    anchor=tiny(root)
    cuda_rng=torch.cuda.get_rng_state().clone()
    tree,meta=restore(root)
    assert tree['history'] is None
    assert torch.equal(cuda_rng,torch.cuda.get_rng_state())
    recheck(root,anchor,'probe_cache_restore_complete')
    atomic_json(root/'reports/probe.json',{'status':'PASS','cache_sha256':meta['file_sha256'],'cuda_rng_unchanged_after_tiny':True,'leaf_count':16})
