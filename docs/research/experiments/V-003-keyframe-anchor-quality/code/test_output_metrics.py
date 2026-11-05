"""CPU contracts: no model imports or inference."""
import unittest
import tempfile
import json
from pathlib import Path
from PIL import Image
from dataclasses import replace
import numpy as np
from anchor_gates import Policy, Row
from post_composite import Geometry, Instance
from output_metrics import bind, descriptors, masked_ssim, silhouette_score, run


class MetricsTests(unittest.TestCase):
    def test_missing_is_zero_only_in_all_frame_score(self):
        mask = np.ones((8, 8), dtype=bool)
        self.assertEqual(silhouette_score(mask, None), (None, 0.0))
        self.assertEqual(silhouette_score(~mask, None), (None, None))
        self.assertEqual(silhouette_score(mask, mask), (1.0, 1.0))

    def test_ssim_identity_difference_empty(self):
        a = np.arange(16*16*3, dtype=float).reshape(16, 16, 3) % 256
        region = np.ones((16, 16), dtype=bool)
        self.assertAlmostEqual(masked_ssim(a, a, region), 1.0)
        self.assertLess(masked_ssim(a, 255-a, region), .5)
        self.assertIsNone(masked_ssim(a, a, ~region))

    def test_native_bbox_returns_canonical_crop_offset(self):
        mask = np.zeros((640, 1152), dtype=bool)
        mask[0:90, 90:180] = True
        row = descriptors([Instance(4, mask)], Geometry((1280, 720), (1152, 640)))[0]
        self.assertAlmostEqual(row.bbox[0], 100)
        self.assertAlmostEqual(row.bbox[1], 4/0.9)
        self.assertAlmostEqual(row.bbox[3]-row.bbox[1], 100)

    def test_end_to_end_missing_body_and_background(self):
        config = json.loads((Path(__file__).parents[1]/'V003_SCENE_CONFIG.json').read_text())
        config['anchor_generation']['resolution_master'] = [100, 100]
        config['generation'].update(resolution=[100, 100], frames=2)
        config['scene']['reflection_rule']['lower_top_below_upper_bottom_minus_px'] = 4
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ('source', 'raw', 'post', 'sam'):
                (root/name).mkdir()
            (root/'post/regions').mkdir()
            frames = []
            for index in range(2):
                original = np.full((100, 100, 3), 80, dtype=np.uint8)
                Image.fromarray(original).save(root/'source'/f'{index:03d}.png')
                Image.fromarray(original+index*10).save(root/'raw'/f'{index:03d}.png')
                Image.fromarray(original).save(root/'post'/f'{index:03d}.png')
                region = np.zeros((100, 100), dtype=np.uint8)
                objects = []
                for track, x in enumerate((10, 60)):
                    mask = np.zeros((100, 100), dtype=np.uint8)
                    mask[20:60, x:x+20] = 255
                    region |= mask
                    Image.fromarray(mask).save(root/'sam'/f'{index:03d}-track-{track:02d}.png')
                    objects.append({'present': True, 'track_index': track})
                Image.fromarray(region).save(root/'post/regions'/f'{index:03d}.png')
                frames.append({'index': index, 'objects': objects})
            summary = {'coordinate_size': [100, 100], 'frames': frames}
            (root/'sam/source.json').write_text(json.dumps(summary))
            summary['frames'][1]['objects'][1]['present'] = False
            (root/'sam/output.json').write_text(json.dumps(summary))
            (root/'scene.json').write_text(json.dumps(config))
            result = run(root/'scene.json', {
                'source_frames': str(root/'source'), 'raw_frames': str(root/'raw'),
                'post_frames': str(root/'post'), 'source_summary': str(root/'sam/source.json'),
                'output_summary': str(root/'sam/output.json')})
            self.assertEqual(result['count_matches_fraction'], .5)
            self.assertEqual(result['roles']['IG']['upright_lower_bound_fraction'], .5)
            self.assertEqual(result['roles']['IG']['iou_all_frame'], .5)
            self.assertEqual(result['background']['post_over_raw'], 0)
            self.assertIsNone(result['background']['raw_over_source'])
            self.assertIsNone(result['background']['post_over_source'])
            # A missing first-frame body makes cast-dependent metrics inconclusive.
            summary['frames'][0]['objects'][1]['present'] = False
            summary['frames'][1]['objects'][1]['present'] = True
            (root/'sam/output.json').write_text(json.dumps(summary))
            unbound = run(root/'scene.json', {
                'source_frames': str(root/'source'), 'raw_frames': str(root/'raw'),
                'post_frames': str(root/'post'), 'source_summary': str(root/'sam/source.json'),
                'output_summary': str(root/'sam/output.json')})
            self.assertEqual(unbound['casting_status'], 'CASTING_UNESTABLISHED')
            self.assertEqual(unbound['count_matches_fraction'], .5)
            self.assertTrue(all(value is None for value in unbound['roles']['IG'].values()))
            self.assertIsNone(unbound['frames'][1]['roles']['IG']['iou_all_frame'])
            self.assertIsNone(unbound['frames'][1]['roles']['IG']['upright_lower_bound'])
            # Nonzero source flicker gives finite raw/source and post/source ratios.
            Image.fromarray(np.full((100, 100, 3), 85, dtype=np.uint8)).save(root/'source/001.png')
            ratios = run(root/'scene.json', {
                'source_frames': str(root/'source'), 'raw_frames': str(root/'raw'),
                'post_frames': str(root/'post'), 'source_summary': str(root/'sam/source.json'),
                'output_summary': str(root/'sam/output.json')})
            self.assertEqual(ratios['background']['source_mean'], 5)
            self.assertEqual(ratios['background']['raw_over_source'], 2)
            self.assertEqual(ratios['background']['post_over_source'], 0)
            self.assertEqual(result['quality'], 'HUMAN_REVIEW_PENDING')

    def test_binding_rejects_geometric_tie(self):
        policy = Policy((100, 100), {'A': 0, 'B': 1}, .5, 4, 2, .08,
                        {'A': (.8, 1.6), 'B': (.7, 1.3)}, (.8, 1.25), False, 2, 12)
        source = {0: Row(0, True, (0, 0, 10, 10), (10, 10), 100),
                  1: Row(1, True, (20, 0, 30, 10), (30, 10), 100)}
        output = {2: Row(2, True, (0, 0, 10, 10), (20, 0), 100),
                  3: Row(3, True, (20, 0, 30, 10), (20, 20), 100)}
        self.assertIsNone(bind(source, output, [2, 3], policy))
        output[2] = replace(output[2], center=(10, 10))
        self.assertEqual(bind(source, output, [2, 3], policy), {'A': 2, 'B': 3})


if __name__ == '__main__':
    unittest.main()
