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
        return {'starttime_ticks':root.joinpath('stat').read_text().rsplit(')',1)[1].split()[19],'cmdline_sha256':hashlib.sha256(root.joinpath('cmdline').read_bytes()).hexdigest(),'proc_exists':True}
    except (FileNotFoundError,ProcessLookupError,PermissionError) as error:
        return {'proc_exists':False,'error':type(error).__name__}


def observe(allowed:dict,owned:set[int],complete:bool)->dict:
    """Observe queue and GPU independently, retaining both even if one fails."""
    row={'started':time.time(),'monotonic_start':time.monotonic(),'errors':[],'owned_pids':sorted(owned),'allowed_pids':sorted(map(int,allowed))}
    queue={'running':[],'pending':[]};gpu=set();row['queue_started_at']=time.time()
    row['queue_started']=time.time();row['queue_monotonic_start']=time.monotonic()
    try:
        raw=json.loads(subprocess.check_output(['curl','-fsS','--max-time','3','http://127.0.0.1:8190/queue'],timeout=5))
        queue={name:[str(item[1]) for item in raw['queue_'+name]] for name in ('running','pending')}
    except (subprocess.SubprocessError,OSError,ValueError,KeyError,IndexError,TypeError) as error:row['errors'].append('queue:'+type(error).__name__)
    row['queue_observed_at']=time.time();row['queue_monotonic_end']=time.monotonic();row['queue']=queue;row['queue_counts']={key:len(value) for key,value in queue.items()}
    row['gpu_started']=time.time();row['gpu_monotonic_start']=time.monotonic();row['gpu_started_at']=time.time()
    try:
        raw=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader,nounits'],timeout=5).decode()
        gpu={int(line.strip()) for line in raw.splitlines() if line.strip().isdigit()}
    except (subprocess.SubprocessError,OSError,ValueError) as error:row['errors'].append('gpu:'+type(error).__name__)
    row['gpu_observed_at']=time.time();row['gpu_monotonic_end']=time.monotonic();row['gpu_pids']=sorted(gpu)
    identities={str(pid):identity(pid) for pid in gpu|set(map(int,allowed))|owned};row['identities']=identities
    matched={int(pid) for pid,expected in allowed.items() if identities[pid].get('proc_exists') and all(identities[pid].get(k)==expected[k] for k in ('starttime_ticks','cmdline_sha256'))}
    if matched!=set(map(int,allowed)):row['errors'].append('allowed_identity_mismatch')
    row['unclassified_pids']=sorted(gpu-matched-owned)
    try:
        memory={line.split(':')[0]:int(line.split()[1])*1024 for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith(('MemAvailable:','SwapTotal:','SwapFree:'))}
        row['available']=memory['MemAvailable'];row['swap']=memory['SwapTotal']-memory['SwapFree']
    except (OSError,ValueError,KeyError) as error:row['errors'].append('memory:'+type(error).__name__);row['available']=0;row['swap']=-1
    row['decision']=decide(row['errors'],len(queue['running']),len(queue['pending']),set(row['unclassified_pids']),complete,row['available']/2**30,row['swap'])
    row['finished']=time.time();row['monotonic_end']=time.monotonic();return row
