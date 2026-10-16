"""make-meme companion ComfyUI node pack.

Installed into ComfyUI/custom_nodes by `make-meme install`. It currently carries
compatibility patches that let make-meme recipes run on Apple Silicon (MPS):

* MoCha RoPE (ComfyUI-WanVideoWrapper `mocha/nodes.py`) builds complex128 rotary
  frequencies; MPS has no float64/complex128 support. We swap in an equivalent
  real-valued (cos/sin, float32) implementation. Numerically it matches the original
  up to float32 precision and is used on every device for consistency.

Patches are applied whether WanVideoWrapper is imported before or after this pack
(ComfyUI's custom node load order is filesystem-dependent).
"""

from __future__ import annotations

import importlib.abc
import importlib.machinery
import logging
import sys

from .mocha_rope import rope_apply_mocha_real, rope_params_mocha_real

log = logging.getLogger("make_meme_nodes")

_TARGET_SUFFIX = ".mocha.nodes"
_patched: set[str] = set()


def _patch_mocha_module(module) -> None:
    name = getattr(module, "__name__", "")
    if name in _patched or not hasattr(module, "rope_apply_mocha"):
        return
    module.rope_params_mocha = rope_params_mocha_real
    module.rope_apply_mocha = rope_apply_mocha_real
    _patched.add(name)
    log.info("make-meme: patched MoCha RoPE in %s (real-valued, MPS-safe)", name)


def _patch_loaded() -> None:
    for name, module in list(sys.modules.items()):
        if name.endswith(_TARGET_SUFFIX) and module is not None:
            _patch_mocha_module(module)


class _PatchingLoader(importlib.abc.Loader):
    def __init__(self, wrapped: importlib.abc.Loader) -> None:
        self._wrapped = wrapped

    def create_module(self, spec):
        return self._wrapped.create_module(spec)

    def exec_module(self, module) -> None:
        self._wrapped.exec_module(module)
        _patch_mocha_module(module)


class _MochaFinder(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path, target=None):
        if not fullname.endswith(_TARGET_SUFFIX):
            return None
        for finder in sys.meta_path:
            if finder is self or not hasattr(finder, "find_spec"):
                continue
            spec = finder.find_spec(fullname, path, target)
            if spec is not None and spec.loader is not None:
                spec.loader = _PatchingLoader(spec.loader)
                return spec
        return None


_patch_loaded()
if not any(isinstance(f, _MochaFinder) for f in sys.meta_path):
    sys.meta_path.insert(0, _MochaFinder())

__version__ = "0.1.0"


class MakeMemeInfo:
    """Reports the companion pack version and active patches; lets make-meme detect
    the pack through /object_info."""

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {}}

    RETURN_TYPES = ("STRING",)
    FUNCTION = "info"
    CATEGORY = "make-meme"

    def info(self):
        return (f"make_meme_nodes {__version__}; patched: {sorted(_patched) or 'none'}",)


NODE_CLASS_MAPPINGS = {"MakeMemeInfo": MakeMemeInfo}
NODE_DISPLAY_NAME_MAPPINGS = {"MakeMemeInfo": "make-meme info"}
