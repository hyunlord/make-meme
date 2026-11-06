# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy", "Pillow", "scipy"]
# ///
"""Run existing Python: leg_metrics.py SCENE PRIVATE_RUNTIME OUTPUT.json.

Runtime: raw_frames, output_summary, base_metrics, native_size, frame_count;
optional input_summary/input_base_metrics for R1 input-mask IoU. Runtime and
paths stay private. The public output contains hashes, measurements and coverage.
"""
from __future__ import annotations
from pathlib import Path
import json
import sys
import numpy as np
from leg_core import frame_metrics, summarize
from leg_io import Canvas, atomic_json, digest, fixed_body, read_masks, read_policy, rgb_master


def run(scene: Path, runtime: dict) -> dict:
    policy=read_policy(scene)
    canvas=Canvas(policy.master_size,tuple(runtime['native_size']))
    base_path=Path(runtime['base_metrics'])
    base=json.loads(base_path.read_text())
    count=int(runtime['frame_count'])
    base_rows={row['frame']:row for row in base['frames']}
    if len(base['frames'])!=count or set(base_rows)!=set(range(count)):
        raise ValueError('Base metrics must cover every frame exactly once')
    input_base=json.loads(Path(runtime['input_base_metrics']).read_text()) if runtime.get('input_base_metrics') else None
    input_rows={row['frame']:row for row in input_base['frames']} if input_base else {}
    valid=canvas.valid()
    frames=[]
    for index in range(count):
        masks=read_masks(Path(runtime['output_summary']),index,canvas)
        body=fixed_body(base,base_rows[index],masks,policy.role)
        reflection=np.zeros_like(valid)
        for track in base_rows[index]['reflection_tracks']:
            if track in masks:
                reflection|=masks[track]
        rgb=rgb_master(Path(runtime['raw_frames'])/f'{index:03d}.png',canvas)
        row=dict(frame_metrics(rgb,body,reflection,valid,policy))
        row.update(frame=index,lab_bbox_master=None,lab_mask_iou_vs_input=None,
                   input_iou_status='NOT_REQUESTED')
        if body is not None and body.any():
            y,x=np.nonzero(body)
            row['lab_bbox_master']=[int(x.min()),int(y.min()),int(x.max()+1),int(y.max()+1)]
        if input_base is not None:
            im=read_masks(Path(runtime['input_summary']),index,canvas)
            ib=fixed_body(input_base,input_rows[index],im,policy.role)
            row['input_iou_status']='MISSING_MASK'
            if ib is not None and body is not None and (ib|body).any():
                row['lab_mask_iou_vs_input']=float((ib&body).sum()/(ib|body).sum())
                row['input_iou_status']='MEASURED'
        frames.append(row)
    observed=[r['lab_mask_iou_vs_input'] for r in frames if r['lab_mask_iou_vs_input'] is not None]
    return {'quality':'HUMAN_REVIEW_PENDING','automatic_ranking':False,'frame_count':count,
            'measurement_policy':json.loads(scene.read_text())['measurement_policy'],
            'scene_sha256':digest(scene),'inputs_sha256':{key:digest(Path(runtime[key])) for key in
            ('output_summary','base_metrics','input_summary','input_base_metrics') if runtime.get(key)},
            'rgb_frame_sha256':[digest(Path(runtime['raw_frames'])/f'{i:03d}.png') for i in range(count)],
            'coordinate_basis':list(policy.master_size),'native_size':list(canvas.native),
            'resized_before_crop':list(canvas.resized),'crop_offset':list(canvas.offset),'observed_canvas_pixels':int(valid.sum()),
            'frames':frames,'summary':summarize(frames,policy),
            'input_mask_iou':{'observed':len(observed),'total':count,'mean':float(np.mean(observed)) if observed else None},
            'limitations':['Brightness ratio is a transparency proxy, not alpha recovery.',
                          'Laplacian includes mask-cut boundaries and may reflect texture or noise.',
                          'Observed-only aggregates retain missing coverage; no automatic ranking.',
                          'Kling lighting and body size differ; reference only.']}


if __name__=='__main__':
    scene,runtime,output=map(Path,sys.argv[1:])
    atomic_json(output,run(scene,json.loads(runtime.read_text())))
