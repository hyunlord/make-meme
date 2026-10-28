# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# Run with existing research Python: video_generate.py /absolute/config.json [--cpu-only]
"""C-002: frozen endpoint/layout conditioning and existing VACE inference, no downloads."""
from pathlib import Path
import ast
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from typing import TYPE_CHECKING, Literal, TypedDict, assert_never

if TYPE_CHECKING:
    import torch
import numpy as np
from PIL import Image
from pydantic import BaseModel, ConfigDict


class Config(BaseModel):
    model_config = ConfigDict(frozen=True, extra='forbid')
    upstream: Path
    weights: Path
    tokenizer: Path
    helper: Path
    helper_sha256: str
    start_anchor: Path
    end_anchor: Path
    output: Path
    prompt: str
    condition_mode: Literal["endpoint", "layout_mov", "layout_still"] = "endpoint"
    layout_dir: Path | None = None
    negative_prompt: str = 'blurry, distorted, deformed, watermark'
    width: Literal[832] = 832
    height: Literal[480] = 480
    frames: Literal[33] = 33
    seed: Literal[20261028] = 20261028
    steps: Literal[50] = 50
    guidance: Literal[5.0] = 5.0
    sigma_shift: Literal[5.0] = 5.0
    fps: Literal[16] = 16


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def atomic_json(path: Path, value) -> None:
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2))
    temporary.replace(path)


def condition(config: Config) -> tuple[list[Image.Image], list[Image.Image], dict]:
    """Run pinned official helper class with same-size alignment and retain its exact outputs."""
    for path in (config.upstream, config.weights, config.tokenizer, config.helper,
                 config.start_anchor, config.end_anchor, config.output):
        assert path.is_absolute(), f'Absolute path required: {path}'
    for path in (config.upstream, config.weights, config.tokenizer, config.helper,
                 config.start_anchor, config.end_anchor):
        assert path.exists(), f'Missing: {path}'
    assert digest(config.helper.read_bytes()) == config.helper_sha256
    anchors = []
    for path in (config.start_anchor, config.end_anchor):
        with Image.open(path) as image:
            assert image.size == (config.width, config.height), 'Common spatial preprocessing required'
            anchors.append(np.array(image.convert('RGB')))
    tree = ast.parse(config.helper.read_text())
    selected = [node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'FrameRefExpandAnnotator']
    assert len(selected) == 1
    def same_size(first, second):
        assert first.shape == second.shape
        return second
    namespace = {'np': np, 'align_frames': same_size}
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(config.helper), 'exec'), namespace)
    helper = namespace['FrameRefExpandAnnotator']({'MODE': 'firstlastframe'})
    result = helper.forward(image=anchors[0], image_2=anchors[1], expand_num=31)
    frames = [Image.fromarray(np.asarray(frame, dtype=np.uint8)) for frame in result['frames']]
    masks = [Image.fromarray(np.asarray(mask, dtype=np.uint8)).convert('RGB') for mask in result['masks']]
    assert len(frames) == len(masks) == 33
    assert frames[0].tobytes() == anchors[0].tobytes() and frames[-1].tobytes() == anchors[-1].tobytes()
    match config.condition_mode:
        case 'endpoint':
            assert config.layout_dir is None, 'Endpoint must not consume layout'
            assert all(frame.getextrema() == ((127,127),)*3 for frame in frames[1:-1])
        case 'layout_mov' | 'layout_still':
            assert config.layout_dir is not None and config.layout_dir.is_absolute()
            layouts = []
            for i in range(33):
                with Image.open(config.layout_dir/f'{i:03d}.png') as image:
                    assert image.mode == 'RGB' and image.size == (832,480)
                    pixels = np.asarray(image)
                    assert pixels.dtype == np.uint8 and np.isin(pixels, [0,255]).all()
                    assert np.array_equal(pixels[:,:,0],pixels[:,:,1]) and np.array_equal(pixels[:,:,1],pixels[:,:,2])
                    assert (pixels == 0).any() and (pixels == 255).any(), 'Empty or filled layout'
                    layouts.append(image.copy())
            for i in range(1,32):
                index = i if config.condition_mode == 'layout_mov' else 0
                frames[i] = layouts[index].copy()
                assert frames[i].tobytes() == layouts[index].tobytes()
        case unreachable:
            assert_never(unreachable)
    assert all(mask.getextrema() == (((0,0),)*3 if i in (0,32) else ((255,255),)*3) for i,mask in enumerate(masks))
    receipt = {'frames':33,'endpoint_positions':[0,32],'expand_num':31,'helper_sha256':config.helper_sha256,
               'condition_mode':config.condition_mode,'missing_rgb_uint8':127 if config.condition_mode=='endpoint' else None,'known_mask':0,'generate_mask':255,'reference_images':None,
               'rgb_pixel_sha256':[digest(f.tobytes()) for f in frames],
               'mask_pixel_sha256':[digest(f.tobytes()) for f in masks],
               'same_size_alignment':'identity; original helper align_frames is identity at equal dimensions'}
    return frames,masks,receipt


class TensorSummary(TypedDict):
    shape: list[int]
    dtype: str
    sha256: str
    finite: bool
    minimum: float
    maximum: float


def tensor_summary(tensor: "torch.Tensor") -> TensorSummary:
    """Read exact contiguous logical bytes without converting BF16 or advancing RNG."""
    import torch
    cpu = tensor.detach().to(device='cpu').contiguous()
    return {'shape':list(cpu.shape), 'dtype':str(cpu.dtype),
            'sha256':digest(cpu.view(torch.uint8).numpy().tobytes()),
            'finite':bool(torch.isfinite(cpu).all()),
            'minimum':float(cpu.min()), 'maximum':float(cpu.max())}


def main() -> None:
    config_path=Path(sys.argv[1]);assert config_path.is_absolute()
    config=Config.model_validate_json(config_path.read_text())
    frames,masks,receipt=condition(config)
    os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1'
    os.environ['TOKENIZERS_PARALLELISM']='false'
    sys.path.insert(0,str(config.upstream))
    import torch
    from diffsynth.pipelines.wan_video import WanVideoPipeline, ModelConfig
    from diffsynth.models import wan_video_dit
    assert shutil.which('ffmpeg') and shutil.which('ffprobe')
    mask_tensor=torch.stack([torch.from_numpy(np.array(m)[:,:,0].copy()) for m in masks]).float()/255
    compressed=torch.nn.functional.interpolate(mask_tensor[None,None],size=(9,480,832),mode='nearest-exact')
    receipt['actual_temporal_mask_means_33']=mask_tensor.mean((1,2)).tolist()
    receipt['actual_temporal_mask_means_9']=compressed.mean((0,1,3,4)).tolist()
    receipt['endpoint_mask_downsampling_limitation']='Official nearest-exact33to9 omits endpoint mask zeros; RGB still enters inactive VAE.'
    checkpoints=sorted(config.weights.glob('diffusion_pytorch_model*.safetensors'))
    assert checkpoints
    paths=[list(map(str,checkpoints)),str(config.weights/'models_t5_umt5-xxl-enc-bf16.pth'),str(config.weights/'Wan2.1_VAE.pth')]
    assert all(Path(p).is_file() for p in paths[1:])
    if '--cpu-only' in sys.argv[2:]:
        print(json.dumps({'status':'CPU_ENTRY_PASS','cuda_initialized':torch.cuda.is_initialized(),'condition':receipt}))
        return
    config.output.mkdir(parents=True,exist_ok=False)
    started=time.monotonic()
    atomic_json(config.output/'config.json',config.model_dump(mode='json'))
    atomic_json(config.output/'condition.json',receipt)
    for name,items in (('condition',frames),('mask',masks)):
        folder=config.output/name;folder.mkdir()
        for i,item in enumerate(items):item.save(folder/f'{i:03d}.png')
    wan_video_dit.FLASH_ATTN_3_AVAILABLE=False
    wan_video_dit.FLASH_ATTN_2_AVAILABLE=False
    wan_video_dit.SAGE_ATTN_AVAILABLE=False
    atomic_json(config.output/'model-load-attempt.json',{'started':time.time(),'attempt':1})
    pipe=WanVideoPipeline.from_pretrained(torch_dtype=torch.bfloat16,device='cuda',
        model_configs=[ModelConfig(path=p,skip_download=True) for p in paths],
        tokenizer_config=ModelConfig(path=str(config.tokenizer),skip_download=True))
    counts={'model_fn_calls':0,'scheduler_steps':0}
    original_model=pipe.model_fn
    def counted_model(*args,**kwargs):
        if counts['model_fn_calls'] == 0:
            context = kwargs['vace_context']
            assert tuple(context.shape) == (1,96,9,60,104)
            mask_context = context[:,32:]
            observation = {'latents':tensor_summary(kwargs['latents']),
                           'vace_context':tensor_summary(context),
                           'vace_mask_context':tensor_summary(mask_context),
                           'vace_mask_temporal_means':mask_context.detach().float().mean((0,1,3,4)).cpu().tolist(),
                           'vace_scale':kwargs['vace_scale'], 'condition_mode':config.condition_mode,
                           'observed_before_original_call':True, 'additional_forward_calls':0}
            atomic_json(config.output/'first-model-input.json',observation)
            assert observation['latents']['finite'] and observation['vace_context']['finite']
        counts['model_fn_calls']+=1
        atomic_json(config.output/'progress.json',counts)
        return original_model(*args,**kwargs)
    pipe.model_fn=counted_model
    original_step=pipe.scheduler.step
    def counted_step(*args,**kwargs):
        result=original_step(*args,**kwargs);counts['scheduler_steps']+=1
        atomic_json(config.output/'progress.json',counts)
        if counts['scheduler_steps']==50:
            cpu=result.detach().cpu();temporary=config.output/'final_latent.tmp'
            torch.save(cpu,temporary);temporary.replace(config.output/'final_latent.pt')
            restored=torch.load(config.output/'final_latent.pt',map_location='cpu',weights_only=True)
            assert torch.equal(cpu,restored)
            atomic_json(config.output/'latent.json',{'shape':list(cpu.shape),'dtype':str(cpu.dtype),'readback_exact':True})
        return result
    pipe.scheduler.step=counted_step
    atomic_json(config.output/'sampler-attempt.json',{'started':time.time(),'attempt':1})
    raw=pipe(prompt=config.prompt,negative_prompt=config.negative_prompt,
        vace_video=frames,vace_video_mask=masks,vace_reference_image=None,
        height=480,width=832,num_frames=33,seed=config.seed,rand_device='cpu',tiled=True,
        cfg_scale=5,num_inference_steps=50,sigma_shift=5,output_type='floatpoint')
    assert counts['scheduler_steps']==50 and torch.isfinite(raw).all()
    torch.save(raw.detach().cpu(),config.output/'raw_output.pt')
    video=pipe.vae_output_to_video(raw);assert len(video)==33
    folder=config.output/'frames';folder.mkdir()
    for i,frame in enumerate(video):
        assert frame.size==(832,480);frame.save(folder/f'{i:03d}.png')
    subprocess.run(['ffmpeg','-v','error','-n','-framerate','16','-i',str(folder/'%03d.png'),'-c:v','libx264','-crf','18','-pix_fmt','yuv420p',str(config.output/'generated.mp4')],check=True)
    subprocess.run(['ffmpeg','-v','error','-i',str(config.output/'generated.mp4'),'-f','null','-'],check=True)
    atomic_json(config.output/'result.json',{'status':'COMPLETE','elapsed_seconds':time.monotonic()-started,
        **counts,'frames':33,'fps':16,'file_duration_seconds':33/16,'endpoint_interval_seconds':32/16,
        'endpoint_overwrite':False,'sam_conditioning':config.condition_mode!='endpoint','condition_mode':config.condition_mode,'source_middle_rgb_conditioning':False})


if __name__=='__main__':
    main()
