# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "scipy", "Pillow"]
# ///
"""CPU reinsertion: existing Python v006_composite.py SCENE PRIVATE_RUNTIME.

Runtime: base_frames (whole clip), refined_frames (local indices), output_summary,
casting_report, output_dir, ffmpeg. Scene requires explicit composition_policy.
No inference, source mutation, or output overwrites.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

import numpy as np
from PIL import Image

from v006_composite_core import BlendPolicy, leg_alpha, mix, temporal_weight


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    scene_path, runtime_path = map(Path, sys.argv[1:])
    scene, runtime = json.loads(scene_path.read_text()), json.loads(runtime_path.read_text())
    shape = tuple(scene['common']['resolution'])
    count = scene['scene']['segment']['frames']
    first, last = scene['refine_window']['segment_frames']
    numeric = scene['composition_policy']
    ramps = scene['reinsertion']['full_window']['linear_blend']
    policy = BlendPolicy((first, last), tuple(ramps['in']), tuple(ramps['out']),
                         numeric['lower_fraction'], numeric['dilation_px'], numeric['feather_px'])
    base, refined = Path(runtime['base_frames']), Path(runtime['refined_frames'])
    summary_path = Path(runtime['output_summary'])
    summary, casting = json.loads(summary_path.read_text()), json.loads(Path(runtime['casting_report']).read_text())
    rows = {r['frame']: r for r in casting['frames']}
    expected = scene['refine_window']['frames']
    if summary['frame_count'] != expected or summary['coordinate_size'] != list(shape):
        raise RuntimeError('Actual SAM geometry does not match refined clip')
    if set(rows) != set(range(first, last + 1)):
        raise RuntimeError('Casting report must use complete global refinement indices')
    target = casting['casting'].get(scene['measurement_policy']['role']) if casting['casting'] else None
    output = Path(runtime['output_dir'])
    output.mkdir(parents=True, exist_ok=False)
    folders = [output / 'full_window', output / 'legs_only']
    for folder in folders:
        folder.mkdir()
    manifest = []
    for index in range(count):
        original = base / f'{index:03d}.png'
        paths = [folder / original.name for folder in folders]
        weight = temporal_weight(index, policy)
        if not first <= index <= last or weight == 0:
            for destination in paths:
                shutil.copyfile(original, destination)
            manifest.append({'frame': index, 'temporal_weight': weight, 'status': 'BASE_BYTE_EXACT',
                             'base_sha256': digest(original), 'full_sha256': digest(paths[0]),
                             'legs_sha256': digest(paths[1]), 'local_exterior_byte_exact': True})
            continue
        local = index - first
        with Image.open(original) as im:
            rgb = np.asarray(im.convert('RGB'))
        with Image.open(refined / f'{local:03d}.png') as im:
            changed = np.asarray(im.convert('RGB'))
        if rgb.shape != (*shape[::-1], 3) or changed.shape != rgb.shape:
            raise RuntimeError('Refined/native input geometry mismatch')
        body = np.zeros(shape[::-1], dtype=bool)
        detected = target is not None and target in rows[index]['actual_tracks']
        if detected:
            with Image.open(summary_path.parent / f'{local:03d}-track-{target:02d}.png') as im:
                body = np.asarray(im.convert('L')) > 0
        alpha = leg_alpha(body, index, policy)
        full = mix(rgb, changed, np.full(shape[::-1], weight))
        legs = mix(rgb, changed, alpha)
        for pixels, destination in zip((full, legs), paths, strict=True):
            Image.fromarray(pixels).save(destination)
        with Image.open(paths[1]) as im:
            exact = bool(np.array_equal(np.asarray(im)[alpha == 0], rgb[alpha == 0]))
        if not exact:
            raise RuntimeError('Local exterior preservation failed')
        manifest.append({'frame': index, 'temporal_weight': weight,
                         'status': 'COMPOSITED' if detected else 'MISSING_LAB_LOCAL_BASE_ONLY',
                         'local_exterior_byte_exact': exact, 'local_edited_pixels': int((alpha > 0).sum()),
                         'base_sha256': digest(original), 'refined_sha256': digest(refined / f'{local:03d}.png'),
                         'full_sha256': digest(paths[0]), 'legs_sha256': digest(paths[1])})
    for folder in folders:
        subprocess.run([runtime['ffmpeg'], '-v', 'error', '-nostdin', '-n', '-threads', '2',
                        '-framerate', str(scene['common']['fps']), '-i', str(folder / '%03d.png'),
                        '-an', '-c:v', 'libx264', '-threads', '2', '-crf', '18', '-pix_fmt', 'yuv420p',
                        '-movflags', '+faststart', str(folder.with_suffix('.mp4'))], check=True)
    payload = {'status': 'CPU_REINSERTION_COMPLETE', 'kind': 'CPU_DERIVATIVES_NOT_MODEL_OUTPUT',
               'scene_sha256': digest(scene_path), 'runtime_sha256': digest(runtime_path),
               'frames': manifest, 'raw_refinement_untouched': True,
               'quality': 'HUMAN_REVIEW_PENDING', 'temporal': 'UNVERIFIED'}
    temporary = output / 'COMPOSITE_MANIFEST.tmp'
    temporary.write_text(json.dumps(payload, indent=2, allow_nan=False) + '\n')
    if json.loads(temporary.read_text()) != payload:
        raise RuntimeError('Manifest readback mismatch')
    temporary.rename(output / 'COMPOSITE_MANIFEST.json')


if __name__ == '__main__':
    main()
