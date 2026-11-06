# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# Run: python3 build_sample.py PRIVATE_MANIFEST.json PRIVATE_OUTPUT_DIRECTORY
"""Hydrate metadata-only sample manifests with hashes; never copy media or load models."""
from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import TypeAlias

Json: TypeAlias = None | bool | int | float | str | list['Json'] | dict[str, 'Json']


class SampleError(RuntimeError):
    """A missing artifact, mismatched hash, or existing record prevents publication."""


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            result.update(block)
    return result.hexdigest()


def hydrate(value: Json) -> Json:
    """Resolve explicit asset_path markers; leave all scene metadata unchanged."""
    match value:
        case dict() as mapping:
            if 'asset_path' in mapping:
                raw_path = mapping['asset_path']
                if not isinstance(raw_path, str):
                    raise SampleError('asset_path must be a string')
                path = Path(raw_path)
                if not path.exists():
                    raise SampleError(f'Missing required artifact: {path}')
                result = {key: hydrate(item) for key, item in mapping.items() if key != 'asset_path'}
                result['path'] = str(path.resolve())
                if path.is_dir():
                    pattern = mapping.get('glob', '*')
                    if not isinstance(pattern, str):
                        raise SampleError('glob must be a string')
                    files = sorted(item for item in path.glob(pattern) if item.is_file())
                    if not files:
                        raise SampleError(f'Empty required asset directory: {path}')
                    inventory: list[Json] = [
                        {'relative_path': item.relative_to(path).as_posix(), 'bytes': item.stat().st_size,
                         'sha256': digest(item)} for item in files
                    ]
                    result.update({'kind': 'directory', 'files': inventory, 'file_count': len(files),
                                   'sha256': hashlib.sha256(json.dumps(inventory, sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
                                   'hash_definition': 'SHA256 of canonical sorted file inventory JSON'})
                else:
                    actual = digest(path)
                    expected = mapping.get('expected_sha256')
                    if expected is not None and expected != actual:
                        raise SampleError(f'Artifact hash mismatch: {path}')
                    result.update({'kind': 'file', 'bytes': path.stat().st_size, 'sha256': actual})
                return result
            return {key: hydrate(item) for key, item in mapping.items()}
        case list() as sequence:
            return [hydrate(item) for item in sequence]
        case None | bool() | int() | float() | str():
            return value
    raise SampleError('Unsupported JSON value')


def publish(manifest_path: Path, output_root: Path) -> list[Path]:
    """Publish immutable SAMPLE records with readback; fail before overwriting any record."""
    manifest = json.loads(manifest_path.read_text())
    records = manifest['samples']
    targets = []
    for record in records:
        sample_id = record['sample_id']
        if not isinstance(sample_id, str) or Path(sample_id).is_absolute() or '..' in Path(sample_id).parts:
            raise SampleError('sample_id must be a safe relative path')
        target = output_root / sample_id / 'SAMPLE.json'
        if target.exists():
            raise SampleError(f'Record already exists: {target}')
        targets.append(target)
    hydrated = [hydrate(record) for record in records]
    for record, target in zip(hydrated, targets, strict=True):
        if not isinstance(record, dict):
            raise SampleError('sample must be an object')
        record.update({'schema_version': '1.0', 'recorded_at_utc': datetime.now(timezone.utc).isoformat(),
                       'record_origin': manifest['record_origin'], 'media_copied': False,
                       'human_review': {'status': 'PENDING', 'form_values': None, 'source_form': None}})
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix('.tmp')
        with temporary.open('x') as stream:
            json.dump(record, stream, indent=2, ensure_ascii=False)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, target)
        temporary.unlink()
        if json.loads(target.read_text()) != record:
            raise SampleError(f'Readback mismatch: {target}')
    return targets


if __name__ == '__main__':
    results = publish(Path(sys.argv[1]), Path(sys.argv[2]))
    print(json.dumps({'sample_count': len(results), 'media_copied': False, 'human_review': 'PENDING'}))
