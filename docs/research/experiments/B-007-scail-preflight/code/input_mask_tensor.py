"""Run exact pinned mask helper and actual CPU driving pre-resize, no model import.
Usage: python input_mask_tensor.py PINNED_SCAIL_ROOT B007_ROOT
"""
import ast
import hashlib
import json
import logging
from pathlib import Path
import subprocess
import sys
import torch
import torch.nn.functional as F
import numpy as np
from PIL import Image

upstream,root=map(Path,sys.argv[1:]);torch.set_num_threads(4)
revision=subprocess.check_output(['git','-C',str(upstream),'rev-parse','HEAD'],text=True).strip()
assert revision=='78fe19576bb06be96c2375e088574a262a300edb'
file=upstream/'wan/utils/scail_utils.py';text=file.read_text();tree=ast.parse(text)
node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='extract_and_compress_mask_to_latent')
function_text=ast.get_source_segment(text,node);assert function_text is not None
namespace={'torch':torch,'F':F,'logging':logging}
exec(compile(ast.Module(body=[node],type_ignores=[]),str(file),'exec'),namespace)
helper=namespace[node.name]
input_dir=root/'inputs/input_preflight';records=[]

def load_image(path):
    pixels=np.array(Image.open(path).convert('RGB'),copy=True)
    records.append({'alias':str(path.relative_to(input_dir)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    return torch.from_numpy(pixels).permute(2,0,1).float()/127.5-1

reference=load_image(input_dir/'reference-mask-512x896.png').unsqueeze(1)
driver=torch.stack([load_image(input_dir/'prepared_mask_local_trim'/f'{i:03d}.png') for i in range(17)],dim=1)
# Exactly scail.py448-453: C,T,H,W is passed to bilinear half-resize, then helper1.
driver_half=F.interpolate(driver,scale_factor=0.5,mode='bilinear',align_corners=False)
outputs={'reference':helper(reference,additional_spatial_downsample=1),
         'driver':helper(driver_half,additional_spatial_downsample=1)}
results={}
for name,value in outputs.items():
    assert value.device.type=='cpu' and torch.isfinite(value).all()
    assert list(value.shape)==([28,1,112,64] if name=='reference' else [28,5,56,32])
    red=[1,8,15,22];other=[i for i in range(28) if i not in red]
    assert torch.count_nonzero(value[other]).item()==0 and torch.count_nonzero(value[red]).item()>0
    assert value.min().item()>=0 and value.max().item()<=1
    fractions=value[(value>0)&(value<1)];assert len(fractions)>0
    results[name]={'shape':list(value.shape),'dtype':str(value.dtype),'device':str(value.device),'red_channel_slots':red,
        'other_color_nonzero':int(torch.count_nonzero(value[other]).item()),'red_nonzero':int(torch.count_nonzero(value[red]).item()),
        'minimum':float(value.min()),'maximum':float(value.max()),'fractional_cell_count':int(fractions.numel()),
        'fraction_examples':torch.unique(fractions)[:12].tolist(),'per_channel_mean':value.mean(dim=(1,2,3)).tolist()}
report={'status':'COMPLETED_CPU_ONLY','upstream_commit':revision,'upstream_file_sha256':hashlib.sha256(file.read_bytes()).hexdigest(),
    'exact_function_sha256':hashlib.sha256(function_text.encode()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    'torch_version':torch.__version__,'source_frames':17,'inputs':records,
    'reference_input_shape':list(reference.shape),'driver_input_shape':list(driver.shape),'driver_half_shape':list(driver_half.shape),
    'actual_call_order':'reference helper(additional_spatial_downsample=1); driver F.interpolate(scale_factor=0.5,bilinear,align_corners=False), then helper(additional_spatial_downsample=1)',
    'correction':'additional_spatial_downsample=2 is not the pinned driver call; resizing before threshold differs from area compression after threshold.',
    'threshold':'channel > (225-127.5)/127.5, strict greater-than; pixels exactly225 are not bright. This check uses exact red/black inputs.',
    'range_note':'Docstring says binary {0,1}, but actual area interpolation yields fractional occupancy. No threshold added after area.',
    'outputs':results,'full_pipeline_import':'NOT_RUN','vae_or_diffusion':'NOT_RUN','gpu':'NOT_USED'}
(root/'reports/input_mask_tensor.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'status':report['status'],'outputs':results},indent=2))
