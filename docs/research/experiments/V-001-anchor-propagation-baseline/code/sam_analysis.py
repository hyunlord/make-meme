# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# Run: existing research Python sam_analysis.py /absolute/config.json [--cpu-only]
"""V-001 instance masks using the existing ComfyUI SAM3.1 integration."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Final, Literal, TypedDict, assert_never
import hashlib
import json
import os
import resource
import sys
import time

if TYPE_CHECKING:
    import numpy as np
    from numpy.typing import NDArray

SIZE: Final = (1280, 720)
MIN_AREA: Final = 0.005


@dataclass(frozen=True, slots=True)
class Config:
    frames: Path
    output: Path
    checkpoint: Path
    comfy_root: Path
    revision: str
    mode: Literal['video', 'image']

    @classmethod
    def read(cls, path: Path) -> Config:
        """Parse the private configuration before any model imports."""
        raw = json.loads(path.read_text())
        cfg = cls(*(Path(raw[key]) for key in ('frames', 'output', 'checkpoint', 'comfy_root')),
                  revision=raw['revision'], mode=raw['mode'])
        assert all(p.is_absolute() for p in (cfg.frames, cfg.output, cfg.checkpoint, cfg.comfy_root))
        assert cfg.frames.is_dir() and cfg.checkpoint.is_file() and cfg.comfy_root.is_dir()
        assert cfg.mode in ('video', 'image') and cfg.revision
        return cfg


class ObjectRow(TypedDict):
    track_index: int
    area: int
    area_fraction: float
    center: list[float] | None
    bbox: list[int] | None
    present: bool
    meets_area_minimum: bool


def describe(mask: NDArray[np.bool_], index: int) -> ObjectRow:
    """Retain missing and tiny masks instead of silently selecting two objects."""
    import numpy as np
    yy, xx = np.where(mask)
    area = len(xx)
    return {'track_index': index, 'area': area, 'area_fraction': area / mask.size,
            'center': [float(xx.mean()), float(yy.mean())] if area else None,
            'bbox': [int(xx.min()), int(yy.min()), int(xx.max()+1), int(yy.max()+1)] if area else None,
            'present': area > 0, 'meets_area_minimum': area / mask.size >= MIN_AREA}


def atomic_bytes(path: Path, data: bytes) -> str:
    """Replace one new output atomically and verify its bytes on disk."""
    temporary = path.with_name(path.name + '.partial')
    with temporary.open('xb') as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)
    digest = hashlib.sha256(data).hexdigest()
    assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
    return digest


def main() -> None:
    from PIL import Image
    cfg = Config.read(Path(sys.argv[1]))
    paths = sorted(cfg.frames.glob('*.png'))
    assert paths
    match cfg.mode:
        case 'image':
            assert len(paths) == 1
        case 'video':
            assert len(paths) in (49, 73)
        case unreachable:
            assert_never(unreachable)
    for path in paths:
        with Image.open(path) as image:
            assert image.size == SIZE
            image.verify()
    if '--cpu-only' in sys.argv:
        print(json.dumps({'status': 'CPU_ENTRY_PASS', 'images_verified': len(paths),
                          'torch_imported': 'torch' in sys.modules, 'coordinate_size': SIZE}))
        return
    started = time.time()
    cfg.output.mkdir(parents=True, exist_ok=True)
    with (cfg.output / 'attempt.json').open('x') as handle:
        json.dump({'started': started, 'kind': 'SAM_ANALYSIS_ONLY', 'mode': cfg.mode}, handle)
    sys.argv = [sys.argv[0]]
    sys.path.insert(0, str(cfg.comfy_root))
    import io
    import numpy as np
    import torch
    import torch.nn.functional as functional
    import comfy.sd
    import comfy.model_management
    from comfy.ldm.sam3.tracker import unpack_masks
    from comfy_extras.nodes_sam3 import SAM3_Detect, SAM3_VideoTrack

    frames = torch.stack([torch.from_numpy(np.asarray(Image.open(path).convert('RGB')).copy()).float()/255
                          for path in paths])
    model, clip, _, _ = comfy.sd.load_checkpoint_guess_config(str(cfg.checkpoint), output_vae=False)
    summary = {'status': 'RUNNING', 'implementation': 'existing ComfyUI SAM3.1',
               'revision': cfg.revision, 'mode': cfg.mode, 'query': 'dog', 'threshold': 0.5,
               'max_objects': 4, 'detect_interval': 1, 'coordinate_size': list(SIZE),
               'casting_assignment': 'UNASSIGNED_TRACK_INDICES', 'frames': [],
               'input_sha256': [hashlib.sha256(path.read_bytes()).hexdigest() for path in paths]}
    try:
        with torch.inference_mode():
            conditioning = clip.encode_from_tokens_scheduled(clip.tokenize('dog'))
            packed = None
            detected = None
            match cfg.mode:
                case 'video':
                    tracked = SAM3_VideoTrack.execute(frames, model, conditioning=conditioning,
                                                     detection_threshold=0.5, max_objects=4, detect_interval=1)[0]
                    packed = tracked['packed_masks']
                    if packed is not None:
                        assert packed.shape[0] == len(paths)
                        buffer = io.BytesIO()
                        np.savez_compressed(buffer, masks=packed.cpu().numpy())
                        atomic_bytes(cfg.output/'sam_raw_packed.npz', buffer.getvalue())
                        with np.load(cfg.output/'sam_raw_packed.npz') as saved:
                            assert np.array_equal(saved['masks'], packed.cpu().numpy())
                case 'image':
                    # Official Detect defaults to one detection per ordinary text prompt.
                    # Its existing multi-conditioning contract exposes the count cap.
                    metadata = conditioning[0][1]
                    metadata['sam3_multi_cond'] = [{'cond': conditioning[0][0],
                        'attention_mask': metadata.get('attention_mask'), 'max_detections': 4}]
                    detected, boxes = SAM3_Detect.execute(model, frames, conditioning=conditioning,
                                    threshold=0.5, refine_iterations=2, individual_masks=True)
                    summary['detection_boxes'] = boxes
                case unreachable:
                    assert_never(unreachable)
            for frame_index in range(len(paths)):
                if packed is not None:
                    raw_masks = unpack_masks(packed[frame_index:frame_index+1]).float()
                    frame_masks = functional.interpolate(raw_masks, size=(SIZE[1], SIZE[0]),
                                                         mode='bilinear', align_corners=False)[0] > 0.5
                elif detected is not None:
                    frame_masks = detected > 0.5
                else:
                    frame_masks = torch.zeros((0, SIZE[1], SIZE[0]), dtype=torch.bool)
                objects = []
                for index, mask in enumerate(frame_masks):
                    array = mask.cpu().numpy().astype(bool)
                    objects.append(describe(array, index))
                    buffer = io.BytesIO()
                    Image.fromarray(array.astype('uint8')*255).save(buffer, format='PNG')
                    target = cfg.output/f'{frame_index:03d}-track-{index:02d}.png'
                    atomic_bytes(target, buffer.getvalue())
                    with Image.open(target) as readback:
                        assert np.array_equal(np.asarray(readback)>0, array)
                present = [row for row in objects if row['present']]
                frame_ok = len(present) == 2 and all(row['meets_area_minimum'] for row in present)
                summary['frames'].append({'index': frame_index, 'objects': objects,
                                          'dog_count': len(present), 'two_dog_area_gate': frame_ok})
                atomic_bytes(cfg.output/'progress.json', json.dumps(summary, indent=2).encode())
        torch.cuda.synchronize()
        summary['cuda_peak_allocated_bytes'] = torch.cuda.max_memory_allocated()
        summary['cuda_peak_reserved_bytes'] = torch.cuda.max_memory_reserved()
    finally:
        comfy.model_management.unload_all_models()
        torch.cuda.empty_cache()
    valid_frames = sum(frame['two_dog_area_gate'] for frame in summary['frames'])
    summary.update(status='SAM_ANALYSIS_COMPLETED', valid_frames=valid_frames,
                   frame_count=len(paths), elapsed_seconds=time.time()-started,
                   finished=time.time(), process_max_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    if len(paths) == 73:
        summary['segment_status'] = 'SEGMENT_ESTABLISHED' if valid_frames >= 66 else 'SEGMENT_NOT_ESTABLISHED'
    atomic_bytes(cfg.output/'summary.json', json.dumps(summary, indent=2).encode())
    print(json.dumps({key: value for key, value in summary.items() if key not in ('frames', 'input_sha256')}))


if __name__ == '__main__':
    main()
