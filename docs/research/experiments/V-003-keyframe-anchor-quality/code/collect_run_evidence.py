# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""CPU-only receipt collector. CLI: SCENE PRIVATE_RUNTIME NEW_OUTPUT_DIR.

Runtime: root, hw_csv, hardware_timezone (default Asia/Seoul), runs:
[{name, stage?, receipt?, output?}]. Paths may be absolute or root-relative.
Defaults: outputs/NAME/{receipt.json,output.mp4}, stages/v003-NAME-heavy.
Only whitelisted fields leave private evidence. Missing measurements are null;
UNKNOWN does not establish whether a remote worker is alive or stopped.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import re
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

type JSON = dict[str, JSON] | list[JSON] | str | int | float | bool | None


def obj(value: JSON) -> dict[str, JSON]:
    return value if isinstance(value, dict) else {}


def number(value: JSON) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        result = float(value) if isinstance(value, (str, int, float)) else None
    except ValueError:
        return None
    return result if result is not None and math.isfinite(result) else None


def load(path: Path, issues: list[str], role: str) -> dict[str, JSON]:
    try:
        value = json.loads(path.read_text())
        if not isinstance(value, dict):
            raise ValueError('expected object')
        return value
    except (OSError, ValueError):
        issues.append(role + '_UNAVAILABLE_OR_INVALID')
        return {}


def stamp(value: JSON, zone: str = 'UTC') -> float | None:
    if isinstance(value, (int, float)):
        return number(value)
    if not isinstance(value, str):
        return None
    try:
        dt = datetime.fromisoformat(value)
        return dt.replace(tzinfo=ZoneInfo(zone)).timestamp() if dt.tzinfo is None else dt.timestamp()
    except ValueError:
        return None


def extreme(values: list[JSON], minimum: bool = False) -> float | None:
    valid = [n for v in values if (n := number(v)) is not None]
    return (min(valid) if minimum else max(valid)) if valid else None


def status(value: JSON) -> str:
    return value if isinstance(value, str) and re.fullmatch('[A-Z][A-Z0-9_]*', value) else 'UNKNOWN'


def observations(path: Path, issues: list[str]) -> list[dict[str, JSON]]:
    rows = []
    if not path.exists():
        issues.append('OBSERVATIONS_UNAVAILABLE')
        return rows
    for line in path.read_text().splitlines():
        try:
            row = json.loads(line)
            if not isinstance(row, dict):
                raise ValueError('expected object')
            rows.append(row)
        except ValueError:
            issues.append('OBSERVATION_ROW_INVALID_OR_INCOMPLETE')
    return rows


HW_FIELDS = ['timestamp', 'gpu_temperature_c', 'gpu_power_w', 'sm_clock_mhz'] + [
    f'thermal_zone{i}_millidegc' for i in range(7)] + ['mem_available_mib']


def hardware(path: Path, start: float | None, end: float | None,
             zone: str, destination: Path) -> dict[str, JSON]:
    selected: list[list[str]] = []
    invalid = 0
    if start is not None and end is not None and path.exists():
        with path.open() as stream:
            for row in csv.reader(stream):
                when = stamp(row[0], zone) if row else None
                if when is None:
                    invalid += 1
                elif start <= when <= end:
                    if len(row) != len(HW_FIELDS):
                        invalid += 1
                    else:
                        selected.append(row)
    with destination.open('w', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(HW_FIELDS)
        writer.writerows(selected)
    result: dict[str, JSON] = {
        'status': 'OBSERVED_SAMPLES' if selected else 'UNKNOWN',
        'samples': len(selected), 'invalid_rows_in_file': invalid,
        'first_timestamp': selected[0][0] if selected else None,
        'last_timestamp': selected[-1][0] if selected else None,
        'excerpt': destination.name,
        'missing_sensor_values': sum(number(v) is None for row in selected for v in row[1:]),
    }
    for col, field in enumerate(HW_FIELDS[1:], 1):
        result[('min_' if field == 'mem_available_mib' else 'max_') + field] = extreme(
            [row[col] for row in selected], minimum=field == 'mem_available_mib')
    return result


def collect_run(root: Path, spec: dict[str, JSON], hw: Path, zone: str,
                destination: Path) -> dict[str, JSON]:
    name = str(spec['name'])
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', name):
        raise ValueError('invalid public run name')
    def path(key: str, default: str) -> Path:
        return root / str(spec.get(key, default))
    issues: list[str] = []
    receipt = load(path('receipt', f'outputs/{name}/receipt.json'), issues, 'RECEIPT')
    stage = path('stage', f'stages/v003-{name.lower()}-heavy')
    supervisor = load(stage / 'reports/supervisor-result.json', issues, 'SUPERVISOR')
    rows = observations(stage / 'reports/observations.jsonl', issues)
    kernel_path = stage / 'reports/kernel-events.jsonl'
    kernel_rows = observations(kernel_path, issues) if kernel_path.exists() else []
    generated = receipt.get('status') == 'GENERATED'
    exited = supervisor.get('status') == 'COMPLETE' and supervisor.get('normal_exit_recorded') is True
    output_exists = path('output', f'outputs/{name}/output.mp4').is_file()
    start = stamp(supervisor.get('started'))
    end = stamp(supervisor.get('finished'))
    if start is None:
        start = stamp(receipt.get('start_utc'))
    if end is None:
        end = stamp(receipt.get('end_utc'))
    if start is None and rows:
        start = stamp(rows[0].get('started'))
    if end is None and rows:
        end = stamp(rows[-1].get('finished'))
    result: dict[str, JSON] = {
        'name': name, 'status': 'COMPLETE' if generated and exited and output_exists else 'UNKNOWN',
        'receipt_status': status(receipt.get('status')),
        'guard_status': status(supervisor.get('status')),
        'guard_reason': status(supervisor.get('guard_reason')),
        'output_file_present': output_exists,
        'normal_exit_recorded': supervisor.get('normal_exit_recorded') if isinstance(supervisor.get('normal_exit_recorded'), bool) else None,
        'measurement_scope': 'FINAL_RECEIPT_AND_SAMPLED_GUARD' if exited else 'PARTIAL_OR_UNAVAILABLE',
        'start_epoch': start, 'end_epoch': end,
        'guard_elapsed_seconds': end - start if start is not None and end is not None else None,
        'observations': len(rows),
    }
    for key in ('elapsed_seconds', 'first_step_seconds', 'denoiser_calls', 'scheduler_steps_completed',
                'cuda_peak_allocated_bytes', 'cuda_peak_reserved_bytes'):
        result[key] = number(receipt.get(key))
    rss = number(receipt.get('peak_rss_kib'))
    result['peak_rss_bytes_receipt'] = rss * 1024 if rss is not None else None
    result['peak_rss_bytes_sampled'] = extreme([supervisor.get('peak_worker_rss_bytes_observed')] + [r.get('worker_rss_highwater_bytes') for r in rows])
    result['cgroup_peak_bytes_sampled'] = extreme([obj(r.get('cgroup')).get('memory.peak') for r in rows])
    result['cgroup_high_events_sampled'] = extreme([obj(obj(r.get('worker_memory')).get('events')).get('high') for r in rows])
    result['min_mem_available_bytes_sampled'] = extreme([supervisor.get('min_available_bytes_observed')] + [obj(r.get('system_memory')).get('available') for r in rows], minimum=True)
    result['psi_full_avg10_max_sampled'] = extreme([obj(r.get('system_memory')).get('psi_full_avg10') for r in rows])
    result['nvrm_events'] = number(supervisor.get('nvrm_events'))
    result['nvrm_hit_observed'] = (True if any(obj(r.get('kernel_watch')).get('nvrm_hit') is True for r in rows) or any(r.get('nvrm_hit') is True for r in kernel_rows)
                                  else (False if result['nvrm_events'] == 0 and supervisor.get('kernel_watch_status') == 'AVAILABLE' else None))
    result['kernel_watch_status'] = status(supervisor.get('kernel_watch_status'))
    concurrent = supervisor.get('concurrent_external_gpu')
    result['concurrent_external_gpu'] = concurrent if isinstance(concurrent, bool) else (True if any(r.get('concurrent_external_gpu') is True for r in rows) else None)
    result['hardware'] = hardware(hw, start, end, zone, destination / f'{name}-hardware.csv')
    result['evidence_issues'] = list(dict.fromkeys(issues))
    return result


def main() -> None:
    scene_path, runtime_path, out_path = map(Path, sys.argv[1:])
    scene = json.loads(scene_path.read_text())
    runtime = json.loads(runtime_path.read_text())
    out_path.mkdir(parents=True, exist_ok=False)
    rows = [collect_run(Path(runtime['root']), spec, Path(runtime['hw_csv']),
                        runtime.get('hardware_timezone', 'Asia/Seoul'), out_path) for spec in runtime['runs']]
    result = {'scene_sha256': hashlib.sha256(scene_path.read_bytes()).hexdigest(),
              'configured_frames': scene['scene']['segment']['frames'],
              'configured_fps': scene['scene']['segment']['fps'], 'runs': rows,
              'sampling_note': 'Guard/hardware extrema are sampled observations, not proof of continuous coverage.'}
    (out_path / 'RUN_EVIDENCE.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')


if __name__ == '__main__':
    main()
