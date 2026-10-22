"""CPU-only pre-inference provenance checks. Never loads model weights as tensors."""
from pathlib import Path
from types import SimpleNamespace,MethodType
import ast,hashlib,json,sys,time
from PIL import Image,ImageOps
import torch
root=Path(sys.argv[1]);prior=Path(sys.argv[2]);cfg=json.loads((root/'configs/R-gray-C-null-20261022.json').read_text())
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
a=(root/'scripts/vace_experiment.py').read_text().replace('B005 forbids adapters','B003 forbids adapters')
checks['runner_only_label_changed']=a==(prior/'scripts/vace_experiment.py').read_text()
for source_root,label,seed in [(prior,f'{cond}-{seed}',seed) for cond in ('C-real','C-null') for seed in (20261022,20261023)]+[(prior.parent/'B-004-reference-neutral',f'R-gray-{seed}',seed) for seed in (20261022,20261023)]:
 new=json.loads((root/f'configs/R-gray-C-null-{seed}.json').read_text());old=json.loads((source_root/f'outputs/{label}/config.json').read_text());out=source_root/f'outputs/{label}'
 fields=[key for key in new if key not in ('output','reference','condition_video','deadline')]
 runtime=json.loads((out/'resolved_runtime.json').read_text())
 item={'same_resolved_runtime':runtime=={'vram_management_enabled':False,'torch_dtype':'torch.bfloat16','device':'cuda','attention':'upstream SDPA fallback','adapter':None},'seed':seed,'reused_run':source_root.name+'/'+label,'same_settings':all(new[k]==old[k] for k in fields),'output_sha256':sha(out/'result.mp4')}
 for name,key in [('target','source_video'),('condition','condition_video')]:
  video=VideoData(image_folder=old[key],height=288,width=512)
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
for previous in (prior,prior.parent/'B-004-reference-neutral'):
 registered=json.loads((previous/'reports/prereg_code_hashes.json').read_text())
 checks[previous.name+'_registered_scripts_unchanged']=all(sha(previous/name if name.startswith('scripts/') else previous/'scripts'/name)==digest for name,digest in registered.items())
 text=(previous/'scripts/vace_experiment.py').read_text().replace('B004 forbids adapters','B003 forbids adapters')
 checks[previous.name+'_runner_equivalent']=text==a
checks['reuse_eligible']=all(all(v for k,v in row.items() if isinstance(v,bool)) for row in reused)
null_video=VideoData(image_folder=cfg['condition_video'],height=288,width=512)
checks['current_null_rgb_zero']=len(null_video)==17 and all(image.convert('RGB').getextrema()==((0,0),)*3 for image in [null_video[i] for i in range(17)])
report={'experiment':'B-005','method':'Fresh CPU-only file hashes, actual VideoData decode, upstream CPU NoiseInitializer; no VAE/text/DiT forward or inference. Prior text/VACE hashes retained for post-run comparison, not freshly computed.','checks':checks,'model_files':model,'upstream_files':upstream,'reused_runs':reused,'seconds':time.monotonic()-start,'gray_sha256':sha(cfg['reference'])}
(root/'reports/reuse_audit.json').write_text(json.dumps(report,indent=2))
print(json.dumps({'checks':checks,'seconds':report['seconds']}));assert all(checks.values())
