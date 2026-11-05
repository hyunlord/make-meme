"""CPU fixtures for configuration-driven anchor gates."""
import json
from pathlib import Path

from anchor_gates import Policy, Row, classify, geometry

CONFIG = Path(__file__).parents[1]/'V003_SCENE_CONFIG.json'


def policy() -> Policy:
    return Policy.read(CONFIG)


def row(track: int, box: tuple[float, float, float, float]) -> Row:
    return Row(track, True, box, ((box[0]+box[2])/2, (box[1]+box[3])/2), 100)


def test_reflection_boundary_and_identity() -> None:
    rows = [row(0, (500, 100, 600, 300)), row(1, (200, 100, 300, 300)),
            row(2, (500, 261, 600, 460)), row(3, (200, 261, 300, 460))]
    assert classify(rows, policy()) == ([0, 1], [2, 3])
    result = geometry(rows, rows, policy())
    assert all(result['gates'].values())


def test_non_upright_shape_fails_even_if_height_passes() -> None:
    source = [row(0, (500, 100, 600, 300)), row(1, (200, 100, 300, 300))]
    anchor = [row(3, (450, 100, 650, 300)), row(2, (200, 100, 300, 300))]
    result = geometry(source, anchor, policy())
    assert result['gates']['G3']
    assert not result['gates']['G6']
    assert result['casting']['Lab'] == 3


def test_missing_body_fails_without_good_point_averaging() -> None:
    source = [row(0, (500, 100, 600, 300)), row(1, (200, 100, 300, 300))]
    result = geometry(source, source[:1], policy())
    assert not result['gates']['G1']
    assert not result['gates']['G6']


def test_gate_cli_background_and_readback(tmp_path: Path) -> None:
    import subprocess
    import sys
    import numpy as np
    from PIL import Image
    p = policy()
    rows = [row(0, (500, 100, 600, 300)), row(1, (200, 100, 300, 300))]
    for folder in ('source', 'anchor'):
        target = tmp_path/folder
        target.mkdir()
        objects = []
        for r in rows:
            assert r.bbox is not None
            x0, y0, x1, y1 = map(int, r.bbox)
            mask = np.zeros((p.size[1], p.size[0]), np.uint8)
            mask[y0:y1, x0:x1] = 255
            Image.fromarray(mask).save(target/f'000-track-{r.track:02d}.png')
            objects.append({'track_index': r.track, 'present': True, 'bbox': r.bbox,
                            'center': r.center, 'area': int((mask > 0).sum())})
        (target/'summary.json').write_text(json.dumps({'coordinate_size': p.size,
            'frames': [{'index': 0, 'objects': objects}]}))
    Image.new('RGB', p.size, (127, 127, 127)).save(tmp_path/'source.png')
    Image.new('RGB', p.size, (140, 140, 140)).save(tmp_path/'anchor.png')
    runtime = {f'{role}_{kind}': str(tmp_path/(f'{role}/summary.json' if kind == 'summary' else f'{role}.png'))
               for role in ('source', 'anchor') for kind in ('summary', 'image')}
    runtime['source_frame_index'] = 0
    (tmp_path/'runtime.json').write_text(json.dumps(runtime))
    subprocess.run([sys.executable, str(Path(__file__).with_name('anchor_gates.py')),
                    str(CONFIG), str(tmp_path/'runtime.json'), str(tmp_path/'gates.json')], check=True)
    result = json.loads((tmp_path/'gates.json').read_text())
    assert result['failed_gates'] == ['G5']
    assert result['background_mae'] == 13
    assert result['G7']['status'] == 'NOT_MEASURED'
