"""Hardware profile detection and the CUDA torch source (no GPU needed: nvidia-smi is faked)."""

from __future__ import annotations

import subprocess
import types

import pytest

from make_meme import installer


def _fake_smi(monkeypatch, output: str, *, system: str = "linux", machine: str = "aarch64", ram_gib: int = 128):
    monkeypatch.setattr(installer.sys, "platform", system)
    monkeypatch.setattr(installer.platform, "machine", lambda: machine)
    monkeypatch.setattr(installer.shutil, "which", lambda name: "/usr/bin/nvidia-smi" if name == "nvidia-smi" else None)
    monkeypatch.setattr(installer.subprocess, "run",
                        lambda *a, **k: types.SimpleNamespace(stdout=output, returncode=0))
    monkeypatch.setattr(installer, "_system_memory_mib", lambda: ram_gib * 1024)


@pytest.mark.parametrize("output,expected", [
    ("[N/A]\n", "cuda"),      # DGX Spark / GB10: unified memory, nvidia-smi can't report it
    ("24576\n", "cuda"),      # RTX 4090
    ("15360\n", "cuda_lowvram"),  # T4
])
def test_detect_profile(monkeypatch, output, expected):
    _fake_smi(monkeypatch, output)
    assert installer.detect_profile() == expected


def test_small_unified_memory_board_is_lowvram(monkeypatch):
    _fake_smi(monkeypatch, "[N/A]\n", ram_gib=8)  # e.g. a Jetson with 8 GB
    assert installer.detect_profile() == "cuda_lowvram"


def test_nvidia_smi_failure_is_lowvram(monkeypatch):
    _fake_smi(monkeypatch, "")

    def boom(*a, **k):
        raise subprocess.CalledProcessError(1, "nvidia-smi")

    monkeypatch.setattr(installer.subprocess, "run", boom)
    assert installer.detect_profile() == "cuda_lowvram"


def test_torch_index_only_for_linux_arm_with_nvidia(monkeypatch):
    monkeypatch.delenv("MAKE_MEME_TORCH_INDEX", raising=False)
    _fake_smi(monkeypatch, "[N/A]")
    assert installer.torch_index_url() == installer.DEFAULT_CUDA_TORCH_INDEX
    _fake_smi(monkeypatch, "24576", machine="x86_64")
    assert installer.torch_index_url() is None  # PyPI's x86_64 wheels already ship CUDA
    monkeypatch.setenv("MAKE_MEME_TORCH_INDEX", "https://download.pytorch.org/whl/cu130")
    assert installer.torch_index_url().endswith("cu130")


def test_drop_file_cache_is_harmless(tmp_path):
    f = tmp_path / "model.safetensors"
    f.write_bytes(b"x" * 1024)
    installer.drop_file_cache(f)  # evicts from the page cache on Linux; no-op elsewhere
    installer.drop_file_cache(tmp_path / "missing.bin")  # never raises
    assert f.read_bytes() == b"x" * 1024


def test_companion_drop_cache_walks_model_files(tmp_path):
    import importlib.util
    from pathlib import Path

    # Load cache.py on its own: the pack's __init__ imports torch (only present inside ComfyUI).
    path = Path(__file__).resolve().parents[1] / "src/make_meme/comfy_nodes/make_meme_nodes/cache.py"
    spec = importlib.util.spec_from_file_location("mm_cache", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    drop_file_cache = mod.drop_file_cache

    (tmp_path / "diffusion_models").mkdir()
    (tmp_path / "diffusion_models" / "big.gguf").write_bytes(b"\0" * (2 << 20))
    (tmp_path / "tiny.txt").write_text("skip me")
    result = drop_file_cache([tmp_path])
    if result["supported"]:
        assert result["files"] == 1 and result["bytes"] == 2 << 20
