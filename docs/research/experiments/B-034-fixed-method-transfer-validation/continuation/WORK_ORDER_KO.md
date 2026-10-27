# B-034 CONTINUATION_01 — 종료 신원 처리 보완과 남은 비교 마무리

저장소: hyunlord/make-meme
브랜치: docs/b-research-20261022

B-034 RECOVERY_01의 BASE decode PASS와
target 외형 FAIL, 종료 감시 NOT_CLEAN을 보존한다.

이번 작업은 새 실험이나 BASE 재생성이 아니다.
종료 감시의 최소 보완 후, 현재 안전 조건이 충족되면
기존 B-034의 CONTROL·STEP 비교를 한 번에 마무리한다.

기준 결과 커밋:
00da73414b0c144ef77f53a79d24cbd06b80b6fd

최신 HEAD를 확인하되 이 커밋으로 강제 되돌리지 않는다.
같은 작업이 실행 중이거나 완료됐다면 중복 실행하지 않는다.

## 1. 먼저 읽을 것

- B-034 PLAN.md와 기존 전체 work order
- recovery/RECOVERY_RESULTS.md
- recovery/GUARD_OBSERVATIONS.md
- recovery/code/safety.py
- recovery/code/supervisor.py
- B-033 METHOD.md와 실제 clean_constraint.py
- 연구 HISTORY·ROADMAP

기존 BLOCKED_AT_BASE_TEARDOWN, other_service_work,
RECOVERY_01 UNKNOWN_GPU_PID는 소급 수정하지 않는다.

## 2. 연구 질문 유지

BASE는 목표 클래식 차량 대신 SUV/왜건형을 만들었다.
이것은 단순 배경 오염과 다른 외형 전파 실패다.

STEP이 이 실패를 해결한다고 가정하지 않는다.
그렇다고 BASE가 나쁘다는 이유로 다른 사례로 바꾸지 않는다.

같은 입력에서 다음을 완성한다.
A. BASE + RGB_POST
B. FINAL_LATENT_ONLY + 같은 RGB_POST
C. STEP_CONSTRAINED + 같은 RGB_POST

목표 외형·원본 동작·형태·보호 장면을 따로 평가한다.
BASE부터 target이 없었으므로, 그대로 유지된 것을
target non-regression PASS로 부르지 않는다.

비강체 ANCHOR_UNSUITABLE과 영상 NOT_RUN은 그대로다.
새 사진·새 사례·R2 대체·추가 이미지 생성을 하지 않는다.

## 3. 종료 감시의 최소 보완

현재 코드는 순간적인 cgroup PID 목록을 자체 작업으로 보고,
그 목록에서 사라진 GPU PID를 UNKNOWN으로 분류한다.
이 구조가 정상 종료 상태에서도 오분류 가능한지 확인한다.

과거 원인 조사는 기존 로그 범위로 제한한다.
현재 없는 증거를 만들려고 sampler나 VAE를 다시 실행하지 마.

새 실행부터 자체 worker가 살아 있을 때
PID, /proc starttime, boot identity, unit/invocation,
소속 cgroup, 최초 확인한 command 정보를 기록한다.
실제 사용 가능한 식별 정보와 한계를 명시한다.

종료 시 현재 cgroup 목록만 보지 말고
기록된 자체 신원, 현재 /proc state/starttime,
systemd MainPID/ExecMainPID·종료 상태를 함께 확인한다.

다음은 금지한다.
- 과거에 봤던 모든 PID를 영구 허용
- PID 숫자 또는 MainPID 일치 하나만으로 허용
- command가 비었다는 이유만으로 자체 프로세스라고 확정
- worker_complete 또는 returncode0만으로 가드 오류 무시
- 외부 작업·관측 오류·PID 재사용을 종료 지연으로 처리

동일한 자체 프로세스의 정상 종료를 확인할 수 있는 경우만
OWN_WORKER_DRAINING으로 구분해 최대30초 정리를 관측한다.
그 동안 새 GPU 단계를 시작하지 않는다.

신원이 불명확하거나 /proc가 사라져 확인할 수 없는 상태는
무조건 허용하지 말고 불확실성을 기록한다.
bounded 재관측 뒤에도 안전을 확인하지 못하면 중단한다.

큐 busy·외부 PID·허용 서비스 신원 변경·memory/swap 위반은
기존처럼 차단한다. 다른 프로세스를 종료하지 않는다.

모든 종료 뒤 fresh live safety를 다시 확인한다.
기존72GiB 시작/24GiB 실행 headroom·swap0 기준은 유지한다.

CPU fixture나 기존 로그 replay로 최소한 다음을 검사한다.
- 정상 자체 프로세스 종료
- 같은 PID지만 다른 starttime
- 실제 외부 GPU PID
- 큐 busy 또는 관측 실패
- 자체 신원 확인 불가

전체 watchdog framework를 새로 만들지 마.
운영 수정과 방법 변경을 분리해 기록한다.

## 4. 기존 artifact 재사용

RECOVERY_01에서 확보한 BASE raw·PNG·MP4·final latent,
기존 source latent·원본·참조·A0·condition cache·noise를 재사용한다.

BASE 재샘플링·재디코딩, source/reference 재인코딩은0회다.
기존 출력이나 로그를 덮어쓰지 않는다.

기존 코드의 hardcoded 과거 deadline은 새 실행 설정에서만
현재 시작 시각 기준으로 명시한다.
과거 예산과 초과 기록을 수정하지 않는다.

## 5. 같은 편집 영역과 방법으로 비교

B-034 사전 PLAN의 support 규칙을 유지한다.
S는 원본 객체, T는 실제 BASE에서 생성된 객체의 support다.

T가 원하는 클래식 target의 정답 support라고 부르지 않는다.
현재 BASE는 잘못된 SUV형이라는 사실을 명시한다.

기존 수동/CPU 도구로 T를 최대30분 안에 작성하고,
S·T·E·M과 평가 crop을 STEP 전에 고정한다.
target처럼 보이게 만들기 위한 warp·mask 축소·사후 조정은 하지 않는다.

기존 규칙:
- H=empty
- source bbox 긴 변 기반 r=max(2,ceil(.02L))
- 기존 dilation·4px feather
- B-033과 동일한 시간 그룹·8×8 max·3×3 guard
를 유지한다.

잘못된 BASE를 바탕으로 한 영역이 의도한 새 차체를
제한할 수 있다는 한계도 기록한다.
STEP이 E를 벗어나면 mask를 늘려 구제하지 않는다.

FINAL_LATENT_ONLY를 기존 final/source latent에서 만들고
최대1회 decode한다.

STEP은 B-033의 같은 clean_constraint.py를 재사용한다.
양 CFG·실제 noise·scheduler·참조·driving은 그대로다.
attention·LoRA·ALG·RoPE·prompt·강도·스케줄은 바꾸지 않는다.

## 6. 예산과 실행

새 full sampler 최대1회:
40step·80forward, final latent 저장 후 decode 최대1회.

FINAL_LATENT_ONLY decode 최대1회.
새 이미지·encoder·학습·설치·다운로드·재시도0회다.

안전·입력 계약이 맞으면 결과가 나쁠 것 같다는 이유로
STEP을 생략하지 않는다.
실제 안전 문제나 입력 오류는 중단한다.

GPU-heavy 작업은 순차 실행한다.
전체 상한3시간, 마지막30분은 기록·전달·종료에 남긴다.
감시 보완은 목표45분 안으로 제한한다.

GPU 단계를 추가 실행할 안전 조건을 확인하지 못하면
남은 작업을 BLOCKED로 남기고 원인을 구체적으로 보고한다.
가드를 꺼서 완료하지 마.

## 7. 평가와 최종 결정

SOURCE / TARGET / A0 / BASE /
FINAL_LATENT_ONLY / STEP과 동일 RGB_POST 결과를
전체17장·local0/8/16에서 비교한다.

- 노출 바퀴·클래식 차체·열린 상부 등 target 특징
- SUV/왜건형 source 회귀
- 접근 흐름·방향·크기 변화
- 도로·산·울타리·비대상 객체
- 경계·접촉·그림자·새 그래픽
을 따로 판정한다.

출력이 source와 비슷해 배경이 깨끗한 것을
객체 교체 성공으로 세지 않는다.
원래 없던 큰 그래픽의 부재도 개선 증거로 쓰지 않는다.

STEP이 배경만 개선해도 target 외형 실패가 남으면
결합 목표 FAIL이다.
새 외형 변화가 나타나면 실제 target 방향인지 확인한다.

실제 연속 시청이 없으면 temporal=UNVERIFIED다.
mask-given/output-mask-assisted 한계를 유지한다.

방법 판정은 기존 B-034 기준으로
ADDITIONAL_BENEFIT / NON_REGRESSION_ONLY /
TRADE_OFF / NO_BENEFIT / WORSE / INCONCLUSIVE를 사용하되,
target이 애초에 없던 축은 N/A 또는 FAIL 유지로 구분한다.

## 8. 기록과 제출

이번은 B-034의 CONTINUATION_01로 기록한다.
새 실험 번호를 만들어 복구 작업을 연구 성과처럼 세지 않는다.

작업 전에 계획 amendment·guard 변경·CPU 검사를 고정한다.
종료 후 기존 기록을 보존하며 HISTORY·ROADMAP에
복구 결과·최종 비교·다음 연구 우선순위를 연결한다.

핵심 최종 질문은:
“원본 문맥 제약이 다른 사례에서도 추가 이득이 있었는가?”
“target 외형 실패는 해결됐는가, 그대로인가?”
“이 방법을 기본 채택할 근거가 있는가?”다.

compact에는 비교 영상·입력·support 시각화·보고서·재현을,
full에는 신규 raw/latent를 보존한다.
기존93.6MB FP32 raw를 검토 ZIP에 반복 중복하지 않는다.

새 파생 MP4 인코딩과 기존 MP4 보존을 구분하고,
실제 CRC·payload hash·추출·Mac/Spark 전송을 확인한다.
개인 정보·가중치·조건 tensor는 공개하지 않는다.
연구 branch commit/push와 원격 SHA를 확인한다.

이 비교 이후 종료한다.
추가 seed·새 사례·모델·학습·강도 탐색은 자동 시작하지 않는다.
