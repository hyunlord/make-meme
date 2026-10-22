"""Decode existing inputs using the actual pinned CPU VideoData path."""
from pathlib import Path
import json,sys,hashlib
import numpy as np
from PIL import Image
root=Path(sys.argv[1]);cfg=json.loads((root/'configs/C-real-20261022.json').read_text())
sys.path.insert(0,cfg['upstream'])
from diffsynth.utils.data import VideoData
result={}
for label,path in [('C-real',Path(cfg['condition_video'])),('C-null',root/'inputs/C-null')]:
 data=VideoData(image_folder=str(path),height=288,width=512)
 assert len(data)==17
 rows=[]
 for i in range(17):
  image=data[i];a=np.asarray(image)
  assert a.shape==(288,512,3) and a.dtype==np.uint8
  with Image.open(path/f'{i:03d}.png') as raw: assert image.tobytes()==raw.convert('RGB').tobytes()
  if label=='C-null': assert not a.any()
  rows.append({'frame':i,'mode':image.mode,'shape':list(a.shape),'dtype':str(a.dtype),'min':int(a.min()),'max':int(a.max()),'rgb_sha256':hashlib.sha256(a.tobytes()).hexdigest()})
 result[label]=rows
(root/'reports/decoded_input_audit.json').write_text(json.dumps(result,indent=2))
print('PASS: actual VideoData yields RGB uint8 288x512x3 for both conditions; real equals original grayscale replicated to RGB, null exactly zero.')
