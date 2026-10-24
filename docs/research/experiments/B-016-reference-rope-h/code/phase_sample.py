"""S: unchanged staged DiT and extracted official UniPC loop, no encoders/VAE."""
from pathlib import Path
from types import SimpleNamespace
import hashlib
import json
import torch
from tqdm import tqdm
from artifacts import save_tree,atomic_json
from extract import sample_source
from runtime_observe import phase
from staged_loader import load_model
from contracts import active_contract, expected_calls
from rope_runtime import install, PositionTrace
import inspect
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
    patched_module=install(root)
    phase('dit_load_start')
    model=load_model(str(root/'upstream/configs/config-14b.json'),str(root/'models/SCAIL.safetensors'),phase_hook=phase)
    assert Path(inspect.getfile(type(model))).resolve()==(root/'patched/model_scail2.py').resolve()
    assert model.forward.__globals__['__file__']==str(root/'patched/model_scail2.py')
    assert model.forward.__globals__['rope_apply_scail'] is patched_module.rope_apply_scail
    atomic_json(root/'reports/loaded_module.json',{'module_alias':'isolated/model_scail2.py','module_sha256':hashlib.sha256((root/'patched/model_scail2.py').read_bytes()).hexdigest(),'canonical_module':'wan.modules.model_scail2','actual_class_file_match':True,'actual_forward_globals_match':True,'freqs_dtype':str(model.freqs.dtype),'frequency_count':model.freqs.shape[0],'blocks':len(model.blocks),'parameter_count':sum(p.numel() for p in model.parameters())})
    assert str(model.freqs.dtype)=='torch.complex128' and len(model.blocks)==40
    model.eval().requires_grad_(False)
    phase('dit_load_end')
    recheck(root,anchor,'after_cpu_load_tiny_recheck')
    tree,meta=restore(root)
    recheck(root,anchor,'after_cache_restore_tiny_recheck')
    generator=torch.Generator(device=device);generator.set_state(tree['generator_state'].cpu())
    scheduler=FlowUniPCMultistepScheduler(num_train_timesteps=config.num_train_timesteps,shift=1,use_dynamic_shifting=False)
    scheduler.set_timesteps(40,device=device,shift=3.0)
    assert torch.equal(scheduler.timesteps,tree['timesteps']) and torch.equal(scheduler.sigmas,tree['sigmas'])
    assert tree['history'] is None
    rope_settings=json.loads((root/'configs/rope_h.json').read_text())
    for key in ('arg_c','arg_null'):
        assert tree[key]['replace_flag'] is False
        assert tree[key].get('additional_ref_latents') is None
        assert tree[key].get('additional_ref_masks') is None
        tree[key]={**tree[key],'reference_rope_h_shift':rope_settings['reference_h_override']}
    counters={'model_calls':0,'completed_steps':0}
    position_trace=PositionTrace(root,lambda:counters['model_calls'])
    model._b016_observe=position_trace.observe
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
        assert counters=={'model_calls':expected_calls(root),'completed_steps':40} and history is None
        assert len(x0)==1 and list(x0[0].shape)==contract.latent_shape and bool(torch.isfinite(x0[0]).all())
        trace_sha=position_trace.finish()
        phase('final_latent_save_start')
        save_tree(root/'artifacts/final_latent.safetensors',{'x0':x0},{'executing_experiment':'B-016','executing_code':json.loads((root/'PREREGISTERED_CODE.json').read_text()),'parent_condition_experiment':'B-013-P','condition_sha256':meta['file_sha256'],'condition_provenance':meta['provenance'],'config':cfg,'counters':counters,'normalization':'Exact generated model-space x0; WanVAE decode applies mean/std internally','history':None,'reference_prefix_included':False,'sampler_source_sha256':hashlib.sha256(extracted.encode()).hexdigest(),'rope_settings':rope_settings,'rope_trace_sha256':trace_sha,'all_block_call_counts':position_trace.counts,'loaded_module':json.loads((root/'reports/loaded_module.json').read_text())})
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
    atomic_json(root/'reports/sampler-attempt.json',{'attempt':1,'max':1,'scope':contract.name+'17f','parent_history':{'E':1,'F':1,'G_reserved':1,'H':1,'B008':1,'B009':1,'B010':0,'B011':1,'B012':2,'B013':2,'B014':1,'B015':1}})
    phase('sampler_start')
    with torch.cuda.amp.autocast(dtype=config.param_dtype),torch.no_grad():
        namespace['sample_func'](tree['noise'],tree['arg_c'],tree['arg_null'],tree['history'])
