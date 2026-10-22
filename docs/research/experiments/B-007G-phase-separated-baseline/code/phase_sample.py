"""S: unchanged staged DiT and extracted official UniPC loop, no encoders/VAE."""
from pathlib import Path
from types import SimpleNamespace
import hashlib
import json
import torch
from tqdm import tqdm
from artifacts import load_tree,save_tree,atomic_json
from extract import sample_source
from runtime_observe import phase
from staged_loader import load_model


def run(root:Path,cfg:dict) -> None:
    from wan.utils.fm_solvers_unipc import FlowUniPCMultistepScheduler
    from wan.configs import SCAIL_CONFIGS
    device=torch.device('cuda:0'); config=SCAIL_CONFIGS['SCAIL-14B']
    phase('dit_load_start')
    model=load_model(str(root/'upstream/configs/config-14b.json'),str(root/'models/SCAIL.safetensors'),phase_hook=phase)
    model.eval().requires_grad_(False)
    phase('dit_load_end')
    tree,meta=load_tree(root/'artifacts/conditions.safetensors')
    generator=torch.Generator(device=device);generator.set_state(tree['generator_state'].cpu())
    scheduler=FlowUniPCMultistepScheduler(num_train_timesteps=config.num_train_timesteps,shift=1,use_dynamic_shifting=False)
    scheduler.set_timesteps(40,device=device,shift=3.0)
    assert torch.equal(scheduler.timesteps,tree['timesteps']) and torch.equal(scheduler.sigmas,tree['sigmas'])
    assert tree['history'] is None
    counters={'model_calls':0,'completed_steps':0}
    def before(module,args):
        counters['model_calls']+=1
        if counters['model_calls']==1:phase('first_forward_start')
    def after(module,args,output):
        if counters['model_calls']==1:
            assert all(bool(torch.isfinite(value).all()) for value in output)
            torch.cuda.synchronize();phase('first_forward_end')
    model.register_forward_pre_hook(before);model.register_forward_hook(after)
    def completed(timestep,sample_scheduler):
        counters['completed_steps']+=1
        atomic_json(root/'reports/progress.json',{**counters,'last_timestep':float(timestep.cpu())})
        phase('step_completed_'+str(counters['completed_steps']))
    def complete(x0,history):
        phase('sampler_loop_exit');torch.cuda.synchronize();phase('sampler_cuda_complete')
        assert counters=={'model_calls':80,'completed_steps':40} and history is None
        assert len(x0)==1 and list(x0[0].shape)==[16,5,64,112] and bool(torch.isfinite(x0[0]).all())
        phase('final_latent_save_start')
        save_tree(root/'artifacts/final_latent.safetensors',{'x0':x0},{'condition_sha256':meta['file_sha256'],'condition_provenance':meta['provenance'],'config':cfg,'counters':counters,'normalization':'Exact generated model-space x0; WanVAE decode applies mean/std internally','history':None,'reference_prefix_included':False,'sampler_source_sha256':hashlib.sha256(extracted.encode()).hexdigest()})
        phase('SAMPLER_LATENT_PASS')
    def apply_clean_history(latent,history):
        assert history is None
        return latent
    extracted=sample_source((root/'upstream/wan/scail.py').read_text(),separated=True)
    namespace={'torch':torch,'tqdm':tqdm,'self':SimpleNamespace(model=model,device=device,rank=0),'offload_model':True,'apply_clean_history':apply_clean_history,'timesteps':scheduler.timesteps,'sample_scheduler':scheduler,'guide_scale':5.0,'seed_g':generator,'completed':completed,'complete':complete,'phase':phase}
    exec(compile(extracted,'<pinned-sampler-extraction>','exec'),namespace)
    phase('sampler_start')
    with torch.cuda.amp.autocast(dtype=config.param_dtype),torch.no_grad():
        namespace['sample_func'](tree['noise'],tree['arg_c'],tree['arg_null'],tree['history'])
