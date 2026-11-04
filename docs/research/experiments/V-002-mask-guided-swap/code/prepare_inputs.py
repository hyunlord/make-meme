# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "pillow", "opencv-python"]
# ///
# Run: existing research Python prepare_inputs.py /private/input-config.json [--cpu-only]
"""V-002 fixed CPU inputs from preserved V-001 RGB, masks, anchor and depth."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Final, TypedDict

import numpy as np
from PIL import Image

from input_geometry import (condition, dilate, generation_rgb, ltx_geometry, read_mask,
                            read_rgb, sha256, subject_reference, vace_geometry, write_rgb)

DEPTH_SHA: Final = '11debd60bfdd02cea8e7fe3d52a02f0f626c7023a9cf55ae9a20644d53fd9181'
ANCHOR_SHA: Final = '071f9e5e3b2c8b110aadd254838415d740b433f9b726bbf18a6117f25c81e779'


class Config(TypedDict):
    source_frames: str
    source_masks: str
    anchor: str
    anchor_masks: str
    depth_raw: str
    output: str
    ffmpeg: str
    ffprobe: str


def validate(config: Config) -> list[Path]:
    assert set(config) == set(Config.__annotations__)
    assert all(Path(value).is_absolute() for value in config.values())
    paths = [Path(config['source_frames']) / f'{i:03d}.png' for i in range(73)]
    paths += [Path(config['source_masks']) / f'{i:03d}-track-{track:02d}.png'
              for i in range(73) for track in range(4)]
    paths += [Path(config['anchor_masks']) / f'000-track-{track:02d}.png' for track in (0, 1)]
    paths += [Path(config['anchor']), Path(config['depth_raw'])]
    assert all(path.is_file() for path in paths)
    assert sha256(Path(config['anchor'])) == ANCHOR_SHA
    assert sha256(Path(config['depth_raw'])) == DEPTH_SHA
    for path in paths[:-1]:
        with Image.open(path) as image:
            assert image.size == (1280, 720), (path.name, image.size)
    assert not Path(config['output']).exists()
    assert Path(config['output']).parent.is_dir()
    return paths


def main() -> None:
    config: Config = json.loads(Path(sys.argv[1]).read_text())
    input_paths = validate(config)
    with np.load(config['depth_raw'], allow_pickle=False) as archive:
        depths = archive['depths'].copy()
    assert depths.shape == (73, 576, 1024) and np.isfinite(depths).all()
    if '--cpu-only' in sys.argv:
        print(json.dumps({'status': 'CPU_INPUTS_VALIDATED', 'frames': 73, 'inputs': len(input_paths),
                          'torch_imported': 'torch' in sys.modules, 'model_loads': 0}))
        return
    import cv2

    output = Path(config['output'])
    temporary = output.with_name(output.name + '.building')
    temporary.mkdir()
    folders = ['source', 'masks', 'depth', 'references', 'ltx-source', 'canny']
    folders += [f'{variant}/{kind}' for variant in ('M1', 'M2', 'M3') for kind in ('frames', 'masks')]
    for folder in folders:
        (temporary / folder).mkdir(parents=True)
    input_hashes = {f'{path.parent.name}/{path.name}': sha256(path) for path in input_paths}
    assert len(input_hashes) == len(input_paths), 'Input role names must not collide'
    resized_depth = np.stack([np.asarray(vace_geometry(Image.fromarray(frame.astype(np.float32))))
                              for frame in depths])
    lower, upper = float(resized_depth.min()), float(resized_depth.max())
    assert upper > lower and resized_depth.shape == (73, 480, 832)
    depth_uint8 = ((resized_depth - lower) / (upper - lower) * 255).astype(np.uint8)
    anchor = read_rgb(Path(config['anchor']))
    native_anchor = np.asarray(vace_geometry(Image.fromarray(anchor)))
    write_rgb(temporary / 'anchor.png', native_anchor)
    write_rgb(temporary / 'ltx-anchor.png', np.asarray(ltx_geometry(Image.fromarray(anchor))))
    reference_rows = {}
    for role, track in [('Lab', 0), ('IG', 1)]:
        reference, bbox = subject_reference(anchor, read_mask(Path(config['anchor_masks']) / f'000-track-{track:02d}.png'))
        write_rgb(temporary / 'references' / f'{role}.png', reference)
        reference_rows[role] = {'anchor_track_index': track, 'canonical_bbox': bbox,
                                'size': [832, 480], 'background_rgb': [255, 255, 255]}
    frame_rows = []
    expected_canny = hashlib.sha256()
    for index in range(73):
        name = f'{index:03d}.png'
        canonical = read_rgb(Path(config['source_frames']) / name)
        source = np.asarray(vace_geometry(Image.fromarray(canonical)))
        ltx_source = np.asarray(ltx_geometry(Image.fromarray(canonical)))
        write_rgb(temporary / 'source' / name, source)
        write_rgb(temporary / 'ltx-source' / name, ltx_source)
        union = np.zeros((480, 832), dtype=bool)
        track_rows = []
        for track, radius in enumerate((24, 12, 12, 12)):
            original = read_mask(Path(config['source_masks']) / f'{index:03d}-track-{track:02d}.png')
            native = np.asarray(vace_geometry(Image.fromarray(original.astype(np.uint8) * 255), nearest=True)) > 0
            expanded = dilate(native, radius)
            union |= expanded
            track_rows.append({'track_index': track, 'radius_px': radius,
                               'native_area': int(native.sum()), 'dilated_area': int(expanded.sum())})
        mask = generation_rgb(union)
        assert np.array_equal(mask[:, :, 0], mask[:, :, 1]) and np.array_equal(mask[:, :, 1], mask[:, :, 2])
        assert set(np.unique(mask).tolist()) <= {0, 255}
        write_rgb(temporary / 'masks' / name, mask)
        depth = np.repeat(depth_uint8[index, :, :, None], 3, axis=2)
        write_rgb(temporary / 'depth' / name, depth)
        gray = np.full_like(source, 127)
        m1, m2 = condition(source, union, gray), condition(source, union, depth)
        for variant, rgb in [('M1', m1), ('M2', m2), ('M3', native_anchor if index == 0 else m1)]:
            actual_mask = np.zeros_like(mask) if variant == 'M3' and index == 0 else mask
            write_rgb(temporary / variant / 'frames' / name, rgb)
            write_rgb(temporary / variant / 'masks' / name, actual_mask)
            if variant != 'M3' or index != 0:
                assert np.array_equal(rgb[~union], source[~union])
        # Installed official LTX compute_reference recipe: float RGB luminance, uint8, cv2.Canny.
        rgb_float = ltx_source.astype(np.float32) / 255.0
        grayscale = (rgb_float[:, :, 0] * .2989 + rgb_float[:, :, 1] * .587 + rgb_float[:, :, 2] * .114)
        edges = cv2.Canny((grayscale * 255).astype(np.uint8), threshold1=92, threshold2=200)
        canny = np.repeat(edges[:, :, None], 3, axis=2)
        write_rgb(temporary / 'canny' / name, canny)
        expected_canny.update(canny.tobytes())
        frame_rows.append({'index': index, 'source_index': 240 + index, 'tracks': track_rows,
                           'union_area': int(union.sum()), 'union_fraction': float(union.mean()),
                           'rgb_channel_values': sorted(np.unique(mask).tolist()), 'channels_equal': True,
                           'M3_frame0_all_keep': index == 0, 'outside_source_exact_except_M3_frame0': True})
    subprocess.run([config['ffmpeg'], '-v', 'error', '-n', '-framerate', '24', '-i',
                    str(temporary / 'canny' / '%03d.png'), '-c:v', 'ffv1', '-level', '3',
                    '-pix_fmt', 'gbrp', str(temporary / 'canny.mkv')], check=True)
    decoded = hashlib.sha256()
    with subprocess.Popen([config['ffmpeg'], '-v', 'error', '-i', str(temporary / 'canny.mkv'),
                           '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], stdout=subprocess.PIPE) as process:
        assert process.stdout is not None
        for chunk in iter(lambda: process.stdout.read(1024 * 1024), b''):
            decoded.update(chunk)
        assert process.wait() == 0
    assert decoded.hexdigest() == expected_canny.hexdigest()
    info = json.loads(subprocess.check_output([config['ffprobe'], '-v', 'error', '-select_streams', 'v:0',
         '-count_frames', '-show_entries', 'stream=width,height,nb_read_frames,r_frame_rate', '-of', 'json',
         str(temporary / 'canny.mkv')], text=True))['streams'][0]
    assert (info['width'], info['height'], int(info['nb_read_frames']), info['r_frame_rate']) == (1152, 640, 73, '24/1')
    assert all(sha256(path) == input_hashes[f'{path.parent.name}/{path.name}'] for path in input_paths)
    assert 'torch' not in sys.modules
    report = {'status': 'CPU_INPUTS_PREPARED', 'frames': 73, 'fps': 24, 'vace_size': [832, 480],
        'geometry': '1280x720 -> bilinear853x480 -> crop(10,0,842,480); masks nearest before dilation',
        'dilation': 'square Chebyshev radius24 Lab,12 IG,12 each reflection; union after dilation',
        'white_rgb': [255, 255, 255], 'mask_channels_equal_all_frames': True,
        'references': reference_rows, 'reference_resize': 'PIL bilinear aspect-fit and centered white832x480 canvas',
        'reference_convention': 'ali-vilab/VACE prepare_source aspect-fit white; supplied native-size references avoid loader resize',
        'depth': {'source_sha256': DEPTH_SHA, 'min': lower, 'max': upper,
                  'normalization': 'global min/max over all73 resampled frames, uint8 truncation', 'new_inference_calls': 0},
        'canny': {'size': [1152, 640], 'thresholds': [92, 200], 'official_installed_thresholds': [100, 200],
                  'threshold_note': 'User-fixed92 overrides installed100 before results; no implicit512 resize',
                  'recipe': 'installed LTX compute_reference float RGB luminance0.2989/0.587/0.114 thenuint8 cv2.Canny',
                  'decoded_rgb_sha256': decoded.hexdigest(), 'lossless_readback': True},
        'frames_detail': frame_rows, 'input_hashes': input_hashes,
        'output_hashes': {str(path.relative_to(temporary)): sha256(path) for path in sorted(temporary.rglob('*')) if path.is_file()},
        'model_loads': 0, 'new_sam_calls': 0, 'torch_imported': False}
    (temporary / 'MASK_CHECK.json').write_text(json.dumps(report, indent=2) + '\n')
    temporary.replace(output)
    print(json.dumps({'status': report['status'], 'mask_check_sha256': sha256(output / 'MASK_CHECK.json')}))


if __name__ == '__main__':
    main()
