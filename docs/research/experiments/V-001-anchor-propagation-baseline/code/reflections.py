# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# Run: python reflections.py /private/sam-summary.json /public/amendment2-metrics.json
"""V-001 amendment 2: the user's exact bbox reflection rule, on existing masks."""
from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import TypedDict
import hashlib
import json
import sys

from sam_analysis import ObjectRow


class ReflectionPair(TypedDict):
    above_track_index: int
    reflection_track_index: int
    horizontal_overlap: float
    smaller_width: float


class Classified(TypedDict):
    actual_track_indices: list[int]
    reflection_track_indices: list[int]
    pairs: list[ReflectionPair]


def classify(objects: Sequence[ObjectRow]) -> Classified:
    """Classify every ordered distinct pair; do not rank or suppress candidates."""
    present = [row for row in objects if row['present'] and row['bbox'] is not None]
    pairs: list[ReflectionPair] = []
    for above in present:
        a = above['bbox']
        assert a is not None and a[2] > a[0] and a[3] > a[1]
        for below in present:
            if above['track_index'] == below['track_index']:
                continue
            b = below['bbox']
            assert b is not None and b[2] > b[0] and b[3] > b[1]
            overlap = max(0, min(a[2], b[2]) - max(a[0], b[0]))
            width = min(a[2]-a[0], b[2]-b[0])
            if overlap >= 0.5*width and b[1] > a[3]-40:
                pairs.append({'above_track_index': above['track_index'],
                              'reflection_track_index': below['track_index'],
                              'horizontal_overlap': overlap, 'smaller_width': width})
    reflected = {pair['reflection_track_index'] for pair in pairs}
    return {'actual_track_indices': sorted(row['track_index'] for row in present
                                          if row['track_index'] not in reflected),
            'reflection_track_indices': sorted(reflected), 'pairs': pairs}


class Cast(TypedDict):
    Lab: int
    IG: int


def first_frame_cast(objects: Sequence[ObjectRow]) -> Cast:
    """Bind two actual objects by user-confirmed frame-240 horizontal ordering."""
    classified = classify(objects)
    actual = [row for row in objects if row['track_index'] in classified['actual_track_indices']]
    assert len(actual) == 2, 'FIRST_FRAME_CASTING_REQUIRES_EXACTLY_TWO_ACTUAL_OBJECTS'
    assert all(row['center'] is not None for row in actual)
    actual.sort(key=lambda row: row['center'][0] if row['center'] else float('nan'))
    assert actual[0]['center'] is not None and actual[1]['center'] is not None
    assert actual[0]['center'][0] < actual[1]['center'][0]
    return {'Lab': actual[1]['track_index'], 'IG': actual[0]['track_index']}


def cast_present(objects: Sequence[ObjectRow], casting: Cast) -> bool:
    """Require the same two cast IDs to be actual and individually large enough."""
    actual = set(classify(objects)['actual_track_indices'])
    rows = {row['track_index']: row for row in objects}
    return all(track in actual and rows[track]['area_fraction'] >= 0.005
               for track in casting.values())


def main() -> None:
    source, target = map(Path, sys.argv[1:])
    raw = source.read_bytes()
    summary = json.loads(raw)
    frames = summary['frames']
    assert len(frames) == 73 and summary['coordinate_size'] == [1280, 720]
    casting = first_frame_cast(frames[0]['objects'])
    rows = [{'index': frame['index'], 'source_index': 240+frame['index'],
             **classify(frame['objects']),
             'casted_area_gate': cast_present(frame['objects'], casting)} for frame in frames]
    count = sum(row['casted_area_gate'] for row in rows)
    result = {'amendment': 2, 'classification': 'POST_RESULT_DEFINITION_CORRECTION',
              'original_gate_status_preserved': summary['segment_status'],
              'input_summary_sha256': hashlib.sha256(raw).hexdigest(),
              'sam_reruns': 0, 'segment': [240, 313], 'coordinate_size': [1280, 720],
              'rule': 'For distinct A,B: overlap_x >= 0.5*min(width_A,width_B) and B.top > A.bottom-40. B is reflection.',
              'casting': casting, 'required_valid_frames': 66, 'valid_frames': count,
              'status': 'SEGMENT_ESTABLISHED' if count >= 66 else 'SEGMENT_NOT_ESTABLISHED',
              'frames': rows}
    target.write_text(json.dumps(result, indent=2)+'\n')
    assert json.loads(target.read_text()) == result
    print(json.dumps({key: value for key, value in result.items() if key != 'frames'}))


if __name__ == '__main__':
    main()
