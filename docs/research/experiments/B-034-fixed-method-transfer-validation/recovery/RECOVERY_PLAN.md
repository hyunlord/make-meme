# B-034 RECOVERY_01 사전 고정

상태: PREPARING. 시작 원격 HEAD `082e2c3f455d5a43559caa61f710c591347fec5f`.
[전체 의뢰서](WORK_ORDER_KO.md)를 실행 기준으로 한다. 새 실험이 아니라 저장된 차량 BASE final latent의 명시적 artifact-consumer 복구다.

## 시간과 허용 연산

- 시작 2026-10-27 05:11:24 UTC, hard deadline 06:11:24 UTC.
- GPU 실행/새 장시간 작업 cutoff 05:56:24 UTC; 마지막15분은 기록·전달·종료.
- 과거 자료 조사 최대15분, worker 최대600초, WanVAE decode 최대1회.
- 이미지·encoder·sampler·학습·설치·재시도·CONTROL·STEP·출력 support 작성0회.

## 의존 관계와 검증

1. 기존 기록과 현재 중복 작업을 읽기 전용 확인한다. 과거 이유는 `UNKNOWN / INSUFFICIENT_EVENT_TELEMETRY`일 수 있으며 현재 안전 판정과 구분한다.
2. 지정 final latent의 파일/원시 tensor hash, FP32 [16,5,64,112], finite, tree와40step/80forward/BASE constraints0 계보를 확인한다.
3. 복구 전용 entrypoint와 별도 receipt를 사용한다. 전역 predecessor 검사나 과거 reason은 바꾸지 않는다.
4. 완료/queue busy/미분류 GPU PID/관측 실패 CPU fixture를 확인한다. 현재 queue·허용 PID identity·자체 PID·memory/swap 관측을 분리한다.
5. code/config를 commit/push한 뒤 live CLEAR일 때만 기존 WanVAE로1회 decode한다. 시작72GiB·실행24GiB·swap0과 기존 보호 서비스는 유지한다. 오류/UNKNOWN/BUSY이면 실행하지 않고 종료한다.
6. [3,17,512,896] finite raw·PNG·24fps 파생 preview를 저장하고 ffprobe/전체decode를 검사한다. 원본 source bytes는 보존한다.
7. SOURCE/TARGET/A0/BASE 전체17장과 local0/8/16을 비교한다. target외형·source동작·장면·형태를 분리하며 temporal=UNVERIFIED를 유지한다.
8. 결과/계보/비용/재현/기록과 작은 ZIP을 검증하고 종료한다.

## 바꾸지 않는 판정

이전 `BLOCKED_AT_BASE_TEARDOWN`와 `other_service_work`, 비강체 `ANCHOR_UNSUITABLE`, B033 PARTIAL은 보존한다. B034 방법 비교는 NOT_RUN이다. 복구 decode와 종료 감시는 별도 판정한다. 새 BASE 출력은 B033 전이 효과의 성공/실패 증거가 아니다.
