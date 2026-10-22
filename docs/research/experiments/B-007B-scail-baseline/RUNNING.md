# B-007B 실행 기록

## 2026-10-22 07:45 UTC — 착수

- 기준 remote HEAD `53c58f3615418ee1a2c46c8fb3435a82518e3650`, 기존 docs checkout clean 확인 후 ff-only로 반입했다. A 및 과거 실험은 보존한다.
- 전체 deadline13:45 UTC. Gate0 입력·환경 → Gate1 소형 공식 변환 대조 → Gate2 최대85GB 선택 다운로드 → Gate3 bounded변환/로딩/최대2추론 → Gate4 평가·기록·ZIP 순서다.
- 신규 학습0, optionalLoRA0. 작은 변환 통과는 대형 checkpoint 안전 보장이 아니며 실제 metadata/memory guard에서 별도 차단할 수 있다.
- 기본 upstream의 FP32 ctor+state_dict 중복상주 위험 때문에 isolated meta/assign 로딩 경로를 검토한다. runtime dtype과 연산 변경 여부를 실제 코드·checkpoint로 구분하고 실행 전에 고정한다.
- CPU 입력 검증·변환 fixture·runtime guard는 독립 병렬 준비하되 대형 다운로드/추론은 root의 순차 Gate 확인 뒤 실행한다.

## Gate 0/1 설계 고정 — 실행 전

- fresh 관측: MemAvailable95,957,929,984 bytes, swap0, disk약1.2496TB, 기존 서비스 queue0/0. 다른 서비스를 종료하지 않는다.
- 사용자 cgroup의 작은 프로세스 제한 probe가 작동했다. 대형 단계는 MemoryMax60GiB/MemoryHigh56GiB/MemorySwapMax0와 단계 deadline, MemAvailable30GiB 이하 지속 watchdog를 함께 사용한다. cgroup의 file cache도 과금되며 sudden OOM 위험을 없애는 보장은 아니다.
- 변환은 공식 key mapping과 원래 tensor dtype을 유지하는 mmap CPU/weights_only + 순차 safetensors 쓰기를 검증한다. 메타데이터 구조나 contiguity가 호환되지 않으면 eager/unsafe pickle로 fallback하지 않는다.
- 기본 DiT FP32 전체상주 대신 **메모리 제한 mixed-BF16 baseline**을 사전 선택한다. 큰 projection/FFN/conv는BF16, 실제 FP32 연산 경로의 time_embedding/time_projection/head 및 modulation/norm은FP32로 유지한다. 이 선택은 공식FP32출력 동등성 주장이 아니다. meta/assign의 같은dtype 동등성과BF16반올림을 소형 fixture에서 별도로 확인한다.
- 고정 공식 tree에 animation_001의 reference/mask/driving이 실제 blob으로 존재한다. 별도 추출·시간축 검사 후 호환되면 공식17f1회→Lab17f1회 순서이며 결과를 보고 prompt/seed/steps를 튜닝하지 않는다.

## 08:01 UTC 부근 — Gate 0/1 조건부 통과, Gate 2 시작 조건 충족

- 실제 Spark 격리 Python/Torch2.14.0+cu130에서 변환 fixture8개 PASS(1.21초). 공식 mapping/save_file tensor 값·dtype·hash와 independent verifier의 payload 손상 거부를 확인했다. 합성 fixture이며 실제65GB형식/peak는 여전히 UNKNOWN이다.
- 실제 upstream cache_video로 원본RGB17장을24fps512×896 MP4로 저장하고 ffprobe17f/0.708333초 확인. 최초 FFMPEG plugin 누락 실패는 기록에 보존했다. 신규환경에만 작은필수패키지26,031,848bytes를 설치했고 Torch는 교체하지 않았다.
- 입력80파일 Mac/Spark 해시동일, 기존Lab148artifact검증. LabmaskPARTIAL과공식예제16fps 유지.
- 공개 고정 downloader/manifest에 따라재사용파일해시를먼저검증하고 신규SAT+CLIP만최대85GB범위에서받는다. actualmetadata gate가실패하면 eager/unsafe로우회하지않는다.
