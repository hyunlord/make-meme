"""CPU-only layout for the seven preregistered fresh processes; no model run."""
from pathlib import Path
import json
import shutil
import sys

root=Path(sys.argv[1]).resolve();baseline=Path(sys.argv[2]).resolve()
stages=('P','PREFIX','BASE_S','BASE_D','TRAIN','TRAIN_S','TRAIN_D')
for stage in stages:
    worker=root/'stages'/stage
    for name in ('reports','configs'): (worker/name).mkdir(parents=True,exist_ok=True)
    for name in ('code','inputs'):
        destination=worker/name
        if not destination.exists():destination.symlink_to(root/name,target_is_directory=True)
    for name in ('models','upstream'):
        destination=worker/name
        if not destination.exists():destination.symlink_to(baseline/name,target_is_directory=True)
    for path in (root/'configs').glob('*.json'):shutil.copy2(path,worker/'configs'/path.name)
    execution={'stage':stage,'predecessor':None if stage=='P' else stages[stages.index(stage)-1],'adapter_enabled':stage in ('TRAIN_S','TRAIN_D')}
    (worker/'configs/execution.json').write_text(json.dumps(execution,indent=2))
    for name in ('PREREGISTERED_CODE.json','PREREGISTERED_INPUTS.json'):
        destination=worker/name
        if not destination.is_symlink():destination.symlink_to(root/name)
    artifacts=root/'artifacts' if stage in ('P','PREFIX','TRAIN') else root/'variants'/('baseline' if stage.startswith('BASE') else 'trained')/'artifacts'
    artifacts.mkdir(parents=True,exist_ok=True)
    if not (worker/'artifacts').exists():(worker/'artifacts').symlink_to(artifacts,target_is_directory=True)
    if artifacts!=root/'artifacts':
        for name in ('conditions.safetensors','conditions.json','conditions_receipt.json','initial_noise.pt','target.safetensors','target.json','training_receipt.json','adapter-final.safetensors','adapter-final.json'):
            destination=artifacts/name
            if not destination.is_symlink():destination.symlink_to(root/'artifacts'/name)
