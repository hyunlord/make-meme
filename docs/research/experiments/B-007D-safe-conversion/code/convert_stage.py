"""Two separate stages; each invocation performs at most one real checkpoint load.
CLI: python convert_stage.py metadata|conversion CHECKPOINT OFFICIAL_CONVERT
     B007B_CODE B007C_CODE OS_PROOF_JSON SHARED_LEDGER OUTPUT_DIR
Execute ONLY inside independently verified OS sandbox. No model forward.
"""
from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import Literal
from pydantic import TypeAdapter

import torch

from scoped_loader import CHECKPOINT_SHA, load_fixed, require, sha
from static_contract import TensorContract, check_key_set, expected_tensors
from same_state_verify import verify_output


def compare_metadata(state: dict[str, torch.Tensor], expected: dict[str, TensorContract], stage: str) -> None:
    for name, tensor in state.items():
        contract = expected[name]
        require(tuple(tensor.shape) == contract.shape and tuple(tensor.stride()) == contract.stride
                and tensor.storage_offset() == contract.storage_offset and str(tensor.dtype) == contract.dtype
                and tensor.untyped_storage().nbytes() == contract.storage_bytes, "Actual tensor metadata differs from static graph")
        if stage == "metadata":
            require(getattr(tensor.untyped_storage(), "_checkpoint_offset", None) == contract.checkpoint_offset,
                    "FakeTensor storage offset differs from exact ZIP header")


def main() -> None:
    stage, checkpoint_arg, official_arg, prior_arg, graph_arg, proof_arg, ledger_arg, output_arg = sys.argv[1:]
    stage = TypeAdapter(Literal["metadata", "conversion"]).validate_python(stage)
    checkpoint, official, prior, graph, proof, ledger, output = [Path(p) for p in
        (checkpoint_arg, official_arg, prior_arg, graph_arg, proof_arg, ledger_arg, output_arg)]
    started = time.monotonic()
    output.mkdir(parents=True, exist_ok=True)
    for name, digest in {'converter_mapping.py': '6e5036c8ea450e8aced25cdc73ee8da0a5570028c5d36147a48b4fe808c0db37', 'converter_stream.py': '1148c7c5efd0f1d1eec46b4d266248f1f3afeb7bb47ee4ffff9e973575c2a510'}.items():
        require(sha(prior / name) == digest, "Prior converter code changed")
    sys.path.insert(0, str(prior))
    from converter_mapping import MappingSource
    from converter_stream import stream_safetensors, tensor_header
    expected = expected_tensors(checkpoint, graph)
    state, scope = load_fixed(checkpoint, proof, ledger, stage)
    check_key_set(set(state), set(expected))
    compare_metadata(state, expected, stage)
    mapper = MappingSource(official).load()
    mapped: dict[str, torch.Tensor] = {}
    provenance = {}
    for original_name, original in state.items():
        pieces = mapper(original_name, original)
        require(bool(pieces) and sum(t.numel()*t.element_size() for t in pieces.values()) == original.numel()*original.element_size(),
                "Mapping drops/adds source tensor bytes")
        offsets = []
        for name, piece in pieces.items():
            require(name not in mapped and piece.dtype == original.dtype, "Duplicate output or dtype change")
            require(piece.untyped_storage()._cdata == original.untyped_storage()._cdata, "Mapping allocated a new payload")
            offsets.append(piece.storage_offset())
            mapped[name] = piece
        ordered = list(pieces.values())
        require(offsets[0] == original.storage_offset(), "Mapped split start differs")
        require(all(offsets[i+1] == offsets[i]+ordered[i].numel() for i in range(len(offsets)-1)), "Mapped QKV/KV split order/coverage differs")
        provenance[original_name] = [{"output": name, "shape": list(piece.shape), "stride": list(piece.stride()),
                                      "storage_offset": piece.storage_offset()} for name, piece in pieces.items()]
    headers = {name: tensor_header(tensor, 0) for name, tensor in mapped.items()}
    evidence = {"stage": stage, "scope": scope, "source_contract": {n: c.model_dump(mode="json") for n, c in expected.items()},
                "mapped_headers": headers, "mapping_provenance": provenance, "checkpoint_sha256": CHECKPOINT_SHA,
                "mapped_tensor_count": len(mapped), "mapped_tensor_bytes": sum(h["data_offsets"][1] for h in headers.values())}
    if stage == "metadata":
        evidence.update({"status": "PASS", "payload_values": "NOT_VERIFIED", "seconds": time.monotonic()-started})
        with (ledger / "metadata-pass.json").open("x") as handle:
            json.dump(evidence, handle, indent=2)
        return
    receipt = json.loads((ledger / "metadata-pass.json").read_text())
    require(receipt["mapped_headers"] == headers and receipt["source_contract"] == evidence["source_contract"], "Metadata changed between stages")
    staging = output / "wan-model.unverified.safetensors"
    final = output / "wan-model.safetensors"
    require(not final.exists(), "Final output already exists")
    written = stream_safetensors(mapped, staging)
    # Retain original state: no second torch.load for verification.
    hashes = verify_output(mapped, staging, {name: item["sha256"] for name, item in written.tensors.items()})
    require(sha(checkpoint) == CHECKPOINT_SHA, "Source changed during conversion")
    os.link(staging, final)
    staging.unlink()
    evidence.update({"status": "CONVERSION_PASS_NOT_MODEL_FORWARD", "seconds": time.monotonic()-started,
                     "writer": asdict(written), "verified_tensor_hashes": hashes, "output_sha256": sha(final)})
    with (output / "conversion.json").open("x") as handle:
        json.dump(evidence, handle, indent=2)


if __name__ == "__main__":
    main()
