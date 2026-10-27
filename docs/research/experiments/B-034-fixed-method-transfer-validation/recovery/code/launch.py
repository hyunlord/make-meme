"""Durable watchdog; ExecStopPost names only this recovery's VAE unit."""
from pathlib import Path
import json,subprocess,sys,time
from supervisor import DEADLINE,UNIT
root=Path(sys.argv[1]);seconds=min(630,int(DEADLINE-time.time()))
assert seconds>60
command=['systemd-run','--user','--wait','--pipe','--unit=make-meme-b034-recovery01-watchdog','-p',f'RuntimeMaxSec={seconds}','-p','KillMode=control-group','-p','TimeoutStopSec=30','-p','ExecStopPost=-/usr/bin/systemctl --user stop '+UNIT,'--',sys.executable,str(root/'code/supervisor.py'),str(root)]
with (root/'reports/launch-attempt.json').open('x') as out:json.dump({'command':command,'started':time.time(),'deadline':DEADLINE},out,indent=2)
raise SystemExit(subprocess.call(command))
