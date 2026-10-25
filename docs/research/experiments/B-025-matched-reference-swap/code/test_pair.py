"""CPU contracts for the single paired-reference intervention."""
import pytest
from pair_contract import pair_changes


def test_only_reference_bundle_can_change():
    original={f't{i}':{'sha256':str(i)} for i in range(16)}
    changed={**original,**{k:{'sha256':'new'} for k in ('t2','t3','t4','t8','t9','t10')}}
    assert len(pair_changes(original,changed))==6


def test_changed_driving_rejected():
    original={f't{i}':{'sha256':str(i)} for i in range(16)}
    with pytest.raises(AssertionError):pair_changes(original,{**original,'t5':{'sha256':'wrong'}})


def test_same_mask_not_required_to_change():
    original={f't{i}':{'sha256':str(i)} for i in range(16)}
    changed={**original,**{k:{'sha256':'new'} for k in ('t2','t3','t8','t9')}}
    assert len(pair_changes(original,changed))==4


def test_actual_parent_semantic_leaf_map_and_cpu_serialization(tmp_path):
    import json
    import os
    from pathlib import Path
    import torch
    from artifacts import load_tree,save_tree
    parent=Path(os.environ['B024_ROOT'])
    tree,meta=load_tree(parent/'artifacts/conditions.safetensors',device='cpu')
    assert meta['structure']['dict']['arg_c']['dict']['context']['list'][0]['tensor']=='t1'
    assert meta['structure']['dict']['arg_null']['dict']['context']['list'][0]['tensor']=='t7'
    for branch,keys in [('arg_c',('t2','t3','t4')),('arg_null',('t8','t9','t10'))]:
        node=meta['structure']['dict'][branch]['dict']
        assert (node['clip_fea']['tensor'],node['ref_latents']['list'][0]['tensor'],node['ref_masks']['list'][0]['tensor'])==keys
        assert tree[branch]['replace_flag'] is True
    tree['arg_c']['context']=[tree['arg_c']['context'][0][:2].clone()]
    target=tmp_path/'fixture.safetensors';save_tree(target,tree,{'scope':'CPU serialization only'})
    loaded,newmeta=load_tree(target,device='cpu')
    assert loaded['arg_c']['context'][0].shape[0]==2
    assert newmeta['tensors']['t1']['shape'][0]==2
    for k in meta['tensors']:
        if k!='t1':assert meta['tensors'][k]==newmeta['tensors'][k]
