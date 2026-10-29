"""Frozen C003 bbox-normalized internal structure, using cached official scribble."""
from dataclasses import dataclass
from pathlib import Path
import hashlib
import json
import sys
import time
import cv2
import numpy as np
from PIL import Image


@dataclass(frozen=True, slots=True)
class Paths:
    source: str
    masks: str
    layouts: str
    scribble: str
    output: str


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path) -> np.ndarray:
    with Image.open(path) as im:
        return np.array(im)


def interior(mask: np.ndarray, layout: np.ndarray) -> np.ndarray:
    assert mask.dtype == np.uint8 and mask.shape == (480,832)
    assert set(np.unique(mask)).issubset({0,255}) and np.any(mask)
    assert layout.dtype == np.uint8 and layout.shape == (480,832,3)
    assert np.array_equal(layout[...,0],layout[...,1]) and np.array_equal(layout[...,0],layout[...,2])
    distance = cv2.distanceTransform((mask > 0).astype(np.uint8), cv2.DIST_L2, cv2.DIST_MASK_PRECISE)
    return (distance > 4.0) & (layout[...,0] == 255)


def bbox(mask: np.ndarray) -> tuple[int,int,int,int]:
    y,x = np.nonzero(mask)
    return int(x.min()),int(y.min()),int(x.max()+1),int(y.max()+1)


def normalize(field: np.ndarray, box: tuple[int,int,int,int]) -> np.ndarray:
    x0,y0,x1,y1 = box
    return cv2.resize(field[y0:y1,x0:x1],(256,256),interpolation=cv2.INTER_LINEAR)


def restore(field: np.ndarray, box: tuple[int,int,int,int]) -> np.ndarray:
    x0,y0,x1,y1 = box
    result = np.zeros((480,832),np.float32)
    result[y0:y1,x0:x1] = cv2.resize(field,(x1-x0,y1-y0),interpolation=cv2.INTER_LINEAR)
    return result


def composite(layout: np.ndarray, allowed: np.ndarray, darkness: np.ndarray) -> np.ndarray:
    result = layout.copy()
    gray = np.rint(255.0*(1.0-np.clip(darkness,0.0,1.0))).astype(np.uint8)
    result[allowed] = np.repeat(gray[...,None],3,axis=2)[allowed]
    assert np.array_equal(result[~allowed],layout[~allowed])
    return result


def prepare(paths: Paths) -> None:
    started = time.monotonic()
    destination = Path(paths.output)
    assert all(Path(p).is_absolute() for p in (paths.source,paths.masks,paths.layouts,paths.scribble,paths.output))
    extraction = json.loads((Path(paths.scribble)/'extraction.json').read_text())
    assert extraction['status'] == 'COMPLETE' and extraction['frames'] == 33
    destination.mkdir(parents=True,exist_ok=False)
    for name in ('internal_dynamic','internal_hold','interior','normalized_darkness','normalized_interior'):
        (destination/name).mkdir()
    held = None
    records = []
    for t in range(33):
        sp = Path(paths.source)/f'{t:03d}.png'
        mp = Path(paths.masks)/f'{t:03d}-mask.png'
        lp = Path(paths.layouts)/f'{t:03d}.png'
        jp = Path(paths.scribble)/f'{t:03d}.png'
        assert extraction['records'][t]['index'] == t
        assert extraction['records'][t]['source_sha256'] == sha(sp)
        assert extraction['records'][t]['raw_sha256'] == sha(jp)
        mask,layout,j = read(mp),read(lp),read(jp)
        assert j.dtype == np.uint8 and j.shape == (480,832)
        allowed = interior(mask,layout)
        box = bbox(mask)
        darkness = allowed.astype(np.float32)*(1.0-j.astype(np.float32)/255.0)
        normalized = normalize(darkness,box)
        x0,y0,x1,y1 = box
        normalized_mask = cv2.resize(allowed[y0:y1,x0:x1].astype(np.uint8),(256,256),interpolation=cv2.INTER_NEAREST_EXACT)
        # Binary masks are diagnostic/support records, never grayscale-interpolated or a new G.
        Image.fromarray(normalized_mask*255).save(destination/'normalized_interior'/f'{t:03d}.png')
        np.save(destination/'normalized_darkness'/f'{t:03d}.npy',normalized,allow_pickle=False)
        if t == 0:
            held = normalized.copy()
        assert held is not None
        dynamic = composite(layout,allowed,restore(normalized,box))
        hold = composite(layout,allowed,restore(held,box))
        assert dynamic.dtype == hold.dtype == np.uint8
        for name,canvas in (('internal_dynamic',dynamic),('internal_hold',hold)):
            Image.fromarray(canvas).save(destination/name/f'{t:03d}.png')
            assert np.array_equal(read(destination/name/f'{t:03d}.png'),canvas)
        Image.fromarray(allowed.astype(np.uint8)*255).save(destination/'interior'/f'{t:03d}.png')
        records.append({'index':t,'source_sha256':sha(sp),'sam_sha256':sha(mp),'layout_sha256':sha(lp),
                        'scribble_sha256':sha(jp),'bbox_xyxy_halfopen':list(box),'interior_pixels':int(allowed.sum()),
                        'excluded_subject_pixels':int(np.count_nonzero(mask)-allowed.sum()),
                        'dynamic_sha256':sha(destination/'internal_dynamic'/f'{t:03d}.png'),
                        'hold_sha256':sha(destination/'internal_hold'/f'{t:03d}.png'),
                        'interior_sha256':sha(destination/'interior'/f'{t:03d}.png'),
                        'outside_interior_equal':True,'dynamic_darkness_sum':float(((255-dynamic[...,0])/255.0)[allowed].sum()),
                        'hold_darkness_sum':float(((255-hold[...,0])/255.0)[allowed].sum()),
                        'dynamic_hold_different_pixels':int(np.any(dynamic!=hold,axis=2).sum())})
    assert all(r['interior_pixels'] > 0 and r['dynamic_darkness_sum'] > 0 for r in records)
    assert sum(r['dynamic_hold_different_pixels'] for r in records[1:32]) > 0
    receipt = {'status':'PASS','frames':33,'records':records,'elapsed_seconds':time.monotonic()-started,
               'polarity':'official output unchanged: dark lines / light background, no threshold',
               'interior_rule':'cv2.distanceTransform DIST_L2 DIST_MASK_PRECISE > 4 AND layout_gray == 255',
               'normalization_size':[256,256],'bbox':'integer half-open [x0,y0,x1,y1), pixel edges',
               'pixel_centers':'source (x+0.5,y+0.5); normalized (j+0.5)/256 - 0.5',
               'sampling':'OpenCV INTER_LINEAR both crop-to-256 and inverse; masks INTER_NEAREST_EXACT; zero outside bbox',
               'edge_note':'cv2 resize edge replication; d is zero near SAM bbox boundary due to 4px interior, so replicated edge intensity is zero',
               'mask_sampling_note':'normalized binary I is diagnostic only; dN bilinear already contains I, inverse clipped by current I exactly as formula',
               'rounding':'numpy rint ties-to-even then uint8','opencv_version':cv2.__version__,
               'anchors':'these K images are middle candidates; video entry replaces indices0/32 with unchanged anchors',
               'tuning':False}
    (destination/'internal-manifest.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({'status':'PASS','manifest_sha256':sha(destination/'internal-manifest.json'),'seconds':receipt['elapsed_seconds']}))


if __name__ == '__main__':
    prepare(Paths(**json.loads(Path(sys.argv[1]).read_text())))
