"""CPU synthetic-only restricted unpickling experiment; never accepts checkpoint input.

python fixture_rng.py NEW_OUTPUT_DIR B007B_CODE_DIR PINNED_CONVERT_PY
Run under an external timeout. Creates its own small tensors and NumPy RNG state.
No weights_only=False, pickle.load, add_safe_globals, or real checkpoint loading.
"""
from __future__ import annotations

import hashlib
import json
import pickle
import sys
import struct
import time
import zipfile
from pathlib import Path

import numpy as np
import torch
from numpy._core.multiarray import _reconstruct
from safetensors.torch import load_file, save_file
from torch._subclasses.fake_tensor import FakeTensor, FakeTensorMode


class UnexpectedFixtureGlobal:
    """Inert local class that is intentionally absent from the scoped allowlist."""


class FixtureError(RuntimeError):
    """A bounded synthetic validation contract failed."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise FixtureError(message)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tensor_record(tensor: torch.Tensor) -> dict[str, str | int | list[int]]:
    return {"dtype": str(tensor.dtype), "shape": list(tensor.shape), "stride": list(tensor.stride()),
            "storage_offset": tensor.storage_offset(), "storage_bytes": tensor.untyped_storage().nbytes()}


def main(output: Path, prior_code: Path, official_source: Path) -> None:
    start = time.monotonic()
    output.mkdir(parents=True, exist_ok=False)
    torch.set_num_threads(2)
    # Import the existing, preregistered strict gate and SHA-checked mapping only.
    sys.path.insert(0, str(prior_code))
    from converter_mapping import ConversionError, MappingSource, checkpoint_tensors, mapped_tensors

    import_baseline = set(torch.serialization.get_safe_globals())
    # FakeTensor lazy imports add framework globals; record rather than clear them.
    with FakeTensorMode():
        pass
    before = set(torch.serialization.get_safe_globals())
    ambient_names = sorted(f"{entry.__module__}.{entry.__qualname__}" for entry in before)
    lazy_added = sorted(f"{entry.__module__}.{entry.__qualname__}" for entry in before - import_baseline)
    base = torch.arange(36, dtype=torch.float32).reshape(6, 6)
    state = {"model.diffusion_model.transformer.layers.0.attention.query_key_value.weight": base,
             "model.diffusion_model.time_embed.0.weight": base[1:5, ::2],
             "model.diffusion_model.time_embed.2.weight": base.T}
    rng = np.random.RandomState(20261022).get_state()
    fixture = output / "locally-created-rng-fixture.pt"
    torch.save({"module": state, "np_rng_state": rng, "iteration": 7}, fixture, pickle_protocol=2)
    native_fixture = fixture
    native_hash = sha(native_fixture)
    fixture = output / "locally-created-legacy-global-fixture.pt"
    old_global = b"cnumpy._core.multiarray\n_reconstruct\n"
    legacy_global = b"cnumpy.core.multiarray\n_reconstruct\n"
    # ONLY a newly created local protocol2 fixture: no FRAME offsets to update.
    # Replace one exact GLOBAL spelling, preserve every storage member byte.
    with zipfile.ZipFile(native_fixture) as source_zip, zipfile.ZipFile(fixture, "x") as target_zip:
        changed = 0
        for info in source_zip.infolist():
            payload = source_zip.read(info.filename)
            if info.filename.endswith("/data.pkl"):
                require(payload.startswith(b"\x80\x02"), "Expected fixture protocol2")
                require(payload.count(old_global) == 1, "Expected exactly one local reconstruct GLOBAL")
                payload = payload.replace(old_global, legacy_global, 1)
                changed += 1
            target_zip.writestr(info, payload)
        require(changed == 1, "Expected one fixture metadata member")
    with zipfile.ZipFile(native_fixture) as native_zip, zipfile.ZipFile(fixture) as legacy_zip:
        require(native_zip.namelist() == legacy_zip.namelist(), "Fixture archive members changed")
        for name in native_zip.namelist():
            if not name.endswith("/data.pkl"):
                require(native_zip.read(name) == legacy_zip.read(name), "Fixture storage/member changed")
    require(sha(native_fixture) == native_hash, "Native fixture changed")
    expected_hash = sha(fixture)
    unsafe = torch.serialization.get_unsafe_globals_in_checkpoint(fixture)
    require(bool(unsafe), "Fixture should expose non-tensor globals")
    try:
        checkpoint_tensors(fixture, metadata=True)
    except ConversionError as error:
        strict_error = str(error)
    else:
        raise FixtureError("Existing strict gate accepted NumPy fixture")
    static_entries = [(_reconstruct, "numpy.core.multiarray._reconstruct"), np.ndarray, np.dtype]
    entries = [*static_entries, type(np.dtype(np.uint32))]
    entry_names = ["numpy.core.multiarray._reconstruct -> " + _reconstruct.__module__ + "." + _reconstruct.__qualname__,
                   "numpy.ndarray", "numpy.dtype", type(np.dtype(np.uint32)).__module__ + "." + type(np.dtype(np.uint32)).__qualname__]
    with torch.serialization.safe_globals(static_entries):
        try:
            torch.load(fixture, map_location="cpu", weights_only=True, mmap=True)
        except pickle.UnpicklingError as error:
            dynamic_dtype_error = str(error)
        else:
            raise FixtureError("Expected rejection without dynamic dtype entry")
    require(set(torch.serialization.get_safe_globals()) == before, "Dynamic failure scope leaked")
    tests = []
    for mmap in (False, True):
        require(sha(fixture) == expected_hash, "Synthetic fixture changed")
        with torch.serialization.safe_globals(entries):
            loaded = torch.load(fixture, map_location="cpu", weights_only=True, mmap=mmap)
        require(set(torch.serialization.get_safe_globals()) == before, "Scoped global state leaked")
        actual = loaded["module"]
        require(actual.keys() == state.keys(), "Tensor key mismatch")
        for key in state:
            require(tensor_record(actual[key]) == tensor_record(state[key]), f"Tensor metadata mismatch {key}")
            require(torch.equal(actual[key], state[key]), f"Tensor value mismatch {key}")
        require(len({value.untyped_storage().data_ptr() for value in actual.values()}) == 1, "Storage sharing lost")
        actual_rng = loaded["np_rng_state"]
        require(actual_rng[0] == rng[0] and np.array_equal(actual_rng[1], rng[1]) and actual_rng[2:] == rng[2:], "RNG mismatch")
        tests.append({"test": "restricted_full_fixture", "mmap": mmap, "status": "PASS"})
    with torch.serialization.safe_globals(entries), FakeTensorMode():
        fake = torch.load(fixture, map_location="cpu", weights_only=True, mmap=True)["module"]
    require(set(torch.serialization.get_safe_globals()) == before, "Fake scope leaked")
    for key in state:
        require(isinstance(fake[key], FakeTensor), "Metadata test returned real tensor")
        require(tensor_record(fake[key]) == tensor_record(state[key]), "Fake metadata mismatch")
    fake_storages = [value.untyped_storage() for value in fake.values()]
    fake_object_alias = all(storage is fake_storages[0] for storage in fake_storages)
    fake_checkpoint_offsets = [getattr(storage, "_checkpoint_offset", None) for storage in fake_storages]
    with zipfile.ZipFile(fixture) as archive:
        storage_members = [info for info in archive.infolist() if "/data/" in info.filename]
        require(len(storage_members) == 1, "Synthetic fixture must have exactly one storage member")
        info = storage_members[0]
        with fixture.open("rb") as handle:
            handle.seek(info.header_offset)
            header = handle.read(30)
        require(header[:4] == b"PK\x03\x04", "Invalid fixture local ZIP header")
        filename_length, extra_length = struct.unpack_from("<HH", header, 26)
        exact_storage_offset = info.header_offset + 30 + filename_length + extra_length
        require(info.compress_type == zipfile.ZIP_STORED and info.file_size == 144, "Unexpected synthetic storage encoding")
    require(all(offset == exact_storage_offset for offset in fake_checkpoint_offsets),
            "Fake checkpoint offsets do not match actual ZIP storage payload offset")
    tests.append({"test": "fake_tensor_mmap_metadata", "status": "PASS", "value_check": "NOT_APPLICABLE",
                  "storage_object_identity_shared": fake_object_alias,
                  "storage_object_identity_status": "PASS" if fake_object_alias else "NOT_PRESERVED",
                  "checkpoint_storage_offsets": fake_checkpoint_offsets, "zip_payload_offset": exact_storage_offset,
                  "scope": "Checkpoint-offset evidence only; not physical storage alias or real checkpoint validation"})
    unexpected = output / "locally-created-unexpected-global.pt"
    torch.save({"module": state, "unexpected": UnexpectedFixtureGlobal()}, unexpected)
    with torch.serialization.safe_globals(entries):
        try:
            torch.load(unexpected, map_location="cpu", weights_only=True, mmap=True)
        except pickle.UnpicklingError as error:
            unexpected_error = str(error)
        else:
            raise FixtureError("Unexpected class accepted")
    require(set(torch.serialization.get_safe_globals()) == before, "Failure scope leaked")
    mapped = mapped_tensors(actual, MappingSource(official_source))
    packed = {key: value.contiguous().clone() for key, value in mapped.items()}
    tensor_file = output / "mapped-tensor-only.safetensors"
    save_file(packed, tensor_file)
    roundtrip = load_file(tensor_file)
    require(roundtrip.keys() == packed.keys(), "Mapped keys differ")
    for key in packed:
        require(torch.equal(roundtrip[key], packed[key]) and roundtrip[key].dtype == packed[key].dtype
                and roundtrip[key].shape == packed[key].shape, "Mapped tensor roundtrip differs")
    require(sha(fixture) == expected_hash, "Original synthetic fixture mutated")
    report = {"scope": "SYNTHETIC_ONLY; no actual checkpoint/model/forward", "torch": torch.__version__, "numpy": np.__version__,
              "strict_gate": "REJECTED_AS_EXPECTED", "strict_error": strict_error, "static_globals": unsafe,
              "scoped_allowlist_exact": entry_names, "missing_dynamic_dtype_rejected": dynamic_dtype_error,
              "legacy_fixture_edit": "Exactly one protocol2 GLOBAL numpy._core to numpy.core; all other members byte-identical; original local fixture preserved", "dynamic_dtype_class": entry_names[-1], "safe_globals_restored": True,
              "ambient_safe_globals_after_import_count": len(import_baseline), "ambient_safe_globals_after_fake_warmup": ambient_names,
              "fake_lazy_import_added_globals": lazy_added, "scope_note": "Four scoped NumPy entries are additional to recorded framework ambient globals; dedicated subprocess only.",
              "rng_algorithm": rng[0], "rng_state_shape": list(rng[1].shape), "rng_state_dtype": str(rng[1].dtype),
              "tests": tests, "unexpected_global_rejected": True, "unexpected_error": unexpected_error,
              "tensors": {key: tensor_record(value) for key, value in state.items()},
              "mapping": {"official_source_sha256": sha(official_source), "existing_mapping_code_sha256": sha(prior_code / "converter_mapping.py"),
                          "output_keys": sorted(packed), "tensor_roundtrip": "PASS", "shared_storage_after_safetensors": "NOT_PRESERVED_BY_DESIGN; cloned independent tensor payloads"},
              "artifacts": {p.name: {"bytes": p.stat().st_size, "sha256": sha(p)} for p in (native_fixture, fixture, unexpected, tensor_file)},
              "elapsed_seconds": time.monotonic()-start, "actual_65GB_loading": "NOT_RUN", "GPU": "NOT_RUN"}
    (output / "fixture_results.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main(*(Path(value).resolve() for value in sys.argv[1:4]))
