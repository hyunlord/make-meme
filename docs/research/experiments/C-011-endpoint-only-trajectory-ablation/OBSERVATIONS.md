# C-011 사후 관측 (사전 사건표: OBSERVATIONS_PRE.md)

## 절차
- 사례마다 다섯 영상을 무작위 순서의 A–E로 가린 9프레임 시트(0/4/…/32)를 먼저 판정했다. 그 다음 key로 라벨을 연결했다. key seed는 20261101이며 비공개 `blind-key.json`에 있다.
- 판정자는 같은 세션의 agent이며, 독립 human 평가가 아니다. 정지 시트만 보았고 연속 재생은 보지 않았다 → **temporal=UNVERIFIED**.

## 라벨 공개 전 기록 (요약)
- **elephant**: A·C가 거의 동일한 쌍. B·D가 거의 동일한 쌍으로 다리에 어두운 덩어리와 녹색 줄이 있다. E가 손상이 가장 적다. 멀어짐과 방향 변화는 다섯 모두 비슷하다.
- **goat**: A·C가 거의 동일한 쌍으로, 머리 회전 시점이 원본에 가장 가깝고 털이 흐리다. B·D가 쌍으로, 옆모습이 일찍 나오고 B는 t16–20에 잔상이 있다. E는 중간이다.

## 라벨
| 사례 | A | B | C | D | E |
|---|---|---|---|---|---|
| elephant | E-NULL | L-BASE | E-ON | L-ON | E-BASE |
| goat | E-ON | L-BASE | E-NULL | L-ON | E-BASE |

두 사례 모두 블라인드에서 짝지어진 것이 정확히 **(E-ON, E-NULL)**과 **(L-BASE, L-ON)**이었다.

## 사건별 판정
### elephant
| 사건 | E-ON vs E-BASE | E-ON vs E-NULL | E-ON vs L-ON | E-BASE vs L-BASE |
|---|---|---|---|---|
| E1 멀어짐 | SIMILAR | SIMILAR | SIMILAR | SIMILAR |
| E2 몸 방향 변화 | SIMILAR | SIMILAR | SIMILAR | SIMILAR |
| E3 다리 들림/내림 (AMBIGUOUS) | UNCERTAIN | SIMILAR | UNCERTAIN | UNCERTAIN |
| E4 먼지 안개 | BETTER (원본처럼 더 유지) | SIMILAR | BETTER | BETTER |
| E5 물줄기 | SIMILAR | SIMILAR | SIMILAR | SIMILAR |
| E6 장면 보존 | SIMILAR | SIMILAR | SIMILAR | SIMILAR |
| 외형 손상 | WORSE (t8 발 쪽 작은 붉은 점, 몸 윤곽 흐림) | SIMILAR | BETTER (L의 다리 어두운 덩어리 없음) | BETTER |

### goat
| 사건 | E-ON vs E-BASE | E-ON vs E-NULL | E-ON vs L-ON | E-BASE vs L-BASE |
|---|---|---|---|---|
| G1 오른쪽 이동 | SIMILAR | SIMILAR | SIMILAR | SIMILAR |
| G2 머리 회전 시점 | BETTER (약함) | SIMILAR | BETTER (약함) | SIMILAR |
| G3 하강 | SIMILAR | SIMILAR | SIMILAR | SIMILAR |
| G4 다리 디딤 (AMBIGUOUS) | UNCERTAIN | SIMILAR | UNCERTAIN | UNCERTAIN |
| G5 털·뿔 외형 | WORSE (흐림) | SIMILAR | WORSE | WORSE |
| G6 장면 | SIMILAR | SIMILAR | SIMILAR | SIMILAR |
| G7 가림 | UNCERTAIN | SIMILAR | UNCERTAIN | UNCERTAIN |

## 보조 수치 (중간 프레임 1–28, 0–255; 정답 지표 아님)
| | elephant | goat |
|---|---|---|
| E-ON ↔ E-NULL 픽셀 차 | 3.8 | 6.8 |
| E-ON ↔ E-BASE | 7.0 | 10.6 |
| L-ON ↔ L-BASE | 5.6 | 7.8 |
| E ↔ L (BASE끼리) | 27.2 | 38.7 |
| source 객체 ROI 오차: E-BASE / E-ON / E-NULL / L-BASE / L-ON | 24.5 / 23.2 / 23.1 / 32.6 / 27.1 | 47.0 / 43.9 / 43.7 / 39.7 / 36.3 |

## 사례별 판정
- **elephant**: **COMMON_ADAPTER_EFFECT_ONLY** (ON ≈ NULL, 둘 다 BASE와 다름). 시스템 측면에서 E 계열은 L의 다리 손상이 없어 원본 객체에 더 가깝다. 다만 point 이득이 없으므로 SYSTEM_GAIN_CANDIDATE 요건은 충족하지 못한다.
- **goat**: **COMMON_ADAPTER_EFFECT_ONLY**. E 계열은 L보다 외형이 흐리고 객체 ROI 오차가 크다(E-ON 43.9 vs L-ON 36.3).
