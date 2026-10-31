# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Read-only native sampler observations; imported by generate_video.py."""
from pathlib import Path
import json
import torch
from runtime_common import atomic_torch, tensor_summary


def summary(tensor: torch.Tensor) -> dict:
    value=tensor.detach().float()
    assert torch.isfinite(value).all()
    return {'rms':float(value.square().mean().sqrt()),'norm':float(value.norm()),
            'minimum':float(value.min()),'maximum':float(value.max())}


class RolloutTrace:
    """Mutable per-step accumulator releases GPU tensors after each original step."""
    def __init__(self, output: Path, guidance: float) -> None:
        self.output=output;self.guidance=guidance;self.index=0
        self.folder=output/'trace';self.folder.mkdir()
        self.branches={};self.contexts={};self.hashes={};self.branch_counts={'positive':0,'negative':0}
        self.saved=(0,25,40,47,49)

    def before_model(self, kwargs: dict, scheduler) -> str:
        assert kwargs['cfg_scale']==self.guidance and not kwargs['cfg_merge']
        branch='positive' if kwargs['positive'] else 'negative'
        assert branch not in self.branches
        context=kwargs['context']
        if branch not in self.contexts:
            self.contexts[branch]=context.detach().cpu()
            self.hashes[branch]=tensor_summary(context)
        assert torch.equal(context,self.contexts[branch].to(context.device))
        if 'vace_context' not in self.contexts:
            self.contexts['vace_context']=kwargs['vace_context'].detach().cpu()
        assert torch.equal(kwargs['vace_context'],self.contexts['vace_context'].to(context.device))
        if not self.branches:
            self.latent=kwargs['latents'].detach()
            self.model_timestep=kwargs['timestep'].detach().cpu()
            self.sigma=float(scheduler.sigmas[self.index])
            self.timestep=float(scheduler.timesteps[self.index])
        else:
            assert torch.equal(self.latent,kwargs['latents'])
            assert torch.equal(self.model_timestep,kwargs['timestep'].cpu())
        self.branch_counts[branch]+=1
        return branch

    def after_model(self, branch: str, prediction: torch.Tensor) -> None:
        self.branches[branch]=prediction.detach()

    def after_step(self, prediction, sample, result, scheduler) -> None:
        assert torch.equal(sample,self.latent)
        expected={'positive'} if self.guidance==1 else {'positive','negative'}
        assert set(self.branches)==expected
        reconstructed=self.branches['positive'] if self.guidance==1 else self.branches['negative']+self.guidance*(self.branches['positive']-self.branches['negative'])
        assert torch.equal(prediction,reconstructed)
        next_sigma=float(scheduler.sigmas[self.index+1]) if self.index<49 else 0.0
        row={'sampler_step':self.index,'sigma':self.sigma,'next_sigma':next_sigma,'timestep':self.timestep,
             'model_timestep_bf16':self.model_timestep.float().tolist(),'effective_cfg':self.guidance,
             'latent':summary(sample),'prediction':summary(prediction),'euler_actual_update':summary(result.float()-sample.float()),
             'branches':{k:summary(v) for k,v in self.branches.items()},'context_hashes':{k:v['sha256'] for k,v in self.hashes.items()}}
        with (self.output/'ROLLOUT_STATS.jsonl').open('a') as stream:stream.write(json.dumps(row)+'\n')
        if self.index in self.saved:
            atomic_torch(self.folder/f'step-{self.index:02d}.pt',{'latent':sample.detach().cpu(),
                'branches':{k:v.cpu() for k,v in self.branches.items()},'combined':prediction.detach().cpu(),
                'sigma':self.sigma,'timestep':self.timestep,'model_timestep':self.model_timestep})
        if self.index==0:atomic_torch(self.folder/'contexts.pt',self.contexts)
        self.index+=1;self.branches.clear();self.latent=None
