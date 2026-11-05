"""CPU-only fixed-scale canny construction; no generated-output-dependent tuning.

Usage: scaled_control.py SCENE.json PRIVATE_RUNTIME.json
Runtime: source_summary, canny_video, canny_sha256, output_dir(new), ffmpeg,
anchors:[{frame,image,summary,casting_report}]. All masks use original SAM IDs.
"""
from __future__ import annotations

from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys

import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt

from scaled_geometry import affine_layer, bbox, direction, fixed_scales, hold_indices, reflection_owners
from scaled_io import Canvas, describe, overlay, read_masks, review_panel, write_sheet


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path) -> dict:
    return json.loads(path.read_text())


def dump(path: Path, report: dict) -> None:
    with path.open('x') as handle:
        json.dump(report, handle, indent=2, allow_nan=False)
        handle.write('\n')
    assert read(path) == report


def scale_evidence(source: dict, anchors: list[dict], casting: dict[str, int]) -> tuple[dict[str, list[float]], list[dict]]:
    values = {role: [] for role in casting}
    evidence = []
    for anchor in anchors:
        frame = anchor['frame']
        original = {row['track_index']: row for row in next(row['objects'] for row in source['frames'] if row['index'] == frame)}
        summary, gate = read(Path(anchor['summary'])), read(Path(anchor['casting_report']))
        assert gate['gates']['G1'] and gate['gates']['G6']
        assert summary['coordinate_size'] == source['coordinate_size']
        targets = {row['track_index']: row for row in summary['frames'][0]['objects']}
        for role, track in casting.items():
            a, b = original[track]['bbox'], targets[gate['casting'][role]]['bbox']
            source_height, anchor_height = a[3]-a[1], b[3]-b[1]
            assert source_height > 0 and anchor_height > 0
            ratio = anchor_height/source_height
            values[role].append(ratio)
            evidence.append({'frame': frame, 'role': role, 'source_bbox_height': source_height,
                             'anchor_bbox_height': anchor_height, 'ratio': ratio})
    return values, evidence


def encode(ffmpeg: str, frames: Path, output: Path, fps: int) -> None:
    subprocess.run([ffmpeg, '-nostdin', '-v', 'error', '-n', '-threads', '2', '-framerate', str(fps),
                    '-i', str(frames/'%03d.png'), '-an', '-c:v', 'ffv1', '-level', '3', '-threads', '2',
                    '-pix_fmt', 'bgr0', str(output)], check=True)


def main() -> None:
    scene_path, runtime_path = map(Path, sys.argv[1:])
    scene, runtime = read(scene_path), read(runtime_path)
    settings = scene['scaled_control']
    casting = scene['scene']['casting_track_indices']
    canvas = Canvas(tuple(scene['anchor_generation']['resolution_master']), tuple(scene['generation']['resolution']))
    count, fps = scene['scene']['segment']['frames'], scene['generation']['fps']
    source_summary, canny = Path(runtime['source_summary']), Path(runtime['canny_video'])
    assert digest(canny) == runtime['canny_sha256']
    source = read(source_summary)
    anchors = sorted(runtime['anchors'], key=lambda anchor: anchor['frame'])
    assert len({anchor['frame'] for anchor in anchors}) == len(anchors) and anchors
    values, evidence = scale_evidence(source, anchors, casting)
    scales = fixed_scales(values, settings['snap_role'], tuple(settings['ig_snap_to_1_if_within']))
    output = Path(runtime['output_dir'])
    output.mkdir(parents=True, exist_ok=False)
    original, scaled, masks_dir, repeated, reviews = (output/name for name in
        ('original_frames', 'scaled_frames', 'scaled_masks', 'scaled_repeat_frames', 'reviews'))
    for folder in (original, scaled, masks_dir, repeated, reviews):
        folder.mkdir()
    subprocess.run([runtime['ffmpeg'], '-nostdin', '-v', 'error', '-n', '-threads', '2', '-i', str(canny),
                    '-vsync', '0', '-start_number', '0', str(original/'%03d.png')], check=True)
    assert [p.name for p in sorted(original.glob('*.png'))] == [f'{index:03d}.png' for index in range(count)]
    reflection = scene['scene']['reflection_rule']
    margin = reflection['lower_top_below_upper_bottom_minus_px']*canvas.resized[1]/canvas.master[1]
    frame_reports, mask_frames, prechecks, panels = [], [], [], []
    anchor_map = {anchor['frame']: anchor for anchor in anchors}
    for index in range(count):
        with Image.open(original/f'{index:03d}.png') as image:
            assert image.size == canvas.target
            rgb = np.asarray(image.convert('RGB'))
        masks = read_masks(source_summary, index, canvas)
        boxes = {track: bbox(mask) for track, mask in masks.items()}
        assert set(casting.values()).issubset(masks)
        owners, candidates = reflection_owners(boxes, casting, reflection['x_overlap_min_frac_of_narrower'], margin)
        supports = {track: distance_transform_edt(~mask) <= settings['edge_dilation_px'] for track, mask in masks.items()}
        background = rgb.copy()
        background[np.logical_or.reduce(list(supports.values()))] = 0
        layers, clipping = {}, []
        for track, mask in masks.items():
            role = next((role for role, body in casting.items() if body == track), None)
            reflected = role is None
            role = owners[track] if reflected else role
            x0, y0, x1, y1 = boxes[track]
            pivot = ((x0+x1)/2, y0 if reflected else y1)
            cutout = rgb.copy()
            cutout[~supports[track]] = 0
            layer = affine_layer(cutout, mask, supports[track], scales[role], pivot)
            layers[track] = layer
            clipping.append({'track': track, 'role': role, 'reflection': reflected, 'pivot': list(pivot),
                             'scale': scales[role], 'unclipped_scaled_mask_pixels': layer.unclipped_pixels,
                             'visible_scaled_mask_pixels': layer.visible_pixels, 'clipped_fraction': layer.clipped_fraction})
            Image.fromarray(layer.core.astype(np.uint8)*255).save(masks_dir/f'{index:03d}-track-{track:02d}.png')
        order = []
        for layer_spec in settings['layer_roles']:
            role = layer_spec['role']
            if layer_spec['kind'] == 'body':
                order.append(casting[role])
            elif layer_spec['kind'] == 'reflection':
                order.extend(sorted(track for track, owner in owners.items() if owner == role))
            else:
                raise ValueError('Unknown configured control layer kind')
        assert sorted(order) == sorted(layers), 'Every source body/reflection must have exactly one layer'
        for track in order:
            layer = layers[track]
            background[layer.support] = layer.rgb[layer.support]
        Image.fromarray(background).save(scaled/f'{index:03d}.png')
        mask_frames.append({'index': index, 'objects': [describe(track, layer.core) for track, layer in layers.items()]})
        frame_reports.append({'frame': index, 'reflection_owners': {str(k): v for k, v in owners.items()},
                              'reflection_candidates': {str(k): v for k, v in candidates.items()}, 'layer_tracks': order,
                              'clipping': clipping, 'scaled_directions': {role: direction(layers[track].core) for role, track in casting.items()}})
        if index in anchor_map:
            anchor = anchor_map[index]
            gate = read(Path(anchor['casting_report']))
            role = settings['precheck_role']
            target = read_masks(Path(anchor['summary']), 0, canvas)[gate['casting'][role]]
            predicted = layers[casting[role]].core
            union = int((target | predicted).sum())
            iou = float((target & predicted).sum()/union) if union else None
            prechecks.append({'frame': index, 'role': role, 'iou': iou, 'gating': False})
            anchor_rgb = review_panel(Path(anchor['image']), canvas)
            overlay(anchor_rgb, predicted, target).save(reviews/f'{index:03d}-overlay.png')
            panels.append((index, Image.fromarray(rgb), Image.fromarray(background), anchor_rgb))
    hold = hold_indices(count, scene['generation']['variants']['S3']['hold_factor'])
    assert len(hold) == scene['generation']['variants']['S3']['frames']
    for index, original_index in enumerate(hold):
        shutil.copy2(scaled/f'{original_index:03d}.png', repeated/f'{index:03d}.png')
    dump(masks_dir/'summary.json', {'status': 'DERIVED_SCALED_SOURCE_MASKS_NOT_SAM_RERUN',
                                   'coordinate_size': list(canvas.target), 'frame_count': count, 'frames': mask_frames})
    write_sheet(panels, reviews/'keyframe-triptych.jpg')
    encode(runtime['ffmpeg'], scaled, output/'scaled.mkv', fps)
    encode(runtime['ffmpeg'], repeated, output/'scaled-repeat.mkv', fps)
    mean_iou = float(np.mean([row['iou'] for row in prechecks if row['iou'] is not None]))
    report = {'kind': 'CPU_DERIVED_STRUCTURE_CONDITION_NOT_MODEL_OUTPUT', 'scales': scales, 'scale_evidence': evidence,
              'scale_basis': 'Fixed median over every accepted anchor, not generated outputs', 'frames': frame_reports,
              'keyframe_prechecks': prechecks, 'precheck_mean_iou': mean_iou,
              'precheck_notice': mean_iou < settings['precheck_mean_iou_notice_below'], 'precheck_gating': False,
              'hold_source_indices': hold, 'geometry': {'master': list(canvas.master), 'resized': list(canvas.resized), 'native': list(canvas.target)},
              'conventions': {'edge_dilation': 'Euclidean native-pixel radius; applied identically to bodies and reflections',
                              'layer_occlusion': 'Overwrite transformed dilated support including its black interior; configured back-to-front order',
                              'reflection_pairing': 'User spatial rule, nearest horizontal center then vertical gap then role for multiple candidates',
                              'clipping': '1 - visible mask pixels / full offscreen-extended transformed mask pixels; NEAREST rasterization',
                              'affine': 'PIL inverse affine NEAREST, pixel-edge pivot bottom-center body/top-center reflection',
                              'overlay': 'Red scaled source, green accepted anchor; overlap mixed; review derivative'},
              'source_canny_sha256': digest(canny), 'scaled_sha256': digest(output/'scaled.mkv'),
              'scaled_repeat_sha256': digest(output/'scaled-repeat.mkv'), 'scene_config_sha256': digest(scene_path),
              'source_summary_sha256': digest(source_summary), 'model_calls': 0}
    dump(output/'SCALED_CONTROL.json', report)
    print(json.dumps({'scales': scales, 'precheck_mean_iou': mean_iou, 'frames': count, 'held_frames': len(hold)}))


if __name__ == '__main__':
    main()
