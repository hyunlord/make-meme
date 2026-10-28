"""Per-attempt expected absence; never a statement of historical normal stop."""
from pathlib import Path
import errno,hashlib,http.client,json,os,subprocess,time,shlex


def absence_decision(authorized:bool,processes:list[int],listeners:list[str],errors:list[str],queue_errno:int|None)->str:
    """Only exact refused TCP plus complete absence can use this exception."""
    if not authorized:return 'POLICY_NOT_AUTHORIZED'
    if errors:return 'OBSERVATION_FAILED'
    if processes or listeners:return 'SERVICE_APPEARED'
    if queue_errno!=errno.ECONNREFUSED:return 'QUEUE_STATE_CONFLICT'
    return 'EXPECTED_ABSENT_OBSERVED'


def load_policy(root:Path)->dict:
    """Bind explicit authorization to this stage, boot and bounded attempt."""
    cfg=json.loads((root/'config.json').read_text())
    policy=json.loads((root/'configs/service-policy.json').read_text())
    assert policy['mode']=='OPTIONAL_EXPECTED_ABSENT' and policy['authorized'] is True
    assert policy['stage_root']==str(root.resolve()) and policy['stage']==cfg['stage']
    assert policy['boot_id']==Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    assert time.time()<policy['deadline_epoch']==cfg['deadline_epoch']
    assert policy['attempt_id']=='B034_CONT02_EXPECTED_ABSENT_01'
    assert policy['process_markers'] and policy['service_cwd'].endswith('/make-meme/ComfyUI')
    assert policy['endpoint']=='http://127.0.0.1:8190/queue'
    for path,digest in policy['logical_files'].items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest
    return policy


def observe_service(policy:dict)->dict:
    """Read bounded process/listener and actual TCP state without GPU initialization."""
    errors=[];processes=[];listeners=[];duplicates=[];queue_errno=None;queue_error=None;queue_status='UNAVAILABLE'
    if 'boot_id' in policy:
        try:
            if Path('/proc/sys/kernel/random/boot_id').read_text().strip()!=policy['boot_id']:errors.append('boot:CHANGED')
        except OSError as error:errors.append('boot:'+type(error).__name__)
    try:
        raw=subprocess.check_output(['ps','-eo','pid=,ppid=,args='],timeout=5,text=True)
        parsed={}
        for line in raw.splitlines():
            parts=line.strip().split(None,2)
            if len(parts)!=3:raise ValueError('MALFORMED_PROCESS_ROW')
            parsed[int(parts[0])]=(int(parts[1]),parts[2])
        if 'research_root' in policy:
            for pid,(_,cmd) in parsed.items():
                if policy['research_root'] not in cmd or 'worker.py' not in cmd:continue
                args=shlex.split(cmd)
                if pid!=os.getpid() and any(arg.endswith('/worker.py') for arg in args) and any(arg.startswith(policy['research_root']+'/') for arg in args):duplicates.append(pid)
        matches={pid for pid,(_,cmd) in parsed.items() if any(marker in cmd for marker in policy['process_markers'])}
        for pid,(_,cmd) in parsed.items():
            if 'main.py' not in cmd:continue
            try:
                if str(Path('/proc',str(pid),'cwd').resolve(strict=True))==policy['service_cwd']:matches.add(pid)
            except FileNotFoundError:
                if Path('/proc',str(pid)).exists():errors.append('process:cwd_missing')
            except PermissionError:errors.append('process:cwd_permission')

        while True:
            expanded=matches|{pid for pid,(ppid,_) in parsed.items() if ppid in matches}
            if expanded==matches:break
            matches=expanded
        processes=sorted(matches)
    except (OSError,subprocess.SubprocessError,ValueError) as error:errors.append('process:'+type(error).__name__)
    try:
        listeners=subprocess.check_output(['ss','-H','-ltnp','sport = :8190'],timeout=5,text=True).splitlines()
    except (OSError,subprocess.SubprocessError) as error:errors.append('listener:'+type(error).__name__)
    connection=http.client.HTTPConnection('127.0.0.1',8190,timeout=3)
    try:
        connection.request('GET','/queue');response=connection.getresponse();response.read()
        queue_error='UNEXPECTED_ENDPOINT_AVAILABLE:'+str(response.status);queue_status='AVAILABLE_UNEXPECTED'
    except ConnectionRefusedError as error:queue_errno=error.errno;queue_error=type(error).__name__
    except (OSError,http.client.HTTPException) as error:queue_error=type(error).__name__;queue_errno=getattr(error,'errno',None)
    finally:connection.close()
    status=absence_decision(policy.get('authorized') is True,processes,listeners,errors,queue_errno)
    return {'status':status,'research_worker_pids':duplicates,'related_pids':processes,'listener_lines':listeners,'errors':errors,'queue_status':queue_status,'queue_counts':None,'queue_errno':queue_errno,'queue_error':queue_error,'observed_at':time.time()}
