# C-009 RESULTS — 흰 마스크 cache로 동일 설정 재학습 (2026-10-31)

## 한 줄
C-006/C-007의 붉은 번짐·투명화는 **빨간 마스크 cache로 학습한 결과**였다. 같은 step0·schedule로 흰 마스크 cache에서 다시 학습하자 손상은 사라졌다.
그러나 새 adapter의 출력은 **BASE와 거의 같고**, NULL과도 거의 같다. 판정: **CONDITION_FIX_REDUCES_DAMAGE**, 방법 자체는 **NO_ESTABLISHED_GAIN**.

## 실제 영상 (elephant validation, seed 20261028, Euler50, 416×240×33)
중간 프레임 1–31의 평균 절대 픽셀 차이(0–255)와 붉은 기 (R − mean(G,B)):

| 비교 | 픽셀 차이 | 의미 |
|---|---|---|
| NEW_ON_1 ↔ BASE_1 | 4.0 | 거의 동일 |
| NEW_ON_5 ↔ BASE_5 | 5.5 | 거의 동일 |
| OLD_ON_1 / OLD_ON_5 ↔ BASE | 61.8 / 62.8 | 과거 손상 |
| NEW_NULL_5 ↔ NEW_ON_5 | 3.3 | 중간 궤적 입력의 영향 미미 |
| CFG5 ↔ CFG1 (BASE / NEW_ON) | 27.0 / 26.0 | 참고: CFG 자체 효과가 adapter 효과보다 훨씬 큼 |

붉은 기: SOURCE 8.9, BASE 10.5/11.9, NEW_ON 11.5/12.8, NEW_NULL 12.9, **OLD_ON 86.8/86.0**.
(source 대비 차이는 정답 지표가 아니라 참고값이다. BASE 25.3/30.4, NEW_ON 24.1/29.4, OLD_ON 64/67.)

시트 검토 (고정 프레임 0/4/…/32, 정지 화면, 연속 재생 검수 아님):

| 사건 | A: NEW_ON vs OLD_ON | B: NEW_ON vs BASE | C: NEW_ON vs NEW_NULL (CFG5) |
|---|---|---|---|
| 붉은 파편·투명화·중복 윤곽 | BETTER (소멸) | SIMILAR | SIMILAR |
| 우측·멀어지는 진행 | BETTER | SIMILAR | SIMILAR |
| 다리 들림·내려옴 순서 | UNCERTAIN (OLD는 판독 불가) | SIMILAR | SIMILAR |
| 다리의 어두운 덩어리·녹색 줄 (CFG5) | — | SIMILAR (BASE에도 있음) | SIMILAR |
| 배경 백화·색 줄 (CFG1) | BETTER | SIMILAR (BASE_1에도 있음) | — |
| 먼지/물줄기 가림 재현 | UNCERTAIN | SIMILAR (둘 다 약함) | SIMILAR |
| 건물·바위·나무 보호 | BETTER | SIMILAR | SIMILAR |
| 양끝 일치·종료부 잔상 | BETTER | SIMILAR | SIMILAR |

- D (CFG1 vs CFG5): 변화량은 BASE와 NEW_ON에서 같은 크기(26–27)다. CFG 차이를 adapter 개선으로 볼 근거가 없다.
- temporal=UNVERIFIED. 시트와 decode 가능성만 확인했고 연속 시청은 하지 않았다.

## one-step probe (정상 context, 60 forward)
balanced loss(객체 MSE + 배경 MSE)의 BASE 대비 변화. elephant·goat, positive/negative 범위:

| σ | OLD_ON_256 (빨강 학습) | NEW_ON_256 |
|---|---|---|
| 0.95 | +0.047 ~ +0.057 | −0.002 ~ −0.004 |
| 0.75 | +0.030 ~ +0.043 | ±0.0003 |
| 0.50 | +0.034 ~ +0.040 | ±0.0007 |
| 0.20 | +0.078 ~ +0.085 | +0.0003 ~ +0.0009 |
| 0.05 | +0.140 ~ +0.154 | +0.0045 ~ +0.0052 (≈+0.4%) |

- 낮은 σ 회귀는 과거 대비 약 30배 줄었다. 다만 σ=0.05에서 작은 +방향이 네 셀 모두 일관되게 남아 있다.
- 학습 중 validation loss: 새 조건 step0 0.110→256 0.108 (elephant σ-index200). 과거 빨강 조건 0.918→0.389는 **다른 입력에서의 값이라 차감하지 않는다**.
  흰 context에서는 step0(=BASE와 같은 zero 출력) 손실이 이미 낮았다. 과거 학습의 큰 감소는 대부분 손상된 조건을 보정한 것이었다고 해석한다.

## 질문별 답
1. **cache**: 12+1개 모두 정상화. 11개는 재인코딩(22 encode), elephant·goat는 C-008 white encoding을 sha 확인 후 재사용.
2. **불변**: `vace_context` 외 key·tensor·메타데이터 모두 byte 동일. 초기 adapter·optimizer·CPU/CUDA RNG·generator·order·cursor가 train-v2 step000과 exact.
3. **학습**: 256/256 완료. step·clip·grid·NULL·negative-text 256행 모두 train-v2와 일치.
   noise tensor는 저장되지 않아 bitwise 동일성은 같은 generator·호출 순서에서 추정한 것이다.
4. **낮은 σ 회귀**: 크게 줄었다. 아주 작은 잔존(+0.4%)은 있다.
5. **색 번짐·중복 윤곽**: 사라졌다 (붉은 기 86 → 12).
6. **궤적 추종**: NEW_ON은 BASE·NEW_NULL보다 낫지 않다. 세 영상이 거의 같다. OBSERVED_TRAJECTORY_GAIN 아님.
7. **외형·장면 손상**: 새로 생긴 것은 없다. BASE의 다리 어두운 덩어리(CFG5)와 배경 백화(CFG1)가 그대로 남았다.
8. **다음**: 확장 검증이 아니다. 정상 조건에서 adapter가 거의 아무것도 하지 않는 문제(작은 residual, 256 update, 궤적 신호의 약한 활용)를 먼저 진단하는 것이 맞다.

## 판정
| 계산 | 값 |
|---|---|
| WHITE_MASK_CONTRACT_VERIFIED | ✅ (11 재인코딩마다 3채널·정규화 검사, 회귀 테스트) |
| CACHE_REBUILD_COMPLETE | ✅ 13/13 |
| NONCONTEXT_FIELDS_UNCHANGED | ✅ |
| CACHE_LIVE_PARITY_VERIFIED | ✅ elephant·goat exact, elephant은 C-007 실제 context와도 exact |
| INIT_PARITY_VERIFIED | ✅ |
| TRAIN_SCHEDULE_MATCHED | ✅ (noise bitwise는 추정) |
| TRAIN_COMPLETE_256 | ✅ |
| CHECKPOINT_RELOAD_VERIFIED | ✅ reload 예측 차이 0 |
| MATCHED_GENERATION_COMPLETE | ✅ 신규 3개. 7개 영상 모두 같은 96채널 context·noise·text·RGB/G |

| 품질 | 값 |
|---|---|
| CONDITION_FIX_REDUCES_DAMAGE | ✅ |
| 방법 이득 | NO_ESTABLISHED_GAIN (NEW_ON ≈ BASE ≈ NEW_NULL) |

C-006/C-007의 과거 판정은 그대로 둔다. 그것은 "오류 조건 학습"의 결과이며, 이번 결과는 그 해석을 바꿀 뿐 소급 PASS가 아니다.

## 범위·한계
- validation 개발 사례 하나(elephant), seed 하나다. test 일반화나 논문 성능이 아니다.
- 정확한 관절·좌우·접촉 GT는 없다.
- BASE는 C-007 결과를 재사용했다. 첫 model_fn 입력이 모두 동일함을 확인했으므로 BASE 재생성은 0회다.

## 비용
encode: cache 22 + live parity 4 + 신규 영상 조건 6 = 32. 학습 256 forward/backward + validation 18 + 진단 5. probe DiT forward 60. sampler 3회 (scheduler step 150, model_fn 250). decode는 영상 3. 복구 0. guard 변경 없음, 모든 stage COMPLETE. → [COSTS](COSTS.json)

## 다음 한 가지 (제안, 미실행)
정상 조건 adapter의 기여가 왜 이렇게 작은지 진단한다: residual 크기, ON/NULL 차이가 나는 block 통계, 궤적 신호에 대한 gradient. 구조·목표 변경은 그 결과를 본 뒤 정한다.
