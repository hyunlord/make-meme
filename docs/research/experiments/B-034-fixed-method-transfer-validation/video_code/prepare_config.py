"""Create the fixed per-task video config after parent accepts that task's A0."""
from pathlib import Path
import json,shutil,sys
root=Path(sys.argv[1]);manifest=json.loads((root/'task_manifest.json').read_text())
(root/'configs').mkdir(exist_ok=True)
assert not (root/'configs/public.json').exists()
assert (root/'inputs/anchor/mask-receipt.json').exists()
caption=manifest['caption'];alias=manifest.get('case_id',manifest.get('alias'))
assert alias in ('rigid_R1','nonrigid_R1')
cfg={'name':'public','task_id':alias,'frames':17,'fps':24,'source_fps':None,'timebase_assumed':True,'height':512,'width':896,'seed':20261022,'steps':40,'solver':'unipc','shift':3.0,'guide_scale':5.0,'segment_overlap':5,'adapter':None,'negative_prompt':'','prompt':caption,'precision':'mixed BF16 with FP32 normalization/time/head islands','driver':'inputs/driver.mp4','driver_mask':'inputs/driver-mask.mp4','reference':'inputs/anchor/reference.png','reference_mask':'inputs/anchor/reference-mask.png'}
(root/'configs/public.json').write_text(json.dumps(cfg,indent=2))
shutil.copyfile(root.parent.parent/'configs/allowed_gpu_processes.json',root/'configs/allowed_gpu_processes.json')
(root/'PREREGISTERED_INPUTS.json').write_text(json.dumps({'experiment':'B-034','task':manifest,'A0_mask':json.loads((root/'inputs/anchor/mask-receipt.json').read_text()),'source_fps':None,'preview_fps':24,'timebase_assumed':True},indent=2))
print(alias)
