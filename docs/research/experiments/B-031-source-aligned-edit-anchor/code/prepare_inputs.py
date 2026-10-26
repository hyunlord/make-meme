# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "pillow"]
# ///
# Run: python prepare_inputs.py B027_ROOT OUTPUT_INPUTS_ROOT PUBLIC_CONTRACT_JSON
"""Prepare B031's six native GT-bbox target crops without generation or warping."""
from dataclasses import dataclass
from hashlib import sha256
import json
from math import ceil, floor
from pathlib import Path
import shutil
import sys
from typing import Final, TypedDict

import numpy as np
from PIL import Image


@dataclass(frozen=True, slots=True)
class CropResult:
    rgb: Image.Image
    support: Image.Image
    bbox: tuple[int, int, int, int]
    crop_box: tuple[int, int, int, int]


@dataclass(frozen=True, slots=True)
class Task:
    task: str
    source: str
    source_frame: int
    target: str
    target_frames: tuple[int, int]
    selected_object: str
    protected: str


class FileReceipt(TypedDict):
    sha256: str
    bytes: int


class CaseRecord(TypedDict):
    case_id: str
    task: str
    reference_id: str
    source_sequence: str
    source_frame: int
    target_sequence: str
    target_frame: int
    track_id: int
    image_order: list[str]
    source_canvas_wh: list[int]
    target_native_wh: tuple[int, int]
    target_bbox_xyxy_exclusive: tuple[int, int, int, int]
    crop_xyxy_exclusive: tuple[int, int, int, int]
    target_crop_wh: tuple[int, int]
    native_support_area: int
    subject_pixel_exact: bool
    outside_rgb_constant: list[int]
    pre_pipeline_resize: None
    pipeline_resize: str
    prompt: str
    files: dict[str, FileReceipt]


TASKS: Final = (
    Task("animal", "dog", 0, "dog-gooses", (0, 85),
         "the large foreground dog", "the fence, bushes, and grass"),
    Task("human", "dance-twirl", 0, "dance-jump", (0, 16),
         "the foreground dancer", "all other people, the courtyard, walls, and hay bales"),
    Task("vehicle", "car-roundabout", 30, "car-shadow", (0, 39),
         "the large foreground car", "all other vehicles, buildings, monument, railings, road, and signs"),
)
TEMPLATE: Final = (
    "Replace {object} in Image1 with the target shown in Image2. "
    "Keep the selected object's pose, facing direction, location within the scene, "
    "and the camera view from Image1. Allow the target's natural body proportions. "
    "Preserve {protected}. Use Image2 for the target's visible appearance, "
    "not its pose or background. Do not leave the original selected object, "
    "duplicate the object, or add new text, logos, graphics, or decorations. "
    "Return the complete edited Image1 scene."
)


def digest(path: Path) -> str:
    """Hash a small input file without changing it."""
    return sha256(path.read_bytes()).hexdigest()


def crop_target(rgb: Image.Image, labels: Image.Image) -> CropResult:
    """Crop track1 with10% bbox width/height per side and neutralize non-support."""
    pixels = np.asarray(rgb.convert("RGB"))
    support = np.asarray(labels) == 1
    assert support.shape == pixels.shape[:2] and support.any(), "invalid track1 support"
    ys, xs = np.where(support)
    x0, y0, x1, y1 = int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1
    w, h = x1 - x0, y1 - y0
    box = (max(0, floor(x0 - 0.1 * w)), max(0, floor(y0 - 0.1 * h)),
           min(rgb.width, ceil(x1 + 0.1 * w)), min(rgb.height, ceil(y1 + 0.1 * h)))
    left, top, right, bottom = box
    cropped = pixels[top:bottom, left:right].copy()
    mask = support[top:bottom, left:right]
    cropped[~mask] = 128
    assert np.array_equal(cropped[mask], pixels[top:bottom, left:right][mask])
    assert np.all(cropped[~mask] == 128)
    return CropResult(Image.fromarray(cropped), Image.fromarray(mask.astype(np.uint8) * 255),
                      (x0, y0, x1, y1), box)


def prepare_task(root: Path, out: Path, task: Task) -> list[CaseRecord]:
    """Read one existing task and save its ordered two-image pairs with hashes."""
    original = root / "data" / "DAVIS"
    task_root = root / "tasks" / task.task
    prior = json.loads((task_root / "task_manifest.json").read_text())
    source = task_root / "inputs" / "source" / "000.png"
    source_native = original / "JPEGImages" / "480p" / task.source / f"{task.source_frame:05d}.jpg"
    assert digest(source_native) == prior["source_records"][0]["hashes"]["rgb_sha256"]
    with Image.open(source) as src:
        assert src.size == (896, 512) and src.mode == "RGB"
    records: list[CaseRecord] = []
    for i, frame in enumerate(task.target_frames, 1):
        case = f"{task.task}_R{i}"
        case_dir = out / case
        case_dir.mkdir(parents=True, exist_ok=False)
        native = original / "JPEGImages" / "480p" / task.target / f"{frame:05d}.jpg"
        mask = original / "Annotations" / "480p" / task.target / f"{frame:05d}.png"
        expected = prior["target_refs"][i - 1]["hashes"]
        assert digest(native) == expected["rgb_sha256"]
        assert digest(mask) == expected["indexed_mask_sha256"]
        with Image.open(native) as rgb, Image.open(mask) as labels:
            result = crop_target(rgb, labels)
            native_size = rgb.size
        copies = {"image1.png": source, "source-native.jpg": source_native,
                  "target-native.jpg": native, "target-instance-mask.png": mask}
        for name, origin in copies.items():
            shutil.copyfile(origin, case_dir / name)
        result.rgb.save(case_dir / "image2.png")
        result.support.save(case_dir / "image2-support.png")
        records.append({
            "case_id": case, "task": task.task, "reference_id": f"R{i}",
            "source_sequence": task.source, "source_frame": task.source_frame,
            "target_sequence": task.target, "target_frame": frame, "track_id": 1,
            "image_order": ["image1.png", "image2.png"],
            "source_canvas_wh": [896, 512], "target_native_wh": native_size,
            "target_bbox_xyxy_exclusive": result.bbox,
            "crop_xyxy_exclusive": result.crop_box, "target_crop_wh": result.rgb.size,
            "native_support_area": int((np.asarray(result.support) > 0).sum()),
            "subject_pixel_exact": True, "outside_rgb_constant": [128, 128, 128],
            "pre_pipeline_resize": None, "pipeline_resize": "record runtime separately",
            "prompt": TEMPLATE.format(object=task.selected_object, protected=task.protected),
            "files": {p.name: {"sha256": digest(p), "bytes": p.stat().st_size}
                      for p in sorted(case_dir.iterdir())},
        })
    return records


def main() -> None:
    """Build the six fixed pairs and path-free public contract."""
    root, out, contract = map(Path, sys.argv[1:])
    assert root.is_dir() and not out.exists(), "preserve existing inputs; no overwrite"
    out.mkdir(parents=True)
    rows = [row for task in TASKS for row in prepare_task(root, out, task)]
    record = {
        "experiment": "B-031", "parent": "B-027", "scope": "public DAVIS mask-given development panel",
        "margin": "10% native GT bbox width and height per side; floor left/top, ceil right/bottom; clip native bounds",
        "bbox_convention": "xyxy with exclusive right/bottom", "track_id": 1,
        "source_fps": None, "preview_fps": 24, "timebase_assumed": True,
        "output_request_wh": [896, 512], "image_seed": 20261026,
        "image_steps": 40, "true_cfg_scale": 4.0, "guidance_scale": 1.0,
        "negative_prompt": " ", "image_attempt_limit": 6,
        "video_preselected_refs": ["animal_R1", "human_R1", "vehicle_R1"],
        "video_requires_suitable_anchor": True,
        "code_sha256": digest(Path(__file__)), "cases": rows,
    }
    payload = json.dumps(record, indent=2, ensure_ascii=False) + "\n"
    contract.write_text(payload)
    (out / "INPUT_CONTRACT.json").write_text(payload)
    print(json.dumps({"cases": len(rows), "contract_sha256": digest(contract)}))


if __name__ == "__main__":
    main()
