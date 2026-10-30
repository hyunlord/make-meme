# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""C006 local frozen runtime and atomic evidence; use existing research Python."""
from pathlib import Path
import hashlib
import json
import os
import sys
from typing import Literal
from pydantic import BaseModel, ConfigDict
import torch
from torch import Tensor


class RuntimeConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra='forbid')
    upstream: Path
    weights: Path
    tokenizer: Path
    data_root: Path
    split_manifest: Path
    tracks_root: Path
    cache_root: Path
    output: Path
    phase: Literal['cache', 'train', 'generate']
    clip_id: str | None = None
    mode: Literal['BASE', 'ON', 'NULL'] = 'BASE'
    adapter_checkpoint: Path | None = None
    seed: int = 20261028
    train_seed: int = 20261030
    max_updates: int = 256
    train_seconds: int = 9000
    deadline_epoch: float


def atomic_json(path: Path, value) -> None:
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2))
    temporary.replace(path)


def tensor_summary(value: Tensor) -> dict:
    cpu = value.detach().cpu().contiguous()
    return {'shape': list(cpu.shape), 'dtype': str(cpu.dtype),
            'sha256': hashlib.sha256(cpu.view(torch.uint8).numpy().tobytes()).hexdigest(),
            'finite': bool(torch.isfinite(cpu).all())}


def atomic_torch(path: Path, value) -> None:
    """Safe tensor/primitive-only pickle container, restricted readback by caller."""
    temporary = path.with_suffix('.tmp')
    torch.save(value, temporary)
    temporary.replace(path)


def setup(config: RuntimeConfig) -> None:
    assert all(path.is_absolute() for path in (config.upstream, config.weights,
               config.tokenizer, config.data_root, config.cache_root, config.output))
    os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', TOKENIZERS_PARALLELISM='false')
    sys.path.insert(0, str(config.upstream))
    from diffsynth.models import wan_video_dit
    wan_video_dit.FLASH_ATTN_3_AVAILABLE = False
    wan_video_dit.FLASH_ATTN_2_AVAILABLE = False
    wan_video_dit.SAGE_ATTN_AVAILABLE = False


def load_pipeline(config: RuntimeConfig):
    from diffsynth.pipelines.wan_video import WanVideoPipeline, ModelConfig
    paths = []
    if config.phase != 'cache':
        paths.append(str(config.weights / 'diffusion_pytorch_model.safetensors'))
    if config.phase != 'train':
        paths.extend([str(config.weights / 'models_t5_umt5-xxl-enc-bf16.pth'),
                      str(config.weights / 'Wan2.1_VAE.pth')])
    pipe = WanVideoPipeline.from_pretrained(
        torch_dtype=torch.bfloat16, device='cuda',
        model_configs=[ModelConfig(path=path, skip_download=True) for path in paths],
        tokenizer_config=ModelConfig(path=str(config.tokenizer), skip_download=True))
    for name in ('dit', 'vace', 'text_encoder', 'vae'):
        module = getattr(pipe, name, None)
        if module is not None:
            module.eval().requires_grad_(False)
    return pipe


def parse_config() -> RuntimeConfig:
    path = Path(sys.argv[1])
    assert path.is_absolute()
    return RuntimeConfig.model_validate_json(path.read_text())
