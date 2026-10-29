# C 연구 — native 편집 앵커와 로컬 영상

C는 외부 native imagegen의 양끝 앵커와 DGX Spark의 로컬 영상 생성을 결합한다. 완전 로컬 시스템으로 부르지 않는다. A/B 환경·장부·실패는 보존하고 B034는 복구하지 않는다.

첫 C001은 공개 강체/비강체 두 사례에서 앵커 외형·원본 행동 상태·중간 영상의 개체/동작/장면을 나누어 본다. SAM은 분석용이며 생성 조건에 들어가지 않는다. 두 전체 RGB 앵커와 caption만 VACE의 실제 양끝 시간 조건에 넣는다.

의뢰: [C001](work_orders/C-001-work-order.md). 다음 모듈은 실제 첫 결과를 사용자와 검토한 뒤 설계한다.

C-002는 C-001 앵커와 ENDPOINT를 그대로 쓰고 기존 SAM source 윤곽을 중간 RGB 조건에 실제 연결한 MOV/STILL 대조다. Source 체형도 함께 들어가는 제한된 구조 표현이며 새로운 체형 전이 신경망이나 순수 motion 분리는 아니다. 실제 네 영상은 완료됐고 차량 TRADE_OFF / 개 COARSE_CONTROL_ONLY로 기본 채택하지 않았다. [의뢰서](work_orders/C002_SAM_LAYOUT_CONDITIONING_WORK_ORDER_KO.md) · [결과](experiments/C-002-sam-layout-conditioning/RESULTS.md).

C-003은 같은 동적 윤곽 안의 source-derived 구조선 시간정보를 묻는 표현 기준선이다. 조건 구현 후 기존 시작 가드에서 중단하여 새 추출·영상0이며 효과 미평가다. 내부 대응·학습·target 체형 전이를 수행한 것으로 확대하지 않는다. [결과](experiments/C-003-internal-structure-conditioning/RESULTS.md).
