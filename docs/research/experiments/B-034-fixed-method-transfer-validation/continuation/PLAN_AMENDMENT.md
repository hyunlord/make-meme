# B-034 CONTINUATION_01 — 실행 전 amendment

2026-10-27 시작 HEAD/원격 `00da73414b0c144ef77f53a79d24cbd06b80b6fd`. [사용자 전체 지시](WORK_ORDER_KO.md)를 이번 범위로 고정한다. 시작 07:16:43 UTC, hard deadline 10:16:43 UTC, 새 GPU 단계 cutoff 09:46:43 UTC. 동일 continuation 실행 부재를 실제로 확인한 뒤 진행한다.

## 보존과 질문

원래 BLOCKED_AT_BASE_TEARDOWN/other_service_work, RECOVERY_01 decode PASS/UNKNOWN_GPU_PID/NOT_CLEAN과 BASE의 target 외형 FAIL은 변경하지 않는다. 비강체 ANCHOR_UNSUITABLE/영상 NOT_RUN도 그대로다. 새 연구 번호나 BASE 재생성이 아니다.

같은 차량에서 BASE+RGB_POST / FINAL_LATENT_ONLY+동일 POST / STEP_CONSTRAINED+동일 POST를 완성한다. 목표 클래식 외형이 없는 BASE를 유지한 것을 target non-regression PASS로 승격하지 않는다. 원본 문맥 제약의 추가 국소 이득과 외형 전파 실패를 분리한다.

## 운영 보완과 방법 불변

이전 가드의 momentary cgroup 목록만으로 종료 신원을 추적하는 한계를 최소 수정한다. 실행 중 확인한 PID/starttime/boot/unit invocation/cgroup/command를 저장하고 현재 proc 및 systemd 종료 상태를 교차 확인한다. 확정된 자체 정상 종료만 OWN_WORKER_DRAINING 최대30초로 관측한다. PID 숫자만, 빈 command만, returncode0만으로 허용하지 않는다. 재사용 PID·외부 PID·관측 실패·queue busy·허용 서비스 신원 변경·memory/swap 위반은 계속 차단한다. proc 부재는 불확실성을 기록하고 bounded 재관측 후 안전 미확인 시 중단한다. 매 단계 후 새 live safety를 확인한다.

CPU fixture는 정상 종료, PID reuse, 외부 GPU, queue busy/관측 실패, 신원 불명을 포함한다. 과거 로그의 설명 가능성과 실제 원인 확정은 구분한다. 새 운영 코드는 continuation에만 저장하고 전역 predecessor와 역사적 코드/로그는 보존한다.

B033 clean_constraint.py, 공식 CFG/UniPC40/shift3/CFG5/80forward, 실제 noise/cache/model/precision/loader는 고정한다. source/ref 인코딩과 BASE 재decode는0이다. FINAL_ONLY만 decode하며 과거 CONTROL_D의 SOURCE_RECON은 실행하지 않는다.

## 영역·평가 고정

기존 source S와 실제 BASE의 잘못된 SUV support T로 E를 만든다. H=empty, source clip bbox 긴변 L의 r=max(2,ceil(.02L)), Euclidean dilation과4px feather, 시간 그룹 [0],[1..4],[5..8],[9..12],[13..16]·8×8 max·3×3 guard는 그대로다. 주석 최대30분. S/T/E/M 및 local0/8/16 경계·접촉 crop을 STEP 전에 hash로 고정한다. STEP이 영역을 벗어나도 수정하지 않는다.

주 평가: 노출 바퀴·클래식 차체·열린 상부, SUV/왜건형 회귀, 접근 방향/크기, 도로·산·울타리, 경계·접촉·그림자. 큰 도로 그래픽은 BASE부터 없었으므로 부재를 개선으로 세지 않는다. 전체17장 raw/post를 함께 공개 가능한 요약과 비공개 viewer로 비교한다. target 축은 FAIL/N/A를 유지하고 다른 축은 실제 관측에 따라 ADDITIONAL_BENEFIT / NON_REGRESSION_ONLY / TRADE_OFF / NO_BENEFIT / WORSE / INCONCLUSIVE로 구분한다. temporal=UNVERIFIED, mask-given/output-mask-assisted.

## 예산과 실행 순서

1. 종료 신원 코드·fixture 준비(목표45분), support 준비 병행.
2. 코드·입력·CPU 검증·영역 freeze를 연구 branch에 commit/push.
3. fresh safety CLEAR이면 FINAL_ONLY decode1 → 종료/회복 → STEP sampler1 → final latent 검증/종료/회복 → STEP decode1.
4. 동일 RGB_POST, 실제 비교·비용·결정·한국어 해설을 기록하고 compact/full 검증 전달.

새 sampler 최대1, decode 최대2, 이미지/encoder/학습/설치/다운로드/재시도0. 72GiB 시작/24GiB 실행 headroom/swap0 유지. GPU 순차, 타 서비스 종료0. 실패는 보존하고 downstream 중단한다. 마지막30분은 문서/보존/전달이며 추가 실험을 예약하지 않는다.

compact는 입력·영상·support·보고서·재현, full은 신규 raw/latent를 추가한다. BASE FP32 raw와 기존 전체 ZIP을 중복 포장하지 않는다. 실제 CRC/추출/payload hash/양 호스트 전송 동일성을 확인하고 미실행은 명시한다.
