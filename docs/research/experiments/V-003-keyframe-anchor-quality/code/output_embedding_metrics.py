"""CPU builder/merger for existing-local embedding worker; never loads a model.

build PRIVATE_MANIFEST.json PRIVATE_RUNTIME.json
merge PRIVATE_MANIFEST.json EMBEDDINGS.json PUBLIC_METRICS.json
Manifest: scene_config, model_path, device, cpu_threads, batch_size,
embedding_output, reference_id, anchors [{id,frame,image,summary,casting_report,
frame_index}], outputs [{id,raw_frames,summary,metrics}]. Anchor frame is the
output comparison time; frame_index is the saved SAM index (normally zero).
All anchors are embedded once. All output frames use fixed saved metrics casting.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

from embed_images import atomic_report


def build(manifest: dict) -> dict:
    scene = json.loads(Path(manifest['scene_config']).read_text())
    frames = scene['generation']['frames']
    anchors = manifest['anchors']
    comparisons = {row['frame']: row['id'] for row in anchors}
    if len(comparisons) != len(anchors):
        raise ValueError('Duplicate keyframe comparison time')
    items = [{key: row[key] for key in ('id', 'image', 'summary', 'casting_report', 'frame_index')} for row in anchors]
    for output in manifest['outputs']:
        for index in range(frames):
            items.append({'id': f"{output['id']}:frame:{index}",
                          'image': str(Path(output['raw_frames'])/f'{index:03d}.png'),
                          'summary': output['summary'], 'casting_report': output['metrics'],
                          'frame_index': index, 'allow_missing': True,
                          'comparison_id': comparisons.get(index)})
    return {**{key: manifest[key] for key in ('scene_config', 'model_path', 'device', 'cpu_threads', 'batch_size', 'reference_id')},
            'output': manifest['embedding_output'], 'items': items}


def merge(manifest: dict, embeddings: dict) -> dict:
    scene = json.loads(Path(manifest['scene_config']).read_text())
    roles = scene['scene']['casting_track_indices']
    count = scene['generation']['frames']
    rows = {item['id']: item for item in embeddings['items']}
    outputs = {}
    for output in manifest['outputs']:
        frames = []
        for index in range(count):
            row = rows[f"{output['id']}:frame:{index}"]
            frames.append({'frame': index, 'cosine_vs_anchor0': row['cosine_vs_reference'],
                           'keyframe_reference': row['comparison_id'],
                           'cosine_vs_keyframe': row['cosine_vs_comparison']})
        aggregate = {}
        for role in roles:
            observed = [row['cosine_vs_anchor0'][role] for row in frames if row['cosine_vs_anchor0'][role] is not None]
            aggregate[role] = {'minimum': min(observed) if observed else None,
                               'mean': sum(observed)/len(observed) if observed else None,
                               'observed_frames': len(observed), 'total_frames': count}
        outputs[output['id']] = {'frames': frames, 'anchor0_similarity': aggregate,
                                 'keyframes': [row for row in frames if row['keyframe_reference'] is not None]}
    return {'quality': 'HUMAN_REVIEW_PENDING', 'gate': False,
            'definition': 'Unmasked SAM bbox RGB; saved fixed casting; missing/unestablished roles null; observed-only cosine averages with coverage',
            'reference_id': embeddings['reference_id'], 'feature': embeddings['feature'],
            'model_config_sha256': embeddings['model_config_sha256'], 'outputs': outputs}


if __name__ == '__main__':
    manifest = json.loads(Path(sys.argv[2]).read_text())
    if sys.argv[1] == 'build':
        destination, result = Path(sys.argv[3]), build(manifest)
    elif sys.argv[1] == 'merge':
        destination = Path(sys.argv[4])
        result = merge(manifest, json.loads(Path(sys.argv[3]).read_text()))
    else:
        raise ValueError('Expected build or merge')
    if destination.exists():
        raise FileExistsError(destination)
    atomic_report(destination, json.dumps(result, indent=2, allow_nan=False)+'\n')
