"""CPU-only SAM geometry contract; no model or torch imports."""
import json
from pathlib import Path
import subprocess
import sys

from PIL import Image
import pytest

SCENE = Path(__file__).parents[1]/'V003_SCENE_CONFIG.json'


@pytest.mark.parametrize('mode', ['image', 'video'])
def test_mode_selects_configured_geometry_without_torch(tmp_path: Path, mode: str) -> None:
    scene = json.loads(SCENE.read_text())
    size = (scene['anchor_generation']['resolution_master'] if mode == 'image'
            else scene['generation']['resolution'])
    frames = tmp_path/'frames'
    frames.mkdir()
    Image.new('RGB', size).save(frames/'000.png')
    checkpoint = tmp_path/'unused-checkpoint'
    checkpoint.touch()
    runtime = {'scene_config': str(SCENE), 'frames': str(frames), 'output': str(tmp_path/'output'),
               'checkpoint': str(checkpoint), 'comfy_root': str(tmp_path), 'revision': 'cpu-fixture', 'mode': mode}
    config = tmp_path/'runtime.json'
    config.write_text(json.dumps(runtime))
    result = subprocess.run([sys.executable, str(Path(__file__).with_name('anchor_sam.py')),
                             str(config), '--cpu-only'], capture_output=True, text=True, check=True)
    report = json.loads(result.stdout)
    assert report['coordinate_size'] == size
    assert report['torch_imported'] is False
    assert report['status'] == 'CPU_ENTRY_PASS'
