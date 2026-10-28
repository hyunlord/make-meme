# EXPECTED_ABSENT_02 결과 — STOPPED_BY_SYSTEM_SWAP / STEP 미완료

사전 고정 커밋 `2d5339b69f8a39d4e96ddc4c310689c8971f7cef` 이후 같은 loader·정책·guard·입력·방법으로 재개했다. **새 STEP 영상은 없다.** CPU 가중치 적재 완료 뒤 DiT device 이동 시작 단계에서 system swap 사용량이0을 초과해 기존 가드가 자체 worker를 중단했다. 설정을 바꾸거나 재시도하지 않았다.

## 기존 점유 작업과 현재 확인

이전 차단 receipt의 프로그램은 캡처 실행파일이었고 cgroup 사용자와 시작 tick이 남아 있었다. 관련 프로젝트와 부모 프로세스는 기록되지 않아 UNKNOWN이다. 같은 boot에서 한 번 수행한 2026-10-28 01:56:54UTC의 지정 프로세스 확인에서는 /proc 항목이 없었다. PID 숫자만으로 같은 작업이라고 판단하지 않았고, 정상 종료 이유나 어느 프로젝트의 실행인지 사후 추정하지 않았다. 사용자명·실행 경로·runtime 신원은 비공개 요약에만 남긴다.

## 고정 계약과 실제 실행

공개 frozen code7개와 새 배포본은 byte-identical이고 historical allowlist도 보존했다. 새 root/unit/deadline 및 이번 승인만 새 설정에 연결했다. literal policy implementation ID는 변경하지 않았으며 실제 재개 ID는 EXPECTED_ABSENT_02로 따로 기록했다. 이전 승인이나 차단 상태를 소급 변경하지 않았다.

동일 worker CPU preflight와 실제 시작3표본은 통과했다. 서비스 EXPECTED_ABSENT_OBSERVED, queue UNAVAILABLE/counts=null, 외부GPU/중복worker 없음, 시작72GiB·swap0 조건을 확인한 후 worker를 실행했다.

02:02:23.363UTC 실행 중 표본에서 MemAvailable68,581,933,056bytes(약63.87GiB), system swap사용262,144bytes(256KiB)를 관측했다.24GiB headroom 위반이 아니라 **swap0 조건 위반**이다. 실제 guard reason은 SYSTEM_HEADROOM_OR_SWAP이다. own cgroup pswpout0 관측만으로 system swap의 유발 주체를 확정할 수 없다. 원인은 UNKNOWN이며 OOM·CUDA·커널 결함으로 확대하지 않는다.

supervisor는 자체 worker만 TERM 중단했다. worker returncode0만으로 PASS하지 않았으며 normal_exit_recorded=false와 NOT_CLEAN 상태를 보존했다. 마지막 phase는 dit_to_device_start다. 최종 종료와 수치 근거는 MEASUREMENTS.json 및 비공개 원시 receipt를 따른다.

| 사용량 | 이번 실제 값 |
|---|---|
| 모델 적재/heavy 시도 | 1 |
| full sampler 시도 | 1 — sampler-attempt 기록 후 첫 forward 전 중단 |
| 모델 forward / scheduler step / clean constraint | 첫 forward 미도달 / 관측0 / 관측0 |
| 새 final latent / raw / MP4 | 없음 |
| STEP decode | 0, sampler 미완료로 미실행 |
| BASE/CONTROL 재생성·재decode, encoder, 이미지, 학습 | 모두0 |
| 설치·다운로드·자동재시도·서비스 조작 | 모두0 |

종료 counter receipt는 NOT_WRITTEN이다. 첫 forward 미도달과 step/constraint 관측0은 마지막 phase와 실행 경로에 근거하며, 정상 완료 counter가 저장됐다는 뜻이 아니다. 종료 후 자체 unit inactive·GPU 목록 비어 있음과 frozen 파일48개 불변을 확인했다. 시스템 swap256KiB는 남았으며 설정을 변경하지 않았다.

이전 CONTINUATION_01 heavy실패1/forward0과 이번 시도는 별도 장부다. 이전 EXPECTED_ABSENT_01의 시작 차단/heavy0도 보존한다. 이번 미사용 예산을 다시 있다고 간주하지 않는다.

## 최종 비교 상태와 방법 결정

- BASE: 기존 클래식 target 외형 FAIL, 닫힌 SUV/왜건 계열이 남음.
- FINAL_LATENT_ONLY: 동일 RGB_POST 뒤 뚜렷한 추가 개선 미관찰, 기존 판정 유지.
- STEP: 실제 영상 NOT_RUN, 두 대조군 대비 추가 이득 **INCONCLUSIVE**. 실행 중 안전 차단을 방법의 효과 없음으로 해석하지 않는다.
- 비강체: ANCHOR_UNSUITABLE/영상 NOT_RUN 유지. B-033의 단일 사례 PARTIAL 유지.
- target 회복과 결합 목표 개선은 새로 입증되지 않았으며 기본 방법 채택 근거도 생기지 않았다. temporal=UNVERIFIED다.

새 STEP raw가 없어 동일 후합성·시트·비교 MP4를 만들지 않았다. 기존 결과를 새 결과처럼 포장하지 않는다. 새 runtime 근거만 작은 증거 ZIP으로 전달하고 기존 큰raw/latent/ZIP을 중복하지 않는다. 코드·정책·메모리/swap 기준을 바꾸지 않고 이번 범위는 종료한다. 추가 seed·방법·재개를 자동 실행하거나 예약하지 않는다.
