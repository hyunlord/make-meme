"""Fresh bounded H worker; parent G cache is immutable, P is never rerun."""
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import traceback


def main() -> None:
    root=Path(sys.argv[1]);stage=sys.argv[2]
    assert stage in ('PROBE','S','D')
    # Record even setup/validation failures; never silently reset a reserved stage.
    with (root/'reports/attempt.json').open('x') as file:
        json.dump({'stage':stage,'time':time.time(),'parent_history':{'E':1,'F':1,'G_reserved':1},'max_stage_attempts':1},file)
    os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_DATASETS_OFFLINE='1',B007E_LOADER_REPORT=str(root/'reports/loader.json'))
    sys.path.insert(0,str(root/'upstream'))
    (root/'reports/before_torch_import.json').write_text(json.dumps({'torch_already_imported':'torch' in sys.modules,'time':time.time(),'CUDA_VISIBLE_DEVICES':os.environ.get('CUDA_VISIBLE_DEVICES','UNSET'),'note':'No CUDA API called at this observation'}))
    from artifacts import atomic_json,load_tree
    from media import verify_inputs
    from runtime_observe import initialize,phase
    initialize(root/'reports/phases.jsonl')
    try:
        manifest=json.loads((root/'PREREGISTERED_CODE.json').read_text())
        for name,digest in manifest['files'].items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest,name
        for name,digest in manifest['upstream'].items():assert hashlib.sha256((root/'upstream'/name).read_bytes()).hexdigest()==digest,name
        if stage!='PROBE':
            previous=root.parent/('PROBE' if stage=='S' else 'S')
            receipt=json.loads((previous/'reports/pipeline-process.json').read_text())
            assert receipt['reason']=='service_exit' and receipt['returncode']==0 and 'MainPID=0' in receipt['final_service']
            assert json.loads((previous/'reports/result.json').read_text())['status']=='COMPLETED'
        cfg=verify_inputs(root)
        parent_contract=json.loads((root/'PREREGISTERED_INPUTS.json').read_text())['parent_cache']
        assert hashlib.sha256((root/'artifacts/conditions.json').read_bytes()).hexdigest()==parent_contract['metadata_sha256']
        path=root/'artifacts'/('final_latent.safetensors' if stage=='D' else 'conditions.safetensors')
        cached,meta=load_tree(path,device='cpu')
        if stage!='D':
            assert meta['file_sha256']=='1f1e0b68495b2276a5b6d12eaf160897a16acb2bd2a089e616a55c40bf590308'
            assert len(meta['tensors'])==16 and meta['provenance']['config']==cfg
            assert list(cached['noise'].shape)==[16,5,64,112] and cached['history'] is None
            assert meta['provenance']['initial_noise_sha256']=='9d26386e01a5dce6b0dc21e3df26aab79b65a4403e11b6c8fc5a71873dd3c950'
        else:
            assert meta['provenance']['counters']=={'model_calls':80,'completed_steps':40}
            assert meta['provenance']['config']==cfg
            assert list(cached['x0'][0].shape)==[16,5,64,112]
        del cached,meta
        phase('stage_'+stage+'_start')
        if stage in ('PROBE','S'):
            import phase_sample  # Same pre-official import set in probe and S.
            if stage=='PROBE':from cuda_probe import run
            else:run=phase_sample.run
        else:from phase_decode import run
        run(root,cfg)
        phase('stage_'+stage+'_complete')
        atomic_json(root/'reports/result.json',{'status':'COMPLETED','stage':stage})
    except BaseException:
        atomic_json(root/'reports/result.json',{'status':'FAILED','stage':stage,'traceback':traceback.format_exc()})
        raise

if __name__=='__main__':main()
