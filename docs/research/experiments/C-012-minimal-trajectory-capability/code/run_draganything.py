# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# Run with the isolated venv: <venv>/bin/python run_draganything.py /abs/config.json [--cpu-only]
# config['repo'] is the pinned DragAnything checkout (79355363); the wrapper chdirs there like demo.py.
"""C-012 CLI wrapper around the official DragAnything demo (no model/algorithm change).

Reuses demo.get_condition / pipeline exactly as demo.py __main__, with three wrapper-level changes:
1. inputs are written as the demo's own folder format (demo.jpg, mask, demo.json), one per path;
2. the DIFT entity feature is computed ONCE (fixed torch seed) on the shared first image and reused for
   A and B, so only the trajectory differs;
3. a fixed CPU generator (seed 20261028) drives the SVD latents/noise augmentation for both paths.
Official values kept: 576x320, 20 frames, motion_bucket_id 180, controlnet_cond_scale 1.0, decode_chunk 8.
First image + trajectory only: the model has no end-anchor input.
"""
from pathlib import Path
import json
import math
import sys
import time

import numpy as np
from PIL import Image

OUT_W, OUT_H, FRAMES = 576, 320, 20
SEED = 20261028


def main() -> None:
    config = json.loads(Path(sys.argv[1]).read_text())
    # The guard runs this file in-process under the research Python; put the isolated venv's pinned
    # packages (transformers 4.36.2, huggingface_hub 0.20.3, accelerate 0.25.0) first. Torch stays shared.
    sys.path.insert(0, config['isolated_site_packages'])
    for name in [m for m in sys.modules if m.split('.')[0] in ('transformers', 'huggingface_hub', 'accelerate', 'tokenizers', 'diffusers')]:
        del sys.modules[name]
    sys.path.insert(0, str(Path(config['c012_code'])))
    from render_task import path_center, W, H
    import os
    import torch
    os.chdir(config['repo'])
    sys.path.insert(0, config['repo'])
    import demo
    from pipeline.pipeline_svd_DragAnything import StableVideoDiffusionPipeline
    from models.DragAnything import DragAnythingSDVModel
    from models.unet_spatio_temporal_condition_controlnet import UNetSpatioTemporalConditionControlNetModel

    for key in ('svd', 'draganything', 'dift_model', 'task'):
        assert Path(config[key]).exists(), key
    if '--cpu-only' in sys.argv[2:]:
        print(json.dumps({'status': 'CPU_PASS', 'cuda_initialized': torch.cuda.is_initialized()}))
        return
    out = Path(config['output']); out.mkdir(parents=True, exist_ok=False)
    task = Path(config['task'])
    sx, sy = 555 / W, OUT_H / H                     # aspect kept within 0.06%; letterbox x pad 10 | 11
    pad_x = 10
    affine = {'sx': sx, 'sy': sy, 'pad_x': pad_x, 'pad_y': 0, 'resized': [555, 320], 'canvas': [OUT_W, OUT_H]}
    def to_canvas(img: Image.Image, mode) -> Image.Image:
        canvas = Image.new(mode, (OUT_W, OUT_H), 0)
        canvas.paste(img.resize((555, 320), Image.Resampling.LANCZOS if mode == 'RGB' else Image.Resampling.NEAREST), (pad_x, 0))
        return canvas
    with Image.open(task / 'anchors/start.png') as im:
        first = to_canvas(im.convert('RGB'), 'RGB')
    with Image.open(task / 'A/mask/000.png') as im:
        mask = to_canvas(im.convert('L'), 'L').convert('RGB')
    inputs = {}
    for path in ('A', 'B'):
        folder = out / 'inputs' / path; folder.mkdir(parents=True)
        first.save(folder / 'demo.jpg', quality=100)
        mask.save(folder / 'ball.png')
        traj = []
        for i in range(FRAMES):
            cx, cy = path_center(path, i / (FRAMES - 1))
            traj.append([int(round(cx * sx + pad_x)), int(round(cy * sy))])
        (folder / 'demo.json').write_text(json.dumps({'1': {'comment': 'ball', 'mask_name': 'ball.png', 'trajectory': traj}}))
        inputs[path] = traj
    assert inputs['A'][0] == inputs['B'][0] and inputs['A'][-1] == inputs['B'][-1]
    started = time.monotonic()
    # (2) DIFT entity feature: one fixed-seed extraction on the shared first image, reused for A and B.
    torch.manual_seed(SEED)
    featurizer = demo.SDFeaturizer(sd_id=config['dift_model'])
    first_for_dift = Image.open(out / 'inputs/A/demo.jpg').convert('RGB')
    cached = demo.extract_dift_feature(first_for_dift, dift_model=featurizer)
    del featurizer; torch.cuda.empty_cache()
    demo.SDFeaturizer = lambda sd_id=None: None
    demo.extract_dift_feature = lambda image, dift_model=None: cached
    dift_receipt = {'shape': list(cached.shape), 'sum': float(cached.float().sum()), 'extractions': 1}
    controlnet = DragAnythingSDVModel.from_pretrained(config['draganything'], torch_dtype=torch.float32)
    unet = UNetSpatioTemporalConditionControlNetModel.from_pretrained(config['svd'], subfolder='unet', variant='fp16', torch_dtype=torch.float32)
    pipeline = StableVideoDiffusionPipeline.from_pretrained(config['svd'], controlnet=controlnet, unet=unet,
                                                            variant='fp16', torch_dtype=torch.float32).to('cuda')
    # fp32 throughout like the official demo (fp16 files upcast); the pipeline's fp16 upcast branch touches
    # an unused self.dinov2 attribute, so mixed precision is not an official path.
    results = {}
    for path in ('A', 'B'):
        args = {'validation_image': str(out / 'inputs' / path), 'frame_number': FRAMES}
        image = Image.open(out / 'inputs' / path / 'demo.jpg').convert('RGB')
        controls, ids, vis = demo.get_condition(target_size=(OUT_H, OUT_W), original_size=(OUT_H, OUT_W), args=args,
                                                first_frame=image, side=100, model_id=config['dift_model'])
        ids = torch.stack(ids, dim=0).permute(0, 3, 1, 2)
        generator = torch.Generator(device='cpu').manual_seed(SEED)
        tick = time.monotonic()
        frames = pipeline(image, controls[:FRAMES], decode_chunk_size=8, num_frames=FRAMES, motion_bucket_id=180,
                          controlnet_cond_scale=1.0, height=OUT_H, width=OUT_W, ids_embedding=ids[:FRAMES],
                          generator=generator).frames[0]
        raw = out / f'raw_{path}'; raw.mkdir()
        conv = out / f'eval416_{path}'; conv.mkdir()
        heat = out / f'control_{path}'; heat.mkdir()
        for i, frame in enumerate(frames):
            frame.save(raw / f'{i:03d}.png')
            # derived for scoring only: inverse letterbox (crop pad, resize back) - no temporal or spatial warp to truth
            frame.crop((pad_x, 0, pad_x + 555, OUT_H)).resize((W, H), Image.Resampling.BILINEAR).save(conv / f'{i:03d}.png')
        for i, c in enumerate(controls[:FRAMES]):
            c.save(heat / f'{i:03d}.png')
        results[path] = {'frames': len(frames), 'seconds': time.monotonic() - tick,
                         'control_sum': float(np.asarray(controls[10]).sum()), 'ids_sum': float(ids.float().sum())}
    (out / 'result.json').write_text(json.dumps({'status': 'COMPLETE', 'affine': affine, 'trajectories': inputs,
        'dift': dift_receipt, 'results': results, 'seed': SEED, 'fps_conditioning': 7, 'frames': FRAMES,
        'resolution': [OUT_W, OUT_H], 'end_anchor_input': False, 'elapsed_seconds': time.monotonic() - started,
        'cuda_peak_allocated': torch.cuda.max_memory_allocated()}, indent=2))
    print(json.dumps({'status': 'COMPLETE', 'results': results}))


if __name__ == '__main__':
    main()
