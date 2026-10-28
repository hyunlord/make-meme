"""CPU-only regression checks for the bounded operational memory contract."""
import tempfile
import unittest
from pathlib import Path

from memory import MemoryBudget, collect_cgroup, collect_system


def sample(t=0.0, **changes):
    row = dict(monotonic=t, page_size=65536, available=80*2**30,
               swap_total=2**30, swap_free=2**30-262144, swap=262144,
               pswpin=0, pswpout=0, psi_full_total=0, errors=[])
    row.update(changes)
    return row


def cgroup(**changes):
    row = dict(path='STEP_S', current=2**30, high=62*2**30, max=64*2**30,
               events={'oom': 0, 'oom_kill': 0, 'high': 0}, swap_current=0,
               swap_max=0, swap_events={'high': 0, 'max': 0, 'fail': 0},
               pressure=None, errors=[])
    row.update(changes)
    return row


class MemoryTests(unittest.TestCase):
    def test_stable_residue_warns_without_stopping(self):
        budget = MemoryBudget()
        budget.inspect(sample(), None, 'BEFORE_CREATED')
        verdict = budget.inspect(sample(10), None, 'BEFORE_CREATED', start=True)
        self.assertEqual(verdict['decision'], 'CLEAR')
        self.assertIn('GLOBAL_SWAP_WARNING', verdict['warnings'])

    def test_worker_swap_and_unapplied_limit_block(self):
        for changes in ({'swap_current': 1}, {'swap_max': 'max'}):
            with self.subTest(changes=changes):
                verdict = MemoryBudget().inspect(sample(), cgroup(**changes), 'ACTIVE')
                self.assertEqual(verdict['decision'], 'WORKER_SWAP_CONTRACT')

    def test_global_growth_blocks_at_inclusive_limit(self):
        budget = MemoryBudget()
        budget.inspect(sample(), None, 'BEFORE_CREATED')
        verdict = budget.inspect(sample(10, swap=262144+64*2**20), cgroup(), 'ACTIVE')
        self.assertEqual(verdict['decision'], 'GLOBAL_SWAP_GROWTH')

    def test_swapout_uses_actual_page_size(self):
        budget = MemoryBudget()
        budget.inspect(sample(), None, 'BEFORE_CREATED')
        verdict = budget.inspect(sample(10, pswpout=1024), cgroup(), 'ACTIVE')
        self.assertEqual(verdict['decision'], 'SWAPOUT_PRESSURE')
        self.assertEqual(verdict['metrics']['swapout_bytes_10s'], 64*2**20)

    def test_psi_pressure_blocks(self):
        budget = MemoryBudget()
        budget.inspect(sample(), None, 'BEFORE_CREATED')
        verdict = budget.inspect(sample(10, psi_full_total=1000000), cgroup(), 'ACTIVE')
        self.assertEqual(verdict['decision'], 'SYSTEM_PSI_FULL_PRESSURE')

    def test_headroom_start_and_runtime(self):
        for start, available in ((True, 71*2**30), (False, 23*2**30)):
            verdict = MemoryBudget().inspect(sample(available=available), None, 'BEFORE_CREATED', start=start)
            self.assertEqual(verdict['decision'], 'START_HEADROOM_NOT_MET' if start else 'SYSTEM_HEADROOM')

    def test_oom_increase_blocks_but_high_does_not(self):
        budget = MemoryBudget()
        budget.inspect(sample(), cgroup(), 'ACTIVE')
        self.assertEqual(budget.inspect(sample(1), cgroup(events={'oom':0,'oom_kill':0,'high':999}), 'ACTIVE')['decision'], 'CLEAR')
        self.assertEqual(budget.inspect(sample(2), cgroup(events={'oom':1,'oom_kill':0,'high':1000}), 'ACTIVE')['decision'], 'WORKER_OOM')

    def test_observation_failure_never_becomes_zero(self):
        for row in (sample(errors=['/proc/vmstat:PermissionError']), sample(page_size=None)):
            self.assertEqual(MemoryBudget().inspect(row, None, 'BEFORE_CREATED')['decision'], 'OBSERVATION_FAILED')

    def test_baseline_survives_serialization_and_decode(self):
        budget = MemoryBudget()
        budget.inspect(sample(), None, 'BEFORE_CREATED')
        budget.inspect(sample(10, swap=262144+32*2**20), cgroup(), 'ACTIVE')
        restored = MemoryBudget(budget.export())
        verdict = restored.inspect(sample(20, swap=262144+64*2**20), cgroup(path='STEP_D'), 'ACTIVE')
        self.assertEqual(verdict['decision'], 'GLOBAL_SWAP_GROWTH')
        self.assertEqual(restored.export()['baseline']['swap'], 262144)

    def test_missing_active_cgroup_and_unverified_removal_fail(self):
        for state in ('ACTIVE', 'REMOVED'):
            self.assertEqual(MemoryBudget().inspect(sample(), None, state)['decision'], 'OBSERVATION_FAILED')
        self.assertEqual(MemoryBudget().inspect(sample(), None, 'REMOVED', verified_exit=True)['decision'], 'CLEAR')

    def test_start_needs_ten_seconds_and_no_swapout(self):
        budget = MemoryBudget()
        self.assertEqual(budget.inspect(sample(), None, 'BEFORE_CREATED', start=True)['decision'], 'START_OBSERVATION_INCOMPLETE')
        self.assertEqual(budget.inspect(sample(10, pswpout=1), None, 'BEFORE_CREATED', start=True)['decision'], 'START_SWAPOUT_OBSERVED')

    def test_preflight_defers_window_but_keeps_start_swap_and_headroom(self):
        for changes, expected in (({}, 'CLEAR'), ({'swap':65*2**20}, 'START_SWAP_BUDGET'),
                                  ({'available':71*2**30}, 'START_HEADROOM_NOT_MET')):
            verdict = MemoryBudget().inspect(sample(**changes),None,'BEFORE_CREATED',start=True,require_window=False)
            self.assertEqual(verdict['decision'], expected)

    def test_collectors_report_missing_required_paths(self):
        with tempfile.TemporaryDirectory() as folder:
            system = collect_system(Path(folder))
            worker = collect_cgroup(Path(folder))
        self.assertTrue(system['errors'])
        self.assertNotIn('available', system)
        self.assertTrue(worker['errors'])
        self.assertNotIn('swap_current', worker)

    def test_invalid_numeric_or_inconsistent_memory_fails(self):
        for changes in ({'page_size':0}, {'swap':-1}, {'swap_total':0}, {'pswpout':-1}):
            self.assertEqual(MemoryBudget().inspect(sample(**changes), None, 'BEFORE_CREATED')['decision'], 'OBSERVATION_FAILED')

    def test_observation_gap_and_counter_regression_fail(self):
        for later in (sample(30), sample(1, pswpout=-1)):
            budget = MemoryBudget()
            budget.inspect(sample(), None, 'BEFORE_CREATED')
            self.assertEqual(budget.inspect(later, None, 'BEFORE_CREATED')['decision'], 'OBSERVATION_FAILED')

    def test_collectors_preserve_optional_pressure_absence(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            for name, text in {'memory.current':'1', 'memory.high':'max', 'memory.max':'64',
                               'memory.events':'high 1\noom 0\noom_kill 0\n',
                               'memory.swap.current':'0', 'memory.swap.max':'0',
                               'memory.swap.events':'high 0\nmax 0\nfail 0\n'}.items():
                (folder/name).write_text(text)
            row = collect_cgroup(folder)
        self.assertEqual(row['errors'], [])
        self.assertIsNone(row['pressure'])
        self.assertEqual(row['high'], 'max')


if __name__ == '__main__':
    unittest.main()
