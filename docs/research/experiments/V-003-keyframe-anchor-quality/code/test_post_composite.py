"""CPU pixel-contract and CLI fixtures for the separate POST derivative."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

import numpy as np
from PIL import Image


def test_core_exterior_and_feather() -> None:
    # Given: different uniform source/RAW, a body and finite dilation/feather.
    from post_composite import compose, feather_alpha
    core = np.zeros((40, 40), bool)
    core[15:25, 15:25] = True
    source = np.full((40, 40, 3), 20, np.uint8)
    raw = np.full_like(source, 220)
    # When: compositing with a five-pixel envelope and three-pixel feather.
    alpha = feather_alpha(core, np.pad(np.ones((20, 20), bool), 10), 3)
    result = compose(source, raw, alpha)
    # Then: every core byte is RAW, exterior source, transition mixed.
    assert np.array_equal(result[core], raw[core])
    assert np.array_equal(result[0], source[0])
    assert np.any((result[:, :, 0] > 20) & (result[:, :, 0] < 220))


def test_reflection_uses_corresponding_body_height() -> None:
    # Given: a short reflection beneath a taller body.
    from post_composite import Instance, expanded_union
    body = np.zeros((100, 100), bool)
    reflection = body.copy()
    body[10:50, 30:40] = True
    reflection[55:65, 30:40] = True
    instances = [Instance(0, body), Instance(2, reflection)]
    # When: the configured reflection rule and 15 percent dilation are applied.
    core, expanded, records = expanded_union(instances, (0.5, 4), 0.15)
    # Then: reflection receives the body's six-pixel radius, not its own two.
    assert records[1]['body_track'] == 0
    assert records[1]['radius_px'] == 6
    assert expanded[70, 35] and not core[70, 35]


def test_geometry_crop_does_not_invent_missing_rows() -> None:
    # Given: a source canvas with row-coded pixel intensities.
    from post_composite import Geometry
    geometry = Geometry((16, 10), (16, 8))
    source = Image.fromarray(np.repeat(np.arange(10, dtype=np.uint8)[:, None], 16, axis=1))
    # When: applying the exact aspect resize and center crop.
    result = np.asarray(geometry.transform(source, mask=True))
    # Then: only real source rows one through eight survive.
    assert result[:, 0].tolist() == list(range(1, 9))


def test_cli_preserves_raw_and_refuses_existing_output(tmp_path: Path) -> None:
    # Given: a complete one-frame local fixture with differently located masks.
    source, raw, source_sam, output_sam = [tmp_path/name for name in ('source', 'raw', 'source_sam', 'output_sam')]
    for folder in (source, raw, source_sam, output_sam):
        folder.mkdir()
    Image.new('RGB', (40, 40), (20, 20, 20)).save(source/'000.png')
    Image.new('RGB', (40, 40), (220, 220, 220)).save(raw/'000.png')
    for folder, x in ((source_sam, 10), (output_sam, 20)):
        mask = np.zeros((40, 40), np.uint8)
        mask[10:25, x:x+5] = 255
        Image.fromarray(mask).save(folder/'000-track-00.png')
        (folder/'summary.json').write_text(json.dumps({'coordinate_size':[40,40], 'frames':[{'index':0, 'objects':[{'track_index':0,'present':True}]}]}))
    config = {'anchor_generation':{'resolution_master':[40,40]},'generation':{'resolution':[40,40],'frames':1},'scene':{'reflection_rule':{'x_overlap_min_frac_of_narrower':0.5,'lower_top_below_upper_bottom_minus_px':4}},'post_composite':{'dilation_fraction':0.15,'feather_px':3}}
    runtime = {'source_frames':str(source),'raw_frames':str(raw),'source_summary':str(source_sam/'summary.json'),'output_summary':str(output_sam/'summary.json'),'output_dir':str(tmp_path/'post')}
    scene_file, runtime_file = tmp_path/'scene.json', tmp_path/'runtime.json'
    scene_file.write_text(json.dumps(config));runtime_file.write_text(json.dumps(runtime))
    before = hashlib.sha256((raw/'000.png').read_bytes()).hexdigest()
    command = [sys.executable,str(Path(__file__).with_name('post_composite.py')),str(scene_file),str(runtime_file)]
    # When: the actual CLI produces a new derivative.
    result = subprocess.run(command, capture_output=True, text=True)
    # Then: original bytes persist and both source/output object cores remain RAW.
    assert result.returncode == 0, result.stderr
    assert hashlib.sha256((raw/'000.png').read_bytes()).hexdigest() == before
    post = np.asarray(Image.open(tmp_path/'post/000.png'))
    assert post[15,12,0] == 220 and post[15,22,0] == 220 and post[0,0,0] == 20
    assert (tmp_path/'post/regions/000.png').is_file()
    assert (tmp_path/'post/alpha/000.png').is_file()
    second = subprocess.run(command, capture_output=True, text=True)
    assert second.returncode != 0
