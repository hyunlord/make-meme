"""Reproduce lossless raw extraction and private manual-polygon rasterization."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
import torch


def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument('--raw',type=Path,required=True)
    parser.add_argument('--polygons',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=False)
    raw=torch.load(args.raw,map_location='cpu',weights_only=True)
    if not isinstance(raw,torch.Tensor) or tuple(raw.shape)!=(3,17,512,896) or raw.dtype!=torch.float32:
        raise ValueError('Expected B031 CTHW float32 raw tensor')
    frames=raw.permute(1,2,3,0).contiguous().numpy()
    if not np.isfinite(frames).all() or frames.min() < -1 or frames.max() > 1:
        raise ValueError('Invalid raw values')
    np.save(args.output/'generated_float.npy',frames,allow_pickle=False)
    records=json.loads(args.polygons.read_text())['frames']
    if [r['frame'] for r in records]!=list(range(17)): raise ValueError('Polygon frame order')
    (args.output/'target').mkdir()
    for record in records:
        if record['shadow_polygons']: raise ValueError('Frozen B032 H is empty')
        mask=Image.new('L',(896,512),0)
        ImageDraw.Draw(mask).polygon([tuple(p) for p in record['polygon_xy']],fill=255)
        mask.save(args.output/'target'/f"{record['frame']:03}.png")
if __name__=='__main__': main()
