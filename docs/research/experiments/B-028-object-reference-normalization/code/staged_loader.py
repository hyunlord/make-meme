"""CPU meta-init staged loader for pinned SCAIL; no device transfer or forward.

load_model(config_path, checkpoint_path) integrates with the isolated pipeline.
B007E_LOADER_REPORT must name a private report. Optional phase_hook receives
phase names only; caller owns OS/GPU guards and artifact SHA verification.
"""
from __future__ import annotations

import json
import os
import time
from collections.abc import Callable
from pathlib import Path
from typing import TypedDict

import torch
from safetensors import safe_open
from torch import nn


class LoaderError(RuntimeError):
    """Fail closed on unsupported architecture/layout, never retry automatically."""


class TensorRecord(TypedDict):
    name: str
    shape: list[int]
    source_dtype: str
    loaded_dtype: str
    numel: int
    loaded_bytes: int


class AssignmentResult(TypedDict):
    missing_keys: list[str]
    unexpected_keys: list[str]
    strict: bool
    assign: bool


def parameter_dtype(name: str) -> torch.dtype:
    """Pinned official FP32 islands include image MLP LayerNorms by exact path."""
    fp32 = (name.startswith(("time_embedding.", "time_projection.", "head.",
                            "img_emb.proj.0.", "img_emb.proj.4."))
            or "norm" in name or "modulation" in name)
    return torch.float32 if fp32 else torch.bfloat16


def assert_no_meta(model: nn.Module) -> None:
    """Catch registered/nonpersistent buffers and direct unregistered tensors."""
    for module_name, module in model.named_modules():
        for name, value in vars(module).items():
            if isinstance(value, torch.Tensor) and value.is_meta:
                raise LoaderError(f"Unmaterialized attribute: {module_name}.{name}")
        for name, value in module.named_parameters(recurse=False):
            if value.is_meta:
                raise LoaderError(f"Unmaterialized parameter: {module_name}.{name}")
        for name, value in module.named_buffers(recurse=False):
            if value.is_meta:
                raise LoaderError(f"Unmaterialized buffer: {module_name}.{name}")


def assign_checkpoint(model: nn.Module, checkpoint_path: Path,
                      dtype_policy: Callable[[str], torch.dtype] = parameter_dtype) -> tuple[list[TensorRecord], AssignmentResult]:
    """Validate complete key/shape schema before replacing any meta parameter.

    Only parameter-only SCAIL state is supported. Persistent and nonpersistent
    buffers reject explicitly; no silently uninitialized buffers or tied params.
    One source tensor and its cast are live at a time besides accumulated model.
    FP32 passthrough aliases mmap pages; virtual/page-cache residency is not capped
    by this function and must be guarded externally.
    """
    if list(model.named_buffers()):
        raise LoaderError("Registered buffers require an explicit materialization policy")
    parameters = dict(model.named_parameters(remove_duplicate=False))
    if len({id(value) for value in parameters.values()}) != len(parameters):
        raise LoaderError("Tied parameters need explicit alias policy")
    if any(not value.is_meta for value in parameters.values()):
        raise LoaderError("Architecture must start on meta device")
    expected = model.state_dict()
    records: list[TensorRecord] = []
    cast_state: dict[str, torch.Tensor] = {}
    with safe_open(checkpoint_path, framework="pt", device="cpu") as checkpoint:
        if set(checkpoint.keys()) != set(expected) or set(expected) != set(parameters):
            raise LoaderError("Missing/unexpected checkpoint or nonparameter state keys")
        for name in checkpoint.keys():
            view = checkpoint.get_slice(name)
            if tuple(view.get_shape()) != tuple(expected[name].shape) or view.get_dtype() != "F32":
                raise LoaderError(f"Checkpoint shape/source dtype mismatch: {name}")
        for name in checkpoint.keys():
            tensor = checkpoint.get_tensor(name)
            dtype = dtype_policy(name)
            if dtype not in (torch.float32, torch.bfloat16):
                raise LoaderError("Only declared FP32/BF16 policy allowed")
            loaded = tensor.to(dtype=dtype, device="cpu")
            cast_state[name] = loaded
            records.append({"name": name, "shape": list(tensor.shape), "source_dtype": str(tensor.dtype),
                            "loaded_dtype": str(dtype), "numel": tensor.numel(),
                            "loaded_bytes": loaded.numel()*loaded.element_size()})
            del tensor, loaded
    incompatible = model.load_state_dict(cast_state, strict=True, assign=True)
    if incompatible.missing_keys or incompatible.unexpected_keys:
        raise LoaderError("Strict assignment returned incompatible keys")
    model.requires_grad_(False)
    # The model and cast_state reference the same assigned payload; no extra copy.
    assignment: AssignmentResult = {"missing_keys": list(incompatible.missing_keys),
                                     "unexpected_keys": list(incompatible.unexpected_keys),
                                     "strict": True, "assign": True}
    del cast_state
    return records, assignment


def load_model(config_path: str, checkpoint_path: str,
               phase_hook: Callable[[str], None] | None = None) -> nn.Module:
    """Construct exact official architecture on meta; restore official RoPE CPU."""
    from wan.modules.model_scail2 import SCAIL2Model, rope_params
    started = time.monotonic()
    if phase_hook:
        phase_hook("dit_meta_init_start")
    with torch.device("meta"):
        model = SCAIL2Model.from_config(config_path)
    if phase_hook:
        phase_hook("dit_meta_init_done")
    records, assignment = assign_checkpoint(model, Path(checkpoint_path))
    if phase_hook:
        phase_hook("dit_staged_weights_done")
    # freqs is intentionally unregistered in pinned upstream; never BF16-cast it.
    d = model.hidden_size_head
    model.freqs = torch.cat([rope_params(8192, d-4*(d//6)), rope_params(8192, 2*(d//6)),
                             rope_params(8192, 2*(d//6))], dim=1)
    assert_no_meta(model)
    if model.freqs.dtype != torch.complex128:
        raise LoaderError("Official RoPE dtype changed")
    report = {"scope": "LOAD_ONLY_NOT_FORWARD_OR_QUALITY", "seconds": time.monotonic()-started,
              "policy": "mixed BF16, FP32 time/head/norm/modulation; lossy versus checkpoint FP32",
              "parameter_count": sum(p.numel() for p in model.parameters()),
              "parameter_bytes": sum(p.numel()*p.element_size() for p in model.parameters()),
              "freqs_shape": list(model.freqs.shape), "freqs_dtype": str(model.freqs.dtype),
              "registered_buffers": len(list(model.buffers())), "tensors": records,
              "load_state_dict_result": assignment}
    destination = Path(os.environ["B007E_LOADER_REPORT"])
    with destination.open("x") as handle:
        json.dump(report, handle, indent=2)
    if phase_hook:
        phase_hook("dit_loader_complete_cpu")
    return model.eval().requires_grad_(False)
