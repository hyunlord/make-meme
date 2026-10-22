# 연구 히스토리 — append-only

기존 결과의 문구를 조용히 바꾸지 않는다. 정정은 새 항목으로 추가하고 이전 항목을 연결한다. 아래 과거 실험 요약은 사용자가 제출한 보고서와 그때의 검토 문서에서 이관한 것이며, 이 문서 작성 과정에서 GPU 실험을 다시 실행한 것은 아니다.

## 2026-10-22 — B-001 첫 야간 연구 실험 이관

- 목적: Spark에서 생성 원리 실습과 실제 영상 모델의 학습·추론 경로를 확인.
- 보고된 실행: Flow Matching MLP 4,000회, VACE LoRA 100 optimizer update. 실제 학습 target은 도시 한 장면 복원.
- 보고된 결과: gradient·기반 가중치 보존·재로딩 검증; 영상 6회 시도에서 4개 출력; 같은 학습 도시 장면 복원 개선; 별도 adapter=null Lab baseline에서는 원본 춤 전이 실패.
- 한계: 도시 결과는 한 장면 overfit. Lab를 100회 학습한 실험이 아님. 시간 품질은 UNVERIFIED. 미관측 개체·동작 일반화, 서비스·논문 품질은 미검증.
- 근거 자산 별칭: `make-meme-B-night1-20261022-021414.zip`.
- 제출된 archive SHA256: `195209679d8fccd0ba0e3fde54de2853b291e1dd21acea861cd7aafadfddad0e`.
- 근거 문서 별칭: `MORNING_BRIEF_KO.md`, `REVIEW_KO.md`, `lab-single-before.json`, `training_config.json`.
- 위 자료의 실제 실행 commit은 실행 담당자가 로컬 환경에서 확인해 추가해야 한다. 이관 시점에는 원격 코드의 실행 동일성을 확정하지 않았다.

## 2026-10-22 — 연구 기록 운영 규칙 확정

- 사용자 요구: 항상 작업의 방향·목표·로드맵·하려는 일·히스토리를 GitHub의 Markdown으로 기록.
- 반영: CHARTER, ROADMAP, HISTORY, RECORDING_PROTOCOL, 실험 PLAN과 template를 마련했다.
- 공개 범위: 연구 문서·비민감 코드·설정·요약·해시. 실제 반려동물 사진·음원·개인 경로·모델·대형 로그는 자동 공개하지 않는다.
- 중요한 범위: 문서 작성과 계획 공개를 완료한 것이며 새 학습·추론은 실행하지 않았다.

## 2026-10-22 — B-002 사전 계획

- 상태: PLANNED / NOT_RUN.
- 질문: 모델을 고정한 상태에서 참조 배경을 바꾸면 생성 결과가 달라지는가?
- 주 비교: 원래 Lab 사진 R vs 동일 전경·자세·크기에서 배경만 흰색으로 대체한 R-bg.
- 진단: source 첫 프레임을 reference로 넣는 P. 같은 prompt가 검은 Lab를 요구하므로 순수 동일 개체 복원 positive control이라고 부르지 않는다.
- 계획: 세 조건 × 두 seed, 기존 R/첫 seed 결과가 정확히 호환되면 재사용. 새 전체 추론은 최대 5회, 학습 0회, 전체 작업 최대 2시간.
- 결정 이유: 추가 도시 학습보다 참조 조건과 구조 조건의 영향을 먼저 분리한다.
- 실행 문서: [B-002 PLAN](experiments/B-002-reference-background/PLAN.md).
- 다음: 실제 실행자는 시작 전 revision을 고정하고, 결과·해석·미확인 사항을 RESULTS.md와 이 히스토리에 추가한다.

## 2026-10-22 08:54 KST — B-002 착수 / 실행 전 고정

- 기준 문서 여섯 개를 읽고 별도 worktree를 구성했다. 기존 실행 checkout과 미추적 자산은 보존한다.
- 질문·가설·두 seed·최대 5회·학습 0회는 원래 PLAN을 유지한다. 실제 경로/전처리/노이즈 호환성을 확인한 뒤 재사용 여부를 결정한다.
- [실행 기록](experiments/B-002-reference-background/RUNNING.md), [계획](experiments/B-002-reference-background/PLAN.md).

## 2026-10-22 09:06 KST — B-002 입력 점검 완료 / 실행 시작

- 사전 계획 `2a1bcc4eceb7a1f461c843ee71445b53ffb98493`, 실행 코드 `9d81447919469c2cdeda69a9d7da25515a5b55f0`를 원격 연구 branch에서 확인한 뒤 첫 추론을 시작했다.
- 원격 가중치/토크나이저9파일 및 upstream핵심5파일, source/edge17프레임 RGB, reference와 noise를 대조해 R/첫seed 재사용을 결정했다. 과거 texttensor 직접해시는 없다는 한계는 남긴다.
- 흰 배경 참조는 원래1536×2048 전경595,340픽셀을 정확히 보존한다. 수동 윤곽/GrabCut이며 자세·크기·위치 변경 없음.
- 신규순서 R-bg22, P22, R23, R-bg23, P23. adapter=null, 학습0회. [실행 기록](experiments/B-002-reference-background/RUNNING.md).

## 2026-10-22 — B-002 통제 비교 완료

- 신규5회 완료/실패0/기존R1개 재사용/계획6셀 미실행0, 학습0, adapter=null. 실제 noise/text pairing 및 조건·코드 해시를 확인했다.
- 두 seed에서 R-bg는 침대·커튼·창 배치 재현을 줄였지만 착석은 유지했다. P는 직립했으나 실제Lab 외형이 달랐으며 prompt/reference 충돌이 있는 보조 진단군이다.
- 정적 관측과 시간 품질을 구분했다. 시간UNVERIFIED, 실제Lab춤/전체제작 수용 아님.
- 다음 하나: R-bg 고정 상태에서 실제 Canny 대 무정보 Canny로 구조 입력의 관측 가능한 효과를 분리. 자동 실행하지 않음.
- [RESULTS](experiments/B-002-reference-background/RESULTS.md), [이론](lessons/B-002-conditioning.md), [실측/해시](experiments/B-002-reference-background/run_summary.json).

## 2026-10-22 10:32 KST — B-003 사전 계획

- B-002에서 배경 복사는 줄었으나 착석이 남아 구조 조건의 영향을 분리한다.
- R-bg 고정, 실제 Canny/검정 무정보 Canny × 두 seed, 신규 추론 최대4회·학습0회·2시간 상한. 기존 결과를 네 셀 대신 재사용하지 않는다.
- 검정 RGB 입력은 VACE 제거가 아니며 reference/mask 경로를 유지한다. GPU 큐와 메모리를 확인했고 기존 환경은 수정하지 않는다.
- [PLAN](experiments/B-003-structure-condition/PLAN.md). 결과는 아직 NOT_RUN.
