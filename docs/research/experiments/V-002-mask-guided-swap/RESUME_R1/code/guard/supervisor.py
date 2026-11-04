"""Continuation-only bounded worker lifecycle; no historical guard override."""
from pathlib import Path
import hashlib,json,subprocess,sys,time,fcntl
from policy import load_policy
from uma import ALLOCATOR,KernelWatch,drop_caches,peak_decision,cache_requirement_decision
from memory import MemoryBudget,collect_cgroup
from safety import observe,start_decision,identity,lifecycle_decision,normal_exit,finalized_exit


def unit_state(unit:str)->dict:
    names=['MainPID','ExecMainPID','ActiveState','SubState','Result','ExecMainCode','ExecMainStatus','InvocationID','ControlGroup']
    command=['systemctl','--user','show',unit]+[arg for name in names for arg in ('-p',name)]
    return dict(line.split('=',1) for line in subprocess.check_output(command,timeout=5).decode().splitlines() if '=' in line)


def worker_memory_cap(available: int) -> int:
    """E2-only 100 GiB cap with the existing 12 GiB host reserve."""
    return min(100*2**30, available-12*2**30)


def worker_rss_highwater(pid: int, proc: Path = Path('/proc')) -> int | None:
    """Sample the owned process high-water RSS; disappearance is not a zero value."""
    try:
        status = (proc/str(pid)/'status').read_text()
    except (FileNotFoundError, ProcessLookupError):
        return None
    fields = dict(line.split(':', 1) for line in status.splitlines() if ':' in line)
    if 'VmHWM' not in fields and fields.get('State', '').strip().startswith(('Z', 'X')):
        return None
    value, unit = fields['VmHWM'].split() if 'VmHWM' in fields else ('', '')
    if unit != 'kB' or not value.isdigit():
        raise ValueError(f'WORKER_RSS_OBSERVATION_INVALID:{pid}')
    return int(value)*1024


def main()->int:
    root=Path(sys.argv[1]);config=json.loads((root/'config.json').read_text());unit=config['unit'];deadline=config['deadline_epoch'];allowed=config['allowed_gpu_processes']
    policy=load_policy(root)
    budget_path=Path(config['memory_budget_state'])
    budget=MemoryBudget(json.loads(budget_path.read_text()) if budget_path.exists() else None)
    def persist_budget():
        temporary=budget_path.with_suffix('.tmp');temporary.write_text(json.dumps(budget.export(),indent=2));temporary.replace(budget_path)
    lock=open(config['research_lock'],'a+')
    fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
    frozen=json.loads((root/'freeze.json').read_text())['files']
    assert str(Path(__file__).with_name('uma.py').resolve()) in frozen,'UMA_HELPER_NOT_FROZEN'
    for path,digest in frozen.items():assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest,path
    with (root/'reports/supervisor-attempt.json').open('x') as out:json.dump({'started':time.time(),'unit':unit,'deadline':deadline},out)
    units=subprocess.check_output(['systemctl','--user','list-units','--all','--no-legend','--plain','--no-pager'],timeout=5,text=True)
    conflicts=[line for line in units.splitlines() if any(marker in line.lower() for marker in ('v001','v002')) and any(state in line.split() for state in ('active','activating','deactivating'))]
    assert not conflicts, 'DUPLICATE_RESEARCH_UNIT'
    heavy=config['stage'].endswith('-heavy')
    allow_external_gpu=heavy and config.get('continue_generation_on_external_gpu',False)
    assert type(config.get('continue_generation_on_external_gpu',False)) is bool
    assert type(config.get('cache_helper_required',False)) is bool
    assert config['environment'].get('PYTORCH_CUDA_ALLOC_CONF',ALLOCATOR)==ALLOCATOR,'ALLOCATOR_CONTRACT'
    if heavy:
        peak={'estimate_gib':config.get('estimated_peak_gib'),'basis':config.get('estimate_basis','')}
        peak['decision']=peak_decision(peak['estimate_gib'],peak['basis'])
        (root/'reports/peak-estimate.json').write_text(json.dumps(peak,indent=2))
        if peak['decision']!='CLEAR':return 2
        precache=observe(allowed,set(),False,policy)
        (root/'reports/cache-admission.json').write_text(json.dumps(precache,indent=2))
        if precache['decision']!='CLEAR' or precache['service_policy']['research_worker_pids']:return 2
        cache=drop_caches()
        cache['decision']=cache_requirement_decision(cache['status'],required=config.get('cache_helper_required',False))
        (root/'reports/cache-drop.json').write_text(json.dumps(cache,indent=2))
        if cache['decision']!='CLEAR':return 2
    samples=[]
    for index in range(36):
        initial=observe(allowed,set(),False,policy,budget)
        initial['memory_verdict']=budget.inspect(initial['system_memory'],None,'BEFORE_CREATED',start=True)
        if initial['decision']=='CLEAR':initial['decision']=initial['memory_verdict']['decision']
        if initial['available'] is not None and initial['decision']=='CLEAR':initial['decision']=start_decision(initial['decision'],initial['available']/2**30,deadline-time.time())
        persist_budget()
        if initial['service_policy']['research_worker_pids']:initial['decision']='DUPLICATE_RESEARCH_WORKER'
        samples.append(initial)
        (root/'reports/start-samples.json').write_text(json.dumps(samples,indent=2))
        if initial['decision']=='CLEAR' and index>=5:break
        if initial['decision'] not in ('CLEAR','START_OBSERVATION_INCOMPLETE'):return 2
        time.sleep(2)
    if initial['decision']!='CLEAR':return 2
    (root/'reports/start-safety.json').write_text(json.dumps(initial,indent=2))
    cap=worker_memory_cap(initial['available']);seconds=min(config['worker_max_seconds'],int(deadline-time.time()-10))
    command=['systemd-run','--user','--wait','--pipe','--unit='+unit,'-p',f'RuntimeMaxSec={seconds}','-p',f'MemoryMax={cap}','-p',f'MemoryHigh={cap}','-p','MemorySwapMax=0','-p','TasksMax=256','-p','RemainAfterExit=yes','-p','KillMode=control-group','-p','TimeoutStopSec=20','--setenv=PYTORCH_CUDA_ALLOC_CONF='+ALLOCATOR,'--',sys.executable,str(root/'code/worker.py'),str(root)]
    watch=KernelWatch.start() if heavy else None
    if watch is not None:
        (root/'reports/kernel-watch-start.json').write_text(json.dumps({'status':watch.status,'cursor':watch.cursor,'detail':watch.detail,'started':time.time()},indent=2))
        if watch.status=='OBSERVATION_FAILED':return 2
    registered={};exit_receipt=None;uncertain_since=None;started=time.time();reason='UNKNOWN';cleanup=[]
    peak_worker_rss=None;nvrm_count=0;concurrent_external_gpu=False
    min_available=min(row['available'] for row in samples if row['available'] is not None)
    with (root/'reports/worker.log').open('w') as log:
        child=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT)
        try:
            while True:
                completed=child.poll() is not None
                kernel=watch.poll() if watch is not None else None
                if kernel is not None:
                    with (root/'reports/kernel-events.jsonl').open('a') as out:out.write(json.dumps(kernel)+'\n')
                    if kernel['status']=='OBSERVATION_FAILED':
                        reason='OBSERVATION_FAILED'
                        break
                    if kernel['nvrm_hit']:
                        reason='ENGINE_STOPPED_NVRM'
                        nvrm_count+=len(kernel['messages'])
                        break
                row=observe(allowed,set(),completed,policy,budget)
                if row['available'] is not None:min_available=min(min_available,row['available'])
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
                    rss=worker_rss_highwater(registered['pid']) if registered else None
                    if rss is not None:peak_worker_rss=rss if peak_worker_rss is None else max(peak_worker_rss,rss)
                    row['worker_rss_highwater_bytes']=rss
                    row['peak_worker_rss_bytes_observed']=peak_worker_rss
                    row['min_available_bytes_observed']=min_available
                    cg_state='ACTIVE' if cg else ('REMOVED' if registered else 'BEFORE_CREATED')
                    row['worker_memory']=collect_cgroup(folder) if cg else None
                    row['cgroup_state']=cg_state
                    row['memory_verdict']=budget.inspect(row['system_memory'],row['worker_memory'],cg_state,verified_exit=exit_receipt is not None or normal_exit(unit_info,registered))
                    persist_budget()
                    elapsed=None if uncertain_since is None else time.monotonic()-uncertain_since
                    row['external_gpu_pids']=sorted(set(row['unclassified_pids'])-{registered.get('pid')})
                    row['concurrent_external_gpu']=bool(allow_external_gpu and row['external_gpu_pids'])
                    concurrent_external_gpu |= row['concurrent_external_gpu']
                    decision=lifecycle_decision(row,registered,unit_info,completed,elapsed,allow_external_gpu=allow_external_gpu)
                except (OSError,subprocess.SubprocessError,ValueError,KeyError) as error:
                    row['lifecycle_error']=type(error).__name__;decision='OBSERVATION_FAILED'
                log.flush()
                with (root/'reports/worker.log').open('rb') as check:
                    check.seek(max(0,(root/'reports/worker.log').stat().st_size-8192));text=check.read().decode(errors='replace')
                if any(marker in text for marker in ('OutOfMemoryError','out of memory',"can't allocate memory",'std::bad_alloc')):decision='ALLOCATION_OOM'
                if decision in ('CLEAR','COMPLETE') and (not row['unclassified_pids'] or allow_external_gpu and set(row['unclassified_pids'])==set(row.get('external_gpu_pids',[]))) and normal_exit(unit_info,registered):
                    exit_receipt={'observed_at':time.time(),'unit':unit_info,'registered_identity':registered,'safety':row}
                    (root/'reports/normal-exit.json').write_text(json.dumps(exit_receipt,indent=2))
                    subprocess.run(['systemctl','--user','stop',unit],check=True,timeout=30)
                if decision in ('OWN_WORKER_DRAINING','IDENTITY_UNCERTAIN') and uncertain_since is None:uncertain_since=time.monotonic()
                row['kernel_watch']=kernel
                row['decision']=decision;row['uncertainty_elapsed']=None if uncertain_since is None else time.monotonic()-uncertain_since
                with (root/'reports/observations.jsonl').open('a') as out:out.write(json.dumps(row)+'\n')
                reason=decision
                if decision not in ('CLEAR','OWN_WORKER_DRAINING','IDENTITY_UNCERTAIN'):break
                if time.time()>=min(deadline,started+seconds):reason='DEADLINE';break
                time.sleep(1)
        finally:
            if child.poll() is None or reason=='ENGINE_STOPPED_NVRM':
                try:subprocess.run(['systemctl','--user','stop',unit],check=False,timeout=30)
                except (OSError,subprocess.SubprocessError) as error:cleanup.append(type(error).__name__)
            try:result=child.wait(timeout=40)
            except subprocess.TimeoutExpired:result=124;cleanup.append('WAIT_TIMEOUT')
            final=observe(allowed,set(),False,policy,budget)
            if final['available'] is not None:min_available=min(min_available,final['available'])
            final['cgroup_state']='REMOVED';final['worker_memory']=None
            final['memory_verdict']=budget.inspect(final['system_memory'],None,'REMOVED',verified_exit=exit_receipt is not None)
            if allow_external_gpu and final['decision']=='UNKNOWN_GPU_PID':
                final['concurrent_external_gpu']=True;concurrent_external_gpu=True
                final['decision']=final['memory_verdict']['decision']
            if final['decision']=='CLEAR':final['decision']=final['memory_verdict']['decision']
            persist_budget()
            try:final['systemd']=unit_state(unit)
            except (OSError,subprocess.SubprocessError,ValueError) as error:
                final['systemd_error']=type(error).__name__;final['decision']='OBSERVATION_FAILED'
            if final['decision']=='CLEAR' and not finalized_exit(final.get('systemd',{}),registered,exit_receipt):final['decision']='UNIT_EXIT_NOT_VERIFIED'
            report={'concurrent_external_gpu':concurrent_external_gpu,'result_flags':['CONCURRENT_EXTERNAL_GPU'] if concurrent_external_gpu else [],'nvrm_events':nvrm_count,'kernel_watch_status':watch.status if watch is not None else 'NOT_REQUESTED_CPU','allocator':ALLOCATOR,'peak_worker_rss_bytes_observed':peak_worker_rss,'peak_worker_rss_scope':'registered worker process /proc VmHWM; sampled lower bound, not final ru_maxrss','min_available_bytes_observed':min_available,'guard_reason':reason,'worker_returncode':result,'cleanup_errors':cleanup,'normal_exit_recorded':exit_receipt is not None,'started':started,'finished':time.time(),'final':final,'status':'ENGINE_STOPPED_NVRM' if reason=='ENGINE_STOPPED_NVRM' else 'COMPLETE' if reason=='COMPLETE' and result==0 and not cleanup and final['decision']=='CLEAR' else 'NOT_CLEAN'}
            (root/'reports/supervisor-result.json').write_text(json.dumps(report,indent=2))
    return 0 if report['status']=='COMPLETE' else 2
if __name__=='__main__':raise SystemExit(main())
