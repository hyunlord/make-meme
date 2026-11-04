"""The r1 user contract excludes E2-only 112 GiB admission and uses a fixed cap."""
import unittest
from safety import start_decision
from supervisor import worker_memory_cap

class R1StartContract(unittest.TestCase):
    def test_111_gib_admitted_when_observed_pressure_clear(self):
        self.assertEqual(start_decision('CLEAR',111,1000),'CLEAR')
    def test_existing_pressure_and_observation_failure_preserved(self):
        for verdict in ('SYSTEM_HEADROOM','SYSTEM_PSI_FULL_PRESSURE','SYSTEM_OOM','OBSERVATION_FAILED','START_OBSERVATION_INCOMPLETE'):
            self.assertEqual(start_decision(verdict,111,1000),verdict)
    def test_deadline_preserved(self):
        self.assertEqual(start_decision('CLEAR',111,60),'DEADLINE')
    def test_fixed_100_gib_cap(self):
        self.assertEqual(worker_memory_cap(111*2**30),100*2**30)
        self.assertEqual(worker_memory_cap(120*2**30),100*2**30)

if __name__=='__main__':unittest.main()
