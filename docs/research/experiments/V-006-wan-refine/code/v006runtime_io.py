# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# Run only through wan_refine.py in the existing research environment.
"""Atomic runtime evidence and raw video persistence."""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, TypeAlias

if TYPE_CHECKING:
    import torch
    from PIL import Image
    from v006runtime_config import Runtime

JsonValue: TypeAlias = str | int | float | bool | None | list["JsonValue"] | dict[str, "JsonValue"]


def atomic_json(path: Path, value: JsonValue) -> None:
    """Replace a receipt atomically without exposing a partial JSON document."""
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")
    temporary.replace(path)


def tensor_summary(tensor: torch.Tensor) -> dict[str, JsonValue]:
    """Record actual shape, dtype and exact bytes; no extra model forward."""
    import torch
    cpu = tensor.detach().to(device="cpu").contiguous()
    return {"shape": list(cpu.shape), "dtype": str(cpu.dtype),
            "sha256": hashlib.sha256(cpu.view(torch.uint8).numpy().tobytes()).hexdigest(),
            "finite": bool(torch.isfinite(cpu).all())}


def save_tensor(tensor: torch.Tensor, path: Path) -> None:
    """Keep a recoverable atomic tensor file and verify exact CPU readback."""
    import torch
    cpu = tensor.detach().cpu().contiguous()
    temporary = path.with_suffix(".tmp")
    torch.save(cpu, temporary)
    temporary.replace(path)
    restored = torch.load(path, map_location="cpu", weights_only=True)
    assert torch.equal(cpu, restored)
    atomic_json(path.with_suffix(".json"), {"readback_exact": True, **tensor_summary(cpu)})


def save_video(images: list[Image.Image], runtime: Runtime) -> None:
    """Preserve lossless decoded frames and an independently decodable preview."""
    assert len(images) == runtime.frames
    folder = runtime.output / "frames"
    folder.mkdir(exist_ok=False)
    for index, image in enumerate(images):
        assert image.mode == "RGB" and image.size == (runtime.width, runtime.height)
        image.save(folder / f"{index:03d}.png")
    subprocess.run([str(runtime.ffmpeg), "-v", "error", "-n", "-framerate",
                    str(runtime.fps), "-i", str(folder / "%03d.png"), "-c:v",
                    "libx264", "-crf", "18", "-pix_fmt", "yuv420p",
                    str(runtime.output / "output.mp4")], check=True)
    subprocess.run([str(runtime.ffmpeg), "-v", "error", "-i",
                    str(runtime.output / "output.mp4"), "-f", "null", "-"], check=True)
