# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
# Run by run_phase.py ENC in the unchanged pinned environment.
"""Only VAE/CLIP reference reencoding, preserving each B027 cache and RNG."""
from pathlib import Path
import copy
import hashlib
import json
import shutil
import torch
from PIL import Image
from artifacts import save_tree, load_tree, atomic_json
from cuda_probe import tiny
from pair_contract import pair_changes
from runtime_observe import phase


def run(root: Path, cfg: dict) -> None:
    anchor=tiny(root)
    from wan.modules.clip import CLIPModel
    from wan.modules.vae import WanVAE
    from wan.configs import SCAIL_CONFIGS
    from wan.utils.scail_utils import load_image_to_tensor_chw_normalized,resize_for_rectangle_crop,extract_and_compress_mask_to_latent
    experiment=(root/'experiment').resolve()
    parent=(experiment/'parent_b027').resolve()
    config=SCAIL_CONFIGS['SCAIL-14B']; device=torch.device('cuda:0')
    phase('reference_encoders_load_start')
    vae=WanVAE(vae_pth=str(root/'models'/config.vae_checkpoint),device=device)
    clip_model=CLIPModel(dtype=config.clip_dtype,device=device,checkpoint_path=str(root/'models'/config.clip_checkpoint),tokenizer_path=str(root/'models'/config.clip_tokenizer))
    phase('reference_encoders_load_end')
    metas={}; rows=[]
    digest=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
    def image(path):
        return resize_for_rectangle_crop(load_image_to_tensor_chw_normalized(Image.open(path).convert('RGB')),(512,896),reshape_mode='center').squeeze(0)
    for case in ('R1','R2'):
        old=parent/'cases'/case/'artifacts'; dest=experiment/'cases'/case/'artifacts'
        tree,old_meta=load_tree(old/'conditions.safetensors',device='cpu')
        ref_image=image(experiment/'inputs'/case/'reference.png')
        mask=image(experiment/'inputs'/case/'reference-mask.png')
        prefix=extract_and_compress_mask_to_latent(mask.unsqueeze(1),additional_spatial_downsample=1)
        assert list(prefix.shape)==[28,1,64,112] and not bool(prefix[0::7].any())
        phase(case+'_reference_encode_start')
        with torch.no_grad():
            ref=vae.encode([ref_image[:,None].to(device)])[0].cpu()
            clip=clip_model.visual([ref_image[:,None].to(device)]).cpu()
        assert list(ref.shape)==[16,1,64,112] and bool(torch.isfinite(ref).all()) and bool(torch.isfinite(clip).all())
        for branch in ('arg_c','arg_null'):
            arg=tree[branch]
            assert arg['replace_flag'] is True
            assert ref.shape==arg['ref_latents'][0].shape and ref.dtype==arg['ref_latents'][0].dtype
            assert clip.shape==arg['clip_fea'].shape and clip.dtype==arg['clip_fea'].dtype
            assert not bool(arg['ref_masks'][0][:,1:].any())
            arg['ref_latents']=[ref.clone()];arg['clip_fea']=clip.clone()
            arg['ref_masks']=[torch.cat([prefix,arg['ref_masks'][0][:,1:].clone()],dim=1)]
        case_cfg=json.loads((experiment/'configs'/f'{case}.json').read_text())
        provenance={**old_meta['provenance'],'experiment':'B-028','parent_experiment':'B-027','parent_cache_sha256':old_meta['file_sha256'],
            'config':case_cfg,'reference_id':case,'reference_only_reencode':True,
            'reference_rgb_sha256':digest(experiment/case_cfg['reference']),
            'reference_mask_sha256':digest(experiment/case_cfg['reference_mask']),
            'code_sha256':digest(root/'PREREGISTERED_CODE.json'),
            'reference_preprocessed_sha256':hashlib.sha256(ref_image.contiguous().numpy().tobytes()).hexdigest(),
            'preprocessed_inputs_scope':'Inherited B027 preprocessed_inputs describes parent; new reference is recorded separately'}
        save_tree(dest/'conditions.safetensors',tree,provenance)
        meta=json.loads((dest/'conditions.json').read_text())
        meta['structure']=copy.deepcopy(old_meta['structure'])
        atomic_json(dest/'conditions.json',meta)
        shutil.copy2(old/'initial_noise.pt',dest/'initial_noise.pt')
        changed=pair_changes(old_meta['tensors'],meta['tensors'])
        assert all(old_meta['tensors'][key]['shape']==meta['tensors'][key]['shape'] and old_meta['tensors'][key]['dtype']==meta['tensors'][key]['dtype'] for key in old_meta['tensors'])
        assert tree['arg_c']['ref_latents'][0].equal(tree['arg_null']['ref_latents'][0])
        rows.append({'case':case,'parent_cache_sha256':old_meta['file_sha256'],'changed':sorted(changed),'preserved':sorted(set(meta['tensors'])-changed),'structure_and_dtype_preserved':True})
        atomic_json(dest/'conditions_receipt.json',{'experiment':'B-028','case':'public','task_id':cfg['task_id'],'reference_id':case,'code_sha256':provenance['code_sha256'],'hashes':{name:digest(dest/name) for name in ('conditions.safetensors','conditions.json','initial_noise.pt')}})
        metas[case]=meta
        phase(case+'_reference_encode_complete')
    changed=pair_changes(metas['R1']['tensors'],metas['R2']['tensors'])
    atomic_json(experiment/'reports/pair-conditions.json',{'status':'PASS','changed_pair_leaves':sorted(changed),'identical_pair_leaves':sorted(set(metas['R1']['tensors'])-changed),'structure_devices_unchanged':True,'parent_comparisons':rows,'counts':{'positive_T5':0,'negative_T5':0,'driving_VAE':0,'R1_VAE':1,'R1_CLIP':1,'R2_VAE':1,'R2_CLIP':1,'target_VAE':0,'DiT':0},'case_hashes':{case:meta['file_sha256'] for case,meta in metas.items()}})
    assert torch.equal(anchor.cpu(),torch.full((16,),5.0))
    phase('CONDITION_CACHE_PASS')
