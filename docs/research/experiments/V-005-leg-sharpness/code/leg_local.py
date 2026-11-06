# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy", "Pillow", "scipy"]
# ///
"""CPU derivative: leg_local.py SCENE PRIVATE_RUNTIME.

Runtime: base_frames, refined_frames, output_summary, base_metrics, native_size,
frame_count, output_dir. SAM/base metrics belong to the refined RAW output.
Writes native PNGs plus manifest; never changes the original or refined RAW.
"""
from __future__ import annotations
from pathlib import Path
import json
import sys
import numpy as np
from PIL import Image
from leg_core import blend,local_alpha
from leg_io import Canvas,atomic_json,digest,fixed_body,read_masks,read_policy,rgb_native


def run(scene: Path, runtime: dict) -> None:
    policy=read_policy(scene)
    canvas=Canvas(policy.master_size,tuple(runtime['native_size']))
    output=Path(runtime['output_dir'])
    output.mkdir(parents=True,exist_ok=False)
    base=json.loads(Path(runtime['base_metrics']).read_text())
    rows={r['frame']:r for r in base['frames']}
    count=int(runtime['frame_count'])
    if len(base['frames'])!=count or set(rows)!=set(range(count)):
        raise ValueError('Every refined frame needs actual base metrics')
    frames=[]
    for index in range(count):
        masks=read_masks(Path(runtime['output_summary']),index,canvas)
        body=fixed_body(base,rows[index],masks,policy.role)
        alpha=canvas.alpha_native(local_alpha(body,index,policy))
        original_path=Path(runtime['base_frames'])/f'{index:03d}.png'
        refined_path=Path(runtime['refined_frames'])/f'{index:03d}.png'
        original,refined=rgb_native(original_path,canvas),rgb_native(refined_path,canvas)
        pixels=blend(original,refined,alpha)
        destination=output/f'{index:03d}.png'
        Image.fromarray(pixels).save(destination)
        with Image.open(destination) as saved:
            assert np.array_equal(np.asarray(saved)[alpha==0],original[alpha==0])
        frames.append({'frame':index,'status':'COMPOSITED' if alpha.any() else 'BASE_ONLY',
                       'lab_detected':body is not None,'edited_pixels':int((alpha>0).sum()),
                       'base_sha256':digest(original_path),'refined_sha256':digest(refined_path),
                       'output_sha256':digest(destination),'exterior_byte_exact':True})
    atomic_json(output/'LOCAL_MANIFEST.json',{'kind':'CPU_LOCAL_COMPOSITE_NOT_MODEL_OUTPUT',
                'scene_sha256':digest(scene),'coordinate_basis':list(policy.master_size),
                'native_size':list(canvas.native),'frames':frames,'quality':'HUMAN_REVIEW_PENDING'})


if __name__=='__main__':
    scene,runtime=map(Path,sys.argv[1:])
    run(scene,json.loads(runtime.read_text()))
