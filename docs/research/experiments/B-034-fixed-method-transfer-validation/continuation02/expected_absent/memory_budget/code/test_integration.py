"""Guard-route agreement checks without GPU/model imports or service operations."""
import unittest
from unittest.mock import patch

from memory import MemoryBudget
from safety import decide, lifecycle_decision, observe
from test_memory import cgroup, sample


def lifecycle_row(verdict):
    return {'errors': [], 'queue_counts': None,
            'service_policy': {'status': 'EXPECTED_ABSENT_OBSERVED'},
            'available': 80*2**30, 'swap': 262144,
            'unclassified_pids': [], 'identities': {}, 'memory_verdict': verdict}


class GuardIntegrationTests(unittest.TestCase):
    def test_both_routes_accept_stable_global_residue(self):
        verdict = MemoryBudget().inspect(sample(), cgroup(), 'ACTIVE')
        self.assertEqual(decide([], 0, 0, set(), False, 80, 262144, verdict), 'CLEAR')
        self.assertEqual(lifecycle_decision(lifecycle_row(verdict), {}, {}, False, None), 'CLEAR')

    def test_both_routes_consume_identical_memory_verdicts(self):
        for changes in ({'available':23*2**30}, {'errors':['permission denied']}):
            with self.subTest(changes=changes):
                verdict = MemoryBudget().inspect(sample(**changes), cgroup(), 'ACTIVE')
                expected = verdict['decision']
                self.assertEqual(decide([], 0, 0, set(), True, 80, 262144, verdict), expected)
                self.assertEqual(lifecycle_decision(lifecycle_row(verdict), {}, {}, True, None), expected)
        verdict = MemoryBudget().inspect(sample(), cgroup(swap_current=1), 'ACTIVE')
        self.assertEqual(decide([], 0, 0, set(), True, 80, 262144, verdict), 'WORKER_SWAP_CONTRACT')
        self.assertEqual(lifecycle_decision(lifecycle_row(verdict), {}, {}, True, None), 'WORKER_SWAP_CONTRACT')

    def test_missing_shared_verdict_fails_closed_in_both_routes(self):
        self.assertEqual(decide([],0,0,set(),False,80,262144), 'OBSERVATION_FAILED')
        row = lifecycle_row(None)
        self.assertEqual(lifecycle_decision(row,{}, {},False,None), 'OBSERVATION_FAILED')

    def test_preflight_observation_failure_is_preserved(self):
        service = {'status':'EXPECTED_ABSENT_OBSERVED', 'queue_status':'UNAVAILABLE', 'research_worker_pids':[]}
        missing = {'monotonic':0.0, 'page_size':65536, 'errors':['/proc/meminfo:PermissionError']}
        with patch('policy.observe_service', return_value=service), patch('safety.subprocess.check_output',return_value=b''), patch('safety.collect_system',return_value=missing):
            row = observe({},set(),False,{'authorized':True})
        self.assertEqual(row['decision'],'OBSERVATION_FAILED')
        self.assertIsNone(row['available'])
        self.assertIsNone(row['swap'])
        self.assertIn('/proc/meminfo:PermissionError',row['errors'])

    def test_external_gpu_and_service_errors_still_override_completion(self):
        verdict = MemoryBudget().inspect(sample(),cgroup(),'ACTIVE')
        self.assertEqual(decide([],0,0,{999},True,80,262144,verdict),'UNKNOWN_GPU_PID')
        row = lifecycle_row(verdict)
        row['errors'] = ['service:SERVICE_APPEARED']
        self.assertEqual(lifecycle_decision(row,{}, {},True,None),'OBSERVATION_FAILED')


if __name__ == '__main__':
    unittest.main()
