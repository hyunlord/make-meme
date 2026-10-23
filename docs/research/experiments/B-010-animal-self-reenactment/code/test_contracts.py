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
    receipt={'experiment':'B-010','case':'lab','code_sha256':hashlib.sha256(code.read_bytes()).hexdigest(),'hashes':{n:hashlib.sha256((tmp_path/'artifacts'/n).read_bytes()).hexdigest() for n in ('conditions.safetensors','conditions.json','initial_noise.pt')}}
    (tmp_path/'artifacts/conditions_receipt.json').write_text(json.dumps(receipt));verify_cache_receipt(tmp_path)
    code.write_text('{}')
    with pytest.raises(AssertionError):verify_cache_receipt(tmp_path)


def test_unknown_case_rejected():
    with pytest.raises(AssertionError):case_contract('cat')




def test_expected_change_contract():
    from compare_conditions import compare_leaf
    a=torch.ones(2,3);b=a+1
    policy={'float_unchanged_rtol':1e-5,'float_unchanged_atol':1e-6}
    assert compare_leaf('root.arg_c.context[0]',a,torch.ones(4,3),policy)
    assert compare_leaf('root.arg_c.ref_latents[0]',a,b,policy)
    assert not compare_leaf('root.arg_c.context[0]',a,a,policy)
    assert not compare_leaf('root.arg_c.clip_fea',a,a,policy)
    assert not compare_leaf('root.arg_c.ref_latents[0]',a,a,policy)
    assert not compare_leaf('root.arg_c.pose_latents[0]',a,b,policy)
    assert not compare_leaf('root.arg_null.context[0]',a,b,policy)
    assert not compare_leaf('root.arg_c.driving_masks[0]',a,a+1e-7,policy)
    assert not compare_leaf('root.noise',a,b,policy)
    assert compare_leaf('root.arg_c.pose_latents[0]',a,a,policy)


def test_full_self_contract_rejects_generated_mask_change(tmp_path):
    import os
    import shutil
    import numpy as np
    from PIL import Image
    from compare_conditions import compare,expected_mask
    baseline=tmp_path/'baseline'
    for folder in [tmp_path/'artifacts',baseline/'artifacts',tmp_path/'inputs/self',baseline/'inputs/lab',tmp_path/'upstream/wan/utils',tmp_path/'configs',tmp_path/'reports']:
        folder.mkdir(parents=True,exist_ok=True)
    helper=tmp_path/'upstream/wan/utils/scail_utils.py';shutil.copyfile(os.environ['SCAIL_UTILS'],helper)
    old_image=baseline/'inputs/lab/reference-mask-white.png';new_image=tmp_path/'inputs/self/reference-mask-white.png'
    original=np.full((8,8,3),255,dtype=np.uint8);original[:4,:,1:]=0
    changed=np.full((8,8,3),255,dtype=np.uint8);changed[:2,:,1:]=0
    Image.fromarray(original).save(old_image);Image.fromarray(changed).save(new_image)
    def tree(image,new):
        mask=torch.cat([expected_mask(image,helper),torch.zeros(28,5,1,1)],dim=1)
        visual={'ref_masks':[mask],'ref_latents':[torch.full((2,3),2. if new else 1.)],'clip_fea':torch.full((2,3),2. if new else 1.),'pose_latents':[torch.ones(2,3)],'driving_masks':[torch.zeros(28,5,1,1)]}
        return {'noise':torch.ones(2),'arg_c':dict(visual,context=[torch.ones(4 if new else 2,3)]),'arg_null':dict(visual,context=[torch.ones(1,3)]),'history':None,'generator_state':torch.zeros(16,dtype=torch.uint8),'timesteps':torch.arange(40),'sigmas':torch.arange(41,dtype=torch.float32)}
    old_tree,new_tree=tree(old_image,False),tree(new_image,True)
    oldpath=baseline/'artifacts/conditions.safetensors';newpath=tmp_path/'artifacts/conditions.safetensors'
    keys=('name','reference','reference_mask','driver','driver_mask','prompt');oldcfg={k:'old-'+k for k in keys};newcfg={k:'new-'+k for k in keys}
    save_tree(oldpath,old_tree,{'config':oldcfg});save_tree(newpath,new_tree,{'config':newcfg})
    policy={'baseline_mask_sha256':hashlib.sha256(old_image.read_bytes()).hexdigest(),'baseline_cache_sha256':hashlib.sha256(oldpath.read_bytes()).hexdigest(),'float_unchanged_atol':1e-6,'float_unchanged_rtol':1e-5,'old_config':oldcfg,'new_config':newcfg,'expected_changed_locations':['root.arg_c.context[0]']+[f'root.{b}.{f}' for b in ['arg_c','arg_null'] for f in ['ref_latents[0]','ref_masks[0]','clip_fea']]}
    (tmp_path/'configs/comparison_policy.json').write_text(json.dumps(policy));(tmp_path/'PREREGISTERED_CODE.json').write_text('{}')
    compare(tmp_path)
    new_tree['arg_c']['ref_masks'][0][:,1:].add_(1e-7)
    newpath.unlink();newpath.with_suffix('.json').unlink()
    save_tree(newpath,new_tree,{'config':newcfg})
    with pytest.raises(AssertionError):compare(tmp_path)
