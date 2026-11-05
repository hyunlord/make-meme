"""G8 reference-only direction from existing source/anchor SAM, no model rerun.

Usage: anchor_direction.py SCENE.json RUNTIME.json OUTPUT.json
Runtime: source_summary, source_frame_index, anchor_summary, casting_report.
"""
from pathlib import Path
import json
import sys

import numpy as np
from PIL import Image

from scaled_geometry import direction


def main() -> None:
    scene_path, runtime_path, output = map(Path, sys.argv[1:])
    scene, runtime = json.loads(scene_path.read_text()), json.loads(runtime_path.read_text())
    role = scene['scaled_control']['precheck_role']
    source_track = scene['scene']['casting_track_indices'][role]
    gate = json.loads(Path(runtime['casting_report']).read_text())
    result = {'gate': False, 'role': role, 'definition': 'Topmost row; median x tie; bbox center in pixel-index coordinates; explicit axis equality',
              'caveat': 'Topmost mask point may be head/ear rather than kicking leg'}
    anchor_track = gate['casting'].get(role)
    for label, summary_key, index, track in [
        ('source', 'source_summary', runtime['source_frame_index'], source_track),
        ('anchor', 'anchor_summary', 0, anchor_track),
    ]:
        summary = Path(runtime[summary_key])
        if track is None:
            result[label] = {'quadrant': 'CASTING_UNESTABLISHED', 'topmost_pixel': None}
            continue
        with Image.open(summary.parent/f'{index:03d}-track-{track:02d}.png') as image:
            result[label] = direction(np.asarray(image.convert('L')) > 0)
    result['quadrant_agreement'] = result['source']['quadrant'] == result['anchor']['quadrant']
    with output.open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
