# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# How to run: imported by the frozen B-034 supervisor; CPU checks: python -m unittest test_memory
"""Attempt-local operating budgets; these are not Linux/vendor safety guarantees."""
from pathlib import Path
from typing import Final, Literal, TypedDict, assert_never
import os
import time

MIB: Final = 2**20
GIB: Final = 2**30
WINDOW: Final = 10.0
CgroupState = Literal['BEFORE_CREATED', 'ACTIVE', 'REMOVED']


class SystemSample(TypedDict, total=False):
    monotonic: float
    page_size: int
    available: int
    swap_total: int
    swap_free: int
    swap: int
    pswpin: int
    pswpout: int
    psi_full_total: int
    errors: list[str]


class CgroupSample(TypedDict, total=False):
    path: str
    current: int
    high: int | str
    max: int | str
    events: dict[str, int]
    swap_current: int
    swap_max: int | str
    swap_events: dict[str, int]
    pressure: str | None
    errors: list[str]


class BudgetState(TypedDict):
    baseline: SystemSample | None
    history: list[SystemSample]
    cgroup_events: dict[str, dict[str, int]]


class Verdict(TypedDict):
    decision: str
    warnings: list[str]
    errors: list[str]
    metrics: dict[str, int | float | None]


def _pairs(text: str) -> dict[str, int]:
    return {parts[0].rstrip(':'): int(parts[1]) for line in text.splitlines() if (parts := line.split())}


def _full_total(text: str) -> int:
    full = next(line for line in text.splitlines() if line.startswith('full '))
    return int(dict(part.split('=', 1) for part in full.split()[1:])['total'])


def collect_system(proc: Path = Path('/proc')) -> SystemSample:
    """Read mandatory counters, retaining concrete file errors without invented values."""
    row: SystemSample = {'monotonic': time.monotonic(), 'errors': []}
    try:
        row['page_size'] = os.sysconf('SC_PAGE_SIZE')
        if row['page_size'] <= 0:
            row['errors'].append('sysconf:SC_PAGE_SIZE:nonpositive')
    except (OSError, ValueError) as error:
        row['errors'].append(f'sysconf:SC_PAGE_SIZE:{type(error).__name__}:{error}')
    for name in ('meminfo', 'vmstat', 'pressure/memory'):
        path = proc / name
        try:
            text = path.read_text()
            match name:
                case 'meminfo':
                    values = _pairs(text)
                    row.update(available=values['MemAvailable']*1024, swap_total=values['SwapTotal']*1024,
                               swap_free=values['SwapFree']*1024)
                    row['swap'] = row['swap_total'] - row['swap_free']
                case 'vmstat':
                    values = _pairs(text)
                    row.update(pswpin=values['pswpin'], pswpout=values['pswpout'])
                case 'pressure/memory':
                    row['psi_full_total'] = _full_total(text)
                case unreachable:
                    assert_never(unreachable)
        except (OSError, ValueError, KeyError, IndexError, StopIteration) as error:
            row['errors'].append(f'{path}:{type(error).__name__}:{error}')
    return row


def collect_cgroup(folder: Path) -> CgroupSample:
    """Required cgroup controls fail closed; missing optional pressure remains null."""
    row: CgroupSample = {'path': str(folder), 'errors': [], 'pressure': None}
    fields = {'memory.current':'current', 'memory.high':'high', 'memory.max':'max',
              'memory.events':'events', 'memory.swap.current':'swap_current',
              'memory.swap.max':'swap_max', 'memory.swap.events':'swap_events'}
    for name, key in fields.items():
        path = folder / name
        try:
            text = path.read_text().strip()
            row[key] = _pairs(text) if key in ('events', 'swap_events') else ('max' if text == 'max' else int(text))
            if key == 'events' and not {'oom', 'oom_kill'} <= row['events'].keys():
                row['errors'].append(f'{path}:missing oom/oom_kill')
            if key == 'swap_events' and not row['swap_events']:
                row['errors'].append(f'{path}:empty required event counters')
        except (OSError, ValueError, KeyError, IndexError) as error:
            row['errors'].append(f'{path}:{type(error).__name__}:{error}')
    try:
        row['pressure'] = (folder/'memory.pressure').read_text()
    except FileNotFoundError:
        row['pressure'] = None
    except OSError as error:
        row['errors'].append(f'{folder}/memory.pressure:{type(error).__name__}:{error}')
    return row


class MemoryBudget:
    """Mutable attempt ledger; export is persisted unchanged between STEP and decode."""
    def __init__(self, snapshot: BudgetState | None = None) -> None:
        self.state: BudgetState = snapshot if snapshot is not None else {'baseline': None, 'history': [], 'cgroup_events': {}}

    def export(self) -> BudgetState:
        return self.state

    def inspect(self, system: SystemSample, cgroup: CgroupSample | None, state: CgroupState,
                *, start: bool = False, verified_exit: bool = False, require_window: bool = True) -> Verdict:
        """One verdict for preflight, startup, runtime, stage boundaries and final checks."""
        verdict: Verdict = {'decision': 'CLEAR', 'warnings': [], 'errors': list(system.get('errors', [])), 'metrics': {}}
        required = ('monotonic','page_size','available','swap_total','swap_free','swap','pswpin','pswpout','psi_full_total')
        verdict['errors'].extend(f'system:missing:{key}' for key in required if system.get(key) is None)
        match state:
            case 'ACTIVE':
                if cgroup is None:
                    verdict['errors'].append('cgroup:ACTIVE:missing')
                else:
                    verdict['errors'].extend(cgroup.get('errors', []))
                    verdict['errors'].extend(f'cgroup:missing:{key}' for key in ('path','current','high','max','events','swap_current','swap_max','swap_events') if key not in cgroup)
                    if not {'oom','oom_kill'} <= cgroup.get('events', {}).keys():
                        verdict['errors'].append('cgroup:events:missing oom/oom_kill')
            case 'REMOVED':
                if not verified_exit:
                    verdict['errors'].append('cgroup:REMOVED:exit_not_verified')
            case 'BEFORE_CREATED':
                if cgroup is not None:
                    verdict['errors'].append('cgroup:BEFORE_CREATED:unexpected_sample')
            case unreachable:
                assert_never(unreachable)
        if verdict['errors']:
            verdict['decision'] = 'OBSERVATION_FAILED'
            return verdict
        if (any(system[key] < 0 for key in required) or system['page_size'] == 0
                or system['swap_free'] > system['swap_total']):
            verdict['errors'].append('system:invalid_negative_counter_page_size_or_swap_range')
        baseline = self.state['baseline']
        if baseline is not None and system['page_size'] != baseline['page_size']:
            verdict['errors'].append('system:page_size_changed')
        if verdict['errors']:
            verdict['decision'] = 'OBSERVATION_FAILED'
            return verdict
        if self.state['baseline'] is None:
            self.state['baseline'] = system.copy()
        baseline = self.state['baseline']
        history = self.state['history']
        now = system['monotonic']
        if history and (now < history[-1]['monotonic'] or now-history[-1]['monotonic'] > WINDOW+0.5
                        or any(system[key] < history[-1][key] for key in ('pswpin','pswpout','psi_full_total'))):
            verdict['errors'].append('system:counter_regression_or_observation_gap_over_10.5s')
            verdict['decision'] = 'OBSERVATION_FAILED'
            return verdict
        history.append(system.copy())
        while len(history) > 1 and history[1]['monotonic'] <= now-WINDOW:
            history.pop(0)
        previous = history[0]
        duration = now-previous['monotonic']
        swapout = (system['pswpout']-previous['pswpout'])*system['page_size']
        stall = (system['psi_full_total']-previous['psi_full_total'])/1e6
        # Bracket the trailing window with the preceding sample; do not dilute a
        # 10-second stall threshold when the sampled bracket is slightly longer.
        ratio = stall/min(duration, WINDOW) if duration > 0 else 0.0
        growth = system['swap']-baseline['swap']
        verdict['metrics'] = {'s0': baseline['swap'], 'swap_growth': growth, 'window_seconds': duration,
                              'swapout_bytes_10s': swapout, 'psi_full_ratio_10s': ratio}
        if system['swap'] > 0 or growth != 0 or swapout:
            verdict['warnings'].append('GLOBAL_SWAP_WARNING')
        if system['available'] < (72 if start else 24)*GIB:
            verdict['decision'] = 'START_HEADROOM_NOT_MET' if start else 'SYSTEM_HEADROOM'
        elif start and system['swap'] > 64*MIB:
            verdict['decision'] = 'START_SWAP_BUDGET'
        elif growth >= 64*MIB:
            verdict['decision'] = 'GLOBAL_SWAP_GROWTH'
        elif swapout >= 64*MIB:
            verdict['decision'] = 'SWAPOUT_PRESSURE'
        elif ratio >= 0.10:
            verdict['decision'] = 'SYSTEM_PSI_FULL_PRESSURE'
        elif start and require_window and duration < WINDOW:
            verdict['decision'] = 'START_OBSERVATION_INCOMPLETE'
        elif start and swapout > 0:
            verdict['decision'] = 'START_SWAPOUT_OBSERVED'
        if state == 'ACTIVE' and cgroup is not None:
            events = cgroup['events']
            # Both stages create fresh units; a first-sample OOM is already a failure.
            initial = self.state['cgroup_events'].setdefault(cgroup['path'], {'oom':0, 'oom_kill':0})
            verdict['metrics'].update(cgroup_high_events=events.get('high'), cgroup_oom=events['oom'], cgroup_oom_kill=events['oom_kill'])
            if cgroup['swap_current'] > 0 or cgroup['swap_max'] != 0:
                verdict['decision'] = 'WORKER_SWAP_CONTRACT'
            elif any(events[key] > initial[key] for key in ('oom','oom_kill')):
                verdict['decision'] = 'WORKER_OOM'
        return verdict
