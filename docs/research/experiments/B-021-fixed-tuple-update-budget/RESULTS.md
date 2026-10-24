# B-021 결과: 20회 replay 기준 초과로 100회 비교 미완료

**STOPPED_AT_REPLAY_20 / 100UPDATE_COMPARISON_NOT_COMPLETED.** 실제 initial adapter에서 fresh AdamW로20update·8평가를 수행했다. 사전등록 adapter 재현 기준을 네 tensor 모두 넘겨21이전에 중단했다. 50/100평가·새 영상은 NOT_RUN이다. 이 결과는100회 학습의 효과가 없다는 증거가 아니다.

사전 실행 commit `62f853b087e7b48baf3401818bfec152110bfe63`, 시작 원격 HEAD `5cde7b21d269234917ac5a0ddc30c21494fff69e`. [PLAN](PLAN.md), [실행 기록](RUNNING.md), [실측](MEASUREMENTS.json), [독립 검증](VALIDATION_SUMMARY.json), [한국어 해설](../../lessons/B-021-finite-fm-optimization.md).

## 1. 완료·실패·미실행

| 항목 | 실제 결과 |
|---|---|
| initial adapter 실제 A/B·Bzero·hash | PASS, B-020 실물 그대로 로딩 |
| producer cache·입력·noise·optimizer 옵션 | PASS, producer=B-020 / consumer=B-021 분리 |
| P / prefix 전체 forward | 0 / 0 |
| TRAIN worker / 실제 update / tuple 평가 | 1 / 20 / 8 |
| update0 split parity | 네 tuple 모두 max_abs0 |
| update20 adapter replay | 네 tensor 모두 FAIL, 사전 atol1e-7/rtol1e-5 |
| update20 scalar loss replay | 네 tuple 모두 PASS |
| restart0/20 저장·CPU readback | PASS, adapter·optimizer·RNG·step·cursor 보존 |
| final base 값 hash / fresh component reload / OFF forward | NOT_REACHED,100회 뒤 검사 위치에 도달하지 않음 |
| 50/100 평가·100endpoint | NOT_RUN |
| PROBE / full sampler / decode | 0 / 0 / 0 |
| 재시도·추가 튜닝 | 0 |
| 새 영상 품질·100회 효과 | NOT_RUN |
| 기존 영상 temporal quality | UNVERIFIED, 이번에 연속 재생 검수하지 않음 |

매 수행step에서 기반parameter optimizer제외·grad=None·finite LoRA gradient·실제3FA2 backward node·고정head 입력gradient를 검사했다. 이 사실을 종료후 기반값 전체 hash 검사나 fresh model reload 성공으로 대체하지 않는다.20번째 checkpoint와 평가 저장 후 assertion이 발생해 durable train-progress에는19개 row만 남았다. 실제20회는 네 AdamW state의 step=20·tuple cursor2·adapter-020·20평가로 독립 확인했으며 누락된20번째 scalar row를 사후 생성하지 않았다.

## 2. 고정 조건과 초기 상태

사용자가 허용한 같은 Lab 영상 f126..142, PTS4.2..4.733333초,17frame/30fps,896×512를 그대로 사용했다. 영상길이는17/30초, 표본간격은16/30초다. 기존 착석 reference, D=Y와 RED/WHITE mask, positive/empty-negative, seed20261022, CFG5/UniPC40/shift3, animation H0·ALG OFF는 바꾸지 않았다. 원본30fps를 다른 fps로 재표시하지 않았다.

초기 adapter payload SHA `1a603a234d0806dcfc2738a1aaf380f0ad98baf934d543a73d7dbea307d1a56b`. Q/V A는 실제 FP32 `[4,5120]`, B는 `[5120,4]` exact zero다. initial의 네 tensor 값은 별도CPU 바이트 판독과 실제GPU 로딩값 비교로 확인했다. B-020 final20을 warm-start로 사용하지 않았다.

AdamW는 lr1e-4,wd0,betas(0.9,0.999),eps1e-8,amsgrad/maximize/capturable/differentiable=False,foreach/fused=None,decoupled_weight_decay=True다. 기존 pinned 환경에서 실제 resolved 옵션을 대조했다. last-block self_attn Q/V rank4·alpha4·dropout0,81,920parameter만 optimizer 대상이다. 나머지모델/head는 고정이며 head로 가는 gradient를 유지했다.

producer manifest SHA `11d03f307f70724502534cbbc109fcb874ebe51b254bc65ed94d7921b60aa01c`, consumer manifest SHA `3c30fca7bc3bf5379ac0eeeb2bb9fd23f3ecff5b17f8479b2ca5f86be090a330`. 기존fm.json이 입력manifest에 묶인 점을 실행 전 발견해 bytes를 보존하고 새 예산은consumer.json에만 두었다. 원본코드·캐시검사를 삭제하거나producer기록을 덮어쓰지 않았다. 기본모델 전체65GB SHA는 B-007D의 검증된 역사값을 재사용했으며 이번 fresh 전체rehash로 표현하지 않는다.

## 3. 실제 수치와 중단 해석

| tuple | B-021 update0 | 기존 B-020 update20 | B-021 update20 | update50 /100 |
|---|---:|---:|---:|---|
| train0 sigma0.2 | 0.1455920785665512 | 0.14547254145145416 | 0.14547225832939148 | NOT_RUN |
| train1 sigma0.5 | 0.05071360245347023 | 0.05067168548703194 | 0.050671838223934174 | NOT_RUN |
| train2 sigma0.8 | 0.03156200796365738 | 0.03149447962641716 | 0.031494442373514175 | NOT_RUN |
| sameclip holdout0.65 | 0.03840317949652672 | 0.03837953507900238 | 0.03837939724326134 | NOT_RUN |

[같은 tuple 평가곡선](curves/evaluation-by-tuple.png)과 [tuple별 pre-step loss](curves/training-by-tuple.png)는 다른sigma를 하나의 하강곡선으로 연결하지 않는다. 50/100은 결측을0으로 채우지 않고 NOT_RUN으로 표시했다. 두 지점 사이 선은 중간 평가값이 관측됐다는 뜻이 아니다.

| adapter | B-020 final20 대비 최대 절대차 | relative L2 | 사전 elementwise 판정 |
|---|---:|---:|---|
| q.A | 2.1911691874e-6 | 1.779873e-5 | FAIL |
| q.B | 5.2415998653e-6 | 2.873027e-4 | FAIL |
| v.A | 9.7928568721e-7 | 3.567393e-6 | FAIL |
| v.B | 3.4683844206e-6 | 1.599498e-4 | FAIL |

판정은 각 원소의 `abs(new-old) <= 1e-7 + 1e-5*abs(old)`이며 relative L2 자체를 threshold와 비교한 것이 아니다. 실제 파일의 값을 독립CPU로 다시 빼서 실패를 확인했다.

loss 차이의 최대는2.831221e-7이다. 각loss replay 차이는 기존20회 개선량의 약0.055~0.583%로 작다. 이는 사전 adapter 기준 실패를 면제하지 않지만, 큰 의미적/영상품질 차이가 입증됐다는 뜻도 아니다. **기준 초과와 품질상 의미를 분리하고 사후 tolerance 완화 없이 중단했다.**

기존평가 prediction으로 계산한 adapterOFF baseline 대비RMS는 update20에서 train0/1/2/holdout 각각0.00510031/0.00354606/0.00298315/0.00320714다. 이것은 B-020과B-021 prediction 사이 차이가 아니라 각새평가와캐시baseline의 차이다. 관측용 full-model forward를 추가하지 않았다.

## 4. 원인 판별의 현재 한계

보존로그상 첫 update의 loss는 exact 같지만 q.B gradient norm은약−1.0914e-10, v.B는약+1.4552e-11 차이가 있다. 처음scalar loss 차이는update2의−3.7253e-9다. 실제initial/입력/tuple/옵션이 같아도 bitwise재현은 자동보장되지 않는다.

공식 attention 경로의 deterministic=False는 가능한 수치 비결정성 근거지만, 이번에는 동일backward를 반복해 원인을 분리하지 않았다. 연산·추가관측의 실행순서 차이도 원인으로 확정하지 않는다. **원인은 UNKNOWN**이다. 이번기록만으로학습량 부족·모델용량한계·전체LoRA불가능을결론낼수없다.

## 5. 자원·저장물·검증 한계

TRAIN guard wall31.355초, 메모리cap16GiB, 최소MemAvailable87,478,116,352B, swap0, cgroup low/high/max/OOM/kill 전부0이다. 마지막 관측CUDA peakallocated4,854,839,808B, reserved최대6,272,581,632B, cgrouppeak2,085,511,168B다. 서로다른회계이며합산하거나40배해전체모델학습용량을추정하지않는다. 마지막 durable allocator관측은update19이며20후 peak가 별도로측정됐다고하지않는다.

실행은 자원가드가 아니라 replay assertion으로 exit1했다. 자체unit은PID0·failed종료상태이며다른서비스는그대로유지됐다. 종료후MemAvailable약96.25GB·swap0을확인했다. 학습/생성백그라운드작업은남기지않았다.

새산출물의범위는 PRIVATE_ONE_CLIP_FM_OVERFIT_NOT_PRODUCTION이다. 실제restart0/20은안전한tensor/primitive schema로보존했고 독립CPU에서optimizer4개모두step20·cursor2와adapter별도파일일치를확인했다. 이저장물로추가학습을자동재개하지않는다. 기존B-020의TEST_ONLY표기는역사기록으로보존했다.

CPU5검사·compile·criticalRuffPASS, 정적typing43errors519warnings NOT_CLEAN을보존한다. 소형CPU검사와실제20checkpointreadback은fresh100모델reload나영상품질수용을대신하지않는다.

## 6. 결론과 다음 하나

**20대100update효과 비교는 미완료다.** 학습초기계보와실제FM20update·재개상태보존은확인했으나사전replay검사에서중단했다. 새영상이없어착석/사족·머리/귀/목·padding/장면복사의100회변화를평가할수없다. 비공개ZIP의기존B-020영상은역사맥락용이며B-021출력으로표시하지않는다.

다음검증가설하나는 **동일입력의FA2 backward 수치 반복성이 이번초기gradient 차이를설명하는가**다. 별도사전등록의제한검증이필요하며이번에는추가backward·학습·sampling을실행하지않았다. threshold를지금낮추거나100회를재개하지않는다.
