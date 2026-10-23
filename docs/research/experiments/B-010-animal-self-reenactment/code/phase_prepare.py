"""P: official conditioning graph with T5/CLIP/VAE only; no DiT construction."""
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import torch
from artifacts import save_tree,atomic_json
from contracts import active_contract
from extract import install_prepare
from runtime_observe import phase
from media import inputs

class Prepared(Exception):
    """Controlled boundary after verified condition write, before any DiT call."""


def run(root:Path,cfg:dict) -> None:
    from wan.modules.t5 import T5EncoderModel
    from wan.modules.clip import CLIPModel
    from wan.modules.vae import WanVAE
    from wan.configs import SCAIL_CONFIGS
    import wan.scail as official
    config=SCAIL_CONFIGS['SCAIL-14B']; device=torch.device('cuda:0');models=root/'models'
    phase('encoders_load_start')
    owner=SimpleNamespace(device=device,rank=0,t5_cpu=True,param_dtype=config.param_dtype,num_train_timesteps=config.num_train_timesteps,vae_stride=config.vae_stride,patch_size=config.patch_size,model=None)
    owner.text_encoder=T5EncoderModel(text_len=config.text_len,dtype=config.t5_dtype,device=torch.device('cpu'),checkpoint_path=str(models/config.t5_checkpoint),tokenizer_path=str(models/config.t5_tokenizer),shard_fn=None)
    owner.vae=WanVAE(vae_pth=str(models/config.vae_checkpoint),device=device)
    owner.clip=CLIPModel(dtype=config.clip_dtype,device=device,checkpoint_path=str(models/config.clip_checkpoint),tokenizer_path=str(models/config.clip_tokenizer))
    phase('encoders_load_end')
    source=inputs(root,cfg)
    contract=active_contract(root)
    observed={key:{'shape':list(value.shape),'dtype':str(value.dtype),'sha256':hashlib.sha256(value.contiguous().numpy().tobytes()).hexdigest()} for key,value in source.items()}
    assert observed==json.loads((root/'configs/expected_preprocessed.json').read_text())
    atomic_json(root/'reports/preprocessed_inputs.json',observed)
    torch.save(source,root/'artifacts/preprocessed_inputs.pt')
    def persist(noise,arg_c,arg_null,history,generator,scheduler,segment_index,start,end):
        assert history is None and (segment_index,start,end)==(0,0,17)
        digest=hashlib.sha256(noise.detach().cpu().numpy().tobytes()).hexdigest()
        assert list(noise.shape)==contract.latent_shape and bool(torch.isfinite(noise).all())
        assert tuple(owner.vae_stride)==(4,8,8)
        torch.save(noise.detach().cpu(),root/'artifacts/initial_noise.pt')
        torch.cuda.synchronize();phase('conditions_save_start')
        save_tree(root/'artifacts/conditions.safetensors',{'noise':noise,'arg_c':arg_c,'arg_null':arg_null,'history':history,'generator_state':generator.get_state(),'timesteps':scheduler.timesteps,'sigmas':scheduler.sigmas}, {'experiment':'B-010','case':contract.name,'preprocessed_inputs':observed,'observed_vae_stride':list(owner.vae_stride),'config':cfg,'initial_noise_sha256':digest,'source_method_hash':method_hash,'history':None,'segment':[0,17],'vae_mean_std':[owner.vae.mean.detach().cpu().tolist(),owner.vae.std.detach().cpu().tolist()],'vae_scale':[part.detach().cpu().tolist() for part in owner.vae.scale],'normalization':'Official WanVAE encode/decode wrapper; no external scaling','input_hashes':json.loads((root/'configs/input_config_hashes.json').read_text()),'code':json.loads((root/'PREREGISTERED_CODE.json').read_text()),'models':json.loads((root/'PREREGISTERED_INPUTS.json').read_text())})
        atomic_json(root/'artifacts/conditions_receipt.json',{'experiment':'B-010','case':contract.name,'code_sha256':hashlib.sha256((root/'PREREGISTERED_CODE.json').read_bytes()).hexdigest(),'hashes':{name:hashlib.sha256((root/'artifacts'/name).read_bytes()).hexdigest() for name in ('conditions.safetensors','conditions.json','initial_noise.pt')},'initial_noise_sha256':digest})
        phase('CONDITION_CACHE_PASS');raise Prepared
    method,method_hash=install_prepare(official,persist)
    try:
        method(owner,input_prompt=cfg['prompt'],**source,replace_flag=False,segment_len=17,segment_overlap=5,shift=3.0,sample_solver='unipc',sampling_steps=40,guide_scale=5.0,seed=cfg['seed'],offload_model=True)
    except Prepared:
        return
    raise RuntimeError('Condition boundary not reached')
