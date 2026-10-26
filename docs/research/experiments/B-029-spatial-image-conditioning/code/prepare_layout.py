# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
# Run in the existing pinned SCAIL environment; installs and encoders forbidden.
"""Create separate METHOD/CONTROL consumers of immutable B027 conditions."""
from pathlib import Path
import hashlib
import json
import shutil
import sys

root=Path(sys.argv[1]).resolve()
parent=Path(sys.argv[2]).resolve()
code=Path(sys.argv[3]).resolve()
variant=sys.argv[4]
assert variant in ('METHOD','CONTROL')
assert not root.exists(), 'Do not reset an existing experiment consumer'
root.mkdir(parents=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for name in ('inputs','task_manifest.json'):
    (root/name).symlink_to(parent/name)
(root/'code').symlink_to(code,target_is_directory=True)
(root/'support').symlink_to(root.parent/'shared_support',target_is_directory=True)
(root/'configs').mkdir();(root/'reports').mkdir()
for name in ('active_case.json','allowed_gpu_processes.json','pinned_upstream.json'):
    shutil.copy2(parent/'configs'/name,root/'configs'/name)
model_manifest=json.loads((parent/'PREREGISTERED_INPUTS.json').read_text())
model_manifest.update(experiment='B-029',consumer_variant=variant,producer_experiment='B-027')
(root/'PREREGISTERED_INPUTS.json').write_text(json.dumps(model_manifest,indent=2)+'\n')
cases=('R1','R2') if variant=='METHOD' else ('R1',)
stages=[f'{case}_{phase}' for case in cases for phase in ('PROBE','S','D')]
(root/'configs/spatial_gate.json').write_text(json.dumps({'variant':variant,'lambda':0.5,'enabled':True,'expected_model_calls':80,'expected_steps':40,'expected_blocks':40},indent=2)+'\n')
for case in cases:
    artifacts=root/'cases'/case/'artifacts';artifacts.mkdir(parents=True)
    for name in ('conditions.safetensors','conditions.json','conditions_receipt.json','initial_noise.pt'):
        (artifacts/name).symlink_to(parent/'cases'/case/'artifacts'/name)
    shutil.copy2(parent/'configs'/f'{case}.json',root/'configs'/f'{case}.json')
for index,stage in enumerate(stages):
    case=stage.split('_')[0];producer=parent/'stages'/f'{case}_S'
    worker=root/'stages'/stage
    for name in ('reports','configs'):(worker/name).mkdir(parents=True)
    for name in ('code','inputs','support','PREREGISTERED_INPUTS.json','PREREGISTERED_CODE.json'):(worker/name).symlink_to(root/name)
    (worker/'experiment').symlink_to(root,target_is_directory=True)
    (worker/'artifacts').symlink_to(root/'cases'/case/'artifacts',target_is_directory=True)
    for name in ('models','upstream'):(worker/name).symlink_to((producer/name).resolve(),target_is_directory=True)
    for name in ('active_case.json','allowed_gpu_processes.json','spatial_gate.json'):
        shutil.copy2(root/'configs'/name,worker/'configs'/name)
    shutil.copy2(producer/'configs/public.json',worker/'configs/public.json')
    shutil.copy2(producer/'configs/input_config_hashes.json',worker/'configs/input_config_hashes.json')
    binding={'producer_experiment':'B-027','consumer_experiment':'B-029','producer_worker':str(producer),'producer_hashes':{name:sha(producer/name) for name in ('PREREGISTERED_CODE.json','artifacts/conditions_receipt.json','artifacts/conditions.json','configs/public.json')}}
    (worker/'configs/cache_binding.json').write_text(json.dumps(binding,indent=2)+'\n')
    execution={'stage':stage,'reference_id':case,'task_id':json.loads((parent/'task_manifest.json').read_text())['task_id'],'predecessor':None if index==0 else stages[index-1],'adapter_enabled':False,'replace_flag':True,'alg':False,'manual_rope_override':False,'variant':variant,'parent_experiment':'B-027'}
    (worker/'configs/execution.json').write_text(json.dumps(execution,indent=2)+'\n')
sys.path.insert(0,str(code))
from contracts import verify_cache_receipt
from media import verify_inputs
for stage in stages:
    worker=root/'stages'/stage
    verify_inputs(worker);verify_cache_receipt(worker)
print(json.dumps({'variant':variant,'cases':cases,'cache_contract':'16 leaves, all bytes preserved','ENC':0,'GPU':0}))
