"""CPU freeze of manually reviewed BASE support using unchanged B034 math."""
from __future__ import annotations
import ast
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
import numpy as np
from PIL import Image
import torch
import torch.nn.functional as F
from safetensors.torch import save_file

root, original = [Path(x).resolve() for x in sys.argv[1:3]]
assert not (root / 'MASK_FREEZE.json').exists()
spec = importlib.util.spec_from_file_location('b034_compositor', original / 'compositor.py')
assert spec and spec.loader
compositor = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = compositor
spec.loader.exec_module(compositor)
# Execute only the exact existing pure CPU mask function; importing the scheduler
# and Wan model is unnecessary for support preparation.
path = original / 'clean_constraint.py'
tree = ast.parse(path.read_text())
function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'latent_mask')
namespace = {'torch': torch, 'F': F}
exec(compile(ast.Module(body=[function], type_ignores=[]), str(path), 'exec'), namespace)
source = np.stack([np.all(np.asarray(Image.open(root/'inputs/source-mask'/f'{i:03d}.png').convert('RGB')) == [255,0,0], axis=-1) for i in range(17)])
target = np.stack([np.asarray(Image.open(root/'inputs/target-mask'/f'{i:03d}.png').convert('L')) > 0 for i in range(17)])
radius = compositor.radius_for_sources(source)
edit = np.stack([compositor.mask_assisted(s,t,radius) for s,t in zip(source,target)])
mask = namespace['latent_mask'](torch.from_numpy(edit))
assert np.all(edit[source|target] == 1)
groups = [[0],list(range(1,5)),list(range(5,9)),list(range(9,13)),list(range(13,17))]
for index,group in enumerate(groups):
    core = torch.from_numpy((source|target)[group].max(0)).reshape(64,8,112,8).any(3).any(1)
    assert bool((mask[0,0,index][core] == 1).all())
np.save(root/'inputs/edit_px.npy',edit)
save_file({'M':mask},str(root/'inputs/mask_latent.safetensors'))
paths = [*sorted((root/'inputs/source-mask').glob('*.png')), *sorted((root/'inputs/target-mask').glob('*.png')), root/'inputs/edit_px.npy',root/'inputs/mask_latent.safetensors',root/'ANNOTATIONS.json']
hash_file = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
result = {'files':{str(p.relative_to(root)):hash_file(p) for p in paths},'source_target_core_coverage':True,'radius':radius,'feather':4,'H_empty':True,'temporal_groups':groups,'M_shape':list(mask.shape),'M_mean':float(mask.mean()),'E_shape':list(edit.shape),'source_code_sha256':{n:hash_file(original/n) for n in ['compositor.py','clean_constraint.py','prepare_support.py']},'method':'B033 unchanged; existing latent_mask function extracted without Wan/scheduler import','T_status':'MASK_PARTIAL; actual wrong BASE SUV, not intended classic-target ground truth','evaluation_crops_xyxy':[[610,210,810,370],[625,285,800,365]],'post_step_adjustment_allowed':False}
(root/'MASK_FREEZE.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'status':'SUPPORT_FROZEN','radius':radius,'M_shape':list(mask.shape),'M_mean':float(mask.mean()),'MASK_FREEZE_sha256':hash_file(root/'MASK_FREEZE.json')}))
