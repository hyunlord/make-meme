"""CPU fixed input manifest; only reference semantic mask and mode change."""
from pathlib import Path
import hashlib
import json
import sys
root=Path(sys.argv[1]);parent=root/'producer'
cfg=json.loads((parent/'configs/real.json').read_text());cfg['reference_mask']='inputs/clip/reference-mask-black.png'
(root/'configs/real.json').write_text(json.dumps(cfg,indent=2))
original=json.loads((parent/'configs/input_config_hashes.json').read_text())
files={k:v for k,v in original.items() if not k.startswith('configs/fm') and not k.startswith('inputs/fm-')}
files.pop('inputs/clip/reference-mask-white.png')
files['inputs/clip/reference-mask-black.png']=hashlib.sha256((root/cfg['reference_mask']).read_bytes()).hexdigest()
for key in list(files):
    if key.startswith('configs/'):
        files[key]=hashlib.sha256((root/key).read_bytes()).hexdigest()
(root/'configs/input_config_hashes.json').write_text(json.dumps(files,indent=2))
