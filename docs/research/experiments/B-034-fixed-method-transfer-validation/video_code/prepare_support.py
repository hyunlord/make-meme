"""Freeze one BASE-assisted support policy, unchanged for all three comparisons."""
from pathlib import Path
import hashlib,json,sys
import numpy as np
from PIL import Image
import torch
from safetensors.torch import save_file
sys.path.insert(0,str(Path(sys.argv[1])/"upstream"))
from clean_constraint import latent_mask
from compositor import mask_assisted,radius_for_sources
root=Path(sys.argv[1]).resolve();assert not (root/'MASK_FREEZE.json').exists()
source=np.stack([np.all(np.asarray(Image.open(root/'inputs/source-mask'/f'{i:03d}.png').convert('RGB'))==[255,0,0],axis=-1) for i in range(17)])
target=np.stack([np.asarray(Image.open(root/'inputs/target-mask'/f'{i:03d}.png').convert('L'))>0 for i in range(17)])
radius=radius_for_sources(source)
edit=np.stack([mask_assisted(s,t,radius) for s,t in zip(source,target)])
mask=latent_mask(torch.from_numpy(edit))
assert np.all(edit[source|target]==1)
groups=[[0],list(range(1,5)),list(range(5,9)),list(range(9,13)),list(range(13,17))]
for index,group in enumerate(groups):
 core=torch.from_numpy((source|target)[group].max(0)).reshape(64,8,112,8).any(3).any(1)
 assert bool((mask[0,0,index][core]==1).all())
np.save(root/'inputs/edit_px.npy',edit);save_file({'M':mask},str(root/'inputs/mask_latent.safetensors'))
files={str(path.relative_to(root)):hashlib.sha256(path.read_bytes()).hexdigest() for path in [*sorted((root/'inputs/target-mask').glob('*.png')),root/'inputs/edit_px.npy',root/'inputs/mask_latent.safetensors']}
(root/'MASK_FREEZE.json').write_text(json.dumps({'files':files,'source_target_core_coverage':True,'radius':radius,'feather':4,'H_empty':True,'temporal_groups':groups,'M_shape':list(mask.shape),'M_mean':float(mask.mean()),'method':'B033 unchanged clean prediction constraint'},indent=2))
print(json.dumps({'status':'SUPPORT_FROZEN','radius':radius,'files':len(files)}))
