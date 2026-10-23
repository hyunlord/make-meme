"""CPU-only exact source first-frame reference and explicitly static control."""
from pathlib import Path
import subprocess,json,hashlib,sys
import numpy as np
from PIL import Image,ImageDraw
root,old=map(Path,sys.argv[1:]);inp=root/'inputs/self';inp.mkdir(parents=True,exist_ok=True);out=root/'reports/preflight';out.mkdir(parents=True,exist_ok=False)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def decode(p):
 raw=subprocess.check_output(['ffmpeg','-v','error','-i',str(p),'-f','rawvideo','-pix_fmt','rgb24','-'])
 return np.frombuffer(raw,np.uint8).copy().reshape(17,896,512,3)
for name in ['driver-24fps.mp4','mask-24fps.mp4','driver','mask']:
 p=inp/name
 if not p.exists():p.symlink_to(old/name)
frames=decode(inp/'driver-24fps.mp4');masks=decode(inp/'mask-24fps.mp4')
# Static-copy intentionally repeats f0. No generated frames are copied.
static=root/'static-copy';static.mkdir(exist_ok=False)
for i in range(17):Image.fromarray(frames[0]).save(static/f'{i:03d}.png')
subprocess.run(['ffmpeg','-v','error','-framerate','24','-i',str(static/'%03d.png'),'-frames:v','17','-c:v','libx264','-pix_fmt','yuv420p',str(static/'STATIC_COPY.mp4')],check=True)
Image.fromarray(frames[0]).save(inp/'reference.png')
lossless=np.array(Image.open(old/'mask/000.png').convert('RGB'))
red=lambda a:(a[...,0]>225)&(a[...,1]<=225)&(a[...,2]<=225)
assert np.array_equal(red(lossless),red(masks[0]))
new=np.full_like(lossless,255);new[red(lossless)]=[255,0,0]
Image.fromarray(new).save(inp/'reference-mask-white.png');Image.fromarray(new).save(inp/'reference-mask.png')
source=root/'source';source.mkdir(exist_ok=False)
for i in range(17):Image.fromarray(frames[i]).save(source/f'{i:03d}.png')
sheet=Image.new('RGB',(1024,5*472),'#202020')
for row,i in enumerate([0,4,8,12,16]):
 for col,(arr,label) in enumerate([(frames[i],'actual source'),(frames[0],'STATIC COPY f0')]):
  sheet.paste(Image.fromarray(arr).resize((256,448)),(col*512, row*472+24));ImageDraw.Draw(sheet).text((col*512+3,row*472+3),f'f{i} {label}',fill='white')
sheet.save(out/'source-static-selected.png')
record={'status':'CPU_INPUTS_READY','reference_from':'actual unchanged driver MP4 decoded RGB first frame; PNG no color changes','reference_matches_prior_lossless_png':bool(np.array_equal(frames[0],np.array(Image.open(old/'driver/000.png').convert('RGB')))),'red_support_matches_decoded_mask':True,'mask_rule':'R>225,G<=225,B<=225 becomes exact RED; all remaining pixels WHITE; no new silhouette','red_pixels':int(red(lossless).sum()),'white_pixels':int((~red(lossless)).sum()),'files':{n:sha(inp/n) for n in ['reference.png','reference-mask-white.png','driver-24fps.mp4','mask-24fps.mp4']},'static_count':17,'fps':24,'duration_seconds':17/24,'sample_endpoint_seconds':16/24,'generated_output':'NOT_RUN'}
(out/'inputs.json').write_text(json.dumps(record,indent=2)+'\n')
