"""CPU case/serialization/writer regressions; no pretrained models or CUDA."""
import hashlib
import json
from pathlib import Path
import subprocess
import pytest
import torch
from contracts import case_contract,verify_cache_receipt
from artifacts import save_tree,load_tree

@pytest.mark.parametrize('name,shape,fps',[('official',[16,5,64,112],16),('lab',[16,5,112,64],24),('self',[16,5,112,64],24)])
def test_case_geometry_and_native_writer(tmp_path,name,shape,fps):
    contract=case_contract(name)
    assert contract.latent_shape==shape and contract.fps==fps
    out=tmp_path/'fixture.mp4'
    subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i',f'color=c=black:s=32x32:r={fps}','-frames:v','17','-c:v','libx264',str(out)],check=True)
    stream=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-of','json',str(out)]))['streams'][0]
    assert int(stream['nb_frames'])==17 and stream['avg_frame_rate']==str(fps)+'/1'
    assert abs(float(stream['duration'])-17/fps)<0.000001


def test_lossless_rng_shape_and_noise(tmp_path):
    state=torch.get_rng_state().clone()
    tree={'noise':torch.arange(16*5*4*2,dtype=torch.float32).reshape(16,5,4,2),'generator_state':state,'sigmas':torch.arange(41,dtype=torch.float32),'timesteps':torch.arange(40,dtype=torch.int64),'history':None}
    path=tmp_path/'conditions.safetensors';save_tree(path,tree,{'case':'lab'})
    loaded,meta=load_tree(path,device='cpu')
    assert all(torch.equal(loaded[k],tree[k]) for k in ('noise','generator_state','sigmas','timesteps'))
    assert torch.equal(state,torch.get_rng_state()) and meta['readback_exact']
    path.write_bytes(path.read_bytes()+b'x')
    with pytest.raises(AssertionError):load_tree(path,device='cpu')


def test_cache_receipt_binds_code_and_inputs(tmp_path):
    (tmp_path/'configs').mkdir();(tmp_path/'artifacts').mkdir()
    (tmp_path/'configs/active_case.json').write_text('{"name":"lab"}')
    (tmp_path/'configs/input_config_hashes.json').write_text('{}')
    code=tmp_path/'PREREGISTERED_CODE.json';code.write_text('{"test":"fixture"}')
    p=tmp_path/'artifacts/conditions.safetensors';save_tree(p,{'noise':torch.zeros(2)}, {'code':json.loads(code.read_text()),'input_hashes':{}})
    torch.save(torch.zeros(2),tmp_path/'artifacts/initial_noise.pt')
    receipt={'experiment':'B-012','case':'lab','code_sha256':hashlib.sha256(code.read_bytes()).hexdigest(),'hashes':{n:hashlib.sha256((tmp_path/'artifacts'/n).read_bytes()).hexdigest() for n in ('conditions.safetensors','conditions.json','initial_noise.pt')}}
    (tmp_path/'artifacts/conditions_receipt.json').write_text(json.dumps(receipt));verify_cache_receipt(tmp_path)
    code.write_text('{}')
    with pytest.raises(AssertionError):verify_cache_receipt(tmp_path)


def test_unknown_case_rejected():
    with pytest.raises(AssertionError):case_contract('cat')




def test_pair_leaf_contract():
    from compare_conditions import compare_leaf
    a=torch.ones(2,3);b=a+1
    policy={'float_unchanged_rtol':1e-5,'float_unchanged_atol':1e-6}
    assert compare_leaf('root.arg_c.pose_latents[0]',a,b,policy)
    assert not compare_leaf('root.arg_c.pose_latents[0]',a,a,policy)
    assert compare_leaf('root.arg_c.ref_latents[0]',a,a,policy)
    assert not compare_leaf('root.arg_c.ref_latents[0]',a,b,policy)
    assert not compare_leaf('root.arg_c.context[0]',a,b,policy)
    assert not compare_leaf('root.arg_null.context[0]',a,b,policy)
    assert not compare_leaf('root.noise',a,b,policy)
    assert not compare_leaf('root.arg_c.ref_masks[0]',a,a+1e-7,policy)


def test_pair_requires_both_real_P_receipts_and_controls(tmp_path,monkeypatch):
    import compare_conditions as module
    policy={'float_unchanged_rtol':1e-5,'float_unchanged_atol':1e-6,'expected_changed_locations':[f'root.{b}.{f}' for b in ('arg_c','arg_null') for f in ('pose_latents[0]','driving_masks[0]')]}
    (tmp_path/'configs').mkdir();(tmp_path/'reports').mkdir();(tmp_path/'configs/comparison_policy.json').write_text(json.dumps(policy));(tmp_path/'PREREGISTERED_CODE.json').write_text('{}')
    trees=[]
    for case,number in [('MOV',1.),('STILL',2.)]:
        r=tmp_path/'cases'/case
        for d in ['configs','artifacts','stages/P/reports','upstream/wan/utils']:(r/d).mkdir(parents=True,exist_ok=True)
        (r/'upstream/wan/utils/scail_utils.py').write_text('fixture')
        (r/'configs/active_case.json').write_text('{"name":"self"}');(r/'configs/input_config_hashes.json').write_text('{}');(r/'PREREGISTERED_CODE.json').write_text(json.dumps({'case_configs':{'MOV':{},'STILL':{}}}))
        visual={'ref_latents':[torch.ones(2)],'ref_masks':[torch.zeros(2)],'clip_fea':torch.ones(2),'pose_latents':[torch.full((2,),number)],'driving_masks':[torch.full((2,),number)]}
        tree={'noise':torch.ones(2),'arg_c':dict(visual,context=[torch.ones(2)]),'arg_null':dict(visual,context=[torch.ones(2)]),'history':None,'generator_state':torch.zeros(16,dtype=torch.uint8),'timesteps':torch.arange(40),'sigmas':torch.arange(41,dtype=torch.float32)};trees.append(tree)
        save_tree(r/'artifacts/conditions.safetensors',tree,{'config':{},'code':json.loads((r/'PREREGISTERED_CODE.json').read_text()),'input_hashes':{}});torch.save(torch.ones(2),r/'artifacts/initial_noise.pt')
        receipt={'experiment':'B-012','case':'self','code_sha256':hashlib.sha256((r/'PREREGISTERED_CODE.json').read_bytes()).hexdigest(),'hashes':{n:hashlib.sha256((r/'artifacts'/n).read_bytes()).hexdigest() for n in ('conditions.safetensors','conditions.json','initial_noise.pt')}}
        (r/'artifacts/conditions_receipt.json').write_text(json.dumps(receipt));(r/'stages/P/reports/result.json').write_text(json.dumps({'status':'COMPLETED','condition_receipt_sha256':hashlib.sha256((r/'artifacts/conditions_receipt.json').read_bytes()).hexdigest()}));(r/'stages/P/reports/pipeline-process.json').write_text(json.dumps({'reason':'service_exit','returncode':0,'final_service':'MainPID=0'}))
    monkeypatch.setattr(module,'expected_driving_mask',lambda r,s:torch.full((2,),1. if r.name=='MOV' else 2.))
    module.compare(tmp_path)
    assert json.loads((tmp_path/'reports/condition_comparison.json').read_text())['status']=='PASS'
    monkeypatch.setattr(module,'expected_driving_mask',lambda r,s:torch.full((2,),9.))
    with pytest.raises(AssertionError):module.compare(tmp_path)
    r=tmp_path/'cases/STILL';(r/'stages/P/reports/pipeline-process.json').write_text('{"reason":"service_exit","returncode":1,"final_service":"MainPID=0"}')
    with pytest.raises(AssertionError):module.compare(tmp_path)
