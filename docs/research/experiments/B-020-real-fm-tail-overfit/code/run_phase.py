"""One reserved fresh worker per fixed phase; failures stop dependent work."""
from pathlib import Path
import hashlib
import json
import os
import sys
import time
import traceback


def main() -> None:
    root=Path(sys.argv[1]);stage=sys.argv[2]
    assert stage in ('P','PREFIX','BASE_S','BASE_D','TRAIN','TRAIN_S','TRAIN_D')
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
        for name,digest in manifest['files'].items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest
        for name,digest in manifest['upstream'].items():assert hashlib.sha256((root/'upstream'/name).read_bytes()).hexdigest()==digest
        execution=json.loads((root/'configs/execution.json').read_text());assert execution['stage']==stage
        assert execution==manifest['stage_execution'][stage]
        cfg=verify_inputs(root);contract=active_contract(root)
        if stage!='P':
            previous=root.parent/execution['predecessor']
            receipt=json.loads((previous/'reports/pipeline-process.json').read_text())
            assert receipt['reason']=='service_exit' and receipt['returncode']==0 and 'MainPID=0' in receipt['final_service']
            assert json.loads((previous/'reports/result.json').read_text())['status']=='COMPLETED'
            cache=verify_cache_receipt(root)
            p_result=json.loads((root.parent/'P/reports/result.json').read_text())
            assert p_result['condition_receipt_sha256']==hashlib.sha256((root/'artifacts/conditions_receipt.json').read_bytes()).hexdigest()
            if stage in ('BASE_D','TRAIN_D'):
                tree,metadata=load_tree(root/'artifacts/final_latent.safetensors',device='cpu')
                assert metadata['provenance']['config']==cfg
                assert metadata['provenance']['counters']=={'model_calls':80,'completed_steps':40}
                assert metadata['provenance']['condition_sha256']==cache['hashes']['conditions.safetensors']
                assert metadata['provenance']['adapter_enabled']==(stage=='TRAIN_D')
                assert list(tree['x0'][0].shape)==contract.latent_shape
                del tree,metadata
        phase('stage_'+stage+'_start')
        if stage=='P':from phase_prepare import run
        elif stage=='PREFIX':from phase_prefix import run
        elif stage=='TRAIN':from phase_train import run
        elif stage in ('BASE_S','TRAIN_S'):from phase_sample import run
        else:from phase_decode import run
        run(root,cfg);phase('stage_'+stage+'_complete')
        result={'status':'COMPLETED','stage':stage}
        if stage=='P':result['condition_receipt_sha256']=hashlib.sha256((root/'artifacts/conditions_receipt.json').read_bytes()).hexdigest()
        atomic_json(root/'reports/result.json',result)
    except (Exception,KeyboardInterrupt):
        atomic_json(root/'reports/result.json',{'status':'FAILED','stage':stage,'traceback':traceback.format_exc()});raise

if __name__=='__main__':main()
