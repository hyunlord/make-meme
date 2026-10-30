"""One guarded source-only pass for three frozen, manually matched head points."""
from dataclasses import dataclass
from pathlib import Path
import json
import sys
import time
import numpy as np
import torch
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
from track_points import sha


@dataclass(frozen=True, slots=True)
class Config:
    data_root: str
    tracker_code: str
    checkpoint: str
    output: str
    correspondence: str
    device: str = 'cuda'


def run(config: Config, cpu_only: bool) -> None:
    for value in (config.data_root, config.tracker_code, config.checkpoint, config.output, config.correspondence):
        assert Path(value).is_absolute()
    data, out, checkpoint = Path(config.data_root), Path(config.output), Path(config.checkpoint)
    manual = json.loads(Path(config.correspondence).read_text())
    assert manual['scope'] == 'HEAD_ONLY' and manual['point_names'] == ['nose', 'screen_left_eye', 'screen_right_eye']
    points = np.asarray(manual['source']['0']['xy416'], dtype=np.float32)
    original = np.asarray(manual['source']['0']['xy832'], dtype=np.float32)
    assert points.shape == (3, 2) and np.array_equal(points, (original + 0.5) * 0.5 - 0.5)
    assert checkpoint.stat().st_size == 101890938
    assert sha(checkpoint) == '2670d4562ed69326dda775a26e54883925cd11b6fc9b24cb7aa9f8078bce7834'
    images, boxes = [], []
    for t in range(33):
        with Image.open(data/'source'/f'{t:03}.png') as image:
            assert image.mode == 'RGB' and image.size == (416, 240)
            images.append(np.array(image))
        with Image.open(data/'mask'/f'{t:03}.png') as mask:
            support = np.asarray(mask)
            assert support.shape == (240, 416)
            y, x = np.nonzero(support)
            assert len(x) > 0
            boxes.append([x.min(), y.min(), x.max()+1, y.max()+1])
    sys.path.insert(0, config.tracker_code)
    from cotracker.predictor import CoTrackerPredictor
    if cpu_only:
        assert not torch.cuda.is_initialized()
        print(json.dumps({'status': 'CPU_PASS', 'queries': 3, 'frames': 33, 'model_loads': 0, 'forward_calls': 0, 'cuda_initialized': False}))
        return
    out.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    predictor = CoTrackerPredictor(checkpoint=None, offline=True, v2=False, window_len=60)
    state = torch.load(checkpoint, map_location='cpu', weights_only=True)
    if 'model' in state:
        state = state['model']
    predictor.model.load_state_dict(state, strict=True)
    predictor.eval().requires_grad_(False).to(config.device)
    queries = np.column_stack((np.zeros(3, np.float32), points))
    with torch.inference_mode():
        video = torch.from_numpy(np.stack(images)).permute(0, 3, 1, 2).unsqueeze(0).float().to(config.device)
        tracks, visible = predictor(video, queries=torch.from_numpy(queries).unsqueeze(0).to(config.device), backward_tracking=False)
        q, v = tracks[0].cpu().numpy(), visible[0].cpu().numpy()
    assert q.shape == (33, 3, 2) and v.shape == (33, 3) and v.dtype == np.bool_
    valid = np.isfinite(q).all(axis=-1) & (q[..., 0] >= 0) & (q[..., 0] <= 415) & (q[..., 1] >= 0) & (q[..., 1] <= 239)
    anchor_valid = np.stack((valid[0] & v[0], valid[32] & v[32]))
    path = out/'tracks.npz'
    np.savez_compressed(path, tracks=q, visible=v, valid=valid, anchor_valid=anchor_valid,
                        bbox=np.asarray(boxes, np.float32), source_frame_ids=np.arange(33), queries=queries)
    with np.load(path, allow_pickle=False) as saved:
        assert np.array_equal(saved['tracks'], q, equal_nan=True)
    for t in (0, 4, 8, 12, 16, 20, 24, 28, 32):
        image = Image.fromarray(images[t]); draw = ImageDraw.Draw(image)
        for k, (x, y) in enumerate(q[t]):
            if valid[t, k]:
                color = 'lime' if v[t, k] else 'orange'
                draw.ellipse((x-2, y-2, x+2, y+2), fill=color)
                draw.text((x+3, y), str(k), fill=color)
        image.save(out/f'overlay-{t:03}.jpg', quality=92)
    endpoint_error = np.linalg.norm(q[32] - np.asarray(manual['source']['32']['xy416']), axis=-1)
    receipt = {'status': 'COMPLETE', 'scope': 'HEAD_ONLY', 'passes': 1, 'points': 3,
               'seconds': time.monotonic()-started, 'tracks_sha256': sha(path),
               'correspondence_sha256': sha(Path(config.correspondence)), 'source_manifest_sha256': sha(data/'manifest.json'),
               'checkpoint_sha256': sha(checkpoint), 'strict_load': True, 'weights_only': True,
               'offline': True, 'v2': False, 'window_len': 60, 'confidence': None,
               'anchor_valid': anchor_valid.tolist(), 'manual_source_end_error_px': endpoint_error.tolist(),
               'manual_endpoint_clamp': False, 'target_images_used_by_tracker': False,
               'limitations': 'Three visible head surface proxies only; manual points are not anatomical or contact GT.'}
    (out/'receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps(receipt), flush=True)


if __name__ == '__main__':
    run(Config(**json.loads(Path(sys.argv[1]).read_text())), '--cpu-only' in sys.argv)
