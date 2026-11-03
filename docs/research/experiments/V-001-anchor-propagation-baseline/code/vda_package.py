# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# Run: E1 Python vda_package.py /absolute/original-depth-config.json [--cpu-only]
"""CPU packaging recovery for preserved VDA depths; never loads a model."""
from __future__ import annotations

from pathlib import Path
import json
import subprocess
import sys
import time

# Guard executes this entry through runpy, which does not add its directory.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from vda_entry import REVISION, SHAPE, atomic_bytes, sha256, validate_video

EXPECTED_DEPTH_SHA = '11debd60bfdd02cea8e7fe3d52a02f0f626c7023a9cf55ae9a20644d53fd9181'


def main() -> None:
    import numpy as np
    from PIL import Image

    raw = json.loads(Path(sys.argv[1]).read_text())
    names = {'engine_root', 'checkpoint', 'source', 'output', 'ffprobe'}
    assert set(raw) == names and all(Path(raw[key]).is_absolute() for key in names)
    output = Path(raw['output'])
    original = output/'receipt.json'
    original_sha = sha256(original)
    receipt = json.loads(original.read_text())
    assert receipt['depths_sha256'] == EXPECTED_DEPTH_SHA
    assert receipt['infer_video_depth_calls'] == 1 and receipt['model_forward_calls'] == 4
    assert sha256(output/'depths.npz') == EXPECTED_DEPTH_SHA
    revision = subprocess.check_output(['git', '-C', raw['engine_root'], 'rev-parse', 'HEAD'], text=True).strip()
    assert revision == REVISION
    with np.load(output/'depths.npz', allow_pickle=False) as saved:
        depths = saved['depths'].copy()
    assert depths.shape == SHAPE and np.isfinite(depths).all()
    lower, upper = depths.min(), depths.max()
    assert upper > lower
    files = sorted((output/'frames').glob('*.png'))
    assert len(files) == 73
    for index, path in enumerate(files):
        assert path.name == f'{index:03d}.png'
        expected = ((depths[index]-lower)/(upper-lower)*255).astype(np.uint8)
        with Image.open(path) as image:
            assert image.size == (1024, 576) and np.array_equal(np.asarray(image), expected)
    assert 'torch' not in sys.modules and 'video_depth_anything' not in sys.modules
    if '--cpu-only' in sys.argv:
        print(json.dumps({'status': 'CPU_PACKAGING_VALIDATED', 'png_exact': 73,
                          'depths_sha256': EXPECTED_DEPTH_SHA, 'torch_imported': False}))
        return
    target = output/'control.mp4'
    recovered_receipt = output/'packaging-recovery.json'
    assert not target.exists() and not recovered_receipt.exists()
    with (output/'packaging-recovery-attempt.json').open('x') as handle:
        json.dump({'started_epoch': time.time(), 'kind': 'CPU_PACKAGING_ONLY'}, handle)
    started = time.perf_counter()
    sys.path.insert(0, raw['engine_root'])
    import matplotlib
    import matplotlib.cm as cm
    from utils.dc_utils import save_video

    # Official save_video uses removed cm.get_cmap even on its grayscale branch.
    alias_added = not hasattr(cm, 'get_cmap')
    if alias_added:
        cm.get_cmap = matplotlib.colormaps.get_cmap
    partial = output/'control.recovery.partial.mp4'
    assert not partial.exists()
    save_video(depths, str(partial), fps=24, is_depths=True, grayscale=True)
    validate_video(Path(raw['ffprobe']), partial)
    partial.replace(target)
    assert sha256(original) == original_sha
    assert 'torch' not in sys.modules and 'video_depth_anything' not in sys.modules
    result = {'status': 'CPU_PACKAGING_RECOVERED', 'original_receipt_sha256': original_sha,
              'original_receipt_preserved': True, 'depths_sha256': EXPECTED_DEPTH_SHA,
              'png_exact': 73, 'frames': 73, 'width': 1024, 'height': 576, 'fps': 24,
              'control_sha256': sha256(target), 'elapsed_seconds': time.perf_counter()-started,
              'matplotlib_version': matplotlib.__version__, 'cm_get_cmap_alias_added': alias_added,
              'encoder': 'official save_video libx264 CRF18 grayscale',
              'torch_imported': False, 'new_model_loads': 0, 'new_depth_calls': 0}
    atomic_bytes(recovered_receipt, json.dumps(result, indent=2).encode())
    print(json.dumps(result))


if __name__ == '__main__':
    main()
