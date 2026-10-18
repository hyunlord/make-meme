"""`make-meme install`: set up a ComfyUI that can run make-meme recipes.

Installs (idempotently) ComfyUI itself, each recipe's custom node packs at pinned
commits, the bundled make_meme_nodes companion pack, and the recipe's model files for
the chosen hardware profile. Works for a local Mac/Linux/Windows box or inside a free
cloud notebook (Kaggle/Colab) — see notebooks/.
"""

from __future__ import annotations

import logging
import os
import platform
import shutil
import subprocess
import sys
from importlib import resources
from pathlib import Path

import httpx

from make_meme.recipes.loader import ModelVariant, Recipe

log = logging.getLogger("make_meme.install")

COMFY_REPO = "https://github.com/comfyanonymous/ComfyUI.git"
EXTRA_COMFY_PACKAGES = ["torchaudio", "gguf"]  # WanVideoWrapper imports torchaudio; GGUF loader
# PyPI's Linux aarch64 torch wheels are CPU-only; CUDA builds come from PyTorch's index.
DEFAULT_CUDA_TORCH_INDEX = "https://download.pytorch.org/whl/cu128"


def _system_memory_mib() -> int:
    try:
        return int(os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 2**20)
    except (ValueError, OSError, AttributeError):
        return 0


def unified_memory_gpu() -> bool:
    """An NVIDIA GPU that shares system RAM (DGX Spark / GB10, Jetson): nvidia-smi can't
    report its memory."""
    if sys.platform == "darwin" or not shutil.which("nvidia-smi"):
        return False
    try:
        out = subprocess.run(["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
                             capture_output=True, text=True, check=True).stdout.split()
        int(out[0]) if out else 0
    except subprocess.CalledProcessError:
        return False
    except ValueError:
        return True
    return False


def detect_profile() -> str:
    if sys.platform == "darwin" and platform.machine() == "arm64":
        return "mps"
    if shutil.which("nvidia-smi"):
        try:
            out = subprocess.run(
                ["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
                capture_output=True, text=True, check=True,
            ).stdout.split()
            vram_mib = int(out[0]) if out else 0
        except subprocess.CalledProcessError:
            vram_mib = 0
        except ValueError:
            # "[N/A]": a unified-memory GPU (DGX Spark / GB10, Jetson) shares system RAM.
            vram_mib = _system_memory_mib()
        return "cuda" if vram_mib >= 20 * 1024 else "cuda_lowvram"
    return "cpu"


def torch_index_url() -> str | None:
    """Where to get CUDA torch for this machine (None: requirements.txt's default is fine)."""
    if override := os.environ.get("MAKE_MEME_TORCH_INDEX"):
        return override
    if sys.platform.startswith("linux") and platform.machine() in ("aarch64", "arm64") and shutil.which("nvidia-smi"):
        return DEFAULT_CUDA_TORCH_INDEX
    return None


def _run(cmd: list[str], cwd: Path | None = None) -> None:
    log.info("$ %s", " ".join(cmd))
    subprocess.run(cmd, cwd=cwd, check=True)


def comfy_python(comfy_dir: Path) -> Path:
    win = comfy_dir / ".venv" / "Scripts" / "python.exe"
    return win if win.exists() else comfy_dir / ".venv" / "bin" / "python"


def _pip_install(comfy_dir: Path, *args: str) -> None:
    py = str(comfy_python(comfy_dir))
    if shutil.which("uv"):
        _run(["uv", "pip", "install", "--python", py, *args])
    else:
        _run([py, "-m", "pip", "install", *args])


def ensure_comfyui(comfy_dir: Path, *, use_system_python: bool = False) -> None:
    if not (comfy_dir / "main.py").exists():
        comfy_dir.parent.mkdir(parents=True, exist_ok=True)
        _run(["git", "clone", "--depth", "1", COMFY_REPO, str(comfy_dir)])
    if use_system_python:
        venv = comfy_dir / ".venv"
        if not venv.exists():
            _run([sys.executable, "-m", "venv", "--system-site-packages", str(venv)])
    elif not comfy_python(comfy_dir).exists():
        if shutil.which("uv"):
            _run(["uv", "venv", "--python", "3.12", str(comfy_dir / ".venv")])
        else:
            _run([sys.executable, "-m", "venv", str(comfy_dir / ".venv")])
    if index := torch_index_url():
        _pip_install(comfy_dir, "torch", "torchvision", "torchaudio", "--index-url", index)
    _pip_install(comfy_dir, "-r", str(comfy_dir / "requirements.txt"))
    _pip_install(comfy_dir, *EXTRA_COMFY_PACKAGES)


def install_companion_nodes(comfy_dir: Path) -> Path:
    src = Path(str(resources.files("make_meme") / "comfy_nodes" / "make_meme_nodes"))
    dest = comfy_dir / "custom_nodes" / "make_meme_nodes"
    if dest.is_symlink() or dest.is_file():
        dest.unlink()
    elif dest.is_dir():
        shutil.rmtree(dest)
    shutil.copytree(src, dest, ignore=shutil.ignore_patterns("__pycache__"))
    return dest


def install_node_pack(comfy_dir: Path, repo: str, ref: str | None, pip: list[str] | None = None) -> None:
    if repo.startswith("builtin:"):
        install_companion_nodes(comfy_dir)
        return
    name = repo.rstrip("/").rsplit("/", 1)[-1].removesuffix(".git")
    dest = comfy_dir / "custom_nodes" / name
    if not dest.exists():
        _run(["git", "clone", repo, str(dest)])
    if ref:
        current = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=dest, capture_output=True, text=True, check=False
        ).stdout.strip()
        if current != ref:
            _run(["git", "fetch", "--depth", "1", "origin", ref], cwd=dest)
            _run(["git", "checkout", ref], cwd=dest)
    if pip is not None:
        if pip:
            _pip_install(comfy_dir, *pip)
        return
    req = dest / "requirements.txt"
    if req.exists():
        _pip_install(comfy_dir, "-r", str(req))


def drop_file_cache(path: Path) -> None:
    """Evict a just-downloaded file from the page cache (Linux). On unified-memory GPUs the
    cache competes with GPU allocations and isn't reclaimed by the CUDA driver."""
    if not hasattr(os, "posix_fadvise"):
        return
    try:
        fd = os.open(path, os.O_RDONLY)
        try:
            os.posix_fadvise(fd, 0, 0, os.POSIX_FADV_DONTNEED)
        finally:
            os.close(fd)
    except OSError:
        log.debug("could not drop page cache for %s", path, exc_info=True)


def download_model(comfy_dir: Path, variant: ModelVariant) -> Path:
    dest = comfy_dir / "models" / variant.dir / variant.file
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    url = f"https://huggingface.co/{variant.repo}/resolve/main/{variant.path}"
    part = dest.with_name(dest.name + ".part")
    headers = {}
    token = os.environ.get("HF_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    offset = part.stat().st_size if part.exists() else 0
    if offset:
        headers["Range"] = f"bytes={offset}-"
    log.info("downloading %s (%.1f GB) -> %s", url, variant.size_gb, dest)
    with httpx.stream("GET", url, headers=headers, follow_redirects=True, timeout=60.0) as r:
        if r.status_code == 416:  # already complete
            part.rename(dest)
            return dest
        r.raise_for_status()
        mode = "ab" if r.status_code == 206 else "wb"
        total = int(r.headers.get("content-length", 0)) + (offset if mode == "ab" else 0)
        done = offset if mode == "ab" else 0
        last_pct = -1
        with part.open(mode) as fh:
            for chunk in r.iter_bytes(chunk_size=8 << 20):
                fh.write(chunk)
                done += len(chunk)
                pct = int(done * 100 / total) if total else -1
                if pct != last_pct and pct % 5 == 0:
                    print(f"  {variant.file}: {pct}%", file=sys.stderr, flush=True)
                    last_pct = pct
    part.rename(dest)
    drop_file_cache(dest)
    return dest


def install_recipe(comfy_dir: Path, recipe: Recipe, profile: str, *, skip_models: bool = False) -> list[str]:
    notes: list[str] = []
    for pack in recipe.custom_nodes:
        install_node_pack(comfy_dir, pack.repo, pack.ref, pack.pip)
    if skip_models:
        return notes
    for model in recipe.models:
        variant = model.profiles.get(profile) or model.profiles.get("default")
        if variant is None:
            notes.append(f"{recipe.name}: no '{profile}' variant for model {model.id}; skipped")
            continue
        download_model(comfy_dir, variant)
        if "AGPL" in variant.license or "SAM" in variant.license:
            notes.append(f"{variant.file}: license {variant.license} — see README 'Model licenses'")
    return notes


# On unified memory every copy counts twice: mmap'd model files sit in the page cache next to
# their GPU copy, ComfyUI's RAM cache keeps CPU copies of models, and its pinned-memory quota
# (~90 % of RAM) plus cudaMallocAsync can fill all 128 GB in seconds on GB10
# (Comfy-Org/ComfyUI#11106). See docs/engine-setup.md for the host tuning a DGX Spark also
# needs (swap off, GPU clock cap against overcurrent power-offs).
UNIFIED_MEMORY_COMFY_ARGS = ["--disable-mmap", "--reserve-vram", "20",
                             "--disable-pinned-memory", "--disable-cuda-malloc"]
# (--cache-none was dropped again: it re-ran every loader node, reloading the 14B video model
# for every shot -- 1-2 min each -- while measured peaks left 57 GB free.)


def comfy_launch_command(comfy_dir: Path, port: int = 8188, listen: str = "127.0.0.1",
                         unified_memory: bool | None = None) -> list[str]:
    cmd = [str(comfy_python(comfy_dir)), "main.py", "--listen", listen, "--port", str(port), "--disable-auto-launch"]
    if unified_memory if unified_memory is not None else unified_memory_gpu():
        cmd += UNIFIED_MEMORY_COMFY_ARGS
    if _has_module(comfy_dir, "sageattention"):
        cmd.append("--use-sage-attention")
    return cmd


def _has_module(comfy_dir: Path, name: str) -> bool:
    py = comfy_python(comfy_dir)
    if not py.exists():
        return False
    probe = subprocess.run([str(py), "-c", f"import importlib.util,sys; sys.exit(importlib.util.find_spec({name!r}) is None)"],
                           capture_output=True, check=False)
    return probe.returncode == 0


def comfy_env(profile: str) -> dict[str, str]:
    env = dict(os.environ)
    if profile == "mps":
        env.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")
    return env
