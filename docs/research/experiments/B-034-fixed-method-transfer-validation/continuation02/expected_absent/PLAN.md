# B-034 CONTINUATION_02 — 한정 부재 기대 정책

시작 HEAD `6f31d8de2c19b3a363c960110e93d3fa412b6a46`의 로컬/원격 일치를 확인했다. 사용자의 [이번 지시](WORK_ORDER_KO.md)는 관리자 inactive/stopped 증명을 요구하던 이전 정책을 이번 잔여 attempt에 한해 명시적으로 대체한다. 기존 UNKNOWN/BLOCKED·실패 예산은 그대로다.

시작2026-10-27T16:13:44Z(KST10월28일01:13:44), GPU 작업 종료 목표17:28:44Z, 전체 hard deadline17:43:44Z. 작은 정책 구현·검사 목표20분이며 마지막15분은 보존·전달에 남긴다.

## 변경 범위와 증명 수준

정책 `OPTIONAL_EXPECTED_ABSENT`, 관측 상태 `EXPECTED_ABSENT_OBSERVED`를 새 attempt 전용 설정으로 고정한다. 이는 승인된 부재 기대와 현재 흔적 부재의 관측이며, 과거 정상 종료·미래 자동 시작 부재·호스트 강제 독점의 증명이 아니다. 기존 allowlist와 수동 launcher는 변경하지 않는다. 관리자 검색·새 관리자 설치·외부 서비스 조작은 하지 않는다.

실제 worker preflight와 supervisor가 같은 정책을 읽는다. 알려진 launcher/실행 경로를 기준으로 관련 프로세스·자식·8190 listener·GPU와 중복 연구 worker를 확인한다. 명시적 정책 승인 및 서비스/listener 부재가 모두 있을 때만 정확한 connection refused를 예외로 허용한다. queue는 UNAVAILABLE/counts=null이며 다른 endpoint 오류·관측 실패·권한 부족은 차단한다.

STEP과 decode 시작 직전 약2초 간격3표본에서 서비스/listener/외부GPU/중복worker 부재, MemAvailable≥72GiB, swap사용0과 정상 관측을 요구한다. 실행 중24GiB headroom/swap0/자체 신원 감시를 유지한다. 서비스 재등장·외부 GPU 등 위반에는 자체 worker만 중단한다. 기존 생애주기/정상 종료 검증을 재사용하며 단계 사이 fresh safety를 적용한다. 비차단 잠금은 이번 연구 중복만 막고 전역 GPU 예약이라고 부르지 않는다.

## 검사 및 실행

신규 정책의 정상 부재 허용, service/listener 존재 차단, 외부GPU 차단, 관측오류 차단, 실행중재등장 차단, 승인없음차단을 CPU에서 검사한다. 기존 loader bootstrap과 B007E_LOADER_REPORT 공통 초기화를 유지한다. 기존24검사를 별도 감사 프로젝트로 반복하지 않는다. 코드/실제설정/입력해시를 고정 commit한 뒤 실제 안전 조건이 통과하면 STEP→최종latent원자저장/검증→자체종료/메모리회복→decode까지 진행한다.

미사용CONT02 heavy/sampler 최대1회,40step·80forward·constraint40회, 해당decode 최대1회다. 실패포함·재시도0. BASE/CONTROL재생성/재decode·source/referenceencoder·이미지·학습·설치·다운로드0. B033clean_constraint·모델·입력·noise/RNG/scheduler·E/M/crop·정밀도·attention·prompt는 그대로다. 896×512·17프레임·source_fps=null·preview24fps·timebase_assumed=true다.

## 평가와 종료

기존BASE/FINAL_ONLY/신규STEP의raw와동일RGB_POST를전체17장/local0/8/16/고정crop으로본다. 클래식target의노출바퀴·긴차체·열린상부, SUV회귀, 접근동작, 보호장면, 경계·접촉·그림자를구분한다. BASE부터없던target에non-regressionPASS를주지않는다. 배경만개선되면보호장면PARTIAL과결합FAIL을함께기록한다. 실제연속시청없으면temporalUNVERIFIED다. 비강체실패는보존한다.

compact는입력/비교영상/작은시트/뷰어/문서,full은신규STEPraw/latent와수치근거다. 기존큰raw/과거ZIP중복없음. Spark/MacCRC·payloadhash·실제추출·전송동일성을검증한다. 공개에는개인경로/PID/전체명령/조건tensor/weights없음. 이번비교뒤종료하며추가실험을예약하지않는다.
