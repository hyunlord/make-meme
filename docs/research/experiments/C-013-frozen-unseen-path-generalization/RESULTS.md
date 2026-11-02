# C-013 결과: BLOCKED_SAFETY, 신규 영상 0/5

**실제 생성 전에 기존 guard가 중단했다. 모델 능력은 미판정이다.**

## 요청한 일곱 질문
1. I25/I50/I75 가운데가 y=96/120/144로 움직였는가? **INCONCLUSIVE**. 요청 좌표만 검증됐고 실제 출력이 없다.
2. 새 요청을 따랐는가, A/B에 붙었는가? **INCONCLUSIVE**. E_req/E_mem은 null이다.
3. S의 아래→중앙→위 순서를 따랐는가? **INCONCLUSIVE**.
4. 단일 공·무늬·형태·배경이 유지됐는가? **NOT_EVALUATED**.
5. seed2 BASE에도 배경 손상이 나타나는가? **BACKGROUND_CAUSE_INCONCLUSIVE**. BASE_S2가 생성되지 않았다.
6. ON은 BASE보다 무엇을 추가로 바꾸는가? **INCONCLUSIVE**. 부모 ON2 관측만으로 원인을 가르지 않는다.
7. 확인한 일반화 범위와 다음 요소 하나? **새 일반화 근거 없음**. 다음 실행의 선행조건 하나는 기존 시작 메모리 guard를 만족하는 환경이다. 이번 세션은 이를 만들기 위해 서비스를 변경·프로세스 종료·swap 해제·재부팅하거나 자동 재시도하지 않았다. 모델·loss·표현 변경을 제안할 결과가 없다.

## 실제 중단과 계산량
첫 BASE_S2의 기존 guarded CPU admission에서 START_SWAP_BUDGET:
- 전역 swap 247,345,152 bytes (235.9MiB), 기존 시작 한도 67,108,864 bytes (64MiB).
- available 121,253,744,640 bytes. GPU 작업 목록은 비어 있었다. 여유 메모리가 많아도 swap 시작 한도는 별도 조건이다.
- 원인을 특정 다른 프로세스 탓으로 추정하지 않았다. queue는 EXPECTED_ABSENT_OBSERVED / UNAVAILABLE, queue_counts=null이다.
- runner exit2. worker 생성 전 중단이므로 supervisor-result.json은 생성되지 않았다. start-samples.json과 memory-budget-state.json 원본을 비공개로 보존했다.
- 모델 적재0, heavy 시작0, sampler0/6, step0, model_fn0, VAE0, 학습/backward0, 설치/다운로드0, 재시도0.
- 네 후속 셀은 시작하지 않았다. 다섯 셀 모두 NOT_RUN; 기술적 중단을 모델 실패로 계산하지 않는다.

## 확보한 것과 미검증
- 사전 PLAN/원본 PATHS/실행 계약을 c515cc8로 먼저 commit/push했다.
- 부모 full SHA와 연구 branch 원격 일치, 기존 C-013 부재 확인. Spark checkpoint2048 SHA는 기대값과 일치했다.
- 네 sidecar의 중간 positions만 변경. 양끝 tensor와 patches/anchor_valid/visible/valid/box_wh exact readback, 부모 point exclusions 유지. CPU 준비에서 CUDA 미초기화 확인.
- 동봉 좌표 전33프레임 공식 일치, 기하 scorer의 정확한 경로 통과/A·B 거부/핵심 missing·duplicate 거부/비표본 missing 품질 거부 확인.
- renderer/template fixture는 NOT_RUN. Mac 기본 Python에 cv2가 없고 설치하지 않았으며, Spark guard 중단 뒤 그 검사를 우회하지 않았다.
- scorer의 실제영상 평가 분기는 미검증 WIP다. lint/typecheck 도구도 로컬 PATH에 없어 NOT_RUN. Python syntax 검사는 통과했다.
- 신규 영상·영상 viewer·경로 측정 그래프는 없다. 전달 ZIP은 **중단 기록 패키지**, 영상 검토 완료 패키지가 아니다.
- temporal=UNVERIFIED; 정적 생성 이미지 검토/연속 지각 검토/독립 human 평가 모두 수행하지 않았다.

C-012의 SEED_SENSITIVE_CAPABILITY 판정은 그대로 보존한다. 본 결과가 이를 부정하거나 일반화로 확장하지 않는다.
