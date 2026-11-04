"""CPU-only r1 policy boundary fixtures; no system or GPU calls."""
import unittest
from safety import lifecycle_decision
from uma import cache_requirement_decision

class R1Policy(unittest.TestCase):
    def row(self):
        return {'errors': [], 'queue_counts': {'running':0,'pending':0},
                'memory_verdict':{'decision':'CLEAR'}, 'unclassified_pids':[999], 'identities':{}}
    def test_generation_external_gpu_continues(self):
        self.assertEqual(lifecycle_decision(self.row(),{}, {},False,None,allow_external_gpu=True),'CLEAR')
    def test_external_gpu_still_blocks_default(self):
        self.assertEqual(lifecycle_decision(self.row(),{}, {},False,None),'UNKNOWN_GPU_PID')
    def test_memory_hazard_not_hidden(self):
        row=self.row();row['memory_verdict']['decision']='WORKER_OOM'
        self.assertEqual(lifecycle_decision(row,{}, {},False,None,allow_external_gpu=True),'WORKER_OOM')
    def test_observation_failure_not_hidden(self):
        row=self.row();row['errors']=['gpu:TimeoutExpired']
        self.assertEqual(lifecycle_decision(row,{}, {},False,None,allow_external_gpu=True),'OBSERVATION_FAILED')
    def test_queue_conflict_not_hidden(self):
        row=self.row();row['queue_counts']['running']=1
        self.assertEqual(lifecycle_decision(row,{}, {},False,None,allow_external_gpu=True),'QUEUE_BUSY')
    def test_owned_identity_uncertainty_still_times_out(self):
        row=self.row();row['unclassified_pids']=[123,999]
        row['identities']={'123':{'proc_exists':False}}
        self.assertEqual(lifecycle_decision(row,{'pid':123},{},False,31,allow_external_gpu=True),'IDENTITY_UNCERTAIN_TIMEOUT')
    def test_completion_does_not_hide_memory_stop(self):
        row=self.row();row['memory_verdict']['decision']='SYSTEM_HEADROOM'
        self.assertEqual(lifecycle_decision(row,{}, {},True,None,allow_external_gpu=True),'SYSTEM_HEADROOM')
    def test_external_only_allows_completion_not_default(self):
        self.assertEqual(lifecycle_decision(self.row(),{}, {},True,None,allow_external_gpu=True),'COMPLETE')
    def test_required_cache_failure_skips(self):
        for status in ('ABSENT_CONTINUE','REFUSED_CONTINUE','UNAVAILABLE_CONTINUE'):
            self.assertEqual(cache_requirement_decision(status,required=True),'SKIPPED_NO_CACHE_HELPER')
            self.assertEqual(cache_requirement_decision(status,required=False),'CLEAR')
    def test_applied_required_cache_passes(self):
        self.assertEqual(cache_requirement_decision('APPLIED',required=True),'CLEAR')

if __name__=='__main__':unittest.main()
