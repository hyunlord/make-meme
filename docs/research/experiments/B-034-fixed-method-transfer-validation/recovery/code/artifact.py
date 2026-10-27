"""Exact parent artifact boundary for an explicitly authorized decode consumer."""
from pathlib import Path
import hashlib,json,sys
import torch

FILE_SHA='687197642b668543d771a14ce8a78fcfa5e58dee91f526ffead26a92448f4d40'
TENSOR_SHA='3a0d6aacca1fe4342ba28b3ea1a12a5a0a2c7d83221226ae896c5cd1f0d322ad'

def verify(root:Path)->tuple[torch.Tensor,dict]:
    """Validate bytes, tree, finite FP32 and original generation provenance."""
    config=json.loads((root/'config.json').read_text());parent=Path(config['parent_root'])
    sys.path.insert(0,str(parent/'video_code'))
    from artifacts import load_tree
    path=parent/'tasks/rigid_R1/cases/BASE/artifacts/final_latent.safetensors'
    assert path.stat().st_size==2293840 and hashlib.sha256(path.read_bytes()).hexdigest()==FILE_SHA
    assert hashlib.sha256(path.with_suffix('.json').read_bytes()).hexdigest()=='d0402a0297c01e553d3145f59aa2296f3b53717583bbde657ebfcce08d802344'
    guard=json.loads((parent/'tasks/rigid_R1/stages/BASE_S/reports/pipeline-process.json').read_text());assert guard['reason']=='other_service_work' and guard['returncode']==0
    tree,meta=load_tree(path,device='cpu');assert set(tree)=={'x0'} and len(tree['x0'])==1
    value=tree['x0'][0];assert value.dtype==torch.float32 and list(value.shape)==[16,5,64,112] and bool(torch.isfinite(value).all())
    assert hashlib.sha256(value.contiguous().numpy().tobytes()).hexdigest()==TENSOR_SHA
    p=meta['provenance'];assert p['method']=='BASE' and p['constraint_calls']==0 and p['counters']=={'model_calls':80,'completed_steps':40}
    assert p['history'] is None and p['reference_prefix_included'] is False and p['adapter_enabled'] is False
    assert hashlib.sha256((parent/'tasks/rigid_R1/shared/conditions.safetensors').read_bytes()).hexdigest()==p['condition_sha256']
    for key in ('frames','height','width','fps'):assert p['config'][key]=={'frames':17,'height':512,'width':896,'fps':24}[key]
    receipt={'status':'VALIDATED','file_sha256':FILE_SHA,'bytes':2293840,'tensor_sha256':TENSOR_SHA,'shape':list(value.shape),'dtype':str(value.dtype),'finite':True,'sidecar_sha256':hashlib.sha256(path.with_suffix('.json').read_bytes()).hexdigest(),'condition_sha256':p['condition_sha256'],'model_provenance_sha256':hashlib.sha256(json.dumps(p['condition_provenance']['model_manifest'],sort_keys=True).encode()).hexdigest(),'parent_guard_reason':'other_service_work','not_initial_noise':True,'generated_only':True}
    return value,receipt

if __name__=='__main__':
    root=Path(sys.argv[1]);_,receipt=verify(root);(root/'reports/artifact.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt))
