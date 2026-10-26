"""CPU-only preparation: exact B032 support, immutable parent and freeze manifest."""
from pathlib import Path
import hashlib,json,shutil,sys
import numpy as np
from PIL import Image
import torch
from safetensors.torch import save_file
sys.path.insert(0,str(Path(sys.argv[1])/'upstream'))
from clean_constraint import latent_mask
from compositor import mask_assisted,radius_for_sources

root=Path(sys.argv[1]);parent=Path(sys.argv[2]);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert not (root/'PREREGISTERED_CODE.json').exists()
for directory in ('artifacts','configs','reports','outputs','inputs'): (root/directory).mkdir(exist_ok=True)
for name in ('conditions.safetensors','conditions.json','conditions_receipt.json','initial_noise.pt'):
 shutil.copyfile(parent/'artifacts'/name,root/'artifacts'/name)
for name in ('public.json','active_case.json','allowed_gpu_processes.json'):
 shutil.copyfile(parent/'configs'/name,root/'configs'/name)
(root/'configs/b033_binding.json').write_text(json.dumps({'parent_worker':str(parent),'producer':'B-031','consumer':'B-033'},indent=2))
source_masks=np.stack([np.all(np.asarray(Image.open(root/'inputs/source-mask'/f'{i:03d}.png').convert('RGB'))==[255,0,0],axis=-1) for i in range(17)])
target_masks=np.stack([np.asarray(Image.open(root/'inputs/target-mask'/f'{i:03d}.png').convert('L'))>0 for i in range(17)])
radius=radius_for_sources(source_masks);assert radius==11
edit=np.stack([mask_assisted(s,t,radius) for s,t in zip(source_masks,target_masks)])
np.save(root/'inputs/edit_px.npy',edit)
mask=latent_mask(torch.from_numpy(edit));save_file({'M':mask},str(root/'inputs/mask_latent.safetensors'))
input_hashes={}
prior=json.loads((root/'inputs/b032-input-freeze.json').read_text())
for role,sub in (('source','source'),('source_support','source-mask'),('target_support','target-mask')):
 expected=[item['sha256'] for item in prior['inputs'] if item['role']==role]
 actual=[sha(root/'inputs'/sub/f'{i:03d}.png') for i in range(17)]
 assert actual==expected,(role,len(expected))
for sub in ('source','source-mask','target-mask'):
 for path in sorted((root/'inputs'/sub).glob('*.png')):input_hashes[str(path.relative_to(root))]=sha(path)
for name in ('edit_px.npy','mask_latent.safetensors'):input_hashes['inputs/'+name]=sha(root/'inputs'/name)
(root/'reports/input-freeze.json').write_text(json.dumps({'hashes':input_hashes,'radius':radius,'feather':4,'H_empty':True,'M_shape':list(mask.shape),'M_free_fraction':float(mask.mean()),'M_soft_fraction':float(((mask>0)&(mask<1)).float().mean()),'temporal_groups':[[0],[1,2,3,4],[5,6,7,8],[9,10,11,12],[13,14,15,16]],'pixel_edit_minmax':[float(edit.min()),float(edit.max())]},indent=2))
execution={}
for stage,previous in (('VAE',None),('S','VAE'),('D','S')):
 stage_root=root/'stages'/stage;(stage_root/'reports').mkdir(parents=True);(stage_root/'configs').mkdir()
 for name in ('code','artifacts','inputs','outputs','upstream','models'):(stage_root/name).symlink_to(root/name)
 (stage_root/'experiment').symlink_to(root)
 for path in (root/'configs').glob('*.json'):shutil.copyfile(path,stage_root/'configs'/path.name)
 row={'stage':stage,'predecessor':previous,'adapter_enabled':False,'replace_flag':True,'alg':False,'manual_rope_override':False,'b029_gate':False,'reference_id':'R1','expected_steps':40,'expected_forwards':80,'deadline':'2026-10-27T01:08:00Z'}
 (stage_root/'configs/execution.json').write_text(json.dumps(row,indent=2));execution[stage]=row
 (stage_root/'PREREGISTERED_CODE.json').symlink_to(root/'PREREGISTERED_CODE.json')
files={str(p.relative_to(root)):sha(p) for folder in ('code','configs') for p in (root/folder).rglob('*') if p.is_file() and '__pycache__' not in str(p)}
files.update(input_hashes)
for p in (root/'stages').glob('*/configs/*.json'):files[str(p.relative_to(root))]=sha(p)
upstream={name:sha(root/'upstream'/name) for name in ('wan/utils/fm_solvers_unipc.py','wan/scail.py','wan/modules/vae.py')}
assert upstream['wan/utils/fm_solvers_unipc.py']=='0dec8c7ed17f6f2049275c6848113314da6ccec1c8db5bdc89df43c05c6038d9'
(root/'PREREGISTERED_CODE.json').write_text(json.dumps({'experiment':'B-033','files':files,'upstream':upstream,'execution':execution,'budget':{'source_encode':1,'source_decode':1,'final_control_decode':1,'sampler':1,'step_decode':1}},indent=2))
print(json.dumps({'status':'FROZEN','files':len(files),'M_shape':list(mask.shape),'radius':radius}))
