"""Synthetic archive fixtures only; never package actual runs during this test."""
import json
import zipfile
from pathlib import Path

import pytest

from package_review import package, verify


def put(root: Path, relative: str, value: bytes = b'synthetic') -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(value)
    return path


def test_task_payload_exclusions_and_actual_extraction(tmp_path: Path) -> None:
    private, public = tmp_path / 'private', tmp_path / 'public'
    put(public, 'RESULTS.md')
    put(public, 'code/run.py')
    put(private, 'tasks/animal/inputs/R1/reference.png')
    put(private, 'tasks/animal/cases/R1/artifacts/raw_output.pt')
    put(private, 'tasks/animal/cases/R1/artifacts/final_latent.safetensors')
    put(private, 'tasks/animal/cases/R1/artifacts/final_latent.json')
    put(private, 'tasks/animal/cases/R1/artifacts/output.mp4')
    put(private, 'tasks/animal/cases/R2/reports/failure.json')
    put(private, 'tasks/animal/cases/R1/artifacts/conditions.safetensors')
    put(private, 'tasks/animal/cases/R1/artifacts/preprocessed_inputs.pt')
    weight = put(private, 'weights/base.safetensors')
    put(private, 'data/DAVIS.zip')
    link = private / 'tasks/animal/weight-link'
    link.symlink_to(weight)
    archive = tmp_path / 'fixture.zip'
    receipt = package(private, public, archive, [])
    assert receipt['actual_extraction_sha256_verified']
    with zipfile.ZipFile(archive) as stream:
        names = stream.namelist()
        assert 'private/tasks/animal/cases/R2/reports/failure.json' in names
        assert 'private/tasks/animal/cases/R1/artifacts/final_latent.safetensors' in names
        assert not any('base.safetensors' in name or name.endswith('conditions.safetensors') or name.endswith('preprocessed_inputs.pt') or 'DAVIS.zip' in name for name in names)
        manifest = json.loads(stream.read('MANIFEST.json'))
        assert any(row.get('hash_kind') == 'symlink text; target never followed' for row in manifest['omitted'])
        assert any(row.get('sha256') for row in manifest['omitted'] if row['path'].endswith('conditions.safetensors'))
    assert verify(archive)['sha256'] == receipt['sha256']
    with pytest.raises(FileExistsError):
        package(private, public, archive, [])


def test_unsafe_archive_rejected(tmp_path: Path) -> None:
    archive = tmp_path / 'unsafe.zip'
    with zipfile.ZipFile(archive, 'w') as stream:
        stream.writestr('../escape', 'bad')
    with pytest.raises(ValueError, match='Unsafe'):
        verify(archive)
