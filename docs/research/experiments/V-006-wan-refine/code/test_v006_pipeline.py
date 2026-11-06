# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "Pillow", "pytest"]
# ///
"""Real CPU CLI fixtures: python -m pytest test_v006_pipeline.py."""
import json
from pathlib import Path
import shutil
import subprocess
import sys

import numpy as np
from PIL import Image
import pytest


def test_compositor_cli_preserves_input_and_writes_both_derivatives(tmp_path: Path) -> None:
    # Given a short native input, a contrasting refinement and explicit casting.
    ffmpeg = shutil.which('ffmpeg')
    if ffmpeg is None:
        pytest.skip('Existing ffmpeg is unavailable; no installation permitted')
    base, refined, sam = [tmp_path / name for name in ('base', 'refined', 'sam')]
    for folder in (base, refined, sam):
        folder.mkdir()
    for index in range(15):
        Image.new('RGB', (30, 20), (20, 40, 60)).save(base / f'{index:03d}.png')
    for index in range(11):
        Image.new('RGB', (30, 20), (220, 140, 160)).save(refined / f'{index:03d}.png')
        mask = np.zeros((20, 30), dtype=np.uint8)
        mask[2:16, 10:20] = 255
        Image.fromarray(mask).save(sam / f'{index:03d}-track-07.png')
    (sam / 'summary.json').write_text(json.dumps({'frame_count': 11, 'coordinate_size': [30, 20]}))
    casting = tmp_path / 'casting.json'
    casting.write_text(json.dumps({'casting': {'Lab': 7}, 'frames': [
        {'frame': i, 'actual_tracks': [7]} for i in range(2, 13)]}))
    scene = tmp_path / 'scene.json'
    scene.write_text(json.dumps({'common': {'resolution': [30, 20], 'fps': 24},
        'scene': {'segment': {'frames': 15}}, 'refine_window': {'segment_frames': [2, 12], 'frames': 11},
        'composition_policy': {'lower_fraction': .45, 'dilation_px': 2, 'feather_px': 2},
        'reinsertion': {'full_window': {'linear_blend': {'in': [2, 4], 'out': [10, 12]}}},
        'measurement_policy': {'role': 'Lab'}}))
    output = tmp_path / 'composite'
    runtime = tmp_path / 'runtime.json'
    runtime.write_text(json.dumps({'base_frames': str(base), 'refined_frames': str(refined),
        'output_summary': str(sam / 'summary.json'), 'casting_report': str(casting),
        'output_dir': str(output), 'ffmpeg': ffmpeg}))
    source_bytes = (base / '005.png').read_bytes()
    # When the actual CLI performs PNG composition and ffmpeg packaging.
    subprocess.run([sys.executable, str(Path(__file__).with_name('v006_composite.py')),
                    str(scene), str(runtime)], check=True, capture_output=True)
    # Then the input, zero-weight endpoints and exterior remain exact.
    assert (base / '005.png').read_bytes() == source_bytes
    for index in (0, 1, 2, 12, 13, 14):
        for role in ('full_window', 'legs_only'):
            assert (output / role / f'{index:03d}.png').read_bytes() == (base / f'{index:03d}.png').read_bytes()
    manifest = json.loads((output / 'COMPOSITE_MANIFEST.json').read_text())
    assert all(row['local_exterior_byte_exact'] for row in manifest['frames'])
    assert (output / 'full_window.mp4').stat().st_size > 0
    assert (output / 'legs_only.mp4').stat().st_size > 0
    with Image.open(output / 'full_window' / '005.png') as image:
        assert np.array_equal(np.asarray(image)[0, 0], [220, 140, 160])


def test_child_sample_links_parent_without_modifying_it(tmp_path: Path) -> None:
    # Given a real parent record and a real output artifact.
    parent = tmp_path / 'parent.json'
    parent.write_text(json.dumps({'sample_id': 'prior/input', 'run_id': 'input'}))
    before = parent.read_bytes()
    artifact = tmp_path / 'output.bin'
    artifact.write_bytes(b'fixture-output')
    inherited = Path(__file__).resolve().parents[2] / 'V-005-leg-sharpness' / 'code'
    manifest = tmp_path / 'manifest.json'
    manifest.write_text(json.dumps({'inherited_builder_code': str(inherited),
        'parent_sample_path': str(parent), 'sample': {'sample_id': 'new/refinement',
        'run_id': 'refinement', 'outputs': {'raw': {'asset_path': str(artifact)}}}}))
    target = tmp_path / 'SAMPLE.json'
    # When a child record is published.
    subprocess.run([sys.executable, str(Path(__file__).with_name('v006_sample.py')),
                    str(manifest), str(target)], check=True, capture_output=True)
    # Then lineage hashes exist, parent bytes remain intact and quality stays pending.
    record = json.loads(target.read_text())
    assert record['schema_version'] == '1.1'
    assert record['parent_sample']['sample_id'] == 'prior/input'
    assert len(record['parent_sample']['sha256']) == 64
    assert parent.read_bytes() == before
    assert record['human_review'] == {'status': 'PENDING', 'form_values': None, 'source_form': None}
