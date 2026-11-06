# SAMPLE.json schema v1.0

V-005부터 생성 출력마다 비공개 `dataset/<experiment>/<run>/SAMPLE.json`을 남긴다. V-003·V-004도 실제 보존 자료에서 소급 작성한다. 소급 기록 시각은 생성 시각과 다르며 `record_origin=BACKFILL`로 구분한다. 원본 파일은 복사·수정하지 않는다. 공개 Git에는 이 문서와 비민감 builder만 둔다.

필수 항목:

- `sample_id`, `experiment`, `run_id`: 출력의 식별자.
- `source`: 원본 영상, 실제 구간 프레임 디렉터리의 경로·hash, 원본 타임라인 `[start,end_exclusive)`와 fps.
- `references`: Lab·IG 원본 사진의 경로·hash·역할. 실제 읽은 호스트를 명시한다.
- `anchors`: 실제 실행 앵커의 원본 구간 위치와 native 위치, 이미지 경로·hash, 적용된 gate 결과와 gate 기록 경로·hash. 사용하지 않은 앵커를 포함하지 않는다.
- `sam`: 원본·출력 summary와 mask 디렉터리의 경로·hash 및 트랙 대응을 판단한 지표 기록. 원본 track 번호를 출력에 자동 적용하지 않는다.
- `control`: 사용한 canny/확대 canny 경로·hash.
- `scene_config`, `generation`: 실제 설정 경로·hash, 모델 경로, seed, 조건 강도·키프레임 binding, 실제 sigma grid·step·call 수와 receipt 경로·hash. 큰 가중치를 다시 읽지 않은 경우 검증한 것처럼 표시하지 않는다.
- `outputs`: native RAW, 비교 RAW, POST 경로·hash. native와 비교본이 같으면 동일 경로가 허용된다. S3의 native145→짝수73 선택은 decode receipt로 구분한다. 국소 합성 등 추가 파생본은 별도 role로 기록한다.
- `human_review`: 처음에는 반드시 `status=PENDING`, `form_values=null`, `source_form=null`. 자동 지표·과거 요약·사용자 대화 평가를 학습용 승인 라벨로 대신하지 않는다. 사용자가 검토 양식을 작성한 뒤에만 그 양식과 hash를 연결해 별도 개정한다.

모든 asset 기록은 `path`, `kind`, `sha256`, 파일이면 `bytes`를 가진다. 디렉터리는 정렬된 상대 파일명·byte·SHA256 목록과 그 canonical JSON의 SHA256을 저장한다. mask·프레임 inventory를 통해 누락도 검출할 수 있다. 경로는 호스트별 절대경로이며, 경로가 기록됐다는 사실만으로 모든 호스트에 복사되었다고 주장하지 않는다.

`build_sample.py` 입력은 비공개 manifest의 `samples` 배열이다. 파일·디렉터리 참조를 `{ "asset_path": "...", "glob": "*.png" }` 형태로 둔다(`glob`은 디렉터리에만 사용). 이미 검증한 다른 호스트의 자산은 `host`, `path`, `sha256`, `bytes`, `verified_at_utc`를 가진 고정 기록으로 전달한다. `expected_sha256`가 있으면 readback hash와 일치해야 한다. 필수 파일 부재·불일치·기존 SAMPLE 존재 시 실패하며, 성공 기록을 덮어쓰지 않는다. CPU 파일 읽기와 JSON 저장만 수행하며 모델·학습·SAM을 실행하지 않는다.

학습 가능한 예시로의 편입 여부는 이 기록의 존재와 다르다. 자동 품질 순위·선택·학습 실행은 하지 않는다.
