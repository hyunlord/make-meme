# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Publish a private child SAMPLE: python v006_sample.py PRIVATE_MANIFEST OUTPUT.

Manifest: inherited_builder_code, parent_sample_path, sample. All asset_path
records use the inherited V005 hashing implementation. No media is copied.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys


def main() -> None:
    manifest_path, target = map(Path, sys.argv[1:])
    if target.exists():
        raise FileExistsError(target)
    manifest = json.loads(manifest_path.read_text())
    sys.path.insert(0, manifest['inherited_builder_code'])
    from build_sample import digest, hydrate

    parent_path = Path(manifest['parent_sample_path'])
    parent = json.loads(parent_path.read_text())
    record = hydrate(manifest['sample'])
    record.update(schema_version='1.1', record_origin='CURRENT_RUN', media_copied=False,
                  recorded_at_utc=datetime.now(timezone.utc).isoformat(),
                  parent_sample={'sample_id': parent['sample_id'], 'path': str(parent_path.resolve()),
                                 'sha256': digest(parent_path), 'kind': 'file', 'bytes': parent_path.stat().st_size,
                                 'relationship': 'REFINEMENT_INPUT',
                                 'source_run_id': parent['run_id']},
                  human_review={'status': 'PENDING', 'form_values': None, 'source_form': None})
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix('.tmp')
    with temporary.open('x') as stream:
        json.dump(record, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    if json.loads(temporary.read_text()) != record:
        raise RuntimeError('Child SAMPLE readback mismatch')
    os.link(temporary, target)
    temporary.unlink()
    print(json.dumps({'status': 'RECORDED', 'parent_sample_id': parent['sample_id'],
                      'parent_sha256': digest(parent_path), 'human_review': 'PENDING'}))


if __name__ == '__main__':
    main()
