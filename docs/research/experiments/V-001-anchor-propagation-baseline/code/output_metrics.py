# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# Run: existing Python output_metrics.py /private/config.json /private/metrics.json
"""V-001 CPU measurements; missing observations remain explicit, never zero error."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, TypedDict, assert_never
import hashlib
import json
import math
import statistics
import sys

import numpy as np
from numpy.typing import NDArray
from PIL import Image, ImageFilter

from anchor_gates import ReflectionColor, reflection_colors
from reflections import Cast, Classified, classify
from sam_analysis import ObjectRow, describe

Geometry = Literal['E1', 'E2', 'CANONICAL']


@dataclass(frozen=True, slots=True)
class Frame:
    rgb: NDArray[np.uint8]
    objects: list[ObjectRow]
    masks: dict[int, NDArray[np.bool_]]
    union: NDArray[np.bool_]


class FrameMetric(TypedDict):
    index: int
    source_index: int
    classification: Classified
    canonical_objects: list[ObjectRow]
    actual_count: int
    actual_two_area_gate: bool
    cast_observed: bool
    trajectory_error_px: dict[str, float | None]
    lab_height_ratio: float | None
    nearest_opposite_assignment: bool | None
    reflection_color_reference_only: list[ReflectionColor]
    background_roi_pixels: int | None
    output_background_difference: float | None
    source_background_difference: float | None


def native_size(geometry: Geometry) -> tuple[int, int]:
    match geometry:
        case 'E1': return (1024, 576)
        case 'E2': return (832, 480)
        case 'CANONICAL': return (1280, 720)
        case unreachable: assert_never(unreachable)


def canonical(image: Image.Image, geometry: Geometry, *, mask: bool) -> Image.Image:
    """Invert engine spatial preprocessing; E2 cropped borders stay unobserved."""
    assert image.size == native_size(geometry)
    resample = Image.Resampling.NEAREST if mask else Image.Resampling.BILINEAR
    if geometry == 'E2':
        padded = Image.new(image.mode, (853, 480), 0)
        padded.paste(image, (10, 0))
        image = padded
    return image.resize((1280, 720), resample)


def visible_support(geometry: Geometry) -> NDArray[np.bool_]:
    """Exclude unobserved crop borders, including RGB resampling edge support."""
    mask = np.asarray(canonical(Image.new('L', native_size(geometry), 255), geometry, mask=True)) > 0
    if geometry == 'E2':
        # A bilinear sample needs both neighbouring native pixels to be observed.
        x = (np.arange(1280)+.5)*853/1280-.5
        mask &= ((x >= 10) & (x <= 841))[None, :]
    return mask


def load_frame(folder: Path, image_path: Path, objects: list[ObjectRow], index: int,
               geometry: Geometry) -> Frame:
    """Resample saved masks only; no segmentation or candidate selection occurs."""
    with Image.open(image_path) as image:
        rgb = np.asarray(canonical(image.convert('RGB'), geometry, mask=False))
    masks: dict[int, NDArray[np.bool_]] = {}
    rows: list[ObjectRow] = []
    union = np.zeros((720,1280), dtype=bool)
    for row in objects:
        track = row['track_index']
        with Image.open(folder/f'{index:03d}-track-{track:02d}.png') as image:
            mask = np.asarray(canonical(image.convert('L'), geometry, mask=True)) > 0
        masks[track] = mask
        rows.append(describe(mask, track))
        union |= mask
    return Frame(rgb, rows, masks, union)


def match_cast(source: list[ObjectRow], output: list[ObjectRow]) -> Cast | None:
    """Assign exactly two actual first-frame objects by the unique lower total distance."""
    ids = classify(output)['actual_track_indices']
    if len(ids) != 2:
        return None
    src, out = ({row['track_index']: row for row in rows} for rows in (source,output))
    centers = [src[0]['center'], src[1]['center'], out[ids[0]]['center'], out[ids[1]]['center']]
    if any(center is None for center in centers):
        return None
    lab, ig, first, second = centers
    assert lab is not None and ig is not None and first is not None and second is not None
    straight = math.dist(lab,first)+math.dist(ig,second)
    crossed = math.dist(lab,second)+math.dist(ig,first)
    if abs(straight-crossed) <= 1e-9:
        return None
    return {'Lab':ids[0], 'IG':ids[1]} if straight < crossed else {'Lab':ids[1], 'IG':ids[0]}


def object_metrics(source: Frame, output: Frame, casting: Cast | None) -> tuple[dict[str, float | None], float | None, bool | None]:
    """Fixed-track correspondence; opposite nearest assignment is only a geometric proxy."""
    errors: dict[str, float | None] = {'Lab':None,'IG':None}
    src, out = ({row['track_index']: row for row in rows} for rows in (source.objects,output.objects))
    actual = set(classify(output.objects)['actual_track_indices'])
    if casting is None:
        return errors, None, None
    for role, source_id in [('Lab',0),('IG',1)]:
        target = out.get(casting[role])
        if target is not None and casting[role] in actual and target['area_fraction'] >= .005:
            a,b = src[source_id]['center'],target['center']
            if a is not None and b is not None:
                errors[role] = math.dist(a,b)
    if any(value is None for value in errors.values()):
        return errors,None,None
    a,b = src[0]['bbox'],out[casting['Lab']]['bbox']
    assert a is not None and b is not None
    ratio = (b[3]-b[1])/(a[3]-a[1])
    lab,ig,olab,oig = src[0]['center'],src[1]['center'],out[casting['Lab']]['center'],out[casting['IG']]['center']
    assert lab is not None and ig is not None and olab is not None and oig is not None
    direct = math.dist(lab,olab)+math.dist(ig,oig)
    opposite = math.dist(lab,oig)+math.dist(ig,olab)
    swapped = None if abs(direct-opposite) <= 1e-9 else opposite < direct
    return errors,ratio,swapped


def transition(previous_source: Frame, source: Frame, previous_output: Frame, output: Frame,
               visible: NDArray[np.bool_]) -> tuple[int, float | None, float | None]:
    """Measure both videos over the same visible nonobject/nonreflection pixels."""
    union = previous_source.union | source.union | previous_output.union | output.union
    dilated = np.asarray(Image.fromarray(union.astype('uint8')*255).filter(ImageFilter.MaxFilter(49))) > 0
    roi = visible & ~dilated
    count = int(roi.sum())
    if not count:
        return 0,None,None
    src = float(np.abs(source.rgb.astype(np.float32)-previous_source.rgb.astype(np.float32))[roi].mean())
    out = float(np.abs(output.rgb.astype(np.float32)-previous_output.rgb.astype(np.float32))[roi].mean())
    return count,out,src


def average(values: list[float]) -> float | None:
    return statistics.mean(values) if values else None


def main() -> None:
    config_path,destination = map(Path,sys.argv[1:])
    cfg = json.loads(config_path.read_text())
    geometry: Geometry = cfg['geometry']
    assert geometry in ('E1','E2','CANONICAL')
    source_path,output_path = Path(cfg['source_summary']),Path(cfg['output_summary'])
    source,output = (json.loads(path.read_text()) for path in (source_path,output_path))
    assert source['coordinate_size'] == [1280,720] and output['coordinate_size'] == list(native_size(geometry))
    source_images,output_images = (sorted(Path(cfg[key]).glob('*.png')) for key in ('source_frames','output_frames'))
    assert len(source_images) == len(source['frames']) and len(output_images) == len(output['frames'])
    fps = float(cfg.get('output_fps',24)); assert fps > 0
    visible = visible_support(geometry); rows: list[FrameMetric] = []
    previous_source = previous_output = None
    casting = None
    for i,raw in enumerate(output['frames']):
        source_index = round(i*24/fps)
        assert source_index < len(source_images), 'OUTPUT_EXCEEDS_SOURCE_TIMELINE'
        sf = load_frame(source_path.parent,source_images[source_index],source['frames'][source_index]['objects'],source_index,'CANONICAL')
        of = load_frame(output_path.parent,output_images[i],raw['objects'],i,geometry)
        if i == 0: casting = match_cast(sf.objects,of.objects)
        classification = classify(of.objects); actual = classification['actual_track_indices']
        actual_rows = [row for row in of.objects if row['track_index'] in actual]
        errors,ratio,opposite = object_metrics(sf,of,casting)
        pixels = outdiff = srcdiff = None
        if previous_source is not None and previous_output is not None:
            pixels,outdiff,srcdiff = transition(previous_source,sf,previous_output,of,visible)
        rows.append({'index':i,'source_index':source_index,'classification':classification,'canonical_objects':of.objects,
                     'actual_count':len(actual),'actual_two_area_gate':len(actual)==2 and all(row['area_fraction']>=.005 for row in actual_rows),
                     'cast_observed':all(value is not None for value in errors.values()),'trajectory_error_px':errors,
                     'lab_height_ratio':ratio,'nearest_opposite_assignment':opposite,
                     'reflection_color_reference_only':reflection_colors(of.rgb,of.masks,classification),
                     'background_roi_pixels':pixels,'output_background_difference':outdiff,'source_background_difference':srcdiff})
        previous_source,previous_output = sf,of
    trajectory = {role:[row['trajectory_error_px'][role] for row in rows if row['trajectory_error_px'][role] is not None] for role in ('Lab','IG')}
    heights = [row['lab_height_ratio'] for row in rows if row['lab_height_ratio'] is not None]
    outdiff = average([row['output_background_difference'] for row in rows if row['output_background_difference'] is not None])
    srcdiff = average([row['source_background_difference'] for row in rows if row['source_background_difference'] is not None])
    anchor_ratio = json.loads(Path(cfg['anchor_gates']).read_text())['bbox_height_ratio']['Lab']
    median = statistics.median(heights) if heights else None
    report = {'status':'MEASURED' if casting is not None else 'CASTING_INCONCLUSIVE','quality':'HUMAN_REVIEW_PENDING',
              'geometry':geometry,'coordinate_size':[1280,720],'mask_normalization':'nearest resize to common pixel canvas; E2 pad10left/11right before resize',
              'rgb_normalization':'bilinear; E2 unobserved and interpolation-edge support excluded','visible_pixels':int(visible.sum()),
              'output_fps':fps,'frame_count':len(rows),'casting':casting,'frames':rows,
              'actual_two_fraction':sum(row['actual_count']==2 for row in rows)/len(rows),
              'actual_two_area_fraction':sum(row['actual_two_area_gate'] for row in rows)/len(rows),
              'trajectory':{role:{'observed_frames':len(values),'missing_frames':len(rows)-len(values),'mean_error_px':average(values),
                                 'mean_error_percent_width':average(values)/12.8 if values else None} for role,values in trajectory.items()},
              'opposite_assignment_proxy_frames':sum(row['nearest_opposite_assignment'] is True for row in rows),
              'opposite_assignment_unobserved_frames':sum(row['nearest_opposite_assignment'] is None for row in rows),
              'opposite_assignment_caveat':'geometric nearest correspondence only; does not establish identity swaps',
              'lab_height_ratio_median':median,'lab_height_observed_frames':len(heights),'anchor_lab_height_ratio':anchor_ratio,
              'lab_height_ratio_relative_to_anchor':median/anchor_ratio if median is not None else None,
              'background_output_mean_difference':outdiff,'background_source_mean_difference':srcdiff,
              'background_flicker_ratio':outdiff/srcdiff if outdiff is not None and srcdiff is not None and srcdiff>0 else None,
              'background_valid_transitions':sum(row['output_background_difference'] is not None for row in rows),
              'reflection_color_quality':'REFERENCE_ONLY_NO_THRESHOLD','input_summary_sha256':{key:hashlib.sha256(path.read_bytes()).hexdigest() for key,path in [('source',source_path),('output',output_path)]}}
    temporary = destination.with_suffix(destination.suffix+'.partial');temporary.write_text(json.dumps(report,indent=2)+'\n');temporary.replace(destination)
    assert json.loads(destination.read_text()) == report
    print(json.dumps({key:value for key,value in report.items() if key != 'frames'}))


if __name__ == '__main__':
    main()
