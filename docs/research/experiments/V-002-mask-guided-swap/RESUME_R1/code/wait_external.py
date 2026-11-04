# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# How to run: python wait_external.py --stage ID --ledger /private/wait.json --public-log /public/WAIT_LOG.json
"""Observe external GPU work before a separately invoked heavy stage; never launch work."""
from __future__ import annotations

import argparse
import fcntl
import json
import os
from pathlib import Path
import subprocess
import time
from typing import Final

INTERVAL: Final = 60.0
STAGE_LIMIT: Final = 7200.0
TOTAL_LIMIT: Final = 10800.0


def known_batch_parents(process_listing: str) -> list[int]:
    """Match executable/first script arguments, excluding shell command strings."""
    found: list[int] = []
    for line in process_listing.splitlines():
        fields = line.split()
        if len(fields) < 3 or not fields[0].isdigit():
            continue
        pid = int(fields[0])
        if pid == os.getpid():
            continue
        executable = Path(fields[2]).name
        arguments = fields[3:]
        if executable == 'r25_grid':
            found.append(pid)
        elif executable.startswith('python'):
            script = next((arg for arg in arguments if not arg.startswith('-')), '')
            if Path(script).name == 'blocked_isolated.py':
                found.append(pid)
    return sorted(set(found))


def observation() -> tuple[list[int], list[int]]:
    """Only read GPU compute PIDs and process arguments; CPU services are excluded."""
    gpu = subprocess.run(['nvidia-smi', '--query-compute-apps=pid', '--format=csv,noheader,nounits'],
                         capture_output=True, text=True, timeout=10, check=True)
    lines = [line.strip() for line in gpu.stdout.splitlines() if line.strip()]
    if any(not line.isdigit() for line in lines):
        raise RuntimeError('Malformed GPU PID output')
    processes = subprocess.run(['ps', '-eo', 'pid=,ppid=,args='], capture_output=True,
                               text=True, timeout=10, check=True)
    return sorted(set(map(int, lines))), known_batch_parents(processes.stdout)


def decision(elapsed: float, total: float, samples: list[dict]) -> str:
    """Budgets take precedence over readiness; three spaced empty samples are required."""
    if elapsed >= STAGE_LIMIT or total >= TOTAL_LIMIT:
        return 'BLOCKED_EXTERNAL_GPU'
    last = samples[-3:]
    if elapsed >= 180 and len(last) == 3 and all(row['empty'] for row in last):
        if last[-1]['elapsed_seconds'] - last[0]['elapsed_seconds'] >= 2 * INTERVAL:
            return 'READY'
    return 'WAITING'


def atomic_json(path: Path, value: dict) -> None:
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    temporary.replace(path)


def public_summary(ledger: dict) -> dict:
    return {'policy': 'V002_R1', 'total_wait_seconds': ledger['total_wait_seconds'],
            'stage_limit_seconds': STAGE_LIMIT, 'total_limit_seconds': TOTAL_LIMIT,
            'stages': {name: {key: value for key, value in stage.items() if key != 'samples'} |
                       {'samples': [{key: value for key, value in row.items()
                                     if key not in ('gpu_pids', 'batch_parent_pids')}
                                    for row in stage['samples']]}
                       for name, stage in ledger['stages'].items()}}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', required=True)
    parser.add_argument('--ledger', type=Path, required=True)
    parser.add_argument('--public-log', type=Path, required=True)
    args = parser.parse_args()
    args.ledger.parent.mkdir(parents=True, exist_ok=True)
    args.public_log.parent.mkdir(parents=True, exist_ok=True)
    with args.ledger.with_suffix('.lock').open('a+') as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        ledger = json.loads(args.ledger.read_text()) if args.ledger.exists() else {'total_wait_seconds': 0.0, 'stages': {}}
        stages = ledger['stages']
        for name, previous in stages.items():
            if name != args.stage and previous['status'] == 'WAITING':
                raise RuntimeError('Another wait stage is unfinished')
        now = time.time()
        if args.stage in stages:
            stage = stages[args.stage]
            if stage['status'] != 'WAITING':
                raise RuntimeError('Finished wait receipts cannot be reused; choose a new admission ID')
        else:
            stage = {'started_at_epoch': now, 'accounted_until_epoch': now, 'elapsed_seconds': 0.0,
                     'status': 'WAITING', 'samples': []}
            stages[args.stage] = stage

        def persist() -> None:
            atomic_json(args.ledger, ledger)
            atomic_json(args.public_log, public_summary(ledger))

        persist()
        while True:
            now = time.time()
            delta = now - stage['accounted_until_epoch']
            if delta < 0:
                stage['status'] = 'OBSERVATION_ERROR_CLOCK_ROLLBACK'
                persist()
                return 3
            ledger['total_wait_seconds'] += delta
            stage['elapsed_seconds'] += delta
            stage['accounted_until_epoch'] = now
            status = decision(stage['elapsed_seconds'], ledger['total_wait_seconds'], [])
            if status == 'BLOCKED_EXTERNAL_GPU':
                stage['status'] = status
                persist()
                return 2
            try:
                gpu, parents = observation()
            except (OSError, subprocess.SubprocessError, RuntimeError) as error:
                stage['status'] = 'OBSERVATION_ERROR'
                stage['error_type'] = type(error).__name__
                persist()
                return 3
            sampled = time.time()
            delta = sampled - stage['accounted_until_epoch']
            if delta < 0:
                stage['status'] = 'OBSERVATION_ERROR_CLOCK_ROLLBACK'
                persist()
                return 3
            ledger['total_wait_seconds'] += delta
            stage['elapsed_seconds'] += delta
            stage['accounted_until_epoch'] = sampled
            row = {'observed_at_epoch': sampled, 'elapsed_seconds': stage['elapsed_seconds'],
                   'gpu_pids': gpu, 'batch_parent_pids': parents, 'gpu_count': len(gpu),
                   'batch_parent_count': len(parents), 'empty': not gpu and not parents}
            stage['samples'].append(row)
            stage['status'] = decision(stage['elapsed_seconds'], ledger['total_wait_seconds'], stage['samples'])
            persist()
            print(json.dumps({'stage': args.stage, 'status': stage['status'],
                              'elapsed_seconds': stage['elapsed_seconds'], 'gpu_count': len(gpu),
                              'batch_parent_count': len(parents)}), flush=True)
            if stage['status'] != 'WAITING':
                return 0 if stage['status'] == 'READY' else 2
            time.sleep(min(INTERVAL, STAGE_LIMIT - stage['elapsed_seconds'],
                           TOTAL_LIMIT - ledger['total_wait_seconds']))


if __name__ == '__main__':
    raise SystemExit(main())
