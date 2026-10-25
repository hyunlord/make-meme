# B-027 전체 비용과 측정 범위

실행 중인 기록이다. 완료 수치와 판정은 모든 worker 종료 후 확정한다.

## 준비 비용

- 공개 DAVIS archive 832,766,765bytes(약0.776GiB), HTTP 다운로드124.402632초, SHA256 `e3d0b5b77c3d031b000a19e0e25e3e2cac65d183755601bc2cf066df1a2aa492`, 전체ZIP CRC 확인.
- 7sequence 열람, 최종3과제/6참조와 제외3입력묶음. 선택·마스크는 공개GT를 제공받는 비용이며 자동 추적 성능이 아니다.
- 원본 JPEG/PNG에서 CPU resize·lossless RGB clip·실제 재decode 검증을 수행했다. 비용에는 입력 열람·문서화·검토물 작성도 포함되지만 agent token 비용이나 사람 노동시간을 측정하지는 않았다.
- 전체 wall-clock 시작 기준은 2026-10-25T15:11:00Z, hard deadline23:11:00Z다. 이를 실제 GPU 사용시간과 구분한다.
- 시작 호출의 상대경로 실패, 남은 실패 watchdog으로 인한 launch 거절, PROBE 대신 R1_PROBE가 필요한 CLI 인자 거절의 3건을 보존한다. 모두 실제 sampler 시작 이전이다. 준비 실패를 성공 시도의 일부로 숨기거나 sampler 재시도라고 계산하지 않는다.

## 회계 규칙

`reporting_code/summarize.py`는 실제 stage supervisor/phase JSONL을 읽는다. 시스템 MemAvailable 최소, swap 최대, 프로세스 RSS/RssAnon/RssFile, cgroup current/peak/anon/file/events, CUDA allocated/reserved/peak를 따로 기록한다. 이들은 겹치는 회계이며 합산하지 않는다. cgroup high 이벤트만으로 OOM이나 CUDA 결함을 확정하지 않는다. 종료 returncode0뿐 아니라 guard reason, 실제 result, step/forward counter와 산출물 유한값·shape를 확인한다.

ENC는 task마다 공통 T5/drive 및 첫 참조를 계산하고 두 번째 참조 VAE/CLIP/mask만 추가한다. DiT를 동시에 올리지 않는다. sampler 비용은 각 CFG40step80forward로 같지만 입력과 실제 runtime에 따라 경과시간이 달라질 수 있다. 관측을 위한 추가 모델 forward는 없다. 출력 시각 실패도 비용 분모에서 제외하지 않는다.

새 모델·패키지·학습·외부 생성·imagegen은0이다. 기존 SCAIL 자산과 환경의 과거 설치·다운로드 비용은 이번 새 다운로드와 섞지 않는다. GPU 작업은 순차이며 다른 서비스의 baseline 사용량을 이번 작업 메모리로 귀속하지 않는다.
