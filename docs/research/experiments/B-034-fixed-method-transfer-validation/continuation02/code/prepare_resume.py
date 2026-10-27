"""Prepare fresh CPU-only resume roots without changing any prior execution artifact."""
from pathlib import Path
import datetime
import hashlib
import json
import shutil
import sys

parent=Path(sys.argv[1]).resolve();code=Path(sys.argv[2]).resolve()
old=parent/'continuation/CONTINUATION_01';root=parent/'continuation/CONTINUATION_02/RESUME_01'
assert not (root/'stages').exists(),'Existing stages: inspect, never duplicate'
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
for stage in ('STEP_S','STEP_D'):
    source=old/'stages'/stage;folder=root/'stages'/stage
    for name in ('reports','configs','artifacts','outputs'):(folder/name).mkdir(parents=True)
    for name in ('upstream','models','experiment','inputs'):(folder/name).symlink_to((source/name).resolve())
    (folder/'code').symlink_to(code)
    for item in (source/'configs').glob('*.json'):shutil.copyfile(item,folder/'configs'/item.name)
    execution=json.loads((folder/'configs/execution.json').read_text());execution.update(deadline='2026-10-27T13:18:47Z',artifact_consumer='B034_CONTINUATION_02_RESUME_01')
    (folder/'configs/execution.json').write_text(json.dumps(execution,indent=2))
    for item in (source/'artifacts').iterdir():
        if item.is_symlink():(folder/'artifacts'/item.name).symlink_to(item.resolve())
    cfg=json.loads((source/'config.json').read_text());cfg.update(unit='make-meme-b034-cont02-r1-'+stage.lower().replace('_','-'),deadline_epoch=datetime.datetime.fromisoformat('2026-10-27T13:18:47+00:00').timestamp(),step_latent=str(root/'stages/STEP_S/artifacts/final_latent.safetensors'))
    (folder/'config.json').write_text(json.dumps(cfg,indent=2))
    (folder/'PREREGISTERED_INPUTS.json').symlink_to((source/'PREREGISTERED_INPUTS.json').resolve())
    original=json.loads((source/'freeze.json').read_text());paths=[Path(name) for name in original['files'] if not Path(name).is_relative_to(old/'code') and not Path(name).is_relative_to(source/'configs') and Path(name)!=source/'config.json']
    paths+=list(code.glob('*.py'))+list((folder/'configs').glob('*.json'))+[folder/'config.json']
    freeze={**original,'experiment':'B034_CONTINUATION_02_RESUME_01','files':{str(path):sha(path) for path in paths},'budget':{'samplers':1,'step_decode':1,'control_decode':0,'source_decode':0,'base_decode':0}}
    for name in ('freeze.json','PREREGISTERED_CODE.json'):(folder/name).write_text(json.dumps(freeze,indent=2))
print(json.dumps({'status':'CPU_LAYOUT_PREPARED_NOT_GPU_AUTHORIZATION','stages':{stage:sha(root/'stages'/stage/'freeze.json') for stage in ('STEP_S','STEP_D')}}))
