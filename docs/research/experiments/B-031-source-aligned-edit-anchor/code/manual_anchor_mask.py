# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "pillow"]
# ///
# Run: python manual_anchor_mask.py A0.png INPUTS_DIR
"""Rasterize recorded manual A0 polygon; preserve interior RGB without retouching."""
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageDraw


def digest(path: Path) -> str:
    """Return SHA256 of an image or small audit record."""
    return sha256(path.read_bytes()).hexdigest()


def main() -> None:
    """Save exact-interior reference and categorical RED/BLACK semantic mask."""
    anchor, out = map(Path, sys.argv[1:])
    polygon = json.loads((out / "polygon.json").read_text())
    points = [tuple(point) for point in polygon["polygon_xy"]]
    with Image.open(anchor) as opened:
        rgb = opened.convert("RGB")
    assert rgb.size == (896, 512), "polygon uses original A0 coordinates"
    support_image = Image.new("L", rgb.size, 0)
    ImageDraw.Draw(support_image).polygon(points, fill=255)
    support = np.asarray(support_image) == 255
    original = np.asarray(rgb)
    reference = original.copy()
    reference[~support] = 128
    semantic = np.zeros_like(original)
    semantic[support] = (255, 0, 0)
    outputs = {
        "reference.png": Image.fromarray(reference),
        "reference-mask.png": Image.fromarray(semantic),
        "support.png": support_image,
    }
    for name, image in outputs.items():
        target = out / name
        assert not target.exists(), f"refuse overwrite: {name}"
        image.save(target)
    preview = rgb.copy()
    ImageDraw.Draw(preview).line(points + points[:1], fill=(0, 255, 0), width=1)
    preview.save(out / "polygon-preview.png")
    with Image.open(out / "reference.png") as check:
        actual = np.asarray(check)
        assert np.array_equal(actual[support], original[support])
        assert np.all(actual[~support] == 128)
    with Image.open(out / "reference-mask.png") as check:
        actual_mask = np.asarray(check)
        assert np.array_equal(actual_mask, semantic)
    ys, xs = np.where(support)
    end = datetime.now(timezone.utc)
    start = datetime.fromisoformat(polygon["started_utc"])
    elapsed = (end - start).total_seconds()
    assert elapsed <= 1800, "manual mask time budget exceeded"
    receipt = {
        "task_id": "vehicle", "reference_id": "R1",
        "method": "manual actual generated A0 polygon", "gt_mask_reused": False,
        "a0_sha256": digest(anchor), "polygon_sha256": digest(out / "polygon.json"),
        "code_sha256": digest(Path(__file__)), "canvas_wh": list(rgb.size),
        "support_area": int(support.sum()),
        "bbox_xyxy_exclusive": [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1],
        "subject_rgb_exact": True, "outside_rgb_constant": [128, 128, 128],
        "semantic": "RED target / BLACK background", "shadow_included": False,
        "started_utc": polygon["started_utc"], "completed_utc": end.isoformat(),
        "elapsed_seconds": elapsed, "uncertainty": polygon["uncertainty"],
        "files": {name: {"sha256": digest(out / name), "bytes": (out / name).stat().st_size}
                  for name in outputs},
        "generation_suitability": "parent review separate; not inferred from raster checks",
    }
    (out / "mask-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
