# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# Run: ABSOLUTE_PYTHON /absolute/run_guarded.py /absolute/stage_root [--preflight-only]
"""Small C-001 adapter for the existing B-034 systemd/memory/lifecycle guard."""
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict
import hashlib
import json
import os
import runpy
import sys
import time


class GuardConfig(TypedDict):
    python: str
    cwd: str
    script: str
    args: list[str]
    environment: dict[str, str]
    checkpoint: str
    input_paths: list[str]
    output_paths: list[str]
    guard_code: str
    stage: str
    unit: str
    deadline_epoch: float
    allowed_gpu_processes: dict
    research_lock: str
    memory_budget_state: str
    worker_max_seconds: int
    cpu_route_receipt: str


@dataclass(frozen=True, slots=True)
class Validated:
    root: Path
    config: GuardConfig
    route_sha256: str
    cpu_only: bool


def absolute(value: str, *, exists: bool = True, directory: bool = False) -> Path:
    path = Path(value)
    if not path.is_absolute():
        raise RuntimeError(f'ABSOLUTE_PATH_REQUIRED:{value}')
    if exists and not path.exists():
        raise RuntimeError(f'PATH_MISSING:{value}')
    if directory and not path.is_dir():
        raise RuntimeError(f'DIRECTORY_REQUIRED:{value}')
    if not exists and not path.parent.is_dir():
        raise RuntimeError(f'OUTPUT_PARENT_MISSING:{value}')
    return path.resolve()


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate(root_value: str) -> Validated:
    """The same absolute-path contract is used before systemd and inside its worker."""
    root = absolute(root_value, directory=True)
    config: GuardConfig = json.loads((root/'config.json').read_text())
    python = absolute(config['python'])
    if python != Path(sys.executable).resolve():
        raise RuntimeError('PYTHON_IDENTITY_MISMATCH')
    absolute(config['cwd'], directory=True)
    script = absolute(config['script'])
    absolute(config['checkpoint'])
    guard = absolute(config['guard_code'], directory=True)
    for name in ('supervisor.py','safety.py','policy.py','memory.py'):
        absolute(str(guard/name))
    for path in config['input_paths']:
        absolute(path)
    for path in config['output_paths']:
        absolute(path, exists=False)
    for name in ('research_lock','memory_budget_state'):
        absolute(config[name], exists=False)
    if not config['unit'].startswith('make-meme-c001-'):
        raise RuntimeError('C001_UNIT_REQUIRED')
    if time.time() >= config['deadline_epoch'] or config['worker_max_seconds'] <= 0:
        raise RuntimeError('DEADLINE')
    if config['allowed_gpu_processes']:
        raise RuntimeError('C001_EXTERNAL_GPU_ALLOWLIST_FORBIDDEN')
    if '--' in config['args'] or any(not isinstance(arg,str) for arg in config['args']):
        raise RuntimeError('INVALID_TARGET_ARGUMENTS')
    freeze = json.loads((root/'freeze.json').read_text())['files']
    for path, expected in freeze.items():
        if sha(absolute(path)) != expected:
            raise RuntimeError(f'FREEZE_MISMATCH:{path}')
    mandatory = {str(root/'config.json'), str(script), str(Path(__file__).resolve())}
    if not mandatory <= set(freeze):
        raise RuntimeError('FREEZE_MISSING_CONFIG_SCRIPT_OR_ADAPTER')
    route = {key:config[key] for key in ('python','cwd','script','environment','checkpoint','input_paths','output_paths','guard_code')}
    route['args'] = [arg for arg in config['args'] if arg != '--cpu-only']
    route['script_sha256'] = sha(script)
    route['adapter_sha256'] = sha(Path(__file__).resolve())
    route_sha = hashlib.sha256(json.dumps(route,sort_keys=True).encode()).hexdigest()
    return Validated(root,config,route_sha,'--cpu-only' in config['args'])


def load_c001_policy(root: Path) -> dict:
    """Keep expected-absence observations; bind only authorization to this C-001 stage."""
    config = json.loads((root/'config.json').read_text())
    policy = json.loads((root/'configs/service-policy.json').read_text())
    if not (policy['mode']=='OPTIONAL_EXPECTED_ABSENT' and policy['authorized'] is True
            and policy['stage_root']==str(root.resolve()) and policy['stage']==config['stage']
            and policy['deadline_epoch']==config['deadline_epoch']>time.time()
            and policy['boot_id']==Path('/proc/sys/kernel/random/boot_id').read_text().strip()
            and policy['attempt_id'].startswith('C001') and policy['process_markers']
            and policy['endpoint']=='http://127.0.0.1:8190/queue'):
        raise RuntimeError('C001_POLICY_BINDING_FAILED')
    for path, expected in policy['logical_files'].items():
        if sha(absolute(path)) != expected:
            raise RuntimeError(f'SERVICE_LOGICAL_FILE_CHANGED:{path}')
    return policy


def worker(job: Validated) -> None:
    """Enter target in the registered Python PID; child GPU processes are never auto-allowed."""
    load_c001_policy(job.root)
    until = time.monotonic()+20
    identity = job.root/'reports/worker-identity.json'
    while not identity.exists():
        if time.monotonic()>until:
            raise RuntimeError('LIVE_IDENTITY_REGISTRATION_TIMEOUT')
        time.sleep(0.1)
    if json.loads(identity.read_text())['pid'] != os.getpid():
        raise RuntimeError('REGISTERED_WORKER_PID_MISMATCH')
    if json.loads((job.root/'reports/start-safety.json').read_text())['decision']!='CLEAR':
        raise RuntimeError('START_GUARD_NOT_CLEAR')
    os.chdir(job.config['cwd'])
    os.environ.update(job.config['environment'])
    sys.argv = [job.config['script'], *job.config['args']]
    runpy.run_path(job.config['script'],run_name='__main__')


def main() -> int:
    job = validate(sys.argv[1])
    sys.path.insert(0,job.config['guard_code'])
    if Path(sys.argv[0]).name=='worker.py':
        worker(job)
        return 0
    policy = load_c001_policy(job.root)
    if '--preflight-only' in sys.argv[2:]:
        from safety import observe
        from memory import MemoryBudget
        row = observe({},set(),False,policy)
        row['memory_verdict'] = MemoryBudget().inspect(row['system_memory'],None,'BEFORE_CREATED',start=True,require_window=False)
        if row['decision']!='CLEAR' or row['memory_verdict']['decision']!='CLEAR' or row['service_policy']['research_worker_pids']:
            raise RuntimeError(f'PREFLIGHT_GUARD_FAILED:{row}')
        print(json.dumps({'status':'PREFLIGHT_PASS','route_sha256':job.route_sha256,'observation':row}))
        return 0
    if not job.cpu_only:
        receipt_path = absolute(job.config['cpu_route_receipt'])
        result = json.loads(receipt_path.read_text())
        route = json.loads((receipt_path.parent/'path-validation.json').read_text())
        if result['status']!='COMPLETE' or not route['cpu_only'] or route['route_sha256']!=job.route_sha256:
            raise RuntimeError('CPU_SYSTEMD_ROUTE_NOT_VERIFIED')
    report = {'route_sha256':job.route_sha256,'cpu_only':job.cpu_only,'started':time.time()}
    (job.root/'reports/path-validation.json').write_text(json.dumps(report,indent=2))
    import supervisor
    supervisor.load_policy = load_c001_policy
    sys.argv = [str(Path(__file__).resolve()), str(job.root)]
    return supervisor.main()


if __name__=='__main__':
    raise SystemExit(main())
