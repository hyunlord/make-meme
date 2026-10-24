"""One bounded VAE/CLIP worker: two old decodes and two reference encode sets."""
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


def run(root:Path,cfg:dict)->None:
    verify_parent_receipt(root)
    anchor=tiny(root)
    from wan.modules.vae import WanVAE
    from wan.modules.clip import CLIPModel
    from wan.configs import SCAIL_CONFIGS
    from wan.utils.scail_utils import load_image_to_tensor_chw_normalized,resize_for_rectangle_crop
    config=SCAIL_CONFIGS['SCAIL-14B'];device=torch.device('cuda:0');parent=root/'producer'
    old,meta=load_tree(parent/'artifacts/conditions.safetensors',device='cpu');tree=copy.deepcopy(old)
    def image(path):
        tensor=load_image_to_tensor_chw_normalized(Image.open(path).convert('RGB'))
        return resize_for_rectangle_crop(tensor,(512,896),reshape_mode='center').squeeze(0)
    original=image(parent/'inputs/clip/reference.png');neutral=image(root/cfg['reference'])
    expected=json.loads((root/'configs/expected_preprocessed.json').read_text())['img']
    original_sha=hashlib.sha256(original.contiguous().numpy().tobytes()).hexdigest()
    assert {'shape':list(original.shape),'dtype':str(original.dtype),'sha256':original_sha}==expected
    assert original.shape==neutral.shape and bool(torch.isfinite(neutral).all())
    comparisons={};new_values={};counts={'vae_decode_reference':0,'vae_decode_driving':0,'vae_encode_original':0,'vae_encode_neutral':0,'clip_original':0,'clip_neutral':0}
    def compare(name,value,cached):
        assert value.shape==cached.shape and value.dtype==cached.dtype and bool(torch.isfinite(value).all())
        delta=value.float()-cached.float()
        comparisons[name]={'shape':list(value.shape),'dtype':str(value.dtype),'max_abs':float(delta.abs().max()),'rms':float(delta.square().mean().sqrt()),'cached_rms':float(cached.float().square().mean().sqrt()),'reencoded_sha256':hashlib.sha256(value.contiguous().view(torch.uint8).numpy().tobytes()).hexdigest(),'cached_sha256':hashlib.sha256(cached.contiguous().view(torch.uint8).numpy().tobytes()).hexdigest(),'allclose_1e3_diagnostic_only':torch.allclose(value,cached,atol=1e-3,rtol=1e-3),'tolerance_role':'descriptive functional check, not byte replay acceptance gate'}
    phase('vae_load_start');vae=WanVAE(vae_pth=str(root/'models'/config.vae_checkpoint),device=device);phase('vae_load_end')
    with torch.no_grad():
        for kind,key in [('reference','ref_latents'),('driving','pose_latents')]:
            counts['vae_decode_'+kind]+=1;phase('old_'+kind+'_decode_start')
            value=vae.decode([old['arg_c'][key][0].to(device)])[0]
            expected_shape=[3,1,512,896] if kind=='reference' else [3,17,256,448]
            assert list(value.shape)==expected_shape and bool(torch.isfinite(value).all())
            torch.save(value.cpu(),root/'artifacts'/('decoded_'+kind+'.pt'));del value
            torch.cuda.synchronize();phase('old_'+kind+'_decode_end')
        for name,img in [('original',original),('neutral',neutral)]:
            counts['vae_encode_'+name]+=1;phase(name+'_vae_encode_start')
            value=vae.encode([img[:,None].to(device)])[0].cpu()
            assert list(value.shape)==[16,1,64,112] and value.dtype==torch.float32 and bool(torch.isfinite(value).all())
            if name=='original':compare('VAE_original_vs_parent',value,old['arg_c']['ref_latents'][0])
            else:new_values['ref']=value
            torch.cuda.synchronize();phase(name+'_vae_encode_end')
    scaling={'mean':vae.mean.cpu().tolist(),'std':vae.std.cpu().tolist(),'normalization':'official encode/decode wrapper only'}
    del vae;gc.collect();torch.cuda.empty_cache();phase('vae_released')
    phase('clip_load_start');clip=CLIPModel(dtype=config.clip_dtype,device=device,checkpoint_path=str(root/'models'/config.clip_checkpoint),tokenizer_path=str(root/'models'/config.clip_tokenizer));phase('clip_load_end')
    with torch.no_grad():
        for name,img in [('original',original),('neutral',neutral)]:
            counts['clip_'+name]+=1;phase(name+'_clip_start')
            value=clip.visual([img[:,None].to(device)]).cpu()
            assert value.shape==old['arg_c']['clip_fea'].shape and value.dtype==old['arg_c']['clip_fea'].dtype and bool(torch.isfinite(value).all())
            if name=='original':compare('CLIP_original_vs_parent',value,old['arg_c']['clip_fea'])
            else:new_values['clip']=value
            torch.cuda.synchronize();phase(name+'_clip_end')
    del clip;gc.collect();torch.cuda.empty_cache();phase('clip_released')
    for branch in ('arg_c','arg_null'):
        tree[branch]['ref_latents']=[new_values['ref'].clone()]
        tree[branch]['clip_fea']=new_values['clip'].clone()
        assert tree[branch]['replace_flag'] is True
    provenance={'experiment':'B-024','parent_cache_sha256':meta['file_sha256'],'parent_metadata_sha256':hashlib.sha256((parent/'artifacts/conditions.json').read_bytes()).hexdigest(),'producer_receipt_sha256':hashlib.sha256((parent/'artifacts/conditions_receipt.json').read_bytes()).hexdigest(),'builder_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'code_sha256':hashlib.sha256((root/'PREREGISTERED_CODE.json').read_bytes()).hexdigest(),'original_preprocessed_sha256':original_sha,'reference_input_sha256':hashlib.sha256((root/cfg['reference']).read_bytes()).hexdigest(),'scaling':scaling,'counts':counts}
    save_tree(root/'artifacts/conditions.safetensors',tree,provenance)
    newmeta=json.loads((root/'artifacts/conditions.json').read_text());newmeta['structure']=copy.deepcopy(meta['structure']);atomic_json(root/'artifacts/conditions.json',newmeta)
    changed={k for k,v in meta['tensors'].items() if v!=newmeta['tensors'][k]};assert changed=={'t2','t3','t8','t9'}
    assert len(meta['tensors'])==16 and counts=={'vae_decode_reference':1,'vae_decode_driving':1,'vae_encode_original':1,'vae_encode_neutral':1,'clip_original':1,'clip_neutral':1}
    assert torch.equal(anchor.cpu(),torch.full((16,),5.0))
    atomic_json(root/'reports/reference-encoding.json',{'status':'CONDITIONS_READY','original_encoder_comparison':comparisons,'counts':counts,'changed_leaves':sorted(changed),'identical_leaves':sorted(set(meta['tensors'])-changed),'structure_and_devices_unchanged':True,'scope':'same reference repeatability, no T5/DiT construction','concrete_pipeline_defect':'NONE_IDENTIFIED_BY_NUMERICAL_CHECKS; reconstruction visual review separate'})
    atomic_json(root/'artifacts/conditions_receipt.json',{'experiment':'B-024','case':'real','hashes':{n:hashlib.sha256((root/'artifacts'/n).read_bytes()).hexdigest() for n in ('conditions.safetensors','conditions.json','initial_noise.pt')},'producer_receipt_sha256':provenance['producer_receipt_sha256'],'code_sha256':provenance['code_sha256']})
