# C-007: 한 번의 예측과 반복 생성은 다른 질문이다

## 직관: 같은 상태에서 좋아졌는가, 계속 따라가도 좋은가?

one-step 검사는 정답 영상 latent z₀에 알려진 noise ε를 섞은 상태에서 예측을 비교한다. 생성은 자신의 직전 예측으로 다음 상태를 만들므로, 작은 차이가 이후 입력 자체를 바꾼다. 한 번의 validation loss 감소가 실제 영상 보존을 보장하지 않는다. 이번에는 학습을 다시 하지 않고 C-006의 0/128/256 checkpoint를 고정해 이 간극을 관찰했다.

Flow Matching의 개념식은 zσ=(1−σ)z₀+σε, v*=ε−z₀다. `diagnose.py`는 설치 scheduler의 `add_noise`와 `training_target`을 실제로 호출한다. 객체 평균과 배경 평균 MSE를 합친 balanced loss를 positive/negative 각각 기록한다. ẑ₀=zσ−σv̂의 오차는 같은 noisy state에서 대략 σ²배 velocity 오차이므로 별개의 품질 증거가 아니다. 생성 중 상태에는 알려진 (z₀, ε) 쌍이 없으므로 replay에서 이 정답 loss를 만들지 않는다.

## 시간축과 조건을 분리하기

영상 프레임 t=0..32, VAE 시간 latent 9개, 생성 step j=0..49, training grid index 0..999는 다른 축이다. 이번 latent는 [1,16,9,30,52], DiT token은 [1,3510,1536]이다. training probe의 목표 sigma .95/.75/.50/.20/.05는 별도 1000개 shift5 grid에서 가장 가까운 실제 값을 선택했다. 예를 들어 exact sigma .95009595와 FP32 timestep 950.09595는 모델에 들어갈 때 BF16 timestep 952로 반올림된다. adapter는 실제 sigma를 사용한다. 생성 grid를 probe grid로 덮어쓰지 않는다.

부모의 index 200/500/800 probe는 낮은 sigma를 직접 검사하지 않았다. 이번 최저 probe는 .04807693이고, 50-step rollout의 마지막 pre-step sigma는 .09259259다. 같은 낮은 영역을 다루지만 정확히 같은 지점이라고 쓰면 안 된다.

positive는 실제 caption, negative는 기존 `blurry, distorted, deformed, watermark`다. negative는 빈 무조건부 branch가 아니다. TRACK_NULL은 중간 궤적을 endpoint에서 유도한 조건으로 대체하는 point 모드이며 텍스트는 그대로다. bypass는 adapter 잔차를 아예 추가하지 않는 custom forward다. CFG1은 positive만 실행하지만 앵커·layout·point 조건은 유지한다.

## CFG가 모든 adapter 차이를 다섯 배 만드는 것은 아니다

같은 z에서 BASE 예측을 b₊,b₋, adapter 예측을 a₊,a₋라 하면 δ₊=a₊−b₊, δ₋=a₋−b₋다. CFG 결합은 v_w=v₋+w(v₊−v₋)이므로

Δ₅=5δ₊−4δ₋=δ₊+4(δ₊−δ₋).

두 branch의 adapter 변화가 같으면 δ₊−δ₋=0이고 추가 증폭은 없다. 이번 checkpoint256 ON의 data-noised probe에서 두 변화의 cosine은 약 .984~.997이고 Δ₅/Δ₁ RMS 비율은 약 1.063~1.274였다. 이는 무조건 5배라는 설명에 반례다. 분모가 거의 0이면 비율과 cosine은 null로 남겼다.

`diagnostic_metrics.py`는 통계를 FP32로 계산하지만 sampler의 원 BF16 결합은 바꾸지 않는다. 실제 BF16 guided prediction과 FP32 식의 차이는 rounding 진단으로 별도 기록했다. guided output의 unguided target MSE 하나로 CFG가 틀렸다고 판정하지 않는다.

## 실제 함수와 잔차의 위치

`wan_adapter_forward.py`는 부모와 동일한 바이트 사본이다. 26~29번 block 직전에 point–anchor 잔차를 더하고 원 VACE hint 순서를 유지한다. `ResidualObserver`는 원 projection 출력을 한 번 읽고 원 반환값을 그대로 전달한다. 실제 splat support는 visibility/validity/finite/inbounds gate, Gaussian cutoff와 시간 pooling의 합집합으로 구하며 MLP나 projection을 다시 실행하지 않는다.

FP32 residual r, BF16로 cast한 r, 실제 (h+r)−h는 서로 다를 수 있다. 작은 값은 BF16 덧셈에서 일부 사라지고 큰 국소값은 후속 attention을 통해 배경까지 영향을 줄 수 있다. 따라서 국소 주입은 국소 출력 보장의 뜻이 아니다. zero-init의 residual 0은 초기 보존을 설명하지만 학습 후 residual이 0이 아니므로 같은 보존을 보장하지 않는다. 이번 native/bypass/zero 일치 검증은 두 영상·다섯 sigma·두 branch 범위이며 모든 입력의 함수 동등성 증명이 아니다.

## 관측과 반례

128/256의 ON과 NULL은 두 영상·두 branch에서 높은/중간 sigma의 balanced loss를 낮췄지만 .20/.05에서는 높였다. 예를 들어 elephant positive의 .20 부근은 BASE .48554에서 256 ON .51750으로, .05 부근은 1.22805에서 1.34021로 악화했다. goat에서도 같은 방향이었다. 특정 sigma에서의 개선을 한 평균으로 합쳐 전 구간 개선이라고 부를 수 없다.

실제 CFG1 ON 영상에서도 BASE1보다 큰 색 번짐·중복 윤곽·배경 손상이 보였다. negative branch를 실행하지 않은 조건이므로 CFG5는 이 회귀의 필요조건이 아니다. 동시에 BASE1 자체에도 색/형태 손상이 있어 모든 artifact를 adapter 탓으로 돌릴 수 없다. 유한한 latent RMS와 시각적 손상은 공존하며 NaN이나 수치 폭발이 관측됐다는 뜻이 아니다. 네 영상과 같은-state replay의 최종 해석은 RESULTS.md에 모았다.

ON/NULL의 유사한 probe 변화는 공유 adapter 부분을 원인 후보로 좁히지만 중간 궤적이 쓸모없다는 증명은 아니다. 낮은 sigma의 회귀, 학습된 공유 잔차, 입력 상태 변화는 함께 존재할 수 있다. Flow Matching 자체가 잘못된 목적이라는 결론도 아니다. 이번은 두 validation 영상과 한 seed의 동결 진단이다.

## 이번에 발견한 조건 계약의 한계

사후 CPU 비교에서 실제 생성의 VACE context와 진단 cache는 RMS .766806/max_abs6.421875로 달랐다. 실제 RGB/mask, tile 크기/stride, 인자 순서와 text는 같지만 inactive/reactive RGB branch의 시간 latent1~8이 다르고0은 같다. mask64는 정확히 같으며 원인은 UNKNOWN이다. 이 차이를 추가 encoder 실행으로 조사하거나 고치지 않았다.

따라서 teacher-forced probe와 rollout의 차이를 오직 자기 예측 누적이나 distribution shift로 설명할 수 없다. 입력 context 차이도 섞여 있다. 반면 실제 savedcontext를 사용하는 같은-state replay20개 비교는 max_abs0으로 재현됐으므로 그 범위의 Δ 분해는 유효하다. 다음 후보 하나는 loss/scale 변경보다 먼저 cache↔generation 조건 인코딩 계약을 규명·검증하는 것이다. 현재 결과로 원인이 확정됐거나 수리가 완료됐다고 주장하지 않는다.

## 이해 확인

1. CFG1은 무조건부 생성인가? 아니다. positive text와 기존 영상/point 조건을 유지하고 negative 호출만 생략한다.
2. δ₊=δ₋이면 CFG5의 adapter 변화는? Δ₅=δ₊이며 다섯 배가 아니다.
3. 서로 다른 rollout의 같은 step prediction 차이를 Δ₅ 식에 넣어도 되는가? 안 된다. 입력 z가 달라 누적 경로 효과가 섞인다. 저장된 같은 z에 두 predictor를 평가해야 한다.
4. 마지막 step j49는 영상 frame49인가? 아니다. 영상은 33프레임이고 j는 50번 Euler 갱신의 인덱스다.
5. loss 감소와 영상 손상이 모순인가? 아니다. 제한된 정답 noisy state의 오차와 자기 예측을 반복한 생성 경로의 품질은 다른 평가다. 이번에는 VACE context도 달라 순수한 반복 효과로 해석할 수 없다.

근거: [Classifier-Free Diffusion Guidance](https://arxiv.org/abs/2207.12598), [Flow Matching for Generative Modeling](https://arxiv.org/abs/2210.02747). 실제 연산은 고정한 설치 파일과 C-007 코드/receipt를 기준으로 해석하며 문헌의 이론을 이번 pilot의 안정성 보증으로 옮기지 않는다.
