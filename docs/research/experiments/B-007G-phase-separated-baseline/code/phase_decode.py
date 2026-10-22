"""D: official VAE only; same full-frame decode, clamp, raw and native-fps writer."""
import json
from pathlib import Path
import subprocess
import torch
from artifacts import load_tree,atomic_json
from runtime_observe import phase


def run(root:Path,cfg:dict) -> None:
    from wan.modules.vae import WanVAE
    from wan.configs import SCAIL_CONFIGS
    from wan.utils.utils import cache_video
    config=SCAIL_CONFIGS['SCAIL-14B'];device=torch.device('cuda:0')
    phase('vae_load_start')
    vae=WanVAE(vae_pth=str(root/'models'/config.vae_checkpoint),device=device)
    phase('vae_load_end')
    tree,meta=load_tree(root/'artifacts/final_latent.safetensors')
    assert meta['provenance']['counters']=={'model_calls':80,'completed_steps':40}
    phase('vae_decode_start')
    with torch.cuda.amp.autocast(dtype=config.param_dtype),torch.no_grad():
        videos=vae.decode(tree['x0'])
        # Original single-segment output assembly, including CPU->device return.
        result=torch.cat([videos[0].cpu()],dim=1).to(device)
    torch.cuda.synchronize();phase('vae_decode_end')
    assert list(result.shape)==[3,17,512,896] and bool(torch.isfinite(result).all())
    phase('decoded_raw_save_start')
    torch.save(result.cpu(),root/'artifacts/raw_output.pt')
    phase('decoded_raw_save_end');phase('video_encode_start')
    output=root/'artifacts/output.mp4'
    cache_video(tensor=result[None],save_file=str(output),fps=16,nrow=1,normalize=True,value_range=(-1,1))
    subprocess.run(['ffmpeg','-v','error','-i',str(output),'-f','null','-'],check=True)
    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-of','json',str(output)]))['streams'][0]
    assert (int(probe['nb_frames']),probe['avg_frame_rate'],probe['width'],probe['height'])==(17,'16/1',896,512)
    atomic_json(root/'reports/video.json',{'status':'VIDEO_OUTPUT_PASS','shape':list(result.shape),'finite':True,'probe':probe,'quality':'UNVERIFIED'})
    phase('VIDEO_OUTPUT_PASS')
