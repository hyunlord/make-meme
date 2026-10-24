"""Private CPU layout; preserve all B020 assets and independent attempts."""
from pathlib import Path
import json
import shutil
import sys
root=Path(sys.argv[1]).resolve();producer=Path(sys.argv[2]).resolve()
for name in ('producer',):
    if not (root/name).exists():(root/name).symlink_to(producer,target_is_directory=True)
(root/'inputs/clip').mkdir(parents=True,exist_ok=True)
for path in (producer/'inputs/clip').iterdir():
    target=root/'inputs/clip'/path.name
    if not target.exists():target.symlink_to(path,target_is_directory=path.is_dir())
for name in ('PREREGISTERED_INPUTS.json',):
    if not (root/name).exists():(root/name).symlink_to(producer/name)
if not (root/'artifacts/initial_noise.pt').exists():(root/'artifacts/initial_noise.pt').symlink_to(producer/'artifacts/initial_noise.pt')
for index,stage in enumerate(('PROBE','S','D')):
    worker=root/'stages'/stage
    for name in ('reports','configs'):(worker/name).mkdir(parents=True,exist_ok=True)
    for name in ('code','inputs','producer','artifacts','PREREGISTERED_INPUTS.json','PREREGISTERED_CODE.json'):
        if not (worker/name).is_symlink():(worker/name).symlink_to(root/name)
    for name in ('models','upstream'):
        if not (worker/name).exists():(worker/name).symlink_to(producer/'stages/BASE_S'/name,target_is_directory=True)
    for path in (root/'configs').glob('*.json'):shutil.copy2(path,worker/'configs'/path.name)
    execution={'stage':stage,'predecessor':None if index==0 else ('PROBE','S','D')[index-1],'adapter_enabled':False,'replace_flag':True,'alg':False,'manual_rope_override':False}
    (worker/'configs/execution.json').write_text(json.dumps(execution,indent=2))
    if not (worker/'experiment').exists():(worker/'experiment').symlink_to(root,target_is_directory=True)
