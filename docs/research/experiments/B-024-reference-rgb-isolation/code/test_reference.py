"""CPU input/provenance contracts before one bounded reference encoder worker."""
from pathlib import Path
import os
import json
import numpy as np
from PIL import Image
from artifacts import load_tree
from contracts import verify_parent_receipt
from media import verify_inputs
ROOT=Path(os.environ['B024_ROOT'])

def test_rgb_support_contract():
    old=np.array(Image.open(ROOT/'producer/inputs/clip/reference.png'))
    new=np.array(Image.open(ROOT/'inputs/clip/reference-rgb-neutral.png'))
    mask=np.array(Image.open(ROOT/'inputs/clip/reference-mask-black.png'))
    support=np.all(mask==[255,0,0],axis=-1)
    assert old.shape==new.shape==mask.shape==(512,896,3)
    assert support.sum()==37209 and np.array_equal(old[support],new[support])
    assert np.all(new[~support]==128)
    assert np.array_equal(mask,np.array(Image.open(ROOT/'producer/inputs/clip/reference-mask-black.png')))

def test_original_cache_role_contract():
    verify_parent_receipt(ROOT)
    tree,metadata=load_tree(ROOT/'producer/artifacts/conditions.safetensors',device='cpu')
    for branch in ('arg_c','arg_null'):
        assert tree[branch]['replace_flag'] is True
        assert list(tree[branch]['ref_latents'][0].shape)==[16,1,64,112]
        assert list(tree[branch]['pose_latents'][0].shape)==[16,5,32,56]
        assert tree[branch]['additional_ref_latents'] is None
    assert len(metadata['tensors'])==16 and tree['history'] is None

def test_unchanged_config_contract():
    cfg=verify_inputs(ROOT)
    original=json.loads((ROOT/'producer/configs/real.json').read_text())
    assert {k:v for k,v in cfg.items() if k!='reference'}=={k:v for k,v in original.items() if k!='reference'}
    assert cfg['adapter'] is None and cfg['reference'].endswith('reference-rgb-neutral.png')

def test_original_sampler_extraction_contract():
    from extract import sample_source
    source=(ROOT/'stages/S/upstream/wan/scail.py').read_text()
    current=sample_source(source,separated=True)
    import importlib.util
    spec=importlib.util.spec_from_file_location('parent_extract',ROOT/'producer/code/extract.py')
    assert spec and spec.loader
    parent=importlib.util.module_from_spec(spec);spec.loader.exec_module(parent)
    assert current==parent.sample_source(source,separated=True)
