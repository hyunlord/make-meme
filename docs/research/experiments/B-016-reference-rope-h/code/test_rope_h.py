"""Small actual-helper checks; synthetic fixed Q/K, not model quality evidence."""
import ast
import json
import os
from pathlib import Path
import pytest
import torch
import torch.nn.functional as F
from rope_h import resolve_reference_h, patch_source

SOURCE=Path(os.environ['SCAIL_MODEL_SOURCE'])

def helpers():
    tree=ast.parse(SOURCE.read_text())
    names={'rope_params','rope_apply_ref','rope_apply_additional_ref','rope_apply_video','rope_apply_pose','rope_apply_scail'}
    nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
    for n in nodes:n.decorator_list=[]
    ns={'torch':torch,'F':F};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(SOURCE),'exec'),ns)
    return ns

@pytest.mark.parametrize('override,expected',[(None,0),(0,0),(120,120)])
def test_override_preserves_baseline_or_selects_height(override,expected):
    assert resolve_reference_h(0,override,0,False,56,1024)==expected

@pytest.mark.parametrize('override,additional,replace,height',[(120,1,False,56),(120,0,True,56),(120,0,False,1000),(-1,0,False,56)])
def test_invalid_contract_fails(override,additional,replace,height):
    with pytest.raises(AssertionError):resolve_reference_h(0,override,additional,replace,height,1024)

def test_exact_patch_only_expected_sites():
    source=SOURCE.read_text();patched=patch_source(source)
    assert patched.count('resolve_reference_h(')==1
    assert 'reference_rope_h_shift: int | None = None,' in patched
    with pytest.raises(AssertionError):patch_source(patched)

def test_actual_helpers_fixed_qk_properties():
    h=helpers();freq=torch.cat([h['rope_params'](8192,44),h['rope_params'](8192,42),h['rope_params'](8192,42)],dim=1)
    kw={'freqs':freq,'rope_T':5,'rope_H':4,'rope_W':4,'rope_ref_T':{'ref':1,'additional_ref':0},'rope_T_shift':{'ref':0,'video':1,'pose':1,'additional_ref':0},'rope_H_shift':{'ref':0,'video':0,'pose':0,'additional_ref':0},'rope_W_shift':{'ref':0,'video':0,'pose':120,'additional_ref':0},'ref_length':16,'seq_length':80,'pose_length':20,'additional_ref_length':0}
    g=torch.Generator().manual_seed(20261022);q=torch.randn(1,116,2,128,generator=g);k=torch.randn(1,116,2,128,generator=g)
    original=h['rope_apply_scail'](q,**kw);k0=h['rope_apply_scail'](k,**kw)
    for override in (None,0):
        z={**kw,'rope_H_shift':{**kw['rope_H_shift'],'ref':resolve_reference_h(0,override,0,False,4,1024)}}
        assert torch.equal(h['rope_apply_scail'](q,**z),original)
    shifted={**kw,'rope_H_shift':{**kw['rope_H_shift'],'ref':120}}
    q1=h['rope_apply_scail'](q,**shifted);k1=h['rope_apply_scail'](k,**shifted)
    assert torch.equal(q1[:,16:],original[:,16:]) and torch.equal(k1[:,16:],k0[:,16:])
    torch.testing.assert_close(q1[:,:16].norm(dim=-1),original[:,:16].norm(dim=-1),rtol=2e-5,atol=2e-5)
    torch.testing.assert_close(k1[:,:16].norm(dim=-1),k0[:,:16].norm(dim=-1),rtol=2e-5,atol=2e-5)
    dot=lambda a,b:torch.einsum('bihd,bjhd->bhij',a,b)/(128**.5)
    torch.testing.assert_close(dot(q1[:,:16],k1[:,:16]),dot(original[:,:16],k0[:,:16]),rtol=2e-5,atol=2e-5)
    for start,end in ((16,96),(96,116)):
        assert (dot(q1[:,:16],k1[:,start:end])-dot(original[:,:16],k0[:,start:end])).abs().max()>1e-4
    assert kw['rope_H_shift']['ref']==0
    if os.environ.get('CPU_NUMERIC_REPORT'):
        report={'q_norm_max_abs':float((q1[:,:16].norm(dim=-1)-original[:,:16].norm(dim=-1)).abs().max()),'k_norm_max_abs':float((k1[:,:16].norm(dim=-1)-k0[:,:16].norm(dim=-1)).abs().max()),'ref_ref_logit_max_abs':float((dot(q1[:,:16],k1[:,:16])-dot(original[:,:16],k0[:,:16])).abs().max()),'ref_video_logit_max_delta':float((dot(q1[:,:16],k1[:,16:96])-dot(original[:,:16],k0[:,16:96])).abs().max()),'ref_pose_logit_max_delta':float((dot(q1[:,:16],k1[:,96:])-dot(original[:,:16],k0[:,96:])).abs().max()),'nonref_bit_exact':True,'rtol':2e-5,'atol':2e-5,'frequency_count':8192,'frequency_dtype':str(freq.dtype),'scope':'Fixed synthetic Q/K only; no downstream attention probability claim'}
        Path(os.environ['CPU_NUMERIC_REPORT']).write_text(json.dumps(report,indent=2))


def test_trace_all_blocks_and_first_last_positions(tmp_path):
    from rope_runtime import PositionTrace
    (tmp_path/'reports').mkdir()
    call=[0];trace=PositionTrace(tmp_path,lambda:call[0])
    t={'additional_ref':0,'ref':0,'pose':1,'video':1}
    h={'ref':120,'additional_ref':0,'pose':0,'video':0}
    w={'ref':0,'additional_ref':0,'pose':120,'video':0}
    for n in range(1,81):
        call[0]=n
        for block in range(40):trace.observe(block,t,h,w,1792,8960,2240,56,32,5)
    assert len(trace.finish())==64
    with pytest.raises(AssertionError):trace.observe(0,t,{**h,'video':1},w,1792,8960,2240,56,32,5)
