# /// script
# requires-python = ">=3.12"
# dependencies = ["pillow"]
# ///
# python reports/validate_runs.py B004_ROOT B003_ROOT
"""Read-only experiment verification; writes only aggregate reports and CSV."""
from pathlib import Path
from PIL import Image, ImageOps
import csv
import hashlib
import json
import subprocess
import sys

root = Path(sys.argv[1]).resolve()
baseline = Path(sys.argv[2]).resolve()
reports = root / "reports"
old = baseline / "outputs/C-real-20261022"
fixed = json.loads((old / "config.json").read_text())
registration = json.loads((root / "configs/PREREGISTRATION.json").read_text())

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def rows(path: Path) -> list:
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

def series(path: Path) -> list[str]:
    return [sha(path / f"{i:03d}.png") for i in range(17)]

attempts = rows(reports / "attempts.jsonl")
started = [row for row in attempts if row["event"] == "started"]
finished = {row["label"]: row for row in attempts if row["event"] == "finished"}
resources = rows(reports / "resource_metrics.jsonl")
expected_code = json.loads((reports / "prereg_code_hashes.json").read_text())
code_matches = {name: sha(root / name if name.startswith("scripts/") else root / "scripts" / name) == expected for name, expected in expected_code.items()}
base_series = {name: series(old / name) for name in ("target", "mask")}
comparisons = []
resource_rows = []
fixed_fields = ("upstream", "weights", "tokenizer", "source_video", "condition_video", "prompt", "negative_prompt", "width", "height", "frames", "fps", "sampling_steps", "cfg", "adapter", "optimizer_checkpoint")
for start in started:
    label = start["label"]
    folder = root / "outputs" / label
    config_file = root / "configs" / f"{label}.json"
    config = json.loads(config_file.read_text())
    item = {"label": label, "attempt": start["attempt"], "seed": config["seed"], "status": "RUNNING", "checks": {}, "hashes": {}}
    item["checks"]["config_ledger_hash"] = sha(config_file) == start["config_sha256"]
    item["checks"]["same_fixed_settings"] = all(config.get(key) == fixed.get(key) for key in fixed_fields)
    item["checks"]["prereg_commit"] = start["prereg_commit"] == registration["commit"]
    ending = finished.get(label)
    if ending:
        item["status"] = "COMPLETED" if ending["returncode"] == 0 else "FAILED"
        item["returncode"] = ending["returncode"]
    if item["status"] == "COMPLETED":
        saved_config = json.loads((folder / "config.json").read_text())
        item["checks"]["saved_config_semantics"] = all(saved_config.get(key) == config.get(key) for key in config)
        item["checks"]["source_mask_unchanged"] = all(series(folder / name) == values for name, values in base_series.items())
        with Image.open(config["reference"]) as image:
            expected_ref = ImageOps.pad(image.convert("RGB"), (512, 288), color=(128, 128, 128))
        with Image.open(folder / "reference.png") as image:
            item["checks"]["reference_preprocess_matches"] = expected_ref.tobytes() == image.convert("RGB").tobytes()
        expected_condition = Path(config["condition_video"])
        item["checks"]["condition_matches_config_rgb"] = all(Image.open(folder/"condition"/f"{i:03d}.png").convert("RGB").tobytes() == Image.open(expected_condition/f"{i:03d}.png").convert("RGB").tobytes() for i in range(17))
        observations = rows(folder / "actual_input_hashes.jsonl")
        latest = observations[-1]["tensors"]
        item["vace_slices"] = observations[-1]["slices"]
        item["hashes"] = {key: value["sha256"] for key, value in latest.items()}
        item["tensor_shapes"] = {key: value["shape"] for key, value in latest.items()}
        item["checks"]["actual_noise_vace_shapes"] = latest["shared.noise"]["shape"] == [1,16,6,36,64] and latest["shared.vace_context"]["shape"] == [1,96,6,36,64]
        initial = json.loads((folder / "initial_noise.json").read_text())
        item["checks"]["actual_noise_matches_saved_noise"] = latest["shared.noise"]["sha256"] == initial["tensor_bytes_sha256"]
        item["checks"]["preprocess_cpu_rng_unchanged"] = all(row["cpu_rng_before"] == row["cpu_rng_after"] for row in observations)
        runtime = json.loads((folder / "resolved_runtime.json").read_text())
        item["runtime"] = runtime
        item["checks"]["adapter_off_no_offload_bf16"] = runtime["adapter"] is None and runtime["vram_management_enabled"] is False and runtime["torch_dtype"] == "torch.bfloat16"
        params = json.loads((folder / "parameter_counts.json").read_text())
        item["parameter_counts"] = params
        item["checks"]["parameter_counts_unchanged"] = params == json.loads((old / "parameter_counts.json").read_text())
        probe = json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=nb_frames,r_frame_rate,duration,width,height", "-of", "json", str(folder / "result.mp4")]))["streams"][0]
        item["video"] = probe
        item["checks"]["17_frames_24fps_512x288"] = probe["nb_frames"] == "17" and probe["r_frame_rate"] == "24/1" and probe["width"] == 512 and probe["height"] == 288 and abs(float(probe["duration"]) - 17/24) < 0.00001
        item["output_sha256"] = sha(folder / "result.mp4")
        summary = json.loads((folder / "summary.json").read_text())
        timing = json.loads((folder / "sampler_timing.json").read_text())
        item["checks"]["40_model_calls"] = timing["calls"] == 40
        used = [row for row in resources if row["label"] == label]
        resource = {"label": label, "process_seconds": ending["time"] - start["time"], "runner_seconds": summary["elapsed_seconds"], "pipeline_seconds": summary["pipeline_seconds_includes_preprocess_decode"], "model_seconds": timing["model_seconds"], "cuda_peak_allocated_bytes": summary["cuda_peak_allocated"], "cuda_peak_reserved_bytes": summary["cuda_peak_reserved"], "os_mem_available_min_bytes": min(row["MemAvailable"] for row in used), "swap_peak_bytes": max(row["swap_used"] for row in used)}
        resource_rows.append(resource)
        item["resources"] = resource
    item["technical_checks_pass"] = all(item["checks"].values())
    comparisons.append(item)

complete = [row for row in comparisons if row["status"] == "COMPLETED"]
paired = {}
for seed in (20261022, 20261023):
    runs = [row for row in complete if row["seed"] == seed]
    prior_folder = baseline / "outputs" / f"C-real-{seed}"
    prior = rows(prior_folder / "actual_input_hashes.jsonl")[-1]
    if len(runs) == 1:
        run = runs[0]
        paired[str(seed)] = {"pair_complete": True,
            "same_noise": run["hashes"]["shared.noise"] == prior["tensors"]["shared.noise"]["sha256"],
            "same_positive_text": run["hashes"]["positive.context"] == prior["tensors"]["positive.context"]["sha256"],
            "same_negative_text": run["hashes"]["negative.context"] == prior["tensors"]["negative.context"]["sha256"],
            "different_context": run["hashes"]["shared.vace_context"] != prior["tensors"]["shared.vace_context"]["sha256"],
            "slice_equal": {key: run["vace_slices"][key]["sha256"] == prior["slices"][key]["sha256"] for key in ("reference_prefix","video_inactive","video_reactive","mask_all")},
            "reused_output_sha256": sha(prior_folder / "result.mp4")}
    else:
        paired[str(seed)] = {"pair_complete": False}
result = {"experiment": "B-004", "prereg_commit": registration["commit"], "new_attempts": len(started), "attempt_cap_2": len(started) <= 2, "new_completed": len(complete), "new_failed": sum(row["status"] == "FAILED" for row in comparisons), "reused": ["B003/C-real-20261022", "B003/C-real-20261023"], "code_hash_matches_prereg": code_matches, "paired_controls": paired, "runs": comparisons, "training_updates": 0, "temporal_quality": "UNVERIFIED", "quality_acceptance": "NOT_INFERRED_FROM_TECHNICAL_CHECKS"}
result["paired_control_checks_pass"] = all(row["pair_complete"] and row["same_noise"] and row["same_positive_text"] and row["same_negative_text"] and row["different_context"] and not row["slice_equal"]["reference_prefix"] and row["slice_equal"]["video_inactive"] and row["slice_equal"]["mask_all"] and row["slice_equal"]["video_reactive"] for row in paired.values())
result["all_completed_technical_checks_pass"] = all(row["technical_checks_pass"] for row in complete) and all(code_matches.values())
result["full_design_completed"] = len(complete) == 2 and len(started) == 2
for path in (reports / "validation.json", reports / "run_summary.json"):
    path.write_text(json.dumps(result, indent=2))
assert "/home/" not in json.dumps(result) and "/Users/" not in json.dumps(result), "summary contains private path"
if resource_rows:
    with (reports / "resource_summary.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(resource_rows[0]))
        writer.writeheader();writer.writerows(resource_rows)
print(json.dumps({key: result[key] for key in ("new_attempts", "new_completed", "new_failed", "code_hash_matches_prereg", "paired_controls")}, indent=2))
