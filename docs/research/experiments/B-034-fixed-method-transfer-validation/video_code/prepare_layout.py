"""CPU-only stage layout and immutable encoder/input freeze after anchor acceptance."""
from pathlib import Path
import hashlib,json,shutil,sys
import torch

root=Path(sys.argv[1]).resolve();code=Path(sys.argv[2]).resolve();upstream=Path(sys.argv[3]).resolve();models=Path(sys.argv[4]).resolve()
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
assert not (root/'PREREGISTERED_CODE.json').exists()
for name,target in [('code',code),('upstream',upstream),('models',models)]:
 if not (root/name).exists():(root/name).symlink_to(target)
for name in ('shared','reports','outputs','configs'):(root/name).mkdir(exist_ok=True)
(root/'configs/active_case.json').write_text(json.dumps({'name':'public'}))
cfg=json.loads((root/'configs/public.json').read_text())
assert cfg['task_id'] in ('rigid_R1','nonrigid_R1') and cfg['adapter'] is None
inputs=[cfg[k] for k in ('reference','reference_mask','driver','driver_mask')]
(root/'configs/input_config_hashes.json').write_text(json.dumps({name:sha(root/name) for name in inputs+['configs/public.json']},indent=2))
sys.path.insert(0,str(upstream));sys.path.insert(0,str(code))
from media import inputs as preprocess
observed={key:{'shape':list(value.shape),'dtype':str(value.dtype),'sha256':hashlib.sha256(value.contiguous().numpy().tobytes()).hexdigest()} for key,value in preprocess(root,cfg).items()}
(root/'configs/expected_preprocessed.json').write_text(json.dumps(observed,indent=2))
for case in ('BASE','STEP'):
 artifacts=root/'cases'/case/'artifacts';artifacts.mkdir(parents=True)
 for name in ('conditions.safetensors','conditions.json','conditions_receipt.json','initial_noise.pt','source_latent.safetensors','source_latent.json'):(artifacts/name).symlink_to(root/'shared'/name)
execution={}
sequence=['ENC','BASE_S','BASE_D','CONTROL_D','STEP_S','STEP_D']
for index,stage in enumerate(sequence):
 folder=root/'stages'/stage;(folder/'reports').mkdir(parents=True);(folder/'configs').mkdir()
 for name in ('code','inputs','outputs','upstream','models'):(folder/name).symlink_to(root/name)
 (folder/'experiment').symlink_to(root)
 artifact=root/'shared' if stage=='ENC' else root/'cases'/('STEP' if stage.startswith('STEP') else 'BASE')/'artifacts'
 (folder/'artifacts').symlink_to(artifact)
 for item in (root/'configs').glob('*.json'):shutil.copyfile(item,folder/'configs'/item.name)
 row={'stage':stage,'method':'STEP' if stage.startswith('STEP') else 'BASE','predecessor':sequence[index-1] if index else None,'adapter_enabled':False,'replace_flag':True,'alg':False,'manual_rope_override':False,'b029_gate':False,'reference_id':'R1','expected_steps':40,'expected_forwards':80,'deadline':'2026-10-27T06:45:00Z'}
 (folder/'configs/execution.json').write_text(json.dumps(row,indent=2));execution[stage]=row
 for name in ('PREREGISTERED_CODE.json','PREREGISTERED_INPUTS.json'):(folder/name).symlink_to(root/name)
files={str(item.relative_to(root)):sha(item) for folder in ('code','configs','inputs','stages') for item in (root/folder).rglob('*') if item.is_file() and '__pycache__' not in str(item) and (folder!='stages' or item.parent.name=='configs')}
upstream_hash={name:sha(upstream/name) for name in ('wan/utils/fm_solvers_unipc.py','wan/scail.py','wan/modules/vae.py')}
assert upstream_hash['wan/utils/fm_solvers_unipc.py']=='0dec8c7ed17f6f2049275c6848113314da6ccec1c8db5bdc89df43c05c6038d9'
(root/'PREREGISTERED_CODE.json').write_text(json.dumps({'experiment':'B-034','files':files,'upstream':upstream_hash,'execution':execution,'budget':{'source_encode':1,'samplers':2,'decodes':4}},indent=2))
(root/'ENC_FREEZE.json').write_text(json.dumps({'receipt_sha256':sha(root/'PREREGISTERED_CODE.json')}))
print(json.dumps({'status':'FROZEN','files':len(files),'case':cfg['task_id']}))
