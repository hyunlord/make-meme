"""One attempt per sequential B034 stage, preserving BASE/STEP shared inputs."""
from pathlib import Path
import hashlib,json,os,sys,time,traceback

def main():
    root=Path(sys.argv[1]);stage=sys.argv[2];assert stage in ('ENC','BASE_S','BASE_D','CONTROL_D','STEP_S','STEP_D')
    with (root/'reports/attempt.json').open('x') as stream:json.dump({'stage':stage,'attempt':1,'time':time.time()},stream)
    os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',B007E_LOADER_REPORT=str(root/'reports/loader.json'))
    sys.path.insert(0,str(root/'upstream'))
    from artifacts import atomic_json
    from contracts import verify_cache_receipt
    from media import verify_inputs
    from runtime_observe import initialize,phase
    initialize(root/'reports/phases.jsonl')
    try:
        experiment=(root/'experiment').resolve();frozen=json.loads((root/'PREREGISTERED_CODE.json').read_text())
        for path,digest in frozen['files'].items():assert hashlib.sha256((experiment/path).read_bytes()).hexdigest()==digest,path
        for path,digest in frozen['upstream'].items():assert hashlib.sha256((root/'upstream'/path).read_bytes()).hexdigest()==digest,path
        execution=json.loads((root/'configs/execution.json').read_text());assert execution==frozen['execution'][stage]
        assert not execution['adapter_enabled'] and execution['replace_flag'] and not execution['alg'] and not execution['manual_rope_override'] and not execution['b029_gate']
        if execution['predecessor']:
            previous=root.parent/execution['predecessor'];receipt=json.loads((previous/'reports/pipeline-process.json').read_text())
            assert receipt['reason']=='service_exit' and receipt['returncode']==0 and 'MainPID=0' in receipt['final_service']
            assert json.loads((previous/'reports/result.json').read_text())['status']=='COMPLETED'
        if stage!='ENC':verify_cache_receipt(root)
        if stage in ('CONTROL_D','STEP_S','STEP_D'):
            mask_freeze=json.loads((experiment/'MASK_FREEZE.json').read_text());assert mask_freeze['source_target_core_coverage'] is True
            for path,digest in mask_freeze['files'].items():assert hashlib.sha256((experiment/path).read_bytes()).hexdigest()==digest,path
        cfg=verify_inputs(root);phase(stage+'_start')
        if stage=='ENC':from phase_encode import run
        elif stage.endswith('_S'):from phase_sample import run
        else:from phase_decode import run
        run(root,cfg);phase(stage+'_complete');atomic_json(root/'reports/result.json',{'status':'COMPLETED','stage':stage})
    except BaseException:
        atomic_json(root/'reports/result.json',{'status':'FAILED','stage':stage,'traceback':traceback.format_exc()});raise
if __name__=='__main__':main()
