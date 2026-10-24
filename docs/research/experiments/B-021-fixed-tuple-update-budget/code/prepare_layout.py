"""CPU layout only, preserving producer payload paths and all previous attempts."""
from pathlib import Path
import json
import shutil
import sys
root=Path(sys.argv[1]).resolve();producer=Path(sys.argv[2]).resolve()
for name in ('inputs','producer'):
    path=root/name
    if not path.exists():path.symlink_to(producer/'inputs' if name=='inputs' else producer,target_is_directory=True)
for filename in ('PREREGISTERED_INPUTS.json',):
    if not (root/filename).exists():(root/filename).symlink_to(producer/filename)
shared=('conditions.safetensors','conditions.json','conditions_receipt.json','initial_noise.pt','target.safetensors','target.json','prefix_receipt.json')
for name in shared:
    if not (root/'artifacts'/name).exists():(root/'artifacts'/name).symlink_to(producer/'artifacts'/name)
stages=('TRAIN','PROBE','TRAIN_S','TRAIN_D')
for index,stage in enumerate(stages):
    worker=root/'stages'/stage
    for name in ('reports','configs'):(worker/name).mkdir(parents=True,exist_ok=True)
    for name in ('code','inputs','producer','PREREGISTERED_INPUTS.json','PREREGISTERED_CODE.json'):
        if not (worker/name).is_symlink():(worker/name).symlink_to(root/name)
    for name in ('models','upstream'):
        if not (worker/name).exists():(worker/name).symlink_to(producer/'stages/TRAIN'/name,target_is_directory=True)
    for path in (root/'configs').glob('*.json'):shutil.copy2(path,worker/'configs'/path.name)
    execution={'stage':stage,'predecessor':None if index==0 else stages[index-1],'adapter_enabled':stage in ('TRAIN_S','TRAIN_D')}
    (worker/'configs/execution.json').write_text(json.dumps(execution,indent=2))
    if not (worker/'artifacts').exists():(worker/'artifacts').symlink_to(root/'artifacts',target_is_directory=True)
