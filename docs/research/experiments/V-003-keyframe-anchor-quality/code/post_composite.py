# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy", "Pillow", "scipy"]
# ///
"""Separate CPU POST PNGs; run existing Python: post_composite.py SCENE.json RUNTIME.json.

Runtime keys: source_frames, raw_frames, source_summary, output_summary, output_dir.
Frames are NNN.png; SAM masks are NNN-track-NN.png beside each summary. RAW is
read-only. Output is a new directory, never an overwrite or replacement of RAW.
Source RGB uses BICUBIC aspect resize plus center crop; masks use NEAREST. Output
SAM may be on the canonical master or native RAW canvas. No missing crop rows
are invented: POST has the same canvas as RAW. Reflection dilation uses its
nearest horizontally matching real body's height; associations are reported.
Finite inward feather lies inside the dilated edit region, with all undilated
source/output instance pixels forced to RAW. Exterior pixels equal source.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict
import hashlib
import json
import math
import sys

import numpy as np
from numpy.typing import NDArray
from PIL import Image
from scipy.ndimage import distance_transform_edt


@dataclass(frozen=True, slots=True)
class Geometry:
    master: tuple[int, int]
    output: tuple[int, int]

    @property
    def resized(self) -> tuple[int, int]:
        scale = max(self.output[0]/self.master[0], self.output[1]/self.master[1])
        return round(self.master[0]*scale), round(self.master[1]*scale)

    def transform(self, image: Image.Image, *, mask: bool) -> Image.Image:
        if image.size != self.master:
            raise ValueError(f'Expected master canvas {self.master}, got {image.size}')
        width, height = self.resized
        left, top = (width-self.output[0])//2, (height-self.output[1])//2
        resized = image.resize((width, height), Image.Resampling.NEAREST if mask else Image.Resampling.BICUBIC)
        return resized.crop((left, top, left+self.output[0], top+self.output[1]))


@dataclass(frozen=True, slots=True)
class Instance:
    track: int
    mask: NDArray[np.bool_]

    @property
    def bbox(self) -> tuple[int, int, int, int]:
        y, x = np.nonzero(self.mask)
        return int(x.min()), int(y.min()), int(x.max()+1), int(y.max()+1)


class DilationRecord(TypedDict):
    track: int
    body_track: int
    radius_px: int
    mask_pixels: int


def expanded_union(instances: list[Instance], rule: tuple[float, float], fraction: float
                   ) -> tuple[NDArray[np.bool_], NDArray[np.bool_], list[DilationRecord]]:
    """Union instances after Euclidean dilation based on corresponding body height."""
    if not instances:
        raise ValueError('No present SAM instances: POST cannot safely establish edit region')
    boxes = {item.track: item.bbox for item in instances}
    candidates: dict[int, list[int]] = {}
    for lower, b in boxes.items():
        candidates[lower] = [upper for upper, a in boxes.items() if upper != lower
                            and max(0, min(a[2], b[2])-max(a[0], b[0])) >= rule[0]*min(a[2]-a[0], b[2]-b[0])
                            and b[1] > a[3]-rule[1]]
    reflected = {track for track, owners in candidates.items() if owners}
    core = np.zeros_like(instances[0].mask)
    expanded = core.copy()
    records: list[DilationRecord] = []
    for item in instances:
        body = item.track
        if item.track in reflected:
            owners = [track for track in candidates[item.track] if track not in reflected]
            if not owners:
                raise ValueError(f'Reflection {item.track} has no corresponding real body')
            b = boxes[item.track]
            body = min(owners, key=lambda track: (abs(sum(boxes[track][::2])-sum(b[::2])), abs(b[1]-boxes[track][3]), track))
        box = boxes[body]
        radius = math.ceil(fraction*(box[3]-box[1]))
        core |= item.mask
        expanded |= distance_transform_edt(~item.mask) <= radius
        records.append({'track': item.track, 'body_track': body, 'radius_px': radius,
                        'mask_pixels': int(item.mask.sum())})
    return core, expanded, records


def feather_alpha(core: NDArray[np.bool_], region: NDArray[np.bool_], width: float) -> NDArray[np.float32]:
    """Finite inward feather, preserving all measured object pixels byte-exact."""
    distance = distance_transform_edt(np.pad(region, 1))[1:-1, 1:-1]
    alpha = np.clip(distance/width, 0, 1).astype(np.float32)
    alpha[core] = 1
    alpha[~region] = 0
    return alpha


def compose(source: NDArray[np.uint8], raw: NDArray[np.uint8], alpha: NDArray[np.float32]) -> NDArray[np.uint8]:
    weight = alpha[:, :, None]
    result = np.rint(raw.astype(np.float32)*weight+source.astype(np.float32)*(1-weight)).astype(np.uint8)
    result[alpha == 1] = raw[alpha == 1]
    result[alpha == 0] = source[alpha == 0]
    return result


def read_instances(summary: Path, index: int, geometry: Geometry) -> list[Instance]:
    """Read every present tracked object, retaining reflections for the edit union."""
    data = json.loads(summary.read_text())
    size = tuple(data['coordinate_size'])
    if size not in (geometry.master, geometry.output):
        raise ValueError(f'Unsupported SAM canvas {size}')
    frame = next(frame for frame in data['frames'] if frame['index'] == index)
    instances = []
    for row in frame['objects']:
        if not row['present']:
            continue
        track = int(row['track_index'])
        with Image.open(summary.parent/f'{index:03d}-track-{track:02d}.png') as image:
            if image.size != size:
                raise ValueError('SAM mask dimensions disagree with summary')
            mask = image.convert('L')
            if size == geometry.master:
                mask = geometry.transform(mask, mask=True)
            pixels = np.asarray(mask) > 0
        if pixels.any():
            instances.append(Instance(track, pixels))
    return instances


def main() -> None:
    scene_path, runtime_path = map(Path, sys.argv[1:])
    scene, runtime = json.loads(scene_path.read_text()), json.loads(runtime_path.read_text())
    geometry = Geometry(tuple(scene['anchor_generation']['resolution_master']), tuple(scene['generation']['resolution']))
    fraction, width = float(scene['post_composite']['dilation_fraction']), float(scene['post_composite']['feather_px'])
    if not 0 <= fraction <= 1 or width <= 0:
        raise ValueError('Invalid configured dilation or feather')
    rule_config = scene['scene']['reflection_rule']
    rule = (float(rule_config['x_overlap_min_frac_of_narrower']),
            float(rule_config['lower_top_below_upper_bottom_minus_px'])*geometry.resized[1]/geometry.master[1])
    source_dir, raw_dir, output = (Path(runtime[key]) for key in ('source_frames', 'raw_frames', 'output_dir'))
    source_summary, output_summary = Path(runtime['source_summary']), Path(runtime['output_summary'])
    if output.resolve() in (source_dir.resolve(), raw_dir.resolve()) or output.exists():
        raise FileExistsError('POST must be a new directory distinct from source and RAW')
    output.mkdir(parents=True, exist_ok=False)
    (output/'regions').mkdir()
    (output/'alpha').mkdir()
    rows = []
    for index in range(int(scene['generation']['frames'])):
        name = f'{index:03d}.png'
        raw_path = raw_dir/name
        raw_hash = hashlib.sha256(raw_path.read_bytes()).hexdigest()
        with Image.open(source_dir/name) as image:
            source = np.asarray(geometry.transform(image.convert('RGB'), mask=False))
        with Image.open(raw_path) as image:
            if image.size != geometry.output:
                raise ValueError('RAW frame dimensions disagree with generation config')
            raw = np.asarray(image.convert('RGB'))
        source_core, source_region, source_records = expanded_union(read_instances(source_summary, index, geometry), rule, fraction)
        output_core, output_region, output_records = expanded_union(read_instances(output_summary, index, geometry), rule, fraction)
        core, region = source_core | output_core, source_region | output_region
        alpha = feather_alpha(core, region, width)
        post = compose(source, raw, alpha)
        temporary = output/(name+'.partial')
        Image.fromarray(post).save(temporary, format='PNG')
        temporary.replace(output/name)
        Image.fromarray(region.astype(np.uint8)*255).save(output/'regions'/name)
        Image.fromarray(np.rint(alpha*255).astype(np.uint8)).save(output/'alpha'/name)
        if hashlib.sha256(raw_path.read_bytes()).hexdigest() != raw_hash:
            raise OSError('RAW changed during compositing')
        rows.append({'index': index, 'raw_sha256': raw_hash,
                     'post_sha256': hashlib.sha256((output/name).read_bytes()).hexdigest(),
                     'core_pixels': int(core.sum()), 'edit_pixels': int(region.sum()),
                     'feather_pixels': int(((alpha > 0) & (alpha < 1)).sum()),
                     'source_instances': source_records, 'output_instances': output_records})
    report = {'kind': 'DERIVED_CPU_POST_NOT_MODEL_OUTPUT', 'raw_preserved': True,
              'scene_config_sha256': hashlib.sha256(scene_path.read_bytes()).hexdigest(),
              'master_size': geometry.master, 'resize_size': geometry.resized, 'post_size': geometry.output,
              'rgb_resampling': 'BICUBIC', 'mask_resampling': 'NEAREST', 'dilation': 'Euclidean ceil(fraction * corresponding body height)',
              'feather': 'finite inward distance / configured width; undilated union forced RAW',
              'missing_inverse_crop_rows': 'not reconstructed; POST stays on RAW cropped canvas', 'frames': rows}
    (output/'POST_MANIFEST.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({'frames': len(rows), 'kind': report['kind']}))


if __name__ == '__main__':
    main()
