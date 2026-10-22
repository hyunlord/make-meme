"""Bounded owned-process supervisor; no unrelated process termination."""
from pathlib import Path
import datetime as dt
import json
import os
import signal
import subprocess
import sys
import time

root=Path(sys.argv[1]);label=sys.argv[2];deadline=dt.datetime.fromisoformat('2026-10-22T08:01:33+00:00').timestamp()
def memory():
    values={line.split(':')[0]:int(line.split()[1])*1024 for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith(('MemAvailable:','SwapTotal:','SwapFree:'))}
    return values['MemAvailable'],values['SwapTotal']-values['SwapFree']
available,swap0=memory()
method_deadline=min(time.time()+2100,deadline-900) if label.startswith('build') else min(time.time()+300,deadline-120)
assert available>=40*1024**3 and time.time()<method_deadline-60
queue=json.loads(subprocess.check_output(['curl','-fsS','--max-time','5','http://127.0.0.1:8190/queue']))
assert not queue['queue_running'] and not queue['queue_pending']
(root/'reports').mkdir(parents=True,exist_ok=True)
with (root/'reports'/f'{label}.log').open('w') as log:
    child=subprocess.Popen(sys.argv[3:],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    record={'pid':child.pid,'pgid':child.pid,'deadline':deadline,'method_deadline':method_deadline,'command':sys.argv[3:],'started':time.time()}
    (root/'reports'/f'{label}-process.json').write_text(json.dumps(record,indent=2))
    low=0;reason='process_exit'
    while child.poll() is None:
        available,swap=memory();low=low+1 if available<20*1024**3 else 0
        with (root/'reports/kernel_resources.jsonl').open('a') as handle:handle.write(json.dumps({'label':label,'time':time.time(),'available':available,'swap':swap})+'\n')
        if time.time()>=method_deadline or low>=3 or swap-swap0>1024**3:
            reason='deadline_or_memory_guard';os.killpg(child.pid,signal.SIGTERM)
            try:child.wait(timeout=max(1,min(25,deadline-time.time()-5)))
            except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL)
            break
        time.sleep(2)
    child.wait();record.update(returncode=child.returncode,reason=reason,finished=time.time());(root/'reports'/f'{label}-process.json').write_text(json.dumps(record,indent=2))
sys.exit(child.returncode)
