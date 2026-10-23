"""Fresh bounded B-011 case worker; each P/PROBE/S/D stage runs at most once."""
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import traceback


def main() -> None:
    root=Path(sys.argv[1]);stage=sys.argv[2]
    assert stage in ('P','PROBE','S','D')
    # Record even setup/validation failures; never silently reset a reserved stage.
    with (root/'reports/attempt.json').open('x') as file:
        json.dump({'stage':stage,'time':time.time(),'parent_history':{'E':1,'F':1,'G_reserved':1,'H':1,'B008':1,'B009':1,'B010':0},'max_stage_attempts':1},file)
    os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_DATASETS_OFFLINE='1',B007E_LOADER_REPORT=str(root/'reports/loader.json'))
    sys.path.insert(0,str(root/'upstream'))
    (root/'reports/before_torch_import.json').write_text(json.dumps({'torch_already_imported':'torch' in sys.modules,'time':time.time(),'CUDA_VISIBLE_DEVICES':os.environ.get('CUDA_VISIBLE_DEVICES','UNSET'),'note':'No CUDA API called at this observation'}))
    from artifacts import atomic_json,load_tree
    from contracts import active_contract,verify_cache_receipt
    import torch
    from media import verify_inputs
    from runtime_observe import initialize,phase
    initialize(root/'reports/phases.jsonl')
    try:
        manifest=json.loads((root/'PREREGISTERED_CODE.json').read_text())
        for name,digest in manifest['files'].items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest,name
        for name,digest in manifest['upstream'].items():assert hashlib.sha256((root/'upstream'/name).read_bytes()).hexdigest()==digest,name
        if stage!='P':
            previous=root.parent/{'PROBE':'P','S':'PROBE','D':'S'}[stage]
            receipt=json.loads((previous/'reports/pipeline-process.json').read_text())
            assert receipt['reason']=='service_exit' and receipt['returncode']==0 and 'MainPID=0' in receipt['final_service']
            assert json.loads((previous/'reports/result.json').read_text())['status']=='COMPLETED'
        cfg=verify_inputs(root);contract=active_contract(root)
        if stage!='P':
            prepared=json.loads((root.parent/'P/reports/result.json').read_text())
            assert prepared['status']=='COMPLETED'
            assert prepared['condition_receipt_sha256']==hashlib.sha256((root/'artifacts/conditions_receipt.json').read_bytes()).hexdigest()
            cache_receipt=verify_cache_receipt(root)
            comparison=json.loads((root.parent.parent/'reports/condition_comparison.json').read_text())
            assert comparison['status']=='PASS'
            assert comparison['new_cache_sha256']==cache_receipt['hashes']['conditions.safetensors']
            assert comparison['policy_sha256']==hashlib.sha256((root/'configs/comparison_policy.json').read_bytes()).hexdigest()
            assert comparison['code_manifest_sha256']==hashlib.sha256((root/'PREREGISTERED_CODE.json').read_bytes()).hexdigest()
            path=root/'artifacts'/('final_latent.safetensors' if stage=='D' else 'conditions.safetensors')
            cached,meta=load_tree(path,device='cpu')
            assert meta['provenance']['config']==cfg
            if stage!='D':
                assert meta['file_sha256']==cache_receipt['hashes']['conditions.safetensors']
                assert len(meta['tensors'])==16 and meta['provenance']['experiment']=='B-011'
                assert list(cached['noise'].shape)==contract.latent_shape and cached['history'] is None
                prior_noise=torch.load(root/'artifacts/initial_noise.pt',map_location='cpu',weights_only=True)
                assert torch.equal(cached['noise'],prior_noise)
                digest=hashlib.sha256(cached['noise'].contiguous().numpy().tobytes()).hexdigest()
                assert digest==cache_receipt['initial_noise_sha256']==meta['provenance']['initial_noise_sha256']
                del prior_noise
            else:
                assert meta['provenance']['counters']=={'model_calls':80,'completed_steps':40}
                assert meta['provenance']['executing_experiment']=='B-011'
                assert meta['provenance']['condition_sha256']==cache_receipt['hashes']['conditions.safetensors']
                assert list(cached['x0'][0].shape)==contract.latent_shape
            del cached,meta
        phase('stage_'+stage+'_start')
        if stage in ('PROBE','S'):
            import phase_sample  # Same pre-official import set in probe and S.
            if stage=='PROBE':from cuda_probe import run
            else:run=phase_sample.run
        elif stage=='P':from phase_prepare import run
        else:from phase_decode import run
        run(root,cfg)
        phase('stage_'+stage+'_complete')
        result={'status':'COMPLETED','stage':stage}
        if stage=='P':result['condition_receipt_sha256']=hashlib.sha256((root/'artifacts/conditions_receipt.json').read_bytes()).hexdigest()
        atomic_json(root/'reports/result.json',result)
    except BaseException:
        atomic_json(root/'reports/result.json',{'status':'FAILED','stage':stage,'traceback':traceback.format_exc()})
        raise

if __name__=='__main__':main()
