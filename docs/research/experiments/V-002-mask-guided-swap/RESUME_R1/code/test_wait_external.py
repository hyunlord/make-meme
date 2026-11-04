"""Synthetic CPU fixtures; no sleep, GPU query or model imports."""
import unittest
from wait_external import decision, known_batch_parents, public_summary

class WaitRules(unittest.TestCase):
    def samples(self, empty=True):
        return [{'elapsed_seconds':t, 'empty':empty} for t in (0,60,120,180)]
    def test_three_minutes_required(self):
        self.assertEqual(decision(120,120,self.samples()[:3]),'WAITING')
        self.assertEqual(decision(180,180,self.samples()),'READY')
    def test_spaced_samples_and_last_three_empty(self):
        rows=self.samples();rows[-2]['empty']=False
        self.assertEqual(decision(180,180,rows),'WAITING')
        rows=[{'elapsed_seconds':t,'empty':True} for t in (178,179,180)]
        self.assertEqual(decision(180,180,rows),'WAITING')
    def test_caps_override_ready(self):
        self.assertEqual(decision(7200,7200,self.samples()),'BLOCKED_EXTERNAL_GPU')
        self.assertEqual(decision(180,10800,self.samples()),'BLOCKED_EXTERNAL_GPU')
    def test_process_arguments_not_shell_strings(self):
        text='''101 1 python3 /x/blocked_isolated.py run /repo
102 101 /x/r25_grid --size 4
103 1 /bin/sh -c python3 /x/blocked_isolated.py
104 1 ssh host ps blocked_isolated.py
105 1 python3 /x/wait_external.py --stage r25_grid
106 1 python3 /x/cpu_api.py
'''
        self.assertEqual(known_batch_parents(text),[101,102])
    def test_public_summary_removes_private_pids(self):
        ledger={'total_wait_seconds':180,'stages':{'sam':{'status':'READY','samples':[{'gpu_pids':[99],'batch_parent_pids':[88],'empty':False}]}}}
        sample=public_summary(ledger)['stages']['sam']['samples'][0]
        self.assertEqual(sample,{'empty':False})

if __name__=='__main__':unittest.main()
