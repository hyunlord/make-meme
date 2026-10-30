# C-007 실제 결과 — CFG1에서도 회귀, 낮은 sigma 오차 증가

실제 영상 네 개와 160 one-step + 40 replay forward를 완료했다. **CFG1에서도 ON은 같은 CFG의 BASE보다 명확히 손상됐다.** CFG5에서만 생기는 문제가 아니다. 동시에 진단 cache와 실제 생성의 VACE context가 다름을 발견해, one-step 개선과 rollout 회귀 사이의 원인 연결은 제한한다. 새 학습·수리·재생성은 하지 않았다.

## 요청한 일곱 질문

1. **CFG1 회귀:** 있다. ON1의 t2~28에서 넓은 빨강/자홍/검정 색 번짐, 코끼리 중복 윤곽·투명화, 건물·바위·나무 손상이 BASE1보다 크다. t29~32에도 잔상/붉은 기운이 남는다. negative branch는 실행되지 않았다.
2. **CFG5 추가 효과:** 같은 CFG의 ON5−BASE5도 명확한 회귀다. BASE5가 BASE1보다 장면 색을 잘 보존해 상대적인 간격은 더 커 보이나, ON5 자체가 ON1보다 명확히 더 나쁘다는 독립 정량 근거는 없다. 같은-state 수치상 추가 변화는 있지만 CFG가 지배적 원인이라는 주장은 미입증이다.
3. **sigma/branch/block:** checkpoint128/256 ON/NULL 모두, 두 영상·두 branch에서 .95/.75/.50 loss는 감소하고 .20/.05는 증가했다. elephant positive .20은 .48554→.51750, .05는 1.22805→1.34021; goat는 .57440→.62569, 1.31470→1.43564다. block26 residual/hidden은 전체 약 .159/.127(elephant/goat), 실제 support 약 .260/.253이며 후반 block 비율은 낮은 sigma에서 커진다. 비율 자체를 손상의 증명으로 쓰지 않는다.
4. **one-step과 실제 경로:** 같은-state replay의 Δ5/Δ1 RMS는 1.136~1.332, 두 delta cosine은 .9803~.9914다. 서로 다른 rollout의 latent 차이는 j0=0에서 j49 CFG1 .5090/CFG5 .5352 RMS로 커졌다. 이는 누적 경로 차이이며 같은-state 예측 차이가 아니다. 유한한 norm이 유지되어 NaN·수치 폭발이라고 부르지 않는다. cache context 차이 때문에 순수한 state distribution 변화의 인과효과로 해석할 수 없다.
5. **ON/NULL:** data-noised probe의 비슷한 변화는 공유 adapter 효과를 지지한다. 중간 궤적이 무용하다는 증명은 아니며 이번 NULL full video는 생성하지 않았다.
6. **연산/입력 일치:** native/bypass/zero 60개 비교 max_abs=0, 실제 branch replay 20개 비교 max_abs=0. 네 영상의 논리 RGB/G·초기 noise·실제 VACE context·mask64는 동일했다. 그러나 진단 cache↔생성 VACE context는 RMS .766806/max_abs6.421875로 불일치했다. text context와 mask64는 일치한다. 상세 제한은 아래와 같다.
7. **다음 하나:** 학습 목적·분기 균형·잔차 제약·표현을 지금 바꾸기 전에 **cache와 실제 생성의 VACE 조건 경로 일치 문제를 규명·검증**하는 별도 후속 의뢰가 우선이다. 이번에는 encoder 재실행·수리·학습·scale 탐색을 하지 않았다.

## 입력 불일치의 범위

`INPUT_PARITY.json`은 실제 생성 context를 CPU에서 부모 진단 cache와 비교한 결과다. 생성 네 셀 사이의 context는 정확히 같다. Positive/negative text는 cache와 bit-exact이고 CFG1 negative는 NOT_CALLED다. VACE inactive16채널 RMS1.47018/max6.421875, reactive16채널 RMS1.16898/max2.9765625가 다르며 mask64는 정확히 같다. 두 RGB branch의 시간 latent0은 같고1~8은 다르다.

읽기 전용 확인에서 source/anchor/layout33장 픽셀, VACE positional 인자 순서, 실제 tiled=True 및 tile_size(30,52)/stride(15,26)는 일치했다. 따라서 그 차이를 원인으로 확정하지 않는다. 현재 원인 UNKNOWN이며 추가 encoder 실행으로 가설을 시험하지 않았다. **IMPLEMENTATION_MISMATCH는 cache↔generation 조건 parity에 한정**한다. native/custom 수학이 불일치했다는 뜻은 아니다. 같은-state replay는 저장한 실제 생성 context를 사용하므로 그 내부 비교는 유효하다.

## 실제 영상 검토

source와 네 결과의 전체33장 및 고정0/4/8/12/16/20/24/28/32를 같은 인덱스로 검토했다. Codex 주 실행자와 같은 세션의 독립 읽기 전용 검토자가 정적 시트/PNG를 봤으며 독립 human 평가가 아니다.

| 항목 | BASE1 | ON1 | BASE5 | ON5 |
|---|---|---|---|---|
| 대상/장면 | 식별 가능하나 몸/상단에 색 파편·지붕 손상 | 넓은 붉은 파편·투명화·중복 윤곽 | 상대적으로 장면 색 양호, 검은 다리/작은 잎 모양 artifact | ON1과 비슷한 심한 색 번짐·잔상 |
| 거친 진행 | 우측/멀어짐과 보이는 발 들림 일부 | 큰 진행 남으나 다리 경계 식별 악화 | 큰 진행/18~23 발 들림 일부 | 큰 진행 남으나 정확도 이득 미입증 |
| 양끝 | 대략 원 장면/대상, 완전 일치 아님 | 시작 근접, 종료 붉은 장면/잔상 | 대략 원 장면/대상 | 시작 근접, 종료 붉은 장면/잔상 |

원본의 먼지/물줄기는 실제 가림이며 generated artifact로 세지 않았다. 보이는 뒤쪽 발의 낮은 위치0~12, 들림16~23, 수직에 가까운27~32 변화는 거친 사건으로만 사용했다. 해부학적 좌우·정확 발 접촉 GT는 없고 동작 점수를 만들지 않았다. `temporal=UNVERIFIED`: 파일 decode와 브라우저 재생 기능 확인은 연속 지각 품질 검수가 아니다.

## 판정과 한계

- BRANCH_REGRESSION: 강하게 지지. CFG1과5 각각 ON−BASE 회귀.
- LOW_SIGMA_REGRESSION: 고정 data-noised 상태에서 지지.
- COMMON_ADAPTER_EFFECT: ON/NULL의 비슷한 probe 변화로 지지되는 후보.
- CFG_INTERACTION_SUPPORTED: 제한적 수치 반응은 있지만 주된 시각 회귀 원인이라는 판정은 INCONCLUSIVE. data-noised Δ5/Δ1은1.063~1.274이며 무조건5배가 아니다.
- ROLLOUT_SENSITIVITY_OBSERVED: 경로 이탈은 관측했으나 cache context confound 때문에 teacher-forced→rollout 원인 설명은 제한.
- IMPLEMENTATION_MISMATCH: cache/generation VACE context parity에 한정.

품질 이득·동작 제어 성공은 NO_ESTABLISHED_GAIN이며 adapter/CFG1을 기본 채택하지 않는다. 두 validation 사례·한 영상·한 seed 결과다. C-006과 A/B/C 과거 실패 및 판정은 소급 변경하지 않는다.

## 실행과 보존

4 sampler / 200 step / 300 sampler calls, 별도 one-step160 + replay40 = 총500 core calls. 네 영상 모두33프레임, latent 원자 저장/readback, raw·PNG·MP4를 보존했다. 예비 forward/sampler/VAE 복구·학습·다운로드0. 6개 heavy phase가 기존 guard에서 COMPLETE/정상 종료했으며 다른 작업을 종료하지 않았다. 자세한 비용은 COSTS.json, sampled memory는 NUMERICS.json, 전달 검증은 DELIVERY.json이다.
