# 2026-10-24 — B-020 검토와 B-021 한정 증량 결정

## 검토 범위

기준 원격 commit `13ac7727e501913ed7e765f44f1d8f6385a19178`의 RESULTS, TRAINING_SUMMARY.json, INPUT_AMENDMENT.md, code/phase_train.py, phase_sample.py, fm_contract.py를 직접 읽고 branch HEAD도 확인했다. 검토자가 Spark에서 재실행한 것은 아니다.

제공 `make-meme-B-020-20261024-final.zip`은 이번 세션에서 container와 Python 각각 ClientError로 접근하지 못했다. 제출값 173,475,156bytes와 SHA `3a59de2c416aa5c5b37b75843251614b0f9dce672f0027af75c3c3135ef6f108`, 양호스트 CRC/hash 일치는 실행 담당자의 보고값이다. 이번 검토자가 영상·payload·호스트 사본을 독립 확인한 것으로 기록하지 않는다.

## 현재 증거

B-020은 실제 허용된 Lab 자연동작 Y를 VAE encode하고 frozen-prefix4tuple을 통과한 실제특징에서 마지막block Q/V LoRA81,920개를20update했다. 공식head/unpatchify까지 gradient를 유지한 실제FM velocity target이다. 인공hidden MSE에서 실제영상 FM으로 넘어왔으며, 네tuple split parity/reload/OFF와base불변이 기록상 PASS다.

| 동일tuple | 학습전 MSE | 20update후 MSE |
|---|---:|---:|
| train sigma0.2 | 0.1455920785665512 | 0.14547254145145416 |
| train sigma0.5 | 0.05071360245347023 | 0.05067168548703194 |
| train sigma0.8 | 0.03156200796365738 | 0.03149447962641716 |
| sameclip holdout0.65 | 0.03840317949652672 | 0.03837953507900238 |

loss 감소는 작고, 실제 학습전후 출력은 착석·후기번짐/잘림을 유지했다. 목표는 원본의 사족으로 서 있는 자연동작 재구성이며 두발춤학습이 아니다. 같은clip·고정3noise/time tuple, 마지막Q/V rank4만 학습한 결과이므로 전체 모델 fine-tuning의 한계나 일반적인 LoRA 실패로 해석할 수 없다. holdout도 독립영상·새개체 평가가 아니다.

## 결정

1. 추가 component smoke나 모델변환/새데이터감사를 하지 않는다. 사용자 제공 영상과 사용허가, 실제 target 및 캐시를 재사용한다.
2. 실행자의100update 제안을 **동일 유한FM문제의 최적화 예산 진단 한 번**으로 채택한다. 설정·데이터·lr·rank·학습층은 그대로이며 개선을 약속하지 않는다.
3. 공개runner는 optimizer state를 저장하지 않는다. final20adapter+fresh AdamW80update를 연속100update라고 부르지 않는다. B-021은 보존한 실제initialadapter에서 fresh AdamW로0→100을 새로 실행하며, 신규예산도100으로 명시한다.
4. 0/20/50/100의 동일4tuple을 비교한다. sigma가 달라 loss scale도 다른 step들을 이어서 학습곡선 하강을 주장하지 않는다. 새로운20회 지점의 replay 차이와 기존 학습변화 크기를 비교해 근거 수준을 남긴다.
5. P/prefix 재계산0, 기존0/20영상재생성0. 100endpoint만sampler1/decode1로 평가한다. 좋은중간checkpoint선별·추가seed·200/500회자동확장없음.
6. 향후 재개를 위해 adapter와optimizer/RNG/step/tuplecursor를 함께 보존한다. parent feature producer hash와 새consumer code hash를 혼동해 기존검사를 삭제하지 않는다.

[실행 계획](../experiments/B-021-fixed-tuple-update-budget/PLAN.md)

## 해석과 연구 방향

train 고정점적합, 같은clip의새noise/time, 실제CFG rollout, 새로운영상/개체일반화는 서로 다른 증거다. 추가update가 작은loss를 더 낮춰도 생성중 자기궤적과 다른 시각조건 경로·공간자세를 해결한다는 보장은 없다. 한정증량 뒤에는 곡선·실제예측변화·영상에 따라 학습분포 또는 학습위치 등 다음가설 하나를 정한다. 입력옵션탐색·성공포장·기록시스템확장을 성과로 삼지 않는다.

이번 원격 변경은 PLAN과 이결정문서 추가뿐이며 기존실행코드·결과·모델·공통이력본문은 수정하지 않았다. 실제B-021은 **PLANNED / NOT_RUN**이고 실행담당자는 사용자수행지시 이후에만 착수해 HISTORY/ROADMAP에 이결정과실제상태를 연결한다. 작성시점 새GPU학습/생성/다운로드0회다.

공식 참고: [PyTorch 일반 checkpoint와optimizer 재개](https://docs.pytorch.org/tutorials/beginner/saving_loading_models.html#saving-loading-a-general-checkpoint-for-inference-and-or-resuming-training), [Flow Matching 원논문](https://arxiv.org/abs/2210.02747), [LoRA 원논문](https://arxiv.org/abs/2106.09685). 후자의일반원리가 이번동물과제의품질개선을보장하지는않는다.
