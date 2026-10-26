"""Apply the same frozen B032 float E to new decoded raw, CPU only."""
from pathlib import Path
import hashlib,json,subprocess,sys
import numpy as np
from PIL import Image
import torch
from compositor import blend,to_uint8
root=Path(sys.argv[1]);edit=np.load(root/'inputs/edit_px.npy')
source=np.stack([np.asarray(Image.open(root/'inputs/source'/f'{i:03d}.png').convert('RGB')).astype(np.float32)/127.5-1 for i in range(17)])
for label in ('FINAL_LATENT_ONLY','STEP_CONSTRAINED'):
 path=root/'outputs'/label/'raw_output.pt'
 if not path.exists():continue
 raw=torch.load(path,map_location='cpu',weights_only=True).float().permute(1,2,3,0).numpy()
 assert raw.shape==source.shape and np.isfinite(raw).all()
 destination=root/'outputs'/(label+'_RGB_POST');frames=destination/'frames';frames.mkdir(parents=True,exist_ok=True)
 for i in range(17):
  result=blend(source[i],raw[i],edit[i])
  assert np.array_equal(result[edit[i]==0],source[i][edit[i]==0])
  assert np.array_equal(result[edit[i]==1],raw[i][edit[i]==1])
  Image.fromarray(to_uint8(result)).save(frames/f'{i:03d}.png')
 subprocess.run(['ffmpeg','-v','error','-framerate','24','-i',str(frames/'%03d.png'),'-c:v','libx264','-crf','18','-pix_fmt','yuv420p',str(destination/'output.mp4')],check=True)
 subprocess.run(['ffmpeg','-v','error','-i',str(destination/'output.mp4'),'-f','null','-'],check=True)
 (destination/'verification.json').write_text(json.dumps({'E_sha256':hashlib.sha256((root/'inputs/edit_px.npy').read_bytes()).hexdigest(),'source_exact_E0':True,'generated_exact_E1':True,'frames':17,'preview_fps':24,'source_fps':None,'timebase_assumed':True,'new_derivative_encoded':True,'temporal':'UNVERIFIED'},indent=2))
