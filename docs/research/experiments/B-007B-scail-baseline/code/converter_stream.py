# /// script
# requires-python = ">=3.12"
# dependencies = ["torch", "numpy"]
# ///
# How to run: imported by converter.py; writes one safetensors file.
"""Serialize contiguous CPU tensors without full-checkpoint byte buffers."""
from __future__ import annotations

import hashlib
import json
import os
import struct
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Final, TypedDict

import torch

from converter_mapping import ConversionError

CHUNK_BYTES: Final = 8 * 1024 * 1024
DTYPES: Final = {torch.float64: "F64", torch.float32: "F32", torch.float16: "F16",
                torch.bfloat16: "BF16", torch.int64: "I64", torch.int32: "I32",
                torch.int16: "I16", torch.int8: "I8", torch.uint8: "U8", torch.bool: "BOOL"}


class TensorHeader(TypedDict):
    dtype: str
    shape: list[int]
    data_offsets: list[int]


class TensorEvidence(TypedDict):
    dtype: str
    shape: list[int]
    bytes: int
    sha256: str
    contiguous: bool


@dataclass(frozen=True, slots=True)
class StreamResult:
    tensor_bytes: int
    tensors: Mapping[str, TensorEvidence]


def tensor_header(tensor: torch.Tensor, offset: int) -> TensorHeader:
    """Check layout without touching values, including FakeTensor metadata."""
    if tensor.layout != torch.strided or not tensor.is_contiguous():
        raise ConversionError("Only contiguous strided tensors are supported")
    if tensor.dtype not in DTYPES or tensor.is_conj() or tensor.is_neg():
        raise ConversionError("Unsupported dtype or unresolved tensor view")
    length = tensor.numel() * tensor.element_size()
    return {"dtype": DTYPES[tensor.dtype], "shape": list(tensor.shape),
            "data_offsets": [offset, offset + length]}


def stream_safetensors(state: Mapping[str, torch.Tensor], output: Path) -> StreamResult:
    """Write little-endian safetensors; preserve partial output on interruption."""
    if sys.byteorder != "little":
        raise ConversionError("This converter requires little-endian CPU")
    if output.exists():
        raise ConversionError("Output already exists; originals are never overwritten")
    header: dict[str, TensorHeader] = {}
    offset = 0
    for name in sorted(state):
        if name == "__metadata__":
            raise ConversionError("Reserved safetensors tensor name")
        tensor = state[name]
        if tensor.device.type != "cpu":
            raise ConversionError("Only CPU storage is permitted")
        header[name] = tensor_header(tensor, offset)
        offset = header[name]["data_offsets"][1]
    encoded = json.dumps(header, separators=(",", ":"), ensure_ascii=False).encode()
    encoded += b" " * (-len(encoded) % 8)
    if len(encoded) >= 100_000_000:
        raise ConversionError("Safetensors header exceeds format limit")
    partial = output.with_name(output.name + ".partial")
    evidence: dict[str, TensorEvidence] = {}
    with partial.open("xb", buffering=0) as handle:
        handle.write(struct.pack("<Q", len(encoded)))
        handle.write(encoded)
        for name in sorted(state):
            tensor = state[name].detach()
            # Reshape before dtype-view supports scalar tensors. No clone or cast.
            array = tensor.reshape(-1).view(torch.uint8).numpy()
            raw = memoryview(array)
            digest = hashlib.sha256()
            for start in range(0, raw.nbytes, CHUNK_BYTES):
                block = raw[start:start + CHUNK_BYTES]
                written = handle.write(block)
                if written != len(block):
                    raise ConversionError("Short write; partial file retained")
                digest.update(block)
            evidence[name] = {"dtype": header[name]["dtype"], "shape": header[name]["shape"],
                              "bytes": raw.nbytes, "sha256": digest.hexdigest(), "contiguous": True}
        os.fsync(handle.fileno())
    # Atomic no-overwrite publication on the same filesystem.
    os.link(partial, output)
    partial.unlink()
    return StreamResult(offset, evidence)
