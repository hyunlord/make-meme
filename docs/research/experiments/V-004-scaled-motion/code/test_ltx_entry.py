"""CPU contracts only; inherited inference is never imported."""
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import tempfile
import json

spec = importlib.util.spec_from_file_location('v004_ltx', Path(__file__).with_name('ltx_entry.py'))
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


class ConditioningTests(unittest.TestCase):
    def test_doubled_guide_preserves_source_time(self):
        anchors = [module.Anchor(k, Path(f'/a{k}')) for k in (0, 16, 72)]
        plan = module.image_plan(anchors, 'guide', [], 1.0, 8, 2)
        self.assertEqual([(p.frame, p.source_frame, p.binding) for p in plan],
                         [(0, 0, 'auto'), (32, 16, 'guide'), (144, 72, 'guide')])

    def test_replace_and_invalid_multiplier_rejected(self):
        anchors = [module.Anchor(0, Path('/a'))]
        with self.assertRaises(ValueError):
            module.image_plan(anchors, 'replace', [0], 1.0, 8, 1)
        with self.assertRaises(ValueError):
            module.image_plan(anchors, 'guide', [], 1.0, 8, 0)

    def test_full_cpu_config_uses_native_variant_frames(self):
        scene_path = Path(__file__).parents[1]/'V004_SCENE_CONFIG.json'
        scene = json.loads(scene_path.read_text())
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runtime = {'scene_config': str(scene_path), 'variant': 'S3', 'seed': scene['generation']['seeds'][0],
                       'engine_root': str(root), 'ffprobe': '/fake/probe'}
            for name in ('checkpoint', 'upsampler', 'gemma', 'lora', 'canny', 'observer_path'):
                path = root/name
                path.touch()
                runtime[name] = str(path)
            runtime.update(output=str(root/'out.mp4'), receipt=str(root/'receipt.json'))
            runtime['anchors'] = []
            for index in scene['keyframes']['segment_frames']:
                path = root/f'a{index}.png'
                path.touch()
                runtime['anchors'].append({'frame': index, 'path': str(path)})
            path = root/'runtime.json'
            path.write_text(json.dumps(runtime))
            def command(args, **kwargs):
                if 'rev-parse' in args:
                    return scene['generation']['runtime_contract']['engine_commit']+'\n'
                if 'diff' in args:
                    return ''
                width, height = scene['generation']['resolution']
                return json.dumps({'streams': [{'width': width, 'height': height, 'nb_read_frames': '145', 'r_frame_rate': '24/1'}]})
            with patch.object(module.subprocess, 'check_output', side_effect=command):
                cfg = module.load_config(path)
            self.assertEqual(cfg.frames, 145)
            self.assertEqual(cfg.images[-1].frame, 144)
            self.assertTrue(cfg.use_control)
            self.assertNotIn('torch', sys.modules)

    def test_temporal_grid_and_fixed_weight_growth(self):
        self.assertEqual(module.latent_frames(145, 8), 19)
        with self.assertRaises(ValueError):
            module.latent_frames(146, 8)
        small = module.peak_projection(71, 40, 73, 7, 73, 11, 8, 38, 8)
        large = module.peak_projection(71, 40, 73, 7, 145, 11, 8, 38, 8)
        self.assertEqual(small, 80.125)
        self.assertAlmostEqual(large, 84.22)
        self.assertLess(large, 100)
        with self.assertRaises(ValueError):
            module.peak_projection(71, 40, 73, 7, 145, 11, 8, 41, 8)


if __name__ == '__main__':
    unittest.main()
