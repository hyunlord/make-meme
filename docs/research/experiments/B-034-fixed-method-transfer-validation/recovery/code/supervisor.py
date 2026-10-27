"""Bounded recovery supervisor with separate queue/PID evidence, unchanged policy."""
from pathlib import Path
import datetime,hashlib,json,subprocess,sys,time
from safety import observe,start_decision

UNIT='make-meme-b034-recovery01-vae'
DEADLINE=datetime.datetime.fromisoformat('2026-10-27T05:56:24+00:00').timestamp()

def state()->str:
    return subprocess.check_output(['systemctl','--user','show',UNIT,'-p','MainPID','-p','ActiveState','-p','Result'],timeout=5).decode()

def cgroup()->tuple[set[int],dict]:
    path=subprocess.check_output(['systemctl','--user','show',UNIT,'-p','ControlGroup','--value'],timeout=5).decode().strip()
    folder=Path('/sys/fs/cgroup')/path.lstrip('/');data={}
    if path and folder.exists():
        for name in ('cgroup.procs','memory.current','memory.peak','memory.events','memory.stat'):
            item=folder/name
            if item.exists():data[name]=item.read_text()
        for pid in data.get('cgroup.procs','').split():
            item=Path('/proc')/pid/'status'
            try:data['pid-'+pid]=item.read_text()
            except FileNotFoundError:data['pid-'+pid]='PROC_DISAPPEARED'
    return {int(pid) for pid in data.get('cgroup.procs','').split()},data

def main()->int:
    root=Path(sys.argv[1]);config=json.loads((root/'config.json').read_text());allowed=config['allowed_gpu_processes']
    for name,digest in json.loads((root/'freeze.json').read_text())['files'].items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest
    for name,digest in json.loads((root/'freeze.json').read_text())['external_files'].items():assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==digest
    assert json.loads((root/'reports/artifact.json').read_text())['status']=='VALIDATED'
    with (root/'reports/supervisor-attempt.json').open('x') as out:json.dump({'attempt':1,'started':time.time(),'deadline':DEADLINE,'worker_max_seconds':600,'unit':UNIT},out)
    initial=observe(allowed,set(),False);initial['decision']=start_decision(initial['decision'],initial['available']/2**30,DEADLINE-time.time());(root/'reports/start-safety.json').write_text(json.dumps(initial,indent=2))
    if initial['decision']!='CLEAR':
        (root/'reports/supervisor-result.json').write_text(json.dumps({'state':'NOT_RUN','initial':initial},indent=2));return 2
    seconds=min(600,int(DEADLINE-time.time()-10));cap=min(64*2**30,initial['available']-24*2**30)
    command=['systemd-run','--user','--wait','--pipe','--unit='+UNIT,'-p',f'RuntimeMaxSec={seconds}','-p',f'MemoryMax={cap}','-p',f'MemoryHigh={cap-2*2**30}','-p','MemorySwapMax=0','-p','TasksMax=256','-p','KillMode=control-group','-p','TimeoutStopSec=20','--',sys.executable,str(root/'code/worker.py'),str(root)]
    started=time.time();reason='UNKNOWN'
    with (root/'reports/worker.log').open('w') as log:
        child=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT)
        try:
            while True:
                completed=child.poll() is not None
                try:owned,stats=cgroup()
                except (subprocess.SubprocessError,OSError,ValueError) as error:owned=set();stats={'observation_error':type(error).__name__}
                row=observe(allowed,owned,completed);row['cgroup']=stats;row['worker_launcher_pid']=child.pid;row['worker_returncode']=child.poll();
                try:row['systemd']=state()
                except (subprocess.SubprocessError,OSError) as error:row['systemd_error']=type(error).__name__;row['decision']='OBSERVATION_FAILED'
                if 'observation_error' in stats:row['decision']='OBSERVATION_FAILED'
                with (root/'reports/observations.jsonl').open('a') as out:out.write(json.dumps(row)+'\n')
                reason=row['decision']
                if reason!='CLEAR':break
                if time.time()>=started+seconds or time.time()>=DEADLINE:reason='DEADLINE';break
                time.sleep(1)
        finally:
            cleanup_errors=[]
            if child.poll() is None:
                try:subprocess.run(['systemctl','--user','stop',UNIT],check=False,timeout=30)
                except (subprocess.SubprocessError,OSError) as error:cleanup_errors.append('stop:'+type(error).__name__)
            try:result=child.wait(timeout=40)
            except subprocess.TimeoutExpired:result=124;cleanup_errors.append('wait:TimeoutExpired')
            try:owned,stats=cgroup()
            except (subprocess.SubprocessError,OSError,ValueError) as error:owned=set();stats={'observation_error':type(error).__name__}
            final=observe(allowed,owned,True);final['cgroup']=stats
            try:final['systemd']=state()
            except (subprocess.SubprocessError,OSError) as error:final['systemd_error']=type(error).__name__;final['decision']='OBSERVATION_FAILED'
            if 'observation_error' in stats:final['decision']='OBSERVATION_FAILED'
            report={'guard_reason':reason,'cleanup_errors':cleanup_errors,'worker_returncode':result,'started':started,'finished':time.time(),'final':final,'historical_guard_reason_unchanged':'other_service_work'}
            (root/'reports/supervisor-result.json').write_text(json.dumps(report,indent=2))
    return result
if __name__=='__main__':raise SystemExit(main())
