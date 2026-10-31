# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# Run on Spark: C009_STAGE_SETTINGS=/abs/private-settings.json python3 make_stage.py /abs/experiment_root <name> <script> [<script-arg> ...] <config.json>
# Private settings keys: research, python, guard, adapter, policy_template, vae (absolute paths; not published).
"""Create cpu/heavy stage roots in the exact C-007 layout for the unchanged C-001 guard adapter."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import sys
import time

_SETTINGS = json.loads(Path(os.environ['C009_STAGE_SETTINGS']).read_text())
RESEARCH = Path(_SETTINGS['research'])          # make-meme-c research root
PYTHON = _SETTINGS['python']                     # existing research venv python
GUARD = Path(_SETTINGS['guard'])                 # C-003 code/guard
ADAPTER = Path(_SETTINGS['adapter'])             # C-001 code/run_guarded.py
TEMPLATE = Path(_SETTINGS['policy_template'])    # C-007 base_5-heavy service-policy.json
VAE = _SETTINGS['vae']                           # Wan2.1_VAE.pth


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(root: Path, name: str, kind: str, script: Path, args: list[str], inputs: list[str],
          outputs: list[str], deadline: float) -> Path:
    stage = root / 'stages' / f'{name}-{kind}'
    (stage / 'configs').mkdir(parents=True)
    (stage / 'code').mkdir()
    (stage / 'reports').mkdir()
    shutil.copy2(ADAPTER, stage / 'code/worker.py')
    config = {'python': PYTHON, 'cwd': str(root), 'script': str(script),
              'args': [*args, *(['--cpu-only'] if kind == 'cpu' else [])],
              'environment': {'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1', 'TOKENIZERS_PARALLELISM': 'false'},
              'checkpoint': VAE, 'input_paths': inputs, 'output_paths': outputs,
              'guard_code': str(GUARD), 'stage': f'{name}-{kind}', 'unit': f'make-meme-c001-c009-{name}-{kind}',
              'deadline_epoch': deadline, 'allowed_gpu_processes': {},
              'research_lock': str(RESEARCH / 'C-001-hybrid-endpoint-baseline/research.lock'),
              'memory_budget_state': str(stage / 'memory-budget-state.json'), 'worker_max_seconds': 1800,
              'cpu_route_receipt': str(root / 'stages' / f'{name}-cpu/reports/supervisor-result.json')}
    (stage / 'config.json').write_text(json.dumps(config, indent=2))
    policy = json.loads(TEMPLATE.read_text())
    policy.update(attempt_id=f'C001_C009_{name}_{kind}', stage=config['stage'], stage_root=str(stage),
                  boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(), deadline_epoch=deadline,
                  research_root=str(root), authorization='C009 white-mask cache rebuild, matched retrain, probes and 3 videos; unchanged guards')
    for path, expected in policy['logical_files'].items():
        assert sha(Path(path)) == expected, f'service logical file changed: {path}'
    (stage / 'configs/service-policy.json').write_text(json.dumps(policy, indent=2))
    frozen = [stage / 'config.json', stage / 'configs/service-policy.json', stage / 'code/worker.py', ADAPTER, script,
              *sorted(script.parent.glob('*.py')), *(GUARD / n for n in ('memory.py', 'safety.py', 'policy.py', 'supervisor.py')),
              *(Path(p) for p in inputs if Path(p).is_file())]
    (stage / 'freeze.json').write_text(json.dumps({'files': {str(p): sha(p) for p in frozen}}, indent=2))
    return stage


def main() -> None:
    """Script args are passed through; the last arg is the JSON config whose output/output_* keys are stage outputs."""
    root, name, script, args = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3]), sys.argv[4:]
    config = json.loads(Path(args[-1]).read_text())
    outputs = [config[key] for key in sorted(config) if key == 'output' or key.startswith('output_')]
    inputs = [arg for arg in args if Path(arg).is_file()]
    deadline = float(int(time.time()) + 4 * 3600)
    for kind in ('cpu', 'heavy'):
        print(build(root, name, kind, script, args, inputs, outputs, deadline))


if __name__ == '__main__':
    main()
