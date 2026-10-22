# /// script
# dependencies = ["Pillow", "numpy"]
# ///
# Run after outputs exist: python3 tools/review_outputs.py B004_ROOT B001_ROOT
"""CPU-only B004 review; root supplies byte-identical reused R-bg folders."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Final

import numpy as np
from PIL import Image, ImageDraw, ImageOps

SEEDS: Final = (20261022, 20261023)
KINDS: Final = ("R-bg", "R-gray")
SELECTED: Final = (0, 4, 8, 12, 16)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def probe(path: Path) -> str:
    """Read existing encoded frame count and timebase with ffprobe."""
    return subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
                           "-show_entries", "stream=width,height,avg_frame_rate,nb_read_frames,duration",
                           "-of", "json", str(path)], check=True, capture_output=True,
                          text=True, timeout=30).stdout


def tile(canvas: Image.Image, path: Path, placement: tuple[int, int, str]) -> None:
    """Display the full canvas uniformly; show missing data explicitly."""
    x, y, label = placement
    draw = ImageDraw.Draw(canvas)
    draw.text((x + 6, y + 6), label, fill="white")
    if path.exists():
        with Image.open(path) as image:
            thumbnail = ImageOps.contain(image.convert("RGB"), (384, 216), Image.Resampling.LANCZOS)
        canvas.paste(thumbnail, (x + (384 - thumbnail.width) // 2, y + 24 + (216 - thumbnail.height) // 2))
    else:
        draw.text((x + 25, y + 110), "NOT_RUN / frame unavailable", fill="#ff8080")


def main() -> None:
    root, previous = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
    out = root / "outputs/review"
    out.mkdir(parents=True, exist_ok=True)
    source = previous / "inputs/lab-single/source"
    source_frames = [source / f"{i:03d}.png" for i in range(17)]
    sheet = Image.new("RGB", (1920, 1200), "#202020")
    for column, frame in enumerate(SELECTED):
        tile(sheet, source_frames[frame], (column * 384, 0, f"SOURCE f{frame} (not Lab ground truth)"))
    manifest = {"qualitative_quality": "NOT_EVALUATED", "temporal_quality": "UNVERIFIED",
                "source_frames": [{"frame": i, "sha256": sha(p)} for i, p in enumerate(source_frames) if p.exists()],
                "runs": [], "comparisons": []}
    for seed_index, seed in enumerate(SEEDS):
        folders = [root / "outputs" / f"{kind}-{seed}" for kind in KINDS]
        for kind_index, (kind, folder) in enumerate(zip(KINDS, folders, strict=True)):
            frames = [folder / f"output-{i:03d}.png" for i in range(17)]
            complete = all(path.exists() for path in frames)
            record = {"condition": kind, "seed": seed, "folder": str(folder), "reused_B003_C_real": kind == "R-bg", "status": "OUTPUTS_PRESENT" if complete else "NOT_RUN",
                      "missing_frames": [i for i, path in enumerate(frames) if not path.exists()],
                      "frame_hashes": [{"frame": i, "sha256": sha(path)} for i, path in enumerate(frames) if path.exists()]}
            all_frames = Image.new("RGB", (1920, 960), "#202020")
            for i, path in enumerate(frames):
                tile(all_frames, path, ((i % 5) * 384, (i // 5) * 240, f"{kind} seed={seed} f{i}"))
            all_frames.save(out / f"{kind}-{seed}-all17.jpg", quality=94)
            for column, frame in enumerate(SELECTED):
                tile(sheet, frames[frame], (column * 384, (1 + seed_index * 2 + kind_index) * 240, f"{kind} seed={seed} f{frame}"))
            if complete:
                arrays = []
                for path in frames:
                    with Image.open(path) as image:
                        arrays.append(np.asarray(image.convert("RGB"), dtype=np.float32))
                record["consecutive_rgb_mae_0_255"] = [float(np.abs(arrays[i + 1] - arrays[i]).mean()) for i in range(16)]
                record["metric_limit"] = "Descriptive wholeframe pixel change; smaller is not necessarily better. Not identity/motion quality or PSNR."
            video = folder / "result.mp4"
            record["video"] = {"sha256": sha(video), "ffprobe": json.loads(probe(video))} if video.exists() else {"status": "NOT_RUN"}
            manifest["runs"].append(record)
        ready = all(path.exists() for path in source_frames) and all((folder / f"output-{i:03d}.png").exists() for folder in folders for i in range(17))
        if ready:
            destination = out / f"source-Rbg-Rgray-{seed}-24fps.mp4"
            command = ["ffmpeg", "-y", "-v", "error", "-framerate", "24", "-start_number", "0", "-i", str(source / "%03d.png")]
            for folder in folders:
                command += ["-framerate", "24", "-start_number", "0", "-i", str(folder / "output-%03d.png")]
            command += ["-filter_complex", "[0:v][1:v][2:v]hstack=inputs=3[v]", "-map", "[v]", "-frames:v", "17",
                        "-fps_mode", "passthrough", "-an", "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", str(destination)]
            subprocess.run(command, check=True, timeout=120)
            metadata = json.loads(probe(destination))
            stream = metadata["streams"][0]
            assert stream["avg_frame_rate"] == "24/1" and int(stream["nb_read_frames"]) == 17
            assert abs(float(stream["duration"]) - 17/24) < 1e-5
            manifest["comparisons"].append({"seed": seed, "status": "ENCODED", "layout": "source|R-bg|R-gray",
                                            "command": command, "sha256": sha(destination), "ffprobe": metadata})
        else:
            manifest["comparisons"].append({"seed": seed, "status": "NOT_RUN", "reason": "Missing frames; no substitution."})
    sheet.save(out / "source-all-four-selected.jpg", quality=94)
    manifest["artifact_hashes"] = [{"path": str(path.relative_to(root)), "sha256": sha(path), "bytes": path.stat().st_size}
                                  for path in sorted(out.iterdir()) if path.is_file() and path.name != "summary.json"]
    (out / "summary.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print("Private CPU review artifacts created. Actual visual judgment remains separate.")


if __name__ == "__main__":
    main()
