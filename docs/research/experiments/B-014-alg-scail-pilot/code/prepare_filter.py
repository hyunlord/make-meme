"""CPU-only derived reference; parent cache and all 16 leaves remain immutable."""
from pathlib import Path
import hashlib
import json
import sys
import torch
from alg import low_pass_reference, spatial_size
from artifacts import load_tree, save_tree
from contracts import alg_settings, verify_cache_receipt


def main(root: Path) -> None:
    receipt=verify_cache_receipt(root);settings=alg_settings(root)
    tree,metadata=load_tree(root/'artifacts/conditions.safetensors',device='cpu')
    positive=tree['arg_c']['ref_latents'][0];negative=tree['arg_null']['ref_latents'][0]
    assert torch.equal(positive,negative) and list(positive.shape)==[16,1,112,64] and positive.dtype==torch.float32
    rng=torch.get_rng_state().clone();original=positive.clone()
    filtered=low_pass_reference(positive,settings.ratio)
    assert torch.equal(positive,original) and torch.equal(rng,torch.get_rng_state())
    assert bool(torch.isfinite(filtered).all())
    assert torch.equal(filtered,positive) if settings.ratio==1 else not torch.equal(filtered,positive)
    digest=lambda value:hashlib.sha256(value.contiguous().view(torch.uint8).numpy().tobytes()).hexdigest()
    provenance={'experiment':'B-014','parent_cache_sha256':receipt['hashes']['conditions.safetensors'],
        'parent_ref_sha256':digest(positive),'filtered_ref_sha256':digest(filtered),
        'alg_config':json.loads((root/'configs/alg.json').read_text()),'parent_code_sha256':receipt['code_sha256'],
        'filter_code_sha256':hashlib.sha256((root/'code/alg.py').read_bytes()).hexdigest(),
        'input_shape':list(positive.shape),'intermediate_size':list(spatial_size(112,64,settings.ratio)),
        'active_indices':[i for i in range(40) if settings.active(i,40)],'rng_unchanged':True,
        'original_ref_unchanged':True,'parent_leaf_count':len(metadata['tensors'])}
    save_tree(root/'artifacts/filtered_reference.safetensors',{'reference':filtered},provenance)


if __name__=='__main__':main(Path(sys.argv[1]))
