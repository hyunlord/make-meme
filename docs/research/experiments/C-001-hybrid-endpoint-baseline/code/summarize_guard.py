"""Export numerical guard evidence without process identities or machine paths."""
from pathlib import Path
import json
import sys


def summarize(stage: Path) -> dict:
    reports = stage/'reports'
    result = json.loads((reports/'supervisor-result.json').read_text())
    rows = [json.loads(line) for line in (reports/'observations.jsonl').read_text().splitlines()]
    systems = [row['system_memory'] for row in rows if row.get('system_memory')]
    groups = [row['worker_memory'] for row in rows if row.get('worker_memory')]
    verdicts = [row['memory_verdict'] for row in rows if row.get('memory_verdict')]
    values = lambda items, key: [item[key] for item in items if item.get(key) is not None]
    return {
        'status': result['status'], 'guard_reason': result['guard_reason'],
        'worker_returncode': result['worker_returncode'],
        'normal_exit_recorded': result['normal_exit_recorded'],
        'cleanup_error_count': len(result['cleanup_errors']),
        'elapsed_seconds': result['finished']-result['started'],
        'observations': len(rows), 'final_decision': result['final']['decision'],
        'final_cgroup_state': result['final'].get('cgroup_state'),
        'minimum_memavailable_bytes': min(values(systems,'available'),default=None),
        'peak_observed_cgroup_current_bytes': max(values(groups,'current'),default=None),
        'maximum_cgroup_swap_current_bytes': max(values(groups,'swap_current'),default=None),
        'observed_cgroup_swap_max_values': sorted(set(values(groups,'swap_max'))),
        'system_swap_min_bytes': min(values(systems,'swap'),default=None),
        'system_swap_max_bytes': max(values(systems,'swap'),default=None),
        'host_page_sizes': sorted(set(values(systems,'page_size'))),
        'maximum_high_event_count': max([g['events']['high'] for g in groups],default=None),
        'maximum_oom_count': max([g['events']['oom'] for g in groups],default=None),
        'maximum_oom_kill_count': max([g['events']['oom_kill'] for g in groups],default=None),
        'memory_decisions': sorted(set(v['decision'] for v in verdicts)),
        'warnings': sorted(set(w for v in verdicts for w in v.get('warnings',[]))),
        'memory_metrics': [v.get('metrics',{}) for v in verdicts],
        'scope': 'Observed samples; cgroup current is not a claim of complete CUDA allocation accounting.'
    }


if __name__ == '__main__':
    print(json.dumps(summarize(Path(sys.argv[1])),indent=2))
