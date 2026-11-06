"""CPU fixtures for thresholds, missing coverage and local composite boundaries."""
import json
from pathlib import Path
import numpy as np
import pytest
from leg_core import Policy, leg_region, frame_metrics, local_alpha, blend, summarize

@pytest.fixture
def policy():
    return Policy((1280,720),'Lab',.45,4,3,(70.,170.),60.,(.299,.587,.114),((0.,1.,0.),(1.,-4.,1.),(0.,1.,0.)),'reflect',(14,34),12,8,(14,17),(31,34))

def test_exact_gray_dark_thresholds(policy):
    # Given a uniform real-body mask, excluded reflection and threshold pixels.
    body=np.ones((20,20),dtype=bool); reflected=np.zeros_like(body)
    rgb=np.full((20,20,3),255,dtype=np.uint8)
    rgb[11:,:, :]=70;rgb[11:,0:10,:]=59
    # When the configured leg metric reads the frame.
    row=frame_metrics(rgb,body,reflected,np.ones_like(body),policy)
    # Then half the dark-or-grey denominator is grey.
    assert row['semi_transparency_ratio']==pytest.approx(.5)

def test_reflections_and_upper_body_excluded(policy):
    body=np.zeros((50,50),bool);body[5:35,10:30]=True
    reflection=np.zeros_like(body);reflection[30:45]=True
    # When a leg region is formed.
    region=leg_region(body,reflection,np.ones_like(body),policy)
    # Then it never includes the upper body or reflection.
    assert not region[:21].any();assert not (region & reflection).any()

def test_missing_and_zero_denominator_remain_null(policy):
    rgb=np.full((20,20,3),255,np.uint8);mask=np.ones((20,20),bool)
    # When no dark/grey pixels or no detected Lab exist.
    assert frame_metrics(rgb,mask,np.zeros_like(mask),mask,policy)['semi_transparency_ratio'] is None
    assert frame_metrics(rgb,None,np.zeros_like(mask),mask,policy)['status']=='MISSING_LAB'

def test_temporal_edges_and_exterior_byte_exact(policy):
    body=np.zeros((80,80),bool);body[10:60,20:50]=True
    base=np.full((80,80,3),31,np.uint8); refined=np.full_like(base,189)
    # When local edits are composed at ramp ends and the active middle.
    for t in (0,14,34,72):
        assert np.array_equal(blend(base,refined,local_alpha(body,t,policy)),base)
    alpha=local_alpha(body,20,policy);result=blend(base,refined,alpha)
    # Then exterior is original and core is refined.
    assert np.array_equal(result[alpha==0],base[alpha==0])
    assert np.array_equal(result[alpha==1],refined[alpha==1])

def test_missing_frames_not_silently_hidden(policy):
    rows=[{'frame':i,'semi_transparency_ratio':None if i==14 else .2,'edge_laplacian_variance':2.} for i in range(73)]
    # When aggregation sees a missing window value.
    result=summarize(rows,policy)
    # Then observed coverage is explicit; no zero imputation.
    assert result['semi_transparency_ratio']['window']['observed']==20
    assert result['semi_transparency_ratio']['window']['total']==21
    assert result['semi_transparency_ratio']['window']['mean']==pytest.approx(.2)

def test_inverse_crop_has_explicit_invalid_rows():
    from leg_io import Canvas
    # Given parent native crop1152x640 from1152x648.
    canvas=Canvas((1280,720),(1152,640))
    # When inverse mapping constructs valid pixels.
    valid=canvas.valid()
    # Then crop loss isn't counted as fabricated RGB.
    assert valid.shape==(720,1280)
    assert not valid[0].any() and not valid[-1].any()
    assert valid[360].all()

def test_real_cli_outputs_keep_input_and_exterior(tmp_path):
    import subprocess,sys
    from PIL import Image
    # Given tiny real PNGs/SAM summaries and a scene policy, no mock image reader.
    policy_json={'measurement_policy':{'master_size':[64,40],'role':'Lab','lower_fraction':.45,
        'mask_dilation_px':4,'boundary_band_px':3,'gray_luma_inclusive':[70,170],
        'dark_luma_exclusive_max':60,'luma_rgb_weights':[.299,.587,.114],
        'laplacian_kernel':[[0,1,0],[1,-4,1],[0,1,0]],'laplacian_border':'reflect',
        'window_inclusive':[1,2],'local_dilation_px':12,'local_feather_px':8,
        'local_ramp_in':[0,1],'local_ramp_out':[2,3]}}
    policy_json['measurement_policy']['master_size']=[64,40]
    policy_json['measurement_policy']['window_inclusive']=[1,2]
    policy_json['measurement_policy']['local_ramp_in']=[0,1]
    policy_json['measurement_policy']['local_ramp_out']=[2,3]
    scene=tmp_path/'scene.json';scene.write_text(json.dumps(policy_json))
    for name in ('raw','base','sam'): (tmp_path/name).mkdir()
    mask=np.zeros((40,64),np.uint8);mask[3:32,20:40]=255
    summary={'coordinate_size':[64,40],'frames':[]};base={'casting':{'Lab':0},'casting_status':'ESTABLISHED','frames':[]}
    for i in range(4):
        Image.fromarray(np.full((40,64,3),90,np.uint8)).save(tmp_path/'raw'/f'{i:03d}.png')
        Image.fromarray(np.full((40,64,3),20,np.uint8)).save(tmp_path/'base'/f'{i:03d}.png')
        Image.fromarray(mask).save(tmp_path/'sam'/f'{i:03d}-track-00.png')
        summary['frames'].append({'index':i,'objects':[{'track_index':0,'present':True}]})
        base['frames'].append({'frame':i,'actual_tracks':[0],'reflection_tracks':[]})
    sp=tmp_path/'sam'/'summary.json';sp.write_text(json.dumps(summary));bp=tmp_path/'base.json';bp.write_text(json.dumps(base))
    (tmp_path/'input-sam').mkdir()
    input_summary=json.loads(json.dumps(summary));input_base=json.loads(json.dumps(base))
    for i in range(4):
        source_mask=mask.copy()
        if i==1:
            source_mask[:]=0;source_mask[3:32,25:45]=255
        if i==2:
            input_summary['frames'][i]['objects'][0]['present']=False
            input_base['frames'][i]['actual_tracks']=[]
        Image.fromarray(source_mask).save(tmp_path/'input-sam'/f'{i:03d}-track-00.png')
    isp=tmp_path/'input-sam'/'summary.json';isp.write_text(json.dumps(input_summary))
    ibp=tmp_path/'input-base.json';ibp.write_text(json.dumps(input_base))
    runtime={'raw_frames':str(tmp_path/'raw'),'output_summary':str(sp),'base_metrics':str(bp),
             'native_size':[64,40],'frame_count':4,'input_summary':str(isp),'input_base_metrics':str(ibp)}
    rp=tmp_path/'runtime.json';rp.write_text(json.dumps(runtime));out=tmp_path/'metrics.json'
    # When CLI runs against actual files, then all rows and coverage are measured.
    subprocess.run([sys.executable,str(Path(__file__).with_name('leg_metrics.py')),str(scene),str(rp),str(out)],check=True)
    result=json.loads(out.read_text());assert len(result['frames'])==4
    assert result['summary']['semi_transparency_ratio']['window']['mean']==1.
    assert result['frames'][0]['lab_mask_iou_vs_input']==1.
    assert result['frames'][1]['lab_mask_iou_vs_input']==pytest.approx(.6)
    assert result['frames'][2]['lab_mask_iou_vs_input'] is None
    assert result['frames'][2]['input_iou_status']=='MISSING_MASK'
    assert result['input_mask_iou']['observed']==3
    assert result['input_mask_iou']['mean']==pytest.approx(2.6/3)
    runtime.update(base_frames=str(tmp_path/'base'),refined_frames=str(tmp_path/'raw'),output_dir=str(tmp_path/'local'))
    rp.write_text(json.dumps(runtime))
    subprocess.run([sys.executable,str(Path(__file__).with_name('leg_local.py')),str(scene),str(rp)],check=True)
    assert np.array_equal(np.asarray(Image.open(tmp_path/'local'/'000.png')),np.asarray(Image.open(tmp_path/'base'/'000.png')))
    assert all(r['exterior_byte_exact'] for r in json.loads((tmp_path/'local'/'LOCAL_MANIFEST.json').read_text())['frames'])
