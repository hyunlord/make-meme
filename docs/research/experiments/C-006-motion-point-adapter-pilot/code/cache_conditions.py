# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Existing Python cache worker: independent endpoint VAE; no target leakage to adapter."""
from pathlib import Path
import json
import sys
import time
import numpy as np
import torch
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from runtime_common import parse_config, setup, load_pipeline, atomic_json, atomic_torch, tensor_summary
from point_features import sample_anchor_patches


def images(root: Path) -> list[Image.Image]:
    result = []
    for index in range(33):
        with Image.open(root / f'{index:03d}.png') as image:
            assert image.mode == 'RGB' and image.size == (416, 240)
            result.append(image.copy())
    return result


def main() -> None:
    config = parse_config()
    setup(config)
    split = json.loads(config.split_manifest.read_text())['clips']
    for clip in split:
        source = config.data_root / clip['sequence']
        assert (source / 'anchors/start.png').is_file()
        assert (config.tracks_root / clip['sequence'] / 'tracks.npz').is_file()
    if '--cpu-only' in sys.argv:
        print(json.dumps({'status': 'CPU_PASS', 'clips': len(split), 'cuda_initialized': torch.cuda.is_initialized()}))
        return
    config.output.mkdir(parents=True, exist_ok=False)
    config.cache_root.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    pipe = load_pipeline(config)
    from diffsynth.pipelines.wan_video import WanVideoUnit_PromptEmbedder, WanVideoUnit_VACE
    prompt_encoder = WanVideoUnit_PromptEmbedder()
    vace_encoder = WanVideoUnit_VACE()
    records = []
    with torch.no_grad():
        negative = prompt_encoder.process(pipe, 'blurry, distorted, deformed, watermark', False)['context']
        for clip in split:
            tick = time.monotonic()
            name = clip['sequence']
            root = config.data_root / name
            source = images(root / 'source')
            layout = images(root / 'layout')
            condition = [source[0], *layout[1:32], source[32]]
            masks = [Image.new('RGB', (416, 240), 0 if t in (0, 32) else 255) for t in range(33)]
            context = prompt_encoder.process(pipe, clip['prompt'], True)['context']
            encoded = vace_encoder.process(pipe, condition, masks, None, 1.0, 240, 416, 33, True, (30, 52), (15, 26))
            # Crucially each endpoint is its own length-one VAE call.
            anchor_latents = []
            for frame in (source[0], source[32]):
                anchor_latents.append(pipe.vae.encode(pipe.preprocess_video([frame]), device='cuda',
                                      tiled=True, tile_size=(30, 52), tile_stride=(15, 26)))
            endpoints = torch.cat(anchor_latents, dim=0)
            with np.load(config.tracks_root / name / 'tracks.npz', allow_pickle=False) as tracks:
                positions = (torch.from_numpy(tracks['tracks']).float() + .5) / torch.tensor([416., 240.])
                visible = torch.from_numpy(tracks['visible'])
                valid = torch.from_numpy(tracks['valid'])
                anchor_valid = torch.from_numpy(tracks['anchor_valid'])
                bbox = torch.from_numpy(tracks['bbox']).float()
            # Native tiled VAE returns CPU latents; patch extraction is a CPU operation.
            patches = sample_anchor_patches(endpoints.detach().cpu(), positions[[0, 32]], anchor_valid)
            box_wh = (bbox[:, 2:] - bbox[:, :2]) / torch.tensor([416., 240.])
            tau = torch.linspace(0, 1, 33)[:, None]
            box_wh = (1-tau)*box_wh[0] + tau*box_wh[-1]
            payload = {'context': context.cpu(), 'negative_context': negative.cpu(),
                'vace_context': encoded['vace_context'].cpu(), 'patches': patches.cpu(),
                'positions': positions, 'visible': visible, 'valid': valid,
                'anchor_valid': anchor_valid, 'box_wh': box_wh,
                'sequence': name, 'split': clip['split'], 'prompt': clip['prompt']}
            if clip['split'] != 'test':
                payload['clean_latent'] = pipe.vae.encode(pipe.preprocess_video(source), device='cuda',
                    tiled=True, tile_size=(30, 52), tile_stride=(15, 26)).cpu()
                spatial_masks = []
                for index in range(33):
                    with Image.open(root / 'mask' / f'{index:03d}.png') as image:
                        spatial_masks.append(torch.from_numpy((np.array(image) > 0).copy()).float())
                mask = torch.stack(spatial_masks)[None, None]
                # Fixed area-based soft mask; temporal and spatial averaging, not motion GT.
                payload['loss_mask'] = torch.nn.functional.adaptive_avg_pool3d(mask, (9, 30, 52))
            path = config.cache_root / f'{name}.pt'
            atomic_torch(path, payload)
            loaded = torch.load(path, map_location='cpu', weights_only=True)
            assert all(torch.equal(loaded[key], value) for key, value in payload.items() if isinstance(value, torch.Tensor))
            receipt = {'sequence': name, 'seconds': time.monotonic()-tick,
                'endpoint_encoder_calls': 2, 'endpoint_input_frames': [1, 1],
                'clean_target_encoded': clip['split'] != 'test',
                'adapter_appearance_source': 'independent endpoint encodes only',
                'vace_context': tensor_summary(payload['vace_context']),
                'anchor_latents': tensor_summary(endpoints), 'patches': tensor_summary(patches),
                'readback_exact': True}
            atomic_json(config.output / f'{name}.json', receipt)
            records.append(receipt)
            print(json.dumps({'cached': name, 'seconds': receipt['seconds']}), flush=True)
    atomic_json(config.output / 'result.json', {'status': 'COMPLETE', 'clips': records,
                'elapsed_seconds': time.monotonic()-started, 'sampler_calls': 0})


if __name__ == '__main__':
    main()
