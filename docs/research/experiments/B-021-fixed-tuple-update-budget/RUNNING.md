# B-021 실행 기록

2026-10-24 · 시작 원격 HEAD `5cde7b21d269234917ac5a0ddc30c21494fff69e`.

## 착수

사용자의 이번 실행 지시로 신규 100update·100endpoint sampler1/decode1을 승인 범위로 기록한다. PLAN 등록만으로 GPU를 시작하지 않았으며, 현재는 기존 B-020 초기 adapter·producer cache·실제 AdamW 옵션과 소비 코드 검증 단계다. 기존 사용자 제공 Lab 자료와 사용 범위는 재확인 요구 없이 유지한다.

전체 마감은 2026-10-24 15:28 UTC이며 기존 시작72GiB·실행24GiB headroom·swap0·타 서비스 보호 조건을 유지한다. 학습worker1, 자동재시도0; P/prefix0. 새로운 소비 코드를 고정하고 공개 기록을 push한 뒤에만 GPU를 실행한다.

실행 순서: 초기 상태와 producer 검증 → CPU 계약과 사전 코드 고정 → TRAIN1(0/20/50/100 평가,20 replay gate) → 안전 회복 → PROBE1 → S1(100endpoint,40step80forward) → final latent 보존/종료 → D1 → 전체17장 비교/기록/비공개ZIP.

새 학습은 final20 warm-start가 아니라 실제 initial A/B + fresh AdamW의 0→100이다. replay 의미 불일치가 있으면21번째 update 전에 중단하며 tolerance 사후 완화나 임의 초기화는 하지 않는다. 품질과 기술 성공은 별도다.

## 실행 전 고정

CPU에서 실제 initial payload/4개 tensor 값과 producer target·조건·4prefix 파일 해시를 확인했다. CUDA는 초기화하지 않았다. 초기 payload SHA는 `1a603a234d0806dcfc2738a1aaf380f0ad98baf934d543a73d7dbea307d1a56b`, producer manifest SHA는 `11d03f307f70724502534cbbc109fcb874ebe51b254bc65ed94d7921b60aa01c`다. [CPU_PREFLIGHT](CPU_PREFLIGHT.json), [consumer 계약](configs/consumer.json).

20 replay의 사전 tolerance는 adapter와 tuple loss 각각 atol1e-7/rtol1e-5다. 기존 split/reload/OFF atol/rtol1e-3은 별도로 유지한다. 의미 불일치 시20 checkpoint와 실패 보고를 보존하고21이전 중단한다. 결과를 본 뒤 tolerance를 넓히지 않는다.

실제 pinned AdamW 기본값은 betas=(0.9,0.999),eps1e-8,wd0,amsgrad/maximize/capturable/differentiable=False,foreach/fused=None,decoupled_weight_decay=True다. `None`을 backend강제False로 바꾸지 않는다. 0/20/50/100 restart 저장물은 tensor/primitive 저장과 optimizer 구조 재로딩으로 값·옵션·RNG·cursor를 확인한다.

CPU5검사·compile·critical Ruff는 PASS다. 정적 typing은43errors519warnings로 NOT_CLEAN이며 unresolved환경import와상속dynamicdict진단 등을 raw보고에 남긴다. ignore나검사삭제로 clean을 만들지 않았다. 이는 실제GPU 학습·영상 검증을 대신하지 않는다.

사전 관측에서 별도 GPU 벤치마크가 잠시 있었고 자체 종료를 확인했다. 타 작업을 종료하지 않았으며 실행 직전 GPU사용프로세스·headroom·swap을 재확인한다. 보호대상 프로세스 ID와 실제 절대경로는 공개하지 않는다.

실제 GPU 실행 전 CPU 계약에서 B-020 입력 manifest가 fm.json도 hash로 고정하는 점을 확인했다. 기존 fm.json을 변경하는 안은 실행 전에 철회하고 producer bytes를 그대로 보존하며 새 예산을 consumer.json에만 두었다. 기존 입력 검사는 삭제하지 않았다. 전체4stage의 실제입력·code/upstream hash·producer cache binding 검사가 CPU에서 통과했다. GPU 시도는0이다.

최종 사전 manifest SHA256: `3c30fca7bc3bf5379ac0eeeb2bb9fd23f3ecff5b17f8479b2ca5f86be090a330`. 독립 리뷰도 이 수정본에 PASS했다. 이전 candidate hash와 CPU 실패 원인은 비공개 기록에 보존했다.
