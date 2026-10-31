# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# Run with existing research Python: rebuild_cache.py /absolute/config.json [--cpu-only]
"""C-009: replace only vace_context in the C-006 caches, re-encoded with white (v,v,v) generation masks."""
from pathlib import Path
import hashlib
import json
import os
import sys
import time

import numpy as np
from PIL import Image
from pydantic import BaseModel, ConfigDict

MASK_CONTRACT = 'white_v1: Image.new(RGB, (416,240), (v,v,v)), v=0 at frames 0/32 else 255'


class Config(BaseModel):
    model_config = ConfigDict(frozen=True, extra='forbid')
    upstream: Path
    weights: Path
    tokenizer: Path
    c006_root: Path
    c008_fixed_cache: Path
    c008_fixed_sha256: dict[str, str]
    output_cache: Path
    output_cross_cache: Path
    output: Path


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def tensor_sha(tensor) -> str:
    import torch
    cpu = tensor.detach().cpu().contiguous()
    return digest(cpu.view(torch.uint8).numpy().tobytes())


def white_masks() -> list[Image.Image]:
    return [Image.new('RGB', (416, 240), (v, v, v)) for v in (0 if t in (0, 32) else 255 for t in range(33))]


def check_mask_contract(masks: list[Image.Image]) -> dict:
    """Every channel must carry the same per-pixel value; channel-0-only checks pass the legacy red mask."""
    pixels = np.stack([np.asarray(m) for m in masks])
    assert pixels.shape == (33, 240, 416, 3) and pixels.dtype == np.uint8
    assert (pixels[..., 0] == pixels[..., 1]).all() and (pixels[..., 1] == pixels[..., 2]).all(), 'mask channels differ'
    assert (pixels[[0, 32]] == 0).all() and (pixels[1:32] == 255).all()
    return {'shape': list(pixels.shape), 'dtype': str(pixels.dtype), 'rgb_equal': True,
            'endpoints_zero': True, 'middle_255': True, 'pixel_sha256': digest(pixels.tobytes())}


def check_normalized(pipe, masks) -> dict:
    tensor = pipe.preprocess_video(masks, min_value=0, max_value=1)
    assert set(tensor.unique().tolist()) <= {0.0, 1.0}
    assert (tensor[:, 0] == tensor[:, 1]).all() and (tensor[:, 1] == tensor[:, 2]).all()
    return {'values': sorted(tensor.unique().tolist()), 'channels_equal': True}


def images(root: Path) -> list[Image.Image]:
    result = []
    for index in range(33):
        with Image.open(root / f'{index:03d}.png') as image:
            assert image.mode == 'RGB' and image.size == (416, 240)
            result.append(image.copy())
    return result


def frames_for(c006: Path, name: str) -> list[Image.Image]:
    """Same condition RGB as cache_conditions.py / cross_cache.py."""
    if name == 'cross-id-dog':
        root = c006 / 'cross-id-dog'
        anchors = []
        for label in ('start', 'end'):
            with Image.open(root / 'anchors' / f'{label}.png') as image:
                assert image.size == (416, 240)
                anchors.append(image.convert('RGB').copy())
        return [anchors[0], *images(root / 'layout')[1:32], anchors[1]]
    root = c006 / 'data' / name
    source = images(root / 'source')
    return [source[0], *images(root / 'layout')[1:32], source[32]]


def compare_payloads(old: dict, new: dict) -> dict:
    import torch
    assert set(old) == set(new), (set(old) ^ set(new))
    unchanged = {}
    for key, value in old.items():
        if key == 'vace_context':
            continue
        if isinstance(value, torch.Tensor):
            assert value.dtype == new[key].dtype and value.shape == new[key].shape and torch.equal(value, new[key]), key
            unchanged[key] = {'shape': list(value.shape), 'dtype': str(value.dtype), 'sha256': tensor_sha(value)}
        else:
            assert value == new[key], key
            unchanged[key] = value if isinstance(value, (str, int, float, bool)) else repr(value)
    return unchanged


def main() -> None:
    config = Config.model_validate_json(Path(sys.argv[1]).read_text())
    split = json.loads((config.c006_root / 'DATA_SPLIT.json').read_text())['clips']
    targets = [(row['sequence'], config.c006_root / 'cache-v2' / f"{row['sequence']}.pt", config.output_cache) for row in split]
    targets.append(('cross-id-dog', config.c006_root / 'cross-cache' / 'cross-id-dog.pt', config.output_cross_cache))
    assert len(targets) == 13 and all(path.is_file() for _, path, _ in targets)
    for name, expected in config.c008_fixed_sha256.items():
        assert digest((config.c008_fixed_cache / f'{name}.pt').read_bytes()) == expected, f'C-008 fixed cache lineage: {name}'
    receipts = {'mask': check_mask_contract(white_masks())}
    os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', TOKENIZERS_PARALLELISM='false')
    sys.path.insert(0, str(config.upstream))
    import torch
    if '--cpu-only' in sys.argv[2:]:
        print(json.dumps({'status': 'CPU_PASS', **receipts, 'cuda_initialized': torch.cuda.is_initialized()}))
        return
    for path in (config.output, config.output_cache, config.output_cross_cache):
        path.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    sys.path.insert(0, str(config.c006_root / 'code'))
    from runtime_common import RuntimeConfig, load_pipeline
    from diffsynth.models import wan_video_dit
    for flag in ('FLASH_ATTN_3_AVAILABLE', 'FLASH_ATTN_2_AVAILABLE', 'SAGE_ATTN_AVAILABLE'):
        setattr(wan_video_dit, flag, False)
    runtime = RuntimeConfig(upstream=config.upstream, weights=config.weights, tokenizer=config.tokenizer,
        data_root=config.c006_root / 'data', split_manifest=config.c006_root / 'DATA_SPLIT.json',
        tracks_root=config.c006_root / 'tracks', cache_root=config.output_cache, output=config.output,
        phase='cache', deadline_epoch=time.time() + 3600)
    pipe = load_pipeline(runtime)  # same T5+VAE cache-phase load as C-006/C-008
    from diffsynth.pipelines.wan_video import WanVideoUnit_VACE
    encodes = 0
    files = {}
    with torch.no_grad():
        for name, old_path, out_root in targets:
            old = torch.load(old_path, map_location='cpu', weights_only=True)
            row = {'source_cache_sha256': digest(old_path.read_bytes())}
            if name in config.c008_fixed_sha256:
                context = torch.load(config.c008_fixed_cache / f'{name}.pt', map_location='cpu', weights_only=True)['vace_context']
                row['vace_context_origin'] = 'reused C-008 white-mask encoding (PARITY_EXACT with generation)'
            else:
                frames, masks = frames_for(config.c006_root, name), white_masks()
                row['mask'] = check_mask_contract(masks)
                row['normalized_mask'] = check_normalized(pipe, masks)
                context = WanVideoUnit_VACE().process(pipe, frames, masks, None, 1.0, 240, 416, 33, True,
                                                     (30, 52), (15, 26))['vace_context'].cpu()
                encodes += 2
                row['vace_context_origin'] = 'C-009 re-encode, white mask'
            assert context.shape == old['vace_context'].shape == (1, 96, 9, 30, 52) and context.dtype == old['vace_context'].dtype
            new = dict(old)
            new['vace_context'] = context.clone()
            row['mask64_equal_old'] = bool(torch.equal(context[:, 32:], old['vace_context'][:, 32:]))
            diff = (context[:, :32].float() - old['vace_context'][:, :32].float())
            row['rgb_branches_rms_vs_old'] = float(diff.pow(2).mean().sqrt())
            row['latent0_equal_old'] = bool(torch.equal(context[:, :32, 0], old['vace_context'][:, :32, 0]))
            path = out_root / f'{name}.pt'
            torch.save(new, path.with_suffix('.tmp'))
            path.with_suffix('.tmp').replace(path)
            restored = torch.load(path, map_location='cpu', weights_only=True)
            row['unchanged_fields'] = compare_payloads(old, restored)
            assert torch.equal(restored['vace_context'], context)
            row['vace_context_sha256'] = tensor_sha(context)
            row['file_sha256'] = digest(path.read_bytes())
            files[name] = row
            print(json.dumps({'cache': name, 'origin': row['vace_context_origin']}), flush=True)
    manifest = {'schema': 'C-009 cache', 'mask_contract': MASK_CONTRACT,
                'files': {name: {'root': 'cross' if name == 'cross-id-dog' else 'main', 'sha256': row['file_sha256']}
                          for name, row in files.items()},
                'legacy_sha256': {name: row['source_cache_sha256'] for name, row in files.items()}}
    for root in (config.output_cache, config.output_cross_cache):
        (root / 'CACHE_MANIFEST.json').write_text(json.dumps(manifest, indent=2))
    (config.output / 'result.json').write_text(json.dumps({'status': 'COMPLETE', 'public_vae_encode_calls': encodes,
        'elapsed_seconds': time.monotonic() - started, 'files': files}, indent=2, default=str))
    print(json.dumps({'status': 'COMPLETE', 'encodes': encodes}))


if __name__ == '__main__':
    main()
