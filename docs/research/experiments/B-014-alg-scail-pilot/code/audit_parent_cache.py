"""CPU-only verification against actual immutable B013 cache, not model inference."""
import hashlib
from pathlib import Path
import sys
import torch
from alg import branch_condition
from artifacts import load_tree,atomic_json
from contracts import verify_cache_receipt,expected_calls


def main(root:Path) -> None:
    receipt=verify_cache_receipt(root)
    tree,meta=load_tree(root/'artifacts/conditions.safetensors',device='cpu')
    filtered,sidecar=load_tree(root/'artifacts/filtered_reference.safetensors',device='cpu')
    positive,negative=tree['arg_c'],tree['arg_null'];rng=torch.get_rng_state().clone()
    observations=[]
    for branch in ('u_orig','u_low','c_low','c_orig'):
        base=positive if branch.startswith('c_') else negative
        selected=branch_condition(branch,positive,negative,filtered['reference'])
        unchanged=[name for name in base if name!='ref_latents' and selected[name] is base[name]]
        assert len(unchanged)==len(base)-1
        assert selected['ref_latents'][0] is (filtered['reference'] if branch.endswith('low') else base['ref_latents'][0])
        observations.append({'branch':branch,'unchanged_kwargs':unchanged,'reference_source':'filtered_cpu_sidecar' if branch.endswith('low') else 'original_parent'})
    assert torch.equal(rng,torch.get_rng_state())
    assert hashlib.sha256((root/'artifacts/conditions.safetensors').read_bytes()).hexdigest()==receipt['hashes']['conditions.safetensors']
    assert len(meta['tensors'])==16
    atomic_json(root/'reports/actual_parent_cache_audit.json',{'status':'PASS','scope':'CPU actual-cache contract; no DiT quality claim',
        'parent_cache_sha256':meta['file_sha256'],'parent_all_16_value_hashes_verified':True,'observations':observations,
        'rng_unchanged':True,'expected_calls':expected_calls(root),'filter_provenance':sidecar['provenance'],
        'unchanged_parent_receipt':verify_cache_receipt(root)==receipt})


if __name__=='__main__':main(Path(sys.argv[1]))
