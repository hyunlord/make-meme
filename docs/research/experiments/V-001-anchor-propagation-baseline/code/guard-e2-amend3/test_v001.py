"""CPU boundary tests: python -m unittest discover -s code/guard -p 'test_v001.py'."""
import unittest
from memory import MemoryBudget, GIB
from safety import decide, start_decision


def sample(t, available=80*GIB, psi=0, out=0, oom=0):
    return dict(monotonic=float(t), page_size=4096, available=available,
                swap_total=4*GIB, swap_free=3*GIB, swap=GIB,
                pswpin=0, pswpout=out, psi_full_total=0,
                psi_full_avg10=psi, oom_kill=oom, errors=[])


class V001Policy(unittest.TestCase):
    def test_existing_swap_and_sub_gib_swapout_warn(self):
        b=MemoryBudget()
        b.inspect(sample(0),None,'BEFORE_CREATED',start=True)
        r=b.inspect(sample(10,out=200000),None,'BEFORE_CREATED',start=True)
        self.assertEqual(r['decision'],'CLEAR')
        self.assertIn('GLOBAL_SWAP_WARNING',r['warnings'])

    def test_low_memory_requires_30_seconds(self):
        b=MemoryBudget()
        for t in range(30):
            self.assertEqual(b.inspect(sample(t,available=11*GIB),None,'BEFORE_CREATED')['decision'],'CLEAR')
        self.assertEqual(b.inspect(sample(30,available=11*GIB),None,'BEFORE_CREATED')['decision'],'SYSTEM_HEADROOM')

    def test_psi_requires_60_seconds_and_persists(self):
        b=MemoryBudget()
        for t in range(60):
            self.assertEqual(b.inspect(sample(t,psi=26),None,'BEFORE_CREATED')['decision'],'CLEAR')
        restored=MemoryBudget(b.export())
        self.assertEqual(restored.inspect(sample(60,psi=26),None,'BEFORE_CREATED')['decision'],'SYSTEM_PSI_FULL_PRESSURE')

    def test_recovery_resets_duration_not_baseline(self):
        b=MemoryBudget()
        for t in range(30): b.inspect(sample(t,available=11*GIB),None,'BEFORE_CREATED')
        b.inspect(sample(30),None,'BEFORE_CREATED')
        self.assertEqual(b.inspect(sample(31,available=11*GIB),None,'BEFORE_CREATED')['decision'],'CLEAR')
        self.assertEqual(b.export()['baseline']['monotonic'],0)

    def test_system_oom_and_observation_failure_block(self):
        b=MemoryBudget(); b.inspect(sample(0),None,'BEFORE_CREATED')
        self.assertEqual(b.inspect(sample(1,oom=1),None,'BEFORE_CREATED')['decision'],'SYSTEM_OOM')
        self.assertEqual(b.inspect({'errors':['missing']},None,'BEFORE_CREATED')['decision'],'OBSERVATION_FAILED')

    def test_start_uses_e2_amended_admission(self):
        self.assertEqual(start_decision('CLEAR',112,100),'CLEAR')

    def test_external_work_and_queue_block(self):
        clear={'decision':'CLEAR'}
        self.assertEqual(decide([],1,0,set(),False,80,0,clear),'QUEUE_BUSY')
        self.assertEqual(decide([],0,0,{999},False,80,0,clear),'UNKNOWN_GPU_PID')
        self.assertEqual(decide(['readfailed'],0,0,set(),False,80,0,clear),'OBSERVATION_FAILED')

    def test_start_window_is_required(self):
        self.assertEqual(MemoryBudget().inspect(sample(0),None,'BEFORE_CREATED',start=True)['decision'],'START_OBSERVATION_INCOMPLETE')

    def test_one_gib_swapout_not_authorized(self):
        b=MemoryBudget();b.inspect(sample(0),None,'BEFORE_CREATED')
        self.assertEqual(b.inspect(sample(1,out=GIB//4096),None,'BEFORE_CREATED')['decision'],'SWAPOUT_PRESSURE')

    def test_observation_gap_and_nan_fail_closed(self):
        b=MemoryBudget();b.inspect(sample(0),None,'BEFORE_CREATED')
        self.assertEqual(b.inspect(sample(11),None,'BEFORE_CREATED')['decision'],'OBSERVATION_FAILED')
        self.assertEqual(MemoryBudget().inspect(sample(0,psi=float('nan')),None,'BEFORE_CREATED')['decision'],'OBSERVATION_FAILED')

    def test_threshold_is_strict_and_psi_transient_allowed(self):
        b=MemoryBudget()
        for t in range(65):
            self.assertEqual(b.inspect(sample(t,available=12*GIB,psi=25),None,'BEFORE_CREATED')['decision'],'CLEAR')

    def test_worker_oom_and_swap_still_block(self):
        cg=dict(path='/owned',current=1,high=10,max=20,events={'oom':1,'oom_kill':0},swap_current=0,swap_max=0,swap_events={'max':0},errors=[])
        self.assertEqual(MemoryBudget().inspect(sample(0),cg,'ACTIVE')['decision'],'WORKER_OOM')
        cg['events']['oom']=0;cg['swap_current']=1
        self.assertEqual(MemoryBudget().inspect(sample(0),cg,'ACTIVE')['decision'],'WORKER_SWAP_CONTRACT')

if __name__=='__main__': unittest.main()
