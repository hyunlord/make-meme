# EXPECTED_ABSENT_02 — 고정 운영 계약의 한정 재개

시작 원격/로컬 HEAD `67fd290a553843e4075a836c3ed734e035d1f35a`. 이전 EXPECTED_ABSENT_01의 외부GPU 시작 차단과 heavy0, CONT01의 heavy실패1/forward0 및 모든 품질 판정을 보존한다.

사용자는 저장된 점유 작업을 한 번 읽기 전용으로 확인하고, 종료됐다면 이번 재개에만 동일 OPTIONAL_EXPECTED_ABSENT 계약을 적용하도록 승인했다. 2026-10-28 01:56:54UTC 단일 확인에서 이전과 같은 boot였으나 해당 프로세스의 /proc 항목은 없었다. 이전 숫자 PID를 허용 목록으로 등록하지 않는다. 과거 receipt에는 프로그램·cgroup UID·starttime/hash가 있으나 프로젝트/부모/상세 명령은 없어 UNKNOWN이다. 개인경로와 runtime신원은 비공개 기록에만 있다.

## 고정 사항과 새 실행 바인딩

worker/bootstrap/loader/policy/safety/supervisor 코드는 이전 고정본과 byte-identical이어야 한다. 새 정책·allowlist·가드 설계나 테스트 프로젝트를 만들지 않는다. 코드의 literal attempt_id 검사는 그대로 보존하므로 기존 `B034_CONT02_EXPECTED_ABSENT_01` 값은 구현이 요구하는 식별자로 남긴다. 실제 새 실행은 `resume_attempt_id=EXPECTED_ABSENT_02`, 새 stage root/unit 및 현재 deadline과 이번 명시적 승인으로 구분한다. 과거 root/receipt를 덮어쓰지 않으며 과거 승인을 영구 연장하지 않는다.

실행 시작 기준시각01:56:54UTC, GPU cutoff03:10UTC, hard deadline03:25UTC. 신규 입력이나 모델계산 변경은 없다. B033 clean_constraint, 조건cache, initialnoise/RNG/scheduler, source latent, E/M/crops, 모델/정밀도/attention을 유지한다. BASE/CONTROL은 읽기 전용이다.

## 실행 순서와 예산

1. 새 설정과 frozen code/input hashes를 확인하고 동일 worker의 CPU preflight를 수행한다. 기존13/24 fixture는 반복하지 않는다.
2. 계획·설정 hash·검증을 commit/push하고 최신 remoteSHA를 확인한다.
3. 기존 supervisor의 약2초 간격3표본에서 관련 서비스/listener/외부GPU/중복worker 부재, 시작72GiB, swap사용0, 관측 성공을 확인한다. 새 충돌은 즉시 중단하며 대기·자동재시도하지 않는다.
4. 통과하면 STEP loading/sampler 최대1회,40step·80forward·constraint40회를 실행한다. 최종latent를 원자저장/readback검증한다.
5. STEP 정상종료 및 fresh safety 뒤 해당 VAE decode 최대1회만 실행한다. 실패 시 sampler 재실행하지 않는다.
6. 같은 E의 RGB_POST 및 기존 평가crop으로 BASE/FINAL_ONLY/STEP을 비교하고 결과와 비용을 기록한다.

실행24GiB headroom/swap0/자체신원 감시를 유지한다. 외부 작업은 조작하지 않는다. BASE/CONTROL 재생성·재decode·encoder·이미지·학습·설치·다운로드0. 실제 모델 적재 시도, forward/step/constraint/decode를 따로 센다.

## 판정과 전달

클래식 target의 긴 차체·노출바퀴·열린상부와 SUV/왜건 회귀, 접근방향/크기, 보호장면, 경계/접촉/그림자를 분리한다. 같은SUV유지를 target non-regression PASS로 보지 않는다. 배경만 좋아도 target외형이 없으면 결합FAIL이다. 미시청 temporalUNVERIFIED, 비강체ANCHOR_UNSUITABLE/영상NOT_RUN, B033PARTIAL을 유지한다.

새 결과가 생기면 작은compact와 신규raw/latent full로 나누고 기존큰raw·과거ZIP은 중복하지 않는다. 양호스트CRC·payloadhash·실제추출·전송동일성을 검증한다. 실제충돌이면 새대형ZIP없이 근거와 사용0을 기록하고 종료한다. 추가사례·seed·튜닝·모델·자동재개를 예약하지 않는다.
