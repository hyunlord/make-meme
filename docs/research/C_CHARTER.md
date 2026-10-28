# C 연구 — native 편집 앵커와 로컬 영상

C는 외부 native imagegen의 양끝 앵커와 DGX Spark의 로컬 영상 생성을 결합한다. 완전 로컬 시스템으로 부르지 않는다. A/B 환경·장부·실패는 보존하고 B034는 복구하지 않는다.

첫 C001은 공개 강체/비강체 두 사례에서 앵커 외형·원본 행동 상태·중간 영상의 개체/동작/장면을 나누어 본다. SAM은 분석용이며 생성 조건에 들어가지 않는다. 두 전체 RGB 앵커와 caption만 VACE의 실제 양끝 시간 조건에 넣는다.

의뢰: [C001](work_orders/C-001-work-order.md). 다음 모듈은 실제 첫 결과를 사용자와 검토한 뒤 설계한다.

C-002는C-001의앵커와ENDPOINT를그대로쓰고,기존SAMsource윤곽을중간RGB조건으로실제연결하는MOV/STILL대조다. source체형도함께들어가는제한된구조표현이며새로운체형전이신경망이나순수motion분리는아니다. [의뢰서](work_orders/C002_SAM_LAYOUT_CONDITIONING_WORK_ORDER_KO.md).
