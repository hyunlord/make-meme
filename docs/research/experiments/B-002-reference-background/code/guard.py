# /// script
# requires-python = ">=3.12"
# ///
"""Bounded own-process monitor; terminate ahead of global deadline, never others."""
import datetime as dt
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

root=Path(__file__).resolve().parents[1]
policy=json.loads((root/'configs/policy.json').read_text())
label,*command=sys.argv[1:]
deadline=dt.datetime.fromisoformat(policy['deadline']).timestamp()
start=time.time()
stop=min(deadline-35,start+1800)
def memory():
    return {s[0].rstrip(':'):int(s[1])*1024 for line in Path('/proc/meminfo').read_text().splitlines() if len(s:=line.split())>=3}
initial=memory()
assert start<stop and initial['MemAvailable']>=40*1024**3
with (root/'reports'/f'{label}.log').open('w') as log:
    proc=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    status={'pid':proc.pid,'pgid':proc.pid,'started':start,'hard_deadline':deadline,'terminate_at':stop,'log':str(root/'reports'/f'{label}.log'),'status':'RUNNING'}
    state=root/'reports'/f'{label}-process.json';state.write_text(json.dumps(status,indent=2))
    low=0
    reason='process_exit'
    while proc.poll() is None:
        mem=memory();swap=mem['SwapTotal']-mem['SwapFree'];low=low+1 if mem['MemAvailable']<20*1024**3 else 0
        with (root/'reports/resource_metrics.jsonl').open('a') as out:out.write(json.dumps({'time':time.time(),'label':label,'MemAvailable':mem['MemAvailable'],'swap_used':swap})+'\n')
        if time.time()>=stop or low>=3 or swap-(initial['SwapTotal']-initial['SwapFree'])>1024**3:
            reason='deadline_or_memory_guard';os.killpg(proc.pid,signal.SIGTERM)
            try:proc.wait(timeout=max(0.1,min(25,deadline-time.time()-2)))
            except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
            break
        time.sleep(min(2,max(0.1,stop-time.time())))
    status.update(status='COMPLETED' if proc.returncode==0 else 'FAILED',returncode=proc.returncode,reason=reason,elapsed=time.time()-start)
    state.write_text(json.dumps(status,indent=2))
sys.exit(proc.returncode or 0)
