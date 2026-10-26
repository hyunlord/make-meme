"""Verify a self-produced review ZIP with actual extraction and payload hashes."""
from __future__ import annotations
import hashlib
import json
import sys
import tempfile
import zipfile
from pathlib import Path


def sha256(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def verify(path: Path) -> None:
    with zipfile.ZipFile(path) as archive, tempfile.TemporaryDirectory(prefix='b030-verify-', dir=path.parent) as directory:
        if archive.testzip() is not None:
            raise ValueError('CRC mismatch')
        names = archive.namelist()
        if len(names) != len(set(names)) or any(Path(name).is_absolute() or '..' in Path(name).parts for name in names):
            raise ValueError('Invalid ZIP member paths')
        archive.extractall(directory)
        manifest = json.loads((Path(directory) / 'PAYLOAD_MANIFEST.json').read_text())
        if set(names) != {row['path'] for row in manifest['files']} | {'PAYLOAD_MANIFEST.json'}:
            raise ValueError('Manifest member set mismatch')
        for row in manifest['files']:
            item = Path(directory) / row['path']
            if item.stat().st_size != row['bytes'] or sha256(item) != row['sha256']:
                raise ValueError(f'Payload mismatch: {row["path"]}')
    print(json.dumps({'archive': path.name, 'bytes': path.stat().st_size,
                      'sha256': sha256(path), 'payload_files': len(manifest['files']),
                      'CRC': 'PASS', 'actual_extraction': 'PASS', 'payload_hashes': 'PASS'}))


if __name__ == '__main__':
    verify(Path(sys.argv[1]))
