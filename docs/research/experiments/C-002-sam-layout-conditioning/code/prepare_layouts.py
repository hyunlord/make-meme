"""Render frozen C001 selected SAM masks as official-style layout contours (CPU only)."""
from pathlib import Path
import hashlib
import json
import sys
import cv2
import numpy as np
from PIL import Image


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def render(mask: np.ndarray) -> np.ndarray:
    if mask.dtype != np.uint8 or mask.shape != (480, 832):
        raise ValueError('Expected original uint8 480x832 SAM mask')
    if not set(np.unique(mask)).issubset({0, 255}) or not np.any(mask):
        raise ValueError('Expected nonempty binary SAM mask; no repair is permitted')
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    canvas = np.full((480, 832, 3), 255, dtype=np.uint8)
    cv2.drawContours(canvas, contours, -1, (0, 0, 0), 3)
    return canvas


def prepare(c001: Path, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=False)
    summary = {'schema': 'C002_LAYOUT_V1', 'origin': 'C001 selected SAM3.1 masks',
               'render': {'contour_mode': 'RETR_EXTERNAL', 'contour_method': 'CHAIN_APPROX_SIMPLE',
                          'thickness': 3, 'foreground': [0,0,0], 'background': [255,255,255],
                          'dtype': 'uint8', 'channels': 'RGB', 'augmentation': False},
               'opencv_version': cv2.__version__, 'cases': {}}
    for case in ('case_rigid', 'case_nonrigid'):
        source = c001/'analysis'/case/'source'
        objects = json.loads((source/'objects.json').read_text())
        manifest = json.loads((c001/'inputs'/case/'manifest.json').read_text())
        assert len(objects) == len(manifest['records']) == 33
        destination = output/case/'layout'; destination.mkdir(parents=True)
        records = []
        for i, (obj, src) in enumerate(zip(objects, manifest['records'], strict=True)):
            assert obj['index'] == src['model_index'] == i
            assert obj['role'] == 'edited_subject' and obj['mask_source'] == 'SAM3.1' and obj['visible']
            path = source/f'{i:03d}-mask.png'
            with Image.open(path) as im: mask = np.array(im)
            canvas = render(mask)
            assert int(np.count_nonzero(mask)) == obj['area']
            ys, xs = np.where(mask > 0)
            assert obj['bbox'] == [int(xs.min()), int(ys.min()), int(xs.max()+1), int(ys.max()+1)]
            target = destination/f'{i:03d}.png'; Image.fromarray(canvas).save(target)
            with Image.open(target) as im:
                assert im.mode == 'RGB' and im.size == (832,480)
                assert np.array_equal(np.array(im), canvas)
            records.append({'index': i, 'source_index': src['source_index'], 'mask_sha256': sha(path),
                            'source_rgb_sha256': sha(c001/'inputs'/case/'source'/f'{i:03d}.png'),
                            'layout_sha256': sha(target), 'sam_area': obj['area'], 'sam_bbox': obj['bbox'],
                            'black_pixels': int(np.sum(canvas[:,:,0] == 0))})
        summary['cases'][case] = records
    (output/'layout-manifest.json').write_text(json.dumps(summary, indent=2)+'\n')
    print(json.dumps({'status':'PASS', 'layouts':66, 'manifest_sha256':sha(output/'layout-manifest.json')}))


if __name__ == '__main__':
    prepare(Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve())
