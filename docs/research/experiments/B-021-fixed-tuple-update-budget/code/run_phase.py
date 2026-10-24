"""One reserved fresh consumer process; B020 caches remain read-only producers."""
from pathlib import Path
import hashlib
import json
import os
import sys
import traceback
import time


def main()->None:
    root=Path(sys.argv[1]);stage=sys.argv[2]
    assert stage in ('TRAIN','PROBE','TRAIN_S','TRAIN_D')
    with (root/'reports/attempt.json').open('x') as stream:json.dump({'stage':stage,'attempt':1,'max':1,'time':time.time(),'retries':0},stream)
    os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_DATASETS_OFFLINE='1',B007E_LOADER_REPORT=str(root/'reports/loader.json'))
    sys.path.insert(0,str(root/'upstream'))
    from artifacts import atomic_json,load_tree
    from contracts import verify_cache_receipt,active_contract
    from media import verify_inputs
    from runtime_observe import initialize,phase
    initialize(root/'reports/phases.jsonl')
    try:
        manifest=json.loads((root/'PREREGISTERED_CODE.json').read_text())
        for name,digest in manifest['files'].items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest,name
        for name,digest in manifest['upstream'].items():assert hashlib.sha256((root/'upstream'/name).read_bytes()).hexdigest()==digest,name
        producer=(root/'producer').resolve()
        assert hashlib.sha256((producer/'PREREGISTERED_CODE.json').read_bytes()).hexdigest()==manifest['producer_code_sha256']
        original=json.loads((producer/'PREREGISTERED_CODE.json').read_text())
        for name,digest in original['files'].items():assert hashlib.sha256((producer/name).read_bytes()).hexdigest()==digest,name
        execution=json.loads((root/'configs/execution.json').read_text());assert execution==manifest['stage_execution'][stage]
        cfg=verify_inputs(root);contract=active_contract(root);cache=verify_cache_receipt(root)
        parent_p=json.loads((producer/'stages/P/reports/result.json').read_text())
        assert parent_p['condition_receipt_sha256']==hashlib.sha256((root/'artifacts/conditions_receipt.json').read_bytes()).hexdigest()
        if execution['predecessor'] is not None:
            previous=root.parent/execution['predecessor']
            receipt=json.loads((previous/'reports/pipeline-process.json').read_text())
            assert receipt['reason']=='service_exit' and receipt['returncode']==0 and 'MainPID=0' in receipt['final_service']
            assert json.loads((previous/'reports/result.json').read_text())['status']=='COMPLETED'
        if stage=='TRAIN_D':
            tree,metadata=load_tree(root/'artifacts/final_latent.safetensors',device='cpu')
            assert metadata['provenance']['config']==cfg
            assert metadata['provenance']['counters']=={'model_calls':80,'completed_steps':40}
            assert metadata['provenance']['condition_sha256']==cache['hashes']['conditions.safetensors']
            assert metadata['provenance']['adapter_enabled'] and metadata['provenance']['executing_experiment']=='B-021'
            assert list(tree['x0'][0].shape)==contract.latent_shape
            del tree,metadata
        phase('stage_'+stage+'_start')
        match stage:
            case 'TRAIN':from phase_train import run
            case 'PROBE':from cuda_probe import run
            case 'TRAIN_S':from phase_sample import run
            case 'TRAIN_D':from phase_decode import run
        run(root,cfg);phase('stage_'+stage+'_complete')
        atomic_json(root/'reports/result.json',{'status':'COMPLETED','stage':stage})
    except (Exception,KeyboardInterrupt):
        atomic_json(root/'reports/result.json',{'status':'FAILED','stage':stage,'traceback':traceback.format_exc()});raise

if __name__=='__main__':main()
