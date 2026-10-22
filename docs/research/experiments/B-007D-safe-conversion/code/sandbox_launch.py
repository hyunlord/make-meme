"""Durable supervisor stops only its own daemon-owned container on every exit."""
from pathlib import Path
import datetime as dt
import json
import subprocess
import sys
import time


def main() -> int:
    root=Path(sys.argv[1]).resolve();stage=sys.argv[2]
    assert stage in ('metadata','conversion')
    deadline=dt.datetime.fromisoformat('2026-10-22T14:34:00+00:00').timestamp()
    seconds=min(1230 if stage=='metadata' else 3630,int(deadline-time.time()-30));assert seconds>30
    name='make-meme-b007d-'+stage
    argv=['systemd-run','--user','--wait','--pipe','--unit='+name+'-supervisor','-p',f'RuntimeMaxSec={seconds}','-p','KillMode=control-group','-p','TimeoutStopSec=25','-p','ExecStopPost=-/usr/bin/docker stop --time 10 '+name,'--','/usr/bin/python3',str(root/'code/sandbox_guard.py'),str(root),stage]
    record=root/'reports'/f'{stage}-supervisor.json';assert not record.exists()
    record.write_text(json.dumps({'command':argv,'deadline':deadline,'runtime_seconds':seconds,'started':time.time()},indent=2))
    return subprocess.run(argv,check=False).returncode


if __name__=='__main__':raise SystemExit(main())
