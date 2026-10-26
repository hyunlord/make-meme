# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
# Run: python prepare_inputs.py B027_ROOT B028_ROOT
"""Derive six normalized references; source and historical artifacts stay read-only."""
from dataclasses import asdict
from pathlib import Path
import hashlib
import json
import sys
import numpy as np
from PIL import Image, ImageDraw
from normalize import normalize

baseline, output = map(Path, sys.argv[1:3])
for task in ('animal','human','vehicle'):
    parent = baseline/'tasks'/task
    root = output/'tasks'/task
    inputs = root/'inputs'
    inputs.mkdir(parents=True, exist_ok=False)
    (root/'parent_b027').symlink_to(parent, target_is_directory=True)
    for name in ('driver.mp4','driver-mask.mp4','source','source-mask'):
        (inputs/name).symlink_to(parent/'inputs'/name)
    manifest = json.loads((parent/'task_manifest.json').read_text())
    changes = []
    for case in ('R1','R2'):
        old = parent/'inputs'/case
        new = inputs/case
        new.mkdir()
        rgb = Image.open(old/'reference.png').convert('RGB')
        semantic = np.asarray(Image.open(old/'reference-mask.png').convert('RGB'))
        mask = Image.fromarray(np.uint8(np.all(semantic == (255,0,0), axis=-1))*255)
        warped, support, geometry = normalize(rgb, mask)
        colors = np.zeros((512,896,3), dtype=np.uint8)
        colors[np.asarray(support) != 0] = (255,0,0)
        warped.save(new/'reference.png')
        Image.fromarray(colors).save(new/'reference-mask.png')
        support.save(new/'support.png')
        board = Image.new('RGB',(1792,548),(25,25,25))
        board.paste(rgb,(0,36));board.paste(warped,(896,36))
        ImageDraw.Draw(board).text((8,8),f'{task} {case} B027 | B028 q=0.80; resampling not restored information',fill='white')
        board.save(new/'comparison.png')
        digest=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
        changes.append({'case':case,**asdict(geometry),'input_bbox':mask.getbbox(),'output_bbox':support.getbbox(),
            'input_area':int(np.count_nonzero(np.asarray(mask))),'output_area':int(np.count_nonzero(np.asarray(support))),
            'old_rgb_sha256':digest(old/'reference.png'),'old_mask_sha256':digest(old/'reference-mask.png'),
            'new_rgb_sha256':digest(new/'reference.png'),'new_mask_sha256':digest(new/'reference-mask.png'),
            'pixel_coordinate':'Pillow affine inverse maps destination pixel centers in pixel-edge coordinate system',
            'rgb_resampling':'bicubic','support_resampling':'nearest','outside_rgb':128})
    manifest['experiment']='B-028'
    manifest['reference_normalization']=changes
    (root/'task_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(task, [(row['case'],row['scale']) for row in changes])
