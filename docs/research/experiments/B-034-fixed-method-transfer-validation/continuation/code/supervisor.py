"""Continuation-only bounded worker lifecycle; no historical guard override."""
from pathlib import Path
import hashlib,json,subprocess,sys,time
from safety import observe,start_decision,identity,lifecycle_decision,normal_exit,finalized_exit


def unit_state(unit:str)->dict:
    names=['MainPID','ExecMainPID','ActiveState','SubState','Result','ExecMainCode','ExecMainStatus','InvocationID','ControlGroup']
    command=['systemctl','--user','show',unit]+[arg for name in names for arg in ('-p',name)]
    return dict(line.split('=',1) for line in subprocess.check_output(command,timeout=5).decode().splitlines() if '=' in line)


def main()->int:
    root=Path(sys.argv[1]);config=json.loads((root/'config.json').read_text());unit=config['unit'];deadline=config['deadline_epoch'];allowed=config['allowed_gpu_processes']
    for path,digest in json.loads((root/'freeze.json').read_text())['files'].items():assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest,path
    with (root/'reports/supervisor-attempt.json').open('x') as out:json.dump({'started':time.time(),'unit':unit,'deadline':deadline},out)
    initial=observe(allowed,set(),False);initial['decision']=start_decision(initial['decision'],initial['available']/2**30,deadline-time.time())
    (root/'reports/start-safety.json').write_text(json.dumps(initial,indent=2))
    if initial['decision']!='CLEAR':return 2
    cap=min(64*2**30,initial['available']-24*2**30);seconds=min(config['worker_max_seconds'],int(deadline-time.time()-10))
    command=['systemd-run','--user','--wait','--pipe','--unit='+unit,'-p',f'RuntimeMaxSec={seconds}','-p',f'MemoryMax={cap}','-p',f'MemoryHigh={cap-2*2**30}','-p','MemorySwapMax=0','-p','TasksMax=256','-p','RemainAfterExit=yes','-p','KillMode=control-group','-p','TimeoutStopSec=20','--',sys.executable,str(root/'code/worker.py'),str(root)]
    registered={};exit_receipt=None;uncertain_since=None;started=time.time();reason='UNKNOWN';cleanup=[]
    with (root/'reports/worker.log').open('w') as log:
        child=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT)
        try:
            while True:
                completed=child.poll() is not None
                row=observe(allowed,set(),completed)
                try:
                    unit_info=unit_state(unit);cg=unit_info['ControlGroup'];folder=Path('/sys/fs/cgroup')/cg.lstrip('/')
                    stats={name:(folder/name).read_text() for name in ('cgroup.procs','memory.current','memory.peak','memory.events','memory.stat') if cg and (folder/name).exists()}
                    pid=int(unit_info['MainPID'])
                    if not registered and pid:
                        ident=identity(pid)
                        if ident.get('proc_exists') and ident.get('state') not in ('Z','X') and ident['cmdline_sha256']!=hashlib.sha256(b'').hexdigest() and pid in {int(x) for x in stats.get('cgroup.procs','').split()} and ('0::'+cg) in ident['cgroup'].splitlines() and unit_info['InvocationID']:
                            registered={**ident,'pid':pid,'unit':unit,'invocation_id':unit_info['InvocationID'],'unit_cgroup':cg,'registered_at':time.time()}
                            temporary=root/'reports/worker-identity.json.tmp';temporary.write_text(json.dumps(registered,indent=2));temporary.replace(root/'reports/worker-identity.json')
                    row['systemd']=unit_info;row['cgroup']=stats;row['registered_identity']=registered
                    elapsed=None if uncertain_since is None else time.monotonic()-uncertain_since
                    decision=lifecycle_decision(row,registered,unit_info,completed,elapsed)
                except (OSError,subprocess.SubprocessError,ValueError,KeyError) as error:
                    row['lifecycle_error']=type(error).__name__;decision='OBSERVATION_FAILED'
                if decision=='CLEAR' and not row['unclassified_pids'] and normal_exit(unit_info,registered):
                    exit_receipt={'observed_at':time.time(),'unit':unit_info,'registered_identity':registered,'safety':row}
                    (root/'reports/normal-exit.json').write_text(json.dumps(exit_receipt,indent=2))
                    subprocess.run(['systemctl','--user','stop',unit],check=True,timeout=30)
                if decision in ('OWN_WORKER_DRAINING','IDENTITY_UNCERTAIN') and uncertain_since is None:uncertain_since=time.monotonic()
                row['decision']=decision;row['uncertainty_elapsed']=None if uncertain_since is None else time.monotonic()-uncertain_since
                with (root/'reports/observations.jsonl').open('a') as out:out.write(json.dumps(row)+'\n')
                reason=decision
                if decision not in ('CLEAR','OWN_WORKER_DRAINING','IDENTITY_UNCERTAIN'):break
                if time.time()>=min(deadline,started+seconds):reason='DEADLINE';break
                time.sleep(1)
        finally:
            if child.poll() is None:
                try:subprocess.run(['systemctl','--user','stop',unit],check=False,timeout=30)
                except (OSError,subprocess.SubprocessError) as error:cleanup.append(type(error).__name__)
            try:result=child.wait(timeout=40)
            except subprocess.TimeoutExpired:result=124;cleanup.append('WAIT_TIMEOUT')
            final=observe(allowed,set(),False);final['decision']=start_decision(final['decision'],final['available']/2**30,deadline-time.time())
            try:final['systemd']=unit_state(unit)
            except (OSError,subprocess.SubprocessError,ValueError) as error:
                final['systemd_error']=type(error).__name__;final['decision']='OBSERVATION_FAILED'
            if final['decision']=='CLEAR' and not finalized_exit(final.get('systemd',{}),registered,exit_receipt):final['decision']='UNIT_EXIT_NOT_VERIFIED'
            report={'guard_reason':reason,'worker_returncode':result,'cleanup_errors':cleanup,'normal_exit_recorded':exit_receipt is not None,'started':started,'finished':time.time(),'final':final,'status':'COMPLETE' if reason=='COMPLETE' and result==0 and not cleanup and final['decision']=='CLEAR' else 'NOT_CLEAN'}
            (root/'reports/supervisor-result.json').write_text(json.dumps(report,indent=2))
    return 0 if report['status']=='COMPLETE' else 2
if __name__=='__main__':raise SystemExit(main())
