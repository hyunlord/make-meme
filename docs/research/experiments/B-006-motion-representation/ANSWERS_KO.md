# B-006 해설

[질문](QUESTIONS_KO.md)으로 돌아가기.

1. root와 scale의 관측 근거가 없으면 root-relative q를 계산하지 않는다. 발은 동일 ID의 인접 두 시점이 실제 관측됐을 때만 화면 속도를 계산하며, f0와 f4라면 Δt=4/24초를 써야 한다. 관측되지 않은 중간값 보간은 ground truth가 아니다. 발이 바닥선에 보인다는 사실만으로 깊이·접촉력·체중 분배를 알 수 없어 contact confidence를 별도로 둔다.
2. shape는 bone offsets/길이, motion은 시간에 따른 rotation과 root translation의 일부다. Xj=Xparent+Rparent Rlocal,j bj에서 bj만 scale해도 접촉·관절 한계·skin·원근은 해결되지 않는다. p=π(X)는 여러3D상태를 같은2D로 보낼 수 있어2D길이 변화가 실제 체형 변화라고 단정할 수 없다.
3. VACE의 RGB 입력 타입은 임의 heatmap 의미를 학습했다는 증거가 아니다. SCAIL은 RGB driving encode/token 결합과 그 조건으로 학습하는 공개 경로가 있다. 그래도 우리 동물의 성공은 미검증이다. 실제 모델은 flash_attention을 직접 부르므로 다른 wrapper의 SDPA fallback을 지나지 않고 현재 FA import 부재가 남는다. 또한 모든 input frames를 읽고 output16fps로 저장하는 기본값은24fps 원본의 움직임 속도를 바꾼다. 시간축 보존을 별도 기록해야 한다.
