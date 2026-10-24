# B-016 실행 기록

2026-10-24, 시작 원격 `6ef151b090d6c839e99d84a3547e7671f128e5ac`.

## 사전 고정

ALG pilot은 종료하고 기본 경로로 채택하지 않는다. B-013 LAB_MOV를 대조군으로 보존한다. animation·기존 CFG에서 reference RoPE H만 0→120으로 변경한다. 120은 patch 위치 인덱스이며 pixel 이동이나 공식 replacement 전체가 아니다.

- P0, PROBE/S/D 각 최대1, retry0. 40step·80forward.
- 시작 UTC00:27, 전체 deadline UTC03:27. worker 보수적 cutoff UTC03:00.
- CPU 코드 검토·fixture 최대45분. 실패하면 실제 sampler 이전 중지한다.
- 기존 캐시16leaf·noise·RNG·scheduler 불변; upstream·A·기존 결과 보존.
- 72GiB 시작/24GiB 실행 headroom, swap0, 다른 서비스 보호 유지.
- 코드·config·입력 해시·CPU 결과를 공개 고정하고 원격 반영 확인 후만 GPU 실행한다.

현재: CPU 검증 준비 중. PROBE/S/D NOT_RUN. 영상 품질 NOT_RUN.

평가: [사전 평가](PREREG_EVALUATION.md), [PLAN](PLAN.md).
