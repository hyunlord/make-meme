"""Prepared fixed-artifact restricted loader; OS sandbox gate required externally.
This module is NOT an OS security boundary. No automatic retry or fallback.
"""
from __future__ import annotations

import hashlib
import importlib
import json
import os
import resource
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, TypedDict

import numpy as np
import torch
from pydantic import ConfigDict, TypeAdapter
from numpy._core.multiarray import _reconstruct
from torch._subclasses.fake_tensor import FakeTensorMode

CHECKPOINT_SHA = "d6c73e94c57eb36e6351c800d1228e41ed7e45db1ccf410dd875bcfdd2945e7f"
CHECKPOINT_BYTES = 65_582_563_395
EXPECTED_UNSAFE = {"numpy.core.multiarray._reconstruct", "numpy.ndarray", "numpy.dtype"}


class LoadingBlocked(RuntimeError):
    """Fail closed; never broaden permissions or retry automatically."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise LoadingBlocked(message)


def sha(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


class Snapshot(TypedDict):
    monotonic_seconds: float
    utc: str
    rss_max_kib: int
    io: dict[str, int]


class PhaseEvidence(TypedDict):
    start: Snapshot
    end: Snapshot
    semantics: str


class ScopeEvidence(TypedDict):
    import_ambient: list[str]
    fake_added: list[str]
    scope_restored: bool
    stage: str
    checkpoint_sha256: str
    hash_phase: PhaseEvidence
    load_phase: PhaseEvidence


def phase_snapshot() -> Snapshot:
    io = {}
    with Path("/proc/self/io").open() as handle:
        for line in handle:
            key, value = line.split(":", 1)
            io[key] = int(value.strip())
    return {"monotonic_seconds": time.monotonic(), "utc": datetime.now(timezone.utc).isoformat(),
            "rss_max_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss, "io": io}


def check_ambient(entries: set, expected_names: list[str]) -> None:
    """Reject aliases/additions; resolve each frozen symbol to exact live identity."""
    names = []
    for entry in entries:
        require(not isinstance(entry, tuple), "Unexpected ambient alias tuple")
        name = f"{entry.__module__}.{entry.__qualname__}"
        require(name in expected_names, "Unexpected ambient global")
        resolved = importlib.import_module(entry.__module__)
        for part in entry.__qualname__.split("."):
            resolved = getattr(resolved, part)
        require(resolved is entry, "Ambient symbol identity mismatch")
        names.append(name)
    require(sorted(names) == sorted(expected_names), "Ambient full name set mismatch")


def load_fixed(checkpoint: Path, proof: Path, ledger: Path, stage: Literal["metadata", "conversion"]) -> tuple[dict[str, torch.Tensor], ScopeEvidence]:
    """Exactly one real load in this call; return retained state and scope evidence.

    Only runner may supply an actual tested sandbox proof. A JSON status is
    insufficient by itself: process isolation must already surround this code.
    Shared ledger path must be identical across both isolated invocations.
    """
    gate = json.loads(proof.read_text())
    require(gate.get("status") == "PASS", "OS isolation proof not PASS")
    hash_start = phase_snapshot()
    require(checkpoint.stat().st_size == CHECKPOINT_BYTES and sha(checkpoint) == CHECKPOINT_SHA,
            "Fixed checkpoint identity mismatch")
    hash_end = phase_snapshot()
    require(torch.__version__ == "2.14.0+cu130" and torch.version.git_version == "08187d9e0fba026dc8217405802ab5381dc88d90"
            and np.__version__ == "2.5.2", "Runtime drift")
    unsafe = set(torch.serialization.get_unsafe_globals_in_checkpoint(checkpoint))
    require(unsafe == EXPECTED_UNSAFE, "Unexpected static globals")
    ambient_path = Path(__file__).with_name("ambient_contract.json")
    require(sha(ambient_path) == "1c9ea8eba2838b73c8f492aded7a3e5d4c7f4ae69bbd7fe0e31d57b7025c94b0", "Ambient manifest digest changed")
    ambient_contract = json.loads(ambient_path.read_text())
    imported = set(torch.serialization.get_safe_globals())
    check_ambient(imported, ambient_contract["post_import"])
    with FakeTensorMode():
        pass
    ambient = set(torch.serialization.get_safe_globals())
    check_ambient(ambient, ambient_contract["post_fake"])
    require(not any(entry in ambient for entry in (_reconstruct, np.ndarray, np.dtype, type(np.dtype(np.uint32)))),
            "Unexpected NumPy ambient allowlist")
    ledger.mkdir(parents=True, exist_ok=True)
    if stage == "conversion":
        require((ledger / "metadata-pass.json").is_file(), "Metadata receipt absent")
        receipt = json.loads((ledger / "metadata-pass.json").read_text())
        require(receipt.get("checkpoint_sha256") == CHECKPOINT_SHA and receipt.get("status") == "PASS",
                "Metadata receipt mismatch")
    attempt = ledger / f"{stage}-attempt.json"
    with attempt.open("x") as handle:
        json.dump({"stage": stage, "pid": os.getpid(), "checkpoint_sha256": CHECKPOINT_SHA,
                   "status": "ATTEMPT_RESERVED_BEFORE_LOAD", "reserved_utc": datetime.now(timezone.utc).isoformat(),
                   "loader_code_sha256": sha(Path(__file__)), "proof_sha256": sha(proof),
                   "hash_phase": {"start": hash_start, "end": hash_end}, "preload_snapshot": phase_snapshot()}, handle)
    entries = [(_reconstruct, "numpy.core.multiarray._reconstruct"), np.ndarray, np.dtype, type(np.dtype(np.uint32))]
    load_start = phase_snapshot()
    if stage == "metadata":
        with torch.serialization.safe_globals(entries), FakeTensorMode():
            checkpoint_data = torch.load(checkpoint, weights_only=True, mmap=True, map_location="cpu")
    else:
        with torch.serialization.safe_globals(entries):
            checkpoint_data = torch.load(checkpoint, weights_only=True, mmap=True, map_location="cpu")
    load_end = phase_snapshot()
    require(set(torch.serialization.get_safe_globals()) == ambient, "Scoped globals not restored")
    require(set(checkpoint_data) == {"iteration", "lr_scheduler", "random_rng_state", "np_rng_state",
                                   "torch_rng_state", "cuda_rng_state", "module"}, "Unexpected root structure")
    rng = checkpoint_data["np_rng_state"]
    require(type(rng) is tuple and len(rng) == 5 and rng[0] == "MT19937", "Unexpected RNG structure")
    require(type(rng[1]) is np.ndarray and rng[1].shape == (624,) and rng[1].dtype == np.dtype("uint32"),
            "Unexpected RNG state array")
    require(type(rng[2]) is int and 0 <= rng[2] <= 624 and rng[3] in (0, 1)
            and type(rng[4]) is float and np.isfinite(rng[4]), "Unexpected RNG scalar fields")
    state = TypeAdapter(dict[str, torch.Tensor], config=ConfigDict(arbitrary_types_allowed=True)).validate_python(checkpoint_data["module"], strict=True)
    require(len(state) == 987 and all(type(key) is str and isinstance(value, torch.Tensor)
                                    for key, value in state.items()), "Unexpected tensor state")
    scope: ScopeEvidence = {"import_ambient": sorted(f"{x.__module__}.{x.__qualname__}" for x in imported),
             "fake_added": sorted(f"{x.__module__}.{x.__qualname__}" for x in ambient-imported),
             "scope_restored": True, "stage": stage, "checkpoint_sha256": CHECKPOINT_SHA,
             "hash_phase": {"start": hash_start, "end": hash_end, "semantics": "Full file65GB byte scan, includes payload IO"},
             "load_phase": {"start": load_start, "end": load_end, "semantics": "Separate restricted load phase; assess actual IO delta, not whole process"}}
    return state, scope
