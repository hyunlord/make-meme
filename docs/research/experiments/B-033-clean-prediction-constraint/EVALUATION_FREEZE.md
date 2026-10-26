# B-033 생성 전 관측 기준

B032 `details.jpg`를 다시 열어 SOURCE/B031RAW/FIXED/MASK의 local0/8/16을 확인했다. MASK에는 뒤쪽 바퀴 아래 적색/흰색/검정 작은 조각이 남고 후반 더 드러난다. 이 조각의 합성 core 포함 여부와 실제 target 본체 포함 여부는 다른 주장이다. Hempty/최대약15px 수동윤곽불확실성을 유지한다.

기존 crop을 바꾸지 않는다 (exclusive xyxy,896×512 좌표):
- vehicle/body `(160,170,760,430)`
- wheel/contact `(80,340,760,465)`
- graphic/road `(0,395,430,512)`

전체17장과 local0/8/16에 동일좌표를 사용한다. Crop은 관측창이며 정답 오염mask가 아니다. 새 결과를 보고 좌표/마스크를 조정하지 않는다.

주 비교는 STEP+동일RGBPOST vs FINALONLY+동일RGBPOST vs B032MASK다. Raw끼리 STEPvsFINALONLY도 본다. 원거리배경복사는보조이며 기술식의성질이다.

| 판정축 | 생성 전 관측 대상 | 실패/불확실 처리 |
|---|---|---|
| 대상외형 | 높은 밝은 차체, 큰창, 루프, 세로후미등 | source의낮은짙은Mini회귀는FAIL |
| 거친동작 | 우향이동과후면노출증가순서 | 큰흔들림만으로성공하지않음 |
| 오염 | 뒤바퀴아래조각/하단strip의크기·색·지속 | 완전제거와부분감소구분,임의점수없음 |
| 경계/접촉 | halo/색차/이중잔상/잘림/그림자/부유 | 가려진접촉은UNCERTAIN |
| 지도적합성 | 새target의frozen support밖이동 | MASK_INCOMPATIBLE위험,재주석없음 |
| VAE오차 | source decode의차체경계·도로질감 | 재구성자체오차를방법실패와분리 |
| 비용 | encode/decode/sampler/수동support포함 | FINALONLY와동급이면추가비용미정당화 |

직접연속시청주체가없으면temporalUNVERIFIED. 정적agent판독은독립humanGT가아니다. 한case/seed/output-assistedmask의개발진단이며미사용일반화아니다. 결과가나쁘면이설정미채택;새실험자동추가0.

원본 계보는 B027의 DAVIS `car-roundabout` track1, f30..46이다. Target원천은 `car-shadow` track1 R1f0이고 B031은 그사진과source첫프레임으로 만든 A0/R_star를 사용한다. B033은 기존R_star를 그대로 재사용하며 개인Lab영상과섞지않는다. 공개GT는mask-given이며자동추적성공이아니다.
