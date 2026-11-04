"""CPU fixtures for an owned worker exiting during RSS sampling."""
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch
from supervisor import sample_owned_rss, worker_rss_highwater

class ExitObservation(unittest.TestCase):
    def registered(self):
        return {'pid':123,'invocation_id':'exact'}
    def unit(self):
        return {'ActiveState':'active','SubState':'exited','MainPID':'0','ExecMainPID':'123',
                'ExecMainCode':'1','ExecMainStatus':'0','Result':'success','InvocationID':'exact','ControlGroup':''}
    @patch('supervisor.worker_rss_highwater', side_effect=ValueError('WORKER_RSS_OBSERVATION_INVALID:123'))
    def test_exit_race_requires_fresh_exact_exit(self,rss):
        fresh=self.unit()
        with patch('supervisor.unit_state',return_value=fresh):
            value,unit,refreshed=sample_owned_rss('owned-unit',self.registered(),{'SubState':'running'})
        self.assertIsNone(value);self.assertEqual(unit,fresh);self.assertTrue(refreshed)
    @patch('supervisor.worker_rss_highwater', side_effect=ValueError('WORKER_RSS_OBSERVATION_INVALID:123'))
    def test_live_invalid_rss_still_raises(self,rss):
        fresh=self.unit();fresh['SubState']='running';fresh['MainPID']='123'
        with patch('supervisor.unit_state',return_value=fresh),self.assertRaises(ValueError):
            sample_owned_rss('owned-unit',self.registered(),fresh)
    @patch('supervisor.worker_rss_highwater', side_effect=ValueError('WORKER_RSS_OBSERVATION_INVALID:123'))
    def test_wrong_invocation_still_raises(self,rss):
        fresh=self.unit();fresh['InvocationID']='different'
        with patch('supervisor.unit_state',return_value=fresh),self.assertRaises(ValueError):
            sample_owned_rss('owned-unit',self.registered(),fresh)
    @patch('supervisor.worker_rss_highwater',return_value=99)
    def test_valid_sample_does_not_refresh(self,rss):
        old={'SubState':'running'}
        with patch('supervisor.unit_state') as query:
            self.assertEqual(sample_owned_rss('owned-unit',self.registered(),old),(99,old,False))
        query.assert_not_called()
    @patch('supervisor.worker_rss_highwater',side_effect=PermissionError('denied'))
    def test_permission_error_is_not_caught(self,rss):
        with self.assertRaises(PermissionError):sample_owned_rss('owned-unit',self.registered(),{})

    def test_real_missing_rss_field_with_exact_exit(self):
        with tempfile.TemporaryDirectory() as directory:
            proc=Path(directory);(proc/'123').mkdir()
            (proc/'123'/'status').write_text('Name: python\nState: R (running)\n')
            with self.assertRaisesRegex(ValueError,'WORKER_RSS_OBSERVATION_INVALID:123'):
                worker_rss_highwater(123,proc)
            with patch('supervisor.worker_rss_highwater',side_effect=lambda pid:worker_rss_highwater(pid,proc)),patch('supervisor.unit_state',return_value=self.unit()):
                self.assertEqual(sample_owned_rss('owned-unit',self.registered(),{}),(None,self.unit(),True))
    def test_other_value_error_does_not_refresh(self):
        with patch('supervisor.worker_rss_highwater',side_effect=ValueError('too many values to unpack')),patch('supervisor.unit_state') as query,self.assertRaises(ValueError):
            sample_owned_rss('owned-unit',self.registered(),{})
        query.assert_not_called()

if __name__=='__main__':unittest.main()
