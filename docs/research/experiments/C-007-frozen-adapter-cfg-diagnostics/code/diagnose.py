# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Run with existing research Python: diagnose.py /absolute/config.json [--cpu-only]."""
from pathlib import Path
from contextlib import nullcontext
import json
import sys
import time
import torch
from pydantic import BaseModel, ConfigDict
sys.path.insert(0, str(Path(__file__).resolve().parent))
from runtime_common import RuntimeConfig, setup, load_pipeline, atomic_json, tensor_summary
from training_state import load_cache, condition_from_cache
from point_adapter import PointAnchorAdapter
from point_features import make_null
from wan_adapter_forward import ForwardInput, adapted_forward
from diagnostic_metrics import branch_metrics, cfg_metrics, ResidualObserver


class Config(BaseModel):
    model_config = ConfigDict(frozen=True, extra='forbid')
    runtime: Path
    checkpoint_root: Path
    input_manifest: Path
    output: Path
    replay_outputs: list[Path] = []
    inference_sidecar: Path


def append(path: Path, row: dict) -> None:
    with path.open('a') as stream:
        stream.write(json.dumps(row, allow_nan=False)+'\n')


def difference(first: torch.Tensor, second: torch.Tensor) -> dict:
    a, b = first.float(), second.float()
    delta = a-b
    denominator = float(a.square().mean().sqrt())
    return {'max_abs':float(delta.abs().max()),'rms':float(delta.square().mean().sqrt()),
            'relative_rms':float(delta.square().mean().sqrt())/denominator if denominator>1e-12 else None,
            'allclose':bool(torch.allclose(first,second,atol=1e-3,rtol=1e-3))}


def main() -> None:
    config=Config.model_validate_json(Path(sys.argv[1]).read_text())
    runtime=RuntimeConfig.model_validate_json(config.runtime.read_text())
    setup(runtime)
    manifest=json.loads(config.input_manifest.read_text())
    if not config.replay_outputs:
        for name in ('elephant','goat'):
            item=load_cache(runtime.cache_root/f'{name}.pt',runtime.point_exclusions)
            assert item['clean_latent'].shape==(1,16,9,30,52)
    else:
        item=load_cache(config.inference_sidecar,runtime.point_exclusions)
        assert set(item)=={'sequence','split','prompt','patches','anchor_valid','positions','visible','valid','box_wh'}
    if '--cpu-only' in sys.argv:
        print(json.dumps({'status':'CPU_PASS','cuda_initialized':torch.cuda.is_initialized()}));return
    config.output.mkdir(exist_ok=False,parents=True)
    tick=time.monotonic();pipe=load_pipeline(runtime);models=(pipe.dit,pipe.vace)
    from diffsynth.diffusion.flow_match import FlowMatchScheduler
    grid=FlowMatchScheduler('Wan');grid.set_timesteps(1000,training=True,shift=5)
    with torch.random.fork_rng(devices=[]):
        adapter=PointAnchorAdapter().to('cuda').eval().requires_grad_(False)
    checkpoints={i:torch.load(config.checkpoint_root/f'checkpoint-{i:03d}.pt',map_location='cpu',weights_only=True)['adapter'] for i in (0,128,256)}
    counts={'one_step_core_forwards':0,'replay_core_forwards':0,'optimizer':0,'backward':0,'updates':0,'model_loads':1}
    replay_checks=[]
    versions=[p._version for m in models for p in m.parameters()]

    def predict(inputs, condition, label, metadata):
        if label == 'BASE':
            return pipe.model_fn(dit=pipe.dit,vace=pipe.vace,latents=inputs.latents,timestep=inputs.timestep,
                context=inputs.context,vace_context=inputs.vace_context,vace_scale=1.0)
        state=None
        if label!='BYPASS':
            step,mode=label.split('_');adapter.load_state_dict(checkpoints[int(step)],strict=True)
            state=(adapter,make_null(condition) if mode=='NULL' else condition)
        observer=ResidualObserver(adapter,metadata,lambda row:append(config.output/'BLOCK_STATS.jsonl',row)) if state else nullcontext()
        with observer:
            return adapted_forward(models,inputs,state)

    with torch.no_grad():
        if not config.replay_outputs:
            for clip_index,name in enumerate(('elephant','goat')):
                item=load_cache(runtime.cache_root/f'{name}.pt',runtime.point_exclusions)
                z0=item['clean_latent'].to('cuda');mask=item['loss_mask'].to('cuda');condition=condition_from_cache(item)
                generator=torch.Generator(device='cpu').manual_seed(20261101+clip_index)
                noise=torch.randn(z0.shape,generator=generator).to('cuda',dtype=torch.bfloat16)
                for point in manifest['probe_grid']:
                    index=point['index'];sigma=grid.sigmas[index];timepoint=grid.timesteps[index]
                    assert float(sigma)==point['sigma'] and float(timepoint)==point['timestep']
                    z=grid.add_noise(z0,noise,timepoint);target=grid.training_target(z0,noise,timepoint)
                    shared={'clip':name,**point,'state':tensor_summary(z),'noise':tensor_summary(noise)}
                    predictions={};base_metrics={}
                    for label in ('BASE','BYPASS','0_ON','0_NULL','128_ON','128_NULL','256_ON','256_NULL'):
                        for branch,key in (('positive','context'),('negative','negative_context')):
                            meta={**shared,'predictor':label,'branch':branch}
                            inputs=ForwardInput(z,timepoint.reshape(1).to('cuda',dtype=torch.bfloat16),item[key].to('cuda'),item['vace_context'].to('cuda'),sigma)
                            pred=predict(inputs,condition,label,meta);assert torch.isfinite(pred).all()
                            counts['one_step_core_forwards']+=1
                            predictions[label,branch]=pred
                            metrics=branch_metrics(pred,target,z,sigma,z0,mask)
                            if label=='BASE':base_metrics[branch]=metrics.copy()
                            else:
                                metrics['native_difference']=difference(predictions['BASE',branch],pred)
                                metrics['change_from_base']={k:metrics[k]-base_metrics[branch][k] for k in ('mse','object_mse','background_mse','balanced_loss')}
                            append(config.output/'PROBES.jsonl',{**meta,**metrics})
                            atomic_json(config.output/'progress.json',counts)
                        if label!='BASE':
                            append(config.output/'CFG_STATS.jsonl',{**shared,'predictor':label,**cfg_metrics(predictions['BASE','positive'],predictions['BASE','negative'],predictions[label,'positive'],predictions[label,'negative'])})
                        if label in ('BYPASS','0_ON','0_NULL'):
                            checks=[difference(predictions['BASE',b],predictions[label,b]) for b in ('positive','negative')]
                            if not all(x['allclose'] for x in checks):
                                atomic_json(config.output/'result.json',{'status':'IMPLEMENTATION_MISMATCH',**counts,'checks':checks,'elapsed_seconds':time.monotonic()-tick});return
                    del predictions
            assert counts['one_step_core_forwards']==160
        else:
            item=load_cache(config.inference_sidecar,runtime.point_exclusions);condition=condition_from_cache(item)
            for folder in config.replay_outputs:
                contexts=torch.load(folder/'trace/contexts.pt',map_location='cpu',weights_only=True)
                for index in (0,25,40,47,49):
                    state=torch.load(folder/f'trace/step-{index:02d}.pt',map_location='cpu',weights_only=True)
                    meta={'trajectory':folder.name,'sampler_step':index,'sigma':state['sigma'],'timestep':state['timestep']}
                    predictions={}
                    for label in ('BASE','256_ON'):
                        for branch in ('positive','negative'):
                            inputs=ForwardInput(state['latent'].to('cuda'),state['model_timestep'].to('cuda'),contexts[branch].to('cuda'),contexts['vace_context'].to('cuda'),torch.tensor(state['sigma']))
                            pred=predict(inputs,condition,label,{**meta,'predictor':label,'branch':branch});assert torch.isfinite(pred).all()
                            counts['replay_core_forwards']+=1;predictions[label,branch]=pred
                            if (label=='BASE') == folder.name.startswith('BASE'):
                                check={**meta,'branch':branch,**difference(state['branches'][branch].to('cuda'),pred)}
                                replay_checks.append(check);append(config.output/'REPLAY_CHECKS.jsonl',check)
                            atomic_json(config.output/'progress.json',counts)
                    append(config.output/'ROLLOUT_PROBES.jsonl',{**meta,**cfg_metrics(predictions['BASE','positive'],predictions['BASE','negative'],predictions['256_ON','positive'],predictions['256_ON','negative'])})
            assert counts['replay_core_forwards']==40
    assert versions==[p._version for m in models for p in m.parameters()]
    assert all(p.grad is None and not p.requires_grad for m in (*models,adapter) for p in m.parameters())
    atomic_json(config.output/'result.json',{'status':'COMPLETE' if all(x['allclose'] for x in replay_checks) else 'REPLAY_MISMATCH',**counts,'replay_allclose':all(x['allclose'] for x in replay_checks),'base_versions_unchanged':True,'elapsed_seconds':time.monotonic()-tick})


if __name__=='__main__':
    main()
