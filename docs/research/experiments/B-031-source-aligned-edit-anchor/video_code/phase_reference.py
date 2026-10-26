# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
# Run only through run_phase.py ENC in the pinned SCAIL environment.
"""Encode one approved R1 anchor; no T5, driving encode, target, or DiT."""
from pathlib import Path
import copy
import gc
import hashlib
import json
import torch
from PIL import Image
from artifacts import atomic_json, load_tree, save_tree
from anchor_contract import changed_reference_leaves
from contracts import verify_parent_receipt
from cuda_probe import tiny
from runtime_observe import phase


def run(root: Path, cfg: dict) -> None:
    verify_parent_receipt(root)
    binding=json.loads((root/'configs/cache_binding.json').read_text())
    parent=Path(binding['producer_worker'])
    approval=json.loads((root/'configs/anchor_suitability.json').read_text())
    assert approval['task_id']==cfg['task_id'] and approval['reference_id']=='R1'
    assert approval['suitable'] is True and approval['qwen_process_exited'] is True
    anchor=tiny(root)
    from wan.modules.vae import WanVAE
    from wan.modules.clip import CLIPModel
    from wan.configs import SCAIL_CONFIGS
    from wan.utils.scail_utils import load_image_to_tensor_chw_normalized,resize_for_rectangle_crop,extract_and_compress_mask_to_latent
    config=SCAIL_CONFIGS['SCAIL-14B'];device=torch.device('cuda:0')
    tree,meta=load_tree(parent/'artifacts/conditions.safetensors',device='cpu')
    def read_image(path: Path) -> torch.Tensor:
        value=load_image_to_tensor_chw_normalized(Image.open(path).convert('RGB'))
        return resize_for_rectangle_crop(value,(512,896),reshape_mode='center').squeeze(0)
    rgb=read_image(root/cfg['reference']);mask=read_image(root/cfg['reference_mask'])
    assert list(rgb.shape)==list(mask.shape)==[3,512,896]
    prefix=extract_and_compress_mask_to_latent(mask.unsqueeze(1),additional_spatial_downsample=1)
    assert list(prefix.shape)==[28,1,64,112] and not bool(prefix[0::7].any())
    observed={key:{'shape':list(value.shape),'dtype':str(value.dtype),'sha256':hashlib.sha256(value.contiguous().numpy().tobytes()).hexdigest()} for key,value in (('reference',rgb),('mask',mask),('mask_prefix',prefix))}
    atomic_json(root/'reports/reference-preprocessed.json',observed)
    phase('vae_load_start')
    vae=WanVAE(vae_pth=str(root/'models'/config.vae_checkpoint),device=device)
    phase('vae_load_end');phase('anchor_vae_encode_start')
    with torch.no_grad():
        ref=vae.encode([rgb[:,None].to(device)])[0].cpu()
    assert ref.shape==tree['arg_c']['ref_latents'][0].shape and ref.dtype==tree['arg_c']['ref_latents'][0].dtype and bool(torch.isfinite(ref).all())
    torch.cuda.synchronize();phase('anchor_vae_encode_end')
    scaling={'mean':vae.mean.cpu().tolist(),'std':vae.std.cpu().tolist(),'normalization':'official WanVAE wrapper only'}
    del vae;gc.collect();torch.cuda.empty_cache();phase('vae_released')
    phase('clip_load_start')
    clip=CLIPModel(dtype=config.clip_dtype,device=device,checkpoint_path=str(root/'models'/config.clip_checkpoint),tokenizer_path=str(root/'models'/config.clip_tokenizer))
    phase('clip_load_end');phase('anchor_clip_encode_start')
    with torch.no_grad():
        embedding=clip.visual([rgb[:,None].to(device)]).cpu()
    assert embedding.shape==tree['arg_c']['clip_fea'].shape and embedding.dtype==tree['arg_c']['clip_fea'].dtype and bool(torch.isfinite(embedding).all())
    torch.cuda.synchronize();phase('anchor_clip_encode_end')
    del clip;gc.collect();torch.cuda.empty_cache();phase('clip_released')
    for branch in ('arg_c','arg_null'):
        prior=tree[branch]
        assert prior['replace_flag'] is True and prior['additional_ref_latents'] is None
        assert not bool(prior['ref_masks'][0][:,1:].any())
        prior['ref_latents']=[ref.clone()];prior['clip_fea']=embedding.clone()
        prior['ref_masks']=[torch.cat([prefix,prior['ref_masks'][0][:,1:].clone()],dim=1)]
    provenance=copy.deepcopy(meta['provenance'])
    provenance['anchor_derivation']={'experiment':'B-031','parent_cache_sha256':meta['file_sha256'],'builder_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'code_sha256':hashlib.sha256((root/'PREREGISTERED_CODE.json').read_bytes()).hexdigest(),'reference_rgb_sha256':hashlib.sha256((root/cfg['reference']).read_bytes()).hexdigest(),'reference_mask_sha256':hashlib.sha256((root/cfg['reference_mask']).read_bytes()).hexdigest(),'config':cfg,'scaling':scaling,'anchor_suitability_sha256':hashlib.sha256((root/'configs/anchor_suitability.json').read_bytes()).hexdigest()}
    save_tree(root/'artifacts/conditions.safetensors',tree,provenance)
    newmeta=json.loads((root/'artifacts/conditions.json').read_text())
    newmeta['structure']=copy.deepcopy(meta['structure']);atomic_json(root/'artifacts/conditions.json',newmeta)
    changed=changed_reference_leaves(meta['tensors'],newmeta['tensors'])
    assert torch.equal(anchor.cpu(),torch.full((16,),5.0))
    counts={'reference_VAE':1,'reference_CLIP':1,'reference_mask_helper':1,'T5':0,'driving_VAE':0,'target_VAE':0,'DiT':0}
    atomic_json(root/'reports/reference-encoding.json',{'status':'CONDITIONS_READY','changed_leaves':sorted(changed),'identical_leaves':sorted(set(meta['tensors'])-changed),'structure_devices_unchanged':True,'counts':counts})
    atomic_json(root/'artifacts/conditions_receipt.json',{'experiment':'B-031','reference_id':'R1','task_id':cfg['task_id'],'changed_leaves':sorted(changed),'hashes':{name:hashlib.sha256((root/'artifacts'/name).read_bytes()).hexdigest() for name in ('conditions.safetensors','conditions.json','initial_noise.pt')},'code_sha256':provenance['anchor_derivation']['code_sha256']})
    phase('CONDITION_CACHE_PASS')
