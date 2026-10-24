"""CPU semantic-mask derivation through pinned helper, never encoder execution."""
from pathlib import Path
import copy
import importlib.util
import hashlib
import json
import sys
import numpy as np
import torch
from PIL import Image
from artifacts import load_tree,save_tree,atomic_json


def digest(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main()->None:
    root=Path(sys.argv[1]);producer=(root/'producer').resolve()
    helper_path=producer/'stages/BASE_S/upstream/wan/utils/scail_utils.py'
    spec=importlib.util.spec_from_file_location('pinned_scail_mask_helper',helper_path)
    assert spec is not None and spec.loader is not None
    helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    extract_and_compress_mask_to_latent=helper.extract_and_compress_mask_to_latent
    load_image_to_tensor_chw_normalized=helper.load_image_to_tensor_chw_normalized
    resize_for_rectangle_crop=helper.resize_for_rectangle_crop
    receipt=json.loads((producer/'artifacts/conditions_receipt.json').read_text())
    for name,sha in receipt['hashes'].items():assert digest(producer/'artifacts'/name)==sha,name
    assert receipt['code_sha256']==digest(producer/'PREREGISTERED_CODE.json')
    old,meta=load_tree(producer/'artifacts/conditions.safetensors',device='cpu');tree=copy.deepcopy(old)
    source=producer/'inputs/clip/reference-mask-white.png';image=np.array(Image.open(source).convert('RGB'))
    colors,counts=np.unique(image.reshape(-1,3),axis=0,return_counts=True)
    assert set(map(tuple,colors)) <= {(255,0,0),(255,255,255)},colors
    red=np.all(image==[255,0,0],axis=-1);white=np.all(image==[255,255,255],axis=-1)
    new=image.copy();new[white]=0;assert np.array_equal(new[red],image[red])
    target=root/'inputs/clip/reference-mask-black.png';assert not target.exists();Image.fromarray(new).save(target)
    def encode(path):
        normalized=load_image_to_tensor_chw_normalized(Image.open(path).convert('RGB'))
        resized=resize_for_rectangle_crop(normalized,(512,896),reshape_mode='center').squeeze(0)
        return extract_and_compress_mask_to_latent(resized.unsqueeze(1),additional_spatial_downsample=1)
    old_prefix=encode(source);new_prefix=encode(target)
    assert list(old_prefix.shape)==[28,1,64,112]
    assert torch.equal(old_prefix[1::7],new_prefix[1::7])
    assert not bool(new_prefix[0::7].any())
    changes=[]
    for branch in ('arg_c','arg_null'):
        prior=old[branch]['ref_masks'][0]
        assert torch.equal(prior[:,:1],old_prefix),branch+' old helper parity'
        assert not bool(prior[:,1:].any())
        tree[branch]['ref_masks']=[torch.cat([new_prefix,prior[:,1:].clone()],dim=1)]
        assert old[branch]['replace_flag'] is False
        tree[branch]['replace_flag']=True
        assert tree[branch]['additional_ref_latents'] is None
        changes.append(branch+'.ref_masks[0]')
    provenance={'experiment':'B-023','parent_experiment':'B-020','parent_cache_sha256':meta['file_sha256'],'parent_metadata_sha256':digest(producer/'artifacts/conditions.json'),'parent_receipt_sha256':digest(producer/'artifacts/conditions_receipt.json'),'builder_sha256':digest(Path(__file__)),'helper_sha256':digest(producer/'stages/BASE_S/upstream/wan/utils/scail_utils.py'),'mask_source_sha256':digest(source),'mask_target_sha256':digest(target),'P_executions':0,'CPU_helper_reconstruction':'old prefix exact; new prefix via pinned helper'}
    save_tree(root/'artifacts/conditions.safetensors',tree,provenance)
    newmeta=json.loads((root/'artifacts/conditions.json').read_text())
    structure=copy.deepcopy(meta['structure'])
    for branch in ('arg_c','arg_null'):structure['dict'][branch]['dict']['replace_flag']={'scalar':True}
    newmeta['structure']=structure;atomic_json(root/'artifacts/conditions.json',newmeta)
    changed=[];same=[]
    def walk(node,path):
        if 'tensor' in node:
            key=node['tensor'];(same if meta['tensors'][key]==newmeta['tensors'][key] else changed).append(path)
        elif 'dict' in node:
            for k,v in node['dict'].items():walk(v,path+'.'+k)
        elif 'list' in node:
            for i,v in enumerate(node['list']):walk(v,path+f'[{i}]')
    walk(meta['structure'],'root')
    assert set(changed)=={'root.'+x for x in changes} and len(same)==14
    check,newmeta=load_tree(root/'artifacts/conditions.safetensors',device='cpu')
    assert torch.equal(check['noise'],old['noise']) if isinstance(old['noise'],torch.Tensor) else all(torch.equal(a,b) for a,b in zip(check['noise'],old['noise']))
    assert digest(producer/'artifacts/conditions.safetensors')==meta['file_sha256']
    atomic_json(root/'reports/cache-derivation.json',{'status':'PASS','changed_tensor_leaves':changed,'identical_tensor_leaves':same,'changed_scalars':['arg_c.replace_flag','arg_null.replace_flag'],'original_colors':dict(zip(map(str,map(tuple,colors)),map(int,counts))),'red_pixels':int(red.sum()),'white_to_black_pixels':int(white.sum()),'red_support_exact':True,'old_helper_prefix_exact':True,'prefix_shape':list(new_prefix.shape),'parent_cache_unchanged':True,'P':0,'provenance':provenance})
    atomic_json(root/'artifacts/conditions_receipt.json',{'experiment':'B-023','case':'real','hashes':{n:digest(root/'artifacts'/n) for n in ('conditions.safetensors','conditions.json','initial_noise.pt')},'parent_receipt_sha256':provenance['parent_receipt_sha256'],'builder_sha256':provenance['builder_sha256']})

if __name__=='__main__':main()
