"""MakeMemeImageEmbed: DINOv2 image embeddings for appearance-similarity clustering.

make_meme.pipelines.photos clusters detected subjects (dogs, people, ...) into
identities by appearance. A raw HSV colour histogram alone is too weak for
this on real photos (confirmed via live testing: two photos of the same dog
can be *farther* apart in histogram space than two photos of two different
dogs, once lighting/pose/background vary realistically). This node runs
facebook/dinov2-small (Apache-2.0, ~86M params) -- a self-supervised vision
transformer whose CLS token is a strong general-purpose appearance embedding
-- and returns one L2-normalized 384-d vector per input image.

Runs inside ComfyUI, not the make-meme MCP process (which stays torch-free):
``transformers``/``torch`` are imported lazily so this module -- and the rest
of the make_meme_nodes pack -- still loads fine wherever they're missing; the
node itself raises a clear, actionable error only when actually invoked
without them.
"""

from __future__ import annotations

import logging
from pathlib import Path

from PIL import Image

log = logging.getLogger("make_meme_nodes")

MODEL_ID = "facebook/dinov2-small"
EMBED_DIM = 384
_NEUTRAL_GREY = (128, 128, 128)

# Lazily-initialized, process-wide: loading dinov2-small per call would be far too slow.
_model = None
_processor = None
_device = None


def _load_model():
    global _model, _processor, _device
    if _model is not None:
        return _model, _processor, _device

    try:
        import torch
        from transformers import AutoImageProcessor, AutoModel
    except ImportError as e:
        raise RuntimeError(
            "MakeMemeImageEmbed requires 'transformers' (and torch) in ComfyUI's own "
            "Python environment. Install it there, e.g. "
            "`<ComfyUI venv>/bin/pip install transformers`."
        ) from e

    try:
        from comfy import model_management

        device = model_management.get_torch_device()
    except ImportError:
        device = torch.device("cpu")

    cache_dir = _embeddings_cache_dir()
    processor = AutoImageProcessor.from_pretrained(MODEL_ID, cache_dir=cache_dir)
    model = AutoModel.from_pretrained(MODEL_ID, cache_dir=cache_dir)
    # fp32 everywhere: MPS has known fp16 numerical issues for some ops, and dinov2-small
    # is tiny enough (~86M params) that fp32 costs nothing meaningful on any device.
    model = model.to(device=device, dtype=torch.float32)
    model.eval()

    _model, _processor, _device = model, processor, device
    return _model, _processor, _device


def _embeddings_cache_dir() -> str | None:
    """ComfyUI's models/embeddings/dinov2-small, if ComfyUI's folder_paths is available;
    None (transformers' own default HF cache) otherwise."""

    try:
        import folder_paths  # type: ignore[import-not-found]

        dirs = folder_paths.get_folder_paths("embeddings")
    except Exception:  # noqa: BLE001 - any lookup failure just falls back to the HF default cache
        return None
    if not dirs:
        return None
    return str(Path(dirs[0]) / "dinov2-small")


def _tensor_to_pil(image_tensor) -> list[Image.Image]:
    """ComfyUI IMAGE tensors are (batch, H, W, 3) float32 in 0..1."""

    import numpy as np

    arr = (image_tensor.clamp(0, 1).cpu().numpy() * 255.0).astype(np.uint8)
    return [Image.fromarray(frame, mode="RGB") for frame in arr]


def _composite_on_grey(images: list[Image.Image], mask_tensor) -> list[Image.Image]:
    """Composite each image onto a neutral grey background using ``mask_tensor``
    (ComfyUI MASK: (batch, H, W) float32 in 0..1, 1 = keep the subject)."""

    import numpy as np

    mask_arr = (mask_tensor.clamp(0, 1).cpu().numpy() * 255.0).astype(np.uint8)
    out = []
    for img, m in zip(images, mask_arr, strict=False):
        mask_img = Image.fromarray(m, mode="L").resize(img.size)
        grey = Image.new("RGB", img.size, _NEUTRAL_GREY)
        grey.paste(img, mask=mask_img)
        out.append(grey)
    return out


class MakeMemeImageEmbed:
    """L2-normalized DINOv2-small CLS-token embedding per input image (384-d each)."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {"image": ("IMAGE", {})},
            "optional": {"mask": ("MASK", {})},
        }

    RETURN_TYPES = ()
    FUNCTION = "embed"
    CATEGORY = "make-meme"
    OUTPUT_NODE = True

    def embed(self, image, mask=None):
        import torch

        model, processor, device = _load_model()

        images = _tensor_to_pil(image)
        if mask is not None:
            images = _composite_on_grey(images, mask)

        inputs = processor(images=images, return_tensors="pt")
        inputs = {k: v.to(device=device) for k, v in inputs.items()}
        with torch.no_grad():
            outputs = model(**inputs)
        cls_tokens = outputs.last_hidden_state[:, 0, :]  # (batch, EMBED_DIM)
        normalized = torch.nn.functional.normalize(cls_tokens, p=2, dim=-1)
        embeddings = normalized.to(torch.float32).cpu().tolist()
        return {"ui": {"embeddings": embeddings}}
