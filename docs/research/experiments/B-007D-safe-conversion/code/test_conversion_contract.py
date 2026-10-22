"""Synthetic-only regressions. No actual checkpoint imports or load calls.
PYTHONPATH=B007B_CODE:B007D_CODE python -m pytest test_conversion_contract.py -q
"""
from pathlib import Path
import struct

import pytest
import torch
from converter_stream import stream_safetensors
from pydantic import ValidationError

from same_state_verify import verify_output
from static_contract import TensorContract, check_key_set, insert_contract


def contract(**changes) -> TensorContract:
    values = {"shape": (2, 2), "stride": (2, 1), "storage_offset": 0, "storage_bytes": 16,
              "checkpoint_offset": 128, "storage_key": "0", "dtype": "torch.float32"}
    values.update(changes)
    return TensorContract(**values)


@pytest.mark.parametrize("changes", [{"storage_offset": 1}, {"stride": (1000, 1)},
                                      {"stride": (-1, 1)}, {"shape": (0, 2)}, {"stride": (1,)}])
def test_storage_bounds_rejected(changes) -> None:
    with pytest.raises(ValidationError):
        contract(**changes)


def test_duplicate_and_missing_keys() -> None:
    rows = {}
    insert_contract(rows, "tensor", contract())
    with pytest.raises(ValueError, match="Duplicate"):
        insert_contract(rows, "tensor", contract())
    with pytest.raises(ValueError, match="key set"):
        check_key_set({"q", "k"}, {"q", "k", "v"}, count=3)
    with pytest.raises(ValueError, match="key set"):
        check_key_set({"q", "k", "v"}, {"q", "k", "v"}, count=987)


def test_same_state_roundtrip_and_wrong_qkv_order(tmp_path: Path) -> None:
    base = torch.arange(24, dtype=torch.float32).reshape(6, 4)
    state = dict(zip(("q", "k", "v"), base.chunk(3)))
    target = tmp_path / "tiny.safetensors"
    result = stream_safetensors(state, target)
    hashes = {key: row["sha256"] for key, row in result.tensors.items()}
    assert verify_output(state, target, hashes) == hashes
    wrong = {"q": state["k"], "k": state["q"], "v": state["v"]}
    with pytest.raises(ValueError, match="content/order"):
        verify_output(wrong, target, hashes)


def test_byte_corruption_rejected(tmp_path: Path) -> None:
    state = {"weight": torch.arange(16, dtype=torch.float32)}
    target = tmp_path / "corrupt.safetensors"
    result = stream_safetensors(state, target)
    hashes = {key: row["sha256"] for key, row in result.tensors.items()}
    with target.open("r+b") as handle:
        header_size = struct.unpack("<Q", handle.read(8))[0]
        handle.seek(8+header_size)
        byte = handle.read(1)
        handle.seek(8+header_size)
        handle.write(bytes([byte[0] ^ 1]))
    with pytest.raises(ValueError, match="content/order"):
        verify_output(state, target, hashes)


def test_blocked_os_proof_precedes_checkpoint_access(tmp_path: Path, monkeypatch) -> None:
    from scoped_loader import LoadingBlocked, load_fixed
    proof = tmp_path / "blocked.json"
    proof.write_text('{"status":"BLOCKED"}')
    def forbidden_load(*args, **kwargs):
        raise AssertionError("torch.load must not run before OS proof")
    monkeypatch.setattr(torch, "load", forbidden_load)
    with pytest.raises(LoadingBlocked, match="OS isolation"):
        load_fixed(tmp_path / "nonexistent-checkpoint.pt", proof, tmp_path / "ledger", "metadata")
    assert not (tmp_path / "ledger").exists()


def test_fake_mapping_chunk_storage_and_order() -> None:
    from torch._subclasses.fake_tensor import FakeTensorMode
    with FakeTensorMode():
        original = torch.empty((12, 4), dtype=torch.float32)
        for pieces in (original.chunk(3, dim=0), original.chunk(2, dim=0)):
            assert all(piece.untyped_storage()._cdata == original.untyped_storage()._cdata for piece in pieces)
            offsets = [piece.storage_offset() for piece in pieces]
            assert offsets[0] == original.storage_offset()
            assert all(offsets[i+1] == offsets[i]+pieces[i].numel() for i in range(len(pieces)-1))
            assert sum(piece.numel() for piece in pieces) == original.numel()


def test_actual_metadata_comparison_path() -> None:
    from convert_stage import compare_metadata
    from scoped_loader import LoadingBlocked
    from torch._subclasses.fake_tensor import FakeTensorMode
    with FakeTensorMode():
        tensor = torch.empty((2, 2), dtype=torch.float32)
        tensor.untyped_storage()._checkpoint_offset = 128
        compare_metadata({"weight": tensor}, {"weight": contract()}, "metadata")
        with pytest.raises(LoadingBlocked, match="metadata differs"):
            compare_metadata({"weight": tensor.T}, {"weight": contract()}, "metadata")
        tensor.untyped_storage()._checkpoint_offset = 129
        with pytest.raises(LoadingBlocked, match="ZIP header"):
            compare_metadata({"weight": tensor}, {"weight": contract()}, "metadata")


def test_ambient_addition_and_alias_rejected() -> None:
    from scoped_loader import LoadingBlocked, check_ambient
    check_ambient({ValueError}, ["builtins.ValueError"])
    with pytest.raises(LoadingBlocked, match="Unexpected ambient"):
        check_ambient({ValueError, TypeError}, ["builtins.ValueError"])
    with pytest.raises(LoadingBlocked, match="alias"):
        check_ambient({(ValueError, "fake.ValueError")}, ["builtins.ValueError"])
