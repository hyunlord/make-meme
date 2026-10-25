# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Private B027 archive, adapted from B025. Run only after all workers terminate.

No size cap: retain failures, report actual size. Never follow symlinks or scan
weights. --verify-only ZIP independently checks CRC and real extracted files.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
import zipfile
from pathlib import Path

TEXT = {'.md', '.py', '.json', '.jsonl', '.csv', '.txt', '.log', '.diff', '.sh', '.html', '.yaml', '.yml'}
MEDIA = {'.png', '.jpg', '.jpeg', '.mp4', '.webm', '.svg'}
DENY = {'weights', 'models', 'upstream', '.venv', 'environment', '.git', '__pycache__',
        '.pytest_cache', '.ruff_cache', 'prefixfeatures', 'prefix_features', 'latent_cache'}
TENSORS = {'raw_output.pt', 'final_latent.safetensors', 'initial_noise.pt'}


def digest(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def collect(private: Path, public: Path, lessons: list[Path]) -> tuple[dict[str, Path], list[dict[str, object]]]:
    selected: dict[str, Path] = {}
    omitted: list[dict[str, object]] = []

    def omit(path: Path, alias: str, reason: str, hash_file: bool = True) -> None:
        row: dict[str, object] = {'path': alias, 'reason': reason}
        if path.is_symlink():
            row['sha256'] = hashlib.sha256(os.fsencode(os.readlink(path))).hexdigest()
            row['hash_kind'] = 'symlink text; target never followed'
        elif path.is_file() and hash_file:
            row.update(bytes=path.stat().st_size, sha256=digest(path), hash_kind='file bytes')
        else:
            row['hash_kind'] = 'NOT_HASHED; directory not traversed'
        omitted.append(row)

    def tree(root: Path, prefix: str, public_only: bool = False) -> None:
        if root.is_symlink():
            omit(root, prefix, 'symlink root')
            return
        if not root.exists():
            omitted.append({'path': prefix, 'reason': 'not present'})
            return
        for base, directories, files in os.walk(root, followlinks=False):
            basepath = Path(base)
            for name in list(directories):
                path = basepath / name
                if path.is_symlink() or name in DENY:
                    directories.remove(name)
                    omit(path, prefix + '/' + str(path.relative_to(root)), 'excluded directory or symlink', False)
            for name in sorted(files):
                path = basepath / name
                alias = prefix + '/' + str(path.relative_to(root))
                if path.is_symlink():
                    omit(path, alias, 'symlink; no target access')
                elif name == 'preprocessed_inputs.pt' or name.startswith('conditions') and path.suffix == '.safetensors':
                    omit(path, alias, 'duplicate preprocessed/condition cache; metadata and source inputs retained')
                elif path.suffix in TEXT or name.startswith('LICENSE') or (not public_only and (path.suffix in MEDIA or name in TENSORS)):
                    selected[alias] = path
                else:
                    omit(path, alias, 'outside explicit payload allowlist')

    tree(public, 'public/experiment', True)
    for lesson in lessons:
        if lesson.is_symlink() or not lesson.is_file() or lesson.suffix != '.md':
            raise ValueError('Lesson must be a concrete Markdown file')
        alias = 'public/lessons/' + lesson.name
        if alias in selected:
            raise ValueError('Duplicate lesson name')
        selected[alias] = lesson
    for name in ('tasks', 'stages', 'review', 'reports', 'configs', 'scripts', 'code', 'data_code', 'media_code', 'research', 'licenses'):
        tree(private / name, 'private/' + name)
    for path in sorted(private.iterdir()):
        if path.is_symlink():
            omit(path, 'private/' + path.name, 'symlink; no target access')
        elif path.is_file() and path.suffix in TEXT:
            selected['private/' + path.name] = path
        elif path.name == 'data':
            omit(path, 'private/data', 'DAVIS corpus/archive excluded; selected input copies and download manifest retained', False)
        elif path.name in DENY:
            omit(path, 'private/' + path.name, 'bulk model/environment excluded without traversal', False)
    return selected, omitted


def verify(archive_path: Path) -> dict[str, object]:
    with zipfile.ZipFile(archive_path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or archive.testzip() is not None:
            raise ValueError('Duplicate entries or CRC failure')
        for name in names:
            if Path(name).is_absolute() or '..' in Path(name).parts:
                raise ValueError('Unsafe archive member')
        manifest = json.loads(archive.read('MANIFEST.json'))
        expected = {row['path'] for row in manifest['payload']}
        if expected | {'MANIFEST.json'} != set(names):
            raise ValueError('Manifest coverage mismatch')
        # Actual extraction, followed by filesystem SHA verification; no pickle loads.
        with tempfile.TemporaryDirectory(prefix='b027-zip-extraction-') as temporary:
            archive.extractall(temporary)
            for row in manifest['payload']:
                path = Path(temporary) / row['path']
                if path.stat().st_size != row['bytes'] or digest(path) != row['sha256']:
                    raise ValueError('Extracted payload hash/size mismatch')
    return {'zip': str(archive_path.resolve()), 'bytes': archive_path.stat().st_size,
            'sha256': digest(archive_path), 'payload_count': len(expected),
            'crc_verified': True, 'actual_extraction_sha256_verified': True,
            'temporal_quality': 'UNVERIFIED', 'quality_claim': 'Archive integrity only'}


def package(private: Path, public: Path, archive_path: Path, lessons: list[Path]) -> dict[str, object]:
    if archive_path.exists():
        raise FileExistsError(archive_path)
    selected, omitted = collect(private, public, lessons)
    if not selected:
        raise ValueError('Empty payload')
    manifest = {'schema': 1, 'experiment': 'B-027', 'payload': [
        {'path': name, 'bytes': path.stat().st_size, 'sha256': digest(path)}
        for name, path in sorted(selected.items())], 'omitted': omitted,
        'scope': 'Actual artifacts present at packaging; missing/failed stages remain reported. No base weights, full DAVIS corpus, condition caches or duplicate prefix features.'}
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name, path in sorted(selected.items()):
            archive.write(path, name)
        archive.writestr('MANIFEST.json', json.dumps(manifest, indent=2) + '\n')
    receipt = verify(archive_path)
    archive_path.with_suffix(archive_path.suffix + '.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('private', type=Path, nargs='?')
    parser.add_argument('public', type=Path, nargs='?')
    parser.add_argument('zip', type=Path, nargs='?')
    parser.add_argument('--lesson', type=Path, action='append', default=[])
    parser.add_argument('--verify-only', type=Path)
    args = parser.parse_args()
    if args.verify_only:
        result = verify(args.verify_only)
    else:
        if not all((args.private, args.public, args.zip)):
            parser.error('private, public and zip paths required')
        result = package(args.private, args.public, args.zip, args.lesson)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
