"""Regression: public source nested under private must survive private dedup rules."""
from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile


class PublicSnapshotTest(unittest.TestCase):
    def test_public_copy_survives_private_exclusion(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            private = root / 'private'
            public = private / 'public_snapshot/experiment'
            public.mkdir(parents=True)
            (private / "CURRENT_STATE.md").write_text("fixture state\n")
            for name in ('PLAN.md', 'RESULTS.md', 'REPRODUCE.md'):
                (public / name).write_text(name + '\n')
            archive = root / 'review.zip'
            subprocess.run([sys.executable, str(Path(__file__).with_name('package_review.py')), str(private), str(public), str(archive), '--exclude', 'public_snapshot/experiment/*=Included-under-public/experiment'], check=True, capture_output=True)
            with zipfile.ZipFile(archive) as z:
                names = set(z.namelist())
                for name in ('PLAN.md', 'RESULTS.md', 'REPRODUCE.md'):
                    self.assertIn('public/experiment/' + name, names)
                    self.assertNotIn('private/public_snapshot/experiment/' + name, names)
                self.assertIsNone(z.testzip())
                manifest = json.loads(z.read('MANIFEST.json'))
                self.assertEqual(len(manifest['payload']), 4)
                self.assertEqual(len([r for r in manifest['omitted'] if r['archive_alias'].startswith('private/public_snapshot/experiment/')]), 3)


if __name__ == '__main__':
    unittest.main()
