# /// script
# dependencies = ["Pillow"]
# ///
# Run: python3 prepare_inputs.py B005_ROOT B006_ROOT
"""Copy only verified original RGB/Canny inputs; never generated output frames."""
import hashlib
import json
from pathlib import Path
import shutil
import sys
from PIL import Image

base, root = Path(sys.argv[1]), Path(sys.argv[2])
records = json.loads((base/'reports/reuse-copy.json').read_text())
record = next(item for item in records if item['condition']=='bg-real' and item['seed']==20261022)
expected = {item['path']:item['copy_sha256'] for item in record['files']}
folder=base/'outputs/bg-real-20261022'
manifest=[]
for source_kind, destination_kind in [('target','source'),('condition','canny')]:
    dest=root/'inputs'/destination_kind;dest.mkdir(parents=True,exist_ok=True)
    for frame in range(17):
        rel=f'{source_kind}/{frame:03d}.png';p=folder/rel;q=dest/f'{frame:03d}.png'
        digest=hashlib.sha256(p.read_bytes()).hexdigest();assert digest==expected[rel]
        with Image.open(p) as image:
            assert image.size==(512,288)
            rgb_hash=hashlib.sha256(image.convert('RGB').tobytes()).hexdigest()
        if q.exists():assert hashlib.sha256(q.read_bytes()).hexdigest()==digest
        else:shutil.copy2(p,q)
        manifest.append({'frame':frame,'kind':destination_kind,'source_alias':f'B005/bg-real-20261022/{rel}',
                         'sha256':digest,'decoded_rgb_sha256':rgb_hash,'destination':str(q.relative_to(root))})
(root/'inputs/manifest.json').write_text(json.dumps({'fps':24,'frames':17,'width':512,'height':288,'files':manifest,
    'origin':'Original source f0..16 and nonlearned Canny70/150; not generated images'},indent=2)+'\n')
print('34 original input files verified/copied; no generation.')
