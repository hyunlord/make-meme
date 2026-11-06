# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "Pillow"]
# ///
"""CPU seam report: existing Python v006_metrics_seams.py SCENE RUNTIME OUTPUT.

Runtime: base_frames, full_window_frames, legs_only_frames. Measures actual PNG
RGB transitions in native coordinates; ratios are descriptive, not pass gates.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image


def transitions(folder: Path, count: int) -> list[float]:
    values = []
    previous = None
    for index in range(count):
        with Image.open(folder / f'{index:03d}.png') as image:
            current = np.asarray(image.convert('RGB'), dtype=np.float64)
        if previous is not None:
            values.append(float(np.abs(current - previous).mean()))
        previous = current
    return values


def main() -> None:
    scene_path, runtime_path, destination = map(Path, sys.argv[1:])
    scene, runtime = json.loads(scene_path.read_text()), json.loads(runtime_path.read_text())
    if destination.exists():
        raise FileExistsError(destination)
    ramps = scene['reinsertion']['full_window']['linear_blend']
    regions = [tuple(ramps[key]) for key in ('in', 'out')]
    count = scene['scene']['segment']['frames']
    boundary = {i for start, end in regions for i in range(start, end + 1)}
    context = {i for start, end in regions for i in range(max(1, start - (end - start + 1)),
                                                        min(count, end + (end - start + 1) + 1))} - boundary
    result = {}
    base = transitions(Path(runtime['base_frames']), count)
    for key in ('base_frames', 'full_window_frames', 'legs_only_frames'):
        values = base if key == 'base_frames' else transitions(Path(runtime[key]), count)
        surround = float(np.mean([values[i - 1] for i in sorted(context)]))
        edge = [values[i - 1] for i in sorted(boundary)]
        result[key] = {'transitions': [{'frame': i, 'rgb_mae': value,
                                      'ratio_to_input': value / base[i - 1] if base[i - 1] else None,
                                      'boundary': i in boundary} for i, value in enumerate(values, 1)],
                       'boundary_mean': float(np.mean(edge)), 'boundary_maximum': max(edge),
                       'surrounding_mean': surround,
                       'boundary_mean_over_surrounding': float(np.mean(edge)) / surround if surround else None}
    payload = {'status': 'MEASURED', 'automatic_ranking': False, 'quality': 'HUMAN_REVIEW_PENDING',
               'definition': 'Native RGB absolute consecutive-frame difference; transition i is frame i-1 to i.',
               'context_definition': 'One ramp-length before/after each boundary interval, excluding both intervals.',
               'boundary_indices': sorted(boundary), 'surrounding_indices': sorted(context), 'outputs': result}
    temporary = destination.with_suffix('.tmp')
    temporary.write_text(json.dumps(payload, indent=2, allow_nan=False) + '\n')
    json.loads(temporary.read_text())
    temporary.rename(destination)


if __name__ == '__main__':
    main()
