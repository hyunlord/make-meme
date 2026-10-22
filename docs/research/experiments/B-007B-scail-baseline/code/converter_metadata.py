# /// script
# requires-python = ">=3.12"
# dependencies = ["torch", "safetensors", "pydantic>=2"]
# ///
# How to run: python converter_metadata.py CHECKPOINT PINNED_CONVERT REPORT.json
"""Standalone safe metadata gate; no tensor payload hashing or conversion."""
from __future__ import annotations

import json
import sys
import time
from collections import Counter
from pathlib import Path

import torch

from converter_mapping import OFFICIAL_SHA, MappingSource, checkpoint_tensors, mapped_tensors
from converter_stream import tensor_header


def inspect_metadata(checkpoint: Path, source: Path, report: Path) -> None:
    """Run existing FakeTensor gate and persist exact mapped shape/dtype counts."""
    started = time.monotonic()
    state = checkpoint_tensors(checkpoint, metadata=True)
    mapped = mapped_tensors(state, MappingSource(source))
    dtype_counts: Counter[str] = Counter()
    dtype_bytes: Counter[str] = Counter()
    headers = {}
    total = 0
    for name, tensor in mapped.items():
        header = tensor_header(tensor, 0)
        length = header["data_offsets"][1]
        dtype_counts[header["dtype"]] += 1
        dtype_bytes[header["dtype"]] += length
        headers[name] = header
        total += length
    result = {
        "status": "PASS_METADATA_ONLY_PAYLOAD_NOT_READ",
        "torch": torch.__version__, "seconds": time.monotonic() - started,
        "official_mapping_sha256": OFFICIAL_SHA,
        "checkpoint_file_bytes": checkpoint.stat().st_size,
        "source_tensor_count": len(state), "mapped_tensor_count": len(mapped),
        "mapped_tensor_bytes": total, "dtype_tensor_counts": dict(dtype_counts),
        "dtype_tensor_bytes": dict(dtype_bytes), "tensors": headers,
        "loader": {"map_location": "cpu", "weights_only": True, "mmap": True, "fake_tensor_mode": True},
        "checks": ["unsafe globals rejected", "official mapping source SHA", "all keys mapped", "dtype supported", "contiguous strided layout", "no conjugate or negative view"],
        "limitations": ["Tensor payload values/hashes not read", "Actual conversion peak NOT_MEASURED", "Not a model state-shape or quality acceptance"],
    }
    with report.open("x") as handle:
        handle.write(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        raise SystemExit("Usage: converter_metadata.py CHECKPOINT PINNED_CONVERT REPORT.json")
    inspect_metadata(*(Path(value) for value in sys.argv[1:]))
