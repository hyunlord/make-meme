# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# Run: existing Python metrics.py /private/config.json /public/metrics.json
"""V-002 CPU-only measurements from completed SAM output and fixed edit masks."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib
import json
import statistics
import sys


from metrics_core import height_ratio, outside_preservation, silhouettes
from output_metrics import Geometry, average, load_frame, match_cast, native_size, object_metrics, transition, visible_support
from anchor_gates import reflection_colors
from reflections import classify


@dataclass(frozen=True, slots=True)
class Config:
    source_summary: Path
    source_frames: Path
    output_summary: Path
    output_frames: Path
    anchor_summary: Path
    anchor_frames: Path
    generation_masks: Path
    geometry: Geometry
    output_fps: float

    @classmethod
    def read(cls, path: Path) -> Config:
        raw = json.loads(path.read_text())
        cfg = cls(*(Path(raw[key]) for key in ('source_summary', 'source_frames', 'output_summary',
                   'output_frames', 'anchor_summary', 'anchor_frames', 'generation_masks')),
                  geometry=raw['geometry'], output_fps=float(raw.get('output_fps', 24)))
        assert cfg.geometry in ('E1', 'E2', 'CANONICAL') and cfg.output_fps == 24
        return cfg


def median(values: list[float]) -> float | None:
    return statistics.median(values) if values else None


def main() -> None:
    config_path, destination = map(Path, sys.argv[1:])
    cfg = Config.read(config_path)
    source, output, anchor = (json.loads(path.read_text()) for path in (cfg.source_summary, cfg.output_summary, cfg.anchor_summary))
    assert all(raw['status'] == 'SAM_ANALYSIS_COMPLETED' for raw in (source, output, anchor)), 'SAM_TECHNICAL_FAILURE_IS_NOT_ZERO_SCORE'
    assert source['coordinate_size'] == anchor['coordinate_size'] == [1280, 720]
    assert output['coordinate_size'] == list(native_size(cfg.geometry))
    source_images, output_images, mask_images, anchor_images = (sorted(folder.glob('*.png')) for folder in
        (cfg.source_frames, cfg.output_frames, cfg.generation_masks, cfg.anchor_frames))
    assert len(source['frames']) == len(source_images) == 73
    assert len(mask_images) in (49, 73) and len(mask_images) >= len(output_images)
    assert len(output['frames']) == len(output_images) and len(output_images) in (49, 73)
    assert len(anchor['frames']) == len(anchor_images) == 1
    af = load_frame(cfg.anchor_summary.parent, anchor_images[0], anchor['frames'][0]['objects'], 0, 'CANONICAL')
    visible = visible_support(cfg.geometry)
    rows = []
    casting = None
    previous_source = previous_output = None
    for index, raw in enumerate(output['frames']):
        assert raw['index'] == source['frames'][index]['index'] == index
        sf = load_frame(cfg.source_summary.parent, source_images[index], source['frames'][index]['objects'], index, 'CANONICAL')
        of = load_frame(cfg.output_summary.parent, output_images[index], raw['objects'], index, cfg.geometry)
        if index == 0:
            casting = match_cast(sf.objects, of.objects)
            anchor_casting = match_cast(sf.objects, af.objects)
        classification = classify(of.objects)
        actual = classification['actual_track_indices']
        errors, lab_ratio, opposite = object_metrics(sf, of, casting)
        score = silhouettes(sf, of, casting, visible)
        roi_count, outside = outside_preservation(sf, of, mask_images[index], visible)
        flicker_pixels = outdiff = srcdiff = None
        if previous_source is not None and previous_output is not None:
            flicker_pixels, outdiff, srcdiff = transition(previous_source, sf, previous_output, of, visible)
        rows.append({'index': index, 'source_timeline_index': 240+index,
                     'classification': classification, 'canonical_objects': of.objects,
                     'actual_count': len(actual), 'actual_two': len(actual) == 2,
                     'actual_two_area_gate': len(actual) == 2 and all(row['area_fraction'] >= .005 for row in of.objects if row['track_index'] in actual),
                     'silhouette_iou': score, 'trajectory_error_px': errors,
                     'lab_height_vs_source': lab_ratio, 'nearest_opposite_assignment': opposite,
                     'reflection_color_reference_only': reflection_colors(of.rgb, of.masks, classification),
                     'outside_mask_pixels': roi_count, 'outside_mask_mae': outside,
                     'background_roi_pixels': flicker_pixels, 'output_background_difference': outdiff,
                     'source_background_difference': srcdiff})
        previous_source, previous_output = sf, of
    by_role = {}
    for role in ('Lab', 'IG'):
        observed = [row['silhouette_iou']['observed'][role] for row in rows if row['silhouette_iou']['observed'][role] is not None]
        complete = [row['silhouette_iou']['all_frame'][role] for row in rows]
        valid = [value for value in complete if value is not None]
        by_role[role] = {'observed_frames': len(observed), 'missing_frames': len(rows)-len(observed),
                         'observed_mean': average(observed),
                         'all_frame_mean': average(valid) if len(valid) == len(rows) else None}
    complete_means = [by_role[role]['all_frame_mean'] for role in ('Lab', 'IG')]
    selection_score = statistics.mean(complete_means) if all(value is not None for value in complete_means) else None
    trajectory = {role: [row['trajectory_error_px'][role] for row in rows if row['trajectory_error_px'][role] is not None] for role in ('Lab', 'IG')}
    output_ratios = [row['silhouette_iou']['output_lab_ig_height_ratio'] for row in rows if row['silhouette_iou']['output_lab_ig_height_ratio'] is not None]
    source_ratios = [row['silhouette_iou']['source_lab_ig_height_ratio'] for row in rows if row['silhouette_iou']['source_lab_ig_height_ratio'] is not None]
    outside_values = [row['outside_mask_mae'] for row in rows if row['outside_mask_mae'] is not None]
    outside_pixels = sum(row['outside_mask_pixels'] for row in rows)
    outside_weighted = sum(row['outside_mask_mae']*row['outside_mask_pixels'] for row in rows if row['outside_mask_mae'] is not None)/outside_pixels if outside_pixels else None
    outdiff = average([row['output_background_difference'] for row in rows if row['output_background_difference'] is not None])
    srcdiff = average([row['source_background_difference'] for row in rows if row['source_background_difference'] is not None])
    report = {'status': 'MEASURED' if casting is not None else 'CASTING_INCONCLUSIVE',
              'quality': 'HUMAN_REVIEW_PENDING', 'temporal': 'UNVERIFIED', 'geometry': cfg.geometry,
              'coordinate_size': [1280, 720], 'frame_count': len(rows), 'output_fps': cfg.output_fps,
              'casting': casting, 'frames': rows, 'actual_two_frames': sum(row['actual_two'] for row in rows),
              'actual_two_fraction': sum(row['actual_two'] for row in rows)/len(rows),
              'actual_two_area_frames': sum(row['actual_two_area_gate'] for row in rows),
              'silhouette_iou': {'per_casting': by_role, 'all_frame_mean_lab_ig': selection_score,
                  'definition': 'Undilated source and fixed-cast output masks, intersected with observed crop support. Missing output detection yields observed=null and explicit empty-prediction IoU0. Technical SAM failure has no metric.',
                  'eligible_for_14b_by_count': len(rows) == 73 and sum(row['actual_two'] for row in rows) >= 66},
              'trajectory': {role: {'observed_frames': len(values), 'missing_frames': len(rows)-len(values),
                                    'mean_error_px': average(values), 'mean_error_percent_width': average(values)/12.8 if values else None}
                             for role, values in trajectory.items()},
              'opposite_assignment_proxy_frames': sum(row['nearest_opposite_assignment'] is True for row in rows),
              'opposite_assignment_unobserved_frames': sum(row['nearest_opposite_assignment'] is None for row in rows),
              'lab_ig_height_ratio': {'output_median': median(output_ratios), 'output_observed_frames': len(output_ratios),
                                    'source_median': median(source_ratios), 'anchor': height_ratio(af.objects, anchor_casting)},
              'outside_mask_preservation': {'frame_mean_mae': average(outside_values), 'pixel_weighted_mae': outside_weighted,
                  'observed_frames': len(outside_values), 'pixels': outside_pixels,
                  'frame0_mae': rows[0]['outside_mask_mae'], 'later_frame_mean_mae': average([row['outside_mask_mae'] for row in rows[1:] if row['outside_mask_mae'] is not None]),
                  'caveat': 'Original canonical RGB comparison after inverse bilinear resize; crop support excluded. M3 frame0 mask is zero, so its approved anchor difference is included. Baseline/canny use M1 evaluation ROI only.'},
              'background_flicker': {'output_mean': outdiff, 'source_mean': srcdiff,
                  'ratio': outdiff/srcdiff if outdiff is not None and srcdiff is not None and srcdiff > 0 else None},
              'caveats': ['SAM correspondence and opposite nearest assignment are geometric proxies, not proof of visual identity.',
                          'Reflection bbox rule may associate one reflection with multiple bodies; color differences are reference-only.',
                          'SAM max4 tracking can omit instances; masks and inverse resizing affect descriptive metrics.'],
              'input_summary_sha256': {role: hashlib.sha256(path.read_bytes()).hexdigest() for role, path in
                                      [('source', cfg.source_summary), ('output', cfg.output_summary), ('anchor', cfg.anchor_summary)]}}
    temporary = destination.with_suffix(destination.suffix+'.partial')
    temporary.write_text(json.dumps(report, indent=2)+'\n')
    temporary.replace(destination)
    assert json.loads(destination.read_text()) == report
    print(json.dumps({key: value for key, value in report.items() if key != 'frames'}))


if __name__ == '__main__':
    main()
