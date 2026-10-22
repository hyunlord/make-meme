# /// script
# requires-python = ">=3.12"
# dependencies = ["torch", "safetensors", "pydantic>=2"]
# ///
# How to run: imported by converter.py; no model downloads.
"""Load only the SHA-verified official mapping and CPU checkpoint tensors."""
from __future__ import annotations

import hashlib
import importlib.util
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import torch
from pydantic import ConfigDict, TypeAdapter
from torch._subclasses.fake_tensor import FakeTensorMode

OFFICIAL_SHA: Final = "0519f688643b0a2c3f13660f196e34280704ddb3e2575aa226e2d2f8f2b4397f"
TENSORS: Final = TypeAdapter(dict[str, torch.Tensor], config=ConfigDict(arbitrary_types_allowed=True))


class ConversionError(RuntimeError):
    """Conversion contract rejected; never fall back to unsafe loading."""


@dataclass(frozen=True, slots=True)
class MappingSource:
    path: Path

    def load(self) -> Callable[[str, torch.Tensor], Mapping[str, torch.Tensor]]:
        """Import a known official file, not checkpoint-supplied code."""
        if hashlib.sha256(self.path.read_bytes()).hexdigest() != OFFICIAL_SHA:
            raise ConversionError("Official converter source SHA mismatch")
        spec = importlib.util.spec_from_file_location("scail_verified_mapping", self.path)
        if spec is None or spec.loader is None:
            raise ConversionError("Official converter module cannot be loaded")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.get_new_mappings


def checkpoint_tensors(path: Path, *, metadata: bool) -> Mapping[str, torch.Tensor]:
    """Restrict unpickling and mapping to CPU; fail closed on unsupported formats."""
    unsafe = torch.serialization.get_unsafe_globals_in_checkpoint(path)
    if unsafe:
        raise ConversionError(f"Checkpoint requires unsupported globals: {unsafe}")
    if metadata:
        with FakeTensorMode():
            checkpoint = torch.load(path, map_location="cpu", weights_only=True, mmap=True)
    else:
        checkpoint = torch.load(path, map_location="cpu", weights_only=True, mmap=True)
    # Only this tensor dictionary crosses the checkpoint trust boundary.
    return TENSORS.validate_python(checkpoint["module"], strict=True)


def mapped_tensors(state: Mapping[str, torch.Tensor], source: MappingSource) -> Mapping[str, torch.Tensor]:
    """Preserve official names, split order, dtype and storage views."""
    mapper = source.load()
    mapped: dict[str, torch.Tensor] = {}
    for name, tensor in state.items():
        for target, value in mapper(name, tensor).items():
            if target in mapped:
                raise ConversionError(f"Duplicate mapped name: {target}")
            mapped[target] = value
    return mapped
