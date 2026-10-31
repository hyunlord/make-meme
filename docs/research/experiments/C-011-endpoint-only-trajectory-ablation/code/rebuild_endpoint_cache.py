# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# Run with existing research Python: rebuild_endpoint_cache.py /absolute/config.json [--cpu-only]
"""C-011: E cache = C-009 white (L) cache with vace_context re-encoded from [A0, gray127 x31, A32] and the white mask.

Only vace_context changes; every other key is carried byte-identically from the C-009 L cache.
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

CONDITION_FAMILY = 'endpoint_gray127_v1'
CLIPS = ('bear', 'blackswan', 'bmx-bumps', 'boat', 'bus', 'camel', 'cows', 'dance-twirl', 'elephant', 'goat')


class Config(BaseModel):
    model_config = ConfigDict(frozen=True, extra='forbid')
    upstream: Path
    weights: Path
    tokenizer: Path
    c006_root: Path
    c009_code: Path
    layout_cache: Path
    output_cache: Path
    output: Path


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def tensor_sha(tensor) -> str:
    import torch
    cpu = tensor.detach().cpu().contiguous()
    return digest(cpu.view(torch.uint8).numpy().tobytes())


def gray_frames(source0: Image.Image, source32: Image.Image) -> list[Image.Image]:
    return [source0, *[Image.new('RGB', (416, 240), (127, 127, 127)) for _ in range(31)], source32]


def check_endpoint_frames(frames: list[Image.Image], a0: Image.Image, a32: Image.Image) -> dict:
    pixels = np.stack([np.asarray(f) for f in frames])
    assert pixels.shape == (33, 240, 416, 3) and pixels.dtype == np.uint8
    assert (pixels[1:32] == 127).all(), 'middle frames must be gray127 on every channel'
    assert frames[0].tobytes() == a0.tobytes() and frames[32].tobytes() == a32.tobytes()
    return {'middle_all_127': True, 'anchors_byte_equal_source_0_32': True, 'pixel_sha256': digest(pixels.tobytes())}


def main() -> None:
    config = Config.model_validate_json(Path(sys.argv[1]).read_text())
    sys.path.insert(0, str(config.c009_code))
    from rebuild_cache import white_masks, check_mask_contract, check_normalized, images, compare_payloads
    layout_manifest_path = config.layout_cache / 'CACHE_MANIFEST.json'
    layout_manifest = json.loads(layout_manifest_path.read_text())
    assert layout_manifest['mask_contract'].startswith('white_v1')
    for clip in CLIPS:
        assert digest((config.layout_cache / f'{clip}.pt').read_bytes()) == layout_manifest['files'][clip]['sha256']
    receipts = {'mask': check_mask_contract(white_masks())}
    os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', TOKENIZERS_PARALLELISM='false')
    sys.path.insert(0, str(config.upstream))
    import torch
    if '--cpu-only' in sys.argv[2:]:
        print(json.dumps({'status': 'CPU_PASS', **receipts, 'cuda_initialized': torch.cuda.is_initialized()}))
        return
    config.output.mkdir(parents=True, exist_ok=False)
    config.output_cache.mkdir(parents=True, exist_ok=False)
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
    pipe = load_pipeline(runtime)  # same T5+VAE cache-phase load as C-006/C-008/C-009
    from diffsynth.pipelines.wan_video import WanVideoUnit_VACE
    files, encodes = {}, 0
    with torch.no_grad():
        for clip in CLIPS:
            layout_path = config.layout_cache / f'{clip}.pt'
            old = torch.load(layout_path, map_location='cpu', weights_only=True)
            source = images(config.c006_root / 'data' / clip / 'source')
            frames, masks = gray_frames(source[0], source[32]), white_masks()
            row = {'frames': check_endpoint_frames(frames, source[0], source[32]),
                   'mask': check_mask_contract(masks), 'normalized_mask': check_normalized(pipe, masks)}
            normalized = pipe.preprocess_video(frames)
            row['normalized_gray_value'] = sorted({float(v) for v in normalized[0, :, 1:32].unique().tolist()})
            row['normalized_dtype'] = str(normalized.dtype)
            context = WanVideoUnit_VACE().process(pipe, frames, masks, None, 1.0, 240, 416, 33, True,
                                                 (30, 52), (15, 26))['vace_context'].cpu()
            encodes += 2
            old_ctx = old['vace_context']
            assert context.shape == old_ctx.shape == (1, 96, 9, 30, 52) and context.dtype == old_ctx.dtype
            assert torch.isfinite(context.float()).all()
            row['inactive_equal_layout'] = bool(torch.equal(context[:, :16], old_ctx[:, :16]))
            row['mask64_equal_layout'] = bool(torch.equal(context[:, 32:], old_ctx[:, 32:]))
            row['reactive_rms_vs_layout'] = float((context[:, 16:32].float() - old_ctx[:, 16:32].float()).pow(2).mean().sqrt())
            row['reactive_latent0_equal_layout'] = bool(torch.equal(context[:, 16:32, 0], old_ctx[:, 16:32, 0]))
            row['reactive_rms'] = float(context[:, 16:32].float().pow(2).mean().sqrt())
            assert row['mask64_equal_layout'] and row['reactive_rms_vs_layout'] > 0
            new = dict(old)
            new['vace_context'] = context.clone()
            path = config.output_cache / f'{clip}.pt'
            torch.save(new, path.with_suffix('.tmp'))
            path.with_suffix('.tmp').replace(path)
            restored = torch.load(path, map_location='cpu', weights_only=True)
            row['unchanged_fields'] = compare_payloads(old, restored)
            assert torch.equal(restored['vace_context'], context)
            row['layout_parent_file_sha256'] = digest(layout_path.read_bytes())
            row['vace_context_sha256'] = tensor_sha(context)
            row['file_sha256'] = digest(path.read_bytes())
            files[clip] = row
            print(json.dumps({'cache': clip, 'inactive_equal_layout': row['inactive_equal_layout']}), flush=True)
    manifest = {'schema': 'C-011 cache', 'mask_contract': 'white_v1: (v,v,v), v=0 at frames 0/32 else 255',
                'condition_family': CONDITION_FAMILY,
                'middle_rgb': '(127,127,127) on all 31 middle frames; anchors = source frames 0/32',
                'source_layout_parent_manifest_sha256': digest(layout_manifest_path.read_bytes()),
                'files': {c: {'root': 'main', 'sha256': r['file_sha256']} for c, r in files.items()},
                # train_white.py refuses any file whose sha is listed here: the layout parents must never be trained on.
                'legacy_sha256': {c: r['layout_parent_file_sha256'] for c, r in files.items()}}
    (config.output_cache / 'CACHE_MANIFEST.json').write_text(json.dumps(manifest, indent=2))
    (config.output / 'result.json').write_text(json.dumps({'status': 'COMPLETE', 'public_vae_encode_calls': encodes,
        'elapsed_seconds': time.monotonic() - started, 'files': files}, indent=2, default=str))
    print(json.dumps({'status': 'COMPLETE', 'encodes': encodes}))


if __name__ == '__main__':
    main()
