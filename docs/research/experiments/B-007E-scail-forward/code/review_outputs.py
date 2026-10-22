"""Offline private review artifacts. No retiming, model, interpolation or warp.

CLI: python review_outputs.py RAW_TENSOR OUTPUT SOURCE MASK REFERENCE PRIVATE_REVIEW_DIR
Run only after the generated video is complete. Sheets are visual-review aids,
not automated quality acceptance. Each clip must contain exactly 17 frames.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Final

import torch
from PIL import Image, ImageDraw, ImageOps

COUNT: Final = 17
CELL: Final = (280, 220)


def extract(video: Path, destination: Path) -> list[Path]:
    """Decode all frames without imposing fps or changing source timing."""
    destination.mkdir(parents=True, exist_ok=False)
    subprocess.run(["ffmpeg", "-v", "error", "-i", str(video), "-fps_mode", "passthrough",
                    "-start_number", "0", str(destination / "%03d.png")], check=True)
    frames = sorted(destination.glob("*.png"))
    if len(frames) != COUNT:
        raise RuntimeError(f"Expected {COUNT} frames, got {len(frames)}")
    return frames


def panel(sheet: Image.Image, path: Path, x: int, y: int, label: str) -> None:
    """Fit complete canvas for display; no subject-dependent crop or zoom."""
    with Image.open(path) as source:
        preview = ImageOps.contain(source.convert("RGB"), (CELL[0], CELL[1] - 22))
    sheet.paste(preview, (x + (CELL[0] - preview.width) // 2, y + 22))
    ImageDraw.Draw(sheet).text((x + 3, y + 3), label, fill="white")


def main(arguments: list[str]) -> None:
    raw_tensor, output, source, mask, reference, review = map(Path, arguments)
    review.mkdir(parents=True, exist_ok=False)
    records = {}
    sequences = {}
    for name, path in (("output", output), ("source", source), ("mask", mask)):
        probe = subprocess.check_output(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
            "-show_entries", "stream=width,height,avg_frame_rate,nb_read_frames,duration", "-of", "json", str(path)])
        records[name] = {"file_sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "probe": json.loads(probe)}
        if name == "output":
            tensor = torch.load(raw_tensor, map_location="cpu", weights_only=True)
            if not isinstance(tensor, torch.Tensor) or tensor.ndim != 4 or tensor.shape[:2] != (3, COUNT):
                raise RuntimeError("Expected raw model output tensor [3,17,H,W]")
            if not bool(torch.isfinite(tensor).all()):
                raise RuntimeError("Raw output has nonfinite values")
            destination = review / name
            destination.mkdir(exist_ok=False)
            pixels = ((tensor.float().clamp(-1, 1) + 1) * 127.5).round().to(torch.uint8).permute(1, 2, 3, 0).numpy()
            sequences[name] = []
            for index, frame in enumerate(pixels):
                target = destination / f"{index:03d}.png"
                Image.fromarray(frame).save(target)
                sequences[name].append(target)
            records[name]["raw_sha256"] = hashlib.sha256(raw_tensor.read_bytes()).hexdigest()
            records[name]["png_source"] = "raw tensor [-1,1] to RGB uint8, round; not lossy MP4 decode"
        else:
            sequences[name] = extract(path, review / name)
    records["reference"] = {"sha256": hashlib.sha256(reference.read_bytes()).hexdigest()}
    for start in (0, 9):
        indices = list(range(start, min(start + 9, COUNT)))
        sheet = Image.new("RGB", (CELL[0] * 4, CELL[1] * len(indices)), (24, 24, 24))
        for row, index in enumerate(indices):
            for column, name in enumerate(("source", "mask", "output")):
                panel(sheet, sequences[name][index], column * CELL[0], row * CELL[1], f"{name} f{index}")
            panel(sheet, reference, 3 * CELL[0], row * CELL[1], "reference (static)")
        sheet.save(review / f"comparison-{start:02d}.png")
    (review / "review_manifest.json").write_text(json.dumps({"files": records,
        "temporal_quality": "UNVERIFIED", "method": "All17 frames decoded, full-canvas display fit only; no acceptance metric"}, indent=2) + "\n")


if __name__ == "__main__":
    if len(sys.argv) != 7:
        raise SystemExit("Usage: review_outputs.py RAW_TENSOR OUTPUT SOURCE MASK REFERENCE PRIVATE_REVIEW_DIR")
    main(sys.argv[1:])
