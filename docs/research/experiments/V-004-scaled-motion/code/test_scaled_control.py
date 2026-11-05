"""CPU geometry fixtures, independent of private media."""
import numpy as np

from scaled_geometry import affine_layer, direction, fixed_scales, reflection_owners


def test_fixed_median_and_ig_snap() -> None:
    values = {'large': [1.2, 1.4, 1.6], 'small': [.95, 1.05, 1.08]}
    assert fixed_scales(values, 'small', (.9, 1.1)) == {'large': 1.4, 'small': 1.0}


def test_clipping_uses_unclipped_scaled_mask_pixels() -> None:
    mask = np.zeros((8, 8), bool)
    mask[4:8, 0:4] = True
    rgb = np.repeat((mask.astype(np.uint8)*255)[:, :, None], 3, axis=2)
    layer = affine_layer(rgb, mask, mask, 2, (2, 8))
    assert layer.unclipped_pixels == 64
    assert layer.visible_pixels == 48
    assert layer.clipped_fraction == .25
    assert layer.core.sum() == 48


def test_identity_affine_is_exact() -> None:
    mask = np.zeros((10, 12), bool)
    mask[2:8, 3:9] = True
    rgb = np.arange(360, dtype=np.uint8).reshape(10, 12, 3)
    layer = affine_layer(rgb, mask, mask, 1, (6, 8))
    assert np.array_equal(layer.rgb[mask], rgb[mask])
    assert np.array_equal(layer.core, mask)
    assert layer.clipped_fraction == 0


def test_reflections_follow_spatial_owner_not_track_number() -> None:
    boxes = {8: (10, 1, 20, 20), 3: (30, 1, 40, 20), 91: (30, 21, 40, 30), 12: (10, 21, 20, 30)}
    assert reflection_owners(boxes, {'left': 8, 'right': 3}, .5, 4)[0] == {91: 'right', 12: 'left'}


def test_g8_topmost_ties_use_median_and_axis_label() -> None:
    mask = np.zeros((8, 8), bool)
    mask[1, 1] = mask[1, 5] = True
    mask[5, 1:6] = True
    result = direction(mask)
    assert result['topmost_pixel'] == [3.0, 1.0]
    assert result['quadrant'] == 'UP_AXIS'
    mask[1, 5] = False
    assert direction(mask)['quadrant'] == 'UPPER_LEFT'


def test_hold_keeps_final_source_frame_once() -> None:
    from scaled_geometry import hold_indices
    indices = hold_indices(73, 2)
    assert len(indices) == 145
    assert indices == [index // 2 for index in range(145)]
    assert indices[-3:] == [71, 71, 72]


def test_full_cpu_pipeline(tmp_path) -> None:
    import hashlib
    import json
    import shutil
    import subprocess
    import sys
    from pathlib import Path
    from PIL import Image
    from scaled_io import describe
    ffmpeg = shutil.which('ffmpeg')
    assert ffmpeg, 'Existing ffmpeg required for CPU packaging fixture'
    code = Path(__file__).parent
    def save(path, value):
        path.write_text(json.dumps(value))
    source = tmp_path/'source'
    source.mkdir()
    frames = tmp_path/'frames'
    frames.mkdir()
    boxes = {0: (65, 12, 85, 36), 1: (20, 8, 32, 30), 8: (65, 40, 85, 55), 9: (20, 34, 32, 49)}
    rows = []
    for index in range(3):
        objects = []
        rgb = np.zeros((64, 128, 3), np.uint8)
        for track, (x0,y0,x1,y1) in boxes.items():
            mask = np.zeros((64,128), bool)
            mask[y0:y1,x0:x1] = True
            Image.fromarray(mask.astype('uint8')*255).save(source/f'{index:03d}-track-{track:02d}.png')
            objects.append(describe(track, mask))
            rgb[mask] = 255
        rows.append({'index':index,'objects':objects})
        Image.fromarray(rgb).save(frames/f'{index:03d}.png')
    summary = source/'summary.json'
    save(summary, {'coordinate_size':[128,64],'frames':rows})
    anchors=[]
    for index in range(3):
        folder=tmp_path/f'anchor{index}'
        folder.mkdir()
        for track in boxes:
            shutil.copy2(source/f'{index:03d}-track-{track:02d}.png',folder/f'000-track-{track:02d}.png')
        save(folder/'summary.json', {'coordinate_size':[128,64],'frames':[rows[0]]})
        save(folder/'gate.json', {'casting':{'Lab':0,'IG':1},'gates':{'G1':True,'G6':True}})
        anchors.append({'frame':index,'image':str(frames/f'{index:03d}.png'),'summary':str(folder/'summary.json'),'casting_report':str(folder/'gate.json')})
    canny=tmp_path/'canny.mkv'
    subprocess.run([ffmpeg,'-v','error','-framerate','24','-i',str(frames/'%03d.png'),'-c:v','ffv1',str(canny)],check=True)
    scene={'scene':{'casting_track_indices':{'Lab':0,'IG':1},'segment':{'frames':3},'reflection_rule':{'x_overlap_min_frac_of_narrower':.5,'lower_top_below_upper_bottom_minus_px':4}},'anchor_generation':{'resolution_master':[128,64]},'generation':{'resolution':[128,64],'fps':24,'variants':{'S3':{'hold_factor':2,'frames':5}}},'scaled_control':{'snap_role':'IG','precheck_role':'Lab','ig_snap_to_1_if_within':[.9,1.1],'edge_dilation_px':4,'precheck_mean_iou_notice_below':.5,'layer_roles':[{'role':'IG','kind':'body'},{'role':'IG','kind':'reflection'},{'role':'Lab','kind':'reflection'},{'role':'Lab','kind':'body'}]}}
    save(tmp_path/'scene.json',scene)
    runtime={'source_summary':str(summary),'canny_video':str(canny),'canny_sha256':hashlib.sha256(canny.read_bytes()).hexdigest(),'output_dir':str(tmp_path/'output'),'ffmpeg':ffmpeg,'anchors':anchors}
    save(tmp_path/'runtime.json',runtime)
    subprocess.run([sys.executable,str(code/'scaled_control.py'),str(tmp_path/'scene.json'),str(tmp_path/'runtime.json')],check=True)
    report=json.loads((tmp_path/'output/SCALED_CONTROL.json').read_text())
    assert report['scales']=={'Lab':1.,'IG':1.}
    assert report['precheck_mean_iou']==1.
    assert report['hold_source_indices']==[0,0,1,1,2]
    assert report['frames'][0]['reflection_owners']=={'8':'Lab','9':'IG'}
    assert (tmp_path/'output/reviews/keyframe-triptych.jpg').is_file()
    assert len(list((tmp_path/'output/scaled_repeat_frames').glob('*.png')))==5
