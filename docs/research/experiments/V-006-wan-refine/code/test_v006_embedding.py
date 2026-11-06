# /// script
# requires-python = ">=3.11"
# dependencies = ["pytest"]
# ///
"""Index-adapter fixture, no model call: python -m pytest test_v006_embedding.py."""
import json
from pathlib import Path
import subprocess
import sys


def test_embedding_preparation_localizes_casting_but_preserves_global_ids(tmp_path: Path) -> None:
    # Given measured global frames and an inherited reference worker template.
    metrics = tmp_path / 'metrics.json'
    metrics.write_text(json.dumps({'casting': {'Lab': 7, 'IG': 9}, 'frames': [
        {'frame': 8 + i, 'local_frame': i, 'actual_tracks': [7, 9]} for i in range(3)]}))
    template = tmp_path / 'template.json'
    template.write_text(json.dumps({'reference_id': 'anchor0', 'output': 'unused',
        'items': [{'id': 'anchor0', 'image': 'anchor.png', 'frame_index': 0}]}))
    config = {'template': str(template), 'metrics': str(metrics), 'name': 'fixture',
              'refined_frames': str(tmp_path / 'frames'), 'output_summary': 'summary.json',
              'local_casting_report': str(tmp_path / 'local.json'),
              'runtime_output': str(tmp_path / 'runtime.json'), 'embedding_output': 'future.json'}
    path = tmp_path / 'config.json'
    path.write_text(json.dumps(config))
    # When the CPU adapter writes a runtime for the unchanged embedding worker.
    subprocess.run([sys.executable, str(Path(__file__).with_name('v006_metrics_embedding.py')),
                    'prepare', str(path)], check=True, capture_output=True)
    # Then masks use local indices while stable IDs preserve source time.
    local = json.loads((tmp_path / 'local.json').read_text())
    runtime = json.loads((tmp_path / 'runtime.json').read_text())
    assert [row['frame'] for row in local['frames']] == [0, 1, 2]
    assert [row['global_frame'] for row in local['frames']] == [8, 9, 10]
    assert [row['id'] for row in runtime['items'][1:]] == ['fixture:frame:8', 'fixture:frame:9', 'fixture:frame:10']
    assert [row['frame_index'] for row in runtime['items'][1:]] == [0, 1, 2]
