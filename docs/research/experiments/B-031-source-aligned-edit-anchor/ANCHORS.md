# B-031 앵커 6개: 기술 완료와 정적 적합성 분리

6개 모두 실제40step·80forward로 PNG와 최종 packed latent를 저장했다. raw 배열은512×896×3이며 finite 검사가 통과했다. 이 기술 완료는 source 자세 유지나 영상 전이 성공이 아니다.

아래 표는 실제 source3장·target6장·A0 6장을 연 parent 및 별도 agent의 정적 검토를 종합한 것이다. 인간 독립 ground truth 또는 개인 신원 인증이 아니며, 일부 agent는 parent의 초기 요약을 받았으므로 blind 검토라고 부르지 않는다. 세부 판독 원문은 비공개 패키지 review/에 보존한다.

| Case | 외형 | Source 자세·위치·방향 | 형태·중복 | 보호 장면 | R1 영상 적합성 |
|---|---|---|---|---|---|
| animal_R1 | PARTIAL: 검은 장모 target 실루엣, 단순 source recolor는 아님; 세부 개체 일치는 불명확 | FAIL: 낮고 수평으로 누운/웅크린 몸과 오른쪽 옆얼굴. Source의 높은 꼬리·들린 몸통·걸음/앞발 배치가 사라짐 | PARTIAL/UNCERTAIN: 몸 하단의 밝은 틈·녹색 fringe, 세부 다리 구조 불명확; 이중 개체는 보이지 않음 | PARTIAL: 울타리·관목·마른 풀의 큰 배치는 유지, 새 개체 주변 경계 흔적 | ANCHOR_UNSUITABLE |
| animal_R2 | PARTIAL: 검은 털·옅은 주둥이/가슴/다리 표시 반영, 원래 옅은 개 제거 | PARTIAL: 높은 몸통과 우향은 있으나 머리가 더 높고 옆얼굴이며 앞발을 크게 굽혀 들어 source의 낮춘 머리·앞발 배치와 다름 | UNCERTAIN: 얼굴/목의 옅은 고리 같은 형태, 굽힌 앞발·접촉 불확실; 중복 개체는 없음 | PARTIAL: 울타리·관목·마른 풀의 큰 배치 유지, 세밀한 보호영역 동일성 미판정 | NOT_SELECTED_R2 |
| human_R1 | PARTIAL: 흰 블라우스·분홍 이중 테두리 넓은 치마·땋은 머리 명확히 반영; 실제 신원 판정 안 함 | FAIL: 등/왼쪽을 보며 팔을 왼쪽으로 뻗은 target 자세. Source의 앞쪽 얼굴·머리 뒤 팔/허리 팔·앞으로 교차한 발 배치 소실 | PARTIAL/UNCERTAIN: 큰 이중 인물은 없으나 손과 치마에 가린 다리 불확실 | PARTIAL: 관객·짚더미·안뜰의 큰 배치 유지, 생성으로 바뀐 세부는 완전 보존 주장 안 함 | ANCHOR_UNSUITABLE |
| human_R2 | PARTIAL: 흰/분홍 의상과 이중 치마 테두리 반영; 얼굴 흐림으로 세부 불확실 | PARTIAL/FAIL: 정면 몸·허리 손·앞발은 일부 source와 대응하나 들린 팔은 머리 뒤가 아닌 좌상방으로 뻗고 치마가 앞쪽으로 부풀어 들림 | PARTIAL: 얼굴 번짐, 비대칭 어깨/상의, 손과 가린 다리 불확실; 중복 인물은 없음 | PARTIAL: 관객·안뜰·짚더미 큰 배치 유지 | NOT_SELECTED_R2 |
| vehicle_R1 | 정적 적합: 은색 높은 cabin·큰 창·roof rail·세로 후미등·차체/바퀴 비율 반영, 단순 recolor 이상 | 정적 적합: target의 좌향을 복사하지 않고 source처럼 우향 측면, 중앙 하단 위치 유지 | 정적 적합: 두 가시 바퀴와 차체가 대체로 일관되고 큰 이중 차량·형태 붕괴 없음 | PARTIAL: 건물·기념물·난간·타 차량·노면 큰 배치 보존; 세부 표지/문자/질감 정확성 미입증 | SUITABLE_FOR_VIDEO |
| vehicle_R2 | 정적 적합: 밝은 높은 차체·큰 창·roof rail·세로 후미등 반영, source와 다른 차체 | PARTIAL/정적 적합: 우향과 중앙 하단 배치 유지, source보다 후면이 조금 더 보이는 시점 차이 | 정적 적합: 큰 차체 손상·중복 차량은 보이지 않음; 밝은 바퀴 디테일은 target과 정확 일치 주장 안 함 | PARTIAL: 도로·기념물·건물·타 차량의 큰 배치 보존, 세부 질감/문자 미입증 | NOT_SELECTED_R2 |


사전 R1 선택을 그대로 유지한다. Animal/human R1은 ANCHOR_UNSUITABLE이므로 영상 NOT_RUN이며 R2로 대체하지 않는다. Vehicle R1만 조건부 영상 대상이다. Vehicle 영상의 실제 결과는 RESULTS/STAGES에서 별도로 판정한다. 정지 이미지의 외형·방향이 양호하다는 사실만으로 motion 또는 temporal PASS를 부여하지 않는다.

## 실제 이미지 계산 비용

| Case | Pipeline 초 | Step | Forward | Raw finite |
|---|---:|---:|---:|---|
| animal_R1 | 389.980 | 40 | 80 | PASS |
| animal_R2 | 382.750 | 40 | 80 | PASS |
| human_R1 | 383.084 | 40 | 80 | PASS |
| human_R2 | 381.918 | 40 | 80 | PASS |
| vehicle_R1 | 379.340 | 40 | 80 | PASS |
| vehicle_R2 | 387.200 | 40 | 80 | PASS |

이미지 pipeline 호출 합계2304.272초, worker wall2598.925초다. 로딩·전송·마스크·영상 단계를 포함한 전체 비용은 COSTS를 따른다. 이 여섯 입력은 개발 패널이며 성공률·미사용 일반화 benchmark로 해석하지 않는다.

## 실제 검토 PNG 해시

| A0 | SHA256 |
|---|---|
| animal_R1 | `aee4cfcd2cc8397198354b23ceb96297dabcbfac1164abc56379c89e75257ad1` |
| animal_R2 | `0d902509df66b3934ac88779a123521e14c0295a9ee1bcfb47a79acff4906801` |
| human_R1 | `1c70d50f1ca063f079a345846f4c057c7e7a657ec4ebf4c7197706ed77f5cb34` |
| human_R2 | `10ca8cf01432d158db6333eb581b1816e628eb8fdf98ab40f24b092d000f2ddb` |
| vehicle_R1 | `f413bf6a86e02ade3ba0d8d0fce46c860b362860ae2afe28528307926c85d90f` |
| vehicle_R2 | `42ae5c79fea43ea5fdc11a3b4996dabd655aad8f4f6e25ebe56382d09d9933e1` |
