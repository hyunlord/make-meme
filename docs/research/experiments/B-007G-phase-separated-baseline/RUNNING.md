# B-007G 실행 기록

- 시작: 2026-10-22 17:56:43 UTC (2026-10-23 KST).
- hard deadline: 2026-10-22 21:56:43 UTC. CPU E/F 비교는 18:41:43 UTC 이전 종료.
- 시작 원격 HEAD: `62c9ef583f109080e640184cecd58a7ad90a853d`.
- 사용자 승인: 공식 예제 조건 준비 P1회 → sampler S최대1회(실패 포함) → 최종 latent decode D1회. 선행 실패 시 후속 NOT_RUN. Lab/재시도/새 모델/학습 없음.
- 현재: 공통 문서·PLAN 확인, E/F 실제 코드·trace 감사와 단계 분리 구현 진행. 실제 P/S/D 모두 NOT_RUN.

## 순서와 완료 증거

1. E/F 동일 phase 및 객체 수명 비교: 진행 중. 누락 경계는 UNOBSERVED, 정확한 원인은 증거 없으면 UNKNOWN.
2. P/S/D 코드·설정·입력 고정 및 CPU 계약 fixture: 대기. 저장값/인자/RNG/scheduler/dtype 계약과 독립 검토를 통과해야 실행.
3. 사전 코드 commit/push 확인 후 P, 종료·자원 회복 후 S, 최종 latent 검증·종료·회복 후 D.
4. 실제 상태·관측·이론·재현 기록과 비공개 ZIP 검증, 원격 최종 SHA 확인.

E/F의 사용량과 실패를 보존한다. F post-sampler 변경은 NOT_REACHED이며 정책 실패로 해석하지 않는다. 기존 24GiB headroom, swap0, 타 서비스 보호를 유지한다. 프로세스 분리는 동시 상주를 줄이는 구조 가설이지 E/F 원인의 확정이나 영상 품질 성공이 아니다.

## 18:03 UTC — CPU 감사 종료, 실제 실행 준비

E/F 동시각으로 볼 수 없는 표본을 구분한 [비교](E_F_COMPARISON.md)와 [객체 수명](OBJECT_LIFETIME.md)을 작성했다. 정확한 F allocating operation은 UNKNOWN이다. cast_state와 model의 assign alias를 두 payload로 계산하지 않았다. 공식 generate와 nested sampler를 좁게 추출해 P/S/D로 연결하는 코드와 CPU fixture 검증을 진행한다. 아직 P/S/D 모두 NOT_RUN이다.

## 18:10 UTC — P 실물 조건 준비 시작

실행 전 고정 commit `648bbe4a1cf9cb13ddf25a6c9b5ca111282b0d6b`의 원격 일치를 확인했다. 가중치8·의존성 증거168·원본 코드8·기존 입력/config10·G 공식 입력 subset5항목을 새로 해시 비교해 일치했다. 최종 고정 코드13개와 CPU fixtures5/5(2.59초)를 확인했다. P는 별도 guarded process에서 시작했고 DiT를 생성하지 않는다. S/D는 아직 NOT_RUN이며 P 저장물·정상 종료·자원 회복 검사를 기다린다.

## P 완료 / S 한정 시도 시작

P guard 정상 종료143.331초, pipeline/watchdog inactive·MainPID0을 확인했다. 조건 저장물17,365,660bytes의 SHA는 `1f1e0b68495b2276a5b6d12eaf160897a16acb2bd2a089e616a55c40bf590308`; lossless readback과 E initial noise 실제 값·해시가 일치한다. P 최소 MemAvailable70,981,316,608bytes, 관측 CUDA allocator peak4,320,272,384bytes. 종료 뒤 MemAvailable93,767,056KiB로 회복한 것을 확인한 후 S1을 시작한다. P 성공은 sampler/MP4 성공이 아니다.

## 최종 종료

P PASS, S FAILED before sampler, D NOT_RUN. 세부 상태·오류·보존 자료는 [RESULTS](RESULTS.md), [장부](RUN_LEDGER.json), [실측](MEASUREMENTS.json)에 고정했다. S1/1 사용, 재시도 없음. 자체 실행 프로세스는 종료됐다.
