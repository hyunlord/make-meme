"""CPU-only amendment4 geometry preparation; never loads VDA or Torch."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

EXPECTED_DEPTH_SHA = '11debd60bfdd02cea8e7fe3d52a02f0f626c7023a9cf55ae9a20644d53fd9181'
REVISION = '4f5ae23172ba60fd7bc11ef671cca678842c7072'


def sha256(path: Path) -> str:
    with path.open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def main() -> None:
    import numpy as np
    from PIL import Image

    raw = json.loads(Path(sys.argv[1]).read_text())
    names = {'source_frames', 'anchor', 'depths', 'engine_root', 'output', 'ffmpeg', 'ffprobe'}
    assert set(raw) == names and all(Path(raw[key]).is_absolute() for key in names)
    output = Path(raw['output'])
    assert not output.exists() and output.parent.is_dir()
    assert sha256(Path(raw['depths'])) == EXPECTED_DEPTH_SHA
    revision = subprocess.check_output(['git', '-C', raw['engine_root'], 'rev-parse', 'HEAD'], text=True).strip()
    assert revision == REVISION
    source = [Path(raw['source_frames']) / f'{i:03d}.png' for i in range(73)]
    for path in [*source, Path(raw['anchor'])]:
        with Image.open(path) as image:
            assert image.size == (1280, 720), (path.name, image.size)
    with np.load(raw['depths'], allow_pickle=False) as saved:
        depths = saved['depths'].copy()
    assert depths.shape == (73, 576, 1024) and np.isfinite(depths).all()
    assert 1152 % 128 == 640 % 128 == (73 - 1) % 8 == 0
    assert 'torch' not in sys.modules and 'video_depth_anything' not in sys.modules
    if '--cpu-only' in sys.argv:
        print(json.dumps({'status': 'CPU_INPUTS_VALIDATED', 'frames': 73, 'width': 1152, 'height': 640,
                          'raw_depth_sha256': EXPECTED_DEPTH_SHA, 'new_model_loads': 0}))
        return
    output.mkdir()
    (output / 'source').mkdir()
    (output / 'depth-frames').mkdir()
    inputs = {str(path): sha256(path) for path in [*source, Path(raw['anchor']), Path(raw['depths'])]}
    for index, path in enumerate([*source, Path(raw['anchor'])]):
        target = output / 'source' / f'{index:03d}.png' if index < 73 else output / 'anchor.png'
        with Image.open(path) as image:
            image.convert('RGB').resize((1152, 648), Image.Resampling.BILINEAR).crop((0, 4, 1152, 644)).save(target)
    resized = np.stack([
        np.asarray(Image.fromarray(frame.astype(np.float32)).resize((1152, 648), Image.Resampling.BILINEAR)
                   .crop((0, 4, 1152, 644)), dtype=np.float32)
        for frame in depths
    ])
    assert resized.shape == (73, 640, 1152) and np.isfinite(resized).all()
    lower, upper = resized.min(), resized.max()
    assert upper > lower
    np.savez_compressed(output / 'depths.npz', depths=resized)
    for index, frame in enumerate(resized):
        normalized = ((frame-lower)/(upper-lower)*255).astype(np.uint8)
        Image.fromarray(normalized).save(output / 'depth-frames' / f'{index:03d}.png')
    # Reuse the already verified official CPU writer, including its fixed global normalization.
    sys.path.insert(0, raw['engine_root'])
    import matplotlib
    import matplotlib.cm as cm
    from utils.dc_utils import save_video
    if not hasattr(cm, 'get_cmap'):
        cm.get_cmap = matplotlib.colormaps.get_cmap
    os.environ["IMAGEIO_FFMPEG_EXE"] = raw["ffmpeg"]
    save_video(resized, str(output / 'control.mp4'), fps=24, is_depths=True, grayscale=True)
    result = subprocess.check_output([raw['ffprobe'], '-v', 'error', '-select_streams', 'v:0',
        '-count_frames', '-show_entries', 'stream=width,height,nb_read_frames,r_frame_rate',
        '-of', 'json', str(output / 'control.mp4')], text=True)
    info = json.loads(result)['streams'][0]
    assert (info['width'], info['height'], int(info['nb_read_frames']), info['r_frame_rate']) == (1152, 640, 73, '24/1')
    assert 'torch' not in sys.modules and 'video_depth_anything' not in sys.modules
    assert all(sha256(Path(path)) == digest for path, digest in inputs.items())
    manifest = {'status': 'CPU_INPUTS_PREPARED', 'inputs': inputs,
        'outputs': {str(path.relative_to(output)): sha256(path) for path in sorted(output.rglob('*')) if path.is_file()},
        'geometry': 'RGB1280x720/depth1024x576 -> bilinear1152x648 -> crop(0,4,1152,644)',
        'depth_normalization': 'official global min/max over all73 resized frames; uint8 truncation',
        'depth_min': float(lower), 'depth_max': float(upper), 'width': 1152, 'height': 640,
        'frames': 73, 'fps': 24, 'encoder': 'official grayscale libx264 CRF18',
        'vda_revision': REVISION, 'new_model_loads': 0, 'new_depth_calls': 0, 'torch_imported': False}
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print(json.dumps({'status': manifest['status'], 'manifest_sha256': sha256(output / 'manifest.json')}))


if __name__ == '__main__':
    main()
