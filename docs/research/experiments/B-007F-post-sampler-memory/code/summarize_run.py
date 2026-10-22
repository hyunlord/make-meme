"""Read completed case evidence without importing model libraries.

Usage: python summarize_run.py CASE_ROOT OUTPUT_JSON
Does not infer scheduler completion from progress bars or exit status alone.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def json_rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()] if path.exists() else []


def optional_json(path: Path) -> dict:
    return json.loads(path.read_text()) if path.exists() else {}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    reports = args.case / "reports"
    service = optional_json(reports / "pipeline-process.json")
    if "finished" not in service:
        raise RuntimeError("Case has no durable terminal supervisor record")
    phases = json_rows(reports / "model_phases.jsonl")
    resources = json_rows(reports / "resource_metrics.jsonl")
    starts: dict[str, float] = {}
    durations: list[dict] = []
    for row in phases:
        name = row["phase"]
        stamp = row.get("monotonic", row["epoch"])
        if name.endswith("_start"):
            starts[name[:-6]] = stamp
        else:
            suffix = next((item for item in ("_end", "_complete", "_done") if name.endswith(item)), None)
            if suffix is not None and name[:-len(suffix)] in starts:
                key = name[:-len(suffix)]
                durations.append({"phase": key, "seconds": stamp - starts.pop(key)})
    cases = []
    for folder in sorted((args.case / "outputs").glob("*")):
        if not folder.is_dir():
            continue
        progress = optional_json(folder / "sampler_progress.json")
        latent = optional_json(folder / "final_latent.json")
        run = optional_json(folder / "run.json")
        artifact = folder / "final_latent.safetensors"
        evidence = {"case": folder.name, "run_status": run.get("status", "NOT_RECORDED"),
                    "error": run.get("error"), "completed_steps": progress.get("completed_steps"),
                    "actual_model_calls": progress.get("actual_model_calls"),
                    "persisted_forward_calls": run.get("forward_calls"),
                    "latent_status": latent.get("status", "NOT_SAVED"),
                    "latent_shape": latent.get("shape"), "latent_dtype": latent.get("dtype"),
                    "latent_readback_exact_runtime": latent.get("readback_exact"),
                    "output_finite": run.get("output_finite"), "mp4_exists": (folder / "output.mp4").exists()}
        if artifact.exists():
            if artifact.stat().st_size > 16 * 1024 * 1024:
                raise RuntimeError("Unexpected latent size; refusing unbounded artifact read")
            digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
            evidence.update(latent_bytes=artifact.stat().st_size, latent_sha256=digest,
                            latent_manifest_hash_match=digest == latent.get("sha256"))
        cases.append(evidence)
    result = {"supervisor": {key: service.get(key) for key in ("reason", "returncode", "started", "finished", "final_service")},
              "last_durable_phase": phases[-1]["phase"] if phases else "NOT_RECORDED",
              "last_phase_epoch": phases[-1]["epoch"] if phases else None,
              "phase_durations": durations, "unpaired_phase_starts": sorted(starts),
              "resource_sample_count": len(resources),
              "min_available_gib": min((row["available"] / 1024**3 for row in resources), default=None),
              "max_swap_bytes": max((row["swap"] for row in resources), default=None),
              "max_observed_cgroup_current_bytes": max((int(row["cgroup"]["memory.current"]) for row in resources if "memory.current" in row.get("cgroup", {})), default=None),
              "cases": cases,
              "limits": ["No completion inferred from tqdm or exit code alone.",
                         "Open phase is an observed boundary, not proof of the internal failure cause.",
                         "OS, cgroup, process and CUDA accounting must not be added together.",
                         "Artifact existence/hash does not establish image or temporal quality."]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
