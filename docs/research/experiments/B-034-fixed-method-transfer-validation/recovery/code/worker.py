"""VAE-only artifact consumer; no predecessor override or sampler path."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,time
import numpy as np
import torch
from PIL import Image
from artifact import verify

root=Path(sys.argv[1]);config=json.loads((root/'config.json').read_text())
with (root/'reports/worker-attempt.json').open('x') as out:json.dump({'attempt':1,'started':time.time()},out)
os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1')
freeze=json.loads((root/'freeze.json').read_text())
for name,digest in freeze['files'].items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest,name
for name,digest in freeze['external_files'].items():assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==digest,name
assert json.loads((root/'reports/start-safety.json').read_text())['decision']=='CLEAR'
latent,receipt=verify(root);assert receipt==json.loads((root/'reports/artifact.json').read_text())
sys.path.insert(0,config['upstream']);sys.path.insert(0,str(Path(config['parent_root'])/'video_code'))
from runtime_observe import initialize,phase
from artifacts import atomic_json
initialize(root/'reports/phases.jsonl')
from wan.modules.vae import WanVAE
from wan.configs import SCAIL_CONFIGS
cfg=SCAIL_CONFIGS['SCAIL-14B'];checkpoint=Path(config['models'])/cfg.vae_checkpoint
assert hashlib.sha256(checkpoint.read_bytes()).hexdigest()==config['vae_sha256']
phase('vae_load_start');vae=WanVAE(vae_pth=str(checkpoint),device=torch.device('cuda:0'));phase('vae_load_complete')
output=root/'outputs/BASE_D_RECOVERY_01';output.mkdir(parents=True)
with (output/'decode-attempt.json').open('x') as out:json.dump({'decode':1,'parent_sha256':receipt['file_sha256']},out)
phase('decode_start')
with torch.no_grad(),torch.cuda.amp.autocast(dtype=cfg.param_dtype):raw=vae.decode([latent.to('cuda')])[0]
torch.cuda.synchronize();phase('decode_complete')
assert list(raw.shape)==[3,17,512,896] and bool(torch.isfinite(raw).all())
raw=raw.cpu();torch.save(raw,output/'raw_output.pt')
frames=output/'frames';frames.mkdir()
pixels=((raw.float().clamp(-1,1)+1)*127.5).floor().to(torch.uint8).permute(1,2,3,0).numpy()
for index,frame in enumerate(pixels):Image.fromarray(frame).save(frames/f'{index:03d}.png')
phase('raw_and_png_saved')
subprocess.run(['ffmpeg','-v','error','-framerate','24','-i',str(frames/'%03d.png'),'-vf','scale=in_range=full:out_range=tv:out_color_matrix=bt709,format=yuv420p','-c:v','libx264','-crf','18','-color_range','tv','-colorspace','bt709','-color_primaries','bt709','-color_trc','bt709',str(output/'output.mp4')],check=True)
subprocess.run(['ffmpeg','-v','error','-i',str(output/'output.mp4'),'-f','null','-'],check=True)
probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-of','json',str(output/'output.mp4')]))['streams'][0]
assert (int(probe['nb_frames']),probe['width'],probe['height'],probe['avg_frame_rate'],probe['pix_fmt'])==(17,896,512,'24/1','yuv420p')
phase('mp4_verified')
atomic_json(root/'reports/result.json',{'decode':'PASS','shape':list(raw.shape),'finite':True,'frames':17,'source_fps':None,'preview_fps':24,'timebase_assumed':True,'temporal':'UNVERIFIED','parent':receipt,'probe':probe,'raw_sha256':hashlib.sha256((output/'raw_output.pt').read_bytes()).hexdigest(),'mp4_sha256':hashlib.sha256((output/'output.mp4').read_bytes()).hexdigest(),'new_sampler':0,'new_encoder':0,'vae_decode':1,'finished':time.time()})
phase('worker_complete')
