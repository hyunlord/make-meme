"""CPU-only neutral RGB outside unchanged exact RED support."""
from pathlib import Path
import hashlib
import json
import sys
import numpy as np
from PIL import Image
root=Path(sys.argv[1]);parent=Path(sys.argv[2]).resolve()
(root/'producer').symlink_to(parent,target_is_directory=True)
(root/'inputs/clip').mkdir(parents=True,exist_ok=True)
for p in (parent/'inputs/clip').iterdir():(root/'inputs/clip'/p.name).symlink_to(p,target_is_directory=p.is_dir())
(root/'PREREGISTERED_INPUTS.json').symlink_to(parent/'PREREGISTERED_INPUTS.json')
(root/'artifacts/initial_noise.pt').symlink_to(parent/'artifacts/initial_noise.pt')
rgb=np.array(Image.open(parent/'inputs/clip/reference.png').convert('RGB'))
mask=np.array(Image.open(parent/'inputs/clip/reference-mask-black.png').convert('RGB'))
assert rgb.shape==mask.shape==(512,896,3)
assert set(map(tuple,np.unique(mask.reshape(-1,3),axis=0)))=={(255,0,0),(0,0,0)}
support=np.all(mask==[255,0,0],axis=-1);new=rgb.copy();new[~support]=128
assert np.array_equal(new[support],rgb[support]);assert np.all(new[~support]==128)
target=root/'inputs/clip/reference-rgb-neutral.png';Image.fromarray(new).save(target)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
(root/'reports/rgb-intervention.json').write_text(json.dumps({'status':'PASS','shape':list(rgb.shape),'support_pixels':int(support.sum()),'outside_pixels':int((~support).sum()),'foreground_rgb_exact':True,'outside_rgb':[128,128,128],'mask_unchanged':True,'original_rgb_sha256':sha(parent/'inputs/clip/reference.png'),'new_rgb_sha256':sha(target),'semantic_mask_sha256':sha(parent/'inputs/clip/reference-mask-black.png')},indent=2))
cfg=json.loads((parent/'configs/real.json').read_text());cfg['reference']='inputs/clip/reference-rgb-neutral.png';(root/'configs/real.json').write_text(json.dumps(cfg,indent=2))
files=json.loads((parent/'configs/input_config_hashes.json').read_text());files.pop('inputs/clip/reference.png');files['inputs/clip/reference-rgb-neutral.png']=sha(target)
for k in files:
 if k.startswith('configs/'):files[k]=sha(root/k)
(root/'configs/input_config_hashes.json').write_text(json.dumps(files,indent=2))
