# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# CPU only, existing research Python: input_contrast.py /abs/config.json
"""Stage A: ON vs make_null() input differences, track overlays, and the pre-GPU finite-difference track choice."""
from pathlib import Path
import json
import sys

import numpy as np
import torch
from PIL import Image, ImageDraw
from pydantic import BaseModel, ConfigDict

sys.path.insert(0, str(Path(__file__).resolve().parent))
from signal_common import CASES, WH, gate_of, tensor_sha, write_json


class Config(BaseModel):
    model_config = ConfigDict(frozen=True, extra='forbid')
    c006_code: Path
    c006_data: Path
    white_cache: Path
    point_exclusions: Path
    output: Path


def stats(values: torch.Tensor) -> dict | None:
    if values.numel() == 0:
        return None
    v = values.double()
    return {'n': int(v.numel()), 'mean': float(v.mean()), 'median': float(v.median()),
            'p90': float(torch.quantile(v, .9)), 'max': float(v.max())}


def main() -> None:
    config = Config.model_validate_json(Path(sys.argv[1]).read_text())
    sys.path.insert(0, str(config.c006_code))
    from training_state import load_cache
    from point_features import make_null, PointCondition
    config.output.mkdir(parents=True, exist_ok=False)
    manifest = json.loads((config.white_cache / 'CACHE_MANIFEST.json').read_text())
    assert manifest['mask_contract'].startswith('white_v1')
    scale = torch.tensor(WH, dtype=torch.float64)
    report = {}
    for name, split in CASES:
        path = config.white_cache / f'{name}.pt'
        raw = torch.load(path, map_location='cpu', weights_only=True)
        item = load_cache(path, config.point_exclusions)  # clones; raw cache untouched
        assert all(torch.equal(raw[k], torch.load(path, map_location='cpu', weights_only=True)[k]) for k in ('valid', 'patches'))
        # Same keys as training_state.condition_from_cache, kept on CPU.
        on = PointCondition(**{key: item[key] for key in ('patches', 'anchor_valid', 'positions', 'visible', 'valid', 'box_wh')})
        null = make_null(on)
        g_on, g_null = gate_of(on), gate_of(null)
        q_on, q_null = on.positions.double(), null.positions.double()
        k = q_on.shape[1]
        common = g_on & g_null
        mid = torch.zeros(33, dtype=torch.bool); mid[1:32] = True
        cm = common & mid[:, None]
        diff_px = ((q_on - q_null) * scale).norm(dim=-1)
        box = null.box_wh.double()  # endpoint-interpolated, identical for ON/NULL kernels
        diff_box = ((q_on - q_null) / box[:, None, :]).norm(dim=-1)
        vel_on = (q_on[1:] - q_on[:-1]) * scale
        vel_null = (q_null[1:] - q_null[:-1]) * scale
        both = common[1:] & common[:-1]
        vel_diff = (vel_on - vel_null).norm(dim=-1)[both]
        only_on = (g_on & ~g_null)
        only_null = (g_null & ~g_on)
        per_track_rms = []
        for j in range(k):
            sel = cm[:, j]
            per_track_rms.append(float(diff_px[sel, j].square().mean().sqrt()) if sel.any() else None)
        # Pre-GPU FD track choice (work order section 9), inputs only.
        candidates = []
        for j in range(k):
            if not bool(on.anchor_valid[:, j].all()):
                continue
            if int(cm[:, j].sum()) < 12:
                continue
            gated = g_on[:, j]
            t = torch.arange(33, dtype=torch.float64)
            bump = (8 / 416) * torch.sin(np.pi * t / 32) ** 2
            x = q_on[:, j, 0]
            in_range = bool(((x + bump)[gated] <= 1).all() and ((x - bump)[gated] >= 0).all())
            if not in_range:
                continue
            candidates.append((-(per_track_rms[j] or 0.0), j))
        fd_track = min(candidates)[1] if candidates else None
        report[name] = {
            'split': split, 'K': k, 'cache_sha256': manifest['files'][name]['sha256'],
            'gated_points_on': int(g_on.sum()), 'gated_points_null': int(g_null.sum()),
            'common_gated_mid': int(cm.sum()),
            'position_diff_px_common_mid': stats(diff_px[cm]),
            'position_diff_normalized_common_mid': stats((diff_px / 416.0)[cm]),
            'position_diff_bbox_units_common_mid': stats(diff_box[cm]),
            'velocity_diff_px_per_frame_common': stats(vel_diff),
            'deviation_from_endpoint_linear_px': stats(diff_px[cm]),
            'only_on_gated': {'count': int(only_on.sum()), 'frames': only_on.any(1).nonzero().flatten().tolist()},
            'only_null_gated': {'count': int(only_null.sum()), 'frames': only_null.any(1).nonzero().flatten().tolist()},
            'per_track_rms_px': per_track_rms,
            'excluded_or_anchor_invalid_tracks': [j for j in range(k) if not bool(on.anchor_valid[:, j].all())],
            'patches_equal': bool(torch.equal(on.patches, null.patches)),
            'anchor_valid_equal': bool(torch.equal(on.anchor_valid, null.anchor_valid)),
            'kernel_box_equal': bool(torch.allclose(on.box_wh[[0, 32]].float(), null.box_wh[[0, 32]].float())),
            'motion_bit': {'on': on.motion_available, 'null': null.motion_available},
            'visibility_bit_differs': int((on.visible.bool() != null.visible.bool()).sum()),
            'validity_bit_differs': int((on.valid.bool() != null.valid.bool()).sum()),
            'fd_track': fd_track, 'fd_candidates': [j for _, j in sorted(candidates)],
            'positions_sha256': tensor_sha(on.positions)}
        # Overlay on existing source frames (derived review image, not generation).
        tiles = []
        for t in (0, 8, 16, 24, 32):
            with Image.open(config.c006_data / name / 'source' / f'{t:03d}.png') as im:
                im = im.convert('RGB').copy()
            d = ImageDraw.Draw(im)
            for j in range(k):
                if g_null[t, j]:
                    x, y = (q_null[t, j] * scale).tolist(); d.ellipse((x - 3, y - 3, x + 3, y + 3), outline=(80, 160, 255), width=2)
                if g_on[t, j]:
                    x, y = (q_on[t, j] * scale).tolist(); d.ellipse((x - 3, y - 3, x + 3, y + 3), fill=(255, 220, 0))
                    if j == fd_track:
                        d.rectangle((x - 6, y - 6, x + 6, y + 6), outline=(255, 0, 255), width=2)
            d.text((4, 4), f'{name} t={t}', fill=(255, 255, 255))
            tiles.append(im)
        sheet = Image.new('RGB', (416 * 5, 240))
        for i, im in enumerate(tiles):
            sheet.paste(im, (416 * i, 0))
        sheet.save(config.output / f'tracks-{name}.jpg', quality=90)
    write_json(config.output / 'INPUT_CONTRAST.json', report)
    for name, r in report.items():
        print(name, r['K'], 'common_mid', r['common_gated_mid'], 'diff_px', r['position_diff_px_common_mid'],
              'only_on', r['only_on_gated']['count'], 'only_null', r['only_null_gated']['count'], 'fd_track', r['fd_track'])


if __name__ == '__main__':
    main()
