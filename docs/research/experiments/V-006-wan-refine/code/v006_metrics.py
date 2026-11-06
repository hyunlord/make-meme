# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "scipy", "Pillow"]
# ///
"""CPU metrics: existing Python v006_metrics.py SCENE PRIVATE_RUNTIME OUTPUT.

Runtime: v004_code, v005_code, inherited_scene, source_summary, output_summary,
input_summary, input_base_metrics, scaled_summary, refined_frames. Output uses
global scene indices; SAM/refined PNG indices remain local to the refine clip.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import numpy as np


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    scene_path, runtime_path, destination = map(Path, sys.argv[1:])
    scene, runtime = json.loads(scene_path.read_text()), json.loads(runtime_path.read_text())
    if destination.exists():
        raise FileExistsError(destination)
    sys.path[:0] = [runtime['v004_code'], runtime['v005_code']]
    from anchor_gates import Policy, classify
    from leg_core import frame_metrics, stats, summarize
    from leg_io import Canvas, read_masks, read_policy, rgb_master
    from output_metrics import bind, descriptors, silhouette_score
    from post_composite import Geometry, read_instances
    from scaled_output_metrics import compare_masks

    inherited = Path(runtime['inherited_scene'])
    base_policy = Policy.read(inherited)
    policy = read_policy(scene_path)
    native = tuple(scene['common']['resolution'])
    geo, canvas = Geometry(policy.master_size, native), Canvas(policy.master_size, native)
    first, last = scene['refine_window']['segment_frames']
    source_path, output_path = Path(runtime['source_summary']), Path(runtime['output_summary'])
    scaled_path, input_path = Path(runtime['scaled_summary']), Path(runtime['input_summary'])
    input_base = json.loads(Path(runtime['input_base_metrics']).read_text())
    input_rows = {row['frame']: row for row in input_base['frames']}
    output_summary = json.loads(output_path.read_text())
    if output_summary['frame_count'] != last - first + 1:
        raise RuntimeError('Output SAM length does not match refinement window')
    if output_summary['coordinate_size'] != list(native):
        raise RuntimeError('Output SAM geometry mismatch')
    minimum = json.loads(inherited.read_text())['sam_settings']['min_area_fraction']
    role = policy.role
    source_track = scene['measurement_extension']['source_track']
    input_track = input_base['casting'].get(role) if input_base['casting'] else None
    valid = canvas.valid()
    casting = None
    frames = []
    for local, index in enumerate(range(first, last + 1)):
        source = descriptors(read_instances(source_path, index, geo), geo)
        actual_items = read_instances(output_path, local, geo)
        outputs = descriptors(actual_items, geo)
        source_by_track, output_by_track = {r.track: r for r in source}, {r.track: r for r in outputs}
        actual, reflections = classify(outputs, base_policy)
        actual = [t for t in actual if output_by_track[t].area / np.prod(policy.master_size) >= minimum]
        if local == 0:
            casting = bind(source_by_track, output_by_track, actual, base_policy)
        target = casting.get(role) if casting else None
        native_masks = {item.track: item.mask for item in actual_items}
        master_masks = read_masks(output_path, local, canvas)
        detected = target is not None and target in actual
        body = master_masks.get(target) if detected else None
        reflection = np.zeros_like(valid)
        for track in reflections:
            if track in master_masks:
                reflection |= master_masks[track]
        pixels = rgb_master(Path(runtime['refined_frames']) / f'{local:03d}.png', canvas)
        row = dict(frame_metrics(pixels, body, reflection, valid, policy))
        row.update(frame=index, local_frame=local, actual_tracks=actual, reflection_tracks=reflections,
                   count_matches=len(actual) == base_policy.count, lab_bbox_master=None,
                   lab_mask_iou_vs_input=None, input_iou_status='MISSING_MASK')
        if body is not None and body.any():
            y, x = np.nonzero(body)
            row['lab_bbox_master'] = [int(x.min()), int(y.min()), int(x.max() + 1), int(y.max() + 1)]
        input_masks = {item.track: item.mask for item in read_instances(input_path, index, geo)}
        input_detected = input_track is not None and input_track in input_rows[index]['actual_tracks']
        input_body = input_masks.get(input_track) if input_detected else None
        predicted = native_masks.get(target) if detected else None
        observed, penalized = silhouette_score(input_body, predicted) if input_body is not None else (None, None)
        row.update(lab_mask_iou_vs_input=observed, lab_mask_iou_vs_input_all_frame=penalized,
                   input_iou_status='MEASURED' if observed is not None else 'MISSING_MASK')
        scaled = {item.track: item.mask for item in read_instances(scaled_path, index, geo)}
        row['scaled_motion'] = compare_masks(scaled.get(source_track), predicted, casting_established=casting is not None)
        nearest = bind(source_by_track, output_by_track, actual, base_policy)
        row['geometric_cast_opposition_proxy'] = nearest != casting if nearest and casting else None
        frames.append(row)
    kick_first, kick_last = scene['measurement_extension']['kick_direction_frames_inclusive']
    kick = [row['scaled_motion'] for row in frames if kick_first <= row['frame'] <= kick_last]
    report = {'quality': 'HUMAN_REVIEW_PENDING', 'temporal': 'UNVERIFIED', 'automatic_ranking': False,
              'casting': casting, 'casting_status': 'ESTABLISHED' if casting else 'UNESTABLISHED',
              'frame_count': len(frames), 'global_frame_range': [first, last], 'frames': frames,
              'coordinate_basis': list(policy.master_size), 'native_size': list(native),
              'geometry': {'resized_before_crop': list(canvas.resized), 'crop_offset': list(canvas.offset)},
              'measurement_policy': scene['measurement_policy'], 'summary': summarize(frames, policy),
              'input_mask_iou': stats([row['lab_mask_iou_vs_input'] for row in frames]),
              'input_mask_iou_missing_penalty': stats([row['lab_mask_iou_vs_input_all_frame'] for row in frames]),
              'scaled_iou': stats([row['scaled_motion']['iou_observed'] for row in frames]),
              'scaled_iou_missing_penalty': stats([row['scaled_motion']['iou_all_frame'] for row in frames]),
              'kick_direction': stats([row['quadrant_agreement_observed'] for row in kick]),
              'kick_direction_missing_penalty': stats([row['quadrant_agreement_window_penalty'] for row in kick]),
              'count_matches_fraction': sum(row['count_matches'] for row in frames) / len(frames),
              'identity_embedding': 'SEPARATE_WORKER_NOT_MEASURED_HERE',
              'scene_sha256': digest(scene_path), 'runtime_sha256': digest(runtime_path),
              'inputs_sha256': {key: digest(Path(runtime[key])) for key in
                               ('source_summary', 'output_summary', 'input_summary', 'input_base_metrics', 'scaled_summary')},
              'limitations': ['Gray ratio is not physical transparency; Laplacian may measure noise/texture.',
                              'Outside-window stats use only the remaining actual refined frames.',
                              'Direction is inherited topmost-mask-point proxy, not anatomical leg tracking.',
                              'IoU and direction do not establish preserved dance motion.']}
    temporary = destination.with_suffix('.tmp')
    temporary.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    if json.loads(temporary.read_text()) != report:
        raise RuntimeError('Metric readback mismatch')
    temporary.rename(destination)


if __name__ == '__main__':
    main()
