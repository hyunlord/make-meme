"""Four frozen positive full forwards; cache the exact final-block boundary."""
from pathlib import Path
import hashlib
import json
import torch
from safetensors.torch import load_file
from artifacts import save_tree,load_tree,atomic_json
from cuda_probe import tiny,recheck,restore
from runtime_observe import phase
from staged_loader import load_model
from fm_contract import fixed_tuples,mix_velocity,CacheBinding


def run(root:Path,cfg:dict) -> None:
    anchor=tiny(root)
    from wan.modules.model_scail2 import SCAIL2Model
    phase('prefix_full_load_start')
    model=load_model(str(root/'upstream/configs/config-14b.json'),str(root/'models/SCAIL.safetensors'),phase_hook=phase)
    assert isinstance(model,SCAIL2Model)
    model.eval().requires_grad_(False)
    recheck(root,anchor,'prefix_loaded_anchor')
    tree,conditions_meta=restore(root)
    target_tree,target_meta=load_tree(root/'artifacts/target.safetensors',device='cpu')
    z_y=target_tree['z_y'];assert z_y.dtype==torch.float32
    noises=load_file(str(root/'inputs/fm-noises.safetensors'))
    fm=json.loads((root/'configs/fm.json').read_text())
    geometry_hash=hashlib.sha256(json.dumps([cfg['height'],cfg['width'],cfg['frames'],cfg['fps']],separators=(',',':')).encode()).hexdigest()
    def digest(value):return hashlib.sha256(value.contiguous().view(torch.uint8).numpy().tobytes()).hexdigest()
    captured={}; receipts=[]
    def capture_block(_module,args,kwargs):
        assert not captured
        captured['h38']=args[0].detach()
        captured['block_kwargs']={key:value for key,value in kwargs.items() if key not in ('rope_apply_func','freqs')}
        captured['freqs_real']=torch.view_as_real(kwargs['freqs']).detach()
    def capture_head(_module,args):
        captured['head_e']=args[1].detach()
    handle_block=model.blocks[39].register_forward_pre_hook(capture_block,with_kwargs=True)
    handle_head=model.head.register_forward_pre_hook(capture_head)
    model.to('cuda');recheck(root,anchor,'prefix_model_cuda_anchor')
    for spec in fixed_tuples():
        phase('prefix_'+spec.tuple_id+'_start')
        mixed=mix_velocity(z_y,noises[spec.tuple_id],spec.sigma)
        with torch.no_grad(),torch.autocast('cuda',dtype=torch.bfloat16):
            predicted=model([mixed.z_sigma.to('cuda')],t=mixed.timestep.to('cuda'),**tree['arg_c'])[0]
        torch.cuda.synchronize();assert torch.isfinite(predicted).all()
        assert set(captured)=={'h38','block_kwargs','freqs_real','head_e'}
        assert captured['block_kwargs']['additional_ref_length']==0
        captured.update(target=mixed.target,baseline_velocity=predicted,z_sigma=mixed.z_sigma,epsilon=mixed.noise)
        binding=CacheBinding(tuple_id=spec.tuple_id,sigma=spec.sigma,seed=spec.seed,noise_hash=digest(mixed.noise),z_y_hash=digest(z_y),conditions_hash=conditions_meta['file_sha256'],model_hash=fm['model_sha256'],geometry_hash=geometry_hash,code_hash=hashlib.sha256((root/'PREREGISTERED_CODE.json').read_bytes()).hexdigest())
        assert binding.noise_hash==fm['noise_hashes'][spec.tuple_id]
        path=root/'artifacts'/('prefix-'+spec.tuple_id+'.safetensors')
        save_tree(path,captured,{'experiment':'B-020','binding':binding.model_dump(),'config':cfg,'tuple_id':spec.tuple_id,'sigma':spec.sigma,'seed':spec.seed,'target_sha256':target_meta['file_sha256'],'conditions_sha256':conditions_meta['file_sha256'],'code':json.loads((root/'PREREGISTERED_CODE.json').read_text()),'source_forward':'official full positive forward; no adapter; same call supplies final velocity','freqs_serialization':'complex128 viewed as float64 real/imag, exact inverse view required'})
        receipts.append({'tuple_id':spec.tuple_id,'file_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'sidecar_sha256':hashlib.sha256(path.with_suffix('.json').read_bytes()).hexdigest()})
        captured.clear();del predicted,mixed
        atomic_json(root/'reports/prefix-progress.json',{'completed':len(receipts),'tuples':receipts})
        phase('prefix_'+spec.tuple_id+'_complete')
    handle_block.remove();handle_head.remove()
    assert len(receipts)==4
    atomic_json(root/'artifacts/prefix_receipt.json',{'status':'PASS','full_positive_forwards':4,'tuples':receipts,'code_sha256':hashlib.sha256((root/'PREREGISTERED_CODE.json').read_bytes()).hexdigest(),'conditions_sha256':conditions_meta['file_sha256'],'target_sha256':target_meta['file_sha256']})
