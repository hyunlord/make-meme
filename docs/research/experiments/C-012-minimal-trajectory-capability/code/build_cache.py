# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# Run with existing research Python: build_cache.py /abs/config.json [--cpu-only]
"""C-012 training cache for the two-clip capability test + RECONSTRUCTION_CONTROL decode.

Public VAE encodes: endpoint VACE context 2 (inactive+reactive, shared by A/B), two independent
single-frame endpoint encodes 2, A/B target encodes 2 = 6. Diagnostic decodes: A/B = 2.
The intermediate target latent is a training target only; sidecars for inference never contain it.
"""
from pathlib import Path
import hashlib
import json
import os
import sys
import time

import numpy as np
from PIL import Image
from pydantic import BaseModel, ConfigDict

PATHS = ('A', 'B')
SEQUENCE = {'A': 'path_A', 'B': 'path_B'}     # lookup keys only; never a network input


class Config(BaseModel):
    model_config = ConfigDict(frozen=True, extra='forbid')
    upstream: Path
    weights: Path
    tokenizer: Path
    c009_code: Path
    task: Path
    output_cache: Path
    output: Path


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def tensor_sha(tensor) -> str:
    import torch
    return digest(tensor.detach().cpu().contiguous().view(torch.uint8).numpy().tobytes())


def main() -> None:
    config = Config.model_validate_json(Path(sys.argv[1]).read_text())
    code = Path(__file__).resolve().parent
    sys.path.insert(0, str(code))
    sys.path.insert(0, str(code / 'gen'))
    sys.path.insert(0, str(config.c009_code))
    from render_task import PROMPT, W, H, D
    from rebuild_cache import white_masks, check_mask_contract, check_normalized, images
    manifest = json.loads((config.task / 'TASK_MANIFEST.json').read_text())
    for rel, expected in manifest['files'].items():
        assert digest((config.task / rel).read_bytes()) == expected, rel
    with Image.open(config.task / 'anchors/start.png') as a, Image.open(config.task / 'anchors/end.png') as b:
        start, end = a.convert('RGB').copy(), b.convert('RGB').copy()
    frames = [start, *[Image.new('RGB', (W, H), (127, 127, 127)) for _ in range(31)], end]
    pixels = np.stack([np.asarray(f) for f in frames])
    assert (pixels[1:32] == 127).all()
    receipts = {'mask': check_mask_contract(white_masks()), 'condition_rgb_sha256': digest(pixels.tobytes())}
    os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', TOKENIZERS_PARALLELISM='false')
    sys.path.insert(0, str(config.upstream))
    import torch
    if '--cpu-only' in sys.argv[2:]:
        print(json.dumps({'status': 'CPU_PASS', **receipts, 'cuda_initialized': torch.cuda.is_initialized()}))
        return
    config.output.mkdir(parents=True, exist_ok=False)
    config.output_cache.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    from diffsynth.models import wan_video_dit
    for flag in ('FLASH_ATTN_3_AVAILABLE', 'FLASH_ATTN_2_AVAILABLE', 'SAGE_ATTN_AVAILABLE'):
        setattr(wan_video_dit, flag, False)
    from diffsynth.pipelines.wan_video import WanVideoPipeline, ModelConfig, WanVideoUnit_PromptEmbedder, WanVideoUnit_VACE
    paths = [str(config.weights / 'models_t5_umt5-xxl-enc-bf16.pth'), str(config.weights / 'Wan2.1_VAE.pth')]
    pipe = WanVideoPipeline.from_pretrained(torch_dtype=torch.bfloat16, device='cuda',
        model_configs=[ModelConfig(path=p, skip_download=True) for p in paths],
        tokenizer_config=ModelConfig(path=str(config.tokenizer), skip_download=True))
    for name in ('text_encoder', 'vae'):
        getattr(pipe, name).eval().requires_grad_(False)
    from point_features import sample_anchor_patches
    counts = {'public_vae_encode': 0, 'diagnostic_decode': 0}
    tile = dict(tiled=True, tile_size=(30, 52), tile_stride=(15, 26))
    with torch.no_grad():
        receipts['normalized_mask'] = check_normalized(pipe, white_masks())
        prompt = WanVideoUnit_PromptEmbedder()
        context = prompt.process(pipe, PROMPT, True)['context'].cpu()
        negative = prompt.process(pipe, 'blurry, distorted, deformed, watermark', False)['context'].cpu()
        vace_context = WanVideoUnit_VACE().process(pipe, frames, white_masks(), None, 1.0, H, W, 33, True,
                                                   (30, 52), (15, 26))['vace_context'].cpu()
        counts['public_vae_encode'] += 2
        assert vace_context.shape == (1, 96, 9, 30, 52) and torch.isfinite(vace_context.float()).all()
        endpoints = torch.cat([pipe.vae.encode(pipe.preprocess_video([f]), device='cuda', **tile).cpu() for f in (start, end)])
        counts['public_vae_encode'] += 2
        files, payloads = {}, {}
        for path in PATHS:
            source = images(config.task / path / 'source')
            assert source[0].tobytes() == start.tobytes() and source[32].tobytes() == end.tobytes()
            with np.load(config.task / path / 'tracks.npz') as tracks:
                positions = (torch.from_numpy(tracks['tracks']).float() + .5) / torch.tensor([float(W), float(H)])
                visible, valid = torch.from_numpy(tracks['visible']), torch.from_numpy(tracks['valid'])
                anchor_valid = torch.from_numpy(tracks['anchor_valid'])
            patches = sample_anchor_patches(endpoints, positions[[0, 32]], anchor_valid)
            box_wh = torch.tensor([[D / W, D / H]]).repeat(33, 1)
            clean = pipe.vae.encode(pipe.preprocess_video(source), device='cuda', **tile).cpu()
            counts['public_vae_encode'] += 1
            masks = []
            for t in range(33):
                with Image.open(config.task / path / 'mask' / f'{t:03d}.png') as m:
                    masks.append(torch.from_numpy((np.array(m) > 0).copy()).float())
            loss_mask = torch.nn.functional.adaptive_avg_pool3d(torch.stack(masks)[None, None], (9, 30, 52))
            point = {'sequence': SEQUENCE[path], 'split': 'train', 'prompt': PROMPT, 'patches': patches,
                     'anchor_valid': anchor_valid, 'positions': positions, 'visible': visible, 'valid': valid, 'box_wh': box_wh}
            train = {**point, 'context': context, 'negative_context': negative, 'vace_context': vace_context,
                     'clean_latent': clean, 'loss_mask': loss_mask}
            for name, value in (('train', train), ('sidecar', point)):
                target = config.output_cache / f'{SEQUENCE[path]}.{name}.pt'
                torch.save(value, target.with_suffix('.tmp')); target.with_suffix('.tmp').replace(target)
                files[target.name] = digest(target.read_bytes())
            payloads[path] = train
            decoded = pipe.vae.decode(clean.to('cuda'), device='cuda', **tile)
            counts['diagnostic_decode'] += 1
            folder = config.output / f'recon_{path}'; folder.mkdir()
            for t, frame in enumerate(pipe.vae_output_to_video(decoded)):
                frame.save(folder / f'{t:03d}.png')
        a, b = payloads['A'], payloads['B']
        identical = {k: bool(torch.equal(a[k], b[k])) for k in ('patches', 'anchor_valid', 'visible', 'valid', 'box_wh',
                                                                  'context', 'negative_context', 'vace_context')}
        identical['positions_endpoints'] = bool(torch.equal(a['positions'][[0, 32]], b['positions'][[0, 32]]))
        identical['positions_middle'] = bool(torch.equal(a['positions'][1:32], b['positions'][1:32]))
        identical['clean_latent_frame0'] = bool(torch.equal(a['clean_latent'][:, :, 0], b['clean_latent'][:, :, 0]))
        assert all(v for k, v in identical.items() if k not in ('positions_middle', 'clean_latent_frame0'))
        assert not identical['positions_middle']
        exclusions = {'clips': {SEQUENCE[p]: {'excluded_point_ids': []} for p in PATHS}}
        (config.output_cache / 'point-exclusions.json').write_text(json.dumps(exclusions, indent=2))
    cache_manifest = {'schema': 'C-012 cache', 'mask_contract': 'white_v1: (v,v,v), v=0 at frames 0/32 else 255',
                      'condition_family': 'endpoint_gray127_v1', 'task_manifest_sha256': digest((config.task / 'TASK_MANIFEST.json').read_bytes()),
                      'files': files, 'vace_context_sha256': tensor_sha(vace_context), 'context_sha256': tensor_sha(context),
                      'ab_identity': identical, 'counts': counts, **receipts}
    (config.output_cache / 'CACHE_MANIFEST.json').write_text(json.dumps(cache_manifest, indent=2))
    (config.output / 'result.json').write_text(json.dumps({'status': 'COMPLETE', **counts,
        'elapsed_seconds': time.monotonic() - started, 'ab_identity': identical}, indent=2))
    print(json.dumps({'status': 'COMPLETE', **counts, 'ab_identity': identical}))


if __name__ == '__main__':
    main()
