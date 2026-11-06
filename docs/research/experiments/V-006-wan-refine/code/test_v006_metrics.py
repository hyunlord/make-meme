# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "Pillow", "pytest"]
# ///
"""Global-index alignment fixture: python -m pytest test_v006_metrics.py."""
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
from PIL import Image


def test_raw_metrics_map_local_frames_to_global_input(tmp_path: Path) -> None:
    # Given matching masks with differing output track IDs and local indices.
    repo_experiments = Path(__file__).resolve().parents[2]
    old_scene = json.loads((repo_experiments / 'V-005-leg-sharpness/V005_SCENE_CONFIG.json').read_text())
    scene = {'common': {'resolution': [60, 40]}, 'refine_window': {'segment_frames': [2, 4]},
             'measurement_policy': old_scene['measurement_policy'],
             'measurement_extension': {'source_track': 0, 'kick_direction_frames_inclusive': [2, 4]}}
    scene['measurement_policy']['master_size'] = [60, 40]
    scene['measurement_policy']['window_inclusive'] = [3, 3]
    inherited = {'scene': {'casting_track_indices': {'Lab': 0, 'IG': 1},
        'reflection_rule': {'x_overlap_min_frac_of_narrower': .5, 'lower_top_below_upper_bottom_minus_px': 1}},
        'anchor_generation': {'resolution_master': [60, 40], 'gates': {
            'G1_real_dog_count': {'equals': 2}, 'G2_centroid_shift_max_frac_width': .08,
            'G3_Lab_bbox_height_ratio': [.85, 1.6], 'G4_IG_bbox_height_ratio': [.7, 1.3],
            'G6_upright_aspect_ratio_vs_source': [.8, 1.25], 'G6_upper_bound_is_failure': False,
            'G5_dilation_px': 2, 'G5_background_mae_max': 12}}, 'sam_settings': {'min_area_fraction': .005}}
    for name, value in [('scene.json', scene), ('inherited.json', inherited)]:
        (tmp_path / name).write_text(json.dumps(value))
    for name, count, tracks in [('source', 5, [0, 1]), ('output', 3, [7, 9])]:
        folder = tmp_path / name
        folder.mkdir()
        rows = []
        for index in range(count):
            for track, left in zip(tracks, [35, 5]):
                mask = np.zeros((40, 60), dtype=np.uint8)
                mask[5:30, left:left+12] = 255
                Image.fromarray(mask).save(folder / f'{index:03d}-track-{track:02d}.png')
            rows.append({'index': index, 'objects': [{'track_index': t, 'present': True} for t in tracks]})
            Image.new('RGB', (60, 40), (40, 40, 40)).save(folder / f'{index:03d}.png')
        (folder / 'summary.json').write_text(json.dumps({'frame_count': count, 'coordinate_size': [60, 40], 'frames': rows}))
    baseline = {'casting': {'Lab': 0, 'IG': 1}, 'frames': [{'frame': i, 'actual_tracks': [0, 1]} for i in range(5)]}
    (tmp_path / 'base.json').write_text(json.dumps(baseline))
    runtime = {'v004_code': str(repo_experiments / 'V-004-scaled-motion/code'),
               'v005_code': str(repo_experiments / 'V-005-leg-sharpness/code'),
               'inherited_scene': str(tmp_path / 'inherited.json'),
               'source_summary': str(tmp_path / 'source/summary.json'),
               'output_summary': str(tmp_path / 'output/summary.json'),
               'input_summary': str(tmp_path / 'source/summary.json'),
               'scaled_summary': str(tmp_path / 'source/summary.json'),
               'input_base_metrics': str(tmp_path / 'base.json'), 'refined_frames': str(tmp_path / 'output')}
    (tmp_path / 'runtime.json').write_text(json.dumps(runtime))
    target = tmp_path / 'metrics.json'
    # When the actual metrics CLI consumes three local output frames.
    subprocess.run([sys.executable, str(Path(__file__).with_name('v006_metrics.py')),
                    str(tmp_path / 'scene.json'), str(tmp_path / 'runtime.json'), str(target)], check=True, capture_output=True)
    # Then global mapping and non-assumed output casting preserve exact-mask scores.
    result = json.loads(target.read_text())
    assert [row['frame'] for row in result['frames']] == [2, 3, 4]
    assert [row['local_frame'] for row in result['frames']] == [0, 1, 2]
    assert result['casting'] == {'Lab': 7, 'IG': 9}
    assert result['input_mask_iou']['mean'] == 1
    assert result['scaled_iou']['mean'] == 1
    assert result['summary']['semi_transparency_ratio']['window']['total'] == 1
    assert result['summary']['semi_transparency_ratio']['outside']['total'] == 2
