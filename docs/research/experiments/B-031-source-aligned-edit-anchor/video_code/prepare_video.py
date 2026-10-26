# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
# Run: pinned-python prepare_video.py CONSUMER_TASK B027_TASK ANCHOR_DIR CODE_ROOT
"""Build one approved R1 video task; source and producer caches stay read-only."""
from pathlib import Path
import hashlib
import json
import shutil
import sys
import numpy as np
from PIL import Image

root=Path(sys.argv[1]).resolve();parent=Path(sys.argv[2]).resolve()
anchor=Path(sys.argv[3]).resolve();code=Path(sys.argv[4]).resolve()
assert not root.exists(), 'Never reset a worker or repeat an attempt'
approval=json.loads((anchor/'anchor_suitability.json').read_text())
assert approval['suitable'] is True and approval['reference_id']=='R1'
assert approval['qwen_process_exited'] is True
reference=anchor/'reference.png';mask=anchor/'reference-mask.png'
rgb=np.array(Image.open(reference).convert('RGB'));semantic=np.array(Image.open(mask).convert('RGB'))
assert rgb.shape==semantic.shape==(512,896,3)
red=np.all(semantic==[255,0,0],axis=-1);black=np.all(semantic==0,axis=-1)
assert np.all(red|black) and bool(red.any()) and np.all(rgb[black]==128)
for name in ('reference.png','reference-mask.png'):
    assert hashlib.sha256((anchor/name).read_bytes()).hexdigest()==approval['input_hashes'][name]
row=parent/'stages/R1_S'
root.mkdir(parents=True)
for name in ('configs','reports','inputs/anchor','cases/R1/artifacts'):(root/name).mkdir(parents=True)
(root/'code').symlink_to(code,target_is_directory=True)
(root/'task_manifest.json').symlink_to(parent/'task_manifest.json')
for name in ('driver.mp4','driver-mask.mp4'):(root/'inputs'/name).symlink_to(parent/'inputs'/name)
for name in ('reference.png','reference-mask.png'):shutil.copy2(anchor/name,root/'inputs/anchor'/name)
shutil.copy2(row/'artifacts/initial_noise.pt',root/'cases/R1/artifacts/initial_noise.pt')
for name in ('active_case.json','allowed_gpu_processes.json','pinned_upstream.json'):
    shutil.copy2(parent/'configs'/name,root/'configs'/name)
manifest=json.loads((parent/'PREREGISTERED_INPUTS.json').read_text())
assert approval['task_id']==manifest['task_id']
manifest.update(experiment='B-031',producer_experiment='B-027',anchor_suitability=approval)
(root/'PREREGISTERED_INPUTS.json').write_text(json.dumps(manifest,indent=2)+'\n')
cfg=json.loads((row/'configs/public.json').read_text())
cfg.update(reference='inputs/anchor/reference.png',reference_mask='inputs/anchor/reference-mask.png')
(root/'configs/R1.json').write_text(json.dumps(cfg,indent=2)+'\n')
stages=('ENC','R1_PROBE','R1_S','R1_D')
for index,stage in enumerate(stages):
    worker=root/'stages'/stage
    for name in ('reports','configs'):(worker/name).mkdir(parents=True)
    for name in ('code','inputs','PREREGISTERED_INPUTS.json','PREREGISTERED_CODE.json'):(worker/name).symlink_to(root/name)
    (worker/'experiment').symlink_to(root,target_is_directory=True)
    (worker/'artifacts').symlink_to(root/'cases/R1/artifacts',target_is_directory=True)
    for name in ('models','upstream'):(worker/name).symlink_to((row/name).resolve(),target_is_directory=True)
    for name in ('active_case.json','allowed_gpu_processes.json'):shutil.copy2(root/'configs'/name,worker/'configs'/name)
    shutil.copy2(anchor/'anchor_suitability.json',worker/'configs/anchor_suitability.json')
    (worker/'configs/public.json').write_text(json.dumps(cfg,indent=2)+'\n')
    hashes={name:hashlib.sha256((worker/name).read_bytes()).hexdigest() for name in (*[cfg[key] for key in ('reference','reference_mask','driver','driver_mask')],'configs/public.json')}
    (worker/'configs/input_config_hashes.json').write_text(json.dumps(hashes,indent=2)+'\n')
    files=('PREREGISTERED_CODE.json','artifacts/conditions_receipt.json','artifacts/conditions.safetensors','artifacts/conditions.json','artifacts/initial_noise.pt','configs/public.json')
    binding={'producer_experiment':'B-027','consumer_experiment':'B-031','producer_worker':str(row),'producer_hashes':{name:hashlib.sha256((row/name).read_bytes()).hexdigest() for name in files}}
    (worker/'configs/cache_binding.json').write_text(json.dumps(binding,indent=2)+'\n')
    execution={'stage':stage,'reference_id':'R1','task_id':manifest['task_id'],'predecessor':None if index==0 else stages[index-1],'adapter_enabled':False,'replace_flag':True,'alg':False,'manual_rope_override':False,'b029_gate':False,'parent_experiment':'B-027'}
    (worker/'configs/execution.json').write_text(json.dumps(execution,indent=2)+'\n')
from contracts import verify_parent_receipt
from media import verify_inputs
for stage in stages:
    worker=root/'stages'/stage
    verify_inputs(worker);verify_parent_receipt(worker)
print(json.dumps({'status':'VIDEO_INPUT_READY','task':manifest['task_id'],'GPU':0,'reference':'R1 only'}))
