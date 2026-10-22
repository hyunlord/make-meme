"""Fresh exec worker; exclusive stage reservation and immutable handoff contracts."""
import json
import hashlib
import os
from pathlib import Path
import sys
import time
import traceback


def main() -> None:
    root=Path(sys.argv[1]);stage=sys.argv[2]
    assert stage in ('P','S','D')
    manifest=json.loads((root/'PREREGISTERED_CODE.json').read_text())
    for name,digest in manifest['files'].items():
        assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest,name
    for name,digest in manifest['upstream'].items():
        assert hashlib.sha256((root/'upstream'/name).read_bytes()).hexdigest()==digest,name
    if stage!='P':
        previous=root.parent/('P' if stage=='S' else 'S')
        receipt=json.loads((previous/'reports/pipeline-process.json').read_text())
        assert receipt['reason']=='service_exit' and receipt['returncode']==0 and 'MainPID=0' in receipt['final_service']
        assert json.loads((previous/'reports/result.json').read_text())['status']=='COMPLETED'
    os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_DATASETS_OFFLINE='1',B007E_LOADER_REPORT=str(root/'reports/loader.json'))
    sys.path.insert(0,str(root/'upstream'))
    from media import verify_inputs
    from runtime_observe import initialize,phase
    from artifacts import atomic_json,load_tree
    cfg=verify_inputs(root)
    if stage!='P':
        cached,metadata=load_tree(root/'artifacts'/('conditions.safetensors' if stage=='S' else 'final_latent.safetensors'),device='cpu')
        if stage=='S':
            assert list(cached['noise'].shape)==[16,5,64,112] and str(cached['noise'].dtype)=='torch.float32'
            assert cached['history'] is None and metadata['provenance']['config']==cfg
            assert metadata['provenance']['initial_noise_sha256']=='9d26386e01a5dce6b0dc21e3df26aab79b65a4403e11b6c8fc5a71873dd3c950'
        else:
            assert len(cached['x0'])==1 and list(cached['x0'][0].shape)==[16,5,64,112]
            assert metadata['provenance']['counters']=={'model_calls':80,'completed_steps':40}
            assert metadata['provenance']['config']==cfg
        del cached,metadata
    initialize(root/'reports/phases.jsonl')
    with (root/'reports/attempt.json').open('x') as file:
        json.dump({'stage':stage,'time':time.time(),'parent_history':{'E':1,'F':1},'G_sampler_cap':1,'stage_cap':1},file)
    phase('stage_'+stage+'_start')
    try:
        if stage=='P':from phase_prepare import run
        elif stage=='S':from phase_sample import run
        else:from phase_decode import run
        run(root,cfg)
        phase('stage_'+stage+'_complete')
        atomic_json(root/'reports/result.json',{'status':'COMPLETED','stage':stage})
    except BaseException:
        atomic_json(root/'reports/result.json',{'status':'FAILED','stage':stage,'traceback':traceback.format_exc()})
        raise

if __name__=='__main__':main()
