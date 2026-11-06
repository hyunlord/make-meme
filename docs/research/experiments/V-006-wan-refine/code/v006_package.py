"""Build an offline, uncompressed review folder from explicitly declared files.

Run on Spark with its existing Python. Scene values come from scene_config and
inherited_config; paths/actual statuses come from a private package declaration.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
from typing import TypedDict


class FileEntry(TypedDict):
    bytes: int
    sha256: str


class Source(TypedDict):
    path: str
    label: str
    start_frame: int
    frames: int


class Clip(TypedDict):
    status: str
    reason: str
    generated: bool
    default_role: str
    sources: dict[str, Source]


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1048576), b''):
            result.update(chunk)
    return result.hexdigest()


def copy_verified(source: Path, target: Path) -> FileEntry:
    expected = digest(source)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    if digest(target) != expected:
        raise OSError(f'Copy verification failed: {target.name}')
    return {'bytes': target.stat().st_size, 'sha256': expected}


def main() -> None:
    cfg = json.loads(Path(sys.argv[1]).read_text())
    scene_path = Path(cfg['scene_config'])
    scene = json.loads(scene_path.read_text())
    inherited = json.loads(Path(cfg['inherited_config']).read_text())
    folder = Path(cfg['review_dir'])
    folder.mkdir(parents=True, exist_ok=False)
    provenance: dict[str, FileEntry] = {}
    clips = []
    for index, label in enumerate(scene['viewer']['columns']):
        declared = cfg['clips'][label]
        clip = {key: declared.get(key) for key in ('status', 'reason', 'generated', 'default_role', 'metrics', 'leg_metrics')}
        clip['label'] = label
        sources = {}
        for role, source in declared.get('sources', {}).items():
            name = f'clip-{index:02d}-{role}.mp4'
            provenance[name] = copy_verified(Path(source['path']), folder/name)
            sources[role] = {'src': name, 'label': source['label'], 'start_frame': source['start_frame'], 'frames': source['frames']}
        clip['sources'] = sources
        if sources and declared.get('default_role') not in sources:
            raise ValueError(f'Missing default role for {label}')
        clips.append(clip)
    documents = {}
    for filename, source in cfg['documents'].items():
        relative = Path(filename)
        if relative.is_absolute() or '..' in relative.parts:
            raise ValueError('Documents must stay inside the review folder')
        provenance[filename] = copy_verified(Path(source), folder/relative)
        documents[filename] = filename
    if 'HUMAN_REVIEW.md' not in documents:
        raise ValueError('Declare the blank public HUMAN_REVIEW.md in documents')
    viewer, measurement = inherited['viewer'], inherited['measurement_policy']
    data = {'title': scene['experiment'], 'stage': cfg['stage'],
            'frames': scene['scene']['segment']['frames'], 'fps': scene['common']['fps'],
            'kick_loop_frames': measurement['window_inclusive'],
            'top_line': scene['viewer']['top_line'],
            'raw_zoom_factor': viewer['raw_zoom_factor'],
            'lower_fraction': measurement['lower_fraction'],
            'playback_rates': viewer['playback_rates'], 'clips': clips,
            'documents': documents, 'leg_references': cfg.get('leg_references', []),
            'quality': 'HUMAN_REVIEW_PENDING', 'temporal': 'UNVERIFIED'}
    (folder/'review-data.json').write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n')
    template = Path(cfg['template']).read_text()
    embedded = json.dumps(data, ensure_ascii=False).replace('<', '\\u003c')
    html, count = re.subn(r'(<script id="review-data" type="application/json">).*?(</script>)',
                         lambda match: match[1]+embedded+match[2], template, flags=re.S)
    if count != 1:
        raise ValueError('Expected one viewer data slot')
    (folder/'index.html').write_text(html)
    (folder/'MEDIA_PROVENANCE.json').write_text(json.dumps(provenance, indent=2)+'\n')
    payload = sorted(path for path in folder.rglob('*') if path.is_file())
    manifest = {'payload_count': len(payload), 'excludes': ['MANIFEST.json'],
                'scene_config_sha256': digest(scene_path),
                'inherited_config_sha256': digest(Path(cfg['inherited_config'])),
                'files': {path.relative_to(folder).as_posix(): {'bytes': path.stat().st_size, 'sha256': digest(path)} for path in payload}}
    (folder/'MANIFEST.json').write_text(json.dumps(manifest, indent=2)+'\n')
    for filename, entry in manifest['files'].items():
        if digest(folder/filename) != entry['sha256']:
            raise OSError(f'Payload readback mismatch: {filename}')
    receipt = {'primary_delivery': 'UNCOMPRESSED_FOLDER', 'folder': folder.name,
               'bytes': sum(entry['bytes'] for entry in manifest['files'].values()),
               'payload_count': len(payload), 'manifest_sha256': digest(folder/'MANIFEST.json'),
               'payload_readback': 'PASS', 'browser_qa': 'NOT_RUN',
               'quality': 'HUMAN_REVIEW_PENDING', 'temporal': 'UNVERIFIED'}
    folder.with_suffix('.receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
