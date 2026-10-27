import errno
import unittest
from policy import absence_decision

class PolicyTests(unittest.TestCase):
    def test_explicit_absence_only(self):
        self.assertEqual(absence_decision(True, [], [], [], errno.ECONNREFUSED), 'EXPECTED_ABSENT_OBSERVED')
    def test_no_permission(self):
        self.assertEqual(absence_decision(False, [], [], [], errno.ECONNREFUSED), 'POLICY_NOT_AUTHORIZED')
    def test_listener_or_process(self):
        for p,l in [([1],[]),([],['8190'])]:
            self.assertEqual(absence_decision(True,p,l,[],errno.ECONNREFUSED),'SERVICE_APPEARED')
    def test_errors_never_absent(self):
        self.assertEqual(absence_decision(True,[],[],['PermissionError'],errno.ECONNREFUSED),'OBSERVATION_FAILED')
    def test_other_queue_failures(self):
        for error in [None,errno.ETIMEDOUT,errno.EACCES,errno.EHOSTUNREACH]:
            self.assertEqual(absence_decision(True,[],[],[],error),'QUEUE_STATE_CONFLICT')

class IntegrationTests(unittest.TestCase):
    def test_external_gpu_is_not_allowed_by_absence(self):
        from safety import lifecycle_decision
        row={'errors':[],'queue_counts':None,'service_policy':{'status':'EXPECTED_ABSENT_OBSERVED'},'available':80*2**30,'swap':0,'unclassified_pids':[999],'identities':{}}
        self.assertEqual(lifecycle_decision(row,{}, {},False,None),'UNKNOWN_GPU_PID')
    def test_runtime_service_appearance_overrides_completion(self):
        from safety import lifecycle_decision
        row={'errors':['service:SERVICE_APPEARED'],'queue_counts':None,'available':80*2**30,'swap':0,'unclassified_pids':[]}
        self.assertEqual(lifecycle_decision(row,{}, {},True,None),'OBSERVATION_FAILED')
    def test_null_queue_needs_explicit_observed_absence(self):
        from safety import lifecycle_decision
        row={'errors':[],'queue_counts':None,'available':80*2**30,'swap':0,'unclassified_pids':[]}
        self.assertEqual(lifecycle_decision(row,{}, {},False,None),'OBSERVATION_FAILED')
    def test_runtime_memory_still_blocks(self):
        from safety import lifecycle_decision
        row={'errors':[],'queue_counts':None,'service_policy':{'status':'EXPECTED_ABSENT_OBSERVED'},'available':23*2**30,'swap':0,'unclassified_pids':[]}
        self.assertEqual(lifecycle_decision(row,{}, {},False,None),'SYSTEM_HEADROOM_OR_SWAP')
    def test_absent_clear_can_complete(self):
        from safety import lifecycle_decision
        row={'errors':[],'queue_counts':None,'service_policy':{'status':'EXPECTED_ABSENT_OBSERVED'},'available':80*2**30,'swap':0,'unclassified_pids':[]}
        self.assertEqual(lifecycle_decision(row,{}, {},True,None),'COMPLETE')

class ObservationTests(unittest.TestCase):
    def test_malformed_gpu_cannot_be_empty(self):
        from unittest.mock import patch
        from safety import observe
        service={'status':'EXPECTED_ABSENT_OBSERVED','queue_status':'UNAVAILABLE'}
        memory='MemAvailable: 90000000 kB\nSwapTotal: 0 kB\nSwapFree: 0 kB\n'
        with patch('policy.observe_service',return_value=service),patch('safety.subprocess.check_output',return_value=b'not-a-pid\n'),patch('safety.Path.read_text',return_value=memory):
            row=observe({},set(),False,{'authorized':True})
        self.assertIn('gpu:ValueError',row['errors'])
        self.assertEqual(row['decision'],'OBSERVATION_FAILED')
    def test_malformed_process_output_blocks(self):
        from unittest.mock import patch,MagicMock
        from policy import observe_service
        connection=MagicMock();connection.request.side_effect=ConnectionRefusedError(errno.ECONNREFUSED,'refused')
        with patch('policy.subprocess.check_output',side_effect=['malformed\n','']),patch('policy.http.client.HTTPConnection',return_value=connection):
            row=observe_service({'authorized':True,'process_markers':['comfy'],'service_cwd':'/comfy'})
        self.assertEqual(row['status'],'OBSERVATION_FAILED')
    def test_orphan_cpu_worker_is_observed(self):
        from unittest.mock import patch,MagicMock
        from policy import observe_service
        connection=MagicMock();connection.request.side_effect=ConnectionRefusedError(errno.ECONNREFUSED,'refused')
        rowtext='99999 1 python /research/B034/code/worker.py /research/B034/stages/STEP_S\n'
        with patch('policy.subprocess.check_output',side_effect=[rowtext,'']),patch('policy.http.client.HTTPConnection',return_value=connection):
            row=observe_service({'authorized':True,'process_markers':['comfy'],'service_cwd':'/comfy','research_root':'/research/B034'})
        self.assertEqual(row['research_worker_pids'],[99999])
