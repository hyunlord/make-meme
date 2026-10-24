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

## CPU 계약 완료 및 실행 코드 고정

10개 CPU 검사 PASS(0.82초). preset atol/rtol2e-5 아래 ref Q/K norm 최대차9.5367e-7, ref-ref logit7.1526e-7; ref 이외 출력 bit-exact이며 cross logit은 변했다. 1307개 state key/shape와16leaf 원본무결성 확인. 전체 package CPU import의 T5 CUDA조회 실패는 보존하며 별도 meta fixture는 full-package/runtime 증거가 아니다. 실제 worker에서 canonical module·class/global SHA와 모든40block×80call을 다시 검증한다.

신규 typed helper2개 오류/경고0, 상속 dynamic adapter3개 typecheck90오류145경고는 NOT_CLEAN으로 공개한다. 억제나 범위밖 리팩터링으로 숨기지 않는다. [CPU 감사](CPU_AUDIT.json), [모델 diff](MODEL_PATCH.diff), [코드 manifest](PREREGISTERED_CODE.json), [입력](PREREGISTERED_INPUTS.json).

독립 읽기 검토는 제한된 실행 GO이며 영상 품질 인증이 아니다. 코드 manifest SHA `1a6827e21c23197fb1aeb0bfc656c933c184ee97618c73fea890071f54db224e`. 원격 고정 확인 후 PROBE→S→D 각최대1회 진행. 현재 GPU NOT_RUN.
