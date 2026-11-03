# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# Run: existing E1 Python vda_entry.py /absolute/private-config.json [--cpu-only]
"""One official Video Depth Anything Large call for frozen E1 source control."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Final
import hashlib
import io
import json
import os
import resource
import subprocess
import sys
import time

REVISION: Final = '4f5ae23172ba60fd7bc11ef671cca678842c7072'
SHAPE: Final = (73, 576, 1024)


@dataclass(frozen=True, slots=True)
class Config:
    engine_root: Path
    checkpoint: Path
    source: Path
    output: Path
    ffprobe: Path

    @classmethod
    def read(cls, path: Path) -> Config:
        """Accept only the private path mapping; inference settings are fixed here."""
        raw = json.loads(path.read_text())
        names = ('engine_root', 'checkpoint', 'source', 'output', 'ffprobe')
        if set(raw) != set(names):
            raise ValueError(f'Expected exactly {names}')
        cfg = cls(*(Path(raw[name]) for name in names))
        for name in names:
            value = getattr(cfg, name)
            if not value.is_absolute():
                raise ValueError(f'{name} must be absolute')
            if name != 'output' and not value.exists():
                raise FileNotFoundError(value)
        if cfg.output.exists():
            raise FileExistsError(cfg.output)
        actual = subprocess.check_output(['git', '-C', str(cfg.engine_root), 'rev-parse', 'HEAD'], text=True).strip()
        if actual != REVISION:
            raise ValueError(f'Unexpected VDA revision {actual}')
        validate_video(cfg.ffprobe, cfg.source)
        return cfg


def validate_video(ffprobe: Path, video: Path) -> None:
    """Require exact source/output dimensions, frame count and presentation rate."""
    result = subprocess.run([str(ffprobe), '-v', 'error', '-select_streams', 'v:0', '-count_frames',
        '-show_entries', 'stream=width,height,nb_read_frames,r_frame_rate', '-of', 'json', str(video)],
        check=True, capture_output=True, text=True)
    streams = json.loads(result.stdout)['streams']
    assert len(streams) == 1
    stream = streams[0]
    assert (int(stream['nb_read_frames']), stream['height'], stream['width']) == SHAPE
    numerator, denominator = map(int, stream['r_frame_rate'].split('/'))
    assert numerator == 24 * denominator


def atomic_bytes(path: Path, data: bytes) -> str:
    """Publish an output only after complete write and compare readback hash."""
    temporary = path.with_name(path.name + '.partial')
    with temporary.open('xb') as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)
    digest = hashlib.sha256(data).hexdigest()
    assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
    return digest


def sha256(path: Path) -> str:
    with path.open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def main() -> None:
    cfg = Config.read(Path(sys.argv[1]))
    if '--cpu-only' in sys.argv:
        assert 'torch' not in sys.modules and 'video_depth_anything' not in sys.modules
        print(json.dumps({'status': 'CPU_VALIDATED', 'torch_imported': False,
                          'frames': SHAPE[0], 'size': [SHAPE[2], SHAPE[1]], 'revision': REVISION}))
        return
    cfg.output.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    receipt = {'status': 'STARTED', 'revision': REVISION, 'encoder': 'vitl', 'input_size': 518,
               'target_fps': 24, 'fp32': False, 'metric': False, 'infer_video_depth_calls': 0,
               'model_forward_calls': 0, 'normalization': 'official whole-clip min/max grayscale',
               'source_sha256': sha256(cfg.source),
               'checkpoint_sha256': sha256(cfg.checkpoint)}
    atomic_bytes(cfg.output/'receipt.json', json.dumps(receipt, indent=2).encode())
    sys.path.insert(0, str(cfg.engine_root))
    import numpy as np
    import torch
    from PIL import Image
    from video_depth_anything.video_depth import VideoDepthAnything
    from utils.dc_utils import read_video_frames, save_video

    try:
        model = VideoDepthAnything(encoder='vitl', features=256,
                                  out_channels=[256, 512, 1024, 1024], metric=False)
        model.load_state_dict(torch.load(str(cfg.checkpoint), map_location='cpu', weights_only=True), strict=True)
        model = model.to('cuda').eval()
        model.requires_grad_(False)
        frames, fps = read_video_frames(str(cfg.source), process_length=73, target_fps=24, max_res=1280)
        assert frames.shape == (*SHAPE, 3) and fps == 24

        original_forward = model.forward

        def counted_forward(*inputs, **kwargs):
            receipt['model_forward_calls'] += 1
            return original_forward(*inputs, **kwargs)

        # Official infer_video_depth calls self.forward directly, bypassing module hooks.
        model.forward = counted_forward
        torch.cuda.synchronize()
        infer_start = time.perf_counter()
        receipt['infer_video_depth_calls'] += 1
        with torch.inference_mode():
            depths, fps = model.infer_video_depth(frames, fps, input_size=518, device='cuda', fp32=False)
        torch.cuda.synchronize()
        model.forward = original_forward
        receipt['infer_seconds'] = time.perf_counter()-infer_start
        assert depths.shape == SHAPE and fps == 24 and np.isfinite(depths).all()
        lower, upper = depths.min(), depths.max()
        assert upper > lower
        buffer = io.BytesIO()
        np.savez_compressed(buffer, depths=depths)
        receipt['depths_sha256'] = atomic_bytes(cfg.output/'depths.npz', buffer.getvalue())
        with np.load(cfg.output/'depths.npz') as saved:
            assert np.array_equal(saved['depths'], depths)
        pngs = cfg.output/'frames'
        pngs.mkdir()
        frame_hashes = []
        for index, depth in enumerate(depths):
            # Identical normalization to official utils.dc_utils.save_video(grayscale=True).
            pixels = ((depth-lower)/(upper-lower)*255).astype(np.uint8)
            buffer = io.BytesIO()
            Image.fromarray(pixels).save(buffer, format='PNG')
            target = pngs/f'{index:03d}.png'
            frame_hashes.append(atomic_bytes(target, buffer.getvalue()))
            with Image.open(target) as readback:
                assert np.array_equal(np.asarray(readback), pixels)
        temporary = cfg.output/'control.partial.mp4'
        save_video(depths, str(temporary), fps=24, is_depths=True, grayscale=True)
        validate_video(cfg.ffprobe, temporary)
        temporary.replace(cfg.output/'control.mp4')
        receipt.update(status='DEPTH_COMPLETE', frames=73, width=1024, height=576,
                       depth_min=float(lower), depth_max=float(upper), frame_sha256=frame_hashes)
        with (cfg.output/'control.mp4').open('rb') as handle:
            receipt['control_sha256'] = hashlib.file_digest(handle, 'sha256').hexdigest()
    finally:
        receipt.update(elapsed_seconds=time.perf_counter()-started,
                       peak_cuda_allocated_bytes=torch.cuda.max_memory_allocated(),
                       peak_cuda_reserved_bytes=torch.cuda.max_memory_reserved(),
                       peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
        if receipt['status'] != 'DEPTH_COMPLETE':
            receipt['status'] = 'INCOMPLETE_NO_AUTOMATIC_RETRY'
        atomic_bytes(cfg.output/'receipt.json', json.dumps(receipt, indent=2).encode())
    print(json.dumps({key: value for key, value in receipt.items() if key != 'frame_sha256'}))


if __name__ == '__main__':
    main()
