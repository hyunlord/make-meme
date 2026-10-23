"""Thin adapter from legacy sampler dictionaries to typed ALG arithmetic."""
import hashlib
import json
import torch
from alg import branch_condition, guided_prediction
from artifacts import load_tree
from contracts import alg_settings


def prepare_prediction(root, model, tree, counters):
    settings=alg_settings(root)
    filtered_tree,sidecar=load_tree(root/'artifacts/filtered_reference.safetensors',device='cpu')
    provenance=sidecar['provenance'];original=tree['arg_c']['ref_latents'][0]
    digest=lambda value:hashlib.sha256(value.detach().cpu().contiguous().view(torch.uint8).numpy().tobytes()).hexdigest()
    assert provenance['parent_ref_sha256']==digest(original)==digest(tree['arg_null']['ref_latents'][0])
    assert provenance['parent_cache_sha256']==hashlib.sha256((root/'artifacts/conditions.safetensors').read_bytes()).hexdigest()
    assert provenance['alg_config']==json.loads((root/'configs/alg.json').read_text())
    assert provenance['filter_code_sha256']==hashlib.sha256((root/'code/alg.py').read_bytes()).hexdigest()
    filtered=filtered_tree['reference'].to(device=original.device,dtype=original.dtype)
    assert filtered.shape==original.shape and digest(filtered)==provenance['filtered_ref_sha256']
    assert filtered.data_ptr()!=original.data_ptr()
    trace=root/'reports/alg_branches.jsonl'
    assert not trace.exists()
    def alg_predict(latents,timestep,positive,negative):
        index=counters['completed_steps']
        def predict(branch):
            condition=branch_condition(branch,positive,negative,filtered)
            reference_hash=provenance['filtered_ref_sha256'] if branch.endswith('low') else provenance['parent_ref_sha256']
            prediction=model(latents,t=timestep,**condition)[0].to(torch.device('cpu'))
            torch.cuda.empty_cache()
            assert bool(torch.isfinite(prediction).all())
            with trace.open('a') as stream:
                stream.write(json.dumps({'step_index':index,'step_fraction':index/39,'branch':branch,
                    'model_call':counters['model_calls'],'reference_sha256':reference_hash,
                    'prediction_norm':float(prediction.float().norm()),'timestep':float(timestep.detach().cpu()[0]),
                    'active':settings.active(index,40)})+'\n');stream.flush()
            return prediction
        result=guided_prediction(predict,settings,index,40,5.0)
        assert bool(torch.isfinite(result).all())
        return result
    return alg_predict,sidecar
