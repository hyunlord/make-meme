# B-034 RECOVERY_01 — 저장된 BASE latent의 VAE-only 복구

작성: 2026-10-27
저장소: `hyunlord/make-meme`
브랜치: `docs/b-research-20261022`
기준 결과 커밋: `082e2c3f455d5a43559caa61f710c591347fec5f`
상태: 제안 / 이 문서를 작성하면서 Spark 접근·GPU 실행·원격 변경은 하지 않음.

## 1. 목적과 연구 내 위치

B-034는 B-033의 고정 clean-prediction 제약을 새로운 공개 사례에서 검증하는 실험이다. 이번에는 그 가설·입력·방법을 변경하지 않는다. 중단된 차량 BASE의 이미 저장된 최종 latent를 한 번 디코딩해 연구를 재개할 출력을 확보한다.

새 B-035 가설이나 별도 커널·가드 연구를 만들지 않는다. B-034 안의 `RECOVERY_01`로 관리한다. 기존 `BLOCKED_AT_BASE_TEARDOWN`, `other_service_work`, 비강체 `ANCHOR_UNSUITABLE`, B-033 PARTIAL 판정은 그대로 보존한다.

현재 STEP은 실행되지 않았으므로 B-033 방법의 새 사례 성공·실패는 판정 불가다. BASE 디코딩 성공도 방법 검증 완료로 보고하지 않는다.

## 2. 먼저 확인할 기존 기록

최신 HEAD와 실제 Spark 작업 상태를 확인한다. 이미 같은 복구가 실행 중이거나 완료됐다면 중복하지 않는다. 기준 커밋으로 브랜치를 강제 되돌리지 않는다.

읽을 자료:
- B-034 `RESULTS.md`, `GUARD_EVENT.md`, `LATENT_REUSE.md`, `EXECUTION_COUNTS.json`
- B-034 `video_code/runtime_guard.py`, `video_code/run_phase.py`, `video_code/phase_decode.py`
- 기존 `BASE_S`의 `progress.json`, `phases.jsonl`, `pipeline-process.json`, `resource_metrics.jsonl`
- 최종 latent와 동일 위치의 JSON sidecar
- CHARTER, ROADMAP, HISTORY 및 기록 규약

저장 결과에 대한 확인 사실:
- 실제 40 step / 80 forward 후 `BASE_S_complete` 기록.
- worker returncode 0, 마지막 MainPID 0 / Result success / inactive.
- supervisor reason은 `other_service_work`로 남음.
- 마지막 cgroup.procs는 비었지만 직전에는 자체 worker가 있었음.
- 발동 순간의 queue 응답과 GPU PID 목록은 보존되지 않음.

이 기록만으로 실제 타 작업, 종료 관측 시차 중 하나를 확정하지 않는다. 최종 잠재공간 값이 유효한 것과 그때의 자원 상황이 안전했는지도 서로 다른 판단이다.

## 3. 과거 원인 조사는 짧게, 현재 안전 확인은 필수

기존 로그와 journal 등 이미 남은 자료를 최대 15분 동안 읽기 전용으로 확인한다. 동일 sampler를 재현하거나 다른 프로세스를 자극해 원인을 찾지 않는다.

정확한 과거 원인이 자료 부족으로 불명확하면 `UNKNOWN / INSUFFICIENT_EVENT_TELEMETRY`로 남긴다. 없는 queue/PID 증거를 추정으로 채우지 않는다. 모든 과거 원인을 완전히 규명할 때까지 이 파일의 디코딩을 무기한 막지는 않는다.

복구 시작의 안전 여부는 별도로 확인한다.
- 기존 보호 서비스의 실행/대기 queue가 비어 있는가?
- GPU PID가 기존에 허용된 프로세스와 그 identity(starttime·command hash 등)에 맞는가?
- 종료됐어야 할 자기 pipeline/watchdog가 남아 있지 않은가?
- 기존 시작 MemAvailable 72GiB, 실행 headroom 24GiB, swap 0 조건을 충족하는가?
- 새로운 복구 시간 제한과 소유 unit 식별자가 고정됐는가?

바쁘거나 알 수 없는 GPU 작업이 있거나 관측이 실패하면 새 작업을 시작하지 않는다. 다른 서비스 중단·queue 삭제·전역 캐시 삭제·driver/swap 변경·임계값 완화를 하지 않는다. 이번 세션에서 자동 대기 루프나 예약 실행은 만들지 않는다.

이전 실패한 stage의 `reason`을 `service_exit`로 바꾸거나, 기존 전역 predecessor 검사를 삭제하지 않는다. 대신 명시적으로 승인된 별도 artifact-consumer 복구 단계로 시작하고, 부모 artifact의 검증과 새 live safety 결과를 함께 기록한다. 기존 파일의 존재만으로 안전 가드를 통과시킨 것으로 처리하지 않는다.

## 4. 가드 관측은 최소 보강, 정책은 유지

현재 조건은 `queue_busy() OR (gpu_pids - baseline_gpu - owned_pids)`를 동일한 `other_service_work`로 묶는다. 이 둘과 관측 실패를 새 로그에서 구분하되, 기존 중단 기준은 완화하지 않는다.

새 복구용 supervisor의 시작·가드 발동·종료 시에 다음을 작은 JSON으로 남긴다.
- 각 관측의 시작/종료 시각과 monotonic 시각
- queue running/pending의 수와 작업 식별자(불필요한 prompt·개인정보 제외)
- 실제 GPU PID 집합, 허용 PID, 자체 cgroup PID, 미분류 PID
- 가능한 PID identity 정보와 `/proc` 소멸 여부
- worker PID/종료코드, systemd 상태, 현재 메모리·swap
- 어느 조건이 stop을 유발했는지와 관측 오류

queue를 bool로만 버리거나 OR short-circuit 때문에 조사값이 사라지지 않도록 한다. 그렇다고 관측 때문에 무한 재조회하거나 guard를 기다리게 하지 않는다. 알 수 없는 PID를 ‘방금 끝난 우리 작업일 것’이라고 허용하지 않는다.

새 unit과 cleanup/ExecStopPost는 복구 작업 자신만 가리켜야 한다. 기존 B-034의 고정 absolute deadline을 재사용하거나 무기한으로 늘리지 않고, 이번 복구에 한정된 새 deadline을 기록한다.

실제 GPU를 켜기 전 완료·queue busy·미분류 PID·관측 실패의 소형 CPU fixture만 확인한다. 가드 framework 전체 재작성·커널/driver 조사로 범위를 확장하지 않는다. 기존 global 코드 대신 복구 전용 작은 wrapper/diff로 남긴다.

## 5. 정확히 사용할 저장물

B-034 실제 root에서 아래 논리 경로를 찾는다. 채팅의 `/mnt/data` 경로를 Spark 경로로 가정하지 않는다.

`tasks/rigid_R1/cases/BASE/artifacts/final_latent.safetensors`

- 파일 크기: **2,293,840 bytes**
- 파일 SHA-256:
  `687197642b668543d771a14ce8a78fcfa5e58dee91f526ffead26a92448f4d40`
- tensor shape: **[16, 5, 64, 112]**
- dtype: **FP32**
- 원시 FP32 tensor bytes SHA-256:
  `3a0d6aacca1fe4342ba28b3ea1a12a5a0a2c7d83221226ae896c5cd1f0d322ad`
- 저장 tree: **{'x0': [tensor]}**, safetensors key `t0`, sidecar의 tree를 따른다.
- 생성 상태: BASE, constraints 0, 40 step / 80 forward.
- 표현: 공식 WanVAE wrapper가 사용하는 model-space latent.

파일·tensor hash, shape, dtype, finite, sidecar의 조건·가중치·실행 계보를 확인한다. source latent나 initial noise를 대신 쓰지 않는다. 기존 파일은 읽기 전용으로 두고 overwrite하지 않는다.

파일이 없다면 검증된 B-034 full ZIP이나 기존 로컬 artifact에서 복구한다. latent가 없거나 손상되었다고 sampler를 재실행하지 않는다. 확인되지 않으면 `ARTIFACT_INVALID_OR_MISSING`으로 종료한다.

## 6. VAE-only decode 한 번

기존에 검증된 WanVAE checkpoint·공식 wrapper·디코딩 정밀도·scaling 규약을 재사용한다. source encode, Qwen, T5, CLIP, 전체 SCAIL DiT, 학습 adapter를 로딩하지 않는다.

별도 `BASE_D_RECOVERY_01` consumer에서 저장된 x0만 입력한다. 기존 phase_decode의 디코딩 계산은 가능한 한 그대로 쓰고, 고정 predecessor 검사 때문에 이 복구를 숨은 skip/force 옵션으로 구현하지 않는다. 새 parent-artifact receipt와 현재 안전 확인을 필수로 하는 명시적 recovery entrypoint를 기록한다.

허용 연산:
- VAE 모델 적재: 1 worker
- 저장된 BASE latent의 VAE decode: 최대 **1회**
- 디코딩 결과의 CPU frame 저장·MP4 인코딩·검증

금지 연산:
- 신규 이미지 생성·encoder·BASE 또는 STEP sampler·학습: 모두 **0회**
- source reconstruction·FINAL_ONLY·STEP decode: **0회**
- 새 모델/패키지 다운로드·설치·외부 생성·imagegen: **0회**
- 자동 재시도: **0회**

출력은 **[3,17,512,896]**, finite, RGB 프레임 17장이다. 공식 decoder의 model-space scaling을 중복 적용하지 않는다. reference prefix를 잘라낸다며 다시 indexing하지 않는다; 저장물 자체가 generated x0다.

원본 fps가 확인되지 않은 상태를 유지한다.
`source_fps=null`, `preview_fps=24`, `timebase_assumed=true`.
17/24초의 파일 길이를 원본 실제 시간축으로 해석하지 않는다.

raw 결과·lossless PNG를 보존하고, 브라우저 호환 MP4는 명시한 고정 색상 변환/픽셀 포맷으로 만든다. 기존 source MP4 bytes는 바꾸지 않는다. preview를 새로 인코딩했다는 사실과 raw 보존을 구분한다. 영상 전체 ffmpeg decode 및 ffprobe의 크기·frame 수·fps를 검증한다.

## 7. 실제 영상 확인과 다음 단계의 경계

SOURCE / TARGET REFERENCE / A0 / BASE를 한 뷰어에 배치한다. 전체 17프레임과 local0/8/16을 확인한다.

다음을 분리해 기록한다.
- target형 차체·전면·바퀴 특징이 유지되는가?
- source의 접근·방향 변화가 대략 이어지는가?
- source형 SUV로 돌아가는가?
- 새 그래픽·객체·도로 패치·경계·접촉 문제가 있는가?

BASE가 잘 나와도 B-033 방법의 전이 성공이 아니다. BASE가 나빠도 실행되지 않은 STEP 효과의 실패가 아니다. 비강체 앵커 실패·영상 미실행도 그대로 보존한다.

같은 과제를 나쁘다는 이유로 다른 사례로 바꾸지 않는다. STEP/control과 출력 support 작성은 이번 복구 범위에 포함하지 않는다. 복구 결과를 확인한 뒤 원래 고정 검증을 이어갈 수 있는지 정한다. BASE가 깨끗하다면 이후에는 개선보다 회귀 여부를 보는 사례가 될 수 있다.

실제 속도 연속 시청을 누가 어떻게 수행했는지 증거가 없으면 `temporal=UNVERIFIED`다. 파일 재생 가능과 시간적 미관을 혼동하지 않는다.

## 8. 상태와 예산

전체 벽시계 상한 **60분**, 마지막 15분은 기록·전달·종료에 남긴다. GPU decode worker 자체 상한 **10분**. 과거 로그 분석은 최대 15분이다. deadline은 착수 시 실제 시간으로 한 번 고정하고 사후 연장하지 않는다.

실제 다른 GPU 작업이 있으면 안전 대기로 종료한다. 새 이미지·샘플러로 대체하거나 과거 결과를 재생성하지 않는다. runtime/guard 오류가 발생하면 저장된 raw와 로그를 보존하고 재시도하지 않는다.

필수 상태 구분:
- 이전 실행: `BLOCKED_AT_BASE_TEARDOWN` 유지.
- 부모 artifact: `VALIDATED` 또는 정확한 실패.
- 현재 안전 검사: `CLEAR` / `BUSY` / `UNKNOWN`.
- 복구 decode: `NOT_RUN` / `PASS` / `FAIL`.
- 복구 종료 감시: decode 결과와 별도 상태.
- B-034 방법 비교: 이번 범위 내에서는 계속 `NOT_RUN`.

새 종료에서도 worker 완료와 guard 이상이 동시에 있으면 둘 다 기록한다. 유효 raw를 삭제하거나 다시 생성하지 않는다. 그 상황을 ‘원래 가드가 오탐이었음’의 증거로 쓰지 않는다.

## 9. 공부·연구 기록·전달

이번 해설은 짧게 세 가지를 연결한다.
1. 샘플링 완료, artifact 무결성, 프로세스 정상 종료, 현재 자원 안전은 서로 다른 상태다.
2. 최종 latent를 저장했기 때문에 생성 모델 전체가 아니라 VAE만으로 영상 복원을 재개할 수 있다.
3. 과거 원인 불명과 현재 제한된 단계의 안전한 실행 허용은 별도 판단이다.

착수 전 `docs/research/experiments/B-034-fixed-method-transfer-validation/recovery/` 등에 의뢰서·RECOVERY_PLAN·검증 계약·예산을 기록한다. 최신 HEAD·실행 코드를 고정하고 연구 브랜치에 남긴다. main 수정·force push·기존 결과 변경은 하지 않는다.

종료 후 RECOVERY_RESULTS, guard 관측, artifact lineage, 재현, 비용을 기록하고 HISTORY/ROADMAP에는 복구 상태만 append한다. B-033 기본 채택·B-034 검증 완료로 올리지 않는다. commit/push와 remote SHA를 확인한다.

복구 후 작은 ZIP에 새 BASE raw/프레임/MP4·source/target/A0 비교·로그·코드·보고서·payload manifest를 묶는다. 기존 대형 ZIP이나 모델 가중치를 다시 넣지 않는다. 공개 저장소에는 실제 미디어·가중치·개인 경로·민감한 queue 정보가 아닌 비민감 코드/요약만 올린다.

Spark/Mac `/tmp`에 실제 저장·전송하고 CRC·payload hash·추출·양쪽 동일성을 확인한다. 이 검증의 범위를 정확히 보고한다.

최종 보고 첫 줄은 ‘저장된 BASE를 새 샘플링 없이 디코딩했는가?’로 답한다. 다음으로 차량 결과의 실제 품질, 보호 서비스 유지, 과거 미해결 원인, 새 연산 횟수와 비용을 제시한다. 이 복구 이후 자동 후속 실행·예약은 하지 않는다.
