# /// script
# requires-python = ">=3.12"
# dependencies = ["torch", "safetensors", "pydantic>=2", "pytest"]
# ///
# How to run: SCAIL_CONVERT_SOURCE=/path/to/pinned/convert.py python -m pytest test_conversion.py -q
"""Synthetic mapping/serialization equivalence; no model or pet quality claims."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path

import pytest
import torch
from converter import convert
from converter_mapping import ConversionError, MappingSource, checkpoint_tensors, mapped_tensors
from converter_stream import stream_safetensors
from safetensors import safe_open
from safetensors.torch import load_file, save_file
from torch._subclasses.fake_tensor import FakeTensor


@pytest.fixture
def official_source() -> Path:
    return Path(os.environ["SCAIL_CONVERT_SOURCE"])


@pytest.fixture
def state() -> dict[str, torch.Tensor]:
    leaves = [
        "mixins.adaln_layer.adaLN_modulations.0",
        "mixins.adaln_layer.query_layernorm_list.0.weight",
        "mixins.adaln_layer.key_layernorm_list.0.weight",
        "mixins.adaln_layer.cross_query_layernorm_list.0.weight",
        "mixins.adaln_layer.cross_key_layernorm_list.0.weight",
        "mixins.adaln_layer.clip_feature_key_layernorm_list.0.weight",
        "mixins.adaln_layer.clip_feature_key_value_list.0.weight",
        "mixins.final_layer.adaLN_modulation",
        "mixins.final_layer.linear.weight",
        "mixins.patch_embed.proj.weight", "mixins.patch_embed.proj_pose.weight",
        "mixins.patch_embed.proj_mask.weight",
        "transformer.layers.0.attention.dense.weight",
        "transformer.layers.0.attention.query_key_value.weight",
        "transformer.layers.0.cross_attention.dense.weight",
        "transformer.layers.0.cross_attention.query.weight",
        "transformer.layers.0.cross_attention.key_value.weight",
        "transformer.layers.0.post_cross_attention_layernorm.weight",
        "transformer.layers.0.mlp.dense_h_to_4h.weight",
        "transformer.layers.0.mlp.dense_4h_to_h.weight",
        "time_embed.0.weight", "adaln_projection.1.weight",
        "text_embedding.0.weight", "clip_proj.proj.0.weight",
        "transformer.layers.0.attention.query_key_value.bias",
        "transformer.layers.0.cross_attention.key_value.bias",
        "mixins.adaln_layer.clip_feature_key_value_list.0.bias",
    ]
    tensors: dict[str, torch.Tensor] = {}
    for index, name in enumerate(leaves):
        dtype = (torch.bfloat16, torch.float32, torch.float16)[index % 3]
        values = torch.arange(24, dtype=torch.float32).reshape(6, 4) + index
        if name.endswith("bias"):
            values = values[:, 0].contiguous()
        tensors["model.diffusion_model." + name] = values.to(dtype)
    return tensors


def tensor_hash(tensor: torch.Tensor) -> str:
    return hashlib.sha256(tensor.reshape(-1).view(torch.uint8).numpy().tobytes()).hexdigest()


def test_official_equivalence(tmp_path: Path, state: dict[str, torch.Tensor], official_source: Path) -> None:
    checkpoint = tmp_path / "small.pt"
    torch.save({"module": state, "iteration": 123}, checkpoint)
    metadata = checkpoint_tensors(checkpoint, metadata=True)
    assert all(isinstance(t, FakeTensor) for t in metadata.values())
    loaded = checkpoint_tensors(checkpoint, metadata=False)
    assert all(t.device.type == "cpu" for t in loaded.values())
    spec = importlib.util.spec_from_file_location("official_golden", official_source)
    assert spec is not None and spec.loader is not None
    official = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(official)
    golden = official.get_new_state_dict(state)
    golden_path = tmp_path / "official.safetensors"
    save_file(golden, golden_path)
    output = tmp_path / "streamed.safetensors"
    convert(checkpoint, official_source, output)
    expected, actual = load_file(golden_path), load_file(output)
    assert actual.keys() == expected.keys()
    evidence = json.loads(output.with_name(output.name + ".manifest.json").read_text())
    for name in actual:
        a, b = actual[name], expected[name]
        assert a.dtype == b.dtype and a.shape == b.shape
        assert a.is_contiguous() and b.is_contiguous()
        assert torch.equal(a, b)
        assert tensor_hash(a) == tensor_hash(b) == evidence["tensors"][name]["sha256"]
    with safe_open(output, framework="pt", device="cpu") as handle:
        assert set(handle.keys()) == set(golden)
    # Explicit independent Q/K/V order check beyond official mapping equivalence.
    source = state["model.diffusion_model.transformer.layers.0.attention.query_key_value.weight"]
    for part, name in enumerate(("q", "k", "v")):
        assert torch.equal(actual[f"blocks.0.self_attn.{name}.weight"], source[part * 2:part * 2 + 2])


def test_storage_views_and_scalar_empty(tmp_path: Path, official_source: Path) -> None:
    qkv = torch.arange(24, dtype=torch.bfloat16).reshape(6, 4)
    mapped = mapped_tensors({"model.diffusion_model.transformer.layers.0.attention.query_key_value.weight": qkv}, MappingSource(official_source))
    assert all(value.untyped_storage().data_ptr() == qkv.untyped_storage().data_ptr() for value in mapped.values())
    tensors = {"scalar": torch.tensor(1.5, dtype=torch.bfloat16), "empty": torch.empty(0), **mapped}
    output = tmp_path / "views.safetensors"
    stream_safetensors(tensors, output)
    restored = load_file(output)
    assert all(torch.equal(value, restored[key]) for key, value in tensors.items())


def test_noncontiguous_rejected(tmp_path: Path) -> None:
    output = tmp_path / "bad.safetensors"
    with pytest.raises(ConversionError, match="contiguous"):
        stream_safetensors({"bad": torch.ones(3, 4).T}, output)
    assert not output.exists()


def test_originals_preserved(tmp_path: Path) -> None:
    output = tmp_path / "existing.safetensors"
    output.write_bytes(b"original")
    with pytest.raises(ConversionError, match="already exists"):
        stream_safetensors({"x": torch.ones(2)}, output)
    assert output.read_bytes() == b"original"


def test_pinned_source_required(tmp_path: Path) -> None:
    source = tmp_path / "changed.py"
    source.write_text("raise RuntimeError('must never execute')")
    with pytest.raises(ConversionError, match="SHA"):
        MappingSource(source).load()


class UnsupportedCheckpoint:
    """Fixture with an unapproved pickle global; it must never be allowlisted."""


def test_unsafe_global_rejected(tmp_path: Path) -> None:
    checkpoint = tmp_path / "unsafe.pt"
    torch.save({"module": {"x": torch.ones(1)}, "extra": UnsupportedCheckpoint()}, checkpoint)
    with pytest.raises(ConversionError, match="globals"):
        checkpoint_tensors(checkpoint, metadata=True)


def test_legacy_mmap_rejected(tmp_path: Path) -> None:
    checkpoint = tmp_path / "legacy.pt"
    torch.save({"module": {"x": torch.ones(1)}}, checkpoint, _use_new_zipfile_serialization=False)
    with pytest.raises((RuntimeError, ValueError)):
        checkpoint_tensors(checkpoint, metadata=True)


def test_independent_verifier_detects_payload_corruption(tmp_path: Path, state: dict[str, torch.Tensor], official_source: Path) -> None:
    from converter_verify import verify

    checkpoint = tmp_path / "verify.pt"
    output = tmp_path / "verify.safetensors"
    torch.save({"module": state}, checkpoint)
    convert(checkpoint, official_source, output)
    report = verify(checkpoint, official_source, output)
    assert report.tensor_count == len(load_file(output))
    with output.open("r+b") as handle:
        handle.seek(-1, 2)
        last = handle.read(1)
        handle.seek(-1, 2)
        handle.write(bytes([last[0] ^ 1]))
    with pytest.raises(ConversionError, match="payload hash"):
        verify(checkpoint, official_source, output)
