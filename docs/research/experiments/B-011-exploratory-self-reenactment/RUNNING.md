# B-011 실행 기록

상태 RUNNING / GPU NOT_RUN. 시작 2026-10-23 06:21 UTC, 원격 HEAD `dfa23d6ffeb49a8471eb3487085739f35e82d646`. 전체 deadline 09:21 UTC, 실행 worker는 보수적으로09:15 UTC를 사용한다. B-010 DIAGNOSTIC_INSUFFICIENT와 사용0 기록을 보존한다.

1. COMPLETED (06:26:42 UTC; 최대342.052초): 최대30분 source-only 관측 재검토 및 A(시간 변화)/B(부위 상대 운동) 평가 범위 사전 고정.
2. COMPLETED (CPU8fixture·540hash·독립 검토 PASS): 동일 입력·prompt·최소 runtime/config 변경·fixture·해시 공개 고정.
3. IN_PROGRESS (사전 커밋 후 P부터 순차 실행): 선행 입력/안전 검사 뒤 P→조건7변경/9보존→PROBE→S→D, 각최대1회·재시도0.
4. PENDING: 전체17장 source/STATIC COPY/출력 비교, 평가 불확실성·실측·한국어 해설.
5. PENDING: 결과·HISTORY·ROADMAP·재현 공개 동기화 및 비공개 ZIP·양호스트 무결성 검증.

19.42px는 전파된 보수적 반경이며 실측 tracker RMSE/표준편차/신뢰구간이 아니다. 확대 입력은 새 고해상도 정보가 아니다. B의 정량 불확실성만으로 A의 탐색 생성 전체를 차단하지 않는다. 입력 정합/실제 변화/안전 계약은 계속 검사한다. 완전 정적·입력 불일치·가드 위반은 중단 사유다.

기존72GiB 시작/24GiB 실행 headroom·swap0·서비스 보호, tiny CUDA/anchor/mixed loader/FlashAttention/단계분리 유지. 신규 모델·학습·다운로드·imagegen·외부생성0. 추가 구간·seed·low-pass·업스케일0. 연속 재생 품질은 실제 관측 전 UNVERIFIED다.

## P 종료 및 실제 조건 비교

P1 PASS, guard121.123초, service_exit/returncode0/PID0. 새 cache SHA `2af5acb5e3835e1e3f23609dcf83a326980818075aff3c11c36cbd5a095583cb`. reference/text7leaf 변경·나머지9leaf 비트 동일, source noise `[16,5,112,64]` FP32 hash `9d26386e01a5dce6b0dc21e3df26aab79b65a4403e11b6c8fc5a71873dd3c950`. 새 positive text `[27,4096]`, 기존 `[44,4096]`. 입력 기대 변경 집합 검사는 유지됐고 실제 값으로 통과했다. PROBE/S/D는 각 선행 성공과 자원 회복을 확인하며 진행한다.

PROBE1 PASS,6.055초, 정상 종료/PID0 확인. 별도 fresh S1이 시작됐으며 tiny CUDA 연산 뒤 기존 staged loader로 적재 중이다. 실제 출력은 아직 NOT_AVAILABLE, D·품질 평가는 NOT_RUN이다.
