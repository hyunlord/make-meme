"""Plot recorded OS/cgroup samples only; no models or CUDA operations.

Run: python plot_resources.py RESOURCE_JSONL OUTPUT_PNG
Event timestamps describe the fixed B-007E run, not inferred subphases.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

GIB = 1024**3


def rss_bytes(status: str, field: str) -> int:
    """Linux /proc status uses kB (1024 bytes); absent fields are not zero."""
    for line in status.splitlines():
        if line.startswith(field + ":"):
            return int(line.split()[1]) * 1024
    raise ValueError(f"Missing {field}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("metrics", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    rows = [json.loads(line) for line in args.metrics.read_text().splitlines() if line]
    assert rows and all(a["time"] <= b["time"] for a, b in zip(rows, rows[1:]))
    start = rows[0]["time"]
    minutes = [(row["time"] - start) / 60 for row in rows]
    available = [row["available"] / GIB for row in rows]
    current: list[float] = []
    anon: list[float] = []
    files: list[float] = []
    for row in rows:
        group = row["cgroup"]
        current.append(int(group["memory.current"]) / GIB if "memory.current" in group else float("nan"))
        statuses = [value for key, value in group.items() if key.startswith("pid-")]
        anon.append(sum(rss_bytes(status, "RssAnon") for status in statuses) / GIB if statuses else float("nan"))
        files.append(sum(rss_bytes(status, "RssFile") for status in statuses) / GIB if statuses else float("nan"))
    figure, axes = plt.subplots(3, 1, figsize=(12, 9), sharex=True)
    axes[0].plot(minutes, available, label="System MemAvailable", linewidth=1)
    axes[0].axhline(24, color="red", linestyle="--", label="24 GiB stop floor")
    axes[1].plot(minutes, current, label="Owned cgroup memory.current", linewidth=1)
    axes[1].axhline(64, color="red", linestyle="--", label="64 GiB cgroup cap")
    axes[2].plot(minutes, anon, label="Sum process RssAnon", linewidth=1)
    axes[2].plot(minutes, files, label="Sum process RssFile", linewidth=1)
    events = [
        (1792678244.543376, "Load complete\n268.587 s phase time"),
        (dt.datetime.fromisoformat("2026-10-22T14:12:05+00:00").timestamp(), "First forward\n14:12:05 UTC"),
        (dt.datetime.fromisoformat("2026-10-22T14:28:39+00:00").timestamp(), "40/40 boundary\n~14:28:39 UTC"),
        (dt.datetime.fromisoformat("2026-10-22T14:30:22+00:00").timestamp(), "Stop\n14:30:22 UTC"),
    ]
    for index, (epoch, label) in enumerate(events):
        point = (epoch - start) / 60
        for axis in axes:
            axis.axvline(point, color="gray", linestyle=":", linewidth=0.8)
        axes[0].annotate(label, (point, 1), xycoords=("data", "axes fraction"),
                         xytext=(-3, 8 + 28 * (index % 2)), textcoords="offset points",
                         ha="right" if index == 3 else "left", fontsize=8)
    for axis in axes:
        axis.set_ylabel("GiB")
        axis.grid(alpha=0.2)
        axis.legend(loc="best", fontsize=8)
    origin = dt.datetime.fromtimestamp(start, dt.timezone.utc).isoformat()
    axes[-1].set_xlabel(f"Minutes since first metric ({origin})")
    figure.suptitle("B-007E observed memory: stopped below system headroom floor", y=0.995)
    figure.text(0.06, 0.012,
                "Separate accounting views; do not add RSS/cgroup/system curves or count unified memory twice.\n"
                "No continuous CUDA allocator curve. Exact offload/decode subphase UNOBSERVED; 40/40 is not video success.", fontsize=9)
    figure.tight_layout(rect=(0, 0.065, 1, 0.91))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists():
        raise FileExistsError(args.output)
    figure.savefig(args.output, dpi=140)
    summary = {"metrics_sha256": hashlib.sha256(args.metrics.read_bytes()).hexdigest(),
               "samples": len(rows), "first_metric_epoch": start,
               "last_metric_epoch": rows[-1]["time"], "last_mem_available_gib": available[-1],
               "min_mem_available_gib": min(available), "events": events,
               "plot_sha256": hashlib.sha256(args.output.read_bytes()).hexdigest(),
               "accounting": "Separate OS/cgroup/process observations; no CUDA curve or additive total.",
               "subphase": "offload/decode UNOBSERVED"}
    args.output.with_suffix(".json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
