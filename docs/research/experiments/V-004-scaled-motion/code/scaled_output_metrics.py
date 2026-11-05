# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy", "Pillow", "scipy"]
# ///
"""CPU-only added metrics; never changes existing metrics or ranks variants.

CLI: scaled_output_metrics.py SCENE PRIVATE_RUNTIME OUTPUT.json
Runtime: base_metrics, output_summary, scaled_summary, scaled_control_report.
Consume comparison-time RAW SAM (including decimated S3), fixed base casting,
and scaled_control.py's scaled_masks/summary.json. All paths remain private.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import numpy as np
from numpy.typing import NDArray

from output_metrics import mean, silhouette_score
from post_composite import Geometry, read_instances
from scaled_geometry import direction


QUADRANTS = {'UPPER_LEFT', 'UPPER_RIGHT', 'LOWER_LEFT', 'LOWER_RIGHT'}


def compare_masks(source: NDArray[np.bool_] | None, output: NDArray[np.bool_] | None,
                  *, casting_established: bool, output_artifact_available: bool = True) -> dict:
    source_direction = direction(source) if source is not None else None
    output_direction = direction(output) if output is not None else None
    comparable = bool(source_direction and output_direction and
                      source_direction['quadrant'] in QUADRANTS and output_direction['quadrant'] in QUADRANTS)
    observed, penalized = None, None
    agreement = None
    if casting_established and output_artifact_available and source is not None and source.any():
        observed, penalized = silhouette_score(source, output)
        if comparable:
            agreement = source_direction['quadrant'] == output_direction['quadrant']
    return {'source_direction': source_direction, 'output_direction': output_direction,
            'iou_observed': observed, 'iou_all_frame': penalized,
            'quadrant_comparable': comparable if casting_established else False,
            'quadrant_agreement_observed': agreement,
            'quadrant_agreement_window_penalty': bool(agreement) if penalized is not None else None,
            'output_detected': output is not None and bool(output.any()),
            'output_artifact_available': output_artifact_available}


def masks(summary: Path, index: int, geometry: Geometry) -> dict[int, NDArray[np.bool_]] | None:
    try:
        return {item.track: item.mask for item in read_instances(summary, index, geometry)}
    except (FileNotFoundError, StopIteration):
        return None


def run(scene_path: Path, runtime: dict) -> dict:
    scene = json.loads(scene_path.read_text())
    base = json.loads(Path(runtime['base_metrics']).read_text())
    control = json.loads(Path(runtime['scaled_control_report']).read_text())
    count = scene['scene']['segment']['frames']
    role = scene['scaled_control']['precheck_role']
    source_track = scene['scene']['casting_track_indices'][role]
    first, last = scene['metrics_added']['kick_direction_frames_inclusive']
    if not 0 <= first <= last < count:
        raise ValueError('Configured kick interval outside comparison clip')
    base_rows = {row['frame']: row for row in base['frames']}
    control_rows = {row['frame']: row for row in control['frames']}
    if len(base_rows) != count or set(base_rows) != set(range(count)):
        raise ValueError('Base metrics must cover every comparison frame exactly once')
    if len(base['frames']) != count or len(control['frames']) != count or set(control_rows) != set(range(count)):
        raise ValueError('Duplicate base rows or incomplete control evidence')
    geo = Geometry(tuple(scene['anchor_generation']['resolution_master']), tuple(scene['generation']['resolution']))
    casting = base.get('casting')
    target = casting.get(role) if casting else None
    established = target is not None and base.get('casting_status') == 'ESTABLISHED'
    frames = []
    for index in range(count):
        source = masks(Path(runtime['scaled_summary']), index, geo)
        outputs = masks(Path(runtime['output_summary']), index, geo)
        actual = target in base_rows[index]['actual_tracks'] if established else False
        predicted = outputs.get(target) if outputs is not None and actual else None
        row = compare_masks(source.get(source_track) if source is not None else None, predicted,
                            casting_established=established, output_artifact_available=outputs is not None)
        row.update(frame=index, source_artifact_available=source is not None,
                   kick_window=first <= index <= last,
                   clipping=control_rows[index]['clipping'])
        frames.append(row)
    kick = frames[first:last+1]
    observed = [row['quadrant_agreement_observed'] for row in kick]
    penalty = [row['quadrant_agreement_window_penalty'] for row in kick]
    return {'quality': 'HUMAN_REVIEW_PENDING', 'temporal_review': 'UNVERIFIED',
            'role': role, 'casting': casting, 'casting_status': base.get('casting_status'),
            'geometry': {'master': geo.master, 'measurement_canvas': geo.output},
            'scene_sha256': hashlib.sha256(scene_path.read_bytes()).hexdigest(),
            'inputs_sha256': {key: hashlib.sha256(Path(runtime[key]).read_bytes()).hexdigest() for key in
                             ('base_metrics', 'output_summary', 'scaled_summary', 'scaled_control_report')},
            'definitions': {'iou': 'Visible scaled source body mask vs fixed-cast actual output. Missing detected output gets zero in all-frame mean; unavailable artifacts or casting are null.',
                            'direction': 'Shared scaled_geometry.direction: median x of topmost pixel row relative to bbox center. Four-quadrant comparable mean and full-window missing/axis penalty both reported.',
                            'caveat': 'Topmost point may be head or ear, not a kicking leg. No automatic motion or quality ranking.',
                            'clipping': 'Reused CPU control evidence, not a measurement of generated output clipping.'},
            'frames': frames,
            'scaled_iou': {'observed_mean': mean([r['iou_observed'] for r in frames]),
                           'all_frame_mean': mean([r['iou_all_frame'] for r in frames]),
                           'observed_frames': sum(r['iou_observed'] is not None for r in frames),
                           'evaluated_frames': sum(r['iou_all_frame'] is not None for r in frames), 'total_frames': count},
            'kick_direction': {'frames_inclusive': [first, last], 'observed_agreement_fraction': mean(observed),
                               'window_agreement_with_missing_axis_penalty': mean(penalty),
                               'comparable_frames': sum(v is not None for v in observed),
                               'evaluated_frames': sum(v is not None for v in penalty),
                               'total_window_frames': len(kick)},
            'control_scales': control['scales'], 'precheck_mean_iou': control['precheck_mean_iou'],
            'precheck_notice': control['precheck_notice'], 'automatic_ranking': False}


def main() -> None:
    scene_path, runtime_path, output = map(Path, sys.argv[1:])
    if output.exists():
        raise FileExistsError(output)
    result = run(scene_path, json.loads(runtime_path.read_text()))
    temporary = output.with_suffix('.tmp')
    with temporary.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    json.loads(temporary.read_text())
    temporary.replace(output)


if __name__ == '__main__':
    main()
