"""Tiny CPU graph contracts; not a 14B numerical/video equivalence claim."""
from pathlib import Path
from types import SimpleNamespace
import json
import os
from unittest.mock import Mock,patch
import pytest
import torch
from artifacts import save_tree,load_tree
from extract import sample_source,install_prepare


def test_lossless_tree_rng_and_dtypes(tmp_path:Path) -> None:
    rng=torch.Generator().manual_seed(123);torch.randn(3,generator=rng)
    value={'context':[torch.ones(2,3,dtype=torch.bfloat16)],'none':None,'flag':False,'seq_len':1e10,'rng':rng.get_state()}
    path=tmp_path/'cache.safetensors';save_tree(path,value,{'fixture':True})
    restored,meta=load_tree(path,device='cpu')
    assert torch.equal(restored['context'][0],value['context'][0]) and restored['none'] is None
    rng2=torch.Generator();rng2.set_state(restored['rng'])
    assert torch.equal(torch.randn(5,generator=rng),torch.randn(5,generator=rng2))
    with pytest.raises(FileExistsError):save_tree(path,value,{})


def test_fixed_source_extraction() -> None:
    source=Path(os.environ['SCAIL_SOURCE']).read_text()
    extracted=sample_source(source,separated=True)
    assert 'self.model.cpu()' not in extracted and 'self.vae' not in extracted
    assert extracted.count("torch.device('cpu') if offload_model else self.device")==3
    assert 'apply_clean_history(temp_x0.squeeze(0), history_latent)' in extracted
    # Actual source module globals suffice for defining (not calling) the method.
    generate,digest=install_prepare(SimpleNamespace(__file__=os.environ['SCAIL_SOURCE'],torch=torch),lambda *args:None)
    assert callable(generate) and len(digest)==64


def test_original_sampler_matches_separated_cpu() -> None:
    source=Path(os.environ['SCAIL_SOURCE']).read_text()
    class Model:
        def to(self,device):return self
        def cpu(self):return self
        def __call__(self,latent,t,**kwargs):return [latent[0]*0.1+kwargs['offset']]
    class Scheduler:
        def step(self,noise,t,latent,**kwargs):return (latent-noise*0.03,)
    noise=torch.arange(24,dtype=torch.float32).reshape(2,3,4)/24
    calls=[];saved=[]
    common={'torch':torch,'tqdm':lambda values:values,'self':SimpleNamespace(model=Model(),device=torch.device('cpu'),rank=0,vae=SimpleNamespace(decode=lambda value:value)),'offload_model':True,'apply_clean_history':lambda value,history:value,'timesteps':torch.tensor([3,2,1]),'sample_scheduler':Scheduler(),'guide_scale':5.0,'seed_g':torch.Generator().manual_seed(1),'phase':lambda name:None,'completed':lambda *args:calls.append(1),'complete':lambda value,history:saved.append(value[0].clone())}
    original=dict(common);separated=dict(common)
    exec(sample_source(source,separated=False),original);exec(sample_source(source,separated=True),separated)
    with patch.object(torch.cuda,'synchronize'),patch.object(torch.cuda,'empty_cache'):
        expected=original['sample_func'](noise.clone(),{'offset':0.2},{'offset':0.1},None)
        actual=separated['sample_func'](noise.clone(),{'offset':0.2},{'offset':0.1},None)
    assert torch.equal(expected[0],actual[0]) and torch.equal(saved[0],expected[0]) and len(calls)==3


def test_actual_unipc_timesteps_and_unused_generator() -> None:
    import importlib.util
    source=Path(os.environ['SCAIL_SOURCE']).parent/'utils/fm_solvers_unipc.py'
    spec=importlib.util.spec_from_file_location('pinned_unipc_fixture',source)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    schedulers=[module.FlowUniPCMultistepScheduler(num_train_timesteps=1000,shift=1,use_dynamic_shifting=False) for _ in range(2)]
    for scheduler in schedulers:scheduler.set_timesteps(40,device='cpu',shift=3)
    assert torch.equal(schedulers[0].timesteps,schedulers[1].timesteps)
    assert torch.equal(schedulers[0].sigmas,schedulers[1].sigmas)
    generator=torch.Generator().manual_seed(20261022);before=generator.get_state().clone()
    latent=torch.ones(1,2,3,4)
    for t in schedulers[0].timesteps:
        latent=schedulers[0].step(latent*0.1,t,latent,return_dict=False,generator=generator)[0]
    assert torch.equal(before,generator.get_state()) and torch.isfinite(latent).all()


def test_prepare_boundary_keeps_condition_branches_without_dit() -> None:
    from contextlib import contextmanager
    from einops import rearrange
    import logging,random,sys
    active=[False];calls=[];captured={}
    @contextmanager
    def autocast(**kwargs):
        active[0]=True
        try:yield
        finally:active[0]=False
    class VAE:
        def encode(self,values):
            calls.append(('encode',active[0]))
            value=values[0]
            return [torch.ones(16,(value.shape[1]-1)//4+1,value.shape[2]//8,value.shape[3]//8)]
    class Scheduler:
        def __init__(self,**kwargs):pass
        def set_timesteps(self,*args,**kwargs):self.timesteps=torch.tensor([1]);self.sigmas=torch.tensor([1.0,0.0])
    class Boundary(Exception):pass
    def persist(noise,arg_c,arg_null,history,*args):
        captured.update(noise=noise,arg_c=arg_c,arg_null=arg_null,history=history)
        raise Boundary
    globals_=SimpleNamespace(__file__=os.environ['SCAIL_SOURCE'],torch=torch,TF=None,logging=logging,random=random,sys=sys,contextmanager=contextmanager,amp=SimpleNamespace(autocast=autocast),rearrange=rearrange,F=torch.nn.functional,FlowUniPCMultistepScheduler=Scheduler,extract_and_compress_mask_to_latent=lambda value,**kw:torch.zeros(28,(value.shape[1]-1)//4+1,value.shape[2]//8,value.shape[3]//8))
    generate,_=install_prepare(globals_,persist)
    owner=SimpleNamespace(model=None,device=torch.device('cpu'),vae_stride=(4,8,8),vae=VAE(),t5_cpu=True,text_encoder=lambda prompts,device:[torch.ones(2,4) if prompts[0] else torch.zeros(1,4)],clip=SimpleNamespace(model=SimpleNamespace(to=lambda *args:None,cpu=lambda:None),visual=lambda value:torch.ones(1,3,4)),param_dtype=torch.bfloat16,num_train_timesteps=1000)
    with patch.object(torch.cuda,'empty_cache'),pytest.raises(Boundary):
        generate(owner,'prompt',torch.zeros(3,32,32),torch.zeros(3,32,32),torch.zeros(17,3,32,32),torch.zeros(3,17,32,32),False,segment_len=17,seed=20261022)
    assert calls==[('encode',False),('encode',True)]
    assert captured['history'] is None
    assert len(captured['arg_c']['context'])==len(captured['arg_null']['context'])==1
    assert captured['arg_c']['context'][0].shape!=(captured['arg_null']['context'][0].shape)
    for arg in [captured['arg_c'],captured['arg_null']]:
        assert arg['history_mask'] is None and arg['additional_ref_latents'] is None and arg['additional_ref_masks'] is None
        assert arg['replace_flag'] is False and arg['seq_len']==1e10
