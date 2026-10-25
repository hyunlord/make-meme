"""CPU-only case paths and immutable stage configuration for the matched pair."""
from pathlib import Path
import json
import hashlib
import sys
import shutil
root=Path(sys.argv[1]).resolve();parent=Path(sys.argv[2]).resolve()
(root/'producer').symlink_to(parent,target_is_directory=True)
(root/'PREREGISTERED_INPUTS.json').symlink_to(parent/'PREREGISTERED_INPUTS.json')
for case in ('LAB','IG'):
    (root/'inputs'/case).symlink_to(root/'inputs'/('REF_'+case),target_is_directory=True)
(root/'inputs/clip').symlink_to(parent/'inputs/clip',target_is_directory=True)
assert (root/'inputs/LAB/reference.png').read_bytes()==(parent/'inputs/clip/reference-rgb-neutral.png').read_bytes()
assert (root/'inputs/LAB/reference-mask.png').read_bytes()==(parent/'inputs/clip/reference-mask-black.png').read_bytes()
prompt="A dog matching the reference image stands naturally on all four legs on a light tiled floor in a sunlit room. It gently turns its head toward the left side of the image while its body stays mostly in place. The stable camera shows the dog's full body and the surrounding room."
base=json.loads((parent/'configs/real.json').read_text());base['prompt']=prompt
for case in ('LAB','IG'):
    destination=root/'cases'/case/'artifacts';destination.mkdir(parents=True,exist_ok=True)
    (destination/'initial_noise.pt').symlink_to(parent/'artifacts/initial_noise.pt')
    cfg={**base,'reference':f'inputs/{case}/reference.png','reference_mask':f'inputs/{case}/reference-mask.png'}
    (root/'configs'/f'{case}.json').write_text(json.dumps(cfg,indent=2))
stages=('ENC','LAB_PROBE','LAB_S','LAB_D','IG_PROBE','IG_S','IG_D')
for index,stage in enumerate(stages):
    worker=root/'stages'/stage;case='IG' if stage.startswith('IG_') else 'LAB'
    for name in ('reports','configs'):(worker/name).mkdir(parents=True,exist_ok=True)
    for name in ('code','inputs','producer','PREREGISTERED_INPUTS.json','PREREGISTERED_CODE.json'):(worker/name).symlink_to(root/name)
    (worker/'experiment').symlink_to(root,target_is_directory=True)
    (worker/'artifacts').symlink_to(root/'cases'/case/'artifacts',target_is_directory=True)
    for name in ('models','upstream'):(worker/name).symlink_to(parent/'stages/S'/name,target_is_directory=True)
    for name in ('active_case.json','allowed_gpu_processes.json'):shutil.copy2(root/'configs'/name,worker/'configs'/name)
    shutil.copy2(root/'configs'/f'{case}.json',worker/'configs/real.json')
    cfg=json.loads((worker/'configs/real.json').read_text())
    paths=[cfg[k] for k in ('reference','reference_mask','driver','driver_mask')]
    paths+=['inputs/IG/reference.png','inputs/IG/reference-mask.png','inputs/LAB/reference.png','inputs/LAB/reference-mask.png']
    hashes={n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in paths};hashes['configs/real.json']=hashlib.sha256((worker/'configs/real.json').read_bytes()).hexdigest()
    (worker/'configs/input_config_hashes.json').write_text(json.dumps(hashes,indent=2))
    execution={'stage':stage,'reference_id':case,'predecessor':None if index==0 else stages[index-1],'adapter_enabled':False,'replace_flag':True,'alg':False,'manual_rope_override':False}
    (worker/'configs/execution.json').write_text(json.dumps(execution,indent=2))
