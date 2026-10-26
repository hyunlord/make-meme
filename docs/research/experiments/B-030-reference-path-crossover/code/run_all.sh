#!/usr/bin/env bash
# Run: bash code/run_all.sh B030_ROOT PINNED_PYTHON
# Sequential only. Every worker reserves a unique attempt with exclusive create.
set -euo pipefail
root="$1"
python="$2"
for task in human vehicle; do
  for row in R1 R2; do
    for phase in PROBE S D; do
      stage="${row}_${phase}"
      worker="$root/tasks/$task/stages/$stage"
      "$python" "$root/code/runtime_launch.py" "$worker" 1800 "$python" "$root/code/run_phase.py" "$worker" "$stage"
      "$python" -c 'import json,sys;from pathlib import Path;p=Path(sys.argv[1]);r=json.loads((p/"reports/result.json").read_text());g=json.loads((p/"reports/pipeline-process.json").read_text());assert r["status"]=="COMPLETED" and g["reason"]=="service_exit" and g["returncode"]==0 and "MainPID=0" in g["final_service"]' "$worker"
    done
  done
done
