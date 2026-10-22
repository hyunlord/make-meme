"""CPU-only pre-inference provenance checks. Never loads model weights as tensors."""
from pathlib import Path
from types import SimpleNamespace,MethodType
import ast,hashlib,json,sys,time
from PIL import Image,ImageOps
import torch
root=Path(sys.argv[1]);prior=Path(sys.argv[2]);cfg=json.loads((root/'configs/R-gray-20261022.json').read_text())
sys.path.insert(0,cfg['upstream'])
from diffsynth.utils.data import VideoData
from diffsynth.pipelines.wan_video import WanVideoUnit_NoiseInitializer
from diffsynth.diffusion.base_pipeline import BasePipeline
start=time.monotonic()
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  while b:=f.read(8388608):h.update(b)
 return h.hexdigest()
def pixels(p):return Image.open(p).convert('RGB').tobytes()
checks={};reused=[]
oldhash=json.loads((prior/'reports/model_revalidation.json').read_text());model=[];upstream=[]
for row in oldhash['model_files']:
 actual=sha(Path(cfg['weights'])/row['file']);model.append(dict(file=row['file'],expected=row['actual'],actual=actual,match=actual==row['actual']))
for row in oldhash['upstream_files']:
 actual=sha(Path(cfg['upstream'])/row['file']);upstream.append(dict(file=row['file'],expected=row['actual'],actual=actual,match=actual==row['actual']))
checks['model_upstream_match']=all(x['match'] for x in model+upstream)
for name in ('vace_observe.py','guard.py'): checks[f'{name}_identical']=sha(root/'scripts'/name)==sha(prior/'scripts'/name)
a=(root/'scripts/vace_experiment.py').read_text().replace('B004 forbids adapters','B003 forbids adapters')
checks['runner_only_label_changed']=a==(prior/'scripts/vace_experiment.py').read_text()
for seed in (20261022,20261023):
 new=json.loads((root/f'configs/R-gray-{seed}.json').read_text());old=json.loads((prior/f'outputs/C-real-{seed}/config.json').read_text());out=prior/f'outputs/C-real-{seed}'
 fields=[key for key in new if key not in ('output','reference','deadline')]
 item={'seed':seed,'same_settings':all(new[k]==old[k] for k in fields),'output_sha256':sha(out/'result.mp4')}
 for name,key in [('target','source_video'),('condition','condition_video')]:
  video=VideoData(image_folder=new[key],height=288,width=512)
  item[name+'_decoded_matches']=len(video)==17 and all(video[i].convert('RGB').tobytes()==pixels(out/name/f'{i:03d}.png') for i in range(17))
 item['mask_matches_white']=all(pixels(out/'mask'/f'{i:03d}.png')==Image.new('RGB',(512,288),'white').tobytes() for i in range(17))
 original=Image.open(old['reference']);ref=ImageOps.pad(original.convert('RGB'),(512,288),color=(128,128,128))
 item['Rbg_preprocessing_matches']=ref.tobytes()==pixels(out/'reference.png')
 gray=Image.open(new['reference']);item['reference_format_same']=gray.mode==original.mode=='RGB' and gray.size==original.size==(1536,2048) and not gray.getexif() and not original.getexif()
 item['gray_uniform128']=gray.getextrema()==((128,128),)*3
 pipe=SimpleNamespace(device='cpu',torch_dtype=torch.bfloat16,vae=SimpleNamespace(model=SimpleNamespace(z_dim=16),upsampling_factor=8));pipe.generate_noise=MethodType(BasePipeline.generate_noise,pipe)
 noise=WanVideoUnit_NoiseInitializer().process(pipe,288,512,17,seed,'cpu',[None],None)['noise'];digest=hashlib.sha256(noise.contiguous().view(torch.uint8).numpy().tobytes()).hexdigest()
 actual=[json.loads(line) for line in (out/'actual_input_hashes.jsonl').read_text().splitlines()][-1]
 item['cpu_noise_sha256']=digest;item['same_actual_noise']=digest==actual['tensors']['shared.noise']['sha256'];item['prior_actual_tensor_hashes']=actual['tensors'];item['prior_actual_slices']=actual['slices']
 reused.append(item)
checks['reuse_eligible']=all(all(v for k,v in row.items() if isinstance(v,bool)) for row in reused)
report={'experiment':'B-004','method':'Fresh CPU-only file hashes, actual VideoData decode, upstream CPU NoiseInitializer; no VAE/text/DiT forward or inference. Prior text/VACE hashes retained for post-run comparison, not freshly computed.','checks':checks,'model_files':model,'upstream_files':upstream,'reused_runs':reused,'seconds':time.monotonic()-start,'gray_sha256':sha(cfg['reference'])}
(root/'reports/reuse_audit.json').write_text(json.dumps(report,indent=2))
print(json.dumps({'checks':checks,'seconds':report['seconds']}));assert all(checks.values())
