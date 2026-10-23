"""CPU-only preregistered single-factor gate; never repair or replace a tensor."""
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


def compare(root: Path) -> None:
    previous=root/'baseline';policy=json.loads((root/'configs/comparison_policy.json').read_text())
    _,old_meta=load_tree(previous/'artifacts/conditions.safetensors',device='cpu')
    _,new_meta=load_tree(root/'artifacts/conditions.safetensors',device='cpu')
    assert old_meta['file_sha256']==policy['baseline_cache_sha256']
    old_config=old_meta['provenance']['config'].copy();new_config=new_meta['provenance']['config'].copy()
    assert old_config.pop('reference_mask')=='inputs/lab/reference-mask.png'
    assert new_config.pop('reference_mask')=='inputs/lab/reference-mask-white.png'
    assert old_config==new_config
    old=load_file(str(previous/'artifacts/conditions.safetensors'));new=load_file(str(root/'artifacts/conditions.safetensors'))
    assert old_meta['structure']==new_meta['structure'] and set(old)==set(new)
    source=root/'upstream/wan/utils/scail_utils.py'
    old_mask_path=root/'inputs/lab/reference-mask.png'
    assert hashlib.sha256(old_mask_path.read_bytes()).hexdigest()==policy['baseline_mask_sha256']
    old_mask=expected_mask(old_mask_path,source)
    new_mask=expected_mask(root/'inputs/lab/reference-mask-white.png',source)
    locations={}
    def locate(node,path):
        if 'tensor' in node:locations[node['tensor']]=path
        elif 'dict' in node:
            for name,item in node['dict'].items():locate(item,path+'.'+name)
        elif 'list' in node:
            for index,item in enumerate(node['list']):locate(item,path+f'[{index}]')
    locate(old_meta['structure'],'root')
    rows=[];passed=True
    mask_keys=[old_meta['structure']['dict'][branch]['dict']['ref_masks']['list'][0]['tensor'] for branch in ('arg_c','arg_null')]
    exact_keys={old_meta['structure']['dict'][name]['tensor'] for name in ('noise','generator_state','timesteps','sigmas')}
    for key in old:
        a,b=old[key],new[key];assert a.shape==b.shape and a.dtype==b.dtype
        exact=torch.equal(a,b);maximum=float((a.double()-b.double()).abs().max())
        if key in mask_keys:
            white=[0,7,14,21];other=[i for i in range(28) if i not in white]
            ok=torch.equal(a[:,:1],old_mask) and torch.equal(b[:,:1],new_mask) and torch.equal(a[:,1:],b[:,1:]) and torch.equal(a[other],b[other])
            ok=ok and bool((b[white,:1]>a[white,:1]).any())
        elif key in exact_keys or 'mask' in locations[key] or not a.is_floating_point():ok=exact
        else:ok=bool(torch.allclose(a,b,rtol=policy['float_unchanged_rtol'],atol=policy['float_unchanged_atol']))
        rows.append({'key':key,'location':locations[key],'shape':list(a.shape),'dtype':str(a.dtype),'exact_equal':exact,'max_abs':maximum,'mask_intervention':key in mask_keys,'pass':ok});passed=passed and ok
    receipt={'status':'PASS' if passed else 'FAIL','rows':rows,'mask_keys':mask_keys,'old_cache_sha256':old_meta['file_sha256'],'new_cache_sha256':new_meta['file_sha256'],'policy_sha256':hashlib.sha256((root/'configs/comparison_policy.json').read_bytes()).hexdigest(),'code_manifest_sha256':hashlib.sha256((root/'PREREGISTERED_CODE.json').read_bytes()).hexdigest(),'helper_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'device':'cpu','cuda_initialized':torch.cuda.is_initialized()}
    atomic_json(root/'reports/condition_comparison.json',receipt)
    assert passed,'Unexpected condition difference; S must not run'

if __name__=='__main__':compare(Path(sys.argv[1]))
