# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# Run with existing research Python: convert_vace_bf16.py --config PRIVATE.json [--cpu-only]
"""V002 r1: materialize VACE transformer CPU BF16 casts once.

python convert_vace_bf16.py --config PRIVATE.json [--cpu-only]
No model imports; torch/safetensors are imported only by an explicit conversion.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import sys
import tempfile
import time

EXPECTED_SOURCE_BYTES = {"F32": 57153966336, "BF16": 6098202624}
EXPECTED_TENSORS = 1331
INDEX = "diffusion_pytorch_model.safetensors.index.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path: Path, value: dict) -> None:
    with tempfile.NamedTemporaryFile("w", dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        json.dump(value, stream, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    if json.loads(path.read_text()) != value:
        raise RuntimeError("JSON readback mismatch")


def read_header(path: Path) -> dict:
    with path.open("rb") as stream:
        prefix = stream.read(8)
        if len(prefix) != 8:
            raise ValueError("Truncated safetensors prefix")
        length = struct.unpack("<Q", prefix)[0]
        if not 0 < length <= 16 * 1024 * 1024:
            raise ValueError("Invalid safetensors header size")
        header = json.loads(stream.read(length))
    for key, tensor in header.items():
        if key != "__metadata__" and tensor["dtype"] not in ("F32", "BF16"):
            raise ValueError(f"Unexpected dtype {tensor['dtype']} in {path.name}:{key}")
    return header


def inspect(config: dict) -> list[dict]:
    if set(config) != {"source_root", "target_root", "receipt"}:
        raise ValueError("Unexpected private config keys")
    source, target, receipt = (Path(config[key]) for key in ("source_root", "target_root", "receipt"))
    if not all(path.is_absolute() for path in (source, target, receipt)):
        raise ValueError("Absolute private paths required")
    if target.exists() or target.is_symlink() or receipt.exists():
        raise ValueError("New target and receipt required; originals/results never overwritten")
    if not target.parent.is_dir() or not receipt.parent.is_dir():
        raise ValueError("Destination parents must exist")
    if source.resolve() == target.resolve() or source.resolve() in target.resolve().parents:
        raise ValueError("Target must be separate from source")
    root_config = json.loads((source / "config.json").read_text())
    if root_config.get("model_type") != "vace" or root_config.get("dim") != 5120:
        raise ValueError("Expected VACE 14B source configuration")
    index = json.loads((source / INDEX).read_text())
    files = sorted(set(index["weight_map"].values()))
    if len(files) != 7:
        raise ValueError("Expected seven VACE shards")
    rows = []
    totals = {"F32": 0, "BF16": 0}
    for filename in files:
        if Path(filename).name != filename:
            raise ValueError("Index path traversal")
        header = read_header(source / filename)
        tensors = {key: value for key, value in header.items() if key != "__metadata__"}
        expected = {key for key, value in index["weight_map"].items() if value == filename}
        if set(tensors) != expected:
            raise ValueError("Index/header tensor names differ")
        sizes = {"F32": 0, "BF16": 0}
        for tensor in tensors.values():
            sizes[tensor["dtype"]] += tensor["data_offsets"][1] - tensor["data_offsets"][0]
        for dtype, size in sizes.items():
            totals[dtype] += size
        rows.append({"file": filename, "source_payload_bytes": sum(sizes.values()),
                     "source_dtype_bytes": sizes,
                     "target_payload_bytes": sizes["F32"] // 2 + sizes["BF16"],
                     "tensor_count": len(tensors)})
    if totals != EXPECTED_SOURCE_BYTES or sum(row["tensor_count"] for row in rows) != EXPECTED_TENSORS:
        raise ValueError("Source headers differ from inspected VACE 14B")
    # Official index counts all parameters as F32; shard 7 is already BF16.
    if index["metadata"]["total_size"] != 69350371584:
        raise ValueError("Source index differs from inspected original metadata")
    required = sum(row["target_payload_bytes"] for row in rows)
    if shutil.disk_usage(target.parent).free < required * 1.1:
        raise RuntimeError("Insufficient free space for separate BF16 copy plus margin")
    return rows


def convert(config: dict, rows: list[dict]) -> None:
    # This is an offline CPU data transform, never a model or inference entry.
    if "torch" in sys.modules:
        raise RuntimeError("Use a fresh process; torch must not be preloaded")
    os.environ["CUDA_VISIBLE_DEVICES"] = ""
    os.environ["OMP_NUM_THREADS"] = "2"
    os.environ["MKL_NUM_THREADS"] = "2"
    os.nice(10)
    import torch
    from safetensors import safe_open
    from safetensors.torch import save_file

    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    source, target, receipt_path = (Path(config[key]) for key in ("source_root", "target_root", "receipt"))
    started = time.monotonic()
    target.mkdir()
    receipt = {"status": "STARTED", "source_model": "Wan2.1-VACE-14B",
               "started_utc": datetime.now(timezone.utc).isoformat(),
               "source_root": str(source), "target_root": str(target),
               "torch_version": torch.__version__, "operation": "original.cpu().to(torch.bfloat16)",
               "verification": "all tensors uint8-view equality with original.to(BF16)",
               "source_index_declared_bytes": 69350371584,
               "source_actual_header_payload_bytes": sum(EXPECTED_SOURCE_BYTES.values()),
               "source_index_mismatch_preserved": True,
               "cuda_visible_devices": "", "nice_increment": 10, "cpu_threads": 2,
               "shards": [], "component_indices": [], "reused_components": []}
    atomic_json(receipt_path, receipt)
    try:
        for filename in ("config.json", "LICENSE.txt"):
            path = source / filename
            if path.is_file():
                shutil.copy2(path, target / filename)
                receipt["reused_components"].append({"name": filename, "method": "byte-copy"})
        receipt["source_root_config_sha256"] = sha256(source / "config.json")
        for row in rows:
            before = time.monotonic()
            original, destination = source / row["file"], target / row["file"]
            source_digest = sha256(original)
            converted = {}
            with safe_open(original, framework="pt", device="cpu") as handle:
                metadata = handle.metadata()
                for key in handle.keys():
                    tensor = handle.get_tensor(key)
                    if tensor.dtype not in (torch.float32, torch.bfloat16) or tensor.device.type != "cpu":
                        raise RuntimeError("Source tensor outside approved FP32/BF16 CPU contract")
                    converted[key] = tensor.to(dtype=torch.bfloat16, device="cpu").contiguous()
                    del tensor
            temporary = destination.with_name(destination.name + ".partial")
            save_file(converted, temporary, metadata=metadata)
            del converted
            with temporary.open("rb") as stream:
                os.fsync(stream.fileno())
            os.replace(temporary, destination)
            with safe_open(original, framework="pt", device="cpu") as old, safe_open(destination, framework="pt", device="cpu") as new:
                if list(old.keys()) != list(new.keys()) or old.metadata() != new.metadata():
                    raise RuntimeError("Readback keys/metadata differ")
                for key in old.keys():
                    expected = old.get_tensor(key).to(torch.bfloat16).contiguous()
                    observed = new.get_tensor(key)
                    if observed.dtype != torch.bfloat16 or expected.shape != observed.shape:
                        raise RuntimeError(f"Readback dtype/shape mismatch: {key}")
                    if not torch.equal(expected.reshape(-1).view(torch.uint8), observed.reshape(-1).view(torch.uint8)):
                        raise RuntimeError(f"Readback bit mismatch: {key}")
                    del expected, observed
            if sha256(original) != source_digest:
                raise RuntimeError("Original changed during conversion")
            receipt["shards"].append({**row, "source_sha256": source_digest,
                                      "converted_sha256": sha256(destination),
                                      "verification": "ALL_TENSORS_BIT_EXACT_TO_OFFICIAL_CPU_CAST",
                                      "elapsed_seconds": time.monotonic() - before})
            atomic_json(receipt_path, receipt)
            print(json.dumps(receipt["shards"][-1]), flush=True)
        original_index = source / INDEX
        index = json.loads(original_index.read_text())
        index["metadata"]["total_size"] = sum(row["target_payload_bytes"] for row in rows)
        atomic_json(target / INDEX, index)
        receipt["component_indices"].append({"component": "transformer-and-vace",
            "source_sha256": sha256(original_index), "converted_sha256": sha256(target / INDEX),
            "target_payload_bytes": index["metadata"]["total_size"]})
        receipt["status"] = "COMPLETE_VERIFIED_CPU_CAST"
    except (OSError, RuntimeError, ValueError, TypeError, KeyError) as error:
        receipt["status"] = "FAILED_INCOMPLETE_NOT_FOR_MODEL_USE"
        receipt["error_type"] = type(error).__name__
        raise
    finally:
        receipt["elapsed_seconds"] = time.monotonic() - started
        receipt["finished_utc"] = datetime.now(timezone.utc).isoformat()
        atomic_json(receipt_path, receipt)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--cpu-only", action="store_true", help="Headers/schema only; no torch import or conversion")
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    rows = inspect(config)
    if args.cpu_only:
        print(json.dumps({"status": "HEADERS_VALIDATED_NO_CONVERSION", "shard_count": len(rows),
                          "target_tensor_bytes": sum(row["target_payload_bytes"] for row in rows)}))
        return
    convert(config, rows)


if __name__ == "__main__":
    main()
