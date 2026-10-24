# 권한·자료 부족·분할

등록된 관련 자산12개를 검사했다. 이는12개 독립 source/동물/학습 pair라는 뜻이 아니다. 핵심 원본은 제3자 춤 reference 영상 하나와 실제 Lab 사진 하나이며 나머지는 이미 사용한 crop/RGB/mask 파생물이다. 허용 manifest root 밖 개인 홈이나 다른 계정을 탐색하지 않았다. [익명 해시 요약](ASSET_SUMMARY.json).

| 범위 | 확인 상태 |
|---|---|
| 이번 private CPU decode/검토·case 복사 | 사용자 지시로 허용 |
| 실제 Lab 사진의 개인 연구 reference 사용 | 기존·이번 명시적 범위에서 사용 |
| 제3자 밈 source의 학습/재배포/상업 허가 | 문서상 근거 없음, UNKNOWN/PENDING |
| 실제 Lab 정답 영상 | 제한된 등록 자료에서 미발견 |
| source의 실촬영/합성 진위·생물학적 개체 | UNKNOWN; 파일 존재나 같은 track을 증거로 대신하지 않음 |
| 공공 MotionPair/APT corpus 확보 | NOT_ACQUIRED, 신청/대량 다운로드0 |

공개 GitHub에는 사진·영상·mask·좌표·개인경로·조건cache·weights를 넣지 않는다. 비공개 ZIP에 들어간다는 사실도 재배포 라이선스를 새로 부여하지 않는다.

모든 source case는 source/track/session/derivative group을 공유하며 DEVELOPMENT로 고정한다. 동일 영상의 reference만 바꾸거나 구간을 잘라도 독립 test가 아니다. 실제 Lab 사진도 기존 개발자료다. TRAIN0·VALIDATION0·TEST0이고, 현재 자료로 일반화 평가를 주장하지 않는다.

## 다음 확보 경로 하나 — 실행하지 않음

**사용자가 권한을 확인한 동일 실제 Lab의 자연 동작 영상과 다른 자세 reference를 작은 촬영 세트로 확보한다.** 필요한 것은 같은 Lab의 편안한 앉기·걷기·자연 고개 돌리기 영상 Y, Y 구간 밖/다른 촬영 시점의 reference R, 촬영 session 및 시간축, private training 사용 범위다. 학습 배선 후보에서는 우선 D=Y라는 shortcut을 명시한다. 독립 검증을 원하면 같은 clip 분할 대신 별도 session을 확보한다.

강아지에게 직립 춤을 강요하지 않는다. 자연 동작 자료는 의인화된 춤의 domain gap을 그대로 남기며 true cross-ID pair를 자동 제공하지 않는다. 이후 R/D/Y·mask·pose coverage·권한이 확인되면 그때 제한된 backward/adapter pilot을 별도로 설계한다. 이번에는 촬영 요청 전송·수집·신청·생성·학습을 실행하지 않았다.

왜 바로 LoRA가 아닌가: 현재 target 권한/진위와 실제 Lab Y가 미확보이고, 공식 SCAIL recipe의 adapter 주입/학습 bucket도 별도 검증이 필요하다. 현재14B 추론 메모리로 backward 가능을 보장할 수 없다.
