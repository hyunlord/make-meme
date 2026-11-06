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
                      '- 밈에 쓸 수 있는가 (예 / 고치면 가능 / 아니오):', '- Kling 대비 (훨씬 못함 / 못함 / 비슷함 / 나음):', '- 발차기 구간이 원본과 같은 동작인가 (다름 / 비슷함 / 같음):', f'- {extra}:', '- 한 줄 메모:', ''])
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
    for index, label in enumerate(scene['viewer']['columns']):
        declared = cfg['clips'].get(label, {'status': 'NOT_RUN', 'reason': 'Not produced at this stage'})
        clip = {'label': label, 'status': declared['status'], 'reason': declared.get('reason', ''),
                'generated': declared.get('generated', False), 'metrics': declared.get('metrics'),
                'leg_metrics': declared.get('leg_metrics'), 'derivative': declared.get('derivative', False)}
        for role in ('raw', 'post'):
            if declared.get(role):
                filename = f'clip-{index:02d}-{role}.mp4'
                provenance[filename] = copy_verified(Path(declared[role]), folder/filename)
                clip[role] = filename
        if clip.get('post') and not clip.get('raw'):
            raise ValueError('POST must not replace a missing RAW')
        clips.append(clip)
    anchors = []
    for frame in sorted(set(scene['anchors']['reused_accepted'] + scene['anchors']['new_for_R3'])):
        declared = cfg.get('anchors', {}).get(str(frame), {'status': 'NOT_GENERATED', 'accepted': False})
        anchor = {'frame': frame, 'status': declared['status'], 'accepted': declared['accepted']}
        if declared.get('image'):
            filename = f'anchor-{frame:04d}.png'
            provenance[filename] = copy_verified(Path(declared['image']), folder/filename)
            anchor['src'] = filename
        anchors.append(anchor)
    # A static one-row sheet complements the actual media and interactive row.
    tile_w = 320
    master_w, master_h = scene['measurement_policy']['master_size']
    tile_h = round(tile_w*master_h/master_w)
    sheet_start, sheet_end = scene['viewer']['anchor_sheet_range']
    sheet_frames = range(sheet_start, sheet_end+1, scene['viewer']['anchor_sheet_step'])
    sheet_anchors = [a for a in anchors if a['frame'] in sheet_frames]
    sheet = Image.new('RGB', (tile_w*len(sheet_anchors), tile_h+48), 'white')
    draw = ImageDraw.Draw(sheet)
    for index, anchor in enumerate(sheet_anchors):
        if anchor.get('src'):
            with Image.open(folder/anchor['src']) as image:
                sheet.paste(image.convert('RGB').resize((tile_w, tile_h)), (index*tile_w, 0))
        draw.text((index*tile_w+8, tile_h+8), f"frame {anchor['frame']} / {anchor['status']}", fill='black')
    sheet.save(folder/'anchor-sheet.jpg', quality=95)
    documents = {'앵커 시트': 'anchor-sheet.jpg', '사용자 검토 양식': 'HUMAN_REVIEW.md'}
    scaled_sheet = None
    if cfg.get('scaled_control_sheet'):
        source = Path(cfg['scaled_control_sheet'])
        scaled_sheet = 'scaled-control-sheet' + source.suffix
        copy_verified(source, folder/scaled_sheet)
        documents['원본 canny / 확대 canny / 앵커 비교 시트'] = scaled_sheet
    for filename, source in cfg.get('documents', {}).items():
        relative = Path(filename)
        if relative.is_absolute() or '..' in relative.parts:
            raise ValueError('Documents must stay inside the review folder')
        (folder/relative).parent.mkdir(parents=True, exist_ok=True)
        copy_verified(Path(source), folder/relative)
        documents[filename] = filename
    labels = [clip['label'] for clip in clips if clip['generated']]
    (folder/'HUMAN_REVIEW.md').write_text(human_review(labels, scene['viewer']['human_review_extra_item']))
    data = {'title': scene['experiment'], 'stage': cfg['stage'],
            'frames': scene['scene']['segment']['frames'], 'fps': scene['scene']['segment']['fps'],
            'kick_loop_frames': scene['measurement_policy']['window_inclusive'],
            'top_line': scene['viewer']['top_line'],
            'raw_zoom_factor': scene['viewer']['raw_zoom_factor'],
            'lower_fraction': scene['measurement_policy']['lower_fraction'],
            'playback_rates': scene['viewer']['playback_rates'],
            'clips': clips, 'anchors': anchors, 'documents': documents,
            'leg_references': cfg.get('leg_references', []),
            'scaled_control_sheet': scaled_sheet,
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
    manifest = {'payload_count': len(payload), 'excludes': ['MANIFEST.json', 'ZIP itself'],
                'scene_config_sha256': digest(scene_path),
                'files': {path.relative_to(folder).as_posix(): {'bytes': path.stat().st_size, 'sha256': digest(path)} for path in payload}}
    (folder/'MANIFEST.json').write_text(json.dumps(manifest, indent=2)+'\n')
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as output:
        for path in [*payload, folder/'MANIFEST.json']:
            output.write(path, path.relative_to(folder).as_posix())
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
    receipt = {'primary_delivery': 'UNCOMPRESSED_FOLDER', 'folder': folder.name,
               'zip_role': 'SECONDARY_SAME_PAYLOAD', 'filename': archive.name, 'bytes': archive.stat().st_size, 'sha256': digest(archive),
               'payload_count': len(payload), 'zip_entry_count': zip_count,
               'crc': 'PASS', 'actual_extraction': 'PASS', 'payload_hashes': 'PASS',
               'browser_qa': 'NOT_RUN', 'quality': 'HUMAN_REVIEW_PENDING'}
    archive.with_suffix('.receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
