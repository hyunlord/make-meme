# B-007H 진행 기록

시작 원격 HEAD: `51daacac291f161a21edeac3a551375fdd24f08c`.
실행 시간 경계: 2026-10-22 23:35 UTC부터 보수적으로 계산, hard deadline 2026-10-23 02:35 UTC.
G cache read-only 재사용; P0·Lab0·다운로드0·학습0. Probe1 ≤300초, S1, 성공한 final latent에 D1.

## 착수

연구 공통 문서·G 결과/실측·실제 코드·H 계획을 확인했다. 코드와 계측을 구현하고 CPU fixture·독립 검토·실행 사전 commit/push 후 실제 probe를 시작한다. 현재 GPU 실행 NOT_RUN.

## 실행 사전 고정

코드/config commit `80f51ffacdb0b20a75e3ff8b1625784f7ded1d37`의 원격 일치를 확인했다. 원격 stage 코드/config/upstream 및 부모 캐시·sidecar 287/287 해시 검증 PASS. CPU3개 fixture·critical Ruff·독립 bounded review PASS. 전체 타입 검사는 NOT_CLEAN이며 STATIC_VALIDATION.json에 별도 기록한다. 모델 없는 실제 PROBE를300초 한도로1회 실행하며 통과·종료·회복 후에만 S로 이어간다.

## PROBE 실물 통과 / S 시작

PROBE는6.062초에 정상 종료했다. 실제64-byte CUDA copy/add/synchronize/readback PASS, 캐시16leaf 원래 device 및 roundtrip 값 검증 PASS, tiny 이후 CUDA RNG 상태 불변. 두 unit MainPID0·inactive 확인 후 fresh S를 시작했다. S는 CPU 가중치를 읽기 전에 실제 tiny 연산을 완료했다. 모델 적재·sampler·D 성공을 아직 주장하지 않는다.

## S가 기존 실패 지점을 통과

이번 실행에서 CPU staged load 뒤 tiny 재검사와16leaf 복원이 통과했다. DiT device 이동·재검사 후 첫 forward는254.93초에 완료됐고 첫 scheduler step은266.80초에 완료됐다. 동일40step sampler 진행 중이며 final latent·D·MP4는 아직 미완료다. 이전 G 원인을 초기화 순서 하나로 확정하지 않는다.
