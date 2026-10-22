# /// script
# dependencies = ["Pillow", "numpy"]
# ///
# Run: python3 tools/review_outputs.py /absolute/B002/root /absolute/B001/root
"""Private CPU evidence sheets/encoding from existing frames; no model or inference."""
from pathlib import Path
import hashlib
import json
import random
import subprocess
import sys
from typing import Final

import numpy as np
from PIL import Image, ImageDraw, ImageOps

SEEDS: Final = (20261022, 20261023)
KINDS: Final = ("R", "R-bg", "P")
SELECTED: Final = (0, 4, 8, 12, 16)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def probe(path: Path) -> str:
    """Return raw ffprobe JSON, avoiding assumptions about execution quality."""
    result = subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
                             "-show_entries", "stream=width,height,avg_frame_rate,nb_read_frames,duration",
                             "-of", "json", str(path)], check=True, capture_output=True, text=True, timeout=30)
    return result.stdout


def draw_tile(canvas: Image.Image, path: Path, placement: tuple[int, int, str]) -> None:
    """Uniform full-canvas display; missing frames remain visibly NOT_RUN."""
    x, y, label = placement
    draw = ImageDraw.Draw(canvas)
    draw.text((x + 5, y + 6), label, fill="white")
    if path.exists():
        with Image.open(path) as original:
            tile = ImageOps.contain(original.convert("RGB"), (384, 216), Image.Resampling.LANCZOS)
        canvas.paste(tile, (x + (384 - tile.width) // 2, y + 24 + (216 - tile.height) // 2))
    else:
        draw.text((x + 30, y + 100), "NOT_RUN / unavailable frame", fill="#ff8080")


def main() -> None:
    """Build evidence only; temporal and qualitative acceptance remain unverified."""
    root = Path(sys.argv[1]).resolve()
    previous = Path(sys.argv[2]).resolve()
    out = root / "outputs/review"
    out.mkdir(parents=True, exist_ok=True)
    runs = {(kind, seed): root / "outputs" / f"{kind}-{seed}" for seed in SEEDS for kind in KINDS}
    runs[("R", 20261022)] = previous / "experiments/vace_baseline/lab-single-before"
    overview = Image.new("RGB", (1920, 6 * 240), "#202020")
    blinded = Image.new("RGB", (1920, 6 * 240), "#202020")
    rng = random.Random(20261022002)
    blind_keys = {}
    report = {"qualitative_quality": "NOT_EVALUATED", "temporal_quality": "UNVERIFIED", "runs": [], "comparisons": []}
    for seed_index, seed in enumerate(SEEDS):
        order = list(KINDS)
        rng.shuffle(order)
        blind_keys[f"seed{seed_index + 1}"] = {chr(65 + i): kind for i, kind in enumerate(order)}
        for kind_index, kind in enumerate(KINDS):
            folder = runs[(kind, seed)]
            frames = [folder / f"output-{i:03d}.png" for i in range(17)]
            available = [path for path in frames if path.exists()]
            complete = len(available) == 17
            record = {"kind": kind, "seed": seed, "folder": str(folder), "reused_B001": kind == "R" and seed == 20261022,
                      "status": "OUTPUTS_PRESENT" if complete else "NOT_RUN", "available_frames": len(available),
                      "missing_frames": [i for i, path in enumerate(frames) if not path.exists()],
                      "frame_hashes": [{"frame": i, "sha256": sha(path)} for i, path in enumerate(frames) if path.exists()]}
            sheet = Image.new("RGB", (1920, 4 * 240), "#202020")
            for i, path in enumerate(frames):
                draw_tile(sheet, path, ((i % 5) * 384, (i // 5) * 240, f"{kind} seed={seed} f{i}"))
            sheet.save(out / f"{kind}-{seed}-all17.jpg", quality=94)
            for column, i in enumerate(SELECTED):
                draw_tile(overview, frames[i], (column * 384, (seed_index * 3 + kind_index) * 240, f"{kind} seed={seed} f{i}"))
                blind_index = order.index(kind)
                draw_tile(blinded, frames[i], (column * 384, (seed_index * 3 + blind_index) * 240, f"Seed {seed_index + 1} candidate {chr(65 + blind_index)} f{i}"))
            if complete:
                values = []
                for path in frames:
                    with Image.open(path) as image:
                        values.append(np.asarray(image.convert("RGB"), dtype=np.float32))
                record["consecutive_frame_rgb_mae_0_255"] = [float(np.abs(values[i + 1] - values[i]).mean()) for i in range(16)]
                record["metric_limit"] = "Wholeframe pixel change only; low is not better, and this is not identity/motion/quality acceptance."
            video = folder / "result.mp4"
            if video.exists():
                record["video"] = {"sha256": sha(video), "ffprobe": json.loads(probe(video))}
            else:
                record["video"] = {"status": "NOT_RUN"}
            report["runs"].append(record)
        source = previous / "inputs/lab-single/source"
        folders = [runs[(kind, seed)] for kind in KINDS]
        ready = all((source / f"{i:03d}.png").exists() for i in range(17)) and all(
            (folder / f"output-{i:03d}.png").exists() for folder in folders for i in range(17))
        if ready:
            command = ["ffmpeg", "-y", "-v", "error", "-framerate", "24", "-start_number", "0", "-i", str(source / "%03d.png")]
            for folder in folders:
                command += ["-framerate", "24", "-start_number", "0", "-i", str(folder / "output-%03d.png")]
            destination = out / f"source-R-Rbg-P-{seed}-24fps.mp4"
            command += ["-filter_complex", "[0:v][1:v][2:v][3:v]hstack=inputs=4[v]", "-map", "[v]",
                        "-frames:v", "17", "-fps_mode", "passthrough", "-an", "-c:v", "libx264", "-crf", "18",
                        "-pix_fmt", "yuv420p", str(destination)]
            subprocess.run(command, check=True, timeout=120)
            metadata = json.loads(probe(destination))
            stream = metadata["streams"][0]
            assert stream["avg_frame_rate"] == "24/1" and int(stream["nb_read_frames"]) == 17
            assert abs(float(stream["duration"]) - 17/24) < 1e-5
            report["comparisons"].append({"seed": seed, "status": "ENCODED", "layout": "source|R|R-bg|P",
                                           "command": command, "sha256": sha(destination), "ffprobe": metadata})
        else:
            report["comparisons"].append({"seed": seed, "status": "NOT_RUN", "reason": "Missing source or generated frames; no substitution."})
    overview.save(out / "all-six-selected.jpg", quality=94)
    blinded.save(out / "blind-six-selected.jpg", quality=94)
    # Keep the key separate: review blind sheet before opening key/labelled evidence.
    (root / "reports/private-blind-key.json").write_text(json.dumps({"randomization_seed": 20261022002, "mapping": blind_keys,
        "limitation": "Label masking only. Prior exposure to old R means this is not a human-blind randomized trial."}, indent=2) + "\n")
    report["artifact_hashes"] = [{"file": str(path.relative_to(root)), "sha256": sha(path), "bytes": path.stat().st_size}
                                  for path in sorted(out.iterdir()) if path.is_file() and path.name != "summary.json"]
    (out / "summary.json").write_text(json.dumps(report, indent=2) + "\n")
    print("Private review artifacts ready. Inspect blind-six-selected.jpg first; no quality judgment made by script.")


if __name__ == "__main__":
    main()
