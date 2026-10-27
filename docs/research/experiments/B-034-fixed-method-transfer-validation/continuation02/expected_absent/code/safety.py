"""Recovery-only observations and unchanged fail-closed safety thresholds."""
from pathlib import Path
import hashlib,json,subprocess,time


def decide(errors:list[str],running:int,pending:int,unknown:set[int],complete:bool,available_gib:float,swap:int)->str:
    """Keep worker completion separate from any concurrent guard violation."""
    if errors:return 'OBSERVATION_FAILED'
    if running or pending:return 'QUEUE_BUSY'
    if unknown:return 'UNKNOWN_GPU_PID'
    if available_gib<24 or swap:return 'SYSTEM_HEADROOM_OR_SWAP'
    return 'COMPLETE' if complete else 'CLEAR'


def start_decision(decision:str,available_gib:float,remaining_seconds:float)->str:
    """The existing stronger start threshold remains separate from runtime limits."""
    if decision!='CLEAR':return decision
    if available_gib<72:return 'START_HEADROOM_NOT_MET'
    if remaining_seconds<=60:return 'DEADLINE'
    return 'CLEAR'

def identity(pid:int)->dict:
    """Capture identity without treating a disappeared process as allowed."""
    root=Path('/proc')/str(pid)
    try:
        stat=root.joinpath('stat').read_text().rsplit(')',1)[1].split()
        return {'starttime_ticks':stat[19],'state':stat[0],'cmdline_sha256':hashlib.sha256(root.joinpath('cmdline').read_bytes()).hexdigest(),'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'cgroup':root.joinpath('cgroup').read_text(),'proc_exists':True}
    except (FileNotFoundError,ProcessLookupError,PermissionError) as error:
        return {'proc_exists':False,'error':type(error).__name__}


def observe(allowed:dict,owned:set[int],complete:bool,policy:dict|None=None)->dict:
    """Observe queue and GPU independently, retaining both even if one fails."""
    row={'started':time.time(),'monotonic_start':time.monotonic(),'errors':[],'owned_pids':sorted(owned),'allowed_pids':sorted(map(int,allowed))}
    queue={'running':[],'pending':[]};gpu=set();row['queue_started_at']=time.time()
    row['queue_started']=time.time();row['queue_monotonic_start']=time.monotonic()
    if policy is not None:
        from policy import observe_service
        service=observe_service(policy);row['service_policy']=service
        row['queue']=None;row['queue_counts']=None;row['queue_status']=service['queue_status']
        if service['status']!='EXPECTED_ABSENT_OBSERVED':row['errors'].append('service:'+service['status'])
    else:
        try:
            raw=json.loads(subprocess.check_output(['curl','-fsS','--max-time','3','http://127.0.0.1:8190/queue'],timeout=5))
            queue={name:[str(item[1]) for item in raw['queue_'+name]] for name in ('running','pending')}
            row['queue']=queue;row['queue_counts']={key:len(value) for key,value in queue.items()};row['queue_status']='AVAILABLE'
        except (subprocess.SubprocessError,OSError,ValueError,KeyError,IndexError,TypeError) as error:
            row['errors'].append('queue:'+type(error).__name__);row['queue']=None;row['queue_counts']=None;row['queue_status']='UNAVAILABLE'
    row['queue_observed_at']=time.time();row['queue_monotonic_end']=time.monotonic()
    row['gpu_started']=time.time();row['gpu_monotonic_start']=time.monotonic();row['gpu_started_at']=time.time()
    try:
        raw=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader,nounits'],timeout=5).decode()
        lines=[line.strip() for line in raw.splitlines() if line.strip()]
        if any(not line.isdigit() for line in lines):raise ValueError('MALFORMED_GPU_ROW')
        gpu={int(line) for line in lines}
    except (subprocess.SubprocessError,OSError,ValueError) as error:row['errors'].append('gpu:'+type(error).__name__)
    row['gpu_observed_at']=time.time();row['gpu_monotonic_end']=time.monotonic();row['gpu_pids']=sorted(gpu)
    identities={str(pid):identity(pid) for pid in gpu|(set(map(int,allowed)) if policy is None else set())|owned};row['identities']=identities
    matched={int(pid) for pid,expected in allowed.items() if policy is None and identities[pid].get('proc_exists') and all(identities[pid].get(k)==expected[k] for k in ('starttime_ticks','cmdline_sha256'))}
    if policy is None and matched!=set(map(int,allowed)):row['errors'].append('allowed_identity_mismatch')
    row['historical_allowed_snapshot_applied']=policy is None
    row['unclassified_pids']=sorted(gpu-matched-owned)
    try:
        memory={line.split(':')[0]:int(line.split()[1])*1024 for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith(('MemAvailable:','SwapTotal:','SwapFree:'))}
        row['available']=memory['MemAvailable'];row['swap']=memory['SwapTotal']-memory['SwapFree']
    except (OSError,ValueError,KeyError) as error:row['errors'].append('memory:'+type(error).__name__);row['available']=0;row['swap']=-1
    row['decision']=decide(row['errors'],len(queue['running']),len(queue['pending']),set(row['unclassified_pids']),complete,row['available']/2**30,row['swap'])
    row['finished']=time.time();row['monotonic_end']=time.monotonic();return row


def classify_worker(current:dict, registered:dict, unit:dict)->str:
    """Require live historical binding plus current identity; absence is not permission."""
    if not registered:return 'UNREGISTERED'
    if not current.get('proc_exists'):return 'IDENTITY_UNCERTAIN'
    if any(current.get(k)!=registered.get(k) for k in ('starttime_ticks','boot_id','cgroup')):return 'IDENTITY_MISMATCH'
    if unit.get('InvocationID')!=registered.get('invocation_id') or unit.get('ControlGroup')!=registered.get('unit_cgroup'):return 'IDENTITY_MISMATCH'
    pid=str(registered['pid'])
    if pid not in (unit.get('MainPID'),unit.get('ExecMainPID')):return 'IDENTITY_MISMATCH'
    if current.get('cmdline_sha256')==registered.get('cmdline_sha256') and current.get('state') not in ('Z','X'):
        return 'OWN_LIVE'
    if current.get('state') in ('Z','X') and unit.get('ExecMainCode')=='1' and unit.get('ExecMainStatus')=='0':
        return 'OWN_WORKER_DRAINING'
    return 'IDENTITY_UNCERTAIN'


def lifecycle_decision(row:dict, registered:dict, unit:dict, completed:bool, elapsed:float|None)->str:
    """External hazards override completion and bounded identity observation."""
    if row['errors']:return 'OBSERVATION_FAILED'
    if row['queue_counts'] is None:
        if row.get('service_policy',{}).get('status')!='EXPECTED_ABSENT_OBSERVED':return 'OBSERVATION_FAILED'
    elif any(row['queue_counts'].values()):return 'QUEUE_BUSY'
    if row['available']<24*2**30 or row['swap']:return 'SYSTEM_HEADROOM_OR_SWAP'
    unknown=set(row['unclassified_pids'])
    if unknown-set([registered.get('pid')]):return 'UNKNOWN_GPU_PID'
    state='CLEAR'
    if unknown:
        state=classify_worker(row['identities'][str(registered['pid'])],registered,unit)
        if state=='OWN_LIVE':state='CLEAR'
        elif state in ('OWN_WORKER_DRAINING','IDENTITY_UNCERTAIN'):
            if elapsed is not None and elapsed>=30:return 'DRAIN_TIMEOUT' if state=='OWN_WORKER_DRAINING' else 'IDENTITY_UNCERTAIN_TIMEOUT'
        else:return 'UNKNOWN_GPU_PID'
    if state!='CLEAR':return state
    return 'COMPLETE' if completed else 'CLEAR'


def normal_exit(unit:dict,registered:dict)->bool:
    """An observed idle GPU is not sufficient to declare the unit clean."""
    return bool(registered) and unit.get('ActiveState')=='active' and unit.get('SubState')=='exited' and unit.get('MainPID')=='0' and unit.get('ExecMainCode')=='1' and unit.get('ExecMainStatus')=='0' and unit.get('Result')=='success' and unit.get('InvocationID')==registered['invocation_id'] and unit.get('ExecMainPID')==str(registered['pid'])


def finalized_exit(unit:dict,registered:dict,receipt:dict|None)->bool:
    return bool(receipt) and normal_exit(receipt['unit'],registered) and unit.get('ActiveState')=='inactive' and unit.get('MainPID')=='0' and unit.get('InvocationID','') in ('',registered['invocation_id'])
