"""CPU contract tests; no model imports or GPU work."""
import importlib.util
from pathlib import Path
import sys
import unittest

MODULE = Path(__file__).with_name('ltx_entry.py')


class ConditioningTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location('ltx_entry', MODULE)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        self.module = module

    def test_replace_uses_nearest_accepted_anchor_and_records_offset(self):
        anchors = [self.module.Anchor(0, Path('/a')), self.module.Anchor(12, Path('/b')), self.module.Anchor(24, Path('/c'))]
        plan = self.module.image_plan(anchors, 'replace', [0, 17], 1.0, 8)
        self.assertEqual([(x.frame, x.source_frame, x.offset) for x in plan], [(0, 0, 0), (17, 12, -5)])

    def test_guide_preserves_arbitrary_pixel_frame(self):
        plan = self.module.image_plan([self.module.Anchor(0, Path('/a')), self.module.Anchor(12, Path('/b'))], 'guide', [], 1.0, 8)
        self.assertEqual([(x.frame, x.binding) for x in plan], [(0, 'auto'), (12, 'guide')])

    def test_replace_rejects_noncausal_pixel_frame(self):
        with self.assertRaises(ValueError):
            self.module.image_plan([self.module.Anchor(0, Path('/a'))], 'replace', [12], 1.0, 8)

    def test_duplicate_anchor_frames_rejected(self):
        with self.assertRaises(ValueError):
            self.module.image_plan([self.module.Anchor(0, Path('/a')), self.module.Anchor(0, Path('/b'))], 'guide', [], 1.0, 8)


if __name__ == '__main__':
    unittest.main()
