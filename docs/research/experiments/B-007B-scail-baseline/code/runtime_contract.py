"""Metadata-only full model key/shape check; no checkpoint payload or inference."""
from __future__ import annotations
from collections import Counter
import json
from pathlib import Path
import sys
import torch
from safetensors import safe_open
from runtime_loader import parameter_dtype


def main() -> None:
    root = Path(sys.argv[1])
    sys.path.insert(0, str(root / "upstream"))
    from wan.modules.model_scail2 import SCAIL2Model
    with torch.device("meta"):
        model = SCAIL2Model.from_config(str(root / "upstream/configs/config-14b.json"))
    state = model.state_dict()
    mismatch: list[dict] = []
    dtypes: Counter[str] = Counter()
    with safe_open(root / "models/SCAIL.safetensors", framework="pt", device="cpu") as stored:
        missing = sorted(set(state) - set(stored.keys()))
        unexpected = sorted(set(stored.keys()) - set(state))
        for name in set(state) & set(stored.keys()):
            shape = stored.get_slice(name).get_shape()
            if list(state[name].shape) != shape:
                mismatch.append({"name": name, "model": list(state[name].shape), "checkpoint": shape})
            dtypes[str(parameter_dtype(name))] += state[name].numel()
    report = {"status": "PASS" if not (missing or unexpected or mismatch) else "FAIL", "model_parameter_count": sum(p.numel() for p in model.parameters()), "state_keys": len(state), "missing": missing, "unexpected": unexpected, "shape_mismatch": mismatch, "planned_dtype_numel": dict(dtypes), "planned_parameter_bytes": sum(count * (4 if dtype == "torch.float32" else 2) for dtype, count in dtypes.items()), "cuda_initialized_by_upstream_import": torch.cuda.is_initialized(), "checkpoint_payload_read": False, "diffusion_calls": 0}
    (root / "reports/model_state_contract.json").write_text(json.dumps(report, indent=2))
    assert report["status"] == "PASS", "Model state metadata mismatch"


if __name__ == "__main__":
    main()
