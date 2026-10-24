# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Keep the system-memory watchdog alive independently of SSH/session lifetime."""
# Run: python runtime_launch.py ROOT SECONDS COMMAND [ARG...]
import json
import subprocess
import sys
import time
from pathlib import Path
from runtime_guard import DEADLINE, UNIT

root = Path(sys.argv[1])
seconds = min(int(sys.argv[2]), int(DEADLINE-time.time()-90))
assert seconds > 0
command = ['systemd-run','--user','--wait','--pipe',
    '--unit=make-meme-b019-watchdog','-p',f'RuntimeMaxSec={seconds+30}',
    '-p','KillMode=control-group','-p','TimeoutStopSec=30',
    '-p','ExecStopPost=-/usr/bin/systemctl --user stop '+UNIT,'--',
    sys.executable,str(root/'code/runtime_guard.py'),str(root),str(seconds),*sys.argv[3:]]
with (root/'reports/watchdog-launch.json').open('x') as stream:
    json.dump({'command':command,'started':time.time(),'deadline':DEADLINE},stream,indent=2)
raise SystemExit(subprocess.call(command))
