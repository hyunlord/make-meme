"""CPU-only self-reenactment condition contract; no tensor repair or substitution."""
import ast
import hashlib
import json
import logging
from pathlib import Path
import sys
import numpy as np
from PIL import Image
import torch
import torch.nn.functional as F
from safetensors.torch import load_file
from artifacts import atomic_json,load_tree


def expected_mask(path: Path, source: Path) -> torch.Tensor:
    text=source.read_text();node=next(n for n in ast.parse(text).body if isinstance(n,ast.FunctionDef) and n.name=='extract_and_compress_mask_to_latent')
    scope={'torch':torch,'F':F,'logging':logging}
    exec(compile(ast.Module(body=[node],type_ignores=[]),str(source),'exec'),scope)
    rgb=torch.from_numpy(np.asarray(Image.open(path).convert('RGB')).copy()).permute(2,0,1).float()
    return scope[node.name](((rgb-127.5)/127.5).unsqueeze(1))


def compare_leaf(location: str, a: torch.Tensor, b: torch.Tensor, policy: dict) -> bool:
    """Expected reference/text changes differ; all other values remain constrained."""
    if a.dtype!=b.dtype or not bool(torch.isfinite(b).all()):return False
    if location=='root.arg_c.context[0]':
        return a.ndim==b.ndim==2 and a.shape[1]==b.shape[1] and not torch.equal(a,b)
    if a.shape!=b.shape:return False
    if '.ref_latents[' in location or '.clip_fea' in location:return not torch.equal(a,b)
    if 'mask' in location or location in ('root.noise','root.generator_state','root.timesteps','root.sigmas') or not a.is_floating_point():return torch.equal(a,b)
    return bool(torch.allclose(a,b,rtol=policy['float_unchanged_rtol'],atol=policy['float_unchanged_atol']))


def compare(root: Path) -> None:
    previous=root/'baseline';policy=json.loads((root/'configs/comparison_policy.json').read_text())
    _,old_meta=load_tree(previous/'artifacts/conditions.safetensors',device='cpu')
    _,new_meta=load_tree(root/'artifacts/conditions.safetensors',device='cpu')
    assert old_meta['file_sha256']==policy['baseline_cache_sha256']
    old_config=old_meta['provenance']['config'].copy();new_config=new_meta['provenance']['config'].copy()
    for key in ('name','reference','reference_mask','driver','driver_mask','prompt'):
        assert old_config.pop(key)==policy['old_config'][key]
        assert new_config.pop(key)==policy['new_config'][key]
    assert old_config==new_config
    old=load_file(str(previous/'artifacts/conditions.safetensors'));new=load_file(str(root/'artifacts/conditions.safetensors'))
    assert old_meta['structure']==new_meta['structure'] and set(old)==set(new) and len(new)==16
    source=root/'upstream/wan/utils/scail_utils.py'
    old_mask_path=previous/'inputs/lab/reference-mask-white.png'
    assert hashlib.sha256(old_mask_path.read_bytes()).hexdigest()==policy['baseline_mask_sha256']
    old_mask=expected_mask(old_mask_path,source);new_mask=expected_mask(root/'inputs/self/reference-mask-white.png',source)
    locations={}
    def locate(node,path):
        if 'tensor' in node:locations[node['tensor']]=(path,node['device'])
        elif 'dict' in node:
            for name,item in node['dict'].items():locate(item,path+'.'+name)
        elif 'list' in node:
            for index,item in enumerate(node['list']):locate(item,path+f'[{index}]')
    locate(old_meta['structure'],'root')
    rows=[];passed=True
    for key in old:
        a,b=old[key],new[key];location,device=locations[key];exact=torch.equal(a,b)
        is_ref_mask='.ref_masks[' in location
        if is_ref_mask:
            ok=a.shape==b.shape and a.dtype==b.dtype and torch.equal(a[:,:1],old_mask) and torch.equal(b[:,:1],new_mask) and torch.equal(a[:,1:],b[:,1:]) and not exact
        else:ok=compare_leaf(location,a,b,policy)
        changed=is_ref_mask or '.ref_latents[' in location or '.clip_fea' in location or location=='root.arg_c.context[0]'
        rows.append({'key':key,'location':location,'old_shape':list(a.shape),'new_shape':list(b.shape),'dtype':str(b.dtype),'device':device,'old_sha256':old_meta['tensors'][key]['sha256'],'new_sha256':new_meta['tensors'][key]['sha256'],'exact_equal':exact,'max_abs':float((a.double()-b.double()).abs().max()) if a.shape==b.shape else None,'expected_change':changed,'pass':ok});passed=passed and ok
    assert {row['location'] for row in rows if row['expected_change']}==set(policy['expected_changed_locations'])
    receipt={'status':'PASS' if passed else 'FAIL','rows':rows,'old_cache_sha256':old_meta['file_sha256'],'new_cache_sha256':new_meta['file_sha256'],'policy_sha256':hashlib.sha256((root/'configs/comparison_policy.json').read_bytes()).hexdigest(),'code_manifest_sha256':hashlib.sha256((root/'PREREGISTERED_CODE.json').read_bytes()).hexdigest(),'helper_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'device':'cpu','cuda_initialized':torch.cuda.is_initialized()}
    atomic_json(root/'reports/condition_comparison.json',receipt)
    assert passed,'Unexpected condition difference; S must not run'

if __name__=='__main__':compare(Path(sys.argv[1]))
