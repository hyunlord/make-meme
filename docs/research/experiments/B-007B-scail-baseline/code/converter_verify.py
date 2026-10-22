# /// script
# requires-python = ">=3.12"
# dependencies = ["torch", "safetensors", "pydantic>=2", "numpy"]
# ///
# How to run: python converter_verify.py CHECKPOINT PINNED_CONVERT OUTPUT.safetensors
"""Independently read safetensors metadata and chunk-hash output against source."""
from __future__ import annotations

import hashlib
import json
import struct
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Final

import torch
from converter_mapping import ConversionError, MappingSource, checkpoint_tensors, mapped_tensors
from converter_stream import CHUNK_BYTES, tensor_header
from pydantic import BaseModel, ConfigDict, TypeAdapter
from safetensors import safe_open


class HeaderEntry(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    dtype: str
    shape: tuple[int, ...]
    data_offsets: tuple[int, int]


HEADERS: Final = TypeAdapter(dict[str, HeaderEntry])


@dataclass(frozen=True, slots=True)
class Verification:
    status: str
    tensor_count: int
    tensor_bytes: int
    hashes: dict[str, str]


def verify(checkpoint: Path, source: Path, output: Path) -> Verification:
    """No load_file/full-output allocation; source pages remain CPU mmap backed."""
    mapping = MappingSource(source)
    metadata = mapped_tensors(checkpoint_tensors(checkpoint, metadata=True), mapping)
    # Official Rust parser independently checks safetensors structural validity.
    with safe_open(output, framework="pt", device="cpu") as reader:
        if set(reader.keys()) != set(metadata):
            raise ConversionError("Output keys differ from official mapping")
        for name, tensor in metadata.items():
            value = reader.get_slice(name)
            expected = tensor_header(tensor, 0)
            if value.get_shape() != expected["shape"] or value.get_dtype() != expected["dtype"]:
                raise ConversionError(f"Output dtype/shape mismatch: {name}")
    del metadata
    state = checkpoint_tensors(checkpoint, metadata=False)
    mapper = mapping.load()
    hashes: dict[str, str] = {}
    total = 0
    with output.open("rb") as handle:
        size_bytes = handle.read(8)
        if len(size_bytes) != 8:
            raise ConversionError("Truncated safetensors header length")
        header_length = struct.unpack("<Q", size_bytes)[0]
        if header_length >= 100_000_000:
            raise ConversionError("Header exceeds bounded format limit")
        headers = HEADERS.validate_json(handle.read(header_length))
        data_start = 8 + header_length
        for original_name, original_tensor in state.items():
            for name, tensor in mapper(original_name, original_tensor).items():
                entry = headers[name]
                expected = tensor_header(tensor, 0)
                raw = memoryview(tensor.detach().reshape(-1).view(torch.uint8).numpy())
                length = entry.data_offsets[1] - entry.data_offsets[0]
                if length != raw.nbytes or length != expected["data_offsets"][1]:
                    raise ConversionError(f"Tensor byte length mismatch: {name}")
                handle.seek(data_start + entry.data_offsets[0])
                source_hash, output_hash = hashlib.sha256(), hashlib.sha256()
                for start in range(0, length, CHUNK_BYTES):
                    source_block = raw[start:start + CHUNK_BYTES]
                    output_block = handle.read(len(source_block))
                    source_hash.update(source_block)
                    output_hash.update(output_block)
                    if len(output_block) != len(source_block):
                        raise ConversionError(f"Truncated tensor bytes: {name}")
                if source_hash.digest() != output_hash.digest():
                    raise ConversionError(f"Tensor payload hash mismatch: {name}")
                hashes[name] = output_hash.hexdigest()
                total += length
    return Verification("VERIFIED_AGAINST_OFFICIAL_MAPPING_AND_SOURCE", len(hashes), total, hashes)


if __name__ == "__main__":
    if len(sys.argv) != 4:
        raise SystemExit("Usage: converter_verify.py CHECKPOINT PINNED_CONVERT OUTPUT.safetensors")
    result = verify(*(Path(value) for value in sys.argv[1:]))
    destination = Path(sys.argv[3] + ".verification.json")
    destination.write_text(json.dumps(asdict(result), indent=2) + "\n")
