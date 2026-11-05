"""CPU measurements only; never infer motion success or human quality from IoU.

Usage: output_metrics.py SCENE.json RUNTIME.json. Runtime: source_frames,
raw_frames, post_frames, source_summary, output_summary, output, anchors
[{frame,image,summary,casting:{role:track}}]. Anchor summary frame defaults to 0.
POST regions/NNN.png come from post_composite.py. All paths remain private.
Reuses V002 missing-silhouette convention and V003 geometry/reflection readers;
V002's engine cannot be imported directly because its scene constants are fixed.
"""
from __future__ import annotations

from itertools import permutations
from pathlib import Path
import json
import math
import sys

import numpy as np
from numpy.typing import NDArray
from PIL import Image
from scipy.ndimage import uniform_filter

from anchor_gates import Policy, Row, classify
from post_composite import Geometry, Instance, read_instances


def descriptors(items: list[Instance], geo: Geometry) -> list[Row]:
    sx, sy = geo.master[0]/geo.resized[0], geo.master[1]/geo.resized[1]
    ox, oy = (geo.resized[0]-geo.output[0])//2, (geo.resized[1]-geo.output[1])//2
    result = []
    for item in items:
        x0, y0, x1, y1 = item.bbox
        y, x = np.nonzero(item.mask)
        result.append(Row(item.track, True, ((x0+ox)*sx, (y0+oy)*sy, (x1+ox)*sx, (y1+oy)*sy),
                          ((float(x.mean())+ox+.5)*sx-.5, (float(y.mean())+oy+.5)*sy-.5),
                          round(int(item.mask.sum())*sx*sy)))
    return result


def bind(source: dict[int, Row], output: dict[int, Row], actual: list[int], policy: Policy) -> dict[str, int] | None:
    if len(actual) != len(policy.cast) or any(t not in source for t in policy.cast.values()):
        return None
    ranked = sorted((sum(math.dist(source[policy.cast[r]].center, output[t].center)
                         for r, t in zip(policy.cast, perm)), perm) for perm in permutations(actual))
    if len(ranked) > 1 and math.isclose(ranked[0][0], ranked[1][0], abs_tol=1e-9, rel_tol=0):
        return None
    return dict(zip(policy.cast, ranked[0][1]))


def silhouette_score(source: NDArray[np.bool_], output: NDArray[np.bool_] | None) -> tuple[float | None, float | None]:
    # Same explicit missing-output convention as V002/code/metrics_core.py.
    if not source.any():
        return None, None
    if output is None:
        return None, 0.0
    score = float((source & output).sum()/(source | output).sum())
    return score, score


def masked_ssim(a: NDArray[np.float64], b: NDArray[np.float64], region: NDArray[np.bool_]) -> float | None:
    if not region.any():
        return None
    mean_a, mean_b = uniform_filter(a, (7, 7, 1)), uniform_filter(b, (7, 7, 1))
    var_a = (uniform_filter(a*a, (7, 7, 1))-mean_a*mean_a)*49/48
    var_b = (uniform_filter(b*b, (7, 7, 1))-mean_b*mean_b)*49/48
    cov = (uniform_filter(a*b, (7, 7, 1))-mean_a*mean_b)*49/48
    c1, c2 = (.01*255)**2, (.03*255)**2
    value = ((2*mean_a*mean_b+c1)*(2*cov+c2))/((mean_a**2+mean_b**2+c1)*(var_a+var_b+c2))
    return float(value.mean(axis=2)[region].mean())


def rgb(path: Path, geo: Geometry) -> NDArray[np.float64]:
    with Image.open(path) as image:
        image = image.convert('RGB')
        if image.size == geo.master:
            image = geo.transform(image, mask=False)
        if image.size != geo.output:
            raise ValueError(f'Unexpected RGB size: {image.size}')
        return np.asarray(image, dtype=np.float64)


def mean(values: list[float | None]) -> float | None:
    found = [x for x in values if x is not None]
    return float(np.mean(found)) if found else None


def run(scene_path: Path, runtime: dict) -> dict:
    scene = json.loads(scene_path.read_text())
    policy = Policy.read(scene_path)
    geo = Geometry(policy.size, tuple(scene['generation']['resolution']))
    count = scene['generation']['frames']
    minimum = scene['sam_settings']['min_area_fraction']
    frames, keyframes, flicker = [], [], []
    casting = None
    previous = None
    anchors = {a['frame']: a for a in runtime.get('anchors', [])}
    for index in range(count):
        source_items = read_instances(Path(runtime['source_summary']), index, geo)
        output_items = read_instances(Path(runtime['output_summary']), index, geo)
        sr, out = descriptors(source_items, geo), descriptors(output_items, geo)
        source, output = {r.track: r for r in sr}, {r.track: r for r in out}
        sm, om = {i.track: i.mask for i in source_items}, {i.track: i.mask for i in output_items}
        actual, reflected = classify(out, policy)
        actual = [t for t in actual if output[t].area/(geo.master[0]*geo.master[1]) >= minimum]
        if index == 0:
            casting = bind(source, output, actual, policy)
        nearest = bind(source, output, actual, policy)
        roles = {}
        for role, source_track in policy.cast.items():
            target = casting.get(role) if casting else None
            observed = target in actual
            row = {'bbox_aspect': None, 'aspect_vs_source': None, 'upright_lower_bound': False if casting else None,
                   'within_reference_band': False if casting else None, 'center_distance_px': None,
                   'center_distance_width_percent': None, 'iou_observed': None, 'iou_all_frame': None}
            if casting is not None and source_track in sm:
                row['iou_observed'], row['iou_all_frame'] = silhouette_score(sm[source_track], om[target] if observed else None)
            if observed and source_track in source:
                a, b = source[source_track].bbox, output[target].bbox
                aspect = (b[3]-b[1])/(b[2]-b[0])
                ratio = aspect/((a[3]-a[1])/(a[2]-a[0]))
                distance = math.dist(source[source_track].center, output[target].center)
                row.update(bbox_aspect=aspect, aspect_vs_source=ratio,
                           upright_lower_bound=ratio >= policy.aspect[0],
                           within_reference_band=policy.aspect[0] <= ratio <= policy.aspect[1],
                           center_distance_px=distance, center_distance_width_percent=100*distance/geo.master[0])
            roles[role] = row
        frames.append({'frame': index, 'actual_tracks': actual, 'reflection_tracks': reflected,
                       'count_matches': len(actual) == policy.count, 'roles': roles,
                       'geometric_cast_opposition_proxy': nearest != casting if nearest and casting else None})
        source_rgb = rgb(Path(runtime['source_frames'])/f'{index:03d}.png', geo)
        raw = rgb(Path(runtime['raw_frames'])/f'{index:03d}.png', geo)
        post = rgb(Path(runtime['post_frames'])/f'{index:03d}.png', geo)
        with Image.open(Path(runtime['post_frames'])/'regions'/f'{index:03d}.png') as image:
            region = np.asarray(image.convert('L')) > 0
        if region.shape != raw.shape[:2]:
            raise ValueError('POST region geometry mismatch')
        if previous is not None:
            visible = ~(region | previous[3])
            row = {'frame': index, 'pixels': int(visible.sum())}
            for name, current, before in zip(('source', 'raw', 'post'), (source_rgb, raw, post), previous[:3]):
                row[name] = float(np.abs(current-before)[visible].mean()) if visible.any() else None
            flicker.append(row)
        previous = source_rgb, raw, post, region
        if index in anchors:
            anchor = anchors[index]
            if set(anchor['casting']) != set(policy.cast):
                raise ValueError('Anchor casting must come from accepted gate artifact')
            am = {i.track: i.mask for i in read_instances(Path(anchor['summary']), anchor.get('summary_frame', 0), geo)}
            ar = rgb(Path(anchor['image']), geo)
            scores = {}
            for role, track in anchor['casting'].items():
                target = casting.get(role) if casting else None
                scores[role] = masked_ssim(ar, raw, am[track] | om[target]) if track in am and target in actual else None
            keyframes.append({'frame': index, 'source_frame': anchor.get('source_frame', index), 'raw_anchor_object_ssim': scores})
    aggregate = {}
    for role in policy.cast:
        rows = [f['roles'][role] for f in frames]
        aggregate[role] = {key: mean([r[key] for r in rows]) for key in
                           ('aspect_vs_source', 'center_distance_width_percent', 'iou_observed', 'iou_all_frame')}
        aggregate[role].update(upright_lower_bound_fraction=sum(r['upright_lower_bound'] for r in rows)/count if casting else None,
                               within_reference_band_fraction=sum(r['within_reference_band'] for r in rows)/count if casting else None)
    raw_f, post_f = mean([f['raw'] for f in flicker]), mean([f['post'] for f in flicker])
    source_f = mean([f['source'] for f in flicker])
    return {'quality': 'HUMAN_REVIEW_PENDING', 'temporal_review': 'UNVERIFIED', 'casting': casting,
            'casting_status': 'ESTABLISHED' if casting else 'CASTING_UNESTABLISHED',
            'geometry': {'master': geo.master, 'measurement_canvas': geo.output, 'resized': geo.resized},
            'definitions': {'iou': 'V002 missing output = all-frame zero; cropped visible support only; NOT a motion pass criterion',
                            'swap': 'Nearest-center opposition proxy only, not an identity verdict',
                            'ssim': 'RGB local 7x7, sample covariance, range255; mean on anchor/output object union',
                            'background': 'Consecutive RGB MAE outside union of both POST edit regions; reflections excluded',
                            'upright': 'bbox height/width proxy; missing frames never pass; reference upper band reported separately'},
            'frames': frames, 'roles': aggregate, 'keyframes': keyframes,
            'count_matches_fraction': sum(f['count_matches'] for f in frames)/count,
            'geometric_opposition_frames': sum(f['geometric_cast_opposition_proxy'] is True for f in frames) if casting else None,
            'background': {'transitions': flicker, 'raw_mean': raw_f, 'post_mean': post_f, 'source_mean': source_f,
                           'raw_over_source': raw_f/source_f if source_f and raw_f is not None else None,
                           'post_over_source': post_f/source_f if source_f and post_f is not None else None,
                           'post_over_raw': post_f/raw_f if raw_f and post_f is not None else None},
            'identity_embedding': 'SEPARATE_WORKER'}


if __name__ == '__main__':
    runtime = json.loads(Path(sys.argv[2]).read_text())
    destination = Path(runtime['output'])
    if destination.exists():
        raise FileExistsError(destination)
    result = run(Path(sys.argv[1]), runtime)
    temp = destination.with_suffix('.tmp')
    temp.write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    json.loads(temp.read_text())
    temp.replace(destination)
