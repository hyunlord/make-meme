# MEMORY_BUDGET_01 — 비교 미완료 / 실행 계약 오류로 운영 보류

**BLOCKED_EXECUTION_CONTRACT_ERROR**, 신규 영상·연구 품질 성과 없음. 사전 고정 `12e1eb5` 후 supervisor를 정확히1회 호출했다. 시작10초는 통과했지만 stage root를 상대경로로 전달한 실행자 오류로 systemd의 기본 작업 디렉터리에서 worker 파일을 찾지 못해 Python이반환2로 종료됐다. worker 본문·모델 로딩·sampler·forward·constraint·decode는 모두0이다. 새 heavy 승인한도를 사용 완료했다고 과장하지 않으며, 오류가 발생하면 종료하라는 이번 계약에 따라 재실행하지 않았다. 남은 숫자를 다음 자동실행 권한으로 넘기지 않는다.

## 운영 정책과 실제 관측

공통 memory verdict를 두 판정 경로·실제 preflight·시작·runtime·최종 관측에 연결했다. 필수 CPU21개는 Mac/Spark에서PASS, 양 stage 실제 no-model preflight는50개 freeze·B007E_LOADER_REPORT 경로/쓰기검사를 통과했다. loader report는 생성하지 않았고 torch/model import도 없었다. 최초 CPU 호출은 서비스 venv의 경로 문자열로 인해 자기 부모 명령이 SERVICE_APPEARED로 잡혔다. 기존 B034 연구 venv로 호출을 바로잡아 통과했으며 이 실패도 비공개 증거에 남긴다. 서비스 정책/allowlist를 완화하거나 외부 프로세스를 조작하지 않았다.

실제 시작6표본10.2548초, S0=258048bytes(252KiB), MemAvailable최소98.8871GiB. 시스템swap증가0, pswpout변화0, PSI full total변화0이며 GLOBAL_SWAP_WARNING을 그대로 기록했다. 이전256KiB와 현재252KiB는 서로다른시각의관측이다. 과거/현재swap발생주체UNKNOWN. 실제page size4096bytes를 읽었고 상수4KiB를 가정하지 않았다.10초 판단은 직전표본으로 구간을보수적으로감싸며 PSI분모는최대10초로제한한다.10.5초초과관측공백은실패다. 시작의 swap-out변화없음 기준은이번계약의보수적운영해석이며공식안전보증이아니다.

unit는failed/failed·MainPID0, 최종GPU목록0이고 서비스EXPECTED_ABSENT_OBSERVED/queue UNAVAILABLE·counts=null이다. worker진입전에실패하여 실제cgroup MemorySwapMax적용·swap/current/events·메모리압박운영검증은NOT_OBSERVED다. 종료후worker_memory=null과cgroup:REMOVED:exit_not_verified/OBSERVATION_FAILED를보존했으며0으로위조하지않았다. 원시guard_reason=COMPLETE는child종료만뜻하고, worker_returncode2·normal_exit없음·최종NOT_CLEAN을우선한다. 정상정리PASS·OOM·CUDA결함으로재분류하지않는다.

## 과학적 판정

기존BASE의클래식target외형FAIL, FINAL_LATENT_ONLY의추가이득미관찰을보존한다. 신규STEPraw/final latent/영상없음으로 차체·노출바퀴·열린상부·SUV잔존·접근동작·보호장면·경계/접촉/그림자의새비교는전부NOT_RUN이다. 배경개선이나비회귀PASS를부여할근거가없다. STEP효과INCONCLUSIVE, temporalUNVERIFIED,기본채택근거없음이다. 과거실패·UNKNOWN·소진장부를변경하지않았다.

## 종료와 범위

이번실행계약오류의책임은실행자에게있다. 기존supervisor는절대stage root로호출해야했으며preflight에는절대경로를썼지만실행호출에서상대경로를사용했다. 새복구실험·재시도·새예산을만들지않고종료한다. 운영코드·검사추가와실제heavy검증미완료를분리한다. ruff/basedpyright는기존환경에없어NOT_RUN이며설치하지않았다. 추가사례/seed/학습/모델/설정탐색은시작하지않았다.

수치/장부는[MEASUREMENTS](MEASUREMENTS.json),사전정책은[PLAN](PLAN.md),CPU/실제preflight는[CPU_REPORT](CPU_REPORT.json),전달증명은[DELIVERY](DELIVERY.md)를참조한다. 신규raw/latent가없어full미생성,신규비교MP4·뷰어도없다. 기존media/과거ZIP/대형raw를복제하지않고이번작은실행증거만전달한다.
