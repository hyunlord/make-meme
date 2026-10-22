# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Bounded B007B owned systemd service; standard-library supervisor."""
# Run: python runtime_guard.py ROOT LABEL SECONDS COMMAND [ARG...]
from pathlib import Path
import datetime as dt
import fcntl
import json
import os
import subprocess
import sys
import time
from typing import Final

DEADLINE: Final = dt.datetime.fromisoformat('2026-10-22T13:45:00+00:00').timestamp()
GIB: Final = 1024**3

def memory() -> tuple[int, int]:
    values = {line.split(':')[0]: int(line.split()[1])*1024 for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith(('MemAvailable:', 'SwapTotal:', 'SwapFree:'))}
    return values['MemAvailable'], values['SwapTotal']-values['SwapFree']

def main() -> int:
    root, label = Path(sys.argv[1]), sys.argv[2]
    seconds = min(int(sys.argv[3]), int(DEADLINE-time.time()-60))
    assert seconds > 0 and label.replace('-', '').isalnum()
    reports = root/'reports'; reports.mkdir(parents=True, exist_ok=True)
    assert not (reports/f'{label}-process.json').exists(), 'Duplicate stage label'
    available, swap0 = memory()
    assert available >= 80*GIB, f'Insufficient starting available memory: {available}'
    queue = json.loads(subprocess.check_output(['curl', '-fsS', '--max-time', '5', 'http://127.0.0.1:8190/queue']))
    assert not queue['queue_running'] and not queue['queue_pending']
    if label.startswith('infer-'):
        with (reports/'inference_attempts.jsonl').open('a+') as ledger:
            fcntl.flock(ledger, fcntl.LOCK_EX); ledger.seek(0)
            attempts = list(ledger)
            assert len(attempts) < 2, 'Inference attempt cap reached'
            ledger.write(json.dumps({'label':label, 'attempt':len(attempts)+1, 'reserved_utc':dt.datetime.now(dt.timezone.utc).isoformat()})+'\n'); ledger.flush(); os.fsync(ledger.fileno())
    unit = 'make-meme-b007b-'+label
    command = ['systemd-run', '--user', '--wait', '--pipe', '--unit='+unit, '-p', 'MemoryMax=60G', '-p', 'MemoryHigh=56G', '-p', 'MemorySwapMax=0', '-p', 'TasksMax=256', '-p', 'KillMode=control-group', '-p', 'TimeoutStopSec=20', '-p', f'RuntimeMaxSec={seconds}', '--', *sys.argv[4:]]
    with (reports/f'{label}.log').open('w') as log:
        child = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
        record = {'pid':child.pid, 'unit':unit, 'started':time.time(), 'stage_deadline':time.time()+seconds, 'global_deadline':DEADLINE, 'command':command}
        (reports/f'{label}-process.json').write_text(json.dumps(record,indent=2))
        low = 0; reason = 'service_exit'; next_queue_check = time.monotonic()+10
        cgroup_path = None; observed_cgroup_peak = None
        while child.poll() is None:
            available, swap = memory(); low = low+1 if available < 30*GIB else 0
            if cgroup_path is None:
                observed = subprocess.run(['systemctl', '--user', 'show', unit, '--property=ControlGroup', '--value'], capture_output=True, text=True, check=False)
                if observed.returncode == 0 and observed.stdout.strip():
                    cgroup_path = Path('/sys/fs/cgroup') / observed.stdout.strip().lstrip('/')
            cgroup_memory = {}
            if cgroup_path is not None:
                for filename in ('memory.current', 'memory.peak', 'memory.events'):
                    try:
                        cgroup_memory[filename] = (cgroup_path / filename).read_text().strip()
                    except OSError as error:
                        cgroup_memory[filename] = {'unavailable': str(error)}
                peak = cgroup_memory.get('memory.peak')
                if isinstance(peak, str) and peak.isdigit():
                    observed_cgroup_peak = max(observed_cgroup_peak or 0, int(peak))
            with (reports/'resource_metrics.jsonl').open('a') as metrics:
                metrics.write(json.dumps({'label':label,'time':time.time(),'available':available,'swap':swap,'cgroup':cgroup_memory})+'\n')
            other_work = False
            if time.monotonic() >= next_queue_check:
                check = subprocess.run(['curl','-fsS','--max-time','5','http://127.0.0.1:8190/queue'],capture_output=True,text=True,check=False)
                if check.returncode == 0:
                    current_queue = json.loads(check.stdout)
                    other_work = bool(current_queue['queue_running'] or current_queue['queue_pending'])
                next_queue_check = time.monotonic()+10
            if other_work or low >= 3 or swap-swap0 > GIB or time.time() >= record['stage_deadline']+10:
                reason = ('other_service_work' if other_work else 'available_memory_below_30GiB' if low >= 3 else 'swap_growth_above_1GiB' if swap-swap0 > GIB else 'stage_deadline')
                record['guard_observation'] = {'available': available, 'swap': swap, 'swap_initial': swap0, 'low_samples': low, 'other_work': other_work, 'time': time.time()}
                subprocess.run(['systemctl','--user','stop',unit],check=False,timeout=30)
                break
            time.sleep(1)
        result = child.wait(timeout=40)
    state = subprocess.run(['systemctl','--user','show',unit,'-p','MemoryPeak','-p','MemoryCurrent','-p','Result','-p','ExecMainStatus','-p','ControlGroup'],capture_output=True,text=True,check=False)
    record.update(returncode=result,reason=reason,finished=time.time(),systemd_properties=state.stdout,observed_cgroup_peak=observed_cgroup_peak,cgroup_path=str(cgroup_path) if cgroup_path else None)
    (reports/f'{label}-process.json').write_text(json.dumps(record,indent=2))
    return result

if __name__ == '__main__':
    raise SystemExit(main())
