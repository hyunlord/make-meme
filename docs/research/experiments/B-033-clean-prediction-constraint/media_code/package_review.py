"""Package an explicitly staged private payload; no discovery or source mutation."""
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


def package(stage: Path, output: Path) -> dict[str, object]:
    if output.exists():
        raise FileExistsError(output)
    files = sorted(path for path in stage.rglob('*') if path.is_file())
    if not files or any(path.is_symlink() for path in stage.rglob('*')):
        raise ValueError('Payload must be nonempty and contain no symlinks')
    rows = [{'path': str(path.relative_to(stage)), 'bytes': path.stat().st_size,
             'sha256': sha256(path)} for path in files]
    manifest = json.dumps({'files': rows}, indent=2, sort_keys=True).encode() + b'\n'
    if any(row['path'] == 'PAYLOAD_MANIFEST.json' for row in rows):
        raise ValueError('Manifest name is reserved')
    with zipfile.ZipFile(output, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True) as archive:
        for path in files:
            info = zipfile.ZipInfo(str(path.relative_to(stage)), (2026, 10, 26, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            with path.open('rb') as source, archive.open(info, 'w', force_zip64=True) as target:
                while block := source.read(1 << 20):
                    target.write(block)
        info = zipfile.ZipInfo('PAYLOAD_MANIFEST.json', (2026, 10, 26, 0, 0, 0))
        info.create_system = 3
        info.external_attr = 0o100644 << 16
        archive.writestr(info, manifest)
    with zipfile.ZipFile(output) as archive, tempfile.TemporaryDirectory(prefix='review-extract-', dir=output.parent) as temporary:
        if archive.testzip() is not None:
            raise ValueError('ZIP CRC validation failed')
        archive.extractall(temporary)
        for row in rows:
            extracted = Path(temporary) / str(row['path'])
            if extracted.stat().st_size != row['bytes'] or sha256(extracted) != row['sha256']:
                raise ValueError(f'Extracted payload mismatch: {row["path"]}')
    result = {'archive': output.name, 'bytes': output.stat().st_size, 'sha256': sha256(output),
              'payload_files': len(rows), 'crc': 'PASS', 'actual_extraction_hashes': 'PASS',
              'compression': 'ZIP_DEFLATED', 'deterministic_metadata': True}
    output.with_suffix('.verification.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


if __name__ == '__main__':
    print(json.dumps(package(Path(sys.argv[1]), Path(sys.argv[2])), indent=2))
