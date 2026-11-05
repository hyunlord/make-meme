"""Existing-local SigLIP crop embeddings; reference-only, never a gate.

Run with existing research Python: embed_images.py PRIVATE_RUNTIME.json [--cpu-only]
Private runtime keys: scene_config, model_path, output, reference_id,
device (cpu/cuda), cpu_threads, batch_size, items.
Each item has id, image, summary, frame_index and casting_report (G1-G6 JSON).
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, assert_never
import hashlib
import json
import math
import os
import resource
import sys
import time

from PIL import Image


@dataclass(frozen=True, slots=True)
class Item:
    identifier: str
    image: Path
    summary: Path
    frame_index: int
    casting_report: Path


@dataclass(frozen=True, slots=True)
class Config:
    scene: Path
    model: Path
    output: Path
    reference_id: str
    device: Literal['cpu', 'cuda']
    threads: int
    batch: int
    roles: tuple[str, ...]
    size: tuple[int, int]
    items: tuple[Item, ...]

    @classmethod
    def read(cls, path: Path) -> Config:
        """Resolve all inputs before torch or transformers are imported."""
        raw = json.loads(path.read_text())
        scene_path = Path(raw['scene_config'])
        scene = json.loads(scene_path.read_text())
        items = tuple(Item(row['id'], Path(row['image']), Path(row['summary']), row['frame_index'],
                           Path(row['casting_report'])) for row in raw['items'])
        cfg = cls(scene_path, Path(raw['model_path']), Path(raw['output']), raw['reference_id'],
                  raw['device'], raw['cpu_threads'], raw['batch_size'],
                  tuple(scene['scene']['casting_track_indices']),
                  tuple(scene['anchor_generation']['resolution_master']), items)
        assert cfg.device in ('cpu', 'cuda') and cfg.threads > 0 and cfg.batch > 0
        assert cfg.model.is_absolute() and cfg.model.is_dir()
        assert (cfg.model/'config.json').is_file() and (cfg.model/'model.safetensors').is_file()
        assert len({item.identifier for item in items}) == len(items)
        assert cfg.reference_id in {item.identifier for item in items}
        assert not cfg.output.exists(), 'Preserve earlier embedding reports'
        return cfg


def crop_bounds(item: Item, roles: tuple[str, ...], size: tuple[int, int]) -> dict[str, tuple[int, int, int, int]]:
    """Use the saved gate correspondence and SAM bbox, without reassigning roles."""
    summary = json.loads(item.summary.read_text())
    assert tuple(summary['coordinate_size']) == size
    frame = next(row for row in summary['frames'] if row['index'] == item.frame_index)
    objects = {row['track_index']: row for row in frame['objects']}
    casting = json.loads(item.casting_report.read_text())['casting']
    bounds = {}
    for role in roles:
        row = objects[casting[role]]
        assert row['present'] and row['bbox'] is not None
        x0, y0, x1, y1 = row['bbox']
        box = (math.floor(x0), math.floor(y0), math.ceil(x1), math.ceil(y1))
        assert 0 <= box[0] < box[2] <= size[0] and 0 <= box[1] < box[3] <= size[1]
        bounds[role] = box
    return bounds


def crops(item: Item, roles: tuple[str, ...], size: tuple[int, int]) -> list[Image.Image]:
    """Read unmodified RGB bbox crops; processor handles the model's input resize."""
    bounds = crop_bounds(item, roles, size)
    with Image.open(item.image) as image:
        assert image.size == size
        rgb = image.convert('RGB')
        return [rgb.crop(bounds[role]) for role in roles]


def atomic_report(output: Path, payload: str) -> None:
    temporary = output.with_suffix(output.suffix+'.partial')
    output.parent.mkdir(parents=True, exist_ok=True)
    with temporary.open('x') as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(output)
    assert output.read_text() == payload


def main() -> None:
    cfg = Config.read(Path(sys.argv[1]))
    for item in cfg.items:
        for crop in crops(item, cfg.roles, cfg.size):
            crop.close()
    if '--cpu-only' in sys.argv:
        print(json.dumps({'status': 'CPU_ENTRY_PASS', 'items': len(cfg.items),
                          'crops': len(cfg.items)*len(cfg.roles), 'torch_imported': 'torch' in sys.modules}))
        return
    started = time.time()
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TRANSFORMERS_OFFLINE'] = '1'
    import torch
    from transformers import AutoImageProcessor, SiglipVisionModel
    torch.set_num_threads(cfg.threads)
    match cfg.device:
        case 'cpu':
            dtype = torch.float32
        case 'cuda':
            assert torch.cuda.is_available()
            dtype = torch.bfloat16
        case unreachable:
            assert_never(unreachable)
    processor = AutoImageProcessor.from_pretrained(str(cfg.model), local_files_only=True)
    model = SiglipVisionModel.from_pretrained(str(cfg.model), local_files_only=True,
                                              torch_dtype=dtype).to(cfg.device).eval().requires_grad_(False)
    vectors = {}
    with torch.inference_mode():
        for item in cfg.items:
            images = crops(item, cfg.roles, cfg.size)
            item_vectors = []
            for offset in range(0, len(images), cfg.batch):
                inputs = processor(images=images[offset:offset+cfg.batch], return_tensors='pt')
                pixel_values = inputs['pixel_values'].to(device=cfg.device, dtype=dtype)
                pooled = model(pixel_values=pixel_values).pooler_output.float()
                assert bool(torch.isfinite(pooled).all())
                norms = pooled.norm(dim=-1, keepdim=True)
                assert bool((norms > 0).all())
                item_vectors.extend((pooled/norms).cpu())
            vectors[item.identifier] = dict(zip(cfg.roles, item_vectors))
            for crop in images:
                crop.close()
    baseline = vectors[cfg.reference_id]
    rows = []
    for item in cfg.items:
        rows.append({'id': item.identifier,
                     'cosine_vs_reference': {role: float(torch.dot(vectors[item.identifier][role], baseline[role]))
                                              for role in cfg.roles},
                     'crop_bbox': crop_bounds(item, cfg.roles, cfg.size),
                     'image_sha256': hashlib.sha256(item.image.read_bytes()).hexdigest(),
                     'sam_summary_sha256': hashlib.sha256(item.summary.read_bytes()).hexdigest(),
                     'casting_report_sha256': hashlib.sha256(item.casting_report.read_bytes()).hexdigest()})
    aggregate = {role: {'minimum': min(row['cosine_vs_reference'][role] for row in rows),
                        'mean': sum(row['cosine_vs_reference'][role] for row in rows)/len(rows)}
                 for role in cfg.roles}
    report = {'status': 'MEASURED_REFERENCE_ONLY', 'gate': False, 'reference_id': cfg.reference_id,
              'feature': 'SiglipVisionModel.pooler_output; L2 normalized',
              'crop': 'SAM bbox RGB, unmasked; official local image processor',
              'device': cfg.device, 'dtype': str(dtype), 'items': rows, 'aggregate': aggregate,
              'model_revision': cfg.model.name, 'local_files_only': True,
              'model_config_sha256': hashlib.sha256((cfg.model/'config.json').read_bytes()).hexdigest(),
              'scene_config_sha256': hashlib.sha256(cfg.scene.read_bytes()).hexdigest(),
              'elapsed_seconds': time.time()-started, 'finished_unix': time.time(),
              'peak_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
    atomic_report(cfg.output, json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({'status': report['status'], 'items': len(rows), 'elapsed_seconds': report['elapsed_seconds']}))


if __name__ == '__main__':
    main()
