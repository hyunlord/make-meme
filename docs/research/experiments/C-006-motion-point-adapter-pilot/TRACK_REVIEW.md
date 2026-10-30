# C-006 tracker 정적 검토

고정 인덱스 0/4/8/12/16/20/24/28/32의 overlay를 12개 클립 모두 검토했다. 의심 지점은 무손실 source PNG 위에 raw NPZ 좌표와 번호를 다시 표시해 확대 확인했다. 생성 결과를 보기 전의 입력 품질 검토이며, 같은 Codex 계열 에이전트의 정적 관측이다. 독립 human 평가나 연속 재생 검수가 아니므로 temporal=UNVERIFIED다.

CoTracker의 visible=true가 객체 위의 정확한 표면 대응을 보장하지 않는다. 명확히 배경으로 벗어난 ID만 전체 궤적 제외 대상으로 고정했다. 가림, 낮은 confidence 추정, mask 밖이라는 사실만으로 제외하지 않았다. 공식 API의 bool visibility를 연속 confidence로 바꾸지 않았다.

| 클립 | 전체 궤적 제외 ID | 유지한 불확실성 |
|---|---|---|
| bear | 없음 | 발·바위 경계와 가림은 정확 대응 미확인 |
| blackswan | 없음 | 물결/몸통 경계와 목 가림 |
| bmx-bumps | 없음 | 바퀴·스포크의 동일 표면 대응 미확인 |
| boat | 없음 | 가느다란 돛대 경계 |
| bus | 없음 | 표지판 가림 및 경계 |
| camel | 없음 | 가려진 발·머리 경계 |
| cows | 없음 | 다리 겹침·발 접촉 |
| dance-twirl | 1, 4 | 대부분 후반 가림; invisible 점을 정답으로 복원하지 않음 |
| elephant | 2, 3, 14 | ID6은 먼지와 발 경계가 모호하여 제외하지 않음 |
| goat | 2, 5, 8, 12 | 가려진 다리의 대응·접촉 미확인 |
| horsejump-low | 없음 | 가려진 다리와 발굽의 표면 대응 미확인 |
| lucia | 3, 6, 7 | ID8 등 invisible 점은 가림만으로 제외하지 않음; ID4는 dress 위 |

## 제외 근거

- lucia ID3: t16 visible=true at (86.5,214.1), pavement/grass well left and below person.
- lucia ID6: t16 visible=true at (81.0,138.6), grass left of person.
- lucia ID7: t16 visible=true at (79.5,174.4), grass left of person.
- dance-twirl ID1: t28 and t32 visible=true on spectators, far right of the dancer.
- dance-twirl ID4: t32 visible=true on spectator area, far right of dancer; t28 invisible alone was not exclusion evidence.
- elephant ID2: t28 visible=true at (126.6,61.2) on tree/foliage above-left of back; t0 was on back boundary.
- elephant ID3: t28 visible=true at (99.8,202.4) on empty ground left of rear foot.
- elephant ID14: t28 visible=true at (111.2,89.1) on foliage left of rump; t0 was on rump boundary.
- goat ID2: t16 and t32 visible=true on hillside to the right of animal; t32 (360.9,144.7).
- goat ID5: t16 and t32 visible=true on rock far below-left of animal; t32 (151.8,227.8).
- goat ID8: t32 visible=true at (336.7,55.8) on hillside clearly above horn tips.
- goat ID12: t16 and t32 visible=true on hillside right of animal; t32 (377.0,120.4).

Lucia의 초기 작은 overlay 판독에서 ID4로 전달된 점은 raw 좌표/확대 원본에서 ID3으로 정정했다. t16 ID4=(166.0,128.2)는 검정 드레스 위이므로 제외하지 않는다.

총 12/192개 궤적을 제외한다. 나머지 ID의 포함은 정확 대응 PASS가 아니라 명확한 배경 이탈 증거가 없다는 뜻이다. raw NPZ는 그대로 보존하며 private point-exclusions.json에 원본 SHA256과 모든 클립의 포함/제외 목록을 남겼다. 후속 입력에서만 이 목록을 전체 시간 및 anchor 적격성에 적용한다. 트래커 재실행·점 재선정·좌표 보정은 0회다.

이 검토는 9개 고정 표본과 의심 원본 확대에 한정된다. 표본 사이의 drift, 얇은 부위, 가려진 관절과 실제 접촉은 UNKNOWN/UNCERTAIN으로 남는다.

## 별도 HEAD_ONLY cross-ID 추적

고정한 얼굴 3점에 대해 공식 tracker를 한 번 호출했다. fixed 0/4/8/12/16/20/24/28/32 overlay에서 코·눈 주변을 따르는 것이 관측되며 명백한 배경 이탈은 없었다. 24번의 source motion blur 때문에 정확한 중심은 불확실하다. 두 끝의 세 점은 모두 visible/valid다. 실제 tracker 끝점과 별도로 고정한 수동 source 끝점의 거리는 416 좌표에서 1.1725 / 1.4698 / 0.8090px였다. 이는 수동 불확실성 약 ±2px 범위의 진단이지 GT 추적 정확도 PASS가 아니다. raw 끝점을 수동 좌표로 덮어쓰지 않았고 재추적·점 추가·제외는 0회다. retarget 이후 양끝 일치는 수식의 속성이므로 이 추적 검토와 구분한다.
