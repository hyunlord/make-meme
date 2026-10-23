# B-015 실행 전 평가 고정

신규 결과를 보기 전에 고정한다. source f7~23과 기존 전체17장/local0·12·14·16 사건을 유지한다.

- 같은 canvas/timebase의 SOURCE / 실제 Lab reference / CFG_MOV / CFG_STILL / ALG_MOV / ALG_STILL을 모두 보존한다.
- 전신: 착석 대 뒷발 직립, 앞발이 아래 지지인지 가슴 앞에 들어 있는지. 머리 반응만으로 전신 성공 처리하지 않는다.
- 국소: 원본 후반 head-roll 방향·증가 순서·사전 시점과의 대응. 정적 driving에서도 생기는 흔들림이나 큰 변화를 성공으로 세지 않는다.
- 형상: 눈·귀·주둥이·목·사지 손상과 최초 관측 시점을 기록한다. 가림/판독불가를 제외한 좋은 프레임만 평가하지 않는다.
- 정체성: 검은Lab 견종 인상과 실제 반려견 얼굴·체형 수용을 분리한다. 넓은 가슴·굵은 사지와 착석 silhouette의 유지도 동작 성공과 다르다.
- 배경·발 접촉·반사는 별도 채널이며 기존 mask 경계 PARTIAL_UNRESOLVED를 유지한다. animation의 침실 보존 자체는 실패가 아니다.
- 비용: 기존80forward와 ALG88forward의 같은 정의의 S guard/worker/sampler 시간 및 peak 회계를 비교한다. 단일실행 speed benchmark로 일반화하지 않는다.

정성적2×2 표를 사용한다. 보정된 q가 없으므로 interaction 수치·gain·유의성은 계산하지 않는다. 17프레임은 독립17시행이 아니다. 연속 재생의 지각적 검토가 없으면 temporal=UNVERIFIED이며 viewer 기능 검증과 구분한다.

첫 프레임 overwrite/clamp·warp·시간맞춤·보간·SR·얼굴복원·후처리 선별 없이 비교한다. B-014 목표품질 NOT_ESTABLISHED를 ALG_STILL 하나로 성공으로 재분류하지 않는다. 추가 강도·스케줄·seed·학습은 실행하지 않고 현재 pilot을 닫는다.
