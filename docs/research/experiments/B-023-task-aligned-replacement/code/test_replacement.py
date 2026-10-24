"""CPU actual-cache and official mode contracts, no models instantiated."""
from pathlib import Path
import json
import os
import torch
from artifacts import load_tree
from contracts import verify_cache_receipt
from media import verify_inputs

ROOT=Path(os.environ['B023_ROOT'])

def test_cache_contract():
    receipt=verify_cache_receipt(ROOT)
    assert receipt['experiment']=='B-023'
    new,meta=load_tree(ROOT/'artifacts/conditions.safetensors',device='cpu')
    old,parent=load_tree(ROOT/'producer/artifacts/conditions.safetensors',device='cpu')
    assert len(meta['tensors'])==16
    for branch in ('arg_c','arg_null'):
        assert new[branch]['replace_flag'] is True and old[branch]['replace_flag'] is False
        assert torch.equal(new[branch]['ref_latents'][0],old[branch]['ref_latents'][0])
        assert torch.equal(new[branch]['driving_masks'][0],old[branch]['driving_masks'][0])
        assert torch.equal(new[branch]['ref_masks'][0][1::7],old[branch]['ref_masks'][0][1::7])
        assert not bool(new[branch]['ref_masks'][0][0::7].any())
    assert torch.equal(new['noise'],old['noise'])
    assert torch.equal(new['generator_state'],old['generator_state'])
    assert torch.equal(new['timesteps'],old['timesteps'])
    assert torch.equal(new['sigmas'],old['sigmas'])

def test_inputs():
    cfg=verify_inputs(ROOT)
    assert (cfg['width'],cfg['height'],cfg['fps'],cfg['frames'])==(896,512,30,17)
    assert cfg['adapter'] is None

def test_official_modes():
    source=(ROOT/'stages/S/upstream/wan/modules/model_scail2.py').read_text()
    block=source[source.index('        base_video_shift ='):source.index('        def apply_rope_scail')]
    for enabled in (False,True):
        ns={'replace_flag':enabled,'additional_ref_count':0,'kwargs':{}}
        exec(compile('\n'.join(x[8:] for x in block.splitlines()),'<pinned official mode>','exec'),ns)
        v=ns['kwargs'];assert v['rope_T_shift']['video']==(0 if enabled else 1)
        assert v['rope_T_shift']['pose']==(0 if enabled else 1)
        assert v['rope_H_shift']['ref']==(120 if enabled else 0)
        assert v['rope_W_shift']=={'ref':0,'additional_ref':0,'pose':120,'video':0}

def test_sampler_unchanged():
    from extract import sample_source
    source=(ROOT/'stages/S/upstream/wan/scail.py').read_text()
    extracted=sample_source(source,separated=True)
    assert 'self.model.cpu()' not in extracted
    assert 'noise_pred = noise_pred_uncond + guide_scale * (' in extracted
    assert 'self.model' in extracted and 'sample_scheduler.step' in extracted
