# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Supervise only the owned component-worker service, with durable systemd limits."""
# Run: python runtime_guard.py ROOT SECONDS COMMAND [ARG...]
from __future__ import annotations

import datetime as dt
import json
import hashlib
import subprocess
import sys
import time
from pathlib import Path
from typing import Final

GIB: Final = 1024**3
DEADLINE: Final = dt.datetime.fromisoformat('2026-10-24T10:30:00+00:00').timestamp()
UNIT: Final = 'make-meme-b019-pipeline'

class GuardBlocked(RuntimeError):
    """Measured resources or deadline prohibit this execution."""


def limits(available: int, swap: int, now: float, deadline: float) -> tuple[int, int]:
    """Policy arithmetic; distinct units retained for testability."""
    seconds = min(14400, int(deadline-now-60))
    if available < 72*GIB or swap != 0 or seconds <= 0:
        raise GuardBlocked('Require72GiB available, zero swap, positive deadline')
    return min(16*GIB, available-24*GIB), seconds


def memory() -> tuple[int, int]:
    """Read actual shared-system available memory and swap usage, in bytes."""
    values = {line.split(':')[0]: int(line.split()[1])*1024 for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith(('MemAvailable:', 'SwapTotal:', 'SwapFree:'))}
    return values['MemAvailable'], values['SwapTotal']-values['SwapFree']


def queue_busy() -> bool:
    """Existing service queue; observation failure fails closed."""
    result = json.loads(subprocess.check_output(['curl','-fsS','--max-time','3','http://127.0.0.1:8190/queue'], timeout=5))
    return bool(result['queue_running'] or result['queue_pending'])


def gpu_pids() -> set[int]:
    """Observe GPU process identities without changing or interrupting them."""
    raw = subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader,nounits'],timeout=5).decode()
    return {int(line.strip()) for line in raw.splitlines() if line.strip().isdigit()}


def main() -> int:
    """Durable deadline plus sampled system/cgroup guard; never stop other units."""
    root = Path(sys.argv[1]); reports = root/'reports'
    reports.mkdir(exist_ok=True)
    available, swap = memory()
    cap, allowed = limits(available, swap, time.time(), DEADLINE)
    seconds = min(int(sys.argv[2]), allowed)
    if queue_busy() or seconds <= 0:
        raise GuardBlocked('Queue occupied or execution time exhausted')
    baseline_gpu = gpu_pids()
    allowed = json.loads((root/'configs/allowed_gpu_processes.json').read_text())
    if not baseline_gpu <= {int(pid) for pid in allowed}:
        raise GuardBlocked('Unapproved existing GPU process; no process will be stopped')
    for pid in baseline_gpu:
        process = Path('/proc')/str(pid)
        expected = allowed[str(pid)]
        if hashlib.sha256((process/'cmdline').read_bytes()).hexdigest()!=expected['cmdline_sha256'] or (process/'stat').read_text().split()[21]!=expected['starttime_ticks']:
            raise GuardBlocked('Existing GPU process identity changed')
    record_path = reports/'pipeline-process.json'
    with record_path.open('x') as stream:
        json.dump({'status':'RESERVED','time':time.time()}, stream)
    command = ['systemd-run','--user','--wait','--pipe','--unit='+UNIT,
        '-p',f'MemoryMax={cap}','-p',f'MemoryHigh={cap-2*GIB}',
        '-p','MemorySwapMax=0','-p','TasksMax=256','-p','KillMode=control-group',
        '-p','TimeoutStopSec=20','-p',f'RuntimeMaxSec={seconds}','--',*sys.argv[3:]]
    record = {'command':command,'started':time.time(),'deadline':time.time()+seconds,'global_deadline':DEADLINE,'memory_cap':cap,'initial_available':available,'baseline_gpu_pids':sorted(baseline_gpu)}
    reason = 'supervisor_observation_failure'; cgroup: Path | None = None
    with (reports/'pipeline.log').open('w') as log:
        child = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
        record['supervisor_pid'] = child.pid
        record_path.write_text(json.dumps(record,indent=2))
        next_queue = time.monotonic()
        try:
            while child.poll() is None:
                available, swap = memory()
                observed = subprocess.check_output(['systemctl','--user','show',UNIT,'-p','ControlGroup','--value'],timeout=5).decode().strip()
                if observed:
                    cgroup = Path('/sys/fs/cgroup')/observed.lstrip('/')
                stats = {}
                if cgroup is not None and cgroup.exists():
                    for name in ('memory.current','memory.peak','memory.events','memory.stat','cgroup.procs'):
                        path = cgroup/name
                        if path.exists():
                            stats[name] = path.read_text()
                    for pid in stats.get('cgroup.procs','').split():
                        status = Path('/proc')/pid/'status'
                        if status.exists():
                            stats['pid-'+pid] = status.read_text()
                with (reports/'resource_metrics.jsonl').open('a') as metrics:
                    metrics.write(json.dumps({'time':time.time(),'available':available,'swap':swap,'cgroup':stats})+'\n')
                if available < 24*GIB or swap != 0:
                    reason = 'system_headroom_or_swap'; break
                if time.time() >= record['deadline']:
                    reason = 'deadline'; break
                if time.monotonic() >= next_queue:
                    owned_pids = {int(p) for p in stats.get('cgroup.procs','').split()}
                    if queue_busy() or gpu_pids()-baseline_gpu-owned_pids:
                        reason = 'other_service_work'; break
                    next_queue = time.monotonic()+10
                time.sleep(1)
            if child.poll() is not None:
                reason = 'service_exit'
        finally:
            if child.poll() is None:
                subprocess.run(['systemctl','--user','stop',UNIT],check=False,timeout=30)
            result = child.wait(timeout=40)
            record.update(reason=reason,returncode=result,finished=time.time())
            record['final_service'] = subprocess.check_output(['systemctl','--user','show',UNIT,'-p','MainPID','-p','Result','-p','ActiveState'],timeout=5).decode()
            record_path.write_text(json.dumps(record,indent=2))
    return result

if __name__ == '__main__':
    raise SystemExit(main())
