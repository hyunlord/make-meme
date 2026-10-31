# C-011 RESULTS — 동적 윤곽을 빼도 점 궤적은 쓰이지 않았다 (2026-11-01)

## 한 줄
VACE 중간 조건을 회색으로 바꾸고 같은 step000·schedule로 256회 다시 학습했다. 그래도 **E-ON과 E-NULL은 거의 같은 영상**이 나왔다(블라인드에서 두 사례 모두 쌍으로 묶임). 수치에서도 point 고유 이득이 없다.

판정:
- point 기여: **NO_PROBE_GAIN**, 영상은 두 사례 모두 **COMMON_ADAPTER_EFFECT_ONLY**
- 전체: **NO_ESTABLISHED_GAIN**

현재 adapter·자료·256회 예산에서는 동적 윤곽 제거만으로 유용한 point 제어가 생기지 않았다.

## 1. 같은 E 안에서 ON이 BASE·NULL보다 원본 동작을 더 따랐나 — 아니다
- **elephant**: E-ON ≈ E-NULL(픽셀 차 3.8, 객체 ROI 오차 23.2 vs 23.1). E-BASE 대비 큰 움직임(멀어짐·방향)은 같다. 먼지 안개는 원본처럼 더 유지하지만, 발 쪽 작은 붉은 점과 흐린 윤곽이 생긴다.
- **goat**: E-ON ≈ E-NULL(6.8, 43.9 vs 43.7). E-BASE 대비 머리 회전 시점이 약간 원본에 가깝지만 털 외형이 흐려졌고, NULL도 똑같이 그렇다.
- BASE와 달라진 부분은 ON/NULL 공통이다 → adapter 공통 효과다.

## 2. ON/NULL은 단지 달라진 것인가, 정답 방향인가
Δ_E = L_ON − L_NULL (W 가중):
- 중심 validation σ0.50: elephant +0.0002, goat +0.0006 → 둘 다 ON이 NULL보다 나쁘다.
- 보조 10셀 중 Δ_E < 0은 2셀(bear σ0.05 −0.0008, dance-twirl σ0.05 −0.0057)뿐이다.
- ON−NULL 변화의 오차 방향 cos는 −0.15 ~ +0.07이다.
- Δ_L(같은 probe, L 계열)은 C-010과 같은 부호 패턴이다. I = Δ_E − Δ_L은 |I| ≤ 0.0076으로 거의 0이다(dance-twirl σ0.95만 +0.0076, E에서 오히려 더 나쁨).
- ON−NULL 출력 차이의 크기도 E와 L이 비슷하다(BASE RMS의 0.65–4.7%).
- 윤곽을 빼도 궤적이 맡는 몫은 늘지 않았다.

## 3. E-ON은 기존 L 시스템보다 좋은가 — 사례마다 다르다
- **elephant**: E 계열이 L보다 원본 객체에 가깝다(ROI 23 vs 27–33). C-007/009 L 영상의 다리 어두운 덩어리·녹색 줄이 E에서는 사라진다. 이것은 **윤곽 제거 자체(E-BASE)의 효과**이며 point 덕분이 아니다.
- **goat**: L이 더 낫다(ROI 36–40 vs 44–47). E는 털·형태가 흐려진다.
- 조건 제거로 잃는 것은 사례에 따라 외형 선명도다(goat). elephant에서는 L의 윤곽이 오히려 다리 손상의 원인일 가능성이 관측된다(가설).

## 4. 계약 동일성 — 확인
- E cache 10개:
  - 중간 31장의 모든 채널이 127이고, 앵커는 source 0/32와 byte 동일하다.
  - 흰 마스크 3채널 검사를 통과했다. 정규화 후 회색 값은 −0.0039(bf16)이며 0이 아니다.
  - L 대비 inactive는 exact, mask64는 exact, reactive는 달라짐(rms ≈ 2.0)을 확인했다.
  - vace_context 외 key는 byte 동일하다.
- live parity: elephant·goat에서 생성 준비 경로의 독립 인코딩이 E cache와 exact(max_abs 0)였다.
- 영상 10개: 첫 model_fn의 context sha가 각 계열 cache와 일치하고, 초기 noise sha도 모두 같다. CFG5에서 model_fn 100회, step 50.
- 학습: step000의 adapter·optimizer·CPU/CUDA RNG·generator·order·cursor가 exact이고, 256행 schedule이 일치한다(noise bitwise는 추정). 256/256 완료, reload 예측 차이 0, backbone 불변.

## 5. Δ, σ, gradient가 지지하는 것과 제한하는 것
- 학습 update의 σ 분포: 55%가 σ≥0.8, 83%가 σ≥0.5(shift5 grid, 실측).
- 높은 σ(0.95)에서 E-BASE의 손실은 L-BASE보다 크다(예: elephant 0.118 vs 0.093). 윤곽이 큰 잡음 구간에서 구조를 주던 몫이 사라진 것이다. 그런데도 ON은 NULL보다 낫지 않다.
- 중간·낮은 σ에서는 E-BASE ≈ L-BASE다(noisy state가 구조를 이미 가짐).
- gradient(validation σ0.5/0.05):
  - ON/NULL motion-context cos가 L 0.991–0.996, E 0.987–0.997로 같다.
  - ON−NULL gradient 크기 비율도 0.08–0.16으로 같다.
  - E에서도 학습 신호가 궤적을 구별하지 않는다는 설명과 일치한다. 다만 cos 자체를 판정 근거로 쓰지는 않았다.
- C-010의 "조건 중복" 가설은 이번 절차에서 **지지되지 않았다**. 단, 중복 외의 모든 설명(학습 난이도·예산·prior 상호작용)을 분리한 것은 아니다.

## 6. 회귀
- E-ON의 앵커 충실도는 BASE와 같다.
- 외형: goat의 털이 흐려지고, elephant의 t8 발 쪽에 작은 붉은 점이 생겼다. NULL에도 같이 있다.
- 장면 보존은 동일하다.
- 시간 품질은 연속 시청을 하지 않았으므로 UNVERIFIED다.

## 7. 비용
- encode: cache 20 + parity 4 + 영상 16 = 40(상한 40).
- 학습 256 update, active 약 258초(heavy stage 267초).
- validation 18, 진단 5, probe 72, gradient 16 + VJP 16, sampler 8 (scheduler step 400, model_fn 800, 각 약 90초), decode 8.
- 기계 복구 0, 다운로드 0.
- 수동 검토: agent 블라인드 시트 1회, 시간은 측정하지 않았다.

## 8. 다음에 바꿀 요소 하나 (제안, 미실행)
**목적함수: 궤적 일치 감독 항 추가.** E 조건, adapter, 학습량은 그대로 둔다. FM loss에 다음 항을 더한다: 예측 clean latent `x̂0 = z_σ − σ·v`에서 ON track 위치 q_t의 latent patch가 같은 점의 endpoint patch와 일치하도록 하는 보조 항. 같은 표면점은 시간이 지나도 같은 외형을 유지한다는 조건이며, gate가 있는 프레임만 쓴다.
- **근거**:
  - 이번 E 학습에서 update의 55%가 이미 σ ≥ 0.8 구간이었다(실측 0.547).
  - 그런데도 윤곽을 뺀 상태에서 ON−NULL 변화는 FM 오차와 정렬되지 않았고(Δ_E > 0 다수), ON/NULL 학습 gradient도 같았다.
  - 따라서 σ 분포나 조건 중복보다 **FM 자기재현 목적 자체가 궤적을 구별할 압력을 주지 않는다**는 설명이 남는다. (처음에는 학습 σ 비중을 후보로 적었으나, 실제 분포를 확인한 뒤 철회했다.)
- **반증**: 같은 256회 예산에서 아래 둘이 모두 나오면, 이 주입 경로(마지막 네 block 앞 residual)로는 궤적 제어를 얻기 어렵다고 보고 VACE 입력 쪽 궤적 표현 같은 다른 경로를 검토한다.
  1. 보조 항 자체는 줄어든다.
  2. 블라인드 영상에서 ON과 NULL이 다시 쌍으로 묶이고, 사전 사건(elephant E1–E3, goat G1–G3)에서 ON이 NULL보다 BETTER인 사건이 없다.
- 이번에 하지 않은 것: 학습량·σ 분포·residual scale·좌표 표현·조건 dropout 변경.

## 한계
validation 두 사례(개발에 반복 사용)와 seed 하나만 썼다. 사람 연속 시청은 없다. elephant의 일부 track이 몸 밖에 있다. 이번 결과를 test 일반화나 통계적 결론으로 확장하지 않는다.
