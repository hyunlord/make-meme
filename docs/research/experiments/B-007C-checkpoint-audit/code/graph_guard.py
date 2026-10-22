"""Bounded owned CPU-only static-audit service, with resource evidence."""
from pathlib import Path
import datetime as dt
import json
import subprocess
import sys
import time


def main() -> int:
    root=Path(sys.argv[1]); label=sys.argv[2]
    assert label in ('fixtures','graph-audit')
    deadline=dt.datetime.fromisoformat('2026-10-22T12:21:00+00:00').timestamp()
    seconds=min(1200,int(deadline-time.time()-60)); assert seconds>0
    reports=root/'reports'; reports.mkdir(parents=True,exist_ok=True)
    path=reports/f'{label}-process.json'; assert not path.exists()
    unit='make-meme-b007c-'+label
    command=['systemd-run','--user','--wait','--pipe','--unit='+unit,'-p','MemoryAccounting=yes','-p','MemoryMax=2G','-p','MemoryHigh=1536M','-p','MemorySwapMax=0','-p','TasksMax=32','-p','KillMode=control-group','-p',f'RuntimeMaxSec={seconds}','--','env','CUDA_VISIBLE_DEVICES=','OMP_NUM_THREADS=1','OPENBLAS_NUM_THREADS=1',*sys.argv[3:]]
    with (reports/f'{label}.log').open('x') as log:
        child=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT)
        record={'pid':child.pid,'unit':unit,'command':command,'started':time.time(),'stage_deadline':time.time()+seconds,'global_deadline':deadline}
        path.write_text(json.dumps(record,indent=2))
        while child.poll() is None:
            props=subprocess.run(['systemctl','--user','show',unit,'-p','ControlGroup','-p','MemoryCurrent','-p','MemoryPeak','-p','MainPID'],capture_output=True,text=True,check=False).stdout
            with (reports/f'{label}-resources.jsonl').open('a') as handle:
                handle.write(json.dumps({'time':time.time(),'properties':props})+'\n')
            if time.time()>record['stage_deadline']+10:
                subprocess.run(['systemctl','--user','stop',unit],timeout=30,check=False)
                break
            time.sleep(1)
        record.update(returncode=child.wait(timeout=40),finished=time.time())
        record['final_properties']=subprocess.run(['systemctl','--user','show',unit,'-p','ActiveState','-p','MainPID','-p','ControlGroup','-p','MemoryPeak','-p','ExecMainStatus'],capture_output=True,text=True,check=False).stdout
        path.write_text(json.dumps(record,indent=2))
    return record['returncode']


if __name__=='__main__': raise SystemExit(main())
