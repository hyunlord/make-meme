# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# Run with existing research Python: train_white.py /abs/c006/code/train_adapter.py /abs/runtime-config.json [--cpu-only]
"""C-009: refuse legacy red-mask caches, then run the unchanged C-006 train_adapter.py in this process."""
from pathlib import Path
import hashlib
import json
import runpy
import sys

WHITE = 'white_v1'


def verify_white_cache(cache_root: Path) -> dict:
    manifest = json.loads((cache_root / 'CACHE_MANIFEST.json').read_text())
    if not manifest['mask_contract'].startswith(WHITE):
        raise SystemExit(f'LEGACY_OR_UNKNOWN_MASK_CONTRACT: {manifest["mask_contract"]}')
    legacy = set(manifest['legacy_sha256'].values())
    checked = {}
    for path in sorted(cache_root.glob('*.pt')):
        sha = hashlib.sha256(path.read_bytes()).hexdigest()
        if sha in legacy:
            raise SystemExit(f'LEGACY_CACHE_FILE: {path.name}')
        if manifest['files'].get(path.stem, {}).get('sha256') != sha:
            raise SystemExit(f'CACHE_NOT_IN_WHITE_MANIFEST: {path.name}')
        checked[path.stem] = sha
    return checked


def main() -> None:
    script, config_path = Path(sys.argv[1]), Path(sys.argv[2])
    assert script.is_absolute() and config_path.is_absolute()
    cache_root = Path(json.loads(config_path.read_text())['cache_root'])
    checked = verify_white_cache(cache_root)
    print(json.dumps({'white_cache_verified': len(checked), 'cache_root_files': checked}), flush=True)
    sys.argv = [str(script), str(config_path), *sys.argv[3:]]
    runpy.run_path(str(script), run_name='__main__')


if __name__ == '__main__':
    main()
