# /// script
# requires-python = ">=3.12"
# dependencies = ["torch", "numpy", "safetensors", "pydantic>=2"]
# ///
# How to run: python converter.py CHECKPOINT PINNED_CONVERT OUTPUT.safetensors
"""Bounded CPU conversion entrypoint; external resource/deadline guard required."""
from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

from converter_mapping import MappingSource, checkpoint_tensors, mapped_tensors
from converter_stream import stream_safetensors, tensor_header


def convert(checkpoint: Path, source: Path, output: Path) -> None:
    """Metadata gate precedes payload reads; unsupported cases stop without fallback."""
    mapping = MappingSource(source)
    metadata = mapped_tensors(checkpoint_tensors(checkpoint, metadata=True), mapping)
    for tensor in metadata.values():
        tensor_header(tensor, 0)
    del metadata
    state = mapped_tensors(checkpoint_tensors(checkpoint, metadata=False), mapping)
    result = stream_safetensors(state, output)
    report = {"status": "WRITTEN_REQUIRES_INDEPENDENT_VERIFICATION", "torch": torch_version(),
              "loader": {"mmap": True, "map_location": "cpu", "weights_only": True},
              "chunk_bytes": 8 * 1024 * 1024, **asdict(result)}
    output.with_name(output.name + ".manifest.json").write_text(json.dumps(report, indent=2) + "\n")


def torch_version() -> str:
    """Report actual runtime without requesting any model execution."""
    import torch
    return torch.__version__


if __name__ == "__main__":
    if len(sys.argv) != 4:
        raise SystemExit("Usage: converter.py CHECKPOINT PINNED_CONVERT OUTPUT.safetensors")
    convert(*(Path(value) for value in sys.argv[1:]))
