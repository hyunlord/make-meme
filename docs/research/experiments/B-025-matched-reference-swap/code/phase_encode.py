"""Single common text encode and IG-only VAE/CLIP encode; no DiT or target."""
from pathlib import Path
import copy
import gc
import hashlib
import json
import torch
from PIL import Image
from artifacts import load_tree,save_tree,atomic_json
from runtime_observe import phase
from cuda_probe import tiny
from contracts import verify_parent_receipt
from pair_contract import pair_changes


def run(root:Path,cfg:dict)->None:
    verify_parent_receipt(root)
    anchor=tiny(root);experiment=(root/'experiment').resolve();parent=root/'producer'
    from wan.modules.vae import WanVAE
    from wan.modules.clip import CLIPModel
    from wan.modules.t5 import T5EncoderModel
    from wan.configs import SCAIL_CONFIGS
    from wan.utils.scail_utils import load_image_to_tensor_chw_normalized,resize_for_rectangle_crop,extract_and_compress_mask_to_latent
    config=SCAIL_CONFIGS['SCAIL-14B'];device=torch.device('cuda:0')
    old,meta=load_tree(parent/'artifacts/conditions.safetensors',device='cpu')
    lab=copy.deepcopy(old);ig=copy.deepcopy(old)
    phase('common_t5_start')
    text=T5EncoderModel(text_len=config.text_len,dtype=config.t5_dtype,device=torch.device('cpu'),checkpoint_path=str(root/'models'/config.t5_checkpoint),tokenizer_path=str(root/'models'/config.t5_tokenizer),shard_fn=None)
    with torch.no_grad():context=text([cfg['prompt']],torch.device('cpu'))
    assert len(context)==1 and context[0].dtype==old['arg_c']['context'][0].dtype and bool(torch.isfinite(context[0]).all())
    lab['arg_c']['context']=[context[0].clone()];ig['arg_c']['context']=[context[0].clone()]
    del text;gc.collect();torch.cuda.empty_cache();phase('common_t5_released')
    def image(path):
        return resize_for_rectangle_crop(load_image_to_tensor_chw_normalized(Image.open(path).convert('RGB')),(512,896),reshape_mode='center').squeeze(0)
    img=image(root/'inputs/IG/reference.png');mask=image(root/'inputs/IG/reference-mask.png')
    prefix=extract_and_compress_mask_to_latent(mask.unsqueeze(1),additional_spatial_downsample=1)
    assert list(prefix.shape)==[28,1,64,112] and not bool(prefix[0::7].any())
    phase('ig_vae_start');vae=WanVAE(vae_pth=str(root/'models'/config.vae_checkpoint),device=device)
    with torch.no_grad():ref=vae.encode([img[:,None].to(device)])[0].cpu()
    assert ref.shape==old['arg_c']['ref_latents'][0].shape and ref.dtype==old['arg_c']['ref_latents'][0].dtype and bool(torch.isfinite(ref).all())
    del vae;gc.collect();torch.cuda.empty_cache();phase('ig_vae_released')
    phase('ig_clip_start');clip=CLIPModel(dtype=config.clip_dtype,device=device,checkpoint_path=str(root/'models'/config.clip_checkpoint),tokenizer_path=str(root/'models'/config.clip_tokenizer))
    with torch.no_grad():clipvalue=clip.visual([img[:,None].to(device)]).cpu()
    assert clipvalue.shape==old['arg_c']['clip_fea'].shape and clipvalue.dtype==old['arg_c']['clip_fea'].dtype and bool(torch.isfinite(clipvalue).all())
    del clip;gc.collect();torch.cuda.empty_cache();phase('ig_clip_released')
    for branch in ('arg_c','arg_null'):
        ig[branch]['ref_latents']=[ref.clone()];ig[branch]['clip_fea']=clipvalue.clone()
        prior=old[branch]['ref_masks'][0];assert not bool(prior[:,1:].any())
        ig[branch]['ref_masks']=[torch.cat([prefix,prior[:,1:].clone()],dim=1)]
    metas={}
    for case,tree in [('LAB',lab),('IG',ig)]:
        dest=experiment/'cases'/case/'artifacts'
        provenance={'experiment':'B-025','reference_id':case,'parent_experiment':'B-024','parent_cache_sha256':meta['file_sha256'],'producer_receipt_sha256':hashlib.sha256((parent/'artifacts/conditions_receipt.json').read_bytes()).hexdigest(),'code_sha256':hashlib.sha256((root/'PREREGISTERED_CODE.json').read_bytes()).hexdigest(),'builder_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'shared_positive_encoding_count':1,'IG_VAE_CLIP_count_each':1,'Lab_VAE_CLIP_count_each':0,'T5_negative_count':0}
        save_tree(dest/'conditions.safetensors',tree,provenance)
        newmeta=json.loads((dest/'conditions.json').read_text());newmeta['structure']=copy.deepcopy(meta['structure']);atomic_json(dest/'conditions.json',newmeta);metas[case]=newmeta
        atomic_json(dest/'conditions_receipt.json',{'experiment':'B-025','case':'real','reference_id':case,'hashes':{n:hashlib.sha256((dest/n).read_bytes()).hexdigest() for n in ('conditions.safetensors','conditions.json','initial_noise.pt')},'producer_receipt_sha256':provenance['producer_receipt_sha256'],'code_sha256':provenance['code_sha256']})
    changed=pair_changes(metas['LAB']['tensors'],metas['IG']['tensors'])
    assert {k for k in meta['tensors'] if meta['tensors'][k]!=metas['LAB']['tensors'][k]}=={'t1'}
    assert torch.equal(anchor.cpu(),torch.full((16,),5.0))
    atomic_json(experiment/'reports/pair-conditions.json',{'status':'PASS','changed_pair_leaves':sorted(changed),'identical_pair_leaves':sorted(set(meta['tensors'])-changed),'LAB_vs_B024_changed':['t1'],'structure_devices_unchanged':True,'counts':{'positive_T5':1,'negative_T5':0,'IG_VAE':1,'IG_CLIP':1,'LAB_VAE':0,'LAB_CLIP':0,'P_full':0},'case_hashes':{c:m['file_sha256'] for c,m in metas.items()}})
