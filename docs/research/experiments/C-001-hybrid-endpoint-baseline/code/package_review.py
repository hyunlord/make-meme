"""Create and verify a ZIP64 review archive without raw tensors or weight payloads."""
from pathlib import Path
import hashlib
import json
import sys
import zipfile


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    source, archive, extracted = map(Path, sys.argv[1:4])
    assert all(path.is_absolute() for path in (source, archive, extracted))
    assert source.is_dir() and not archive.exists() and not extracted.exists()
    files = sorted(path for path in source.rglob('*') if path.is_file())
    assert files and not any(path.suffix in ('.pt', '.pth', '.safetensors') for path in files)
    manifest = {str(path.relative_to(source)): sha(path) for path in files}
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True) as output:
        for path in files:
            output.write(path, str(path.relative_to(source)))
    with zipfile.ZipFile(archive) as package:
        assert package.testzip() is None
        package.extractall(extracted)
    actual = {str(path.relative_to(extracted)): sha(path) for path in extracted.rglob('*') if path.is_file()}
    assert actual == manifest
    receipt = {'crc':'PASS', 'extracted_payload_sha256':'PASS', 'files':len(files),
               'archive_bytes':archive.stat().st_size, 'archive_sha256':sha(archive),
               'payload':manifest}
    archive.with_suffix('.verification.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps({key:value for key,value in receipt.items() if key!='payload'}))


if __name__ == '__main__':
    main()
