"""CPU-only B012-to-Lab task lineage; seven task leaves differ, nine stay controlled."""
from pathlib import Path
import hashlib
import json
import sys
from typing import Final
import torch
from artifacts import atomic_json, load_tree
from compare_conditions import expected_mask

CHANGED: Final = frozenset([
    f'root.{branch}.{field}'
    for branch in ('arg_c','arg_null')
    for field in ('ref_latents[0]','ref_masks[0]','clip_fea')
] + ['root.arg_c.context[0]'])


def compare_leaf(location: str, a: torch.Tensor, b: torch.Tensor) -> bool:
    """Preserve B012 numeric tolerances; discrete/mask/noise controls are exact."""
    if a.dtype!=b.dtype or not bool(torch.isfinite(b).all()):return False
    if location=='root.arg_c.context[0]':return a.ndim==b.ndim==2 and a.shape[1]==b.shape[1]==4096 and 0<a.shape[0]<=512 and 0<b.shape[0]<=512 and not torch.equal(a,b)
    if a.shape!=b.shape:return False
    if '.ref_masks[' in location:return not torch.equal(a[:,:1],b[:,:1]) and torch.equal(a[:,1:],b[:,1:]) and bool((b[:,1:]==0).all())
    if location in CHANGED:return not torch.equal(a,b)
    if 'mask' in location or location in ('root.noise','root.generator_state','root.timesteps','root.sigmas') or not a.is_floating_point():return torch.equal(a,b)
    return bool(torch.allclose(a,b,rtol=1e-5,atol=1e-6))


def compare(root: Path) -> None:
    """Bind old artifacts to preregistered hashes and new artifacts to the actual P pair."""
    baseline=json.loads((root/'configs/lineage_baseline.json').read_text())
    pair=json.loads((root/'reports/condition_comparison.json').read_text())
    assert pair['status']=='PASS'
    cases={};passed=True
    for old_name,new_name in [('MOV','LAB_MOV'),('STILL','LAB_STILL')]:
        old_root=root.parent/baseline['experiment_directory']/'cases'/old_name
        new_root=root/'cases'/new_name
        spec=baseline['cases'][old_name]
        for name,digest in spec['artifacts'].items():assert hashlib.sha256((old_root/'artifacts'/name).read_bytes()).hexdigest()==digest,name
        for name,digest in spec['driving_inputs'].items():
            assert hashlib.sha256((old_root/'inputs'/name).read_bytes()).hexdigest()==digest
            assert hashlib.sha256((new_root/'inputs'/name).read_bytes()).hexdigest()==digest
        old,om=load_tree(old_root/'artifacts/conditions.safetensors',device='cpu')
        new,nm=load_tree(new_root/'artifacts/conditions.safetensors',device='cpu')
        assert nm['file_sha256']==pair['case_cache_sha256'][new_name]
        assert om['structure']==nm['structure'] and len(om['tensors'])==len(nm['tensors'])==16
        old_cfg=om['provenance']['config'];new_cfg=nm['provenance']['config']
        assert {k:v for k,v in old_cfg.items() if k!='prompt'}=={k:v for k,v in new_cfg.items() if k!='prompt'}
        assert old_cfg['prompt']!=new_cfg['prompt']
        expected=expected_mask(new_root/'inputs/reference-mask-white.png',new_root/'upstream/wan/utils/scail_utils.py')
        for branch in ('arg_c','arg_null'):assert torch.equal(new[branch]['ref_masks'][0][:,:1],expected)
        rows=[]
        def visit(node, a, b, location):
            if 'tensor' in node:
                key=node['tensor'];ok=compare_leaf(location,a,b)
                rows.append({'location':location,'baseline_shape':list(a.shape),'shape':list(b.shape),'dtype':str(a.dtype),'device':node['device'],'B012_sha256':om['tensors'][key]['sha256'],'Lab_sha256':nm['tensors'][key]['sha256'],'expected_change':location in CHANGED,'exact_equal':torch.equal(a,b),'max_abs':float((a.double()-b.double()).abs().max()) if a.shape==b.shape else None,'pass':ok})
            elif 'dict' in node:
                for key,child in node['dict'].items():visit(child,a[key],b[key],location+'.'+key)
            elif 'list' in node:
                for index,child in enumerate(node['list']):visit(child,a[index],b[index],location+f'[{index}]')
            else:assert a==b
        visit(om['structure'],old,new,'root')
        assert {row['location'] for row in rows if row['expected_change']}==CHANGED
        case_pass=all(row['pass'] for row in rows);passed=passed and case_pass
        cases[new_name]={'status':'PASS' if case_pass else 'FAIL','baseline_case':old_name,'baseline_cache_sha256':om['file_sha256'],'cache_sha256':nm['file_sha256'],'rows':rows}
    receipt={'status':'PASS' if passed else 'FAIL','cases':cases,'baseline_policy_sha256':hashlib.sha256((root/'configs/lineage_baseline.json').read_bytes()).hexdigest(),'code_manifest_sha256':hashlib.sha256((root/'PREREGISTERED_CODE.json').read_bytes()).hexdigest(),'device':'cpu','cuda_initialized':torch.cuda.is_initialized()}
    atomic_json(root/'reports/lineage_comparison.json',receipt)
    assert passed,'B012-to-Lab controls differ; S must not run'

if __name__=='__main__':compare(Path(sys.argv[1]))
