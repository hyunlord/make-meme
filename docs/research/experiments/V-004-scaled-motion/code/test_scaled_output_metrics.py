import json
from pathlib import Path

import numpy as np
from PIL import Image
import pytest

from scaled_output_metrics import compare_masks, run


def asymmetric():
    mask = np.zeros((8, 8), dtype=bool)
    mask[2:7, 1:6] = True
    mask[1, 1] = True
    return mask


def test_same_and_opposite_direction():
    mask = asymmetric()
    same = compare_masks(mask, mask, casting_established=True)
    assert same['iou_observed'] == 1
    assert same['quadrant_agreement_observed'] is True
    other = compare_masks(mask, np.fliplr(mask), casting_established=True)
    assert other['quadrant_agreement_observed'] is False


def test_missing_vs_unknown_casting_or_artifact():
    mask = asymmetric()
    missing = compare_masks(mask, None, casting_established=True)
    assert missing['iou_observed'] is None
    assert missing['iou_all_frame'] == 0
    assert missing['quadrant_agreement_window_penalty'] is False
    for kwargs in ({'casting_established': False},
                   {'casting_established': True, 'output_artifact_available': False}):
        result = compare_masks(mask, None, **kwargs)
        assert result['iou_all_frame'] is None
        assert result['quadrant_agreement_window_penalty'] is None


def test_axis_is_not_counted_as_quadrant_success():
    mask = np.zeros((8, 8), dtype=bool)
    mask[1:6, 1:6] = True
    result = compare_masks(mask, mask, casting_established=True)
    assert result['source_direction']['quadrant'] == 'UP_AXIS'
    assert result['quadrant_agreement_observed'] is None
    assert result['quadrant_agreement_window_penalty'] is False


def write(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))
    return str(path)


def fixture(tmp_path):
    scene = {'scene': {'segment': {'frames': 3}, 'casting_track_indices': {'Animal': 9}},
             'scaled_control': {'precheck_role': 'Animal'},
             'metrics_added': {'kick_direction_frames_inclusive': [1, 2]},
             'anchor_generation': {'resolution_master': [8, 8]}, 'generation': {'resolution': [8, 8]}}
    scene_path = Path(write(tmp_path/'scene.json', scene))
    base = {'casting': {'Animal': 7}, 'casting_status': 'ESTABLISHED',
            'frames': [{'frame': i, 'actual_tracks': [7] if i < 2 else []} for i in range(3)]}
    control = {'frames': [{'frame': i, 'clipping': [{'track': 9, 'clipped_fraction': 0.1}]} for i in range(3)],
               'scales': {'Animal': 1.2}, 'precheck_mean_iou': 0.6, 'precheck_notice': False}
    runtime = {'base_metrics': write(tmp_path/'base.json', base),
               'scaled_control_report': write(tmp_path/'control.json', control)}
    for key, track in [('scaled_summary', 9), ('output_summary', 7)]:
        folder = tmp_path/key
        summary = {'coordinate_size': [8, 8], 'frames': []}
        for i in range(3):
            objects = [] if key == 'output_summary' and i == 2 else [{'track_index': track, 'present': True}]
            summary['frames'].append({'index': i, 'objects': objects})
            folder.mkdir(exist_ok=True)
            if objects:
                Image.fromarray(asymmetric().astype('uint8')*255).save(folder/f'{i:03d}-track-{track:02d}.png')
        runtime[key] = write(folder/'summary.json', summary)
    return scene_path, runtime


def test_config_driven_window_fixed_cast_and_missing_penalty(tmp_path):
    scene, runtime = fixture(tmp_path)
    result = run(scene, runtime)
    assert result['role'] == 'Animal'
    assert result['scaled_iou']['all_frame_mean'] == pytest.approx(2/3)
    assert result['scaled_iou']['observed_mean'] == 1
    assert result['kick_direction']['total_window_frames'] == 2
    assert result['kick_direction']['observed_agreement_fraction'] == 1
    assert result['kick_direction']['window_agreement_with_missing_axis_penalty'] == 0.5
    assert result['kick_direction']['comparable_frames'] == 1
    assert '/private' not in json.dumps(result)


def test_missing_mask_artifact_not_silently_detection_zero(tmp_path):
    scene, runtime = fixture(tmp_path)
    (Path(runtime['output_summary']).parent/'001-track-07.png').unlink()
    result = run(scene, runtime)
    assert result['frames'][1]['output_artifact_available'] is False
    assert result['frames'][1]['iou_all_frame'] is None
    assert result['scaled_iou']['evaluated_frames'] == 2
