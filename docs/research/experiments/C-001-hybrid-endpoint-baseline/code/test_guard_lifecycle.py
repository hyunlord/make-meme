"""Replay the observed active/exited unit with an already-removed cgroup."""
from pathlib import Path
import json
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0,str(Path(__file__).parent/'guard'))
import supervisor


class LifecycleTests(unittest.TestCase):
    def replay(self, child_completed_at_exit=False, memory_error=False):
        temporary=tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root=Path(temporary.name)
        (root/'reports').mkdir()
        config={'unit':'make-meme-c001-cpu-test','deadline_epoch':9999999999,
                'allowed_gpu_processes':{},'memory_budget_state':str(root/'memory.json'),
                'research_lock':str(root/'lock'),'worker_max_seconds':60}
        (root/'config.json').write_text(json.dumps(config))
        (root/'freeze.json').write_text(json.dumps({'files':{}}))
        state={'samples':0,'units':0,'stopped':False}
        registered={'proc_exists':True,'state':'R','starttime_ticks':'123','boot_id':'boot',
                    'cgroup':'0::/mock\n','cmdline_sha256':'not-empty'}
        def observe(*args):
            state['samples']+=1
            return {'errors':[],'available':80*2**30,'swap':262144,'decision':'CLEAR',
                    'service_policy':{'status':'EXPECTED_ABSENT_OBSERVED','research_worker_pids':[]},
                    'queue_counts':None,'unclassified_pids':[],'identities':{},
                    'system_memory':{'monotonic':float(state['samples']*2),'page_size':4096,
                                     'available':80*2**30,'swap_total':2**30,'swap_free':2**30-262144,
                                     'swap':262144,'pswpin':0,'pswpout':0,'psi_full_total':0,'errors':[]}}
        def unit(*args):
            state['units']+=1
            active=not state['stopped']
            running=active and state['units']==1
            return {'MainPID':'101' if running else '0','ExecMainPID':'101' if active else '0',
                    'ActiveState':'active' if active else 'inactive','SubState':'running' if running else ('exited' if active else 'dead'),
                    'Result':'success','ExecMainCode':'0' if running else '1','ExecMainStatus':'0',
                    'InvocationID':'invocation' if active else '', 'ControlGroup':'/mock' if running else ''}
        def run(command,**kwargs):
            state['stopped']=True
            return MagicMock(returncode=0)
        child=MagicMock()
        child.poll.side_effect=lambda: 0 if state['stopped'] or (child_completed_at_exit and state['units']>=1) else None
        child.wait.return_value=0
        real_read=Path.read_text
        def read(path,*args,**kwargs):
            if str(path).startswith('/sys/fs/cgroup/mock/'):
                return '101\n' if path.name=='cgroup.procs' else '0\n'
            return real_read(path,*args,**kwargs)
        cg={'path':'/mock','current':1,'high':62*2**30,'max':64*2**30,'events':{'oom':0,'oom_kill':0},
            'swap_current':0,'swap_max':0,'swap_events':{'high':0,'max':0,'fail':0},'pressure':None,'errors':[]}
        real_exists=Path.exists
        def exists(path):
            return True if str(path).startswith('/sys/fs/cgroup/mock/') else real_exists(path)
        original_inspect=supervisor.MemoryBudget.inspect
        def inspect(budget,system,cgroup,cg_state,**kwargs):
            verdict=original_inspect(budget,system,cgroup,cg_state,**kwargs)
            if memory_error and cg_state=='REMOVED':
                verdict['decision']='SYSTEM_PSI_FULL_PRESSURE'
            return verdict
        with patch.object(sys,'argv',['supervisor',str(root)]),patch.object(supervisor,'load_policy',return_value={}), \
             patch.object(supervisor,'observe',side_effect=observe),patch.object(supervisor,'unit_state',side_effect=unit), \
             patch.object(supervisor,'identity',return_value=registered),patch.object(supervisor,'collect_cgroup',return_value=cg), \
             patch.object(supervisor.subprocess,'check_output',return_value=''),patch.object(supervisor.subprocess,'Popen',return_value=child), \
             patch.object(supervisor.subprocess,'run',side_effect=run),patch.object(supervisor.time,'sleep'), \
             patch.object(Path,'read_text',read),patch.object(Path,'exists',exists), \
             patch.object(supervisor.MemoryBudget,'inspect',inspect):
            result=supervisor.main()
        return result,json.loads((root/'reports/supervisor-result.json').read_text())

    def test_normal_exit_receipt_precedes_removed_cgroup_memory_verdict(self):
        result,receipt=self.replay()
        self.assertEqual(result,0,receipt['guard_reason'])
        self.assertTrue(receipt['normal_exit_recorded'])
        self.assertEqual(receipt['status'],'COMPLETE')

    def test_completed_child_also_records_normal_exit(self):
        result,receipt=self.replay(child_completed_at_exit=True)
        self.assertEqual(result,0,receipt['guard_reason'])
        self.assertTrue(receipt['normal_exit_recorded'])

    def test_exit_identity_proof_does_not_override_real_memory_pressure(self):
        result,receipt=self.replay(memory_error=True)
        self.assertEqual(result,2)
        self.assertEqual(receipt['guard_reason'],'SYSTEM_PSI_FULL_PRESSURE')
        self.assertFalse(receipt['normal_exit_recorded'])


if __name__=='__main__':
    unittest.main()
