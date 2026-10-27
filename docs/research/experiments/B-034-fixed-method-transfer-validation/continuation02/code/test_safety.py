"""CPU lifecycle policy fixtures, never GPU process simulations."""
import unittest
from safety import classify_worker,lifecycle_decision,start_decision,normal_exit,finalized_exit
class Policy(unittest.TestCase):
    def setUp(self):
        self.reg={'pid':123,'starttime_ticks':'42','boot_id':'boot','cgroup':'0::/unit','cmdline_sha256':'abc','invocation_id':'inv','unit_cgroup':'/unit'}
        self.unit={'MainPID':'123','ExecMainPID':'123','InvocationID':'inv','ControlGroup':'/unit','ExecMainCode':'1','ExecMainStatus':'0'}
        self.current={**self.reg,'proc_exists':True,'state':'Z','cmdline_sha256':'empty'}
        self.row={'errors':[],'queue_counts':{'running':0,'pending':0},'available':80*2**30,'swap':0,'unclassified_pids':[123],'identities':{'123':self.current}}
    def test_verified_normal_exit(self):self.assertEqual(lifecycle_decision(self.row,self.reg,self.unit,True,0),'OWN_WORKER_DRAINING')
    def test_reuse(self):
        self.current['starttime_ticks']='43';self.assertEqual(lifecycle_decision(self.row,self.reg,self.unit,True,0),'UNKNOWN_GPU_PID')
    def test_external(self):
        self.row['unclassified_pids'].append(999);self.assertEqual(lifecycle_decision(self.row,self.reg,self.unit,True,0),'UNKNOWN_GPU_PID')
    def test_queue(self):
        self.row['queue_counts']['running']=1;self.assertEqual(lifecycle_decision(self.row,self.reg,self.unit,True,0),'QUEUE_BUSY')
    def test_error(self):
        self.row['errors']=['gpu'];self.assertEqual(lifecycle_decision(self.row,self.reg,self.unit,True,0),'OBSERVATION_FAILED')
    def test_missing(self):
        self.current['proc_exists']=False;self.assertEqual(lifecycle_decision(self.row,self.reg,self.unit,True,0),'IDENTITY_UNCERTAIN');self.assertEqual(lifecycle_decision(self.row,self.reg,self.unit,True,30),'IDENTITY_UNCERTAIN_TIMEOUT')
    def test_drain_deadline(self):self.assertEqual(lifecycle_decision(self.row,self.reg,self.unit,True,30),'DRAIN_TIMEOUT')
    def test_empty_not_proof(self):
        self.current['state']='R';self.assertEqual(classify_worker(self.current,self.reg,self.unit),'IDENTITY_UNCERTAIN')
    def test_invocation(self):
        self.unit['InvocationID']='different';self.assertEqual(classify_worker(self.current,self.reg,self.unit),'IDENTITY_MISMATCH')
    def test_memory_overrides(self):
        self.row['available']=23*2**30;self.assertEqual(lifecycle_decision(self.row,self.reg,self.unit,True,0),'SYSTEM_HEADROOM_OR_SWAP')
    def test_complete_clear(self):
        self.row['unclassified_pids']=[];self.assertEqual(lifecycle_decision(self.row,self.reg,self.unit,True,0),'COMPLETE')
    def test_start_threshold(self):self.assertEqual(start_decision('CLEAR',71,100),'START_HEADROOM_NOT_MET')
    def test_final_exit(self):
        unit={**self.unit,'MainPID':'0','ActiveState':'active','SubState':'exited','Result':'success'}
        self.assertTrue(normal_exit(unit,self.reg))
        for key,value in (('MainPID','123'),('ActiveState','inactive'),('ExecMainStatus','1'),('InvocationID','other')):
            self.assertFalse(normal_exit({**unit,key:value},self.reg))
    def test_final_collected_receipt(self):
        proof={'unit':{**self.unit,'MainPID':'0','ActiveState':'active','SubState':'exited','Result':'success'}}
        final={'MainPID':'0','ActiveState':'inactive','InvocationID':''}
        self.assertTrue(finalized_exit(final,self.reg,proof))
        self.assertFalse(finalized_exit(final,self.reg,None))
        self.assertFalse(finalized_exit({**final,'InvocationID':'new'},self.reg,proof))
        self.assertFalse(finalized_exit({**final,'MainPID':'123'},self.reg,proof))
if __name__=='__main__':unittest.main()
