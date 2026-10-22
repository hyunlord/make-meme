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

## 2026-10-22 — B-003 첫 seed 실행 완료

- 계획7368c1f 및 실행코드49c41ec의 원격 SHA를 확인한 뒤 실행했다.
- 첫 seed real/null 두 run 완료, 실제 noise/text/reference/inactive/mask동일 및 reactive 차이를 확인했다. 대표 f8의 real 착석/null 네발 자세 차이를 정적으로 관측했다. 전체 결론은 두 번째 seed와 모든 프레임 검토 뒤 기록한다.
- 모델9파일·핵심코드5파일을 새로 해시 검사했다. [진행 기록](experiments/B-003-structure-condition/RUNNING.md).

## 2026-10-22 — B-003 통제 비교 완료

- 4/4신규완료,실패0,재사용0,학습0,adapter=null. 실제 pairednoise/text/ref/inactive/mask동일,reactive/context상이 확인.
- 두 seed 모두 real착석/null사족. 구조 경로 영향은 관측됐으나 원본 직립 춤 성공0/4. reference 단독 지배는 확정하지 않음.
- 모든17프레임 시트와 대표 원본프레임을 정적 검토. 연속재생미관측으로 시간UNVERIFIED. 개인자료는GitHub비공개.
- 다음 하나: C-real 고정 R-bg/균일회색 reference 비교 제안만. 자동실행없음.
- [RESULTS](experiments/B-003-structure-condition/RESULTS.md),[이론](lessons/B-003-structure-conditioning.md),[실측](experiments/B-003-structure-condition/run_summary.json).

## 2026-10-22 — B-003 원격 실행 코드 검토 / 새 실행 없음

- 목적: 결과 요약뿐 아니라 원격에 게시된 실행·관측·검증 코드와 실제 기록의 연결을 확인한다. 검토 기준 commit은 `29f2576e56dbc5c5ed5a97d795a11d1fd5834eb5`이며, 검토 시작 시 연구 branch HEAD가 이 SHA임을 직접 조회했다.
- 직접 읽은 핵심: [runner](experiments/B-003-structure-condition/code/vace_experiment.py), [runtime observer](experiments/B-003-structure-condition/code/vace_observe.py), [validator](experiments/B-003-structure-condition/code/validate_runs.py), C-real 설정, PLAN, RESULTS, run_summary의 paired-controls 및 연구 기록 문서.
- 코드 확인: source RGB는 기록·비교용이고, 실제 `pipe(...)`에는 condition 영상·white mask·reference가 전달된다. B-003 runner는 adapter/optimizer checkpoint가 null임을 검사하며 별도 adapter load·학습 경로를 실행하지 않는다.
- 관측 확인: observer는 sampler 입력의 실제 noise/text/VACE tensor 및 reference/inactive/reactive/mask 구역을 해시한다. 공개 run_summary는 같은 seed에서 noise/text/reference/inactive/mask 동일과 reactive 차이를 기록한다. 이는 기록·코드 대조이며 검토자가 Spark에서 새로 tensor를 채취한 것은 아니다.
- 해석 정정: 구조 입력에 대한 출력 민감도와 원하는 원본 동작의 전달은 다르다. real착석/null사족 결과는 입력의 영향을 지지하지만, reference가 단독으로 지배하거나 Canny가 정답 동작을 전달한다는 증거는 아니다. 검정 영상과 회색 reference는 각각 별도의 내용 개입이며 해당 조건 branch의 제거와 같지 않다.
- 범위 제한: 이번에는 ZIP 내부·원본 이미지·연속 재생·Spark GPU 실행을 독립 검증하지 않았다. upstream 전체와 원격 공개 코드가 로컬 실행 파일의 모든 바이트와 동일한지도 새로 검증하지 않았다. 새 생성·학습·가중치 변경은 0회다.
- 다음 연구는 기존 RESULTS의 회색 reference 비교 제안을 유지하되 아직 PLANNED로 확정하거나 실행·승인하지 않는다. 이번 변경은 이 검토 이력 추가뿐이며 기존 실험 결과와 코드, A 상태는 보존한다.

## 2026-10-22 — B-004 사전 계획 등록 / 추론 미실행

- 질문: 기존 C-real을 고정하고 R-bg(Lab 배경 제거 참조)와 R-gray(균일 RGB128 참조)의 차이를 같은 seed에서 비교한다.
- B-003 C-real 두 결과가 실질적으로 같은 설정과 실제 초기 노이즈를 썼다는 것이 확인될 때만 대조군으로 재사용하며, 새 추론은 회색 참조 조건 최대 2회·학습 0회다.
- 회색 참조는 reference branch 제거가 아니고 개체·자세·배경 정보를 함께 없앤다. 직립이 나오더라도 실제 Lab identity/춤 성공이라고 판정하지 않는다.
- 실험 실행은 아직 NOT_RUN, 결과·시간 품질 미검증. GitHub에 계획 등록은 모델 호출이나 사용자 GPU 실행이 아님.
- [B-004 PLAN](experiments/B-004-reference-neutral/PLAN.md). 다음은 Codex가 계획과 실제 코드/데이터를 대조한 후 사전 등록된 조건으로 실행하고 결과를 보고하는 것.

## 2026-10-22 — B-004 실행 착수 및 첫 seed 완료

- 시작 HEAD `b08f4a5a163bd0e8256a2c7491585dd9074cc2e9`; 기존 PLAN 보존. 재사용 감사 후 코드/설정 commit `eafa250e9d03818bf6b94e69f3d2ae657076ec98` push 확인.
- 모델/입력/초기 noise 비교 가능. 첫 회색 참조 seed 완료, 두 번째 순차 실행. 학습0/adapter=null, 최대 신규2회. [RUNNING](experiments/B-004-reference-neutral/RUNNING.md).

## 2026-10-22 — B-004 통제 비교 완료

- 신규2/2완료,기존2재사용,실패0,학습0. 두seed의noise/text/구조/mask동일과referenceprefix변경실측.
- R-bg는두seed착석; R-gray는seed22착석/seed23직립형태. 실제Labidentity와원본안무미수용,연속재생미관측시간UNVERIFIED.
- 다음하나는R-gray고정C-real/C-null비교제안만이며NOT_RUN. [RESULTS](experiments/B-004-reference-neutral/RESULTS.md),[이론](lessons/B-004-reference-condition.md). 과거PLANNED기록은당시상태로보존.

## 2026-10-22 — B-004 원격 결과 검토와 B-005 사전 등록

- B-004 원격 결과 commit `546221cd887c18ec308bba4ac2f33444b6f23096`에서 RESULTS/학습 문서/run_summary를 조회함. 신규2/2, 기존2재사용, adapter=null/학습0, paired 실험은 noise/text/structure/mask 동일·reference prefix 상이로 기록됨. GPU나 비공개 MP4/ZIP을 독립 실행·시청한 것은 아님.
- R-bg의 C-real은 양 seed 착석. R-gray는 seed22 착석/seed23 직립 실루엣만 생성. 실제 Lab identity·안무는 두 seed 모두 미수용, 시간 품질 UNVERIFIED. 회색은 정상적인 identity 참조가 아닌 OOD일 수 있음.
- 다음 B-005는 2×2 factorial의 빠진 R-gray+C-null 두 seed만 신규 실행하도록 사전 계획했음. B-003(R-bg+C-real/null) 4개 및 B-004(R-gray+C-real) 2개를 설정·noise 검증 후 재사용. 최대 신규2회·학습0. 원본 동작·Lab identity를 모두 수용하기 전에는 조건 차이를 성공으로 부르지 않음.
- [B-004 결과](experiments/B-004-reference-neutral/RESULTS.md) · [B-005 계획](experiments/B-005-factorial/PLAN.md). 이 기록은 문서 작업으로, B-005 GPU 실험은 NOT_RUN.
