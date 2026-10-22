"""Tiny CPU-only tests; actual official architecture fixture has no pretrained data."""
import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest
import torch
from safetensors.torch import save_file
from staged_loader import (
    LoaderError,
    assert_no_meta,
    assign_checkpoint,
    load_model,
    parameter_dtype,
)
from torch import nn


def test_exact_and_cast_assignment(tmp_path: Path) -> None:
    base = nn.Linear(3, 2)
    file = tmp_path / "tiny.safetensors"
    save_file(base.state_dict(), file)
    with torch.device("meta"):
        exact = nn.Linear(3, 2)
        cast = nn.Linear(3, 2)
    _, assignment = assign_checkpoint(exact, file, lambda _: torch.float32)
    assign_checkpoint(cast, file)
    assert_no_meta(exact)
    assert assignment == {"missing_keys": [], "unexpected_keys": [], "strict": True, "assign": True}
    for name, tensor in base.state_dict().items():
        assert torch.equal(tensor, exact.state_dict()[name])
        assert torch.equal(tensor.bfloat16(), cast.state_dict()[name])


@pytest.mark.parametrize("fault", ["missing", "unexpected", "shape", "dtype"])
def test_schema_rejected_before_assignment(tmp_path: Path, fault: str) -> None:
    state = dict(nn.Linear(3, 2).state_dict())
    if fault == "missing":
        del state["bias"]
    elif fault == "unexpected":
        state["extra"] = torch.ones(1)
    elif fault == "shape":
        state["weight"] = torch.ones(4, 3)
    else:
        state["weight"] = state["weight"].half()
    file = tmp_path / "bad.safetensors"
    save_file(state, file)
    with torch.device("meta"):
        model = nn.Linear(3, 2)
    with pytest.raises(LoaderError):
        assign_checkpoint(model, file)
    assert all(p.is_meta for p in model.parameters())


def test_buffer_and_unregistered_meta_rejected(tmp_path: Path) -> None:
    with torch.device("meta"):
        model = nn.Linear(3, 2)
        model.register_buffer("nonpersistent", torch.ones(1), persistent=False)
    with pytest.raises(LoaderError, match="buffers"):
        assign_checkpoint(model, tmp_path / "never-read")
    plain = nn.Linear(3, 2)
    plain.hidden = torch.empty(1, device="meta")
    with pytest.raises(LoaderError, match="attribute"):
        assert_no_meta(plain)


def test_tiny_official_architecture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Avoid upstream package initializer importing T5's CUDA default argument.
    # Real pinned model_scail2.py and relative attention.py remain unchanged.
    spec = importlib.util.find_spec("wan")
    assert spec is not None and spec.submodule_search_locations is not None
    package_root = Path(next(iter(spec.submodule_search_locations)))
    for name, location in (("wan", package_root), ("wan.modules", package_root / "modules")):
        package = ModuleType(name)
        package.__path__ = [str(location)]
        monkeypatch.setitem(sys.modules, name, package)
    from wan.modules.model_scail2 import SCAIL2Model
    torch.manual_seed(20261022)
    original = SCAIL2Model(model_type="i2v", dim=128, ffn_dim=256, num_heads=1, num_layers=1, freq_dim=32)
    original.save_config(tmp_path)
    file = tmp_path / "official-tiny.safetensors"
    save_file(original.state_dict(), file)
    monkeypatch.setenv("B007E_LOADER_REPORT", str(tmp_path / "loader-report.json"))
    phases: list[str] = []
    mixed = load_model(str(tmp_path / "config.json"), str(file), phases.append)
    assert isinstance(mixed, SCAIL2Model)
    assert set(mixed.state_dict()) == set(original.state_dict())
    for name, tensor in original.state_dict().items():
        assert torch.equal(mixed.state_dict()[name], tensor.to(parameter_dtype(name)))
    assert torch.equal(mixed.freqs, original.freqs)
    assert_no_meta(mixed)
    assert phases[-1] == "dit_loader_complete_cpu"
    assert mixed.img_emb.proj[0].weight.dtype == mixed.img_emb.proj[4].weight.dtype == torch.float32
    with torch.no_grad(), torch.autocast("cpu", dtype=torch.bfloat16):
        image = mixed.img_emb(torch.randn(1, 4, 1280))
    with torch.no_grad():
        time = mixed.time_embedding(torch.randn(1, 32))
        projected = mixed.time_projection(time)
        head = mixed.head(torch.randn(1, 4, 128), time)
    assert all(bool(torch.isfinite(value).all()) for value in (image, time, projected, head))
