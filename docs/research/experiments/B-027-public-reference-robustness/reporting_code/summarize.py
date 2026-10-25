# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""CPU evidence summary; reads local reports, never imports a model or launches work."""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Final, TypeAlias

JSON: TypeAlias = str | int | float | bool | None | list['JSON'] | dict[str, 'JSON']
Record: TypeAlias = dict[str, JSON]
STAGES: Final = ('ENC', 'R1_PROBE', 'R1_S', 'R1_D', 'R2_PROBE', 'R2_S', 'R2_D')
TASKS: Final = ('animal', 'human', 'vehicle')


def parse_memory(value: str) -> int:
    """Linux proc kB means 1024 bytes; cgroup values already use bytes."""
    parts = value.split(':')[-1].split()
    factors = {'B': 1, 'kB': 1024, 'KiB': 1024, 'MiB': 1024**2, 'GiB': 1024**3}
    return int(parts[0]) * factors[parts[1] if len(parts) > 1 else 'B']


def read_json(path: Path) -> Record:
    """An absent or concurrently incomplete receipt is not completion evidence."""
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, dict):
        raise ValueError('Receipt root must be an object')
    return data


def rows(path: Path) -> tuple[list[Record], int]:
    """Keep valid observations and explicitly count incomplete live-log rows."""
    valid: list[Record] = []
    invalid = 0
    if path.is_file():
        with path.open() as stream:
            for line in stream:
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    invalid += 1
                    continue
                if isinstance(data, dict):
                    valid.append(data)
                else:
                    invalid += 1
    return valid, invalid


def digest(path: Path) -> str:
    """Stream file bytes without loading tensor payloads into memory."""
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()


def numeric_table(raw: str) -> dict[str, int]:
    return {line.split()[0]: int(line.split()[1]) for line in raw.splitlines() if len(line.split()) == 2}


def summarize_memory(observations: list[Record]) -> tuple[Record, Record]:
    """Each account stays separate; no sum of CUDA/RSS/cgroup/system memory."""
    peaks: Record = {}
    events: Record = {}
    def remember(key: str, value: int, minimum: bool = False) -> None:
        old = peaks.get(key)
        peaks[key] = value if not isinstance(old, (int, float)) else (min(old, value) if minimum else max(old, value))
    for row in observations:
        available = row.get('mem_available', row.get('available'))
        if isinstance(available, str):
            remember('mem_available_min', parse_memory(available), True)
        elif isinstance(available, int):
            remember('mem_available_min', available, True)
        swap = row.get('swap_used', row.get('swap'))
        if isinstance(swap, int):
            remember('swap_used_peak', swap)
        for key in ('cuda_allocated', 'cuda_reserved', 'cuda_peak_allocated'):
            value = row.get(key)
            if isinstance(value, int):
                remember(key + '_peak', value)
        group = row.get('cgroup', {})
        if not isinstance(group, dict):
            raise ValueError('cgroup must be an object')
        process = row.get('process_memory', [])
        status_lines = [line for line in process if isinstance(line, str)] if isinstance(process, list) else []
        for key, value in group.items():
            if key.startswith('pid-') and isinstance(value, str):
                status_lines.extend(value.splitlines())
        for line in status_lines:
            label = line.split(':')[0]
            if label in ('VmRSS', 'RssAnon', 'RssFile', 'VmHWM'):
                name = {'VmRSS':'rss_peak', 'RssAnon':'rss_anon_peak', 'RssFile':'rss_file_peak', 'VmHWM':'rss_hwm_peak'}[label]
                remember(name, parse_memory(line))
        for field in ('memory.current', 'memory.peak'):
            value = group.get(field)
            if isinstance(value, str):
                remember('cgroup_' + field.split('.')[1] + '_peak', int(value))
        stats = group.get('memory.stat')
        if isinstance(stats, str):
            for key, value in numeric_table(stats).items():
                if key in ('anon', 'file'):
                    remember('cgroup_' + key + '_peak', value)
        raw_events = group.get('memory.events')
        if isinstance(raw_events, str):
            for key, value in numeric_table(raw_events).items():
                previous = events.get(key, 0)
                if isinstance(previous, int):
                    events[key] = max(previous, value)
    return peaks, events


def summarize_stage(stage: Path) -> Record:
    reports = stage/'reports'
    process = read_json(reports/'pipeline-process.json')
    attempt = read_json(reports/'attempt.json')
    result = read_json(reports/'result.json')
    phases, partial = rows(reports/'phases.jsonl')
    resources, partial_resource = rows(reports/'resource_metrics.jsonl')
    status: JSON = result.get('status')
    if status is None:
        status = 'RUNNING' if attempt else ('PRE_WORKER_LAUNCH_ONLY' if (reports/'watchdog-launch.json').exists() else 'NOT_RUN')
        if process.get('finished') is not None:
            status = 'INCOMPLETE_EXIT' if attempt else 'PRE_WORKER_FAILED'
    started, finished = process.get('started'), process.get('finished')
    duration = finished - started if isinstance(started, (int, float)) and isinstance(finished, (int, float)) else None
    memory, events = summarize_memory(phases + resources)
    hashes: Record = {}
    launch_errors = list(reports.glob('launch-failure-*.json'))
    for archived in reports.glob('pre-worker-failure-*/classification.json'):
        classification = read_json(archived)
        if classification.get('actual_probe_attempts') == 0 and classification.get('sampler_attempts') == 0:
            launch_errors.append(archived)
    for evidence in launch_errors:
        hashes['reports/' + evidence.relative_to(reports).as_posix()] = digest(evidence)
    for name in ('attempt.json', 'result.json', 'phases.jsonl', 'progress.json', 'video.json', 'first-forward-inputs.json', 'replacement-mode.json', 'resource_metrics.jsonl'):
        path = reports/name
        if path.is_file():
            hashes['reports/' + name] = digest(path)
    for name in ('final_latent.safetensors', 'final_latent.json', 'output.mp4', 'raw_output.pt'):
        path = stage/'artifacts'/name
        if path.is_file():
            hashes['artifacts/' + name] = digest(path)
    timeline: list[JSON] = [{key: row[key] for key in ('phase', 'epoch', 'elapsed_seconds') if key in row} for row in phases]
    return {'status': status, 'worker_attempts': 1 if attempt else 0,
            'sampler_attempts': 1 if (reports/'sampler-attempt.json').is_file() else 0,
            'pre_worker_errors': len(launch_errors),
            'pre_worker_launch_present': (reports/'watchdog-launch.json').exists() and not bool(attempt),
            'started_epoch': started, 'finished_epoch': finished, 'completed_duration_seconds': duration,
            'guard_reason': process.get('reason'), 'service_returncode': process.get('returncode'),
            'counters': read_json(reports/'progress.json'), 'phase_timeline': timeline,
            'memory_bytes': memory, 'cgroup_events_observed_max': events,
            'incomplete_log_rows': partial + partial_resource, 'file_sha256': hashes}


def summarize(root: Path) -> Record:
    tasks: Record = {}
    for task in TASKS:
        task_root = root/'tasks'/task
        stages: Record = {stage: summarize_stage(task_root/'stages'/stage) for stage in STAGES}
        pair_path = task_root/'reports/pair-conditions.json'
        pair = read_json(pair_path)
        safe_pair = {key: value for key, value in pair.items() if key in ('status', 'changed_pair_leaves', 'identical_pair_leaves', 'structure_devices_unchanged', 'counts', 'case_hashes')}
        tasks[task] = {'stages': stages, 'pair_contract': safe_pair, 'pair_sha256': digest(pair_path) if pair_path.is_file() else None}
    return {'experiment': 'B-027', 'snapshot_epoch': time.time(), 'tasks': tasks,
            'memory_rule': 'Distinct observed accounts; never sum. Missing metrics are unknown, not zero. RSS peak is max observed individual process, not a process sum.',
            'status_rule': 'RUNNING means worker attempt without terminal receipt; not an independent liveness assertion.',
            'temporal_quality': 'UNVERIFIED'}


def main() -> None:
    root = Path(sys.argv[1]).resolve()
    destination = root/'reports/execution_summary.json'
    destination.parent.mkdir(exist_ok=True)
    temporary = destination.with_suffix('.tmp')
    temporary.write_text(json.dumps(summarize(root), indent=2)+'\n')
    os.replace(temporary, destination)
    print('reports/execution_summary.json written; runtime inputs unchanged')


if __name__ == '__main__':
    main()
