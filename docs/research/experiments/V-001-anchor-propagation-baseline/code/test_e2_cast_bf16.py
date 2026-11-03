"""Stdlib-only fixtures by default; opt-in torch fixture only after GPU work ends."""
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

import e2_cast_bf16 as cast


def write_tensor(path, dtype="F32"):
    header = {"__metadata__": {"format": "pt"},
              "test.weight": {"dtype": dtype, "shape": [4], "data_offsets": [0, 16]}}
    data = json.dumps(header).encode()
    data += b" " * (-len(data) % 8)
    path.write_bytes(struct.pack("<Q", len(data)) + data + struct.pack("<4f", 0.0, 1.125, -2.5, float("nan")))


def fixture(root):
    source = root / "original"
    source.mkdir()
    (source / "config.json").write_text('{"model_type":"bernini_renderer"}')
    (source / "vae").mkdir()
    (source / "vae/config.json").write_text('{}')
    for component in cast.COMPONENTS:
        directory = source / component
        directory.mkdir()
        mapping = {}
        for i in range(12):
            name = f"shard-{i:02}.safetensors"
            # Unique tensor names per shard are required by the index contract.
            write_tensor(directory / name)
            raw = (directory / name).read_bytes()
            n = struct.unpack("<Q", raw[:8])[0]
            header = json.loads(raw[8:8+n])
            header[f"test.weight.{i}"] = header.pop("test.weight")
            encoded = json.dumps(header).encode()
            encoded += b" " * (-len(encoded) % 8)
            (directory / name).write_bytes(struct.pack("<Q",len(encoded)) + encoded + raw[8+n:])
            mapping[f"test.weight.{i}"] = name
        (directory / cast.INDEX).write_text(json.dumps({"metadata": {"total_size": 192}, "weight_map": mapping}))
    config = {"source_root": str(source), "target_root": str(root / "converted"),
              "receipt": str(root / "receipt.json"), "source_revision": cast.REVISION}
    path = root / "private.json"
    path.write_text(json.dumps(config))
    return config, path


class CastTests(unittest.TestCase):
    def test_header_schema_inspection_imports_no_torch(self):
        with tempfile.TemporaryDirectory() as directory:
            config, _ = fixture(Path(directory))
            rows = cast.inspect(config)
            self.assertEqual(len(rows), 24)
            self.assertEqual(sum(row["target_payload_bytes"] for row in rows), 192)
            self.assertFalse(Path(config["target_root"]).exists())
            self.assertNotIn("torch", sys.modules)

    def test_rejects_non_fp32_header(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.safetensors"
            write_tensor(path, "BF16")
            with self.assertRaisesRegex(ValueError, "Unexpected dtype"):
                cast.read_header(path)

    def test_existing_target_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            config, _ = fixture(Path(directory))
            Path(config["target_root"]).mkdir()
            with self.assertRaisesRegex(ValueError, "New target"):
                cast.inspect(config)

    def test_index_header_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            config, _ = fixture(Path(directory))
            index_path = Path(config["source_root"]) / "transformer" / cast.INDEX
            index = json.loads(index_path.read_text())
            index["metadata"]["total_size"] = 0
            index_path.write_text(json.dumps(index))
            with self.assertRaisesRegex(ValueError, "payload size mismatch"):
                cast.inspect(config)

    @unittest.skipUnless(os.environ.get("E2_CAST_RUN_TORCH_FIXTURE") == "1", "Only after parent GPU work ends")
    def test_real_tiny_cpu_cast_readback_and_original_retention(self):
        with tempfile.TemporaryDirectory() as directory:
            config, path = fixture(Path(directory))
            source_files = sorted(Path(config["source_root"]).rglob("*.safetensors"))
            original_hashes = [cast.sha256(item) for item in source_files]
            subprocess.run([sys.executable, str(Path(cast.__file__)), "--config", str(path)], check=True)
            receipt = json.loads(Path(config["receipt"]).read_text())
            self.assertEqual(receipt["status"], "COMPLETE_VERIFIED_CPU_CAST")
            self.assertEqual(len(receipt["shards"]), 24)
            self.assertEqual(original_hashes, [cast.sha256(item) for item in source_files])
            self.assertTrue((Path(config["target_root"]) / "vae").is_symlink())
            for row in receipt["component_indices"]:
                self.assertEqual(row["target_payload_bytes"], 96)


if __name__ == "__main__":
    unittest.main()
