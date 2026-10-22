"""Independent output-byte parity against retained mmap state; never torch.load."""
from __future__ import annotations

import hashlib
import json
import struct
from collections.abc import Mapping
from pathlib import Path

import torch
from safetensors import safe_open

CHUNK_BYTES = 8 * 1024 * 1024


def verify_output(state: Mapping[str, torch.Tensor], output: Path,
                  writer_hashes: Mapping[str, str]) -> dict[str, str]:
    from converter_stream import tensor_header
    headers = {name: tensor_header(tensor, 0) for name, tensor in state.items()}
    with safe_open(output, framework="pt", device="cpu") as reader:
        if set(reader.keys()) != set(state):
            raise ValueError("Rust parser keys differ")
        for name in state:
            item = reader.get_slice(name)
            if item.get_shape() != headers[name]["shape"] or item.get_dtype() != headers[name]["dtype"]:
                raise ValueError("Rust parser metadata differs")
    hashes: dict[str, str] = {}
    with output.open("rb") as handle:
        header_size = struct.unpack("<Q", handle.read(8))[0]
        if header_size >= 100_000_000:
            raise ValueError("Oversized output header")
        actual_headers = json.loads(handle.read(header_size))
        for name, tensor in state.items():
            raw = memoryview(tensor.detach().reshape(-1).view(torch.uint8).numpy())
            entry = actual_headers[name]
            if entry["data_offsets"][1]-entry["data_offsets"][0] != raw.nbytes:
                raise ValueError("Tensor byte length mismatch")
            handle.seek(8+header_size+entry["data_offsets"][0])
            source_hash, output_hash = hashlib.sha256(), hashlib.sha256()
            for start in range(0, raw.nbytes, CHUNK_BYTES):
                block = raw[start:start+CHUNK_BYTES]
                actual = handle.read(len(block))
                if len(actual) != len(block):
                    raise ValueError("Short output read")
                source_hash.update(block)
                output_hash.update(actual)
            if source_hash.digest() != output_hash.digest() or output_hash.hexdigest() != writer_hashes[name]:
                raise ValueError("Tensor content/order corruption")
            hashes[name] = output_hash.hexdigest()
    return hashes
