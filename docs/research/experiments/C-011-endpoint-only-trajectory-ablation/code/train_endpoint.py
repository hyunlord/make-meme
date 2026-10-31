# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# Run with existing research Python: train_endpoint.py /abs/c009/code/train_white.py /abs/c006/code/train_adapter.py /abs/config.json [--cpu-only]
"""C-011: refuse anything but the endpoint_gray127_v1 cache, then hand over to the unchanged C-009 wrapper
(white_v1 + per-file sha + legacy/layout-parent refusal) and the unchanged C-006 trainer."""
from pathlib import Path
import json
import runpy
import sys


def main() -> None:
    wrapper, trainer, config_path = (Path(a) for a in sys.argv[1:4])
    assert wrapper.is_absolute() and trainer.is_absolute() and config_path.is_absolute()
    config = json.loads(config_path.read_text())
    manifest = json.loads((Path(config['cache_root']) / 'CACHE_MANIFEST.json').read_text())
    if manifest.get('condition_family') != 'endpoint_gray127_v1':
        raise SystemExit(f"NOT_ENDPOINT_CACHE: {manifest.get('condition_family')}")
    print(json.dumps({'condition_family': manifest['condition_family']}), flush=True)
    sys.argv = [str(wrapper), str(trainer), str(config_path), *sys.argv[4:]]
    runpy.run_path(str(wrapper), run_name='__main__')


if __name__ == '__main__':
    main()
