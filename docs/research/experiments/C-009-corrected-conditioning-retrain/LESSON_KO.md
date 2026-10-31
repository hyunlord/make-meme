# C-009 해설 — 입력을 고치자 손상은 사라졌고, 방법의 이득도 함께 사라졌다

## 1. 직관
C-006 adapter는 "빨강 채널만 생성 대상"이라는 이상한 조건에서 학습됐다. 그 조건의 VACE context에서는 기반 모델의 예측부터 크게 틀렸고(step0 validation 0.26–0.92), adapter는 그 오류를 메우는 방향으로 움직였다.
생성 때는 정상 context가 들어오므로, 배운 보정은 필요 없는 보정이 되어 붉은 번짐으로 나타났다. 정상 context에서 다시 학습하니 메울 오류가 거의 없었고, adapter는 거의 아무것도 바꾸지 않았다.

## 2. 수식
c_bad = 빨간 마스크 cache, c_good = 흰 마스크 cache, ψ₀ = 같은 초기값, S = 같은 학습 schedule(clip·σ·NULL·negative 순서).

    ψ_bad  = Train(ψ₀, c_bad,  S)      (C-006 train-v2)
    ψ_good = Train(ψ₀, c_good, S)      (C-009)

평가는 모두 같은 c_good에서 한다:

    v_base(z,σ,c_good),  v_{ψ_bad}(z,σ,c_good),  v_{ψ_good}(z,σ,c_good)

마스크 채널 오류: I = (1−M)⊙N(X), R = M⊙N(X). M_bad = [1,0,0]이면 중간 프레임의 G/B가 inactive로 새고 R만 reactive로 간다. mask64는 M[0]만 읽으므로 두 cache에서 같다. 그래서 mask64 비교만으로는 차이가 보이지 않는다. 실제로 13개 모두 mask64는 같았고, RGB branch만 rms 약 1.32 달랐다.

## 3. 실제 함수와 값
- `vace_context` 하나만 바꾸고 나머지 key는 byte 단위로 그대로 두었다. 그래야 "조건 하나만 바꾼 통제 실험"이 된다. target·patch·T5가 함께 바뀌면 원인을 나눌 수 없다.
- 256에서 이어 학습하지 않은 이유: ψ_bad는 c_bad에 맞춘 상태라서, 거기서 출발하면 ψ₀ 대비 비교가 아니게 된다. C-006 `train_adapter.py`의 resume 경로로 `train/checkpoint-000.pt`의 adapter, optimizer, CPU/CUDA RNG, generator, order, cursor를 그대로 복원했다. 새 step000은 과거 step000과 모든 항목에서 exact였다.
- seed가 같은 것과 상태가 같은 것은 다르다. 같은 seed라도 module 생성이나 진단에서 RNG를 먼저 소비하면 noise가 달라진다. 저장된 generator 상태와 같은 호출 순서를 확인했고, 256행의 clip·grid·NULL·negative가 모두 일치했다. noise tensor 자체는 저장되지 않아 bitwise 동일성은 추정이다.

## 4. 관측
- 과거와 새 loss는 직접 비교하지 않는다. 같은 grid·noise라도 조건 c가 다르면 다른 문제의 loss다. 새 조건의 step0 loss가 이미 낮다는 사실 자체가 해석의 핵심이다.
- probe (같은 c_good): ψ_bad는 모든 σ에서 BASE보다 나쁘다(+0.03~+0.15, σ=0.05에서 최대). ψ_good은 ±0.005 이내다.
- 영상: NEW_ON↔BASE 4–5.5, NEW_NULL↔NEW_ON 3.3, CFG1↔5 26–27(0–255). 붉은 기는 86 → 12.

## 5. 손상 감소 ≠ 방법 이득
- 손상 감소(A: NEW vs OLD)는 오류를 고친 효과다.
- 방법 이득(B: NEW_ON vs BASE)과 궤적 이득(C: NEW_ON vs NEW_NULL)이 있어야 point adapter가 의미 있다.
- BASE는 기반 모델 자체, NULL은 같은 adapter·앵커 특징이되 중간 궤적을 직선 보간으로 바꾼 입력이다. 이번에는 B와 C 모두 차이가 거의 없다.

## 6. 남은 한계
- σ=0.05의 +0.4% 잔존: 낮은 σ에서는 잔차의 작은 변화도 상대적으로 커진다. 원인은 이번에 진단하지 않았다.
- 256 update·1.27M parameter의 작은 adapter가 BASE에서 거의 움직이지 않은 이유(작은 gradient, 투입 위치, 궤적 표현)는 미확인이다.
- validation 한 영상·한 seed의 개발 비교이며, held-out 일반화 평가가 아니다.

## 이해 확인
- Q: mask64가 같은데 왜 cache를 다시 만들어야 했나? A: 두 RGB branch(32채널)가 마스크의 G/B 채널에 의존하기 때문이다.
- Q: NEW_ON이 OLD_ON보다 훨씬 좋으니 방법이 성공했나? A: 아니다. BASE와 같아진 것일 뿐이다. 이득은 BASE·NULL 대비로 판단한다.
