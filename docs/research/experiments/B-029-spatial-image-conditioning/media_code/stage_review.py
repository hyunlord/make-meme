"""Stage only named research payload classes; no weights or condition-cache discovery."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

EXPERIMENTS = {'B027': 'B-027-public-reference-robustness',
               'B028': 'B-028-object-reference-normalization',
               'B029': 'B-029-spatial-image-conditioning'}
REVIEW_NAMES = {'all17.png', 'local0-8-16.png', 'references.png',
                'comparison-preview24.mp4', 'manifest.json', 'review-sheets.html'}
ARTIFACT_NAMES = {'output.mp4', 'final_latent.json'}
RAW_NAMES = {'raw_output.pt', 'final_latent.safetensors'}


def digest(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def stage(base: Path, destination: Path, full: bool) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    videos = []

    def add(source: Path, relative: Path) -> None:
        if not source.is_file():
            raise FileNotFoundError(source)
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            if digest(source) != digest(target):
                raise ValueError(f'Staged file changed: {relative}')
        else:
            try:
                os.link(source, target)
            except OSError:
                shutil.copyfile(source, target)
        if source.name == 'output.mp4':
            videos.append({'path': str(relative), 'bytes': source.stat().st_size,
                           'sha256': digest(source), 'operation': 'byte-exact original MP4, no reencoding'})

    for label, folder in EXPERIMENTS.items():
        root = base / folder
        if not root.exists():
            continue
        for source in sorted((root / 'tasks').rglob('*')):
            relative = source.relative_to(root)
            parts = relative.parts
            if not source.is_file() or source.is_symlink():
                continue
            if not full and 'original-source' in parts:
                continue
            if 'inputs' in parts and source.suffix == '.png' and (label == 'B027' or (label == 'B028' and any(ref in parts for ref in ('R1', 'R2')))):
                add(source, Path(label) / relative)
            elif 'artifacts' in parts and source.name in ARTIFACT_NAMES:
                add(source, Path(label) / relative)
            elif label != 'B027' and source.suffix in ('.json', '.jsonl'):
                add(source, Path(label) / relative)
            elif full and label != 'B027' and 'artifacts' in parts and source.name in RAW_NAMES:
                add(source, Path(label) / relative)
        if label != 'B027':
            for source in sorted(root.glob('*')):
                if source.is_file() and not source.is_symlink() and (source.name == 'CURRENT_STATE.md' or source.name.startswith('PREREGISTERED_')):
                    add(source, Path(label) / source.name)
            for code_folder in ('code', 'configs'):
                for source in sorted((root / code_folder).rglob('*')):
                    if source.is_file() and not source.is_symlink() and source.suffix in ('.py', '.sh', '.json', '.md'):
                        add(source, Path(label) / source.relative_to(root))
            for source in sorted((root / 'reports').rglob('*')):
                if source.is_file() and source.suffix in ('.json', '.jsonl', '.md', '.csv'):
                    add(source, Path(label) / source.relative_to(root))
            for source in sorted((root / 'review').rglob('*')):
                if not full and label == 'B029' and source.parent.name.endswith('-METHOD') and (source.parent.with_name(source.parent.name.removesuffix('-METHOD') + '-CONTROL') / 'manifest.json').is_file():
                    continue
                if source.is_file() and source.name in REVIEW_NAMES and source.name != 'review-sheets.html':
                    add(source, Path(label) / source.relative_to(root))
            for source in sorted((root / 'media_code').glob('*')):
                if source.is_file() and source.suffix in ('.py', '.html', '.md'):
                    add(source, Path(label) / 'media_code' / source.name)
    for label in ('B028', 'B029'):
        viewer = destination / label / 'review/review-sheets.html'
        if viewer.parent.exists():
            if viewer.exists():
                viewer.unlink()
            subprocess.run([sys.executable, str(base / EXPERIMENTS[label] / 'media_code/sheet_viewer.py'), str(viewer.parent)], check=True)
    root = base / EXPERIMENTS['B029']
    for task in ('animal', 'human', 'vehicle'):
        folder = root / 'tasks' / task / 'shared_support'
        if not folder.exists():
            folder = root / 'map_review' / task / 'shared_support'
        for name in ('support-review.png', 'support.json') + (('support.safetensors',) if full else ()):
            if (folder / name).is_file():
                add(folder / name, Path('B029/maps') / task / name)
    (destination / 'UNCHANGED_MP4_HASHES.json').write_text(json.dumps(videos, indent=2) + '\n')
    (destination / 'ARCHIVE_EXCLUSIONS.md').write_text('''# Archive scope

This is a private combined B028/B029 development-panel delivery. Original MP4 files remain byte-exact; labeled comparison MP4s are newly encoded review derivatives. All17 sheets retain every frame with uniform sheet-only downscale. Temporal quality remains UNVERIFIED.

Excluded: model weights, condition caches, duplicate prefix features, duplicate per-frame comparison PNGs, temporary transfers, and B027 raw tensors already preserved in the original archive. For CONTROL cases, review-lite retains the four-column SOURCE/BASE/METHOD/CONTROL comparison instead of duplicating its METHOD-only three-column comparison. Full retains both. Full contains B028/B029 raw tensors and final latents. Review-lite also excludes pre-transform original-source PNGs while retaining all 17 actual processed source frames, references and masks; original-source PNGs remain in full. Review-lite omits these tensors and latents; no failed case is intentionally omitted.

B027 original full archive: make-meme-B-027-public-panel-20261026.zip, 872854474 bytes, SHA256 81e437aa8ee4e424bae0f32c6ed8eb5f4ce79cec5f0657c117bced7cf6bdff04. Existing /tmp archive on Spark and Mac supplies baseline raw lineage. B027 original source/reference/MP4 payloads are included here.

Payloads are transferred incrementally and archives assembled locally on each host. This is not a claim that a finished large ZIP was transferred unless the final receipt explicitly records that action. Missing or failed runtime stages are described in the experiment reports and attempt ledger.
''')
    (destination / 'README_KO.md').write_text("""# B-028 + B-029 비공개 검토 자료

먼저 [B-028 전체 비교 뷰어](B028/review/review-sheets.html)와 [B-029 기준선·방법·대조군 뷰어](B029/review/review-sheets.html)를 브라우저에서 열어 주세요. 모든17프레임과 local0/8/16을 유지했습니다. 영상은 source FPS 미확인에 따른 preview24fps이며 실제 원본 초 단위 시간축 보존을 주장하지 않습니다.

- [B-028 결과](docs/research/experiments/B-028-object-reference-normalization/RESULTS.md)
- [B-029 결과](docs/research/experiments/B-029-spatial-image-conditioning/RESULTS.md)
- [B-029 핵심 대조](docs/research/experiments/B-029-spatial-image-conditioning/ABLATIONS.md)
- [원본 MP4 해시 표](UNCHANGED_MP4_HASHES.json), [제외 목록](ARCHIVE_EXCLUSIONS.md)

`tasks/.../artifacts/output.mp4`는 생성 원본 MP4의 바이트를 그대로 보존합니다. 뷰어의 `comparison-preview24.mp4`는 라벨을 붙여 가로로 합친 검토용 파생 영상이며 새로운 생성 결과가 아닙니다. All17 시트는 전체 canvas를 균일하게50% 축소했고 대상별 확대·정렬을 하지 않았습니다. 반복 재생의 끝→처음 경계는 clip 내부 동작이 아닙니다.

시간 품질은 **UNVERIFIED**입니다. 브라우저 재생 가능·프레임 선택 기능 검사는 사람이 실제 속도로 연속 시청한 품질 승인과 다릅니다.

Full에는 `B028/tasks/<task>/cases/<ref>/artifacts/` 및 `B029/tasks/<task>/<METHOD 또는 CONTROL>/cases/<ref>/artifacts/`의 `raw_output.pt`, `final_latent.safetensors`, `final_latent.json`을 보존합니다. final latent의 모델·조건·VAE 규약은 해당 JSON과 재현 문서를 먼저 확인해야 하며, 조건 cache나 initial noise로 바꾸어 사용하면 안 됩니다.

Review-lite는 raw tensor·final latent·support tensor와 처리 전 original-source PNG를 제외합니다. 실제 처리된 source17장·reference·mask·원본 MP4·전체 프레임 비교는 유지합니다. CONTROL이 있는 case는 중복 METHOD 단독3열 대신 SOURCE/BASE/METHOD/CONTROL4열을 보여 줍니다. Full에는 두 비교를 모두 보존합니다. 가중치·중복 condition cache는 두 ZIP 모두 제외하고 기존 로컬 계보를 참조합니다.

`PAYLOAD_MANIFEST.json`은 각 payload의 크기·SHA256입니다. ZIP 자체의 크기·SHA256·CRC·실제 추출 검증과 호스트 간 전달 상태는 ZIP 옆의 별도 verification/receipt에 있습니다. 기존 원본과 과거 ZIP은 삭제하지 않았습니다.
""")
    print(json.dumps({'stage': str(destination), 'files': sum(p.is_file() for p in destination.rglob('*')),
                      'bytes': sum(p.stat().st_size for p in destination.rglob('*') if p.is_file()), 'full': full}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('base', type=Path)
    parser.add_argument('destination', type=Path)
    parser.add_argument('--full', action='store_true')
    args = parser.parse_args()
    stage(args.base, args.destination, args.full)
