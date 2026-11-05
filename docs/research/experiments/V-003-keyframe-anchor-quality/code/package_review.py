# /// script
# requires-python = ">=3.11"
# dependencies = ["Pillow"]
# ///
# How to run on Spark: EXISTING_PYTHON package_review.py PRIVATE_PACKAGE.json
"""Copy declared media, render an offline viewer and verify a compact archive.

No discovery or inference. All scene values come from scene_config. Each stage
uses a new review_dir and zip_path, preserving previous delivery artifacts.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
from typing import TypedDict
import zipfile

from PIL import Image, ImageDraw


class FileEntry(TypedDict):
    bytes: int
    sha256: str


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def copy_verified(source: Path, target: Path) -> FileEntry:
    expected = digest(source)
    shutil.copy2(source, target)
    if digest(target) != expected:
        raise OSError(f'Copy verification failed: {target.name}')
    return {'bytes': target.stat().st_size, 'sha256': expected}


def human_review(labels: list[str], extra: str) -> str:
    lines = ['# 사용자 검토', '', '품질: HUMAN_REVIEW_PENDING', '',
             '직접 재생한 뒤 작성해 주세요. 자동 측정값으로 이 양식을 채우지 않습니다.', '']
    for label in labels:
        lines.extend([f'## {label}', '', '- 래브라도로 보이는가 (예 / 애매 / 아니오):',
                      '- IG로 보이는가 (예 / 애매 / 아니오):', '- 원본 춤 동작을 따라가는가 (1–5):',
                      '- 래브라도가 IG보다 크게 유지되는가 (예 / 애매 / 아니오):',
                      '- 깜빡임·떨림 (없음 / 약간 / 심함):', '- 배경·주변 손상 (없음 / 약간 / 심함):',
                      '- 밈에 쓸 수 있는가 (예 / 고치면 가능 / 아니오):', f'- {extra}:', '- 한 줄 메모:', ''])
    return '\n'.join(lines)


def main() -> None:
    cfg = json.loads(Path(sys.argv[1]).read_text())
    scene_path = Path(cfg['scene_config'])
    scene = json.loads(scene_path.read_text())
    folder, archive = Path(cfg['review_dir']), Path(cfg['zip_path'])
    if folder.exists() or archive.exists():
        raise FileExistsError('Use new stage paths; previous delivery is immutable')
    folder.mkdir(parents=True)
    archive.parent.mkdir(parents=True, exist_ok=True)
    provenance: dict[str, FileEntry] = {}
    clips = []
    for index, label in enumerate(scene['viewer_columns']):
        declared = cfg['clips'].get(label, {'status': 'NOT_RUN', 'reason': 'Not produced at this stage'})
        clip = {'label': label, 'status': declared['status'], 'reason': declared.get('reason', ''),
                'generated': declared.get('generated', False), 'metrics': declared.get('metrics')}
        for role in ('raw', 'post'):
            if declared.get(role):
                filename = f'clip-{index:02d}-{role}.mp4'
                provenance[filename] = copy_verified(Path(declared[role]), folder/filename)
                clip[role] = filename
        if clip.get('post') and not clip.get('raw'):
            raise ValueError('POST must not replace a missing RAW')
        clips.append(clip)
    anchors = []
    for frame in scene['keyframes']['segment_frames']:
        declared = cfg.get('anchors', {}).get(str(frame), {'status': 'NOT_GENERATED', 'accepted': False})
        anchor = {'frame': frame, 'status': declared['status'], 'accepted': declared['accepted']}
        if declared.get('image'):
            filename = f'anchor-{frame:04d}.png'
            provenance[filename] = copy_verified(Path(declared['image']), folder/filename)
            anchor['src'] = filename
        anchors.append(anchor)
    # A static one-row sheet complements the actual media and interactive row.
    tile_w = 320
    master_w, master_h = scene['anchor_generation']['resolution_master']
    tile_h = round(tile_w*master_h/master_w)
    sheet = Image.new('RGB', (tile_w*len(anchors), tile_h+48), 'white')
    draw = ImageDraw.Draw(sheet)
    for index, anchor in enumerate(anchors):
        if anchor.get('src'):
            with Image.open(folder/anchor['src']) as image:
                sheet.paste(image.convert('RGB').resize((tile_w, tile_h)), (index*tile_w, 0))
        draw.text((index*tile_w+8, tile_h+8), f"frame {anchor['frame']} / {anchor['status']}", fill='black')
    sheet.save(folder/'anchor-sheet.jpg', quality=95)
    documents = {'앵커 시트': 'anchor-sheet.jpg', '사용자 검토 양식': 'HUMAN_REVIEW.md'}
    for filename, source in cfg.get('documents', {}).items():
        if Path(filename).name != filename:
            raise ValueError('Documents must use flat relative names')
        copy_verified(Path(source), folder/filename)
        documents[filename] = filename
    labels = [clip['label'] for clip in clips if clip['generated']]
    (folder/'HUMAN_REVIEW.md').write_text(human_review(labels, scene['human_review_extra_item']))
    data = {'title': scene['experiment'], 'stage': cfg['stage'],
            'frames': scene['generation']['frames'], 'fps': scene['generation']['fps'],
            'clips': clips, 'anchors': anchors, 'documents': documents,
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
    payload = sorted(path for path in folder.iterdir() if path.is_file())
    manifest = {'payload_count': len(payload), 'excludes': ['MANIFEST.json', 'ZIP itself'],
                'scene_config_sha256': digest(scene_path),
                'files': {path.name: {'bytes': path.stat().st_size, 'sha256': digest(path)} for path in payload}}
    (folder/'MANIFEST.json').write_text(json.dumps(manifest, indent=2)+'\n')
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as output:
        for path in [*payload, folder/'MANIFEST.json']:
            output.write(path, path.name)
    extracted = folder.with_name(folder.name+'-verified-extraction')
    if extracted.exists():
        raise FileExistsError(extracted)
    with zipfile.ZipFile(archive) as saved:
        if saved.testzip() is not None:
            raise OSError('Archive CRC failed')
        saved.extractall(extracted)
        zip_count = len(saved.namelist())
    for name, entry in manifest['files'].items():
        if digest(extracted/name) != entry['sha256']:
            raise OSError(f'Extracted payload mismatch: {name}')
    receipt = {'filename': archive.name, 'bytes': archive.stat().st_size, 'sha256': digest(archive),
               'payload_count': len(payload), 'zip_entry_count': zip_count,
               'crc': 'PASS', 'actual_extraction': 'PASS', 'payload_hashes': 'PASS',
               'browser_qa': 'NOT_RUN', 'quality': 'HUMAN_REVIEW_PENDING'}
    archive.with_suffix('.receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
