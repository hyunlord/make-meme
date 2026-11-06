# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""CPU embedding adapter: python v006_metrics_embedding.py prepare|merge CONFIG.

Prepare config: template, metrics, refined_frames, output_summary, name,
local_casting_report, runtime_output, embedding_output. Merge adds merged_output.
The unchanged inherited embedding worker consumes runtime_output under guards.
"""
from __future__ import annotations

from enum import Enum
import hashlib
import json
from pathlib import Path
import sys
from typing import assert_never


class Action(Enum):
    PREPARE = 'prepare'
    MERGE = 'merge'


def main() -> None:
    action = Action(sys.argv[1])
    config = json.loads(Path(sys.argv[2]).read_text())
    metrics = json.loads(Path(config['metrics']).read_text())
    match action:
        case Action.PREPARE:
            template = json.loads(Path(config['template']).read_text())
            reference = next(item for item in template['items'] if item['id'] == template['reference_id'])
            casting = {**metrics, 'frames': [{**row, 'frame': row['local_frame'],
                                              'global_frame': row['frame']} for row in metrics['frames']]}
            local_casting = Path(config['local_casting_report'])
            if local_casting.exists() or Path(config['runtime_output']).exists():
                raise FileExistsError('Preserve previous embedding preparation')
            local_casting.write_text(json.dumps(casting, indent=2, allow_nan=False) + '\n')
            items = [reference]
            for row in metrics['frames']:
                index = row['local_frame']
                items.append({'id': f"{config['name']}:frame:{row['frame']}",
                              'image': str(Path(config['refined_frames']) / f'{index:03d}.png'),
                              'summary': config['output_summary'], 'casting_report': str(local_casting),
                              'frame_index': index, 'allow_missing': True, 'comparison_id': None})
            runtime = {key: value for key, value in template.items() if key not in ('items', 'output')}
            runtime.update(items=items, output=config['embedding_output'])
            with Path(config['runtime_output']).open('x') as stream:
                json.dump(runtime, stream, indent=2, allow_nan=False)
                stream.write('\n')
        case Action.MERGE:
            embedded = json.loads(Path(config['embedding_output']).read_text())
            by_id = {item['id']: item for item in embedded['items']}
            frames = [{'frame': row['frame'], 'local_frame': row['local_frame'],
                       'cosine_vs_anchor0': by_id[f"{config['name']}:frame:{row['frame']}"]['cosine_vs_reference']}
                      for row in metrics['frames']]
            roles = list(frames[0]['cosine_vs_anchor0'])
            aggregate = {}
            for role in roles:
                values = [row['cosine_vs_anchor0'][role] for row in frames if row['cosine_vs_anchor0'][role] is not None]
                aggregate[role] = {'mean': sum(values) / len(values) if values else None,
                                   'minimum': min(values) if values else None,
                                   'observed_frames': len(values), 'total_frames': len(frames)}
            report = {'quality': 'HUMAN_REVIEW_PENDING', 'gate': False, 'frames': frames,
                      'reference_id': embedded['reference_id'], 'anchor0_similarity': aggregate,
                      'model_config_sha256': embedded['model_config_sha256'], 'feature': embedded['feature'],
                      'embedding_report_sha256': hashlib.sha256(Path(config['embedding_output']).read_bytes()).hexdigest()}
            with Path(config['merged_output']).open('x') as stream:
                json.dump(report, stream, indent=2, allow_nan=False)
                stream.write('\n')
        case unreachable:
            assert_never(unreachable)


if __name__ == '__main__':
    main()
