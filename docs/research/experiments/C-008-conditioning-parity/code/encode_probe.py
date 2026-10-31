# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# Run with existing research Python: encode_probe.py /absolute/config.json [--cpu-only]
"""C-008: re-run the C (cache) and G (generation) VACE encodings and record VAE runtime state.

Observation only: hooks record summaries/clones and never modify inputs, caches, RNG or outputs.
"""
from collections import Counter
from pathlib import Path
from typing import Literal
import hashlib
import importlib.util
import inspect
import json
import os
import sys
import time

import numpy as np
from PIL import Image
from pydantic import BaseModel, ConfigDict


class ProbeConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra='forbid')
    upstream: Path
    weights: Path
    tokenizer: Path
    c006_root: Path
    c007_root: Path
    output: Path
    path: Literal['C', 'G']
    clips: list[str]
    endpoint_and_target: bool = True
    repeat_context: bool = True
    cross_call_in_g: bool = True
    # legacy_int: C-006 `Image.new('RGB', size, 255)` -> PIL packs the int as (255, 0, 0).
    # white: the single C-008 intervention, (255, 255, 255) as the official helper produces.
    mask_fill: Literal['legacy_int', 'white'] = 'legacy_int'
    semantics_checks: bool = False
    fixed_cache_root: Path | None = None


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def summary(tensor) -> dict:
    import torch
    cpu = tensor.detach().to('cpu').contiguous()
    as_float = cpu.float()
    return {'shape': list(cpu.shape), 'dtype': str(cpu.dtype), 'device': str(tensor.device),
            'sha256': digest(cpu.view(torch.uint8).numpy().tobytes()),
            'finite': bool(torch.isfinite(as_float).all()),
            'min': float(as_float.min()), 'max': float(as_float.max()),
            'rms': float(as_float.pow(2).mean().sqrt())}


def atomic_json(path: Path, value) -> None:
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2, default=str))
    temporary.replace(path)


def images(root: Path) -> list[Image.Image]:
    result = []
    for index in range(33):
        with Image.open(root / f'{index:03d}.png') as image:
            assert image.mode == 'RGB' and image.size == (416, 240)
            result.append(image.copy())
    return result


class VaeObserver:
    """Counts public encodes and reports whether the causal temporal cache was actually used."""

    def __init__(self, pipe):
        from diffsynth.models.wan_video_vae import CausalConv3d
        self.pipe = pipe
        self.calls = []
        self.cache_hits = Counter()
        self.public_encode = pipe.vae.encode
        self.inner_encode = pipe.vae.model.encode
        for module in pipe.vae.model.encoder.modules():
            if isinstance(module, CausalConv3d):
                module.register_forward_pre_hook(self._pre_hook)
        pipe.vae.encode = self._encode
        pipe.vae.model.encode = self._inner

    def _pre_hook(self, module, args):
        given = len(args) > 1 and args[1] is not None
        self.cache_hits['cache_given' if given else 'no_cache'] += 1

    def _inner(self, x, scale):
        before = dict(self.cache_hits)
        out = self.inner_encode(x, scale)
        feat = self.pipe.vae.model._enc_feat_map
        self.inner_rows.append({'tile_input_shape': list(x.shape), 'out_shape': list(out.shape),
            'feat_map_len': len(feat), 'feat_map_tensor_entries': sum(1 for f in feat if hasattr(f, 'shape')),
            'causal_conv_calls_with_cache': self.cache_hits['cache_given'] - before.get('cache_given', 0),
            'causal_conv_calls_without_cache': self.cache_hits['no_cache'] - before.get('no_cache', 0)})
        return out

    def _encode(self, videos, device, **kwargs):
        import torch
        self.inner_rows = []
        row = {'index': len(self.calls), 'input': summary(videos if isinstance(videos, torch.Tensor) else torch.stack(list(videos))),
               'kwargs': {k: v for k, v in kwargs.items()}, 'device': str(device),
               'grad_enabled': torch.is_grad_enabled(), 'inference_mode': torch.is_inference_mode_enabled(),
               'autocast': torch.is_autocast_enabled()}
        out = self.public_encode(videos, device, **kwargs)
        row['output'] = summary(out)
        tiles = self.inner_rows
        row['tiles'] = len(tiles)
        row['tile0'] = tiles[0] if tiles else None
        row['all_tiles_same_cache_usage'] = len({(t['causal_conv_calls_with_cache'], t['causal_conv_calls_without_cache']) for t in tiles}) <= 1
        self.calls.append(row)
        return out


def runtime_state(pipe) -> dict:
    import torch
    import diffsynth
    from diffsynth.models import wan_video_vae
    from diffsynth.models.wan_video_vae import count_conv3d
    encoder = pipe.vae.model.encoder
    types = Counter(f'{type(m).__module__}.{type(m).__qualname__}' for m in encoder.modules())
    params = list(pipe.vae.parameters())
    scale = pipe.vae.scale
    return {'diffsynth_file': diffsynth.__file__,
            'wan_video_vae_file': wan_video_vae.__file__,
            'wan_video_vae_sha256': digest(Path(wan_video_vae.__file__).read_bytes()),
            'wan_video_pipeline_sha256': digest(Path(inspect.getfile(type(pipe))).read_bytes()),
            'vae_class': f'{type(pipe.vae).__module__}.{type(pipe.vae).__qualname__}',
            'inner_class': f'{type(pipe.vae.model).__module__}.{type(pipe.vae.model).__qualname__}',
            'encoder_count_conv3d': count_conv3d(encoder),
            'encoder_module_types': dict(types),
            'vae_training': pipe.vae.training,
            'param_dtypes': sorted({str(p.dtype) for p in params}),
            'param_devices': sorted({str(p.device) for p in params}),
            'param_count': sum(p.numel() for p in params),
            'scale': [summary(s) for s in scale] if isinstance(scale, (list, tuple)) else summary(scale),
            'pipe_device': str(pipe.device), 'pipe_dtype': str(pipe.torch_dtype),
            'vram_management_enabled': getattr(pipe, 'vram_management_enabled', None),
            'loaded_models': [name for name in ('dit', 'vace', 'text_encoder', 'vae') if getattr(pipe, name, None) is not None],
            'torch': torch.__version__}


def compare(new, old) -> dict:
    a, b = new.float(), old.float()
    assert a.shape == b.shape, (a.shape, b.shape)
    diff = a - b
    ref = b.pow(2).mean().sqrt().item()
    rms = diff.pow(2).mean().sqrt().item()
    result = {'exact': bool(torch_equal(new, old)), 'max_abs': diff.abs().max().item(), 'rms': rms,
              'ref_rms': ref, 'rel_rms': rms / ref if ref > 1e-12 else None}
    if a.dim() == 5 and a.shape[1] == 96:
        for name, s in (('inactive', slice(0, 16)), ('reactive', slice(16, 32)), ('mask', slice(32, 96))):
            result[name + '_per_t_rms'] = [diff[:, s, t].pow(2).mean().sqrt().item() for t in range(a.shape[2])]
    elif a.dim() == 5:
        result['per_t_rms'] = [diff[:, :, t].pow(2).mean().sqrt().item() for t in range(a.shape[2])]
    return result


def torch_equal(a, b) -> bool:
    import torch
    return a.dtype == b.dtype and torch.equal(a, b)


def load_pipe(config: ProbeConfig, full: bool):
    import torch
    from diffsynth.pipelines.wan_video import WanVideoPipeline, ModelConfig
    from diffsynth.models import wan_video_dit
    wan_video_dit.FLASH_ATTN_3_AVAILABLE = False
    wan_video_dit.FLASH_ATTN_2_AVAILABLE = False
    wan_video_dit.SAGE_ATTN_AVAILABLE = False
    t5 = str(config.weights / 'models_t5_umt5-xxl-enc-bf16.pth')
    vae = str(config.weights / 'Wan2.1_VAE.pth')
    if full:  # exactly C-007 generate_video.py
        checkpoints = sorted(config.weights.glob('diffusion_pytorch_model*.safetensors'))
        paths = [list(map(str, checkpoints)), t5, vae]
    else:  # exactly C-006 runtime_common.load_pipeline(phase='cache')
        paths = [t5, vae]
    pipe = WanVideoPipeline.from_pretrained(torch_dtype=torch.bfloat16, device='cuda',
        model_configs=[ModelConfig(path=p, skip_download=True) for p in paths],
        tokenizer_config=ModelConfig(path=str(config.tokenizer), skip_download=True))
    for name in ('dit', 'vace', 'text_encoder', 'vae'):
        module = getattr(pipe, name, None)
        if module is not None:
            module.eval().requires_grad_(False)
    return pipe


def generation_mask(t: int, mask_fill: str) -> Image.Image:
    value = 0 if t in (0, 32) else 255
    return Image.new('RGB', (416, 240), value if mask_fill == 'legacy_int' else (value,) * 3)


def c_condition(config: ProbeConfig, clip: str):
    """C-006 cache_conditions.py; only the mask fill differs when mask_fill='white'."""
    root = config.c006_root / 'data' / clip
    source = images(root / 'source')
    layout = images(root / 'layout')
    condition = [source[0], *layout[1:32], source[32]]
    masks = [generation_mask(t, config.mask_fill) for t in range(33)]
    return source, condition, masks


def g_config(config: ProbeConfig, clip: str, prompt: str):
    spec = importlib.util.spec_from_file_location('c007_generate', config.c007_root / 'code/generate_video.py')
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(config.c007_root / 'code'))
    spec.loader.exec_module(module)
    base = json.loads((config.c007_root / 'configs/BASE_5.json').read_text())
    data = config.c006_root / 'data' / clip
    base.update(start_anchor=str(data / 'anchors/start.png'), end_anchor=str(data / 'anchors/end.png'),
                layout_dir=str(data / 'layout'), prompt=prompt, output=str(config.output / f'g-{clip}-unused'))
    return module, module.Config.model_validate(base)


def causal_semantics(pipe, source, clean, endpoints) -> dict:
    """Causal contract: latent t depends on frames <= 4t only; prefix encodes agree with the full encode."""
    import torch
    kwargs = dict(device='cuda', tiled=True, tile_size=(30, 52), tile_stride=(15, 26))
    result = {'first_frame_alone_vs_full_t0': [compare(endpoints[0:1, :, 0:1], clean[:, :, 0:1])],
              'last_frame_alone_vs_full_t8_is_not_expected_equal': compare(endpoints[1:2, :, 0:1], clean[:, :, 8:9])}
    prefix = pipe.vae.encode(pipe.preprocess_video(source[:5]), **kwargs).cpu()
    result['prefix5_vs_full_t0_1'] = compare(prefix, clean[:, :, :2])
    future = [*source[:17], *[Image.new('RGB', (416, 240), (0, 0, 0))] * 16]
    altered = pipe.vae.encode(pipe.preprocess_video(future), **kwargs).cpu()
    result['future_frames_17_32_blacked_vs_full_t0_4'] = compare(altered[:, :, :5], clean[:, :, :5])
    result['future_frames_17_32_blacked_vs_full_t5_8_should_differ'] = compare(altered[:, :, 5:], clean[:, :, 5:])
    return result


class PrepareDone(Exception):
    pass


def run_g_prepare(pipe, module, gconfig):
    """C-007 pipe(...) call unchanged; stop at the first denoising iteration (no DiT forward)."""
    frames, masks, receipt = module.condition(gconfig)
    captured = {}
    vace_unit = next(u for u in pipe.units if type(u).__name__ == 'WanVideoUnit_VACE')
    original = vace_unit.process
    def observed(*args, **kwargs):
        result = original(*args, **kwargs)
        captured['vace_context'] = result['vace_context'].detach().clone().cpu()
        return result
    vace_unit.process = observed
    def stop_before_denoise(timesteps):
        captured['timesteps'] = len(timesteps)
        raise PrepareDone
    try:
        pipe(prompt=gconfig.prompt, negative_prompt=gconfig.negative_prompt,
             vace_video=frames, vace_video_mask=masks, vace_reference_image=None,
             height=240, width=416, num_frames=33, seed=gconfig.seed, rand_device='cpu', tiled=True,
             cfg_scale=gconfig.guidance, num_inference_steps=50, sigma_shift=5, output_type='floatpoint',
             progress_bar_cmd=stop_before_denoise)
    except PrepareDone:
        pass
    finally:
        vace_unit.process = original
    assert 'vace_context' in captured and captured['timesteps'] == 50
    return frames, masks, receipt, captured['vace_context']


def main() -> None:
    config_path = Path(sys.argv[1])
    assert config_path.is_absolute()
    config = ProbeConfig.model_validate_json(config_path.read_text())
    split = {c['sequence']: c for c in json.loads((config.c006_root / 'DATA_SPLIT.json').read_text())['clips']}
    for clip in config.clips:
        assert clip in split and split[clip]['split'] == 'validation'
        assert (config.c006_root / 'cache-v2' / f'{clip}.pt').is_file()
    os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', TOKENIZERS_PARALLELISM='false')
    sys.path.insert(0, str(config.upstream))
    import torch
    if '--cpu-only' in sys.argv[2:]:
        print(json.dumps({'status': 'CPU_PASS', 'cuda_initialized': torch.cuda.is_initialized()}))
        return
    config.output.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    pipe = load_pipe(config, full=config.path == 'G')
    observer = VaeObserver(pipe)
    from diffsynth.pipelines.wan_video import WanVideoUnit_VACE
    report = {'path': config.path, 'runtime': runtime_state(pipe), 'clips': {}}
    tensors = {}
    with torch.no_grad():
        for clip in config.clips:
            old = torch.load(config.c006_root / 'cache-v2' / f'{clip}.pt', map_location='cpu', weights_only=True)
            row = {}
            source, condition, masks = c_condition(config, clip)
            if config.path == 'G':
                module, gconfig = g_config(config, clip, split[clip]['prompt'])
                g_frames, g_masks, receipt, context = run_g_prepare(pipe, module, gconfig)
                row['g_inputs_equal_c_inputs'] = (all(a.tobytes() == b.tobytes() for a, b in zip(g_frames, condition))
                                                  and all(a.tobytes() == b.tobytes() for a, b in zip(g_masks, masks)))
                tensors[f'{clip}/G'] = context
                row['G_vs_cache_old'] = compare(context, old['vace_context'])
                if clip == 'elephant':
                    old_g = torch.load(config.c007_root / 'outputs/BASE_5/trace/contexts.pt', map_location='cpu', weights_only=True)['vace_context']
                    row['G_vs_G_old'] = compare(context, old_g)
                if config.cross_call_in_g:
                    direct = WanVideoUnit_VACE().process(pipe, condition, masks, None, 1.0, 240, 416, 33, True, (30, 52), (15, 26))['vace_context'].cpu()
                    tensors[f'{clip}/C_call_in_G_process'] = direct
                    row['C_call_in_G_process_vs_G'] = compare(direct, context)
                    row['C_call_in_G_process_vs_cache_old'] = compare(direct, old['vace_context'])
            else:
                context = WanVideoUnit_VACE().process(pipe, condition, masks, None, 1.0, 240, 416, 33, True, (30, 52), (15, 26))['vace_context'].cpu()
                tensors[f'{clip}/C'] = context
                row['C_vs_cache_old'] = compare(context, old['vace_context'])
                if clip == 'elephant':
                    old_g = torch.load(config.c007_root / 'outputs/BASE_5/trace/contexts.pt', map_location='cpu', weights_only=True)['vace_context']
                    row['C_vs_G_old'] = compare(context, old_g)
                if config.repeat_context:
                    again = WanVideoUnit_VACE().process(pipe, condition, masks, None, 1.0, 240, 416, 33, True, (30, 52), (15, 26))['vace_context'].cpu()
                    row['C_repeat'] = compare(again, context)
            if config.endpoint_and_target:
                sys.path.insert(0, str(config.c006_root / 'code'))
                from point_features import sample_anchor_patches
                anchors = [pipe.vae.encode(pipe.preprocess_video([frame]), device='cuda', tiled=True,
                           tile_size=(30, 52), tile_stride=(15, 26)) for frame in (source[0], source[32])]
                endpoints = torch.cat(anchors, dim=0)
                with np.load(config.c006_root / 'tracks' / clip / 'tracks.npz', allow_pickle=False) as tracks:
                    positions = (torch.from_numpy(tracks['tracks']).float() + .5) / torch.tensor([416., 240.])
                    anchor_valid = torch.from_numpy(tracks['anchor_valid'])
                patches = sample_anchor_patches(endpoints.detach().cpu(), positions[[0, 32]], anchor_valid)
                row['patches_vs_old'] = compare(patches, old['patches'])
                clean = pipe.vae.encode(pipe.preprocess_video(source), device='cuda', tiled=True,
                                        tile_size=(30, 52), tile_stride=(15, 26)).cpu()
                tensors[f'{clip}/clean_latent'] = clean
                tensors[f'{clip}/endpoints'] = endpoints.cpu()
                row['clean_latent_vs_old'] = compare(clean, old['clean_latent'])
                if config.semantics_checks:
                    row['semantics'] = causal_semantics(pipe, source, clean, endpoints.cpu())
            if config.fixed_cache_root is not None:
                assert config.path == 'C' and config.mask_fill == 'white'
                config.fixed_cache_root.mkdir(parents=True, exist_ok=True)
                payload = dict(old)
                payload['vace_context'] = context.clone()
                payload['c008_provenance'] = 'C-006 cache-v2 payload; only vace_context re-encoded with white generation mask'
                path = config.fixed_cache_root / f'{clip}.pt'
                torch.save(payload, path.with_suffix('.tmp'))
                path.with_suffix('.tmp').replace(path)
                loaded = torch.load(path, map_location='cpu', weights_only=True)
                assert all(torch.equal(loaded[k], v) for k, v in payload.items() if isinstance(v, torch.Tensor))
                row['fixed_cache'] = {'sha256': digest(path.read_bytes()),
                    'unchanged_keys_equal_old': sorted(k for k, v in old.items() if isinstance(v, torch.Tensor) and k != 'vace_context' and torch.equal(loaded[k], v)),
                    'vace_context': summary(loaded['vace_context'])}
            report['clips'][clip] = row
            atomic_json(config.output / 'report.json', report)
    report['vae_calls'] = observer.calls
    report['public_vae_encode_calls'] = len(observer.calls)
    report['elapsed_seconds'] = time.monotonic() - started
    report['dit_forward_calls'] = 0
    torch.save(tensors, config.output / 'tensors.pt')
    report['tensors_sha256'] = digest((config.output / 'tensors.pt').read_bytes())
    report['status'] = 'COMPLETE'
    atomic_json(config.output / 'report.json', report)
    print(json.dumps({'status': 'COMPLETE', 'calls': len(observer.calls)}))


if __name__ == '__main__':
    main()
