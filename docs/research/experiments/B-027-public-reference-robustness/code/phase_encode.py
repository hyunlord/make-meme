# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
# Run using the existing pinned SCAIL environment; do not install dependencies.
"""One official public P plus reference-only R2 encoding; no DiT or target encode."""
from pathlib import Path
from types import SimpleNamespace
import copy
import gc
import hashlib
import json
import shutil
import torch
from PIL import Image
from artifacts import save_tree, atomic_json
from contracts import active_contract
from cuda_probe import tiny
from extract import install_prepare
from media import inputs
from pair_contract import pair_changes
from runtime_observe import phase

class Prepared(Exception):
    """Stop the official method at its first sampler boundary, without a forward."""


def run(root: Path, cfg: dict) -> None:
    anchor=tiny(root)
    from wan.modules.t5 import T5EncoderModel
    from wan.modules.clip import CLIPModel
    from wan.modules.vae import WanVAE
    from wan.configs import SCAIL_CONFIGS
    from wan.utils.scail_utils import load_image_to_tensor_chw_normalized,resize_for_rectangle_crop,extract_and_compress_mask_to_latent
    import wan.scail as official
    experiment=(root/'experiment').resolve();models=root/'models'
    config=SCAIL_CONFIGS['SCAIL-14B'];device=torch.device('cuda:0')
    contract=active_contract(root)
    source=inputs(root,cfg)
    observed={key:{'shape':list(value.shape),'dtype':str(value.dtype),'sha256':hashlib.sha256(value.contiguous().numpy().tobytes()).hexdigest()} for key,value in source.items()}
    assert observed==json.loads((root/'configs/expected_preprocessed.json').read_text())
    atomic_json(root/'reports/preprocessed_inputs.json',observed)
    phase('encoders_load_start')
    owner=SimpleNamespace(device=device,rank=0,t5_cpu=True,param_dtype=config.param_dtype,num_train_timesteps=config.num_train_timesteps,vae_stride=config.vae_stride,patch_size=config.patch_size,model=None)
    owner.text_encoder=T5EncoderModel(text_len=config.text_len,dtype=config.t5_dtype,device=torch.device('cpu'),checkpoint_path=str(models/config.t5_checkpoint),tokenizer_path=str(models/config.t5_tokenizer),shard_fn=None)
    owner.vae=WanVAE(vae_pth=str(models/config.vae_checkpoint),device=device)
    owner.clip=CLIPModel(dtype=config.clip_dtype,device=device,checkpoint_path=str(models/config.clip_checkpoint),tokenizer_path=str(models/config.clip_tokenizer))
    phase('encoders_load_end')
    captured={}
    def persist(noise,arg_c,arg_null,history,generator,scheduler,segment_index,start,end):
        assert history is None and (segment_index,start,end)==(0,0,17)
        assert list(noise.shape)==contract.latent_shape and bool(torch.isfinite(noise).all())
        assert tuple(owner.vae_stride)==(4,8,8)
        assert arg_c['replace_flag'] is True and arg_null['replace_flag'] is True
        captured.update(noise=noise,arg_c=arg_c,arg_null=arg_null,history=history,generator_state=generator.get_state(),timesteps=scheduler.timesteps,sigmas=scheduler.sigmas)
        raise Prepared
    method,method_hash=install_prepare(official,persist)
    try:
        method(owner,input_prompt=cfg['prompt'],**source,replace_flag=True,segment_len=17,segment_overlap=5,shift=3.0,sample_solver='unipc',sampling_steps=40,guide_scale=5.0,n_prompt='',seed=cfg['seed'],offload_model=True)
    except Prepared:
        phase('official_condition_boundary')
    assert captured and owner.model is None
    del owner.text_encoder;gc.collect();torch.cuda.empty_cache()
    first=experiment/'cases/R1/artifacts'
    noise=captured['noise'].detach().cpu()
    torch.save(noise,first/'initial_noise.pt')
    provenance={'experiment':'B-027','task_id':cfg['task_id'],'source_method_hash':method_hash,'preprocessed_inputs':observed,'config':cfg,'history':None,'segment':[0,17],'observed_vae_stride':list(owner.vae_stride),'normalization':'Official WanVAE encode/decode wrapper; no external scaling','initial_noise_sha256':hashlib.sha256(noise.numpy().tobytes()).hexdigest(),'model_manifest':json.loads((root/'PREREGISTERED_INPUTS.json').read_text()),'code_sha256':hashlib.sha256((root/'PREREGISTERED_CODE.json').read_bytes()).hexdigest()}
    save_tree(first/'conditions.safetensors',captured,{**provenance,'reference_id':'R1','reference_rgb_sha256':hashlib.sha256((root/cfg['reference']).read_bytes()).hexdigest(),'reference_mask_sha256':hashlib.sha256((root/cfg['reference_mask']).read_bytes()).hexdigest()})
    from artifacts import load_tree
    second_tree,first_meta=load_tree(first/'conditions.safetensors',device='cpu')
    captured.clear();gc.collect();torch.cuda.empty_cache()
    def image(path):
        return resize_for_rectangle_crop(load_image_to_tensor_chw_normalized(Image.open(path).convert('RGB')),(512,896),reshape_mode='center').squeeze(0)
    ref2=image(experiment/'inputs/R2/reference.png')
    mask2=image(experiment/'inputs/R2/reference-mask.png')
    prefix=extract_and_compress_mask_to_latent(mask2.unsqueeze(1),additional_spatial_downsample=1)
    assert list(prefix.shape)==[28,1,64,112] and not bool(prefix[0::7].any())
    phase('reference2_encode_start')
    with torch.no_grad():
        ref=owner.vae.encode([ref2[:,None].to(device)])[0].cpu()
        owner.clip.model.to(device)
        clip=owner.clip.visual([ref2[:,None].to(device)]).cpu()
    assert list(ref.shape)==[16,1,64,112] and bool(torch.isfinite(ref).all()) and bool(torch.isfinite(clip).all())
    for branch in ('arg_c','arg_null'):
        prior=second_tree[branch]
        assert ref.shape==prior['ref_latents'][0].shape and ref.dtype==prior['ref_latents'][0].dtype
        assert clip.shape==prior['clip_fea'].shape and clip.dtype==prior['clip_fea'].dtype
        assert not bool(prior['ref_masks'][0][:,1:].any())
        prior['ref_latents']=[ref.clone()];prior['clip_fea']=clip.clone()
        prior['ref_masks']=[torch.cat([prefix,prior['ref_masks'][0][:,1:].clone()],dim=1)]
    second=experiment/'cases/R2/artifacts'
    shutil.copy2(first/'initial_noise.pt',second/'initial_noise.pt')
    second_cfg=json.loads((experiment/'configs/R2.json').read_text())
    save_tree(second/'conditions.safetensors',second_tree,{**provenance,'config':second_cfg,'reference_id':'R2','parent_cache_sha256':first_meta['file_sha256'],'reference_only_reencode':True,'reference_rgb_sha256':hashlib.sha256((experiment/second_cfg['reference']).read_bytes()).hexdigest(),'reference_mask_sha256':hashlib.sha256((experiment/second_cfg['reference_mask']).read_bytes()).hexdigest()})
    second_meta=json.loads((second/'conditions.json').read_text())
    second_meta['structure']=copy.deepcopy(first_meta['structure'])
    atomic_json(second/'conditions.json',second_meta)
    metas={'R1':first_meta,'R2':second_meta}
    for case in ('R1','R2'):
        dest=experiment/'cases'/case/'artifacts'
        atomic_json(dest/'conditions_receipt.json',{'experiment':'B-027','case':'public','task_id':cfg['task_id'],'reference_id':case,'code_sha256':provenance['code_sha256'],'hashes':{name:hashlib.sha256((dest/name).read_bytes()).hexdigest() for name in ('conditions.safetensors','conditions.json','initial_noise.pt')}})
    changed=pair_changes(first_meta['tensors'],second_meta['tensors'])
    atomic_json(experiment/'reports/pair-conditions.json',{'status':'PASS','changed_pair_leaves':sorted(changed),'identical_pair_leaves':sorted(set(first_meta['tensors'])-changed),'structure_devices_unchanged':True,'counts':{'positive_T5':1,'negative_T5':1,'driving_VAE':1,'R1_VAE':1,'R1_CLIP':1,'R2_VAE':1,'R2_CLIP':1,'target_VAE':0,'DiT':0},'case_hashes':{case:meta['file_sha256'] for case,meta in metas.items()}})
    assert torch.equal(anchor.cpu(),torch.full((16,),5.0))
    phase('CONDITION_CACHE_PASS')
