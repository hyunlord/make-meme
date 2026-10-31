# C-010 RESULTS — 궤적 신호는 어디서 약해지나 (2026-10-31)

## 결론
궤적 신호는 adapter 안에서 **사라지지 않는다.** residual로 실제 hidden에 더해지고, 최종 예측도 바꾼다. 문제는 그 변화의 **방향**이다.
- ON−NULL로 생긴 예측 변화는 σ 0.95·0.50에서 네 사례 모두 FM 오차를 줄이는 방향이 아니다 (가중 cos −0.06 ~ +0.02, 손실은 오히려 증가).
- 학습 기울기도 ON과 NULL이 거의 같다 (projection cos 0.94–0.98, motion context cos 0.95–0.997).
- 현재 목적함수와 조건 아래에서 adapter는 궤적을 쓰라는 신호를 거의 받지 못하고, 양쪽에 공통인 보정만 배운 것으로 보인다.

사전 규칙상 판정은 **DIAGNOSTIC_INCONCLUSIVE**다 (아래 규칙 6이 정의대로는 성립하지 않음). 우선 가설은 **조건 중복으로 인해 궤적 고유의 학습 신호가 없다**는 것이다.

**다음에 바꿀 요소 하나 (제안, 미실행)**: 중간 프레임의 동적 윤곽을 VACE 조건에서 뺀다(endpoint-only 조건). 그래서 중간 움직임 정보가 point 궤적으로만 들어오게 한 대조에서 같은 진단을 다시 한다.

## 1. 입력에 구별할 만큼의 차이가 있었나 — 있다
ON−NULL 위치 차이 (공통 가시 중간점, px): bear 평균 7.0/p90 15.8, dance-twirl 23.8/62.6, elephant 3.7/7.7, goat 14.3/20.5.
- NULL은 양끝이 보이면 중간을 전부 visible로 둔다. 그래서 ON에서는 가려졌는데 NULL에서만 gate인 점이 93–343개다. ON에서만 gate인 점은 0이다.
- patch, anchor_valid, kernel 폭은 동일하다.
- elephant가 가장 작은 대비를 가진다. 시트로 보면 일부 점은 몸 밖(물줄기/지면)에 있다.
- P1 상대 차이 0.15–0.26 → INPUT_CONTRAST_LIMITED 아님.

## 2. 어디까지 전달됐나 — 최종 예측까지
ckpt256, ON vs NULL, 각 경계 **안에서**의 상대 차이 (σ 무관하게 거의 같음):

| 경계 | bear | dance-twirl | elephant | goat |
|---|---|---|---|---|
| P1 입력 (gated) | 0.17 | 0.26 | 0.15 | 0.18 |
| P2 MLP | 0.083 | 0.10 | 0.072 | 0.086 |
| P4 splat (support) | 0.38 | 1.07 | 0.35 | 0.72 |
| 시간 평균 η | 0.97 | 0.98 | 0.96 | 0.97 |
| P5 grouped (support) | 0.35 | 0.98 | 0.32 | 0.66 |
| P6 residual b26 (support) | 0.34 | 0.98 | 0.34 | 0.67 |
| hidden b26 덧셈 후 (support, σ0.5) | 0.0094 | 0.023 | 0.0093 | 0.017 |
| pre-head (support, σ0.5) | 0.020 | 0.056 | 0.020 | 0.036 |
| 예측 RMS(v_ON−v_NULL)/RMS(v_BASE) σ0.5 | 0.0093 | 0.022 | 0.010 | 0.013 |

- MLP에서 차이가 절반으로 줄지만, 공간 배치에서 위치가 달라지므로 다시 커진다. 시간 평균은 차이 에너지의 96–98%를 남긴다(상쇄 없음). projection도 그대로 옮긴다.
- 규칙 2·3 불성립.
- hidden 단계의 값이 작아 보이는 이유는 감쇠가 아니라 주입 크기 때문이다. residual이 hidden의 약 2.5%이므로 0.34 × 0.025 ≈ 0.009다.
- 이후 block을 지나며 차이는 커지고(b26 → pre-head 약 2배), 예측에도 남는다 → 규칙 5 불성립.

## 3. 의도한 residual과 실제 hidden 변화
block26 support 기준 residual/hidden RMS: 2.2–2.6% (b29 1.0–1.6%).
- 실효/의도 RMS = 1.00, cast 상대 오차 0.17%.
- 0이 아닌 residual 원소 중 BF16 덧셈 후 hidden이 변하지 않은 비율: 16–29%. 크기가 작은 원소가 반올림으로 사라진 것이며, RMS로는 거의 영향이 없다.
- support 밖의 residual은 정확히 0이다(구조적 0).
- 규칙 4 불성립 → EFFECTIVE_UPDATE_ROUNDING을 주원인으로 보지 않는다.

## 4. 최종 변화가 정답 오차를 줄였나
`L_A − L_B = ||Δ||²_W − 2⟨Δ, e_B⟩_W` (분해식과 직접 계산 차이 ≤ 2e-16):

| ckpt256 | σ0.95 | σ0.50 | σ0.05 |
|---|---|---|---|
| ON vs BASE 손실 차 | −0.0019 ~ −0.0061 (4/4 개선, cos 0.14–0.25) | 3/4 개선 (cos 0.05–0.14) | 4/4 악화 (+0.001 ~ +0.005, cos 0.03) |
| NULL vs BASE | ON과 거의 같거나 더 좋음 | 같음 | 같음 |
| **ON vs NULL** | 4/4 ON이 나쁨 (cos −0.06 ~ −0.002) | 4/4 ON이 나쁨 (cos −0.001 ~ +0.02) | 3/4 ON이 좋음 (cos 0.02–0.07; goat만 나쁨) |

- BASE보다 나아진 부분은 NULL도 똑같이 얻는다 → 공통 adapter 보정이다.
- 궤적 고유 변화(ON−NULL)는 높은·중간 σ에서 오차 방향과 거의 직교하거나 반대여서 ||Δ||²만큼 손실을 늘린다. 낮은 σ에서만 약하게 정렬된다.
- 객체 영역이 ON−NULL 손실 차이의 대부분을 차지한다(예: dance-twirl σ0.5 객체 +0.0045, 배경 −0.00003).

## 5. 일관성
- ckpt128과 256은 같은 패턴이다(ON−NULL 부호가 셀 단위로 일치).
- train(bear, dance-twirl)과 validation(elephant, goat)의 차이 없음 → TRAIN_VALIDATION_GAP 아님.
- σ에 따라 방향이 바뀌는 것(낮은 σ에서만 정렬)이 유일한 축이다.
- 저장된 C-009 NEW_ON_5 rollout 상태(σ 1.0 / 0.56 / 0.09)에서 ON−NULL은 BASE RMS의 0.5% / 0.9% / 1.7%로, one-step probe와 같은 크기다. 정답 velocity가 없으므로 방향은 판단하지 않는다.

## 6. gradient와 유한 차분이 말하는 것
- **gradient**: ON/NULL parameter gradient cos는 projection 0.94–0.98(dance-twirl 0.56–0.65), MLP0 0.67–0.99이고, motion context gradient cos는 0.95–0.997이다.
  balanced FM loss가 주는 학습 방향이 궤적 유무와 거의 무관하다. 즉 256회 학습이 ON과 NULL을 구별하도록 밀어주지 않았다.
  첫 linear에서 `delta_q` 열은 입력 RMS 0.002–0.01, 원소당 gradient가 다른 열보다 약 100배 작다(1e-7 vs 1e-5). 차원과 단위가 달라 원인으로 단정하지는 않는다.
  `positions.detach()` 때문에 좌표 gradient가 None인 것은 학습 단절이 아니다.
- **유한 차분** (한 track, ±4/±8 px, σ0.5, ckpt256): 반응은 있다. 반복 바닥은 0으로 결정적이다.
  - grouped context와 residual 차이는 변위에 비례해 2배가 된다.
  - 그러나 예측 차이는 4px와 8px에서 거의 같고(0.0054→0.0059, goat), D4·D8 방향 cos는 0.05–0.17이다.
  - 즉 작은 residual 변화가 BF16 backbone을 지나며 크기·방향이 일정하지 않은 약 0.005 RMS의 변화로 나타난다.
  - ON−NULL 예측 차이(0.010–0.016)는 이 바닥의 2–3배에 불과하다. 이는 §4의 cos≈0과 맞는 관측이지만, 이번 사전 규칙에는 없던 해석이므로 **관측**으로만 남긴다.
- dance-twirl은 FD 후보 track이 없다(FD_NOT_AVAILABLE).

## 사전 규칙 판정
| 규칙 | 결과 |
|---|---|
| 1 INPUT_CONTRAST_LIMITED | ✗ |
| 2 FEATURE_ATTENUATION (집계) | ✗ (η 0.96–0.98, P5 ≫ P2) |
| 3 PROJECTION_INSENSITIVE | ✗ |
| 4 EFFECTIVE_UPDATE_ROUNDING | ✗ (실효/의도 1.0, 불변 16–29%) |
| 5 READOUT_INSENSITIVE | ✗ |
| 6 MISALIGNED_CORRECTION | **정의대로는 ✗**: 첫 조건(ON vs BASE cos ≤ 0.02)이 공통 보정 때문에 성립하지 않는다. 둘째 조건(ON−NULL 손실 ≥ 0)은 9/12 셀에서 성립 |
| 7 TRAIN_VALIDATION_GAP | ✗ |

PLAN에 따라 **DIAGNOSTIC_INCONCLUSIVE**다. 규칙 6을 사후에 ON−NULL 기준으로 바꾸지 않는다. 대신 그 증거(§4·§6)를 근거로 우선 가설 하나를 둔다.

## 7. 다음 변경 하나와 반증 조건
- **선택: 조건 중복 제거.** 학습·진단 조건의 VACE 중간 프레임에서 동적 윤곽을 빼고(양끝 앵커만, 기존 `condition_mode=endpoint`), point 궤적만 중간 움직임을 전달하게 한다. adapter·loss·scale·위치는 그대로 둔다.
- **근거**: 신호는 예측까지 전달되지만(§2·3), 궤적 고유 변화가 FM 오차와 정렬되지 않고(§4), 학습 gradient가 ON/NULL을 구별하지 않는다(§6).
  noisy state와 동적 윤곽이 이미 중간 움직임을 주므로 궤적이 줄 추가 정보가 거의 없다는 설명이 가장 단순하다.
- **반증 조건**: endpoint-only 조건에서 같은 진단을 했을 때 아래 셋이 모두 나오면 조건 중복 가설을 버린다.
  1. ON/NULL motion-context gradient cos가 여전히 > 0.9
  2. σ0.5에서 ON−NULL 손실 차이가 여전히 ≥ 0 (4사례 중 3 이상)
  3. ON−NULL 예측 차이가 같은 크기 임의 섭동 바닥의 3배 이하
  그때 다음 후보는 표현(`delta_q`·offset 단위가 1e-3 수준인 입력 설계)이다.
- **이번 결과가 하지 않는 말**: 더 큰 residual이나 더 긴 학습이 해법이라는 근거는 없다. 낮은 σ의 약한 정렬을 동작 이득으로 부르지 않는다.
  one-step 학습형 probe의 noisy state에는 이미 중간 target 정보가 들어 있다. 따라서 "point를 덜 쓴다"가 곧 "생성에서 point가 불필요하다"는 뜻은 아니다.

## 비용
full forward 127 / 131 (main 84, observer OFF 4, 반복 2, gradient 16, FD 12, rollout 9). VJP 16, adapter-only 116, optimizer step 0, 학습·sampler·VAE·다운로드 0.
heavy stage 126초, 메모리 peak 8.7 GB, swap 0. guard 변경 없음. 관측 사본은 원본과 bit-exact(4/4)이고, 반복 차이 0이다.
