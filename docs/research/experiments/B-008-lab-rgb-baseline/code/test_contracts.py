"""CPU case/serialization/writer regressions; no pretrained models or CUDA."""
import hashlib
import json
from pathlib import Path
import subprocess
import pytest
import torch
from contracts import case_contract,verify_cache_receipt
from artifacts import save_tree,load_tree

@pytest.mark.parametrize('name,shape,fps',[('official',[16,5,64,112],16),('lab',[16,5,112,64],24)])
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
    receipt={'experiment':'B-008','case':'lab','code_sha256':hashlib.sha256(code.read_bytes()).hexdigest(),'hashes':{n:hashlib.sha256((tmp_path/'artifacts'/n).read_bytes()).hexdigest() for n in ('conditions.safetensors','conditions.json','initial_noise.pt')}}
    (tmp_path/'artifacts/conditions_receipt.json').write_text(json.dumps(receipt));verify_cache_receipt(tmp_path)
    code.write_text('{}')
    with pytest.raises(AssertionError):verify_cache_receipt(tmp_path)


def test_unknown_case_rejected():
    with pytest.raises(AssertionError):case_contract('cat')
