# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# Run: python render_task.py /abs/output_task_dir
"""C-012 deterministic CPU renderer: one patterned ball, same endpoints, opposite middle paths A/B.

ORACLE_RENDERER / TRAIN_TARGET only. Coordinates are pixel-index (pixel i has its centre at i);
normalized point coordinates follow C-006: (x + 0.5) / W, (y + 0.5) / H.
"""
from pathlib import Path
import hashlib
import json
import math
import sys

import cv2
import numpy as np
from PIL import Image

W, H, T = 416, 240, 33
D = 56                      # ball diameter (px)
S = 64                      # sprite canvas
SUPER = 8                   # sprite supersampling
BACKGROUND_SEED = 20261201  # static tabletop texture
PROMPT = 'A single patterned ball slides across a plain tabletop. The camera remains fixed.'
SAMPLE_FRAMES = (0, 4, 8, 12, 16, 20, 24, 28, 32)
# Four distinct static markers (shape differs so each can be matched alone); none is round.
MARKERS = {'cross': (30, 30), 'square': (386, 30), 'triangle': (30, 210), 'bar': (386, 210)}
POINT_OFFSETS = [(0.0, 0.0)] + [(14 * math.cos(k * math.pi / 4), 14 * math.sin(k * math.pi / 4)) for k in range(8)]


def path_center(path: str, tau: float) -> tuple[float, float]:
    """Pixel-index centre. Endpoint offset is exactly zero (no sin round-off at t=0,32)."""
    x = W * (0.25 + 0.50 * tau)
    offset = 0.0 if tau in (0.0, 1.0) else H * 0.20 * math.sin(math.pi * tau) ** 2
    sign = {'A': -1.0, 'B': 1.0}[path]
    return x, H * 0.50 + sign * offset


def sprite() -> np.ndarray:
    """Premultiplied float RGBA, disk centred at pixel-index (S-1)/2; fixed shading and asymmetric pattern."""
    n = S * SUPER
    coords = (np.arange(n) + 0.5) / SUPER - 0.5          # pixel-index coords of sub-samples
    yy, xx = np.meshgrid(coords, coords, indexing='ij')
    c = (S - 1) / 2
    u, v = (xx - c) / (D / 2), (yy - c) / (D / 2)         # unit disk coords
    r2 = u * u + v * v
    inside = r2 <= 1.0
    z = np.sqrt(np.clip(1 - r2, 0, 1))
    light = np.array([-0.45, -0.55, 0.70]); light /= np.linalg.norm(light)
    shade = 0.45 + 0.55 * np.clip(u * light[0] + v * light[1] + z * light[2], 0, 1)
    rgb = np.empty((n, n, 3)); rgb[:] = (222, 74, 42)                              # base: red-orange
    band = np.abs(v - 0.45 * u + 0.05) < 0.20                                      # tilted blue band
    rgb[band] = (40, 92, 205)
    rgb[(u + 0.38) ** 2 + (v + 0.42) ** 2 < 0.17 ** 2] = (250, 250, 245)            # white spot (upper-left)
    rgb[(u - 0.42) ** 2 + (v - 0.40) ** 2 < 0.16 ** 2] = (245, 205, 40)             # yellow spot (lower-right)
    rgb[(u - 0.55) ** 2 + (v + 0.30) ** 2 < 0.10 ** 2] = (30, 30, 30)               # small dark dot (upper-right)
    rgb = rgb * shade[..., None]
    alpha = inside.astype(np.float64)
    rgba = np.concatenate([rgb * alpha[..., None], alpha[..., None]], -1)
    return rgba.reshape(S, SUPER, S, SUPER, 4).mean((1, 3))


def background() -> np.ndarray:
    rng = np.random.default_rng(BACKGROUND_SEED)
    yy, xx = np.mgrid[0:H, 0:W]
    base = np.array([188.0, 176.0, 150.0])
    grain = 3.0 * np.sin(xx / 7.0 + 0.6 * np.sin(yy / 23.0))
    img = base[None, None] + grain[..., None] + rng.normal(0, 2.0, (H, W, 1))
    img = np.clip(img, 0, 255)
    ink = (38, 72, 60)
    x, y = MARKERS['cross']; cv2.line(img, (x - 7, y), (x + 7, y), ink, 3); cv2.line(img, (x, y - 7), (x, y + 7), ink, 3)
    x, y = MARKERS['square']; cv2.rectangle(img, (x - 6, y - 6), (x + 6, y + 6), ink, -1)
    x, y = MARKERS['triangle']; cv2.fillPoly(img, [np.array([[x, y - 8], [x - 8, y + 7], [x + 8, y + 7]], np.int32)], ink)
    x, y = MARKERS['bar']; cv2.rectangle(img, (x - 10, y - 3), (x + 10, y + 3), ink, -1)
    return img


def place(sprite_rgba: np.ndarray, cx: float, cy: float) -> np.ndarray:
    """Pure translation of the one sprite (bilinear, sub-pixel)."""
    c = (S - 1) / 2
    m = np.float32([[1, 0, cx - c], [0, 1, cy - c]])
    return cv2.warpAffine(sprite_rgba.astype(np.float32), m, (W, H), flags=cv2.INTER_LINEAR,
                          borderMode=cv2.BORDER_CONSTANT, borderValue=0)


def compose(bg: np.ndarray, layer: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    alpha = layer[..., 3:4]
    rgb = np.clip(np.rint(bg * (1 - alpha) + layer[..., :3]), 0, 255).astype(np.uint8)
    mask = (layer[..., 3] >= 0.5).astype(np.uint8) * 255
    return rgb, mask


def layout_from_mask(mask: np.ndarray) -> np.ndarray:
    """Same rule as C-006 data_prepare: white canvas, black external contour, thickness 3."""
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    layout = np.full((H, W, 3), 255, np.uint8)
    cv2.drawContours(layout, contours, -1, (0, 0, 0), 3)
    return layout


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def render(out: Path) -> dict:
    bg = background()
    spr = sprite()
    bg_u8 = np.clip(np.rint(bg), 0, 255).astype(np.uint8)
    endpoint = {}
    for t in (0, 32):
        cx, cy = path_center('A', t / 32)
        assert path_center('B', t / 32) == (cx, cy)
        endpoint[t] = compose(bg, place(spr, cx, cy))      # rendered ONCE, shared by A and B
    manifest = {'width': W, 'height': H, 'frames': T, 'diameter': D, 'prompt': PROMPT,
                'background_seed': BACKGROUND_SEED, 'markers': MARKERS, 'sprite_canvas': S, 'sprite_supersample': SUPER,
                'coordinates': 'pixel-index; normalized = (x+0.5)/W, (y+0.5)/H',
                'task_labels': ['ORACLE_RENDERER', 'TRAIN_TARGET', 'TRACK_GIVEN', 'MASK_GIVEN'],
                'point_offsets_px': POINT_OFFSETS, 'paths': {}}
    (out / 'anchors').mkdir(parents=True)
    Image.fromarray(endpoint[0][0]).save(out / 'anchors/start.png')
    Image.fromarray(endpoint[32][0]).save(out / 'anchors/end.png')
    Image.fromarray(bg_u8).save(out / 'background.png')
    for path in ('A', 'B'):
        root = out / path
        for sub in ('source', 'mask', 'layout'):
            (root / sub).mkdir(parents=True)
        centers, points = [], []
        for t in range(T):
            cx, cy = path_center(path, t / 32)
            rgb, mask = endpoint[t] if t in (0, 32) else compose(bg, place(spr, cx, cy))
            Image.fromarray(rgb).save(root / 'source' / f'{t:03d}.png')
            Image.fromarray(mask).save(root / 'mask' / f'{t:03d}.png')
            Image.fromarray(layout_from_mask(mask)).save(root / 'layout' / f'{t:03d}.png')
            centers.append([cx, cy])
            points.append([[cx + dx, cy + dy] for dx, dy in POINT_OFFSETS])
        np.savez(root / 'tracks.npz', tracks=np.array(points, np.float32), centers=np.array(centers, np.float64),
                 visible=np.ones((T, 9), bool), valid=np.ones((T, 9), bool), anchor_valid=np.ones((2, 9), bool))
        manifest['paths'][path] = {'centers': centers}
    return manifest


def check(out: Path, manifest: dict) -> dict:
    def load(path):
        return np.array(Image.open(path))
    a = {t: (out / 'A/source' / f'{t:03d}.png').read_bytes() for t in (0, 32)}
    b = {t: (out / 'B/source' / f'{t:03d}.png').read_bytes() for t in (0, 32)}
    receipt = {}
    receipt['endpoints_byte_equal'] = all(load(out / 'A/source' / f'{t:03d}.png').tobytes() == load(out / 'B/source' / f'{t:03d}.png').tobytes()
                                          and a[t] == b[t] for t in (0, 32))
    ca, cb = np.array(manifest['paths']['A']['centers']), np.array(manifest['paths']['B']['centers'])
    receipt['endpoint_centers'] = {'start': ca[0].tolist(), 'end': ca[32].tolist()}
    receipt['mid_separation_px'] = float(np.linalg.norm(ca[16] - cb[16]))
    receipt['max_center_gap_px'] = float(np.abs(ca - cb).max())
    inside, point_in_mask, bg_static = True, True, True
    bg = load(out / 'background.png')
    union = np.zeros((H, W), bool)
    for path in ('A', 'B'):
        tracks = np.load(out / path / 'tracks.npz')['tracks']
        for t in range(T):
            mask = load(out / path / 'mask' / f'{t:03d}.png') > 0
            union |= mask
            ys, xs = np.nonzero(mask)
            inside &= bool(xs.min() > 2 and xs.max() < W - 3 and ys.min() > 2 and ys.max() < H - 3)
            area = mask.sum()
            inside &= bool(abs(area - math.pi * (D / 2) ** 2) < 0.03 * math.pi * (D / 2) ** 2)
            for x, y in tracks[t]:
                point_in_mask &= bool(mask[int(round(y)), int(round(x))])
    far = cv2.dilate(union.astype(np.uint8), np.ones((5, 5), np.uint8)) == 0
    for path in ('A', 'B'):
        for t in range(T):
            rgb = load(out / path / 'source' / f'{t:03d}.png')
            bg_static &= bool((rgb[far] == bg[far]).all())
    receipt.update(object_inside_all_frames_constant_area=inside, points_inside_mask=point_in_mask,
                   background_static_outside_object=bg_static)
    assert receipt['endpoints_byte_equal'] and receipt['mid_separation_px'] > 95.9
    assert inside and point_in_mask and bg_static
    return receipt


def main() -> None:
    out = Path(sys.argv[1])
    assert out.is_absolute()
    out.mkdir(parents=True, exist_ok=False)
    manifest = render(out)
    manifest['checks'] = check(out, manifest)
    manifest['files'] = {str(p.relative_to(out)): sha(p.read_bytes()) for p in sorted(out.rglob('*')) if p.is_file()}
    (out / 'TASK_MANIFEST.json').write_text(json.dumps(manifest, indent=2))
    print(json.dumps({'status': 'TASK_RENDERED', **manifest['checks']}))


if __name__ == '__main__':
    main()
