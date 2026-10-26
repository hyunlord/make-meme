#!/usr/bin/env bash
# Run: bash run_video.sh TASK_ROOT PINNED_PYTHON
# Execute only after the parent has reviewed A0 and confirmed Qwen exit.
set -euo pipefail
root="$1"
python="$2"
for stage in ENC R1_PROBE R1_S R1_D; do
  worker="$root/stages/$stage"
  "$python" "$root/code/runtime_launch.py" "$worker" 1800 "$python" "$root/code/run_phase.py" "$worker" "$stage"
  "$python" -c 'import json,sys;from pathlib import Path;p=Path(sys.argv[1]);r=json.loads((p/"reports/result.json").read_text());g=json.loads((p/"reports/pipeline-process.json").read_text());assert r["status"]=="COMPLETED" and g["reason"]=="service_exit" and g["returncode"]==0 and "MainPID=0" in g["final_service"]' "$worker"
done
