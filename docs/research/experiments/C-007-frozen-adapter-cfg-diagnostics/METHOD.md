# C-007 실제 진단 경로

C-006의 point_features, point_adapter, wan_adapter_forward, training_state, runtime_common은 동일 바이트 사본이다. optimizer를 정의하는 부모 함수는 호출하지 않는다. 모든 모델은 eval/requires_grad_(False), 진단 및 생성은 no_grad다. adapter 모듈 생성은 fork_rng로 격리하고 저장된 adapter state만 strict load한다. optimizer state나 학습 RNG를 복원하지 않는다.

## 입력과 시간

1000-step Wan grid와 50-step 생성 grid는 별도 scheduler 객체다. 진단 noise는 영상별 CPU Generator seed20261101/20261102에서 한 번 만들고 모든 sigma·checkpoint·branch에 공유한다. 설치 scheduler의 add_noise와 training_target으로 zσ 및 ε−z0를 구한다. exact FP32 sigma/timestep과 모델에 들어가는 BF16 timestep을 구분한다. 생성 pipeline의 실제 CFG1은 positive 한 번, CFG5는 positive/negative 각각 한 번 뒤 기존 BF16 결합이다.

진단의 clean_latent/loss_mask는 one-step에서만 읽는다. 영상과 rollout replay는 sequence/split/prompt/patches/anchor_valid/positions/visible/valid/box_wh 아홉 key만 담은 sidecar를 읽는다. 기존 load_cache로 수동 제외를 적용하고 raw cache는 변경하지 않는다. 생성기에는 clean target·loss mask·cached text/VACE tensor를 넘기지 않는다. 실제 PNG 양끝/동적 layout을 pipeline이 다시 인코딩한다. 실제 생성 text/VACE context는 사후 CPU에서 진단 cache와 비교한다.

## 읽기 전용 관측

ResidualObserver는 원래 adapter.forward 앞에서 동일한 gate와 Gaussian kernel의 지원 영역만 계산한다. MLP나 projection은 추가로 실행하지 않는다. 각 projection의 원래 FP32 출력을 forward hook으로 읽고, 원 residual 함수가 반환한 결과를 그대로 돌려준다. FP32 residual, BF16 cast, 실제 (h+r)−h를 구분하며 전체와 실제 support의 RMS·norm·token p50/p95/max를 기록한다. geometry support와 context가 수치적으로 0이 아닌 영역은 별도 값이다.

RolloutTrace는 실제 positive flag와 text context hash/equality로 branch를 식별한다. 같은 step의 두 branch가 같은 latent와 BF16 timestep을 쓰는지 확인한다. 원 scheduler.step을 정확히 한 번 호출한 뒤 반환된 tensor를 변경 없이 관측한다. 50개 step의 latent/prediction/update 요약과 다섯 pre-step snapshot을 저장한다. 영상 frame t와 sampler step j는 다른 축이다.

같은-state replay는 CFG5 두 경로의 저장 latent·실제 context·실제 timestep을 사용한다. native/ON의 positive/negative 네 예측으로 delta와 CFG 결합 차이를 구하며 원 경로의 저장 예측과 allclose를 확인한다. 생성 상태에 target velocity가 있다고 가정하거나 clean target을 대입한 FM loss를 만들지 않는다.

## 지표의 범위

분기 MSE는 latent channel 평균 뒤 객체/배경 영역별 평균이며 balanced loss는 두 평균의 합이다. clean estimate 오차는 같은 data-noised state에서의 진단으로, sigma² velocity 오차와 관련되어 독립 품질 증거가 아니다. negative branch의 감독 오차도 일반적인 negative conditioning 정답으로 해석하지 않는다.

CFG delta는 동일 latent에서 Δ5=5δ+−4δ−=δ++4(δ+−δ−)다. native BF16 guided prediction과 FP32 식 재구성의 차이를 따로 보존한다. norm이 1e-12 이하인 분모/두 delta의 cosine은 null이다. 서로 달라진 두 rollout의 prediction을 같은-state delta로 섞지 않는다. latent 오차나 norm은 동작 정확도·정체성 점수가 아니다.

기본 연산 검사는 sigma 다섯 개 × 두 영상 × 두 text branch의 native/bypass/zero 범위이며 전 입력 함수 동등성의 증명은 아니다. 본질적 불일치가 있으면 primary 원인 진단을 제한하고 원 알고리즘을 조용히 수리하지 않는다. 기존 guard와 실패 기록은 유지한다.
