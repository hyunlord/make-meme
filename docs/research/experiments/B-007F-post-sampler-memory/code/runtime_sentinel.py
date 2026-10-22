# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Bounded no-model proof: durable outer timeout stops only its owned child unit."""
# Run: python runtime_sentinel.py REPORT_JSON
from pathlib import Path
import json
import subprocess
import sys
import time

inner = 'make-meme-b007f-sentinel-child'
outer = 'make-meme-b007f-sentinel-watchdog'
command = ['systemd-run','--user','--wait','--pipe','--unit='+outer,
    '-p','RuntimeMaxSec=3','-p','TimeoutStopSec=5','-p','KillMode=control-group',
    '-p','ExecStopPost=-/usr/bin/systemctl --user stop '+inner,'--',
    '/usr/bin/systemd-run','--user','--wait','--pipe','--unit='+inner,
    '-p','MemoryMax=68719476736','-p','MemoryHigh=66571993088',
    '-p','MemorySwapMax=0','-p','TasksMax=256','-p','KillMode=control-group',
    '-p','RuntimeMaxSec=60','--','/usr/bin/sleep','60']
started = time.time()
child = subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
time.sleep(1)
properties = subprocess.check_output(['systemctl','--user','show',inner,'-p','MemoryMax','-p','MemoryHigh','-p','MemorySwapMax','-p','RuntimeMaxUSec','-p','KillMode','-p','MainPID'],text=True,timeout=5)
stdout,_ = child.communicate(timeout=20)
final = subprocess.check_output(['systemctl','--user','show',inner,'-p','MainPID','-p','ActiveState','-p','Result'],text=True,timeout=5)
assert 'MainPID=0' in final and 'MemoryMax=68719476736' in properties and 'MemorySwapMax=0' in properties
report = {'status':'PASS','elapsed_seconds':time.time()-started,'command':command,'returncode':child.returncode,'properties':properties,'final':final,'log':stdout,'scope':'No checkpoint, no GPU operation; outer timeout stopped its owned child.'}
Path(sys.argv[1]).write_text(json.dumps(report,indent=2))
