"""Stdlib-only environment contract shared by preflight and real workers."""
from dataclasses import dataclass
from pathlib import Path
from collections.abc import MutableMapping
import hashlib
import json
import os
import tempfile


class BootstrapError(RuntimeError):
    """Reject an invalid execution contract before importing tensor libraries."""


@dataclass(frozen=True, slots=True)
class BootstrapReceipt:
    stage: str
    root: str
    loader_report: str
    writable_probe_removed: bool
    files_verified: int


def validate_report(root: Path, environment: MutableMapping[str, str]) -> Path:
    """Validate explicit current-stage output without creating the report."""
    value = environment.get('B007E_LOADER_REPORT')
    if not value:
        raise BootstrapError('B007E_LOADER_REPORT missing before model import')
    report = Path(value)
    expected = root.resolve() / 'reports' / 'loader.json'
    if not report.is_absolute() or report != expected or report.resolve() != expected:
        raise BootstrapError('Loader report must be the current stage absolute path')
    if report.exists() or report.is_symlink():
        raise BootstrapError('Loader report collision; original report is preserved')
    reports = expected.parent
    if not reports.is_dir() or reports.is_symlink() or not reports.stat().st_mode & 0o222:
        raise BootstrapError('Current reports directory missing or unwritable')
    with tempfile.NamedTemporaryFile(prefix='.bootstrap-', dir=reports, delete=True) as probe:
        probe.write(b'B034_CONTINUATION_02\n')
        probe.flush()
        os.fsync(probe.fileno())
    return report


def bootstrap(root: Path, environment: MutableMapping[str, str] | None = None) -> BootstrapReceipt:
    """Set required variables explicitly, then validate the frozen stage boundary."""
    root = root.resolve()
    env = os.environ if environment is None else environment
    config = json.loads((root / 'config.json').read_text())
    stage = config.get('stage')
    if stage not in ('STEP_S', 'STEP_D') or root.name != stage:
        raise BootstrapError('Only the explicit STEP_S or STEP_D stage is permitted')
    execution = json.loads((root / 'configs/execution.json').read_text())
    if execution.get('stage') != stage or execution.get('method') != 'STEP':
        raise BootstrapError('Stage execution contract mismatch')
    if execution.get('expected_steps') != 40 or execution.get('expected_forwards') != 80:
        raise BootstrapError('Sampler budget mismatch')
    if any(execution.get(key) is not False for key in ('adapter_enabled', 'alg', 'manual_rope_override', 'b029_gate')) or execution.get('replace_flag') is not True:
        raise BootstrapError('Unexpected method intervention')
    env['HF_HUB_OFFLINE'] = '1'
    env['TRANSFORMERS_OFFLINE'] = '1'
    env['B007E_LOADER_REPORT'] = str(root / 'reports/loader.json')
    report = validate_report(root, env)
    frozen = json.loads((root / 'freeze.json').read_text())['files']
    for name, digest in frozen.items():
        path = Path(name)
        if not path.is_absolute() or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise BootstrapError('Frozen input/code mismatch: ' + name)
    for key in ('upstream', 'models', 'video_code'):
        path = Path(config[key])
        if not path.is_absolute() or not path.is_dir():
            raise BootstrapError('Required directory missing: ' + key)
    return BootstrapReceipt(stage, str(root), str(report), True, len(frozen))
