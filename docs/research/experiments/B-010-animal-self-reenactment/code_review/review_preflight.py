"""Actual-source/static CPU comparison; existing B009 explicitly contextual only."""
from pathlib import Path
import subprocess,json,sys,hashlib
import numpy as np
from PIL import Image,ImageDraw
root,context=map(Path,sys.argv[1:]);out=root/'reports/output-review';out.mkdir(exist_ok=False)
for name in ['frames','video-frames']:(out/name).mkdir()
ctx=np.frombuffer(subprocess.check_output(['ffmpeg','-v','error','-i',str(context),'-f','rawvideo','-pix_fmt','rgb24','-']),np.uint8).reshape(17,896,512,3)
f0=Image.open(root/'source/000.png').convert('RGB');sheet=Image.new('RGB',(1152,6*256),'#222');selected=Image.new('RGB',(768,5*480),'#222')
for i in range(17):
 source=Image.open(root/'source'/f'{i:03d}.png').convert('RGB');three=Image.new('RGB',(768,480),'#222');video=Image.new('RGB',(1536,928),'#222')
 for col,(im,label) in enumerate([(source,'SOURCE'),(f0,'STATIC COPY f0'),(Image.fromarray(ctx[i]),'B009 CONTEXT ONLY')]):
  three.paste(im.resize((256,448)),(col*256,24));ImageDraw.Draw(three).text((col*256+3,3),f'f{i} {label}',fill='white')
  video.paste(im,(col*512,32));ImageDraw.Draw(video).text((col*512+5,7),label,fill='white')
 three.save(out/'frames'/f'{i:03d}.png');video.save(out/'video-frames'/f'{i:03d}.png');sheet.paste(three.resize((384,240)),((i%3)*384,(i//3)*256))
 if i in [0,4,8,12,16]:selected.paste(three,(0,(i//4)*480))
sheet.save(out/'all17.png');selected.save(out/'selected.png')
subprocess.run(['ffmpeg','-v','error','-framerate','24','-i',str(out/'video-frames/%03d.png'),'-frames:v','17','-c:v','libx264','-pix_fmt','yuv420p',str(out/'source-static-context.mp4')],check=True)
probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-count_frames','-show_streams','-of','json',str(out/'source-static-context.mp4')]))['streams'][0];assert probe['nb_read_frames']=='17' and probe['avg_frame_rate']=='24/1'
(out/'manifest.json').write_text(json.dumps({'new_model_output':'NOT_RUN','comparison':'actual source / deliberate static f0 copy / reused B009 context only, not a controlled baseline','fps':24,'frames':17,'duration_seconds':17/24,'temporal_quality':'UNVERIFIED','probe':probe,'context_sha256':hashlib.sha256(context.read_bytes()).hexdigest()},indent=2)+'\n')
