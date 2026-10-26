"""Sequential fresh workers with frozen provenance and one attempt per phase."""
from pathlib import Path
import hashlib,json,os,sys,time,traceback

def main():
    root=Path(sys.argv[1]);stage=sys.argv[2];assert stage in ('VAE','S','D')
    with (root/'reports/attempt.json').open('x') as stream:json.dump({'stage':stage,'attempt':1,'time':time.time()},stream)
    os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',B007E_LOADER_REPORT=str(root/'reports/loader.json'))
    sys.path.insert(0,str(root/'upstream'))
    from artifacts import atomic_json
    from contracts import verify_cache_receipt
    from runtime_observe import initialize,phase
    initialize(root/'reports/phases.jsonl')
    try:
        frozen=json.loads((root/'PREREGISTERED_CODE.json').read_text())
        for path,digest in frozen['files'].items():assert hashlib.sha256((root/'experiment'/path).read_bytes()).hexdigest()==digest,path
        for path,digest in frozen['upstream'].items():assert hashlib.sha256((root/'upstream'/path).read_bytes()).hexdigest()==digest,path
        execution=json.loads((root/'configs/execution.json').read_text());assert execution==frozen['execution'][stage]
        assert execution['adapter_enabled'] is False and execution['replace_flag'] is True and not execution['alg'] and not execution['manual_rope_override'] and not execution['b029_gate']
        if execution['predecessor']:
            previous=root.parent/execution['predecessor'];receipt=json.loads((previous/'reports/pipeline-process.json').read_text())
            assert receipt['reason']=='service_exit' and receipt['returncode']==0 and 'MainPID=0' in receipt['final_service']
            assert json.loads((previous/'reports/result.json').read_text())['status']=='COMPLETED'
        verify_cache_receipt(root)
        cfg=json.loads((root/'configs/public.json').read_text())
        phase(stage+'_start')
        if stage=='S':from phase_sample import run
        else:from phase_vae import run
        run(root,cfg);phase(stage+'_complete');atomic_json(root/'reports/result.json',{'status':'COMPLETED','stage':stage})
    except BaseException:
        atomic_json(root/'reports/result.json',{'status':'FAILED','stage':stage,'traceback':traceback.format_exc()});raise
if __name__=='__main__':main()
