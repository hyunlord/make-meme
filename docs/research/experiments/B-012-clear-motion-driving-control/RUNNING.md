# B-012 실행 기록

상태 RUNNING / 실제 P·PROBE·S·D NOT_RUN. 시작2026-10-23 13:19 UTC, 원격 HEAD `aea64a71baf75db31a4aa4b9240ae4de8ad44545`. 총 deadline17:19 UTC, worker는17:10 UTC를 보수적 종료 시각으로 사용한다. 앞선 연결 실패 시도는 파일 읽기 응답을 확보하지 못한 도구 장애이며 sampler사용0이다. B-010 사용0·B-011 사용1 기록을 보존한다.

1. IN_PROGRESS: 원본 실제 파일/fps/hash 확인·최대3개17프레임 후보의 source-only 검토. 선정 deadline14:04 UTC(45분). 조건을 만족한 후보 중 가장 이른 구간과 사건을 생성 전에 고정한다.
2. PENDING: 입력 준비·MOV/STILL RGB와mask 모두 동적/정적 대응·공통reference/text·최소 실행 코드와4변경/12보존 계약·CPU fixture·사전 공개 고정. 새 mask가 필요하면 CPU 국소 준비 최대30분.
3. PENDING: MOV P1→STILL P1→실제 조건pair 검사 후, 각 PROBE/S/D를 순차 실행. 각단계1회·전체sampler2회·실패포함·재시도0.
4. PENDING: 전체17장 SOURCE/STATIC COPY/MOV/STILL, 사전 상대 사건·coverage·불확실성·실측·한국어 해설.
5. PENDING: RESULTS/HISTORY/ROADMAP·재현 commit/push/원격 SHA와 비공개 ZIP·양호스트 무결성.

기존 tiny CUDA/anchor/mixed loader/FlashAttention/조건-샘플링-decode 분리·72GiB시작/24GiB실행 headroom·swap0·타 서비스 보호를 유지한다. 새 모델·다운로드·학습·LoRA·imagegen·외부생성0. 첫 결과의 품질만으로 STILL을 생략하지 않으며 입력·자원·안전 실패는 후속 중단 사유다. 동일seed만이 아닌 실제noise/RNG를 비교한다. 현재 결과·품질 미실행이며 실제 연속 재생을 관찰하지 못하면 temporal UNVERIFIED다.
