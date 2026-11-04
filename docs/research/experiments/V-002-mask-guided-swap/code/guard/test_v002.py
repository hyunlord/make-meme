"""CPU-only regression tests for V002 scoped UMA additions."""
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch
from uma import KernelWatch, drop_caches, peak_decision

class V002Uma(unittest.TestCase):
    def test_peak_above100_blocks(self):
        self.assertEqual(peak_decision(100.01,'weights plus activation estimate'),'START_PEAK_ESTIMATE_EXCEEDED')
        self.assertEqual(peak_decision(100,'weights plus activation estimate'),'CLEAR')
    def test_missing_or_nonfinite_estimate_blocks(self):
        for value in (None, float('nan'),-1):
            self.assertEqual(peak_decision(value,'basis'),'START_PEAK_ESTIMATE_INVALID')
        self.assertEqual(peak_decision(12,''),'START_PEAK_ESTIMATE_INVALID')
    @patch('uma.Path.is_file', return_value=False)
    @patch('uma.subprocess.run')
    def test_absent_helper_never_invokes_sudo(self, run, exists):
        self.assertEqual(drop_caches()['status'],'ABSENT_CONTINUE')
        run.assert_not_called()
    @patch('uma.Path.is_file', return_value=True)
    @patch('uma.subprocess.run', return_value=subprocess.CompletedProcess([],1,'','sudo denied'))
    def test_refused_helper_records_and_continues(self, run, exists):
        self.assertEqual(drop_caches()['status'],'REFUSED_CONTINUE')
        self.assertEqual(run.call_args.args[0],['sudo','-n','/usr/local/sbin/drop-caches'])
    @patch('uma.subprocess.run', return_value=subprocess.CompletedProcess([],0,'','No journal files were found.'))
    def test_unreadable_kernel_uses_other_guards(self, run):
        watch=KernelWatch.start()
        self.assertEqual(watch.status,'UNAVAILABLE_CONTINUE')
        self.assertFalse(watch.poll()['nvrm_hit'])
    @patch('uma.subprocess.run', side_effect=[
        subprocess.CompletedProcess([],0,'{"__CURSOR":"old","MESSAGE":"NV_ERR_NO_MEMORY old"}\n-- cursor: old\n',''),
        subprocess.CompletedProcess([],0,'{"__CURSOR":"new","MESSAGE":"normal fresh event"}\n-- cursor: new\n','')])
    def test_old_nvrm_is_not_a_fresh_trigger(self, run):
        watch=KernelWatch.start()
        self.assertFalse(watch.poll()['nvrm_hit'])
        self.assertIn('--after-cursor=old',run.call_args.args[0])
    @patch('uma.subprocess.run', side_effect=[
        subprocess.CompletedProcess([],0,'-- cursor: old\n',''),
        subprocess.CompletedProcess([],0,'{"__CURSOR":"new","MESSAGE":"NVRM NV_ERR_NO_MEMORY"}\n-- cursor: new\n','')])
    def test_first_new_nvrm_is_a_stop(self, run):
        self.assertTrue(KernelWatch.start().poll()['nvrm_hit'])
    @patch('uma.subprocess.run', side_effect=[
        subprocess.CompletedProcess([],0,'-- cursor: old\n',''),
        subprocess.TimeoutExpired('journalctl',3)])
    def test_previously_readable_kernel_timeout_blocks(self, run):
        self.assertEqual(KernelWatch.start().poll()['status'],'OBSERVATION_FAILED')
    @patch('uma.subprocess.run', side_effect=[
        subprocess.CompletedProcess([],0,'-- cursor: old\n',''),
        subprocess.CompletedProcess([],1,'','permission denied')])
    def test_previously_readable_kernel_permission_loss_blocks(self, run):
        self.assertEqual(KernelWatch.start().poll()['status'],'OBSERVATION_FAILED')
    @patch('uma.subprocess.run', side_effect=[
        subprocess.CompletedProcess([],0,'-- cursor: old\n',''),
        subprocess.CompletedProcess([],0,'{malformed','')])
    def test_previously_readable_kernel_parse_failure_blocks(self, run):
        self.assertEqual(KernelWatch.start().poll()['status'],'OBSERVATION_FAILED')
    @patch('uma.subprocess.run', side_effect=subprocess.TimeoutExpired('journalctl',3))
    def test_initial_timeout_is_not_permission_exception(self, run):
        self.assertEqual(KernelWatch.start().status,'OBSERVATION_FAILED')
    @patch('uma.Path.is_file', return_value=True)
    @patch('uma.subprocess.run', return_value=subprocess.CompletedProcess([],0,'',''))
    def test_cache_success_is_recorded(self, run, exists):
        self.assertEqual(drop_caches()['status'],'APPLIED')

if __name__=='__main__':unittest.main()
