# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# Run: python check_resume_policy.py C013_GUARD_DIR
"""Synthetic safety boundaries for the C-013-only admission amendment."""
import sys
import json
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from memory import MemoryBudget, MIB, GIB
from safety import decide, start_decision


def sample(t: float) -> dict:
    return dict(monotonic=t, errors=[], page_size=4096, available=100*GIB,
                swap_total=16*GIB, swap_free=15*GIB, swap=GIB,
                pswpin=0, pswpout=0, psi_full_total=0)


def main() -> None:
    checks = {}
    def run(name: str, changes: dict, expected: str, *, start: bool = True) -> None:
        budget = MemoryBudget()
        first = budget.inspect(sample(0), None, 'BEFORE_CREATED', start=True)
        assert first['decision'] == 'START_OBSERVATION_INCOMPLETE'
        row = sample(10); row.update(changes)
        verdict = budget.inspect(row, None, 'BEFORE_CREATED', start=start)
        assert verdict['decision'] == expected, (name, verdict)
        assert budget.export()['baseline']['swap'] == GIB
        assert 'GLOBAL_SWAP_WARNING' in verdict['warnings'] or expected == 'OBSERVATION_FAILED'
        checks[name] = expected
    run('stable_high_swap', {}, 'CLEAR')
    run('growth', {'swap': GIB+64*MIB, 'swap_free': 15*GIB-64*MIB}, 'GLOBAL_SWAP_GROWTH')
    run('swapout', {'pswpout': 64*MIB//4096}, 'SWAPOUT_PRESSURE')
    run('psi', {'psi_full_total': 1000000}, 'SYSTEM_PSI_FULL_PRESSURE')
    run('start_headroom', {'available': 71*GIB}, 'START_HEADROOM_NOT_MET')
    run('runtime_headroom', {'available': 23*GIB}, 'SYSTEM_HEADROOM', start=False)
    run('observation_error', {'errors': ['fixture']}, 'OBSERVATION_FAILED')
    for field, value, expected in [('swap_current', 1, 'WORKER_SWAP_CONTRACT'), ('swap_max', 1, 'WORKER_SWAP_CONTRACT'), ('events', {'oom': 1, 'oom_kill': 0}, 'WORKER_OOM')]:
        budget=MemoryBudget();budget.inspect(sample(0),None,'BEFORE_CREATED')
        cg=dict(path='/fixture',current=1,high=60*GIB,max=64*GIB,events={'oom':0,'oom_kill':0},swap_current=0,swap_max=0,swap_events={'max':0},pressure='',errors=[])
        cg[field]=value
        assert budget.inspect(sample(10),cg,'ACTIVE')['decision']==expected
        checks[field]=expected
    clear={'decision':'CLEAR'}
    assert decide([],0,0,{123},False,100,GIB,clear)=='UNKNOWN_GPU_PID'
    assert decide([],1,0,set(),False,100,GIB,clear)=='QUEUE_BUSY'
    assert decide(['service:changed'],0,0,set(),False,100,GIB,clear)=='OBSERVATION_FAILED'
    assert start_decision('CLEAR',71,100)=='START_HEADROOM_NOT_MET'
    checks.update(external_gpu='BLOCKED',service='BLOCKED',insufficient_window='BLOCKED')
    print(json.dumps({'status':'PASS','checks':checks},indent=2))


if __name__ == '__main__':
    main()
