"""One source encode and bounded full-frame VAE decodes, no other models."""
from pathlib import Path
import hashlib
import json
import subprocess
import numpy as np
from PIL import Image
import torch
from safetensors.torch import load_file,save_file
from artifacts import load_tree,save_tree,atomic_json
from runtime_observe import phase
from clean_constraint import mix_clean


def decode(vae,latent:torch.Tensor,root:Path,label:str,config)->None:
    from wan.utils.utils import cache_video
    output=root/'outputs'/label;output.mkdir(parents=True,exist_ok=True)
    with (output/'decode-attempt.json').open('x') as stream:json.dump({'attempt':1,'label':label},stream)
    phase(label+'_decode_start')
    with torch.no_grad(),torch.cuda.amp.autocast(dtype=config.param_dtype):
        result=vae.decode([latent.to('cuda')])[0]
    torch.cuda.synchronize();phase(label+'_decode_end')
    assert list(result.shape)==[3,17,512,896] and bool(torch.isfinite(result).all())
    raw=result.cpu();torch.save(raw,output/'raw_output.pt')
    frames=output/'frames';frames.mkdir(exist_ok=True)
    pixels=((raw.float().clamp(-1,1)+1)*127.5).floor().to(torch.uint8).permute(1,2,3,0).numpy()
    for i,frame in enumerate(pixels):Image.fromarray(frame).save(frames/f'{i:03d}.png')
    cache_video(tensor=result[None],save_file=str(output/'output.mp4'),fps=24,nrow=1,normalize=True,value_range=(-1,1))
    subprocess.run(['ffmpeg','-v','error','-i',str(output/'output.mp4'),'-f','null','-'],check=True)
    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-of','json',str(output/'output.mp4')]))['streams'][0]
    assert (int(probe['nb_frames']),probe['avg_frame_rate'],probe['width'],probe['height'])==(17,'24/1',896,512)
    atomic_json(output/'verification.json',{'shape':list(raw.shape),'finite':True,'probe':probe,'temporal':'UNVERIFIED','raw_sha256':hashlib.sha256((output/'raw_output.pt').read_bytes()).hexdigest()})
    phase(label+'_saved')


def run(root:Path,cfg:dict)->None:
    from wan.modules.vae import WanVAE
    from wan.configs import SCAIL_CONFIGS
    config=SCAIL_CONFIGS['SCAIL-14B'];execution=json.loads((root/'configs/execution.json').read_text())
    phase('vae_load_start');vae=WanVAE(vae_pth=str(root/'models'/config.vae_checkpoint),device=torch.device('cuda:0'));phase('vae_load_end')
    if execution['stage']=='CONTROL_D':
        source,source_meta=load_tree(root/'artifacts/source_latent.safetensors',device='cpu')
        decode(vae,source['z_src'],root,'SOURCE_RECON',config)
        base,base_meta=load_tree(root/'artifacts/final_latent.safetensors',device='cpu')
        assert base_meta['provenance']['method']=='BASE'
        mask=load_file(str(root/'inputs/mask_latent.safetensors'))['M']
        final=mix_clean(base['x0'][0],source['z_src'],mask)
        save_tree(root/'artifacts/final_only_latent.safetensors',{'x0':[final]},{'source_sha256':source_meta['file_sha256'],'baseline_final_sha256':base_meta['file_sha256'],'operation':'M*z_base+(1-M)*z_src','not_sampler':True})
        decode(vae,final,root,'FINAL_LATENT_ONLY',config)
    else:
        tree,metadata=load_tree(root/'artifacts/final_latent.safetensors',device='cpu')
        assert metadata['provenance']['counters']=={'model_calls':80,'completed_steps':40}
        assert metadata['provenance']['method']==execution['method']
        assert metadata['provenance']['constraint_calls']==(40 if execution['method']=='STEP' else 0)
        decode(vae,tree['x0'][0],root,'BASE' if execution['method']=='BASE' else 'STEP_CONSTRAINED',config)
