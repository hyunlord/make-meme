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
    """Exactly four driving leaves change; all other semantic values stay controlled."""
    if a.shape!=b.shape or a.dtype!=b.dtype or not bool(torch.isfinite(b).all()):return False
    if '.pose_latents[' in location or '.driving_masks[' in location:return not torch.equal(a,b)
    if 'mask' in location or location in ('root.noise','root.generator_state','root.timesteps','root.sigmas') or not a.is_floating_point():return torch.equal(a,b)
    return bool(torch.allclose(a,b,rtol=policy['float_unchanged_rtol'],atol=policy['float_unchanged_atol']))


def expected_driving_mask(root: Path, source: Path) -> torch.Tensor:
    """Evaluate the pinned helper on the actual saved normalized mask video, on CPU."""
    text=source.read_text();node=next(n for n in ast.parse(text).body if isinstance(n,ast.FunctionDef) and n.name=='extract_and_compress_mask_to_latent')
    scope={'torch':torch,'F':F,'logging':logging}
    exec(compile(ast.Module(body=[node],type_ignores=[]),str(source),'exec'),scope)
    inputs=torch.load(root/'artifacts/preprocessed_inputs.pt',map_location='cpu',weights_only=True)
    tensor=inputs['driving_mask_video']
    expected=json.loads((root/'configs/expected_preprocessed.json').read_text())['driving_mask_video']
    assert list(tensor.shape)==expected['shape'] and str(tensor.dtype)==expected['dtype']
    assert hashlib.sha256(tensor.contiguous().numpy().tobytes()).hexdigest()==expected['sha256']
    value=F.interpolate(tensor,scale_factor=0.5,mode='bilinear',align_corners=False)
    return scope[node.name](value,additional_spatial_downsample=1)


def compare(root: Path) -> None:
    policy=json.loads((root/'configs/comparison_policy.json').read_text())
    roots=[root/'cases'/case for case in ('MOV','STILL')]
    metadata=[];values=[]
    for case in roots:
        pr=json.loads((case/'stages/P/reports/pipeline-process.json').read_text())
        assert pr['reason']=='service_exit' and pr['returncode']==0 and 'MainPID=0' in pr['final_service']
        result=json.loads((case/'stages/P/reports/result.json').read_text());assert result['status']=='COMPLETED'
        assert result['condition_receipt_sha256']==hashlib.sha256((case/'artifacts/conditions_receipt.json').read_bytes()).hexdigest()
        from contracts import verify_cache_receipt
        verify_cache_receipt(case)
        manifest=json.loads((case/'PREREGISTERED_CODE.json').read_text())
        for name,digest in manifest['case_configs'][case.name].items():assert hashlib.sha256((case/name).read_bytes()).hexdigest()==digest,name
        _,meta=load_tree(case/'artifacts/conditions.safetensors',device='cpu');metadata.append(meta)
        values.append(load_file(str(case/'artifacts/conditions.safetensors')))
    old_meta,new_meta=metadata;old,new=values
    assert old_meta['provenance']['config']==new_meta['provenance']['config']
    assert old_meta['structure']==new_meta['structure'] and set(old)==set(new) and len(new)==16
    source=roots[0]/'upstream/wan/utils/scail_utils.py'
    masks=[expected_driving_mask(case,source) for case in roots]
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
        a,b=old[key],new[key];location,device=locations[key];changed='.pose_latents[' in location or '.driving_masks[' in location
        ok=compare_leaf(location,a,b,policy)
        if '.driving_masks[' in location:ok=ok and torch.equal(a,masks[0]) and torch.equal(b,masks[1])
        rows.append({'key':key,'location':location,'shape':list(a.shape),'dtype':str(a.dtype),'device':device,'MOV_sha256':old_meta['tensors'][key]['sha256'],'STILL_sha256':new_meta['tensors'][key]['sha256'],'exact_equal':torch.equal(a,b),'max_abs':float((a.double()-b.double()).abs().max()),'expected_change':changed,'pass':ok});passed=passed and ok
    assert {row['location'] for row in rows if row['expected_change']}==set(policy['expected_changed_locations'])
    receipt={'status':'PASS' if passed else 'FAIL','rows':rows,'case_cache_sha256':{case:meta['file_sha256'] for case,meta in zip(('MOV','STILL'),metadata)},'policy_sha256':hashlib.sha256((root/'configs/comparison_policy.json').read_bytes()).hexdigest(),'code_manifest_sha256':hashlib.sha256((root/'PREREGISTERED_CODE.json').read_bytes()).hexdigest(),'helper_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'device':'cpu','cuda_initialized':torch.cuda.is_initialized()}
    atomic_json(root/'reports/condition_comparison.json',receipt)
    assert passed,'Unexpected condition difference or insufficient manipulation; S must not run'

if __name__=='__main__':compare(Path(sys.argv[1]))
