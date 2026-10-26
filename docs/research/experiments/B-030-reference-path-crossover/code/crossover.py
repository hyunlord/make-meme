# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
# Run through prepare_layout.py using the pinned environment; no downloads.
"""Copy only the two CLIP leaves while retaining every original device contract."""
from collections.abc import Mapping
from pathlib import Path
from typing import Final
import copy
import hashlib
import json
import shutil
import torch
from safetensors.torch import load_file, save_file

CLIP_KEYS: Final = frozenset({'t2', 't8'})


def crossed_values(row: Mapping[str, torch.Tensor], donor: Mapping[str, torch.Tensor]) -> Mapping[str, torch.Tensor]:
    """Return a detached copy with only conditional/unconditional CLIP replaced."""
    assert set(row) == set(donor) == {f't{i}' for i in range(16)}
    for key in CLIP_KEYS:
        assert row[key].shape == donor[key].shape and row[key].dtype == donor[key].dtype
    return {key: (donor[key] if key in CLIP_KEYS else value).clone() for key, value in row.items()}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def derive(row: Path, donor: Path, output: Path) -> None:
    """Write a new lossless cache; parents and CPU RNG remain unchanged."""
    before_rng = torch.get_rng_state().clone()
    names = ('conditions.safetensors', 'conditions.json', 'conditions_receipt.json', 'initial_noise.pt')
    original = {str(p / name): sha(p / name) for p in (row, donor) for name in names}
    a = json.loads((row / 'conditions.json').read_text())
    b = json.loads((donor / 'conditions.json').read_text())
    assert a['structure'] == b['structure']
    for branch in ('arg_c', 'arg_null'):
        node = a['structure']['dict'][branch]['dict']['clip_fea']
        assert node['tensor'] == ('t2' if branch == 'arg_c' else 't8')
    values = crossed_values(load_file(str(row / 'conditions.safetensors')), load_file(str(donor / 'conditions.safetensors')))
    assert not (output / 'conditions.safetensors').exists()
    save_file(values, str(output / 'conditions.safetensors'))
    metadata = copy.deepcopy(a)
    for key in CLIP_KEYS:
        metadata['tensors'][key] = copy.deepcopy(b['tensors'][key])
    metadata['file_sha256'] = sha(output / 'conditions.safetensors')
    metadata['bytes'] = (output / 'conditions.safetensors').stat().st_size
    metadata['provenance']['crossover'] = {'consumer': 'B-030', 'row_sha256': a['file_sha256'], 'clip_donor_sha256': b['file_sha256'], 'changed_leaves': sorted(CLIP_KEYS), 'encoder_calls': 0}
    (output / 'conditions.json').write_text(json.dumps(metadata, indent=2) + '\n')
    shutil.copy2(row / 'initial_noise.pt', output / 'initial_noise.pt')
    restored = load_file(str(output / 'conditions.safetensors'))
    assert all(torch.equal(value, restored[key]) for key, value in values.items())
    for path, digest in original.items():
        assert sha(Path(path)) == digest
    assert torch.equal(before_rng, torch.get_rng_state())
    receipt = {'experiment': 'B-030', 'hashes': {name: sha(output / name) for name in ('conditions.safetensors', 'conditions.json', 'initial_noise.pt')}, 'parents': original, 'expected_changed': sorted(CLIP_KEYS), 'cpu_rng_unchanged': True, 'readback_exact': True}
    (output / 'conditions_receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
