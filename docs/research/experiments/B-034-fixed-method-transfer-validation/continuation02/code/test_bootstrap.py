"""CPU-only required environment/path contracts before any tensor imports."""
from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile
import unittest
from bootstrap import bootstrap, validate_report, BootstrapError

class BootstrapContracts(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name).resolve()/'STEP_S';self.root.mkdir()
        for name in ('reports','configs','upstream','models','video_code'):(self.root/name).mkdir()
        config={'stage':'STEP_S',**{name:str(self.root/name) for name in ('upstream','models','video_code')}}
        (self.root/'config.json').write_text(json.dumps(config))
        (self.root/'configs/execution.json').write_text(json.dumps({'stage':'STEP_S','method':'STEP','expected_steps':40,'expected_forwards':80,'adapter_enabled':False,'alg':False,'manual_rope_override':False,'b029_gate':False,'replace_flag':True}))
        (self.root/'freeze.json').write_text(json.dumps({'files':{}}))
    def tearDown(self):self.temp.cleanup()
    def test_missing_parent_is_explicitly_set(self):
        env={};r=bootstrap(self.root,env);self.assertEqual(env['B007E_LOADER_REPORT'],str(self.root/'reports/loader.json'));self.assertEqual(env['HF_HUB_OFFLINE'],'1');self.assertFalse(Path(r.loader_report).exists())
    def test_stale_parent_is_replaced(self):
        env={'B007E_LOADER_REPORT':'/old/loader.json','HF_HUB_OFFLINE':'0'};bootstrap(self.root,env);self.assertEqual(env['B007E_LOADER_REPORT'],str(self.root/'reports/loader.json'));self.assertEqual(env['TRANSFORMERS_OFFLINE'],'1')
    def test_unbootstrapped_missing_rejected(self):
        with self.assertRaises(BootstrapError):validate_report(self.root,{})
    def test_outside_rejected(self):
        with self.assertRaises(BootstrapError):validate_report(self.root,{'B007E_LOADER_REPORT':'/tmp/loader.json'})
    def test_collision_preserved(self):
        p=self.root/'reports/loader.json';p.write_text('preserve')
        with self.assertRaises(BootstrapError):bootstrap(self.root,{})
        self.assertEqual(p.read_text(),'preserve')
    def test_unwritable_rejected(self):
        p=self.root/'reports';p.chmod(0o555)
        try:
            with self.assertRaises(BootstrapError):bootstrap(self.root,{})
        finally:p.chmod(0o755)
    def test_stage_mismatch(self):
        (self.root/'config.json').write_text(json.dumps({'stage':'CONTROL_D'}))
        with self.assertRaises(BootstrapError):bootstrap(self.root,{})
    def test_report_parent_missing(self):
        (self.root/'reports').rmdir()
        with self.assertRaises(BootstrapError):bootstrap(self.root,{})
    def test_worker_entrypoint_no_imports(self):
        env=os.environ.copy();env.pop('B007E_LOADER_REPORT',None)
        command=[sys.executable,str(Path(__file__).with_name('worker.py')),str(self.root),'--preflight-only']
        result=subprocess.run(command,env=env,text=True,capture_output=True,check=True)
        r=json.loads(result.stdout);self.assertFalse(r['torch_imported']);self.assertFalse(r['loader_report_created']);self.assertFalse((self.root/'reports/worker-attempt.json').exists());self.assertEqual(list((self.root/'reports').iterdir()),[])
    def test_worker_stale_parent(self):
        env={**os.environ,'B007E_LOADER_REPORT':'/prior/stage/loader.json'}
        result=subprocess.run([sys.executable,str(Path(__file__).with_name('worker.py')),str(self.root),'--preflight-only'],env=env,text=True,capture_output=True,check=True)
        self.assertEqual(json.loads(result.stdout)['bootstrap']['loader_report'],str(self.root/'reports/loader.json'))
if __name__=='__main__':unittest.main()
