"""Private CPU review; python output_review.py RUN.json. No diffusion or interpolation.

RUN.json: {"run_id":"lab", "fps":24, "reference":"...", "reference_mask":"...",
"source_video":"...", "driving_mask_video":"...", "output_video":"...",
"destination":"...", "crops":[{"name":"head","box":[0.2,0.1,0.8,0.5]}]}.
Paths are private, absolute. Official example uses fps16; Lab uses fps24.
Crops are optional user-specified normalized rectangles, never inferred landmarks.
"""
from __future__ import annotations

import hashlib
import json
import math
import subprocess
import sys
from fractions import Fraction
from pathlib import Path
from typing import Literal

from PIL import Image, ImageDraw, ImageOps
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Crop(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    name: str = Field(pattern=r"^[a-zA-Z0-9_-]+$")
    box: tuple[float, float, float, float]

    @model_validator(mode="after")
    def valid_box(self) -> Crop:
        x0, y0, x1, y1 = self.box
        if not (0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1):
            raise ValueError("Crop must be a nonempty normalized rectangle")
        return self


class Run(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    run_id: str = Field(pattern=r"^[a-zA-Z0-9_-]+$")
    fps: Literal[16, 24]
    reference: Path
    reference_mask: Path
    source_video: Path
    driving_mask_video: Path
    output_video: Path
    destination: Path
    crops: tuple[Crop, ...] = ()


class Stream(BaseModel):
    width: int
    height: int
    avg_frame_rate: str
    nb_read_frames: str
    duration: str | None = None


class Probe(BaseModel):
    streams: list[Stream]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def probe(path: Path, fps: int) -> Probe:
    command = ["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
               "-show_entries", "stream=width,height,avg_frame_rate,nb_read_frames,duration",
               "-of", "json", str(path)]
    result = Probe.model_validate_json(subprocess.check_output(command))
    if len(result.streams) != 1:
        raise ValueError("Expected one selected video stream")
    stream = result.streams[0]
    if int(stream.nb_read_frames) != 17 or Fraction(stream.avg_frame_rate) != fps:
        raise ValueError(f"Refuse frame/time mismatch: {path.name}")
    return result


def decode(path: Path, destination: Path) -> list[Path]:
    destination.mkdir()
    subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-fps_mode", "passthrough",
                    "-start_number", "0", str(destination / "%03d.png")], check=True)
    frames = sorted(destination.glob("*.png"))
    if len(frames) != 17:
        raise ValueError("Expected all17 decoded frames; no truncation allowed")
    return frames


def load(path: Path) -> Image.Image:
    with Image.open(path) as image:
        return image.convert("RGB")


def panel(path: Path, label: str, categorical: bool = False) -> Image.Image:
    tile = Image.new("RGB", (256, 280), (28, 28, 28))
    image = load(path)
    fitted = ImageOps.contain(image, (256, 256), Image.Resampling.NEAREST if categorical else Image.Resampling.LANCZOS)
    tile.paste(fitted, ((256 - fitted.width) // 2, 24 + (256 - fitted.height) // 2))
    ImageDraw.Draw(tile).text((5, 5), label, fill="white")
    return tile


def main(config_path: Path) -> None:
    run = Run.model_validate_json(config_path.read_text())
    paths = {"reference": run.reference, "reference_mask": run.reference_mask,
             "source": run.source_video, "driving_mask": run.driving_mask_video,
             "output": run.output_video}
    before = {key: sha(path) for key, path in paths.items()}
    probes = {key: probe(paths[key], run.fps).model_dump() for key in ("source", "driving_mask", "output")}
    run.destination.mkdir(parents=True, exist_ok=False)
    decoded = {key: decode(paths[key], run.destination / key) for key in ("source", "driving_mask", "output")}
    strips = run.destination / "comparison_frames"
    strips.mkdir()
    sheet = Image.new("RGB", (1280, 17 * 280))
    for index in range(17):
        strip = Image.new("RGB", (1280, 280))
        columns = [(run.reference, "reference", False), (run.reference_mask, "reference mask", True),
                   (decoded["source"][index], "source", False),
                   (decoded["driving_mask"][index], "driving mask", True),
                   (decoded["output"][index], "actual output", False)]
        for col, (path, label, categorical) in enumerate(columns):
            strip.paste(panel(path, f"{label} f{index} t={index/run.fps:.4f}s", categorical), (col * 256, 0))
        strip.save(strips / f"{index:03d}.png")
        sheet.paste(strip, (0, index * 280))
        for crop in run.crops:
            pair = Image.new("RGB", (512, 280))
            for col, key in enumerate(("source", "output")):
                image = load(decoded[key][index])
                x0, y0, x1, y1 = crop.box
                box = (math.floor(x0*image.width), math.floor(y0*image.height),
                       math.ceil(x1*image.width), math.ceil(y1*image.height))
                cropped = image.crop(box)
                folder = run.destination / "crops" / crop.name / key
                folder.mkdir(parents=True, exist_ok=True)
                path = folder / f"{index:03d}.png"
                cropped.save(path)
                pair.paste(panel(path, f"{key} {crop.name} f{index}"), (256*col, 0))
            pair.save(run.destination / "crops" / crop.name / f"pair-{index:03d}.png")
    sheet.save(run.destination / "all17-contact.png")
    video = run.destination / "comparison.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-framerate", str(run.fps), "-i", str(strips / "%03d.png"),
                    "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", str(video)], check=True)
    comparison_probe = probe(video, run.fps)
    after = {key: sha(path) for key, path in paths.items()}
    if before != after:
        raise ValueError("Input changed during review")
    outputs = {str(p.relative_to(run.destination)): sha(p) for p in sorted(run.destination.rglob("*")) if p.is_file()}
    report = {"run_id": run.run_id, "status": "CPU_REVIEW_ARTIFACTS_CREATED", "config_sha256": sha(config_path),
              "inputs_sha256": before, "input_probes": probes, "comparison_probe": comparison_probe.model_dump(),
              "outputs_sha256": outputs, "fps": run.fps, "frame_count": 17,
              "crop_boxes": [c.model_dump() for c in run.crops],
              "display": "Fixed letterboxed tiles only; raw decoded outputs retained; no interpolation or temporal changes.",
              "temporal_quality": "UNVERIFIED", "static_quality": "NOT_REVIEWED", "encoding_is_quality_acceptance": False}
    (run.destination / "review_manifest.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
