"""E2-only memory admission boundaries; no systemd or GPU execution."""
import hashlib
import json
from pathlib import Path
import unittest
import tempfile
import supervisor
from safety import start_decision

GIB = 2**30

class E2Amendment(unittest.TestCase):
    def test_start_requires_at_least_112_gib(self):
        self.assertEqual(start_decision('CLEAR',112-1/GIB,100),'START_HEADROOM_NOT_MET')
        self.assertEqual(start_decision('CLEAR',112,100),'CLEAR')

    def test_existing_blocker_and_deadline_are_preserved(self):
        self.assertEqual(start_decision('OBSERVATION_FAILED',120,100),'OBSERVATION_FAILED')
        self.assertEqual(start_decision('START_OBSERVATION_INCOMPLETE',120,100),'START_OBSERVATION_INCOMPLETE')
        self.assertEqual(start_decision('CLEAR',120,60),'DEADLINE')

    def test_worker_cap_is_100_gib_at_admitted_headroom(self):
        self.assertEqual(supervisor.worker_memory_cap(112*GIB),100*GIB)
        self.assertEqual(supervisor.worker_memory_cap(120*GIB),100*GIB)

    def test_live_worker_rss_highwater_bytes(self):
        with tempfile.TemporaryDirectory() as temp:
            proc=Path(temp);folder=proc/'123';folder.mkdir()
            (folder/'status').write_text('Name: worker\nState: R (running)\nVmHWM: 123456 kB\n')
            self.assertEqual(supervisor.worker_rss_highwater(123,proc),123456*1024)

    def test_absent_or_zombie_worker_rss_is_unavailable(self):
        with tempfile.TemporaryDirectory() as temp:
            proc=Path(temp);folder=proc/'123';folder.mkdir()
            self.assertIsNone(supervisor.worker_rss_highwater(123,proc))
            (folder/'status').write_text('Name: worker\nState: Z (zombie)\n')
            self.assertIsNone(supervisor.worker_rss_highwater(123,proc))

    def test_live_worker_missing_rss_fails_observation(self):
        with tempfile.TemporaryDirectory() as temp:
            proc=Path(temp);folder=proc/'123';folder.mkdir()
            (folder/'status').write_text('Name: worker\nState: R (running)\n')
            with self.assertRaises(ValueError):
                supervisor.worker_rss_highwater(123,proc)

    def test_old_guard_files_remain_byte_identical(self):
        here=Path(__file__).resolve().parent
        for row in json.loads((here/'ORIGINAL_HASHES.json').read_text()):
            self.assertEqual(hashlib.sha256((here.parent/'guard'/row['file']).read_bytes()).hexdigest(),row['original_sha256'])

if __name__=='__main__': unittest.main()
