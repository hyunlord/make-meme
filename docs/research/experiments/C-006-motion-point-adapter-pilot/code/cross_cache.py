# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Optional HEAD_ONLY endpoint-retargeted cache; run after the six primary samples."""
from pathlib import Path
import json
import sys
import time
import numpy as np
import torch
from PIL import Image
sys.path.insert(0, str(Path(__file__).resolve().parent))
from runtime_common import parse_config, setup, load_pipeline, atomic_json, atomic_torch, tensor_summary
from point_features import sample_anchor_patches, retarget_endpoints
from cache_conditions import images


def main() -> None:
    config = parse_config()
    setup(config)
    manual = json.loads(config.split_manifest.read_text())
    assert manual['scope'] == 'HEAD_ONLY'
    with np.load(config.tracks_root / 'tracks.npz', allow_pickle=False) as tracked:
        source = (torch.from_numpy(tracked['tracks']).float()+.5)/torch.tensor([416., 240.])
        visible = torch.from_numpy(tracked['visible'])
        valid = torch.from_numpy(tracked['valid'])
        anchor_valid = torch.from_numpy(tracked['anchor_valid'])
    target_endpoints = torch.tensor([manual['target'][str(t)]['normalized_xy'] for t in (0, 32)])
    target_boxes = torch.tensor([manual['target'][str(t)]['bbox416_halfopen'] for t in (0, 32)])
    source_boxes = torch.tensor([manual['source'][str(t)]['bbox416_halfopen'] for t in (0, 32)])
    ratios = (target_boxes[:, 2:]-target_boxes[:, :2])/(source_boxes[:, 2:]-source_boxes[:, :2])
    positions = retarget_endpoints(source, target_endpoints, ratios)
    valid = valid & torch.isfinite(positions).all(-1) & (positions >= 0).all(-1) & (positions <= 1).all(-1)
    anchor_valid = anchor_valid & valid[[0, 32]]
    assert anchor_valid.all(), 'Three manually corresponding head points must be visible at both endpoints'
    assert torch.allclose(positions[[0, 32]], target_endpoints, atol=1e-6, rtol=0)
    box_wh_end = (target_boxes[:, 2:]-target_boxes[:, :2])/torch.tensor([416., 240.])
    tau = torch.linspace(0, 1, 33)[:, None]
    box_wh = (1-tau)*box_wh_end[0]+tau*box_wh_end[1]
    if '--cpu-only' in sys.argv:
        print(json.dumps({'status': 'CPU_PASS', 'retarget_endpoint_exact': True,
                          'shape': list(positions.shape), 'cuda_initialized': torch.cuda.is_initialized()}))
        return
    config.output.mkdir(parents=True, exist_ok=False)
    config.cache_root.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    pipe = load_pipeline(config)
    from diffsynth.pipelines.wan_video import WanVideoUnit_PromptEmbedder, WanVideoUnit_VACE
    prompt = json.loads((config.data_root/'generation-text.json').read_text())['prompt']
    anchors = []
    for name in ('start', 'end'):
        with Image.open(config.data_root/'anchors'/f'{name}.png') as image:
            assert image.size == (416, 240)
            anchors.append(image.convert('RGB').copy())
    layout = images(config.data_root/'layout')
    frames = [anchors[0], *layout[1:32], anchors[1]]
    masks = [Image.new('RGB', (416, 240), 0 if t in (0, 32) else 255) for t in range(33)]
    with torch.no_grad():
        encoder = WanVideoUnit_PromptEmbedder()
        context = encoder.process(pipe, prompt, True)['context']
        negative = encoder.process(pipe, 'blurry, distorted, deformed, watermark', False)['context']
        vace = WanVideoUnit_VACE().process(pipe, frames, masks, None, 1., 240, 416, 33, True, (30, 52), (15, 26))
        latent_endpoints = torch.cat([pipe.vae.encode(pipe.preprocess_video([anchor]), device='cuda',
            tiled=True, tile_size=(30, 52), tile_stride=(15, 26)).cpu() for anchor in anchors])
        patches = sample_anchor_patches(latent_endpoints, target_endpoints, anchor_valid)
    payload = {'sequence': 'cross-id-dog', 'split': 'exploratory', 'prompt': prompt,
        'context': context.cpu(), 'negative_context': negative.cpu(), 'vace_context': vace['vace_context'].cpu(),
        'patches': patches, 'positions': positions, 'visible': visible, 'valid': valid,
        'anchor_valid': anchor_valid, 'box_wh': box_wh}
    path = config.cache_root/'cross-id-dog.pt'
    atomic_torch(path, payload)
    restored = torch.load(path, map_location='cpu', weights_only=True)
    assert all(torch.equal(restored[key], value) for key, value in payload.items() if isinstance(value, torch.Tensor))
    atomic_json(config.output/'result.json', {'status': 'COMPLETE', 'seconds': time.monotonic()-started,
        'scope': 'HEAD_ONLY', 'points': 3, 'bbox_ratios': ratios.tolist(),
        'positions': tensor_summary(positions), 'endpoint_patches': tensor_summary(patches),
        'independent_endpoint_encodes': 2, 'clean_target_encoded': False, 'readback_exact': True})


if __name__ == '__main__':
    main()
