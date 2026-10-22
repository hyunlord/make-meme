# /// script
# requires-python = ">=3.12"
# dependencies = ["torch", "safetensors"]
# ///
"""Tensorwise meta loading with explicit mixed-BF16 policy; original weights preserved."""
# Run through isolated SCAIL constructor; see runtime_prepare.py.
from pathlib import Path
import json
import os
import time
import torch
from safetensors import safe_open


def parameter_dtype(name: str) -> torch.dtype:
    """Keep explicit FP32 arithmetic islands and normalization/modulation parameters."""
    fp32 = name.startswith(('time_embedding.', 'time_projection.', 'head.')) or name.startswith(('img_emb.proj.0.', 'img_emb.proj.4.')) or 'norm' in name or 'modulation' in name
    return torch.float32 if fp32 else torch.bfloat16


def load_model(config_path: str, checkpoint_path: str) -> torch.nn.Module:
    from wan.modules.model_scail2 import SCAIL2Model, rope_params
    started = time.monotonic()
    with torch.device('meta'):
        model = SCAIL2Model.from_config(config_path)
    expected = model.state_dict()
    records = []
    with safe_open(checkpoint_path, framework='pt', device='cpu') as checkpoint:
        assert set(checkpoint.keys()) == set(expected), 'Checkpoint/model keys differ'
        for name in checkpoint.keys():
            tensor = checkpoint.get_tensor(name)
            assert tensor.shape == expected[name].shape, name
            dtype = parameter_dtype(name)
            loaded = tensor.to(dtype=dtype, device='cpu')
            parent, _, leaf = name.rpartition('.')
            module = model.get_submodule(parent) if parent else model
            assert leaf in module._parameters, 'Unexpected buffer requires explicit policy'
            module.register_parameter(leaf, torch.nn.Parameter(loaded, requires_grad=False))
            records.append({'name':name,'shape':list(tensor.shape),'source_dtype':str(tensor.dtype),'loaded_dtype':str(dtype),'numel':tensor.numel(),'loaded_bytes':loaded.numel()*loaded.element_size()})
            del tensor, loaded
    d = model.hidden_size_head
    model.freqs = torch.cat([rope_params(8192,d-4*(d//6)),rope_params(8192,2*(d//6)),rope_params(8192,2*(d//6))],dim=1)
    assert all(not p.is_meta for p in model.parameters()) and not model.freqs.is_meta
    report = {'policy':'mixed BF16 with FP32 time/head/norm/modulation islands; not official FP32 equivalence','seconds':time.monotonic()-started,'parameter_count':sum(p.numel() for p in model.parameters()),'parameter_bytes':sum(p.numel()*p.element_size() for p in model.parameters()),'freqs_shape':list(model.freqs.shape),'freqs_dtype':str(model.freqs.dtype),'tensors':records}
    Path(os.environ['B007B_LOADER_REPORT']).write_text(json.dumps(report,indent=2))
    return model.eval().requires_grad_(False)
