# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
# Run using the existing pinned SCAIL environment; do not install dependencies.
"""CPU-only public-task layout; historical inputs are never imported as conditions."""
from pathlib import Path
import hashlib
import json
import shutil
import sys

root=Path(sys.argv[1]).resolve()
baseline=Path(sys.argv[2]).resolve()
code=Path(sys.argv[3]).resolve()
manifest=json.loads((root/'task_manifest.json').read_text())
assert manifest['source_fps'] is None and manifest['preview_fps']==24 and manifest['timebase_assumed'] is True
assert len(manifest['source_frames'])==17 and len(manifest['target_refs'])==2
assert [ref['reference_id'] for ref in manifest['target_refs']]==['R1','R2']
assert (root/'inputs/R1/reference.png').read_bytes()!=(root/'inputs/R2/reference.png').read_bytes()
(root/'code').symlink_to(code,target_is_directory=True)
(root/'configs').mkdir(exist_ok=True);(root/'reports').mkdir(exist_ok=True)
model_manifest=json.loads((baseline/'PREREGISTERED_INPUTS.json').read_text())
model_manifest={key:model_manifest[key] for key in ('source_commit','hf_revision','versions','weights')}
model_manifest.update(experiment='B-027',weight_provenance='Read-only existing B-025 model lineage; no fresh checkpoint download',task_id=manifest['task_id'])
(root/'PREREGISTERED_INPUTS.json').write_text(json.dumps(model_manifest,indent=2))
(root/'configs/active_case.json').write_text(json.dumps({'name':'public'}))
shutil.copy2(baseline/'configs/allowed_gpu_processes.json',root/'configs/allowed_gpu_processes.json')
base={'name':'public','task_id':manifest['task_id'],'frames':17,'fps':24,'source_fps':None,'timebase_assumed':True,'height':512,'width':896,'seed':20261022,'steps':40,'solver':'unipc','shift':3.0,'guide_scale':5.0,'segment_overlap':5,'adapter':None,'negative_prompt':'','prompt':manifest['prompt'],'precision':'mixed BF16 with FP32 normalization/time/head islands','driver':'inputs/driver.mp4','driver_mask':'inputs/driver-mask.mp4'}
for case in ('R1','R2'):
    (root/'cases'/case/'artifacts').mkdir(parents=True,exist_ok=True)
    cfg={**base,'reference':f'inputs/{case}/reference.png','reference_mask':f'inputs/{case}/reference-mask.png'}
    (root/'configs'/f'{case}.json').write_text(json.dumps(cfg,indent=2))
stages=('ENC','R1_PROBE','R1_S','R1_D','R2_PROBE','R2_S','R2_D')
for index,stage in enumerate(stages):
    worker=root/'stages'/stage;case='R2' if stage.startswith('R2_') else 'R1'
    for name in ('reports','configs'):(worker/name).mkdir(parents=True,exist_ok=True)
    for name in ('code','inputs','PREREGISTERED_INPUTS.json','PREREGISTERED_CODE.json'):(worker/name).symlink_to(root/name)
    (worker/'experiment').symlink_to(root,target_is_directory=True)
    (worker/'artifacts').symlink_to(root/'cases'/case/'artifacts',target_is_directory=True)
    for name in ('models','upstream'):(worker/name).symlink_to((baseline/'stages/LAB_S'/name).resolve(),target_is_directory=True)
    for name in ('active_case.json','allowed_gpu_processes.json'):shutil.copy2(root/'configs'/name,worker/'configs'/name)
    shutil.copy2(root/'configs'/f'{case}.json',worker/'configs/public.json')
    cfg=json.loads((worker/'configs/public.json').read_text())
    paths=[cfg[k] for k in ('reference','reference_mask','driver','driver_mask')]
    paths+=['inputs/R1/reference.png','inputs/R1/reference-mask.png','inputs/R2/reference.png','inputs/R2/reference-mask.png']
    hashes={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in paths}
    hashes['configs/public.json']=hashlib.sha256((worker/'configs/public.json').read_bytes()).hexdigest()
    (worker/'configs/input_config_hashes.json').write_text(json.dumps(hashes,indent=2))
    execution={'stage':stage,'reference_id':case,'task_id':manifest['task_id'],'predecessor':None if index==0 else stages[index-1],'adapter_enabled':False,'replace_flag':True,'alg':False,'manual_rope_override':False}
    (worker/'configs/execution.json').write_text(json.dumps(execution,indent=2))
# CPU-only decoding, resize and normalization with the exact pinned helper.
sys.path.insert(0,str(code));sys.path.insert(0,str(root/'stages/ENC/upstream'))
from media import inputs,verify_inputs
for stage in stages:
    worker=root/'stages'/stage;cfg=verify_inputs(worker)
    if stage=='ENC':
        values=inputs(worker,cfg)
        observed={key:{'shape':list(value.shape),'dtype':str(value.dtype),'sha256':hashlib.sha256(value.contiguous().numpy().tobytes()).hexdigest()} for key,value in values.items()}
        (worker/'configs/expected_preprocessed.json').write_text(json.dumps(observed,indent=2))
upstream=json.loads((baseline/'PREREGISTERED_CODE.json').read_text())['upstream']
(root/'configs/pinned_upstream.json').write_text(json.dumps(upstream,indent=2))
print(json.dumps({'task_id':manifest['task_id'],'stages':list(stages),'CPU_input_checks':'PASS','GPU':0}))
