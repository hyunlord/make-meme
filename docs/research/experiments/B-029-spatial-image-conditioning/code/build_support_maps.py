# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
# Run: existing-pinned-python build_support_maps.py B027_TASK_ROOT OUTDIR
"""CPU source-support construction; fixed approximations, no new segmentation."""
from pathlib import Path
from typing import TypedDict
import ast
import hashlib
import json
import math
import sys
import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import maximum_filter
import torch
from torch import Tensor
from torch.nn import functional as F
from safetensors import safe_open
from safetensors.torch import save_file
from spatial_image_gate import SOURCE_SHA256, GateMode, coefficients


class MapMetadata(TypedDict):
    bbox_xyxy: list[int]
    dilation_radius: int
    source_shape: list[int]
    token_shape: list[int]
    temporal_groups: list[list[int]]
    processing_order: str


def support_map(masks: Tensor, grid: tuple[int, int, int]) -> tuple[Tensor, MapMetadata]:
    """Map exact source support to the predeclared approximate token times."""
    assert masks.ndim == 3 and masks.shape[0] == 17 and masks.dtype == torch.bool
    assert masks.device.type == 'cpu' and grid[0] == 5
    points = masks.any(0).nonzero()
    assert len(points) > 0
    y0,x0 = points.min(0).values.tolist(); y1,x1 = (points.max(0).values+1).tolist()
    radius = math.ceil(.1*max(x1-x0,y1-y0))
    groups = [[0],list(range(1,5)),list(range(5,9)),list(range(9,13)),list(range(13,17))]
    unions = torch.stack([masks[group].any(0) for group in groups])
    dilated = maximum_filter(unions.numpy(), size=(1,2*radius+1,2*radius+1), mode='constant', cval=0)
    smoothed = F.avg_pool2d(torch.from_numpy(dilated.copy()).float().unsqueeze(1), 7, stride=1, padding=3)
    result = F.interpolate(smoothed, size=grid[1:], mode='area')[:,0].clamp(0,1).contiguous()
    return result, {'bbox_xyxy':[x0,y0,x1,y1],'dilation_radius':radius,'source_shape':list(masks.shape),
        'token_shape':list(result.shape),'temporal_groups':groups,
        'processing_order':'temporal union -> square dilation with zero outside -> 7x7 zero-padded mean -> area resize'}


def build(task: Path, output: Path) -> None:
    """Save lossless map, exact input hashes, overlap statistics and a review sheet."""
    files = sorted((task/'inputs/source-mask').glob('*.png'))
    assert [path.name for path in files] == [f'{index:03d}.png' for index in range(17)]
    cache_path = task/'cases/R1/artifacts/conditions.safetensors'
    metadata_path = cache_path.with_suffix('.json')
    producer = json.loads(metadata_path.read_text())
    with safe_open(str(cache_path), framework='pt', device='cpu') as cache:
        latent_shape = cache.get_slice('t0').get_shape()
    assert latent_shape == producer['tensors']['t0']['shape'] == [16,5,64,112]
    upstream = task/'stages/R1_S/upstream'
    model_source = upstream/'wan/modules/model_scail2.py'
    assert hashlib.sha256(model_source.read_bytes()).hexdigest() == SOURCE_SHA256
    tree = ast.parse(model_source.read_text())
    model_class = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'SCAIL2Model')
    constructor = next(node for node in model_class.body if isinstance(node, ast.FunctionDef) and node.name == '__init__')
    defaults = dict(zip([arg.arg for arg in constructor.args.args][-len(constructor.args.defaults):], constructor.args.defaults))
    default_patch = list(ast.literal_eval(defaults['patch_size']))
    config_path = upstream/'configs/config-14b.json'
    config = json.loads(config_path.read_text())
    patch_size = config.get('patch_size', default_patch)
    assert patch_size == [1,2,2]
    grid = tuple(size//patch for size,patch in zip(latent_shape[1:],patch_size))
    assert len(grid) == 3 and all(size % patch == 0 for size,patch in zip(latent_shape[1:],patch_size))
    masks = []
    hashes = {}
    for path in files:
        with Image.open(path) as image:
            rgb = np.array(image.convert('RGB'))
        assert rgb.shape == (512,896,3)
        red = (rgb == [255,0,0]).all(-1)
        assert bool(red.any()) and bool(((rgb == [255,255,255]).all(-1) | red).all())
        masks.append(torch.from_numpy(red))
        hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    source = torch.stack(masks)
    support, metadata = support_map(source, grid)
    shift_hw = [grid[1]//2, grid[2]//2]
    shifted = torch.roll(support, shift_hw, (1,2))
    method = coefficients(support, GateMode.METHOD, .5)
    control = coefficients(support, GateMode.CONTROL, .5)
    assert torch.equal(method.flatten(1).sort().values, control.flatten(1).sort().values)
    overlap = (torch.minimum(support,shifted).sum((1,2)) / torch.maximum(support,shifted).sum((1,2))).tolist()
    output.mkdir(parents=True, exist_ok=False)
    save_file({'E':support}, str(output/'support.safetensors'))
    sheet = Image.new('RGB',(896,5*174),(24,24,24)); draw=ImageDraw.Draw(sheet)
    for index, group in enumerate(metadata['temporal_groups']):
        union = source[group].any(0).numpy().astype(np.uint8)*255
        panels = [Image.fromarray(union).convert('RGB'), Image.fromarray((support[index].numpy()*255).astype(np.uint8)).convert('RGB'), Image.fromarray((shifted[index].numpy()*255).astype(np.uint8)).convert('RGB')]
        for column, panel in enumerate(panels):
            sheet.paste(panel.resize((280,160),Image.Resampling.NEAREST),(column*298,index*174+14))
        draw.text((2,index*174),f't{index} source frames {group}: union | METHOD E | CONTROL E',fill='white')
    sheet.save(output/'support-review.png')
    report = {**metadata,'source_mask_sha256':hashes,'lambda':.5,'control_shift_hw':shift_hw,
        'initial_noise_shape':latent_shape,'patch_size':patch_size,'patch_size_origin':'config override or pinned constructor default',
        'model_source_sha256':SOURCE_SHA256,'config_sha256':hashlib.sha256(config_path.read_bytes()).hexdigest(),
        'condition_metadata_sha256':hashlib.sha256(metadata_path.read_bytes()).hexdigest(),
        'condition_file_sha256':hashlib.sha256(cache_path.read_bytes()).hexdigest(),
        'soft_minmax_iou_per_time':overlap,'mean_E_per_time':support.mean((1,2)).tolist(),
        'method_gate_mean_per_time':method.mean((1,2)).tolist(),'gate_range':[float(method.min()),float(method.max())],
        'method_control_histogram_equal':True,'method_control_identical':bool(torch.equal(method,control)),
        'support_file_sha256':hashlib.sha256((output/'support.safetensors').read_bytes()).hexdigest(),
        'interpretation':'Explicit temporal approximation, not VAE receptive-field identity or edited alpha. Fixed overlap is reported without shift search.'}
    (output/'support.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))


if __name__ == '__main__':
    build(Path(sys.argv[1]), Path(sys.argv[2]))
