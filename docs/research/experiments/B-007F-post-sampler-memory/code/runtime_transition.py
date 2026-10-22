"""Observe completed sampling and durably preserve the exact VAE decode input."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import torch
from safetensors.torch import load_file, save_file
from runtime_observe import phase

_destination: Path | None = None
_provenance: dict = {}
_calls = 0
_steps = 0
_last: dict = {}


def atomic_json(path: Path, value: dict) -> None:
    temporary = path.with_suffix(path.suffix + '.tmp')
    with temporary.open('x') as stream:
        json.dump(value, stream, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def configure(destination: Path, config: dict, record: dict, pipeline) -> None:
    global _destination, _provenance, _calls, _steps
    _destination = destination
    _calls = _steps = 0
    root = destination.parents[1]
    vae = pipeline.vae
    def values(item):
        if isinstance(item, torch.Tensor):
            return {'shape':list(item.shape),'dtype':str(item.dtype),'values':item.detach().cpu().tolist()}
        return [values(part) for part in item] if isinstance(item,(list,tuple)) else item
    _provenance = {'config':config,'input_file_hashes':record['input_file_hashes'],
        'preprocessed_inputs':record['inputs'], 'normalization':{
            'convention':'Exact normalized model-space x0 passed to WanVAE.decode; wrapper applies scale=[mean,1/std]; no external inverse scaling',
            'mean':values(vae.mean),'std':values(vae.std),'scale':values(vae.scale)},
        'upstream_source_hashes':json.loads((root/'reports/source_hashes.json').read_text()),
        'model_and_code_manifest':json.loads((root/'PREREGISTERED_CODE.json').read_text()),
        'registered_inputs':json.loads((root/'PREREGISTERED_INPUTS.json').read_text()),
        'crop':'official resize_for_rectangle_crop(center), unchanged',
        'reference_included_in_generated_latent':False}


def model_called() -> None:
    global _calls
    _calls += 1


def step_completed(timestep: torch.Tensor, scheduler) -> None:
    global _steps, _last
    _steps += 1
    _last = {'completed_steps':_steps,'actual_model_calls':_calls,
             'last_timestep':float(timestep.detach().cpu()),
             'scheduler_sigmas':scheduler.sigmas.detach().cpu().tolist()}
    if _destination is None:
        raise RuntimeError('Missing transition destination')
    atomic_json(_destination/'sampler_progress.json',_last)
    phase('sampler_step_completed_'+str(_steps))


def preserve_final(x0: list[torch.Tensor], history_latent, segment_index: int, segment_start: int=0, segment_end: int=17, segment_count: int=1) -> None:
    """Only bounded latent copies; never retain CUDA tensors in global state."""
    if _destination is None or len(x0)!=1 or _steps!=40 or _calls!=80:
        raise RuntimeError('Final sampler contract not fulfilled')
    phase('sampler_loop_exit')
    if torch.cuda.is_initialized():
        torch.cuda.synchronize()
    phase('sampler_cuda_completion')
    phase('final_latent_save_start')
    value = x0[0].detach().to(device='cpu',copy=True).contiguous()
    if not bool(torch.isfinite(value).all()):
        raise RuntimeError('Nonfinite final decode latent')
    path = _destination/'final_latent.safetensors'
    temporary = path.with_suffix('.safetensors.tmp')
    if path.exists() or temporary.exists():
        raise FileExistsError('Final latent must never be overwritten')
    save_file({'x0':value},str(temporary))
    with temporary.open('rb') as stream:
        os.fsync(stream.fileno())
    restored = load_file(str(temporary))['x0']
    if restored.dtype!=value.dtype or not torch.equal(restored,value):
        raise RuntimeError('Latent readback mismatch')
    os.replace(temporary,path)
    fd=os.open(path.parent,os.O_RDONLY)
    try: os.fsync(fd)
    finally: os.close(fd)
    run=json.loads((_destination/'run.json').read_text())
    metadata={**_provenance,**_last,'initial_noise':run['initial_noise'],
        'segment_index':segment_index,'segment_start':segment_start,'segment_end':segment_end,'segment_count':segment_count,
        'history_present':history_latent is not None,'history_shape':list(history_latent.shape) if history_latent is not None else None,
        'shape':list(value.shape),'dtype':str(value.dtype),'original_device':str(x0[0].device),
        'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
        'value_sha256':hashlib.sha256(value.view(torch.uint8).numpy().tobytes()).hexdigest(),
        'readback_exact':True,'status':'FINAL_LATENT_SAVED'}
    atomic_json(_destination/'final_latent.json',metadata)
    phase('final_latent_save_end')


def post_sampler_decode(model, vae, x0, offload_model: bool, rank: int, *, skip_cpu: bool=True):
    """The only changed movement is this final DiT CPU transfer."""
    if offload_model:
        if skip_cpu:
            phase('post_sampler_offload_SKIPPED')
        else:
            model.cpu()
        phase('empty_cache_start')
        torch.cuda.empty_cache()
        phase('empty_cache_end')
    if rank!=0:
        raise RuntimeError('Single-rank experiment only')
    phase('vae_decode_start')
    result=vae.decode(x0)
    phase('vae_decode_cuda_sync_start')
    if torch.cuda.is_initialized():
        torch.cuda.synchronize()
    phase('vae_decode_cuda_sync_end')
    phase('vae_decode_end')
    return result
