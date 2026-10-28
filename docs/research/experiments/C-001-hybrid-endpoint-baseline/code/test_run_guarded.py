"""CPU tests of shared path validation and same-PID target entry, without systemd/GPU."""
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import run_guarded


class GuardAdapterTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name).resolve()
        (self.root/'reports').mkdir()
        (self.root/'configs').mkdir()
        self.guard = self.root/'guard'
        self.guard.mkdir()
        for name in ('supervisor.py','safety.py','policy.py','memory.py'):
            (self.guard/name).write_text('')
        self.script = self.root/'target.py'
        self.output = self.root/'result.json'
        self.script.write_text(f'import os,json\nfrom pathlib import Path\nPath({str(self.output)!r}).write_text(json.dumps({{"pid":os.getpid(),"cwd":os.getcwd()}}))\n')
        self.checkpoint = self.root/'checkpoint'
        self.checkpoint.mkdir()
        self.config = {'python':sys.executable,'cwd':str(self.root),'script':str(self.script),
                       'args':['--cpu-only'],'environment':{},'checkpoint':str(self.checkpoint),
                       'input_paths':[str(self.script)],'output_paths':[str(self.output)],
                       'guard_code':str(self.guard),'stage':'CPU','unit':'make-meme-c001-cpu-test',
                       'deadline_epoch':9999999999,'allowed_gpu_processes':{},
                       'research_lock':str(self.root/'lock'),'memory_budget_state':str(self.root/'memory.json'),
                       'worker_max_seconds':60,'cpu_route_receipt':''}
        self.freeze()

    def tearDown(self):
        self.temporary.cleanup()

    def freeze(self):
        (self.root/'config.json').write_text(json.dumps(self.config))
        paths = [self.root/'config.json',self.script,Path(run_guarded.__file__).resolve()]
        (self.root/'freeze.json').write_text(json.dumps({'files':{str(path):hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}}))

    def test_absolute_shared_configuration_passes(self):
        job = run_guarded.validate(str(self.root))
        self.assertTrue(job.cpu_only)
        self.assertEqual(job.root,self.root)

    def test_relative_stage_and_script_fail(self):
        with self.assertRaisesRegex(RuntimeError,'ABSOLUTE_PATH_REQUIRED'):
            run_guarded.validate('relative-stage')
        self.config['script']='target.py'
        self.freeze()
        with self.assertRaisesRegex(RuntimeError,'ABSOLUTE_PATH_REQUIRED'):
            run_guarded.validate(str(self.root))

    def test_tampered_script_fails_freeze(self):
        self.script.write_text('raise RuntimeError("changed")')
        with self.assertRaisesRegex(RuntimeError,'FREEZE_MISMATCH'):
            run_guarded.validate(str(self.root))

    def test_cpu_flag_only_does_not_change_route(self):
        cpu = run_guarded.validate(str(self.root))
        self.config['args']=[]
        self.freeze()
        heavy = run_guarded.validate(str(self.root))
        self.assertEqual(cpu.route_sha256,heavy.route_sha256)
        self.assertFalse(heavy.cpu_only)

    def test_worker_uses_registered_pid_and_validated_cwd(self):
        job = run_guarded.validate(str(self.root))
        (self.root/'reports/worker-identity.json').write_text(json.dumps({'pid':os.getpid()}))
        (self.root/'reports/start-safety.json').write_text(json.dumps({'decision':'CLEAR'}))
        previous = Path.cwd()
        try:
            with patch('run_guarded.load_c001_policy',return_value={}),patch.object(sys,'argv',sys.argv.copy()):
                run_guarded.worker(job)
        finally:
            os.chdir(previous)
        result=json.loads(self.output.read_text())
        self.assertEqual(result,{'pid':os.getpid(),'cwd':str(self.root)})

    def test_worker_rejects_wrong_registered_pid(self):
        job=run_guarded.validate(str(self.root))
        (self.root/'reports/worker-identity.json').write_text(json.dumps({'pid':os.getpid()+1}))
        with patch('run_guarded.load_c001_policy',return_value={}):
            with self.assertRaisesRegex(RuntimeError,'REGISTERED_WORKER_PID_MISMATCH'):
                run_guarded.worker(job)


if __name__=='__main__':
    unittest.main()
