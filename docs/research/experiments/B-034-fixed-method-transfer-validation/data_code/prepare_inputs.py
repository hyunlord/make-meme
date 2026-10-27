# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "pillow", "pydantic>=2"]
# ///
# How to run: python prepare_inputs.py RESEARCH_DOCS DAVIS_ZIP PRIVATE_ROOT
"""Prepare the two prospectively fixed B034 cases using existing CPU helpers."""
from dataclasses import asdict, dataclass
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import sys
from typing import Final
from zipfile import ZipFile

import numpy as np
from PIL import Image


@dataclass(frozen=True, slots=True)
class Case:
    alias: str
    source: str
    target: str
    target_track: int
    selected_object: str
    protected: str
    caption: str


CASES: Final = (
    Case("rigid_R1", "car-turn", "classic-car", 3, "the car on the road",
         "the mountain, meadow, trees, roadside posts, and road",
         "A car matching the reference image approaches along a curved mountain road. "
         "It grows larger and moves toward the left side of the image as it follows the bend. "
         "The mountains, meadow, trees, roadside posts and road remain in place."),
    Case("nonrigid_R1", "hike", "lady-running", 1, "the person walking on the mountain path",
         "the rocky mountain slope, path, and surrounding landscape",
         "A person matching the reference image walks toward the right along a rocky mountain path. "
         "The legs alternate steps while the body stays upright. "
         "The rocky slope, path and distant mountains remain visible."),
)


def digest(path: Path) -> str:
    """Hash a prepared artifact without modifying it."""
    return sha256(path.read_bytes()).hexdigest()


def main() -> None:
    """Reuse B027 fit/encode and B031 crop/template with explicit track selection."""
    docs, archive, root = map(Path, sys.argv[1:])
    sys.path.insert(0, str(docs / "experiments/B-027-public-reference-robustness/data_code"))
    from data_prepare import encode_verify, fit_pair, sheet
    # Avoid importing this script under its own prepare_inputs module name.
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "b031_input_contract", docs / "experiments/B-031-source-aligned-edit-anchor/code/prepare_inputs.py")
    assert spec is not None and spec.loader is not None
    prior = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = prior
    spec.loader.exec_module(prior)
    rows = []
    with ZipFile(archive) as bundle:
        for case in CASES:
            task = root / "tasks" / case.alias
            inputs = task / "inputs"
            inputs.mkdir(parents=True, exist_ok=False)
            for folder in ("source", "source-mask", "source-support", "original-source"):
                (inputs / folder).mkdir()
            frames, masks, source_records = [], [], []
            for frame in range(17):
                rgb_bytes = bundle.read(f"DAVIS/JPEGImages/480p/{case.source}/{frame:05d}.jpg")
                label_bytes = bundle.read(f"DAVIS/Annotations/480p/{case.source}/{frame:05d}.png")
                rgb = Image.open(BytesIO(rgb_bytes)).convert("RGB")
                labels = np.asarray(Image.open(BytesIO(label_bytes)))
                assert labels.ndim == 2 and np.any(labels == 1)
                image, support, geometry = fit_pair(rgb, Image.fromarray(np.uint8(labels == 1) * 255))
                selected = np.asarray(support) != 0
                semantic = np.full((*selected.shape, 3), 255, dtype=np.uint8)
                semantic[selected] = (255, 0, 0)
                mask = Image.fromarray(semantic)
                image.save(inputs / "source" / f"{frame:03d}.png")
                mask.save(inputs / "source-mask" / f"{frame:03d}.png")
                support.save(inputs / "source-support" / f"{frame:03d}.png")
                (inputs / "original-source" / f"{frame:03d}.jpg").write_bytes(rgb_bytes)
                (inputs / "original-source" / f"{frame:03d}-labels.png").write_bytes(label_bytes)
                frames.append(image)
                masks.append(mask)
                source_records.append({"frame": frame, "track": 1, "geometry": asdict(geometry),
                                       "rgb_sha256": sha256(rgb_bytes).hexdigest(),
                                       "mask_sha256": sha256(label_bytes).hexdigest(),
                                       "support_area": int(selected.sum())})
            videos = {"driver": encode_verify(frames, inputs / "driver.mp4"),
                      "driver_mask": encode_verify(masks, inputs / "driver-mask.mp4")}
            rgb_bytes = bundle.read(f"DAVIS/JPEGImages/480p/{case.target}/00000.jpg")
            label_bytes = bundle.read(f"DAVIS/Annotations/480p/{case.target}/00000.png")
            target = Image.open(BytesIO(rgb_bytes)).convert("RGB")
            labels = np.asarray(Image.open(BytesIO(label_bytes)))
            selected_labels = Image.fromarray(np.uint8(labels == case.target_track))
            crop = prior.crop_target(target, selected_labels)
            qwen = root / "qwen-inputs" / case.alias
            qwen.mkdir(parents=True, exist_ok=False)
            frames[0].save(qwen / "image1.png")
            crop.rgb.save(qwen / "image2.png")
            crop.support.save(qwen / "image2-support.png")
            (qwen / "target-native.jpg").write_bytes(rgb_bytes)
            (qwen / "target-instance-mask.png").write_bytes(label_bytes)
            (qwen / "source-native.jpg").write_bytes((inputs / "original-source/000.jpg").read_bytes())
            sheet(frames, [f"SOURCE local{i} / f{i}" for i in range(17)], task / "source-all17.jpg", 4)
            record = {**asdict(case), "case_id": case.alias, "source_track": 1,
                      "source_frames": list(range(17)), "target_frame": 0,
                      "image_order": ["image1.png", "image2.png"],
                      "prompt": prior.TEMPLATE.format(object=case.selected_object, protected=case.protected),
                      "negative": "", "source_fps": None, "preview_fps": 24,
                      "timebase_assumed": True, "canvas_wh": [896, 512],
                      "source_records": source_records, "videos": videos,
                      "target_bbox_xyxy_exclusive": crop.bbox,
                      "crop_xyxy_exclusive": crop.crop_box,
                      "target_native_wh": target.size, "target_crop_wh": crop.rgb.size,
                      "native_support_area": int(np.count_nonzero(np.asarray(crop.support))),
                      "subject_pixel_exact": True, "outside_rgb_constant": [128, 128, 128],
                      "files": {p.name: {"sha256": digest(p), "bytes": p.stat().st_size}
                                for p in sorted(qwen.iterdir())}}
            (task / "task_manifest.json").write_text(json.dumps(record, indent=2) + "\n")
            rows.append(record)
    payload = {"experiment": "B-034", "cases": rows, "image_seed": 20261026,
               "output_request_wh": [896, 512],
               "image_steps": 40, "true_cfg_scale": 4.0, "guidance_scale": 1.0,
               "negative_prompt": " ", "image_attempt_limit": 2,
               "code_sha256": digest(Path(__file__)), "new_download_bytes": 0,
               "dataset": "DAVIS-2017-trainval-480p", "license": "CC-BY-NC-4.0"}
    (root / "INPUT_CONTRACT.json").write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps({"case_count": len(rows), "input_contract_sha256": digest(root / "INPUT_CONTRACT.json")}))


if __name__ == "__main__":
    main()
