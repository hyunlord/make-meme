# C-013 사전 실행 계획

- 작성 시각: 2026-11-02T05:03:35.220636+00:00
- 상태: PLANNED. 이 commit 전에 신규 과제 분석·GPU 실행 없음.
- 부모: C-012 / 6fba3a00d587bc0f130420e0f5b8c264b5e7a548.
- 연구 branch: docs/c-research-20261028. 로컬/원격 부모 SHA 일치, 연구 worktree clean 확인. 일반 개발 checkout 및 기존 변경 보존.
- 인수: Mac에서 기존 SSH 인증으로 Spark 접근 확인. 부모 task/cache/configs/outputs/code/stages 존재, C-013 기존 실행 없음. 실제 절대경로는 비공개 설정으로 보존한다. 체크포인트와 trace의 실제 hash 검증은 실행 전 필수.
- 의뢰: [실행 계약](../../work_orders/C013_FROZEN_UNSEEN_PATH_GENERALIZATION_CODEX_KO.md). 사용자가 현재 세션에 실행·commit·push·전달을 승인했다.

## 질문과 동결 입력
Q1: A/B의 미학습 보간 I25/I50/I75를 따르는가? Q2: S의 아래→중앙→위 순서를 따르는가? Q3: seed2 배경 손상은 BASE에서도 발생하는가?
PATHS.json은 동봉 JSON의 byte 동일 사본이다. float64 공식 대조 전33프레임 오차 <1e-12 확인. x=104+208t/32; y=120+(2alpha-1)48sin²(pi*t/32), S는 120+48sin²(pi*t/32)sin(2pi*t/32). 양끝 y=120 강제. 입력은 부모 9점 offsets를 유지하고 (pixel+0.5)/(416,240), 양끝 tensor는 부모에서 exact 복사.
Checkpoint2048 SHA256 c246971ad353f78ddb0ff7bbb162f26187f9d5437eb1158e732fd29cd334f977. eval/frozen, optimizer 없음.
부모 생성기·precision·sampler·prompt·negative prompt·앵커·마스크·patches·valid/visible/box 유지. 중간 positions만 변경. inference whitelist 유지, NULL 없음, label은 lookup only.

## 실행 순서와 예산
1. 부모 실제 파일/hash/trace/가드 인수 및 사전 기록 commit/push.
2. CPU sidecar/config 제작·원자 저장·readback, evaluator fixture 검증.
3. BASE_S2 OFF seed20261029 → I25_S1 → I50_S1 → I75_S1 → S_S1 ON seed20261028. 기존 guarded cpu→heavy runner, 직렬 실행.
4. 전33프레임 검출·공통 배경 ROI·matched 입력 검증 및 정적 시각 검토.
5. 실제 MP4 우선 검토 페이지/ZIP, Spark/Mac CRC·추출·payload·hash 확인, 문서와 HISTORY/ROADMAP commit/push.
정상 sampler5/step250/model_fn250, VAE 조건 encode 통상10/decode5. 기계 sampler 복구 예비1, hard cap6; 품질 재시도0. latent 후 decode 실패는 sampler 반복 금지, VAE-only 복구 최대1. 학습/backward/probe/target encode/patch encode/다운로드/설치/외부 모델0.
전체 2시간 상한, 마지막20분 기록·전달에 예약. 시작 시각은 본 세션 인수 시작. 가드·메모리·서비스 정책을 변경하지 않고 안전 중단은 우회하지 않는다. 다른 프로세스 종료/환경변경/삭제 금지.

## 사전 평가
부모 Reader.ball 전체화면 template64, PRESENT=.50, DUPLICATE_RATIO=.75, d56 재사용. 부모 judge_pair 재사용 금지.
fixture: 네 oracle 중심오차<1px; 빈 배경 missing; 두 공 duplicate; A/B를 새 경로라 하면 PASS 불가; 배경 이동 검출. 실패 시 생성 출력 판정 전에 scorer 수정.
주9시점 0/4/8/12/16/20/24/28/32 중 정상≥8, 양끝과 핵심8/12/16/20/24 모두 정상. 주시점 평균≤11.2px, 중앙 평균≤8.4px, t16≤8.4px, 양끝 각각≤11.2px. 다른 프레임 소실/중복은 완전 경로품질 PASS 불가.
E_req와 시점별 가까운 A/B까지의 E_mem을 핵심5시점에서 계산, E_req+4≤E_mem. 누락은0으로 채우지 않는다. A/B attraction 관측을 내부 암기 구조 증명으로 확대하지 않는다.
보간 공동: 핵심 시점마다 y25<y50<y75, 인접 간격≥목표의1/2, x도 목표와 일치. S는 t8/12 아래,16 중앙,20/24 위이며 같은 단일 객체. 위치/단일성·무늬·형태/잔해/배경/시간 품질 별도.
공통 ROI: A/B+새4경로 모든 renderer mask 합집합을8px 팽창해 제외. RGB MAE,p95,차이25초과 픽셀 비율(합격선 아님), marker peak/dx/dy/raw median 보존. 불안정 표식은 MARKER_UNRELIABLE/BACKGROUND_DEFORMATION, 카메라 이동 단정 금지.
seed2 BASE/ON A/B 비교는 noise/context/text/앵커 exact가 전제. BASE_FAILURE_PRESENT / ADAPTER_ADDED_SCENE_REGRESSION / MIXED_BASE_ADAPTER_EFFECT / BACKGROUND_CAUSE_INCONCLUSIVE 구분.

## 입력 parity와 중단
첫 model_fn의96채널 context, 초기 noise, text, 실제 sigma/timestep, RGB/3채널 G, checkpoint/patches/visible/valid/positions를 기존 trace와 대조. 같은 seed noise exact, context exact. 실제50step/50call 및 final latent readback 확인.
경로·인자·import·CPU 좌표 오류는 승인 범위에서 수정. 권한/안전 중단/필수 자료 유실/예산 초과는 해당 부분 중단, ARTIFACT_UNAVAILABLE·INPUT_PARITY_UNRESOLVED 등을 보존. 잃은 과거 영상 재생성 금지.

## 결과와 전달
PLAN/PATHS/RUNS/METRICS/RESULTS/METHOD_AND_LESSON_KO/REPRODUCE/DELIVERY 기록. 원 MP4 byte 보존; raw/latent/가중치 private Spark. 공개 Git에는 비민감 문서·코드·hash만.
연속 지각 검수 없이 temporal=UNVERIFIED. 같은 세션의 이미지 검토는 독립 human 평가 아님. 실제 새4영상과 요청 경로를 첫 화면, 부모A/B 비교, seed2 BASE/ON 별도 탭, 공통 slider·시트·평면도·재생 제공.
ZIP은 실제 날짜, manifest 자기 자신/ZIP 제외; payload 수와 총 entry 수 분리. 접근하지 못한 호스트 PASS 금지. 다음 실험 자동 시작 없음.

## 실행 종료 주석 (원 사전 계획 보존)
첫 guarded CPU admission에서 START_SWAP_BUDGET으로 중단. 신규5셀 모두 NOT_RUN. 세부 RUNS/RESULTS 참조. 재시도·가드 변경 없이 종료; 사전 평가 기준은 수정하지 않음.
