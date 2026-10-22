# /// script
# requires-python = ">=3.12"
# ///
"""One inference attempt, fail closed before preregistration; no automatic retry."""
from pathlib import Path
import datetime as dt
import fcntl
import hashlib
import json
import re
import subprocess
import sys
import time

root = Path(__file__).resolve().parents[1]
config = Path(sys.argv[1]).resolve()
label = sys.argv[2]
assert re.fullmatch(r"[A-Za-z0-9_-]+",label)
policy = json.loads((root/'configs/policy.json').read_text())
registration = json.loads((root/'configs/PREREGISTRATION.json').read_text())
assert registration['pushed'] is True and re.fullmatch(r'[0-9a-f]{40}',registration['commit'])
assert time.time() < dt.datetime.fromisoformat(policy['deadline']).timestamp()
resolved = json.loads(config.read_text())
assert resolved['adapter'] is None and resolved['mode']=='inference'
ledger = root/'reports/attempts.jsonl'
with Path(policy['shared_gpu_lock']).open('a') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    rows=[json.loads(line) for line in ledger.read_text().splitlines()] if ledger.exists() else []
    attempts=[row for row in rows if row['event']=='started']
    assert len(attempts)<4
    assert not any(row['label']==label for row in attempts)
    # Queue endpoint is an explicitly configured existing service, never guessed.
    if policy.get('queue_url'):
        queue=json.loads(subprocess.check_output(['curl','-fsS','--max-time','5',policy['queue_url']]))
        assert not queue['queue_running'] and not queue['queue_pending']
    row={'event':'started','attempt':len(attempts)+1,'label':label,'config_sha256':hashlib.sha256(config.read_bytes()).hexdigest(),'prereg_commit':registration['commit'],'time':time.time()}
    with ledger.open('a') as handle: handle.write(json.dumps(row)+'\n')
    result=subprocess.run([sys.executable,str(root/'scripts/guard.py'),label,sys.executable,str(root/'scripts/vace_experiment.py'),str(config)],check=False)
    with ledger.open('a') as handle: handle.write(json.dumps({'event':'finished','attempt':row['attempt'],'label':label,'returncode':result.returncode,'time':time.time()})+'\n')
    sys.exit(result.returncode)
