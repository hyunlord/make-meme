"""S: unchanged staged DiT and extracted official UniPC loop, no encoders/VAE."""
from pathlib import Path
from types import SimpleNamespace
import hashlib
import json
import torch
from tqdm import tqdm
from artifacts import save_tree,atomic_json,load_tree
from safetensors.torch import load_file
from clean_constraint import CleanConstraintScheduler
from extract import sample_source
from runtime_observe import phase
from staged_loader import load_model
from contracts import active_contract
from cuda_probe import diagnostic,tiny,restore,recheck


def run(root:Path,cfg:dict) -> None:
    contract=active_contract(root)
    diagnostic(root,'before_official_import')
    from wan.utils.fm_solvers_unipc import FlowUniPCMultistepScheduler
    from wan.configs import SCAIL_CONFIGS
    device=torch.device('cuda:0'); config=SCAIL_CONFIGS['SCAIL-14B']
    diagnostic(root,'after_official_import')
    anchor=tiny(root)
    atomic_json(root/'reports/model-load-attempt.json',{'attempt':1,'max':1,'parent':'B-007H','intervention':'tiny real CUDA before unchanged staged loader'})
    phase('dit_load_start')
    model=load_model(str(root/'upstream/configs/config-14b.json'),str(root/'models/SCAIL.safetensors'),phase_hook=phase)
    model.eval().requires_grad_(False)
    execution=json.loads((root/'configs/execution.json').read_text())
    assert execution['adapter_enabled'] is False and execution['replace_flag'] is True
    assert execution['b029_gate'] is False
    from wan.modules.model_scail2 import WanI2VCrossAttention
    assert WanI2VCrossAttention.forward.__module__ == 'wan.modules.model_scail2'
    from torch import nn
    assert all(type(model.get_submodule(f'blocks.{i}.self_attn.{key}')) is nn.Linear for i in range(40) for key in ('q','v'))
    assert not any('lora' in name.lower() for name,_ in model.named_parameters())
    adapter_sha=None
    atomic_json(root/'reports/adapter-selection.json',{'enabled':False,'sha256':None,'active_lora':0,'ALG':False,'manual_rope_override':False})
    phase('dit_load_end')
    recheck(root,anchor,'after_cpu_load_tiny_recheck')
    tree,meta=restore(root)
    recheck(root,anchor,'after_cache_restore_tiny_recheck')
    generator=torch.Generator(device=device);generator.set_state(tree['generator_state'].cpu())
    scheduler_type=CleanConstraintScheduler if execution['method']=='STEP' else FlowUniPCMultistepScheduler
    scheduler=scheduler_type(num_train_timesteps=config.num_train_timesteps,shift=1,use_dynamic_shifting=False)
    scheduler.set_timesteps(40,device=device,shift=3.0)
    assert torch.equal(scheduler.timesteps,tree['timesteps']) and torch.equal(scheduler.sigmas,tree['sigmas'])
    if execution['method']=='STEP':
        source,_=load_tree(root/'artifacts/source_latent.safetensors',device='cpu')
        scheduler.bind(source['z_src'],load_file(str(root/'inputs/mask_latent.safetensors'))['M'],root/'reports/constraint.jsonl')
    assert tree['history'] is None
    assert tree['arg_c']['replace_flag'] is True and tree['arg_null']['replace_flag'] is True
    counters={'model_calls':0,'completed_steps':0}
    input_rows=[]
    def before(module,args,kwargs):
        assert kwargs['replace_flag'] is True
        assert kwargs['additional_ref_latents'] is None
        branch='arg_c' if counters['model_calls']%2==0 else 'arg_null'
        assert kwargs['ref_latents'][0] is tree[branch]['ref_latents'][0]
        assert kwargs['clip_fea'] is tree[branch]['clip_fea']
        assert kwargs['pose_latents'][0] is tree[branch]['pose_latents'][0]
        assert kwargs['ref_masks'][0] is tree[branch]['ref_masks'][0]
        if len(input_rows)<2:
            actual_input=args[0][0].detach().cpu().contiguous()
            actual_hash=hashlib.sha256(actual_input.view(torch.uint8).numpy().tobytes()).hexdigest()
            assert actual_hash==meta['tensors']['t0']['sha256']
            atomic_json(root/'reports/initial-model-input.json',{'sha256':actual_hash,'shape':list(actual_input.shape),'dtype':str(actual_input.dtype),'equals_frozen_initial_noise':True})
            del actual_input
            keys=('t3','t2') if branch=='arg_c' else ('t9','t8')
            input_rows.append({'task_id':cfg['task_id'],'reference_id':execution['reference_id'],'reference_rgb_file_sha256':meta['provenance']['reference_rgb_sha256'],'reference_mask_file_sha256':meta['provenance']['reference_mask_sha256'],'condition_producer':'B-034','reference_mask_sha256':meta['tensors']['t4' if branch=='arg_c' else 't10']['sha256'],'branch':branch,'ref_and_clip_same_objects_as_verified_restored_cache':True,'reference_sha256':meta['tensors'][keys[0]]['sha256'],'clip_sha256':meta['tensors'][keys[1]]['sha256'],'additional_forward':0,'inspection_tensor_copy':0})
            atomic_json(root/'reports/first-forward-inputs.json',{'rows':input_rows})
        counters['model_calls']+=1
        if counters['model_calls']==1:phase('first_forward_start')
    def after(module,args,output):
        if counters['model_calls']==1:
            assert all(bool(torch.isfinite(value).all()) for value in output)
            torch.cuda.synchronize();phase('first_forward_end')
    model.register_forward_pre_hook(before,with_kwargs=True);model.register_forward_hook(after)
    mode_rows=[]
    def block_trace(module,args,kwargs):
        if len(mode_rows)<2:
            row={k:kwargs[k] for k in ('rope_T_shift','rope_H_shift','rope_W_shift','rope_ref_T')}
            assert row['rope_T_shift']=={'additional_ref':0,'ref':0,'pose':0,'video':0}
            assert row['rope_H_shift']=={'additional_ref':120,'ref':120,'pose':0,'video':0}
            assert row['rope_W_shift']=={'additional_ref':0,'ref':0,'pose':120,'video':0}
            mode_rows.append({'forward':counters['model_calls'],**row})
            atomic_json(root/'reports/replacement-mode.json',{'source':'actual first block kwargs, no RoPE override','rows':mode_rows})
    model.blocks[0].register_forward_pre_hook(block_trace,with_kwargs=True)
    def completed(timestep,sample_scheduler):
        counters['completed_steps']+=1
        atomic_json(root/'reports/progress.json',{**counters,'last_timestep':float(timestep.cpu())})
        phase('step_completed_'+str(counters['completed_steps']))
    def complete(x0,history):
        phase('sampler_loop_exit');torch.cuda.synchronize();phase('sampler_cuda_complete')
        assert counters=={'model_calls':80,'completed_steps':40} and history is None
        if execution['method']=='STEP':
            assert scheduler.constraint_calls==40
            assert len((root/'reports/constraint.jsonl').read_text().splitlines())==40
        assert len(x0)==1 and list(x0[0].shape)==contract.latent_shape and bool(torch.isfinite(x0[0]).all())
        phase('final_latent_save_start')
        save_tree(root/'artifacts/final_latent.safetensors',{'x0':x0},{'executing_experiment':'B-034','method':execution['method'],'constraint_calls':getattr(scheduler,'constraint_calls',0),'adapter_enabled':execution['adapter_enabled'],'adapter_sha256':adapter_sha,'executing_code':json.loads((root/'PREREGISTERED_CODE.json').read_text()),'parent_condition_experiment':'B-034-fixed-method-transfer-validation','condition_sha256':meta['file_sha256'],'condition_provenance':meta['provenance'],'config':cfg,'counters':counters,'normalization':'Exact generated model-space x0; WanVAE decode applies mean/std internally','history':None,'reference_prefix_included':False,'sampler_source_sha256':hashlib.sha256(extracted.encode()).hexdigest()})
        phase('SAMPLER_LATENT_PASS')
    def apply_clean_history(latent,history):
        assert history is None
        return latent
    extracted=sample_source((root/'upstream/wan/scail.py').read_text(),separated=True)
    def measured_phase(label):
        phase(label)
        if label=='dit_to_device_end':recheck(root,anchor,'after_dit_move_tiny_recheck')
    namespace={'torch':torch,'tqdm':tqdm,'self':SimpleNamespace(model=model,device=device,rank=0),'offload_model':True,'apply_clean_history':apply_clean_history,'timesteps':scheduler.timesteps,'sample_scheduler':scheduler,'guide_scale':5.0,'seed_g':generator,'completed':completed,'complete':complete,'phase':measured_phase}
    exec(compile(extracted,'<pinned-sampler-extraction>','exec'),namespace)
    atomic_json(root/'reports/sampler-attempt.json',{'attempt':1,'max':1,'scope':contract.name+'17f','parent_history':{'E':1,'F':1,'G_reserved':1,'H':1,'B008':1,'B009':1,'B010':0,'B011':1}})
    phase('sampler_start')
    with torch.cuda.amp.autocast(dtype=config.param_dtype),torch.no_grad():
        namespace['sample_func'](tree['noise'],tree['arg_c'],tree['arg_null'],tree['history'])
