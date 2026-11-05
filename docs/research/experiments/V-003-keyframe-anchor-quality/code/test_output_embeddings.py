"""No torch/transformers import: saved-crop and merge contracts only."""
import json
from pathlib import Path
import tempfile
import unittest
from PIL import Image
from embed_images import Item, crop_bounds, crops
from output_embedding_metrics import build, merge


class OutputEmbeddingTests(unittest.TestCase):
    def test_native_crop_missing_and_unestablished_cast(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            summary = {'coordinate_size': [100, 60], 'frames': [{'index': 1, 'objects': [
                {'track_index': 7, 'present': True, 'bbox': [10, 5, 30, 45]},
                {'track_index': 8, 'present': True, 'bbox': [40, 5, 60, 45]}]}]}
            (root/'sam.json').write_text(json.dumps(summary))
            report = {'casting': {'A': 7, 'B': 8}, 'frames': [{'frame': 1, 'actual_tracks': [7]}]}
            (root/'metrics.json').write_text(json.dumps(report))
            Image.new('RGB', (100, 60)).save(root/'frame.png')
            item = Item('output', root/'frame.png', root/'sam.json', 1, root/'metrics.json', True)
            self.assertEqual(crop_bounds(item, ('A', 'B'), (200, 120)), {'A': (10, 5, 30, 45)})
            images = crops(item, ('A', 'B'), (200, 120))
            self.assertEqual([image.size for image in images], [(20, 40)])
            for image in images:
                image.close()
            report['casting'] = None
            (root/'metrics.json').write_text(json.dumps(report))
            self.assertEqual(crop_bounds(item, ('A', 'B'), (200, 120)), {})
            self.assertEqual(crops(item, ('A', 'B'), (200, 120)), [])

    def test_builder_and_nullable_merge(self):
        with tempfile.TemporaryDirectory() as temp:
            scene = Path(temp)/'scene.json'
            scene.write_text(json.dumps({'generation': {'frames': 2}, 'scene': {'casting_track_indices': {'A': 0}}}))
            manifest = {'scene_config': str(scene), 'model_path': '/existing', 'device': 'cpu',
                        'cpu_threads': 1, 'batch_size': 2, 'reference_id': 'anchor0', 'embedding_output': '/report',
                        'anchors': [{'id': 'anchor0', 'frame': 0, 'image': '/anchor', 'summary': '/sam',
                                     'casting_report': '/gates', 'frame_index': 0}],
                        'outputs': [{'id': 'K1', 'raw_frames': '/frames', 'summary': '/sam', 'metrics': '/metrics'}]}
            runtime = build(manifest)
            self.assertEqual(len(runtime['items']), 3)
            self.assertEqual(runtime['items'][1]['comparison_id'], 'anchor0')
            self.assertIsNone(runtime['items'][2]['comparison_id'])
            report = {'reference_id': 'anchor0', 'feature': 'test', 'model_config_sha256': 'hash', 'items': [
                {'id': 'K1:frame:0', 'cosine_vs_reference': {'A': .7}, 'comparison_id': 'anchor0', 'cosine_vs_comparison': {'A': .7}},
                {'id': 'K1:frame:1', 'cosine_vs_reference': {'A': None}, 'comparison_id': None, 'cosine_vs_comparison': {'A': None}}]}
            merged = merge(manifest, report)
            stats = merged['outputs']['K1']['anchor0_similarity']['A']
            self.assertEqual(stats, {'minimum': .7, 'mean': .7, 'observed_frames': 1, 'total_frames': 2})
            self.assertEqual(len(merged['outputs']['K1']['keyframes']), 1)
            self.assertEqual(merged['quality'], 'HUMAN_REVIEW_PENDING')


if __name__ == '__main__':
    unittest.main()
