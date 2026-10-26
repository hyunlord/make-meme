# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
# Run: pinned-python code/prepare_layout.py CONSUMER_TASK B027_TASK CODE_ROOT
"""Prepare two separate CLIP crossover cases without an encoder or GPU call."""
from pathlib import Path
import json
import shutil
import sys
from crossover import derive, sha

root=Path(sys.argv[1]).resolve()
parent=Path(sys.argv[2]).resolve()
code=Path(sys.argv[3]).resolve()
assert not root.exists(), 'Never reset an existing consumer or attempt'
root.mkdir(parents=True)
for name in ('inputs','task_manifest.json'):(root/name).symlink_to(parent/name)
(root/'code').symlink_to(code,target_is_directory=True)
(root/'configs').mkdir();(root/'reports').mkdir()
for name in ('active_case.json','allowed_gpu_processes.json','pinned_upstream.json'):
    shutil.copy2(parent/'configs'/name,root/'configs'/name)
manifest=json.loads((parent/'PREREGISTERED_INPUTS.json').read_text())
manifest.update(experiment='B-030',producer_experiment='B-027')
(root/'PREREGISTERED_INPUTS.json').write_text(json.dumps(manifest,indent=2)+'\n')
stages=[f'{case}_{phase}' for case in ('R1','R2') for phase in ('PROBE','S','D')]
for case,other,cell in (('R1','R2','Y12'),('R2','R1','Y21')):
    artifacts=root/'cases'/case/'artifacts';artifacts.mkdir(parents=True)
    derive(parent/'cases'/case/'artifacts',parent/'cases'/other/'artifacts',artifacts)
    shutil.copy2(parent/'configs'/f'{case}.json',root/'configs'/f'{case}.json')
    for phase in ('PROBE','S','D'):
        stage=f'{case}_{phase}';index=stages.index(stage)
        row=parent/'stages'/f'{case}_S';donor=parent/'stages'/f'{other}_S'
        worker=root/'stages'/stage
        for name in ('reports','configs'):(worker/name).mkdir(parents=True)
        for name in ('code','inputs','PREREGISTERED_INPUTS.json','PREREGISTERED_CODE.json'):(worker/name).symlink_to(root/name)
        (worker/'experiment').symlink_to(root,target_is_directory=True)
        (worker/'artifacts').symlink_to(artifacts,target_is_directory=True)
        for name in ('models','upstream'):(worker/name).symlink_to((row/name).resolve(),target_is_directory=True)
        for name in ('active_case.json','allowed_gpu_processes.json'):
            shutil.copy2(root/'configs'/name,worker/'configs'/name)
        for name in ('public.json','input_config_hashes.json'):
            shutil.copy2(row/'configs'/name,worker/'configs'/name)
        binding={'producer_experiment':'B-027','consumer_experiment':'B-030','cell':cell,'row_worker':str(row),'clip_worker':str(donor),'row_code_sha256':sha(row/'PREREGISTERED_CODE.json'),'clip_code_sha256':sha(donor/'PREREGISTERED_CODE.json')}
        (worker/'configs/cache_binding.json').write_text(json.dumps(binding,indent=2)+'\n')
        execution={'stage':stage,'reference_id':case,'clip_reference_id':other,'cell':cell,'task_id':manifest['task_id'],'predecessor':None if index==0 else stages[index-1],'adapter_enabled':False,'replace_flag':True,'alg':False,'manual_rope_override':False,'b029_gate':False,'parent_experiment':'B-027'}
        (worker/'configs/execution.json').write_text(json.dumps(execution,indent=2)+'\n')
from contracts import verify_cache_receipt
from media import verify_inputs
for stage in stages:
    worker=root/'stages'/stage
    verify_inputs(worker);verify_cache_receipt(worker)
(root/'reports/crossover-preflight.json').write_text(json.dumps({'status':'PASS','cells':['Y12','Y21'],'changed_per_row':['t2','t8'],'unchanged_per_row':14,'ENC':0,'GPU':0},indent=2)+'\n')
print(json.dumps({'status':'PASS','root':str(root),'GPU':0}))
