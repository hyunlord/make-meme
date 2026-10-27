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

## 2026-10-22 — B-005 실행 전 고정

- 시작HEAD `582e67ca0b153b5d602b04587b9f57cd36ad3426`, 기존PLAN유지. 기존6결과재사용검증통과,모델/입력/noise/코드해시고정.
- 신규gray+null두seed만실행예정,학습0,상한2회·2시간. [RUNNING](experiments/B-005-factorial/RUNNING.md).

## 2026-10-22 — B-005 첫 신규 run 완료

- 실행 고정 `ac0ecbec709ac72a36668ed22f2d09a42577f257` 원격 확인 후 첫 gray+null seed가 exit0으로 종료했다. 두 번째만 순차 실행.
- 신규 모델·학습 없음. 전체8셀 비교는 아직 미완료이며 정적대표프레임을 시간품질 통과로 해석하지 않음.

## 2026-10-22 — B-005 요인 비교 완료

- 신규gray+null2/2완료·실패0·기존6재사용·학습0. 전체8셀noise/text/조건tensor와코드무결성대조통과.
- 신규2개사족. 직립형태는gray+real의seed23한개뿐이며실제Lab+원본춤동시수용0/8. 시간UNVERIFIED.
- 같은제거실험반복중단. 다음하나는동물관절궤적·가시성·발접촉표현적합성검증제안만(NOT_RUN). [RESULTS](experiments/B-005-factorial/RESULTS.md),[이론](lessons/B-005-conditioning-interaction.md).


## 2026-10-22 — B-005 원격 기록 검토, 조건 제거 실험 종료 / B-006 사전 등록

- 사용자 제출 B-005 결과와 원격 commit `1d7e97b63dcfb27a1d16c9f91fc5a99103149688`의 RESULTS/learning/run_summary를 대조했다. R-bg/R-gray × C-real/C-null × 2seed의 8개 조건을 완성(6개 재사용+2개 신규). 8개 모두 실제 Lab identity와 원본 춤의 동시 수용 실패. 1개 회색/real의 직립 실루엣을 안무 성공으로 재분류하지 않는다.
- 이 문서 검토에서는 Spark에서 모델을 직접 재실행하지 않았다. 제출 ZIP `make-meme-B-005-20261022.zip`은 이번 리뷰 시점에 Python/container 파일 열기 요청이 실패하여 CRC/실제 영상 재생을 독립 검증하지 못했다. SHA256 `dd1500c9aa328c297637c71936a694b073ec59383ab07836bddb2a03dbd88ca9`와 파일 822개 검증은 실행 담당자가 보고한 값이다. 시간 품질 UNVERIFIED 유지.
- 판단: 조건 입력의 영향은 확인됐으나 유용한 동작 전달은 실패. 동일 회색/검정 콘텐츠 대체 실험을 반복하지 않고 동작 표현과 공식 조건 인터페이스 검토로 상위 연구 질문을 변경.
- [B-006 사전 PLAN](experiments/B-006-motion-representation/PLAN.md): 비학습식 원본 동작 주석·비교 시각화, 2D landmark의 가림/접촉 표시, 기존 VACE와 공식 SCAIL-2 RGB driving 경로·Spark 적합성 문서/코드 비교. 새 대형 모델 설치/영상 추론/학습은 NOT_RUN, 승인 범위 아님.

## 2026-10-22 — B-006 실행 전 고정

- 시작 원격 HEAD `f6819d2a5e487516896e1169237d910bd98354fd`와 사전 PLAN을 확인했다. 기존 실행 환경과 공개 문서 worktree를 분리하고 A 및 이전 결과를 보존한다.
- 수동 가시성 schema와 CPU 가시화 코드를 결과 전에 고정한다. 관측 불가능한 관절은 null; 3D 접촉/체중 분배를 2D 점으로 확정하지 않는다.
- 신규 모델 다운로드·영상 diffusion 추론·학습은 0회. 공식 SCAIL-2/VACE 코드 조사와 원본 17프레임의 동작 표현 감사만 진행한다. [RUNNING](experiments/B-006-motion-representation/RUNNING.md).

## 2026-10-22 — B-006 동작 표현·공식 조건 경로 검토 완료

- 17프레임 RGB/Canny34파일을 해시 대조하고 실제 개별 관측했다. 119개 보이는 표면점, 153개 관측 불가 관절 중심, 17개 가려진 꼬리 부착점을 구분했다. null을 보간 정답으로 바꾸지 않았다.
- 원본/Canny/overlay 비교·궤적·24fps17프레임 영상 및 Spark CPU heatmap 실습 완료. 수동점 표현이지 pose 모델 성능이 아니며 연속 재생 품질 UNVERIFIED.
- 공식 SCAIL-2 두 branch와 기존 VACE의 조건·학습 코드를 고정 commit에서 비교했다. VACE 공식 pose 지원은 있지만 animal schema 직접 지원은 미확인. SCAIL RGB driving은 공식 경로가 있으나 현재 환경의 FlashAttention 부재로 실행 BLOCKED, 전체 peak 메모리는 UNKNOWN이다.
- 다음 후보는 SCAIL-2 공식 Wan RGB driving baseline 하나. 색상 마스크·시간축16/24fps·추가 저장공간과 의존성 검증이 선행한다. 새 모델 다운로드·diffusion 추론·학습은0, B-007은 미실행이며 자동 확대하지 않는다.
- [RESULTS](experiments/B-006-motion-representation/RESULTS.md), [모델 감사](experiments/B-006-motion-representation/MODEL_AUDIT.md), [이론](lessons/B-006-animal-motion-representation.md).

## 2026-10-22 — B-006 완료 기록 검토 / B-007A 사전 등록

- 기준 remote commit `6cdd53a053c37d9a41832a08bc53949afe5fe070`에서 B-006 RESULTS, MODEL_AUDIT, VACE_AUDIT, 수학·재현 문서를 읽었다. B-006 CPU 관측점119, 미관측/가림170, RGB/Canny/heatmap 비교 및 SCAIL-2 공식 입력 검토를 완료했다고 기록됨. 이번 문서 검토자가 Spark 학습·추론을 다시 수행하지는 않았다.
- SCAIL-2 wan-scail2 공식 RGB driving+color masks 경로가 다음 후보. 현 Spark에는 필수 flash_attn module이 없으며 SM121 actual kernel/14B peak 및 입력 FPS 정합 미검증. 선택 LoRA 제외 약80GB checkpoint와 추가 변환 공간 필요. 다른 모델의 SM121 kernel 문제 사례만으로 SCAIL 직접 실패를 확정하지 않는다.
- [B-007A PLAN](experiments/B-007-scail-preflight/PLAN.md) 등록: 최대 2시간, 격리 환경의 실제 FlashAttention kernel smoke, 색상마스크·24fps·crop 및 checkpoint 변환 메모리 위험 사전검증. 80GB 모델 다운로드/전체 영상 inference/학습은 NOT_RUN 및 이번 승인 범위 밖. 통과 이후에만 별도 B-007B 승인 계획.
- 사용자 제공 ZIP `make-meme-B-006-20261022.zip`과 SHA `da563753334b2e94b5b95391cb1e0916d32f4b8121006b688e2329b1ea201f8c`의 실제 CRC/파일 해시 및 영상 재생은 이번 검토의 컨테이너 도구 오류로 독립 검증하지 못함. 개인 영상 공개하지 않음.

## 2026-10-22 — B-007A 실행 전 고정

- 시작 remote `6ca9271b8d565cf88db22bbfe61bbedecf7b915c`; 2시간/의존성2GB/최대두방법 경계를 유지한다. 격리된 실제 BF16 FlashAttention smoke와 CPU 입력 검사를 고정한다.
- 세로 Lab reference가 공식 출력 H/W를 교환하는 조건을 발견했다. 같은 crop geometry로 RGB/mask와 머리·발 보존을 확인한다.
- [실행 기록](experiments/B-007-scail-preflight/RUNNING.md). 모델 가중치·diffusion·학습은0이며 B-007B로 자동 확대하지 않는다.

## 2026-10-22 — B-007A 첫 빌드 실패 보존

- FlashAttention 릴리스의 C++17과 기존 Torch2.14의 C++20 요구가 충돌했다. 설치/연산 성공을 선언하지 않는다.
- 고정 공식 main은 현재 Torch를 위한 C++20 및 SM121 분기를 제공하므로 두 번째이자 마지막 설치 방법으로 선택했다. [RUNNING](experiments/B-007-scail-preflight/RUNNING.md).
- 원본 RGB와 mask의 동일 crop에서 머리/발은 보존되지만 초기 GrabCut에 바닥 반사가 포함됐다. 해당 v1을 보존하고 관측 가능한 바닥 경계의 수동 수정과 한계를 기록한다.

## 2026-10-22 — B-007A CPU 입력 계약과 실제 mask 함수 검증 완료

- 동일 red ID/black 배경, RGB/mask 동일 crop와119개 가시점 보존,17장24fps encode/decode 일치를 확인했다. v1 반사 오염과 v2 수동 국소 제외를 모두 보존했으며 얇은 경계는 PARTIAL이다.
- 실제 pinned mask 함수 CPU 실행에서 reference[28,1,112,64], driver[28,5,56,32], red4슬롯만 활성임을 확인했다. driver 실제 순서는 bilinear half resize 후 helper1이며 area 결과는 fractional occupancy다. [입력 검사](experiments/B-007-scail-preflight/INPUT_PREFLIGHT.md).
- 격리 FlashAttention 방법2 컴파일은 진행 중이며 실제 kernel/SDPA 오차는 아직 NOT_RUN이다. 모델 다운로드·전체 추론·학습0을 유지한다.

## 2026-10-22 — B-007A 실제 커널 사전검증 완료

- GB10 SM121 공식 FA2 BF164케이스가 FP32 SDPA 대비 사전 오차 기준을 통과했다. 릴리스 C++17 실패, Ninja PATH 수정, 내부 deadline 종료와 동일 source 한정 continuation을 보존했다.
- 의존성 source56,998,912 bytes, 새 모델 가중치/전체 diffusion/학습0. 마스크 입력 계약과 실제 helper CPU 검증 완료, 얇은 경계는 PARTIAL. 모델 변환·load peak는 NOT_MEASURED.
- [B-007A RESULTS](experiments/B-007-scail-preflight/RESULTS.md), [이론](lessons/B-007-attention-memory-feasibility.md). B-007B는 별도 승인 전 NOT_RUN이다.

## 2026-10-22 — B-007A 업로드·원격 결과 독립 검토 및 B-007B 계획 등록

- B-007A 원격 결과 commit `2f8d97bdbee699bdb168a0b00fa0b6db8f63bba8`에서 RESULTS/attention/resource/입력-masks 보고서를 읽었다. Mac/Spark 간 바이트 일치는 실행 담당자 보고이며 이 검토에서는 직접 접근한 **업로드 ZIP 한 벌**을 확인했다.
- 업로드 `make-meme-B-007A-20261022-0705.zip`: 15,456,993bytes, SHA256 `ef66556e9af77caa5f9d3cafb3405cb151d03c6237b4268258dc77c0cf4a5d6b` 직접 일치. ZIP CRC pass, manifest 224개 모두 ZIP 안의 해당 파일 bytes·SHA256과 직접 대조해 일치(전체 entry225, 나머지는 manifest 자체). 모델 forward/커널 재실행은 하지 않았다.
- 실행 기록에서 GB10 FA2 BF16 tiny attention4/4 PASS, max abs error0.00465846, 기준 atol0.01/rtol0.02, 본체 추론/peak UNKNOWN 확인. 공식 SAT checkpoint65.58GB, 필수 비선택 파일80.002GB, 변환 원본 torch.load→safetensors.save_file 및 로딩 시 peak 위험. 마스크 경계 PARTIAL, 기본 writer16fps vs source24fps mismatch.
- 결정: 작은 kernel PASS는 실질적 진전이므로 다음은 **B-007B**로 전체 모델 baseline을 단계별 시도할 가치가 있다. 다만 대규모 변환이 RAM/다른 작업에 위험하므로 다운로드 전에 메모리 안전 변환 경로를 확인하고 실제 안전 조건을 통과할 때만 80GB 파일 확보·변환·공식 예제/실제 Lab 17f 최대2건 추론하도록 사전 계획한다.
- [B-007B PLAN](experiments/B-007B-scail-baseline/PLAN.md) 등록은 계획 공개만으로, 대형 다운로드·변환·확산 영상·학습은 여전히 NOT_RUN. 사용자 또는 실행 agent의 다음 명시 지시 전 자동 실행하지 않는다.

## 2026-10-22 — B-007B 제한 baseline 실행, 실제 metadata에서 차단

- 사용자 승인 후53c58f3부터 Gate0~4를 순서대로 진행했다. 실행 전 변환기·guard·두baseline설정을 연구브랜치에 고정했다. 기존환경/A를 보존하고8개합성변환fixture와CPU writer계약을 확인했다.
- 필수SAT/CLIP 신규68,111,049,006bytes를 받고공식SHA검증,나머지6파일은검증후재사용했다. 실제SATmetadata의NumPy globals3개가사전fail-closed정책에걸렸다. np_rng_state/MT19937 opcode문맥은확인했지만unsafe역직렬화나새parser로우회하지않았다.
- **BLOCKED: 전체변환·모델load·forward·영상NOT_RUN,추론0/2,학습0.** B007A커널PASS를전체모델PASS로확대하지않는다. 실제메모리peak미측정,소유프로세스종료. 다음한경로는동일checkpoint의비텐서RNG메타데이터안전분리감사이며자동실행하지않는다.
- [RESULTS](experiments/B-007B-scail-baseline/RESULTS.md), [재현](experiments/B-007B-scail-baseline/REPRODUCE.md), [수학·코드](lessons/B-007B-conversion-and-model-forward.md). 이전PLANNED와B007A기록은그당시상태로보존한다.

## 2026-10-22 — B-007B checkpoint gate BLOCKED 확인 / B-007C 감사 사전 등록

- 원격 B-007B result commit `083a1ffc78f35ee4b37ac15e6ee55db6626580fb`의 RESULTS, REPRODUCE 및 converter_mapping.py를 확인. 신규68,111,049,006 bytes 선택 다운로드와 SHA 검증 완료, 실제 checkpoint의 np_rng_state 근방 NumPy globals `_reconstruct`, ndarray, dtype가 보수적 safe gate에서 거부됨. 변환/모델 load/diffusion 추론/학습 NOT_RUN(추론0/2). 악성 판정이나 메모리 OOM 증거가 아님.
- 사용자 제공 업로드 `make-meme-B-007B-20261022.zip` 직접 확인: 28,160,888bytes, SHA256 `1351e61ad9ff4ba1f9af39008424c0dafe13e8f647750803b5c8ff14b3450c84`, ZIP CRC PASS, manifest의 포함 171파일 길이/SHA 모두 PASS. Mac/Spark 간 바이트 동일성은 실행 담당자의 별도 확인 보고이며 이번 검토자가 해당 호스트에 직접 재연결한 것은 아님.
- private 실패 로그에서 실제 `get_unsafe_globals_in_checkpoint()` 기반 검사 거부는 `torch.load`/FakeTensorMode 이전임을 확인. opcode의 인접성만으로 NumPy globals가 RNG metadata 외에는 안 쓰인다고 확증하지 않음.
- [B-007C 안전 직렬화 감사 사전 PLAN](experiments/B-007C-checkpoint-audit/PLAN.md): 모델 재다운로드0·diffusion 추론0·optimizer0; static pickle/storage graph + synthetic fixture로 안전한 tensor-only extraction 경로 검토. `weights_only=False` 우회 금지. scoped safe_globals도 실제 65GB에 곧바로 적용하지 않음. 성공 후에도 대형 변환/모델 실행은 별도 PLAN 필요. 이 기록 시점 B-007C는 PLANNED/NOT_RUN.

## 2026-10-22 — B-007C 비실행 checkpoint 감사와 제한 fixture

- 원격 `6e2594f`의 PLAN을 확인하고 그래프·guard·fixture 코드를 실행 전에 등록했다. 실제65,582,563,395-byte SAT의 ZIP/data.pkl을 실행 없이 읽고 전후 전체 SHA와 다운로드 장부 보존을 확인했다.
- memo/BUILD를 포함한 symbolic graph에서 NumPy3 globals는 `np_rng_state`에서만 도달했다. nonliteral 객체·storage key의 root 간 공유는0. RNG는 MT19937, uint32[624],2496-byte 표현이며 실제 NumPy 객체 생성은 하지 않았다. 이는 임의 reducer 의미까지 증명한 것이 아니다.
- 소형 legacy-name fixture에서 exact scoped NumPy4항목 + weights_only CPU/mmap 값·형상·storage parity와 공식mapping/safetensors roundtrip 확인. 최초 FakeTensor framework globals 추가 및 두 번째 FakeTensor 객체 identity 실패를 보존했다. 실제 storage 검증과 FakeTensor ZIP offset 검증을 분리했다.
- **AUDIT_PASS는 감사/후속 경로 선정에 한정**. 실제65GB allowlist load·변환·모델·diffusion·학습은 모두 NOT_RUN/0. 다음 한 경로는 SHA고정·검증된격리에서 exact scoped loader metadata-only부터 시작하는 조건부 변환이며, 이번에 실행하지 않는다.
- [RESULTS](experiments/B-007C-checkpoint-audit/RESULTS.md), [코드 감사](experiments/B-007C-checkpoint-audit/CODE_AUDIT.md), [이론](lessons/B-007C-serialization-and-metadata.md). 기존 B-007B BLOCKED 기록과 strict gate는 보존한다.

## 2026-10-22 — B-007C AUDIT_PASS 검토 / B-007D 사전 등록

- B-007C 실행 담당 결과 커밋 `73c0a54f90726832c7932a64c7fd98b42832ff79`와 원격 RESULTS/CODE_AUDIT/REPRODUCE 조회. 실제 SAT checkpoint 크기65,582,563,395 bytes, SHA d6c73e94c57eb36e6351c800d1228e41ed7e45db1ccf410dd875bcfdd2945e7f. 비실행 pickle graph(7 root, 989 storage, 993 ZIP member)에서 NumPy globals는 np_rng_state root에 국한. 소형 fixture scoped 4종+weights_only/mmap/fake metadata 검사 PASS; 첫 두 실패 기록과 FakeTensor object identity 한계를 보존. **실제 65GB restricted load/변환/전체 모델 load/추론/학습은 NOT_RUN.**
- 업로드 `/mnt/data/make-meme-B-007C-20261022.zip`은 이번 세션의 Python/CaaS 읽기 도구 장애로 직접 CRC/해시 재검증하지 못함. 크기 383,179bytes, SHA 37a3b451fa8f0f6faadefc31d2f9375081f72df38a4f68b17f391b6e16636836 및 69개 파일 검증은 실행 담당자의 보고값으로만 기록함. 정확한 파일 경로를 읽도록 시도했으나 성공하지 않았으므로 독립 검증 완료라고 말하지 않음.
- 다음 [B-007D PLAN](experiments/B-007D-safe-conversion/PLAN.md)은 SHA·환경 고정 + 실제 OS 격리 아래 정확한 scoped safe_globals(4개), weights_only CPU mmap FakeTensor metadata-only 검증을 우선한다. 그 결과와 변환 memory safety가 모두 확인된 경우에만 실제 tensor-only SAT→Wan 변환을 최대 1회 시도. 신규 다운로드0, diffusion 추론0, 학습0. 여전히 SCAIL 영상 baseline은 NOT_RUN.

## 2026-10-22 — B-007D 첫 실제 제한 metadata 로드 통과

- 사전 실행 코드 `5e134fa3c8668bd9abe8b00067c01d84cd2580b3` 고정, OS 격리와 deadline cleanup 실증 후 실제 첫 CPU mmap/FakeTensor load를 수행했다.
- module987개 metadata/ZIP 대응 및 공식1307개 mapping PASS. NumPy4종 scope 복원 확인. 전체 tensor 값·모델 forward는 이 단계에서 검증하지 않았다.
- 독립 검토 및 신선한 자원 확인 후 기존 PLAN의 조건부 변환을 한 번 진행한다. [실행 기록](experiments/B-007D-safe-conversion/RUNNING.md).

## 2026-10-22 — B-007D 실제 제한 변환 완료

**CONVERSION_PASS, 모델 실행·영상 baseline NOT_RUN.** OS 격리·정확한 scoped globals·실제 metadata 통과 후 두 번째이자 마지막 CPU mmap load로 SAT→Wan tensor-only 변환을 완료했다. 원본987개에서 mapped1,307개를 만들고 모든 값 hash·dtype·shape·QKV 순서와 원본 SHA를 검증했다. 전체 변환 guard456.759초, cgroup cap32GiB, 표본 RSS 약53GiB(서로 다른 회계), OOM0. 실제 load2회·재시도0. [결과](experiments/B-007D-safe-conversion/RESULTS.md), [이론](lessons/B-007D-real-checkpoint-loading.md).

다음 하나는 별도 승인된 SCAIL 모델 적재·공식/Lab17프레임 제한 baseline이다. CPU 변환 성공은 GPU 모델 fit·영상 동작·개체 품질 성공이 아니다. 이번에는 모델·추론·학습을 시작하지 않았다.

## 2026-10-22 — B-007D 변환 성공 독립 자료 확인 / B-007E 첫 전체 모델 baseline 사전 등록

- 사용자 제출 ZIP `make-meme-B-007D-20261022-1308.zip` 369,538 bytes를 현 세션 컨테이너로 직접 열어 SHA256 `ef6d94c37a1720223b52a1e61d0776e93bc2e11f299e73003801a271a954e96c` 확인, ZIP CRC 정상, manifest 59개 파일의 크기·해시 독립 PASS. Spark 저장 65.58GB 실물과 Mac 원본은 이 검토에서 직접 읽지 않았으므로 host 간 일치·실제 모델 forward를 검증했다고 주장하지 않는다.
- GitHub B-007D 결과 commit `5e396f0cee097423e7c2ecdc3e7c4d80cc78ed64` RESULTS와 ZIP conversion ledger/code/checks를 대조. 실제 CPU mmap 제한 load 2회, SAT 987개→Wan 1,307개 tensor value/dtype/shape/hash 대응 PASS, converted output 65,582,313,560 bytes/SHA `8b844f026510f0b94d3209d66444b403a089ec179dc149d85513c13b2fa37118`. 변환 guard 456.759초, cgroup peak32GiB/RSS HWM약53GiB라는 별도 회계, OOM0. 변환 코드의 lint/type 지적은 잔존.
- 다음 [B-007E PLAN](experiments/B-007E-scail-forward/PLAN.md): 변환본 재사용, SCAIL2 official full-model RAM/디바이스 적재 계측과 메모리-안전한 로딩만 통과 시 공식17f·Lab17f 각 최대1회 생성(새 전체 diffusion 최대2회), 학습/재다운로드0. **SCAIL 모델 load/forward/영상 출력은 아직 NOT_RUN.**

## 2026-10-22 — B-007E 실제 적재·첫 forward 통과, 영상 출력 차단

**LOAD_PASS / FIRST_FORWARD_PASS / VIDEO_OUTPUT_BLOCKED.** 실제 SCAIL pipeline은268.587초에 적재,1,307tensor strict검사와12,992-token 첫 finite forward를 통과했다. 공식 sampler1회에서40/40 progress 뒤 post-sampler offload/decode 경계의 MemAvailable23.899GiB가24GiB 하한을 밑돌아 자기 프로세스만 종료했다. 정확한 종료 subphase는UNOBSERVED이며 OOM/FlashAttention 실패로 단정하지 않는다. 최종 raw/MP4/denoisedlatent 없음, Lab NOT_RUN, 추론1/2·학습0·다운로드0. [결과](experiments/B-007E-scail-forward/RESULTS.md).

다음 하나는 final latent 저장·phase hook과 post-loop DiT GPU 유지 경로의 제한된 메모리 전이 검증이다. 별도 승인 전 새 sampler·모델·학습을 자동 시작하지 않는다. 기존 계획·과거 NOT_RUN은 해당 시점 기록으로 보존한다.

## 2026-10-23 — B-007F 착수: 최종 latent 보존과 post-loop 이동 한 곳 변경

- 시작 원격 HEAD `fcd1fda723b3828d416fa4de7b14fa292f9e02a6`와 [사전 계획](experiments/B-007F-post-sampler-memory/PLAN.md)을 확인했다. B-007E의 1/2 시도·실패 기록은 보존한다.
- 기존 mixed-BF16 loader·가중치·입력·sampler·72/24GiB 가드를 유지하고 post-loop `self.model.cpu()` 한 곳만 생략한다. final decode latent의 원자적 저장·정확한 counter·단계별 메모리 관측을 선행 구현한다.
- 신규 sampler 최대2회: 공식1회, raw/MP4 검증과 종료 후 자원 회복이 모두 통과한 경우에만 별도 프로세스의 Lab1회. 자동 재시도·다운로드·학습0. 실행 코드를 공개 고정한 뒤 시작하며 현재 sampler NOT_RUN이다.

## 2026-10-23 — B-007F 공식 예제 첫 forward 전 중단

- 실행 사전 고정 `97189c029ac298b0aded73990d1858d5df9b93bf`. 새 공식 시도1/2에서 전체 적재331.44초는 통과했으나 초기 noise 저장 이후 첫 DiT forward 이전에 MemAvailable23.912720GiB가 기존24GiB 하한을 밑돌아 종료했다. swap/OOM0, exact allocating subphase UNOBSERVED.
- post-sampler 정책은 NOT_REACHED이며 final latent/raw/MP4 없음. initial noise는 E와 동일하지만 final latent가 아니다. Lab NOT_RUN·자동 재시도0·다운로드/학습0. [RESULTS](experiments/B-007F-post-sampler-memory/RESULTS.md).
- 다음 하나는 저장된 E/F trace와 코드의 pre-forward 메모리 수명 CPU-only 감사다. 새 모델 로딩·sampler·decode를 자동 실행하지 않는다. 기존 E 실패와 F 시도 장부를 보존한다.

## 2026-10-23 — B-007G 착수: 순차 프로세스로 메모리 수명 분리

- 시작 원격 `62c9ef583f109080e640184cecd58a7ad90a853d`와 [PLAN](experiments/B-007G-phase-separated-baseline/PLAN.md)을 확인했다. F post-sampler 정책은 NOT_REACHED이므로 실패 원인으로 단정하지 않는다.
- E/F CPU-only 비교 최대45분 후, 기존 수학·noise·dtype·입력 계약을 유지한 P(조건 인코딩)/S(DiT)/D(VAE) 별도 프로세스를 검증한다. 기존 pipeline 전체를 반복 적재하는 경로는 사용하지 않는다.
- 전체4시간, 공식17f16fps 한정 P1/S최대1/D1, 선행 실패 시 후속 중지. 24GiB 가드·기존 서비스·A와 E/F 기록 보존. 코드/fixture/검토/사전 push 이전 실제 실행 NOT_RUN. [진행](experiments/B-007G-phase-separated-baseline/RUNNING.md).

## 2026-10-23 — B-007G 조건 준비 프로세스 통과

- 사전 실행 고정 `648bbe4`와 신선한 가중치·환경·입력 해시를 확인한 뒤 P1을 실행했다. DiT 없이 공식 조건과 E와 같은 실제 initial noise를 저장하고 정상 종료했다.
- 조건17,365,660bytes readback/hash PASS, 전체 guarded P143.331초. 메모리 회복과 PID0 확인 후 S1에 진입하며 T5/CLIP/VAE는 인스턴스화하지 않는다. S/D 결과와 영상 품질은 아직 미확인이다. [진행](experiments/B-007G-phase-separated-baseline/RUNNING.md).

## B-007G 종료 (2026-10-23)

**CONDITION_CACHE_PASS / S_FAILED / D_NOT_RUN.** P143.331초에 실제 조건과 동일 initial noise를 저장했다. S121.054초 시도는 CPU DiT 적재 후 첫 조건의 CUDA 복원에서 `cuDevicePrimaryCtxRetain` OOM으로 종료됐고 sampler loop·첫 forward에 도달하지 않았다. 24GiB 가드 종료가 아니며 정확한 드라이버/메모리 원인은 UNKNOWN이다. 신규 슬롯1/1 사용, 재시도0, final latent/MP4 없음. [결과](experiments/B-007G-phase-separated-baseline/RESULTS.md).

다음 하나는 기존 P 캐시를 활용하는 S의 CUDA context/CPU weight 수명 사전 진단이다. decode-only용 final latent는 없으며 새 sampler는 자동 실행하지 않는다.

## B-007H 착수 (2026-10-23)

**RUNNING / probe·S·D NOT_RUN.** 원격 `51daacac291f161a21edeac3a551375fdd24f08c`와 [PLAN](experiments/B-007H-cuda-lifecycle/PLAN.md)을 확인했다. G의 조건 캐시를 재사용하며 P는 반복하지 않는다. 같은 서비스 환경의 작은 실제 CUDA 연산과 leaf별 복원 검증을 선행하고, 통과하면 별도 worker에서 CPU DiT 적재 전 CUDA 연산을 수행한다. initialized flag와 실제 연산 성공을 구분하며 원인을 사전 확정하지 않는다. probe1·CPU DiT load1·sampler1·decode1 상한, 선행 실패 시 후속 중지, 기존72/24GiB·swap0 가드 보존.

## B-007H 모델 없는 실제 CUDA 검사 통과 (2026-10-23)

사전 코드 `80f51ff`로 PROBE1을 실행해6.062초에 실제64-byte CUDA 연산·캐시16leaf 원래 device/값 복원을 통과했다. P 재실행0. 정상 종료·자원 가드를 확인한 뒤 별도 S1을 시작한다. 초기화 순서가 G 실패의 유일한 원인이었다는 결론은 아직 내리지 않는다.

## B-007H 종료 (2026-10-23)

**PROBE/S/D PASS / 공식17프레임 MP4·final latent 확보.** G 조건을 재사용하고 CPU DiT 적재 전 실제64-byte CUDA 연산을 완료했다. S1회에서80 forward·40step, D1회에서896×512·16fps·1.0625초 영상을 저장했다. guarded S1199.009초/D15.228초, 최소 MemAvailable52.44GiB, swap/OOM0. P·재시도·Lab·학습0. G 원인UNKNOWN과 시간 품질UNVERIFIED를 유지한다. [RESULTS](experiments/B-007H-cuda-lifecycle/RESULTS.md).

다음 하나는 기존 Lab 참조/RGB/mask의 제한된17프레임 baseline이다. 별도 결정 전 자동 실행하지 않는다.

## B-008 착수 (2026-10-23)

**RUNNING / Lab P·PROBE·S·D NOT_RUN.** 원격 `c7d38938e51943576637611cdec9ae51902e0d65`와 [PLAN](experiments/B-008-lab-rgb-baseline/PLAN.md), [단계 전환 결정](decisions/20261023-B-007H-to-B-008.md)을 확인했다. H의 공식 MP4 확보를 기반으로 실행 진단에서 실제 Lab 품질 연구로 옮긴다. 성공한 tiny CUDA 선행/anchor·단계 분리·loader를 유지하고 기존 실제 사진/RED mask/f0~16으로 Lab 전용 P를 만든다. 가로 공식값을 삭제해 우회하지 않고 case별 manifest로 검증한다. 3시간, P1/PROBE1/S1/D1·학습0·재시도0. 결과 관찰 전 코드·config를 고정한다.

## B-008 Lab 전용 조건 준비 통과 (2026-10-23)

P1 guarded118.06초, 세로 noise/reference/driving shape와 독립 전처리4개 hash 통과. 원본 Lab 입력에서 새 캐시를 생성했으며 공식 인간 cache 재사용0이다. fresh PROBE/S/D는 순차 선행 gate에 따라 진행한다. [진행](experiments/B-008-lab-rgb-baseline/RUNNING.md).

## B-008 종료 (2026-10-23)

**P/PROBE/S/D PASS / Lab MP4·final latent 확보 / 직립 동작 전달 FAIL.** 실제17f24fps·512×896,40step80forward, 신규 sampler1회·재시도/학습0. 전체17장 정적 검토에서 검은 Lab 외형은 유지됐지만 참조의 착석·침실 구도가 남아 원본 직립/앞발 동작을 재현하지 못했다. 특정 개체UNCERTAIN, temporalUNVERIFIED. S1066.317초, D15.219초, 최소MemAvailable51.978GiB,swap/OOM0. [RESULTS](experiments/B-008-lab-rgb-baseline/RESULTS.md).

다음 한 실험은 동일 source 동물의 첫 프레임을 참조로 한 RGB-driving 자기 재현 진단이다. 기본 동물 움직임 재현과 cross-identity/체형 전이의 어려움을 구분하려는 계획이며 새 실행은 별도 결정 전 시작하지 않는다.

## B-009 착수 및 B-008 해석 보완 (2026-10-23)

**RUNNING / P·PROBE·S·D NOT_RUN.** [독립 검토 결정](decisions/20261023-B-008-review-and-B-009.md)에 따라 자기 재현보다 [reference mask 단일 변경](experiments/B-009-reference-mask-semantics/PLAN.md)을 우선한다. 기존 Lab mask의 정확한BLACK만WHITE로 바꾸고RED·RGB·driving·text·모드·seed·sampler는 유지한다. B-008을 대조군으로 재사용하며 새 P/PROBE/S/D 각1회·sampler1회·재시도/학습0이다.

해석 정정: animation의WHITE는 참조 배경 가시성 조건이므로 침실이 남는 것 자체를 실패로 판단하지 않는다. B-008의 직립 전달 실패 관측은 유지한다. 공식 mixed-fps 학습 설명상 writer16fps 기본값을 고정16fps 학습 분포의 증거로 사용할 수 없다. 과거 기록은 보존하고 현재 해석을 이 항목으로 보완한다.

## B-009 실제 조건 단일 변경 검증 통과 (2026-10-23)

사전 코드1936356으로 P1을 실행해114.974초에 완료했다. 두 CFG reference mask WHITE prefix만 변하고 나머지14leaf가 모두비트동일함을 확인했다. RGB reference가 달라진 비교가 아니다. PROBE1도6.079초에 종료돼 승인된 S1을 시작한다. 영상 품질은 아직 미확인. [진행](experiments/B-009-reference-mask-semantics/RUNNING.md).

## B-009 종료 (2026-10-23)

**실행/조건통제 PASS · 직립/앞발 전달 FAIL.** 각P/PROBE/S/D1회,40step80forward,17f24fps MP4와 final latent 확보. 양 CFG WHITE prefix만 바뀌고 나머지14leaf는비트동일했다. 전체17장 정적 검토에서 B-008/B-009 모두 착석과 내려놓은 앞발을 유지했다. WHITE 하나로 충분하지 않으며 침실 유지 자체는 실패가 아니다. 실제 개체UNCERTAIN,temporalUNVERIFIED. S1093.089초/D15.233초,최소가용51.975GiB,swap/OOM0,cgroup high2101. [RESULTS](experiments/B-009-reference-mask-semantics/RESULTS.md).

다음 후보 하나는 source-first-frame 자기 재현과 생성 없는first-frame-repeat 정적 대조군의 동작 비교다. 직립 복사만으로 성공 처리하지 않으며 판별 어려우면INCONCLUSIVE. 이번에는 실행하지 않았다. 추가 생성/학습은 별도 결정 전 진행하지 않는다.

## B-010 착수 (2026-10-23)

B-009 WHITE 단일 변경으로 직립/앞발 전달이 회복되지 않아 색상 탐색을 끝내고 [동물 자기 재현](experiments/B-010-animal-self-reenactment/PLAN.md)을 진단한다. 원본f0를 reference로 사용하고 실제17프레임의 변화가 STATIC COPY보다 잘 전달되는지를 묻는다. GPU 전에 표면점 관측가능성과 기준을 고정하며 직립 복사 자체는 성공이 아니다. 새P/PROBE/S/D각최대1회·sampler1·재시도/학습0. 현재 NOT_RUN. [진행](experiments/B-010-animal-self-reenactment/RUNNING.md).

## B-010 생성 전 중단 (2026-10-23)

**DIAGNOSTIC_INSUFFICIENT / GPU NOT_RUN.** source f0 반복 STATIC COPY를 먼저 만들고 보이는 표면점20개 비교를 수행했다. E_copy15.5107px가 전파된 평균 관측오차19.4222px보다 작고 앞발 변화도 오차 범위였다. 일부 머리 위치 변화는 관측됐으나 전체 이동/배율과 분리한 관절 동작 증거가 부족했다. 원본 무동작이나 모델 실패가 아니라 현재 주석 정밀도의 한계다. P/PROBE/S/D모두0, 새로운 latent/생성영상 없음. [RESULTS](experiments/B-010-animal-self-reenactment/RESULTS.md).

다음 한 작업은 동일17프레임의 실제512×896 표면점 직접 재주석 CPU 감사다. 이를 이번에 수행하거나 새 sampler/구간/seed로 자동 확대하지 않았다.

## B-011 착수: 평가 수준을 나눈 탐색적 자기 재현 (2026-10-23)

시작 원격 `dfa23d6ffeb49a8471eb3487085739f35e82d646`의 [PLAN](experiments/B-011-exploratory-self-reenactment/PLAN.md)과 [사전 변경 결정](decisions/20261023-B-010-review-and-B-011.md)을 확인했다. B-010 중단은 보존하며 평균 전파 반경을 실측 RMSE로 해석하지 않는다. source의 관측 가능한 시간 변화(A)와 정확한 부위 상대 운동(B)을 생성 전에 분리하고 B 불확실성은 결과의 한계로 남긴다. 동일17장·source-f0 참조·고정 prompt로 새 P/PROBE/S/D 각최대1회, sampler1회·재시도/학습0. 관측 검토30분·전체3시간 상한. [진행](experiments/B-011-exploratory-self-reenactment/RUNNING.md).

## B-011 새 자기 재현 조건 검증 완료 (2026-10-23)

사전 고정 `ee730af08a29ecfce3d0b6a243e18f04a2c64584` 뒤 P1을121.123초에 완료했다. 실제 cache에서 reference/text 관련7leaf 변경과 driving/negative/noise/RNG/scheduler9leaf 보존을 확인했고, 보존9개는 모두 비트 동일했다. positive text는44→27token으로 바뀌었으며 Lab cache를 재사용한 결과가 아니다. P 종료/PID0 확인 후 fresh PROBE→S→D를 선행 gate에 따라 진행한다. 생성 품질은 아직 미확인이다. [진행](experiments/B-011-exploratory-self-reenactment/RUNNING.md).

## B-011 종료 (2026-10-23)

**실행 PASS / 화면 변화 대응 근거 / 관절 운동 INCONCLUSIVE.** P/PROBE/S/D각1회·sampler1회·재시도0회로40step80forward,finite final latent와17f24fps MP4를 확보했다. 고정25위치/20변위를 모두 포함한 raw E_copy16.5407px/E_gen3.5212px이며 머리의 위·왼쪽 이동과 후반 오른쪽 복귀가 대응했다. 출력의 미보정 위치 오차·앞발10위치 UNCERTAIN·같은 관측자 편향이 남으므로 통계적 우월성이나 관절 안무를 수용하지 않는다. gain UNDEFINED, temporal UNVERIFIED. B-010 중단/GPU0은 보존한다. S1062.421초,최소가용52.86GiB,swap/OOM0,cgroup high3357. [RESULTS](experiments/B-011-exploratory-self-reenactment/RESULTS.md).

다음 한 작업은 기존 원본의 더 명확한 머리·앞발 상대 동작 구간을 source-only로 검토하는 것이다. 동일17장 재주석 반복·추가 생성·seed·학습은 실행하지 않았다.

## B-012 착수: 동적 driving pair의 추가 시간 정보 (2026-10-23)

최신 원격 `aea64a71baf75db31a4aa4b9240ae4de8ad44545`와 [PLAN](experiments/B-012-clear-motion-driving-control/PLAN.md), [전환 결정](decisions/20261023-B-011-review-and-B-012.md)을 확인했다. B-011의 화면 변화 대응은 보존하되 정적 driving 모델 대조군이 없었던 한계를 직접 비교한다. 최대45분 source-only 후보3개에서 최초 적합17장 구간을 선정하고 같은reference/text/noise의 MOV 대 STILL을 각1회 실행한다. STATIC COPY는 모델 출력이 아닌 별도CPU 반복 기준이다. 4시간·sampler최대2회·재시도/학습0. 이전 연결 장애 시도는 sampler0이며 새 실험의 모델 실패로 세지 않는다. [진행](experiments/B-012-clear-motion-driving-control/RUNNING.md).
## 2026-10-23 — B-012 source-only 선정과 실행 계약 고정

- 실제24fps·361프레임 원본에서 후보3개를 검토하고 첫 적합구간 f7~23을 선정했다. 늦은 머리 roll과 몸통 상대 배치를 local0/12/14/16에 사전 고정했다. 끝 자세의 난점·얇은 mask 경계 PARTIAL은 유지한다.
- MOV/STILL은 동일reference/text 아래 RGB와mask의 시간 정보만 공동 변경한다. CPU STATIC COPY와 모델STILL을 구분한다. 두 P에서 실제4변경/12보존·noise/RNG 검증 후 순차 sampler2회만 허용한다. 이 기록 시점 실제 GPU0. [실행](experiments/B-012-clear-motion-driving-control/RUNNING.md).
## 2026-10-23 — B-012 실제 인코딩·paired 조건 통과

- 사전 고정 `8e80bdcfb9351bde5960cea4655f95ffaf22e98b` 이후 MOV/STILL을 각각 실제17장 비디오로 인코딩하고 정상 종료했다. latent slice 반복은 사용하지 않았다.
- 두 CFG의 driving4leaf만 달랐고 나머지12leaf는 모두 bit-exact였다. 초기noise/RNG/schedule·reference/text 보존을 확인했다. 두 결과 영상·동작 품질은 아직 미확인이며 정상 자원 조건에서 PROBE/S/D를 순차 실행한다. [조건 실측](experiments/B-012-clear-motion-driving-control/CONDITION_COMPARISON.json).
## 2026-10-23 — B-012 MOV 첫 출력 확보

MOV는 PROBE/S/D 각1회로 실제40step·80forward·finite final latent·17f24fps raw/MP4를 저장하고 정상 종료했다. S guard1102.221초, 재시도0. 첫 결과의 품질과 무관하게 같은 계약의 STILL 대조군을 순차 실행한다. 동작 전달 수용은 두 출력의 사전 사건 비교 뒤 판단하며 현재 미판정이다.

## B-012 종료: 동적 driving의 제한된 상대 동작 근거 (2026-10-23)

**COMPLETED / 실행·조건 통제 PASS / temporal UNVERIFIED.** source-only f7~23에서 MOV/STILL 각각 P/PROBE/S/D1회·40step80forward·17f24fps MP4와 final latent를 확보했다. 양 CFG driving4leaf만 변경되고 나머지12leaf는 실제 bit-exact였다. 전체17장 정적 검토에서 MOV는 후반 머리-몸통 상대 roll의 방향·순서를 원본에 가깝게 재현했고 STILL은 초기 자세 부근이었다. 한 same-identity pair의 동적RGB+mask 공동 기여에 대한 탐색적 근거이며 정밀 앞발·접촉·Lab 전이는 미입증이다. sampler2/2·실패/재시도/학습0, 최소 시스템가용52.095GiB·swap/OOM0. [RESULTS](experiments/B-012-clear-motion-driving-control/RESULTS.md).

다음 연구 제안은 같은 [7,24) 구간의 실제 Lab cross-identity 전이 비교 하나다. NOT_RUN이며 이번에 추가 생성·모델·학습을 시작하지 않았다. 앞선 단계의 RUNNING/NOT_RUN 기록은 당시 이력으로 보존한다.

## B-013 착수: 같은 driving에서 Lab 전이의 전신·국소 제어 분리 (2026-10-24)

**RUNNING / GPU NOT_RUN.** 시작 원격 `28a8540172768481efad7013281a7ce649985245`의 [PLAN](experiments/B-013-lab-driving-transfer/PLAN.md)과 [결정](decisions/20261024-B-012-review-and-B-013.md)을 확인했다. B-012 same-identity의 동적RGB+mask 기여를 실제 Lab 과제에서 비교한다. 기존 source[7,24) 처리RGB/mask 및 결과2개를 보존·재사용하며 새LAB_MOV/LAB_STILL만각1회다. Lab 내부가 주 통제이며 source/Lab 사이 reference·자세·체형·장면·text 차이를 순수identity효과로 부르지 않는다. 전신직립·국소머리roll·실제개체를 별도 평가한다. 4시간·sampler최대2·재시도/학습0, codegraph경고는TOOLING_WARNING으로 분리한다. [진행](experiments/B-013-lab-driving-transfer/RUNNING.md).

## B-013 실제 조건 인코딩 완료 (2026-10-24)

사전 고정 `f02896f825703a321c84127d4ef8135720176811`을 push·원격 확인한 뒤 두 Lab P를 각각1회 실행하고 정상 종료했다. [실측 pair](experiments/B-013-lab-driving-transfer/CONDITION_COMPARISON.json)의 driving4개만 바뀌었고 나머지12개는 bit-exact다. [B-012 계보](experiments/B-013-lab-driving-transfer/LINEAGE_COMPARISON.json)는 각7개 reference/text 변경과9개 통제 bit-exact를 확인했다. mask prefix/zero suffix 검사도 유지했다. 영상 품질은 아직 미판정이며 자원 회복 후 PROBE/S/D를 순차 진행한다.

## B-013 LAB_MOV 출력 확보·STILL 진행 (2026-10-24)

첫 Lab 조건은 실제40step·80forward·finite final latent와17f24fps raw/MP4를 확보했다. S guard1181.60초, D16.20초, 정상 프로세스 종료를 확인했다. 시각 품질은 판정 전이며 안전 조건이 충족돼 예정한 LAB_STILL을 이어간다. sampler2/2 예약·재시도0; 첫 품질에 따른 대조군 생략이나 추가 생성은 없다.

## B-013 종료: 착석 전신과 국소 머리 반응의 분리 (2026-10-24)

**COMPLETED / 실행·조건 PASS / 전신 FAIL / 국소 PARTIAL / temporal UNVERIFIED.** LAB_MOV/LAB_STILL 각각 P/PROBE/S/D1회·40step80forward·finite final latent·17f24fps MP4를 확보했다. pair4변경/12bit-exact, 대응 B-0127변경/9bit-exact로 입력 계보를 확인했다. 전체17장 정적 검토에서 두 출력 모두 착석·지지 앞발이 남았다. LAB_MOV의 후반 머리 반응은 더 크지만 눈·주둥이·귀 번짐으로 충실한 roll·실제 개체 유지 수용은 어렵다. 단순 검은 Lab 유사성과 실제 반려견 일치를 구분한다. sampler2/2·실패/재시도/학습0, 최소가용46.139GiB·swap/OOM0, cgroup high4242/3670은 공개한다. [RESULTS](experiments/B-013-lab-driving-transfer/RESULTS.md).

다음 연구 하나는 SCAIL reference conditioning에 ALG의 시간별 참조 완화 원리를 적용할 수 있는지 검토하고 전신 자세 대 개체 보존의 통제 실험을 설계하는 것이다. 공식3branch와2→3forward 비용, 저주파 착석 실루엣·identity 약화 위험, SCAIL 미검증을 명시한다. 이번에는 수정·추론·학습 NOT_RUN이며 자동 실행하지 않는다. 앞선 RUNNING 기록은 당시 이력으로 보존한다.

## B-014 착수: 입력 비교에서 제한된 sampling 개입으로 (2026-10-24)

**RUNNING / CPU 이식 검증 중 / GPU NOT_RUN.** 원격`152b6771397176ac0eb1860debc0902331c5d523`의 [PLAN](experiments/B-014-alg-scail-pilot/PLAN.md)과 [결정](decisions/20261024-B-013-review-and-B-014.md)을 확인했다. B-013의 전신FAIL/국소PARTIAL/얼굴번짐을 보존하며 단순움직임증가를 목표로 삼지 않는다. 공식ALG의 원본negative 기준항을 보존한3항식을 ref-latent 공간필터로 이식하고, CPU계약·사전코드고정이 통과할 때만 기존LAB_MOV조건으로 pilot1회 수행한다. ratio0.4·45×26·bilinearAA·i0..7고정,40step88forward; P0·retry0·학습0·3시간. 새모델·ALG_STILL·추가seed·강도탐색은 실행하지 않는다. [진행](experiments/B-014-alg-scail-pilot/RUNNING.md).

## 2026-10-24 — B-014 ALG 이식 pilot 종료

- GPU 이전 commit `3cd90e196307fe1f663e8533124a0cbe42f8f41e`; 공식3항식/공간필터/초기8step/88forward를 고정했다. CPU9·helper typecheck 및 실제 parent-cache 계약을 확인했다. 기존 결과는 보존했다.
- P0, PROBE/S/D 각각1회·실패0·재시도0. 실제40step88forward·finite final latent·17f24fps MP4 완료. 자체unit inactive/PID0, 기존 서비스 유지.
- 전신 착석 FAIL, 후기 국소 PARTIAL, 후기 얼굴·귀 번짐 지속, 실제개체 UNCERTAIN, 시간 UNVERIFIED. 일부 초기/중기 얼굴 가독성 차이가 있지만 동작충실도+개체형태 동시 개선은 NOT_ESTABLISHED.
- S1266.471초 guard, 최소가용46.507GiB, CUDA peak33.847GiB, swap/OOM0. NFE80→88 비용과 관측 한계를 분리했다.
- [결과](experiments/B-014-alg-scail-pilot/RESULTS.md), [이식감사](experiments/B-014-alg-scail-pilot/ADAPTATION_AUDIT.md), [학습](lessons/B-014-alg-and-conditional-velocity.md).
- 다음 하나는 고정 ALG_STILL 대조군 제안이며 이번 NOT_RUN/미승인. 추가 실험으로 자동 진행하지 않는다.

## 2026-10-24 — B-015 착수: ALG pilot의 마지막 정적 driving 대조군

원격 `7214ed16e550169d92eaeb5e98a36fc7fc5d5a5a`의 [PLAN](experiments/B-015-alg-driving-control/PLAN.md)과 [결정](decisions/20261024-B-014-review-and-B-015.md)을 확인했다. B-014 이식·실행 PASS와 목표품질 NOT_ESTABLISHED는 보존한다. 남은 ALG_STILL 한 칸만 생성해 CFG/ALG×MOV/STILL을 완성하는 진단이며 강도·스케줄 탐색이 아니다. B-013 STILL cache를 읽기 전용 재사용하고 실제4변경/12보존 및 새 STILL-bound sidecar를 CPU 검증한다. 현재 GPU NOT_RUN, P0·PROBE/S/D각최대1·재시도0·3시간. [진행](experiments/B-015-alg-driving-control/RUNNING.md), [사전 평가](experiments/B-015-alg-driving-control/PREREG_EVALUATION.md). 비교 후 현재 ALG pilot을 닫고 다음 가설 하나만 제안한다.

## 2026-10-24 — B-015 대조군 완료 및 고정 ALG pilot 종료

실행전고정a2847634d45d6860ea6c0d7d9c42d7dc18781b3f 이후 ALG_STILL만1회생성했다. P0·PROBE/S/D각1·재시도0·실제40step88forward·finite final latent·17f24fps MP4. 실제cache4변경/12bit-exact, STILL-bound sidecar와기존필터값일치, 종료149hash보존을확인했다. S guard1264.928초·최소가용46.226GiB·swap/OOM0, high4674는별도기록했다.

전체17장검토에서두STILL은상대적으로선명한착석,두MOV는후반머리변화/얼굴·귀손상. 전신FAIL·개체UNCERTAIN·목표개선NOT_ESTABLISHED·temporalUNVERIFIED. [RESULTS](experiments/B-015-alg-driving-control/RESULTS.md), [학습](lessons/B-015-guidance-driving-interaction.md). 현재ALGpilot을닫고추가강도/스케줄/seed탐색을하지않는다. 다음가설은animation을유지한reference RoPE H offset단독개입이며코드상분리가능하지만미검증혼합규약이다. 구현/추론NOT_RUN. 이전착수기록과B014실패는보존한다.

## B-016 착수 (2026-10-24)

**RUNNING / GPU NOT_RUN.** 고정 ALG pilot을 종료하고 기본 CFG로 복귀한다. 원격 `6ef151b090d6c839e99d84a3547e7671f128e5ac`의 [PLAN](experiments/B-016-reference-rope-h/PLAN.md)에 따라 기존 LAB_MOV 캐시16leaf와 모든 입력·sampler를 보존한 채 animation reference RoPE H만120으로 지정한다. 격리 코드/CPU fixed-QK 계약/실제 import를 먼저 검증하며 기존 H0 결과를 재사용한다. P0·PROBE/S/D각최대1·40step80forward·3시간·retry/학습0. 이 hybrid가 학습분포 내라는 주장이나 replacement 전체 재현은 하지 않는다. [진행](experiments/B-016-reference-rope-h/RUNNING.md).

## B-016 CPU 계약과 PROBE 완료 (2026-10-24)

사전 실행 코드 `68c5af7`를 원격 고정했다. CPU10검사와16leaf 원본계약을 확인하고, PROBE1의 정상 종료·자원 회복 뒤 S1에 진입했다. 실수Q/K 고정검사의 불변성은 실제 softmax/영상 품질 증거가 아니다. full-package CPU import 실패와 meta-only fixture 구분·상속 typing NOT_CLEAN을 보존한다. [진행](experiments/B-016-reference-rope-h/RUNNING.md).

## B-016 종료 (2026-10-24)

**COMPLETED / 실행·ref-H 단일 개입 PASS / 전신 FAIL / 품질 개선 NOT_ESTABLISHED / temporal UNVERIFIED.** P0·PROBE/S/D각1·40step80forward, 실제 canonical patch와40blocks×80회 위치검사, 원본16leaf 보존을 확인했다. finite final latent와17f24fps MP4를 확보했지만 H120도 착석·지지 앞발이며 후기 머리/얼굴 손상이 남았다. 일부 차이를 원본 roll·실제 개체 동시 개선으로 올리지 않는다. S1057.032초·최소가용52.605GiB·swap/OOM0. [RESULTS](experiments/B-016-reference-rope-h/RESULTS.md).

ALG는 기본 채택하지 않고 offset sweep도 종료한다. 다음 가설 하나는 동물 identity/reference 자세 분리를 학습할 허가된 paired 데이터의 타당성 감사다. 다른 개체를 Lab 정답으로 쓰지 않으며 이번에는 데이터 수집·학습·추가 생성 NOT_RUN이다.

## B-017 착수 (2026-10-24)

**RUNNING / 생성·학습0.** ALG/H120을 기본 경로로 채택하지 않고, 허용된 실제 자료로 R/D/Y 학습 예제를 구성할 수 있는지 조사한다. 시작 HEAD `ffe0369682eb2b0c3a903c44a2f23d5ff91b2299`, [PLAN](experiments/B-017-paired-animal-data/PLAN.md), [선정 규칙](experiments/B-017-paired-animal-data/SELECTION_RULES.md). SELF_RECON_SMOKE·SAME_ID_POSE_VARIATION·실제 CROSS_ID_MOTION_PAIR와 권한 상태를 별도 판정한다. 기존 source 개발구간을 독립test로 바꾸지 않으며 다른 개체나 생성실패를 Lab target으로 승격하지 않는다. 3시간CPU중심, 최대8case; 다음 학습은 자동 실행하지 않는다.

## B-017 종료 (2026-10-24)

**COMPLETED_CPU_AUDIT / RIGHTS_PENDING / DATA_GAP.** 등록자료12asset에서 source-file 검토case2개와 실제LabY가없는후보1개를구성했다. 실제CPU14media역할decode·shape·fps·PTS·복사hash통과, 두sourcecase D=Y동일, 독립test0. self파일구조는있지만 원본진위/학습권한UNKNOWN으로training-ready0; f0/f7참조다양성NOT_ESTABLISHED; 실제cross-IDpair0이다. [RESULTS](experiments/B-017-paired-animal-data/RESULTS.md), [학습해설](lessons/B-017-paired-data-and-flow-training.md). 공식Wan/SAT경로의Y·R·D·first_frame/history/loss·genericLoRA와실제recipe차이를확인했다. 생성·모델load·VAEencode·optimizer0. 다음한작업은권한있는실제Lab자연동작영상과다른자세reference/촬영session확보이며, 추가학습·생성은실행하지않는다. ALG/H120은기본경로로채택하지않는다.

## B-018 착수 (2026-10-24)

**RUNNING / GPU NOT_RUN.** 원격 `a8885357684904285014ee28ac568f568ee59762`의 계획과 실행 지시를 확인했다. B-017 RIGHTS_PENDING/DATA_GAP는 보존하며 실데이터 확보와 학습 배선 검증을 분리한다. 마지막 self-attention 하나에 synthetic tensor와 Q/V rank4 LoRA를 사용한다. CPU 계약을 먼저 검사하고 공식 FA backward·최대3 update·adapter 저장/재로딩을 GPU worker1회 안에서 확인한다. 전체 모델·영상·개인 미디어 학습은0, 실제 동물 품질은 NOT_RUN이다.

## B-018 종료 (2026-10-24)

**COMPONENT_BACKWARD_PASS / COMPONENT_UPDATE_RELOAD_PASS.** 사전고정 `2b562188cc0ad30cf822583d53a3d66babbd8e1e` 후 GPU worker1회에서 공식 FA2 backward3회·AdamW3update·attention8forward를 완료했다. Q/V rank4 adapter81,920개만 변경, base 불변·fresh reload·OFF 오차0. 선택10tensor419,553,280bytes만 읽었으며 개인미디어·전체모델·영상sampler0이다. worker7.9725s·CUDApeak297,412,096B·swap/OOM0·자체unit종료 확인. CPU11검사PASS이나 정적typing은helper19warnings/runner20errors135warnings로NOT_CLEAN을 보존한다. [RESULTS](experiments/B-018-lora-component-smoke/RESULTS.md). B-017 RIGHTS_PENDING/DATA_GAP, FULL_MODEL_TRAINING/VIDEO_QUALITY/IDENTITY_POSE_DISENTANGLEMENT NOT_RUN은 그대로다. 다음한연구는같은synthetic계약의마지막transformerblock단위backward/메모리검증계획이며 이번에는 실행하지 않았다.

## B-019 착수 (2026-10-24)

**RUNNING / GPU NOT_RUN.** 시작 HEAD `a930e137e3301fa3b3f748e8e3942a54f492c290`의 [PLAN](experiments/B-019-transformer-block-backward/PLAN.md)에 따라 공식 마지막 block 전체의 frozen cross/FFN/residual 경로를 통과하는 LoRA gradient를 검사한다. B-018 실제 synthetic x/target·initial adapter를 재사용하고 소형3update/8forward 뒤 안전할 때만12992token forward/backward1회·update0을 수행한다. worker1회·16GiBcap·72GiB시작/24GiBheadroom·swap0·2시간이며 자료/권한 부족과 영상학습NOT_RUN은 보존한다.

## 2026-10-24 B-019 종료: 마지막 block의 실제 gradient 경로

[RESULTS](experiments/B-019-transformer-block-backward/RESULTS.md): 소형8forward/3backward/3update·fresh reload/OFF PASS, 긴12,992token 한block1forward/1backward/update0 PASS. FA2실제 backward와 cross/FFN derivative·image/text context gradient를 확인했다. 총worker1·9forward·4backward·3update, 재시도0. 긴CUDA peakallocated5.816GiB는 전체모델 학습 보증이 아니다. B-017실데이터/권한 DATA_PENDING은 유지하며 다음 목표는 권한확인된 실제Lab 자연동작의 동일개체 조건부FM 소형overfit 하나다. 이번에 전체모델/영상/실데이터학습은 NOT_RUN이며 추가component 시리즈나학습은 시작하지 않는다.

## 2026-10-24 B-020 준비 확인: DATA_PENDING, 실행 미착수

최신 원격 `82d22372693a641aa78eaa7974b0a269dab81665`의 [PLAN](experiments/B-020-real-fm-tail-overfit/PLAN.md)을 확인했다. B-019로 구성요소 smoke는 종료한다. 이번 요청에는 실제 Lab 자연동작 Y/R와 사용 범위가 새로 제공되지 않아 기존 데이터 부족을 유지한다. 같은 권한 감사·synthetic 대체 실험·GPU 실행은0이다. [준비 상태](experiments/B-020-real-fm-tail-overfit/STATUS.md)에 누락자료와 실행 재개 조건을 한 번 기록했다. 실제 자료·실행 지시 이후 입력/시간축·3학습tuple/1동일clip 보조tuple·공식FM/head 계약과 코드를 확정할 때만 착수를 기록한다. 현재 PLANNED / DATA_PENDING / GPU NOT_RUN이며 학습을 시작하지 않았다.

## 2026-10-24 B-020 실제 자료 제공 후 착수

**RUNNING / 입력 CPU 확인 완료 / GPU 아직 NOT_RUN.** 사용자가 새 자연동작 영상과 기존 앉은 Lab 사진의 동일 개체 및 비공개 연구 학습·평가 사용을 확인했다. 새 자료의 권한 게이트를 해소하되 B-017의 과거 제3자 자료 권한 부족은 보존한다. [입력 확정](experiments/B-020-real-fm-tail-overfit/INPUT_AMENDMENT.md): 최초 적합 f126~142,30fps,896×512 letterbox, D=Y SELF_RECON_FM_SMOKE. 실제 Y VAE velocity target의 고정3학습/1동일clip noise-time holdout, 마지막block Q/V LoRA 최대20update로 넘어간다. synthetic 구성요소 실험 반복·cross-ID 일반화·전체모델 학습은 이번 목표가 아니다. CPU계약과 런타임 소스 검토 이후 코드/config/hash를 고정하고 단계별 안전 조건하에만 실행한다.

### B-020 P 완료

실제 Lab Y의 정상 VAE 인코딩과 조건 캐시 저장을 완료했다. worker170.530초, clean exit 후 고정4tuple prefix에 진입한다. 이는 target 확보이며 아직 학습·영상 품질 수용은 아니다. [실행 기록](experiments/B-020-real-fm-tail-overfit/RUNNING.md).

### B-020 prefix 완료·baseline 시작

고정4tuple의 실제 전체 positive forward에서 h38와기준velocity를 저장했다. 학습하지 않은 기준 영상 BASE_S1에 진입했으며 split parity/학습은 아직 미실행이다. 같은 clip/조건/noise의 사전 고정 비교만 진행한다.

### B-020 학습 전 샘플링 완료

BASE_S1의40step/80forward·final latent 저장을 확인하고 별도VAE decode로 이동했다. 실제FM 업데이트는 아직0이며, 기준출력은 학습 전 것으로 보존한다.

### B-020 실제 FM 20update·reload 완료

실제Y velocity target을 공식head/unpatchify까지 통과시킨 tail학습20update·10eval을 완료했다. parity/reload/OFF 오차0, base불변이며 고정3train/1sameclipholdout loss는 소폭 감소했다. 이는 학습배선/유한tuple회귀 결과로만 수용한다. 동일조건의 학습후샘플링1회에 진입하며 품질은 아직미검증이다.

## 2026-10-24 B-020 종료: 실제FM 연결 PASS, 품질 개선 미입증

[RESULTS](experiments/B-020-real-fm-tail-overfit/RESULTS.md): 사용자 허용 실제Lab 자연동작17frame/30fps로 P1·prefix4tuple·실제FM tail20update/10eval·전후sampler각40/80·decode각1을 완료했다. parity/reload/OFF max_abs0·base불변, 고정train/holdout MSE는 소폭 감소했다. 그러나 전후 모두 착석 reference 자세·배경과 후반 머리잘림이 남아 target의서있는전신 FAIL/품질개선 NOT_ESTABLISHED, temporal UNVERIFIED다. 모든자체GPUworker종료·재시도0·swap/OOM0, cgroup high이벤트는실측대로보존한다. 다음은같은조건의사전고정100update로 적합량부족 가설을검사하는연구하나만제안하며 이번에는실행하지않는다. D=Y shortcut·동일clip noiseholdout·cross-ID/일반화 NOT_RUN을유지한다.

## 2026-10-24 B-021 착수: 고정 FM 문제의 update 예산 비교

**RUNNING / GPU NOT_RUN.** 시작 원격 `5cde7b21d269234917ac5a0ddc30c21494fff69e`의 [PLAN](experiments/B-021-fixed-tuple-update-budget/PLAN.md)을 사용자 지시에 따라 실행한다. B-020 실제 initial adapter와 producer 캐시를 보존·재사용하고 fresh AdamW로0→100을 한 번 학습한다. 20회 replay를 증량 전에 검사하며, 기술 검증 통과 시 고정100endpoint 영상만 한 번 생성한다. 학습량 부족을 원인으로 미리 확정하지 않고, 실제3tuple 적합·sameclip holdout·CFG rollout·영상품질을 구분한다. [실행 기록](experiments/B-021-fixed-tuple-update-budget/RUNNING.md).

### B-021 20회 replay 중단

TRAIN1에서 실제20update/8평가 후 사전adapter replay 기준을 넘겨21이전 중단했다. loss replay4개는PASS지만adapter4개는FAIL이다. 50/100·영상은NOT_RUN, 기존실험은그대로보존한다. 실패원인과품질영향은아직UNKNOWN이며추가학습 없이저장물과기존로그를분석한다.


## 2026-10-24 B-021 종료: update20 replay 중단

[RESULTS](experiments/B-021-fixed-tuple-update-budget/RESULTS.md): 실제 initial+fresh AdamW로20update·8평가를 수행했다. 네 scalar loss replay는 PASS지만 네 adapter tensor는 사전 elementwise 기준을 초과해21이전 중단했다. 0/20 adapter·optimizer·RNG·cursor 저장/readback은 PASS,50/100·새 sampler/decode는 NOT_RUN이다. 100회 품질 효과는 미확인이며 원인은 UNKNOWN이다. 같은 입력의 FA2 backward 수치 반복성 가설 하나만 다음 연구로 제안하고 추가 실행은 하지 않는다. 사후 tolerance 완화·자동 재개는 하지 않으며 과거 품질 미입증을 보존한다.

## 2026-10-24 B-022 착수: 저장된 같은20회 상태의 추가 학습

[PLAN](experiments/B-022-resumed-update-comparison/PLAN.md)을 사용자 승인 범위에서 실행한다. B-021의 엄격한 독립 replay FAIL을 보존하고, 이번 질문은 유효한 동일 checkpoint에서 추가80update의 효과다. adapter뿐 아니라 AdamW/RNG/cursor를 복원하고 제한된 velocity/gradient 진단 후 matched20/100 영상 비교를 수행한다. 현재 CPU 사전검증 중, GPU NOT_RUN이며 실제 실행 전 코드/config를 고정한다.

### B-022 동일checkpoint 재개 학습 완료

restart20의18개tensor와 optimizer/RNG/cursor를 복원하고 추가80update를 완료했다.20/50/100 고정tuple 평가loss는 감소했으며 fresh reload/OFF·이번 실행 기반값 불변은PASS다. 진단3backward에서 prediction은 같고 gradient에는 작은 차이가 있었으나 FA2 단독 원인은UNKNOWN이다. 비학습tail forward33회로상한내이며 영상pair는진행중이다. B-021의FAIL과미도달검사는보존한다.

## 2026-10-24 UTC / 2026-10-25 KST B-022 종료

[RESULTS](experiments/B-022-resumed-update-comparison/RESULTS.md): 같은B021restart20에서optimizer/RNG/cursor복원후80회추가학습·33비학습forward·3진단backward를완료했다. 고정4tupleloss감소와새reload/OFF·이번base불변PASS다. matched20/100은동일16leaf/noise로각40/80sampler·decode1,17f30fps완료. 두영상모두착석/침실/padding/후반얼굴손상·잘림이남아전신FAIL·품질개선NOT_ESTABLISHED·temporalUNVERIFIED다. B021FAIL/NOT_REACHED는보존한다. 자체worker종료·swap/OOM0,high reclaim이벤트는원시기록유지. 자동증량은하지않는다. 실행중추가된B연구v2/B023문서도보존했으며,다음은이미계획된공식replacement로과제조건불일치가설을검사하는경로하나만제안한다. B023은NOT_RUN이다.

## 2026-10-25 B-023 착수: 원본 보존 편집의 과제 적합성

최신 원격 `fee6896bea73a2cd2a3b5f6c7f5baf062eb505d3`와 B-022 종료를 확인했다. B-023 기존 실행 디렉터리/활성 작업이 없는 상태에서 CPU 입력·계보 검증을 시작했다. B020 실제 Lab f126..142·30fps·896×512·미학습 기준선을 유지하고 ref RED/BLACK + driver RED/WHITE + 공식 replacement를 묶어 비교한다. 과거 밈2case/ROI 후보는 이번 범위가 아니다. 신규 sampler 최대1·decode1, 학습/다운로드/합성0; 미실행 상태에서 코드·EditSpec·조건 차이를 사전 고정한다. 최종 목표는 단일 Spark의 원본 보존 객체 편집이며 이번은 그 첫 제한 기준선이다. 결과에 따라 다음 병목 하나만 선택한다.

## 2026-10-25 B-023 종료: 공식 replacement 실행, 과제 품질 미수용

[RESULTS](experiments/B-023-task-aligned-replacement/RESULTS.md): 동일Lab 자연동작 f126..142/30fps에서 P0·PROBE1·S1(40/80)·D1을 완료했다. 양CFG ref RED/BLACK·driver RED/WHITE와 공식replacement 위치 계약, noise/14leaf보존·adapter/ALG/override OFF를 확인했다. raw에는 중앙 착석/침실/세로경계가 남고 양옆이 원본과 다른 방으로 생성되어 사족자세·장면보존 FAIL, 후반얼굴손상/잘림 지속·품질개선 미입증이다. temporal UNVERIFIED, 같은개체/sourcecopy 한계 유지. 새학습/설치/재시도/ROI합성0, 자체worker종료. 다음 병목은 참조 공간배치와 객체외형의 분리이며 조건 연결의 구현 문제와 모델 의존성을 구분할 한정 검증만 제안한다. 추가 실험은 실행/예약하지 않는다.

## 2026-10-25 B-024 착수: 참조 RGB의 배경·padding 분리

[B024 PLAN](experiments/B-024-reference-rgb-isolation/PLAN.md)에 따라 B023정식replacement과제FAIL을보존하고, 같은Lab의reference에서기존REDsupport밖RGB만128로바꾸는한정비교를착수한다. 원본보존객체편집의병목을조건경로에서좁히며VAE/CLIP두경로재계산,semanticmask/모드/noise불변을검증한다. 현재CPU준비/GPU NOT_RUN, 연결확인최대30분·전체3시간·sampler최대1이다. 배경제거는자세제거가아니며새학습/모델/합성은없다.

### B-024 조건 연결 확인 및 실행 진입

기존reference/driving latent를각1회복원해착석침실과사족자연동작의역할을직접확인했다. 원본VAE/CLIP재인코딩max/RMS0,새회색reference의4leaf변경/12보존을확인했다. 구체적pipeline결함은발견하지못했으나모든잠재결함을배제한것은아니다. 신규referenceworker1회종료후PROBE와단일S를진행하며첫실제CFG에서새reference객체전달을확인했다. 결과품질은아직판정하지않는다.

## 2026-10-25 B-024 종료: 참조 비객체 RGB 중립화와 원본 보존 개선

[RESULTS](experiments/B-024-reference-rgb-isolation/RESULTS.md): 기존support안RGB를exact보존하고밖만128로바꿔VAE/CLIP4leaf를재계산했다.12leaf/noise/semanticmask/replacement계약불변,REF/PROBE/S/D각1·40/80·finallatent/MP4완료다. 원본/B023/B024전체17장정적검토에서침실·세로구획대신원본에가까운사족자세·타일장면·후반고개방향이관측됐다. 실제raw→PNG17개계보를추가확인해source파일대체를배제했지만모델의source-copy가능성은남는다. 따라서reference개체치환/cross-ID/일반화는미입증,temporalUNVERIFIED다. 기존B023/B021실패를소급수정하지않는다. 다음병목하나는짧은cross-ID과제에서reference외형반영을source-copy와구별하는것이며추가실행/예약은없다.

## 2026-10-25 B-025 착수: 같은 중립 caption의 참조 교체

B024의 정적 자세·장면 개선과 source-copy 혼동을 보존한다. [B025](experiments/B-025-matched-reference-swap/RUNNING.md)는 같은 자연동작·중립 caption·실제 noise에서 Lab/IG 참조 묶음만 달리하는 두 출력을 생성해 원본 보존 객체 편집의 실제 외형 변경 근거를 확인한다. 기존 사용자 원본 IG와 기존 support를 찾아 입력을 고정했고 새 모델/주석 확대 없이 CPU 검사를 수행했다. GPU는 사전 코드 공개 고정 이후 순차 각1회이며 현재 NOT_RUN이다. 원래 B024 caption 출력은 새 Lab 대조군으로 대신하지 않는다.

### B-025 실제 조건 준비 완료

공통 positive T5 1회, IG VAE/CLIP 각1회, Lab 특징 재사용으로 ENC가 완료됐다. 실제 pair는 양CFG ref/CLIP/refmask6leaf만 변경되고 나머지10leaf와 device구조가 동일하다. B024와 새Lab의 차이는 positive t1뿐이다. encoder 종료/자원회복 후 신규Lab sampler에 진입한다. 시각결과는 아직 미판정이다.

## 2026-10-25 B-025 종료: 참조 외형 반응과 자세 복사 분리

[RESULTS](experiments/B-025-matched-reference-swap/RESULTS.md). 같은 중립 caption/source/noise의 신규 Lab/IG pair를 각40step80forward로 완료했다. Lab은 사족 자세·원본 방·후반 고개 방향을 유지했다. IG는 회갈색/흰가슴·좁은주둥이·가는사지로 바뀌어 단순 recolor 이상의 참조 반응이 있으나 누운 reference 자세도 복사했고 source의 서기와 머리 궤적을 보존하지 못했다. 방 구도는 남지만 바닥 로프가 없어 scene PARTIAL이다. 따라서 기술 PASS, appearance 반응 근거, 결합 편집 목표 FAIL, 실제개체 UNCERTAIN/temporalUNVERIFIED다. B024 개선이나 과거 실패를 소급 변경하지 않는다. 다음 병목은 동일 IG의 실제 서 있는 참조와 비교할 때 목표 자세 일치가 전신 동작 보존을 바꾸는지이며 이번 추가 실행은 없다.


## 2026-10-25 B-026 availability 종료: REFERENCE_PENDING / GPU 0

[결과](experiments/B-026-reference-pose-sensitivity/RESULTS.md). 시작 원격 `dbcec725cd9e64bc6f83c8b948ece488622d8b0a`와 중복 실행 부재를 확인하고, 허용된 원본 11장 및 기존 manifest만 검토했다. 누운 IG 사진들과 상체를 세운 차량 후보는 있지만 후자는 뒤쪽 몸통·뒷다리 지지가 가려져 자연스러운 사족 기립을 확정할 수 없다. 적합한 같은 IG 원본 영상 계보도 확인되지 않았다. 따라서 P/PROBE/S/D·학습 모두 0회, 새 ZIP 없이 자료 대기한다. 다음 필요 입력은 같은 IG의 실제 사족 기립 원본 한 장이며 추가 검사나 다른 실험은 시작하지 않는다. 이는 참조 자세 적합성의 조건부 진단이며 최종 제품 목표를 기립 참조 필수로 바꾸지 않는다. B-025의 외형 반응과 자세·동작 실패는 그대로 보존한다.

## 2026-10-26 KST B-027 착수: 개인 사례에서 공개 다중 사례로 전환

최신 원격 `88145d9324765b8ca68fabca24dd5d76f6a2ceb0`와 B-027 중복 실행 부재를 확인했다. [PLAN](experiments/B-027-public-reference-robustness/PLAN.md)에 따라 공개 source/target 및 두 reference를 출력 전에 고정한다. 공식 DAVIS TrainVal480p 다운로드와 이용 조건 확인을 시작했고 GPU NOT_RUN이다. 개인사진은 주평가에서 제외하고 B-026 선택적 대기와 과거 실패를 보존한다. 새 모델/패키지/학습0, 공개자료 누적5GiB와 최대6sampler·8시간 상한을 유지한다. 실제 파일 확보와 선정 완료는 후속 입력 기록에서 별도로 확인한다.

### B-027 입력 고정 및 실행 진입

공식 DAVIS480p832766765bytes의 전체ZIP CRC와 로컬SHA를 확인했다.7sequence에서최대12입력묶음을검토해 dog→dog-gooses, dance-twirl→dance-jump, car-roundabout→car-shadow를 고정했다. 원본FPS미확인/preview24fps,각17frame·896×512·mask-given이다. 두참조의자세/시점/크기/가림한계와사전사건을 [CASES](experiments/B-027-public-reference-robustness/CASES.md)에 기록했다. 실제lossless입력검사와CPU계약8개PASS;GPU는사전코드commit후순차실행한다. 개인자료는사용하지않는다.

### B-027 동물·사람 pair 실제 관측

동물/사람 각2출력을40step80forward와 final latent/17frame decode로 확보했다. 동물 두 참조는 어두운target 대신 옅은source 외형을 남겼고 R1에는 큰 문자 장식이 추가됐다. 사람 두 참조는 흰상의/분홍치마가 반영되지만 팔·얼굴·후반치마 형상 및 서명 모양 추가가 남았다. 기술PASS를 결합 편집 성공으로 올리지 않는다. 각pair6reference leaf만 변경/10보존이며 실제 noise/RNG도 확인했다. 차량 pair는 고정입력 그대로 진행 중이고 추가생성·수정은 없다. 전체정적근거는[VISUAL_REVIEW](experiments/B-027-public-reference-robustness/VISUAL_REVIEW.md)에 남긴다.


### B-027 종료: 공개 패널6출력과 실패 유형 확보

공개3과제×2참조의 실제6출력과 최종latent를 확보했다. 동물은 source 외형 잔존, 사람은 target 의상 반영과 형상 손상, 차량은 부분 외형 반영과 혼합 차체/조건별 그래픽 추가로 결합 편집 품질은 미입증이다. 기술21worker·240step480forward PASS와 시각 판정을 구분하고 temporal UNVERIFIED를 유지한다. [결과](experiments/B-027-public-reference-robustness/RESULTS.md), [다음 한 가설](experiments/B-027-public-reference-robustness/NEXT_DECISION.md). 다음은 원본 문맥과 ID 주입을 분리한 공식 VideoPainter 경로의 한정 비교 제안이며 설치·실행은 NOT_RUN이다. 신규 학습/모델/패키지/외부생성0, sampler6/6·재시도0, pre-worker오류3은 별도 보존한다. 공개자료0.776GiB와 mask-given/source_fps미확인 조건을 유지했다. 자체GPU worker는 종료했고 보호 서비스와 swap0를 확인했다. 개인사진 대기·추가 생성으로 자동 전환하지 않는다.

## 2026-10-26 통합 의뢰 착수: B-028 실측 후 생성 경로 개입 결정

시작 원격 `84b69080c8e4e9da858f784c11f7916b370a9d51`을 확인했다. [전체 수행 의뢰서](work_orders/20261026-B028-to-method-research.md)를 원문 그대로 보존한다. Spark의 B-028 실행 폴더·프로세스·실행 장부 부재를 확인했으므로 기존 B-028 PLAN의 최대6회부터 수행한다. 공개 개발 패널은 그대로이며 개인 촬영을 요구하지 않는다. B-027 실패와 B-026 선택적 보류는 보존한다. B-028 관측 뒤에만 공통 기준선 및 다음 방법/대조 PLAN을 확정한다. 전체8시간, 추가 방법 분기 최대8회 또는 미사용 검증 분기 최대2회 중 하나만 적용하며 재시도·학습·설치0이다. 현재 CPU 준비 / 신규 GPU0, 실제 시작 UTC01:37, 전체 deadline UTC09:37.

## 2026-10-26 B-028 종료와 B-029 사전 선택

B-028 6/6 sampler·6/6 decode, 각40step80forward와 final latent를 확보했다. 전체17장 정적 검토에서 외형 반응과 일부 장식 제거는 늘었으나 vehicle R1/R2는 원본 반대 방향의 큰 참조 자세, R2 새 문자 패널, human R2 회색 가림 형태가 남았다. [RESULTS](experiments/B-028-object-reference-normalization/RESULTS.md). 공동 목표 미충족, temporalUNVERIFIED이며 기술완료와 분리한다.

03:34 UTC 이후 분기A/B-029를 선택했다. 중요한 회귀 때문에 전6case 공통 기준선은 B-027이며 best-of 혼합0이다. [PLAN](experiments/B-029-spatial-image-conditioning/PLAN.md)과 [DECISION](experiments/B-029-spatial-image-conditioning/DECISION.md)에 generated query의 기존 이미지 attention 출력만 평균1 계수로 재가중하는 한 개입을 고정한다. METHOD6와 animalR1/vehicleR1 shifted CONTROL2,encoder0,학습/설치0. 현재 구현/CPU검사이며 새GPU0. 효과와 원인은 결과로 판단하고 추가 sweep을 하지 않는다.

### B-029 코드·지도 사전 고정

세 과제 support 지도와 두 shifted CONTROL을 실제 CPU에서 생성했다. source support와 시간 묶음·generated token grid[5,32,56]을 확인했고, CONTROL의 soft overlap은0~0.01459로 기록했다. CPU 계약10개와 compile 검사는 통과했으나 LSP transport가 닫혀 정적진단은 NOT_CLEAN이다. 최초 지도 클래스명 오류는 GPU 전에 수정·보존했다. [PREREGISTRATION](experiments/B-029-spatial-image-conditioning/PREREGISTRATION.json)에5consumer와 실제 코드·입력·noise·모델 계보를 고정한다. 이 기록 시점 B-029 GPU0이며 원격 반영 확인 후 고정8case를 순차 실행한다. 소형 검사와 시각 품질을 구분한다.

### B-029 동물 비교의 중간 관측

METHOD2와 CONTROL1의 실제40step80forward·17frame decode를 완료했다. 첫 실제 gate는 start1792/length8960/suffix2240, grid[5,32,56], img_x FP32를 유지했고40block×80호출을 확인했다. 두 METHOD 모두 어두운 target 대신 밝은 source 계열을 남겼다. R1은 BASE/CONTROL의 큰 장식을 더 작은 원형 장식으로 줄였지만 제거하지 못했고, R2는 source의 털·하네스·배치를 더 닮았다. [순차 정적 관측](experiments/B-029-spatial-image-conditioning/VISUAL_OBSERVATIONS.md). 동물 결합 목표는 실패이며 사람·차량은 고정 계획대로 진행 중이다. 위치 제어의 부분 반응을 전체 방법 성공으로 확대하지 않는다.

### B-029 사람 pair 중간 관측

METHOD R1/R2 각40step80forward와17frame 출력을 확보했다. 전체17장 정적 비교에서 R1의 치마 윤곽/테두리는 일부 정돈됐지만 원본 팔·다리 대응과 서명 모양이 남았다. R2는 크게 들린 치마·후기 얼굴/상체 가림과 잘못된 팔 배치가 지속되어 R1 개선이 참조 전반으로 이어지지 않았다. 실제 인물 일치·정확 관절·시간 품질은 미확인이다. 차량의 고정 METHOD2/CONTROL1을 진행하며 코드/설정은 바꾸지 않는다.

### B-029 차량 R1 중간 관측

METHOD R1의40step80forward·finite17frame과 전체 정적 비교를 확보했다. 은색 반응은 있으나 source Mini형 차체를 강하게 남기고, 하단 큰 차량 후면 그래픽이 원본 도로를 가린다. 원본의 큰 오른쪽 이동/후면 노출 변화는 남는다. 기존 베이스보다 결합 목표가 개선됐다고 판정하지 않는다. 차량 R2 및 사전 shifted CONTROL을 같은 설정으로 진행하며 전체종료/채택판정은 대기한다.

### B-029 종료: 고정 공간 가중은 채택하지 않음

2026-10-26 UTC06:15:19, METHOD6/CONTROL2 각40step80forward·finite17frame과 final latent를 확보했다. 전체17장 정적검토에서 animal target 교체 실패, human R1 일부 치마 정돈과 R2 형상 실패, vehicle R2 새 그래픽 회귀를 확인했다. animal CONTROL은 더 큰 배지지만 vehicle CONTROL은 METHOD의 큰 장식이 없어 위치 가설의 일관된 유용성은 미입증이다. [RESULTS](experiments/B-029-spatial-image-conditioning/RESULTS.md), [대조](experiments/B-029-spatial-image-conditioning/ABLATIONS.md). 기술 PASS를 품질 PASS로 바꾸지 않으며 temporalUNVERIFIED다.

독립 실행 근거 감사에서8case/24stage·정확한16leaf/noise계보·40×80gate·finallatent/decode·프로세스 종료를 확인했다. B029 encoder/학습/설치/재시도0, 전체 의뢰는미착수B0286+B0298=14회다. 다음 한 가설은 reference VAE joint 경로의 공간 전달 분리이며 미실행 제안이다. 추가seed/강도/학습/새backend를 실행하지 않는다. full/review-lite 검증은 별도 전달 기록에 남긴다.


## 2026-10-26 B-030 착수: 참조 경로 교차 진단

B028/B029 고정 설정의 NOT_ADOPTED와 CONTROL/비용/한계를 유지한다. 시작 원격 `230dad2ba9ffe5a02da3b408058e604e7dea757e`에서 [B030 PLAN](experiments/B-030-reference-path-crossover/PLAN.md)을 확인했다. 기존 B027 human/vehicle 대각4출력을 재사용하고 양 CFG clip_fea만 교차한4셀로 조건부 의존을 관측한다. VAE+mask와CLIP을 pose/identity로 미리 분리해 부르지 않는다. 현재 CPU 준비, 신규 sampler0/4·encoder0·학습0; 실제 시각 사전항목·코드·cache 계보를 고정한 뒤 순차 실행한다. 시작08:19:50UTC, deadline11:19:50UTC. 새 gate나 원인 확정이 아닌 다음 방법 표적의 증거를 얻는 범위다.

### B-030 종료: 행 경향과 조합 의존을 함께 확인

사전 고정 `23408cf5f54938a377ed3356e55216efdf0a1573` 원격 일치 후 신규4셀을 순차 실행했고 UTC09:38:04에 마지막 decode를 완료했다. 각40step80forward·finite final latent·17frame MP4, encoder/학습/설치/재시도0이다. 양 CFG CLIP2leaf만 변경하고14leaf·noise·RNG·scheduler·부모 캐시를 보존했다. 실행68.37분, CUDA peak33.847GiB, 최소 MemAvailable52.911GiB,swap/OOM0. 기술 PASS와 시각 판정을 구분한다.

전체17장 정적 비교에서 human R2 VAE+mask 행의 큰 치마가 두 CLIP 열에서 반복됐지만 원반/세로 접힘·얼굴 가림·수평 파편은 조합에 따라 달랐다. Vehicle 큰 별도 그림은Y11에만 있고 다른3셀에는 없어 단일 경로에 귀속할 수 없으며, 네 셀 모두 source형 차체 비율을 남겼다. [RESULTS](experiments/B-030-reference-path-crossover/RESULTS.md), [행렬 검토](experiments/B-030-reference-path-crossover/MATRIX_REVIEW.md). VAE=pose/CLIP=identity, encoder 단독 원인, 일반화·품질 개선은 미입증이고 temporalUNVERIFIED다.

다음 한 가설은 참조 VAE+mask 묶음의 공간 배치와 source 구조의 경쟁을 외형 전달과 분리할 수 있는지다. 사람의 행 경향은 검토 표적을 좁히는 근거이지 구체적 gate·layer·강도 선택의 증거는 아니다. 추가 zero-out·학습·모델·긴 영상은 실행하지 않고 종료했다. B028/B029 기각과 과거 실패는 보존한다.

## B-031 착수 — 원본 자세 정렬 앵커의 분해형 기준선 (2026-10-26)

사용자 승인으로 [B-031](experiments/B-031-source-aligned-edit-anchor/PLAN.md)을 실행한다. B030 PARTIAL/INCONCLUSIVE와 B028/B029 NOT_ADOPTED는 보존한다. encoder역할단정이나새gate대신 로컬Qwen이미지편집기로target외형+source첫자세를먼저만들고 적합한R1만기존SCAIL로전파한다. 개인추가사진요구없음. 상태PREPARING; 이미지최대6·조건부영상최대3·학습0,6시간에전송포함. [실행계약](experiments/B-031-source-aligned-edit-anchor/EXECUTION_CONTRACT.md). 원격9ca7606과실제Spark작업을확인해중복B031이없었고 기존환경은보존한다.

### B-031 이미지 단계 종료와 차량 한정 전이 착수

고정2e5e29d 이후 Qwen6회가 각각40step80forward·finite896×512로 완료됐다. 실제원본/참조/A0정적검토에서 animalR1은낮은참조자세, humanR1은뒤·옆모습과펼친치마를따라 ANCHOR_UNSUITABLE로영상생략했다. 두R2를대체하지않는다. VehicleR1은높은은색차체와source우향·위치를함께유지해수동A0support228.29초후영상후보로확정했다. [ANCHORS](experiments/B-031-source-aligned-edit-anchor/ANCHORS.md).

Qwen worker43.315분,480forward,CUDApeak55.933GiB,최소가용25.935GiB,swap0이다. `del/empty_cache`후잔존할당은UNKNOWN으로남기고실제프로세스종료·가용89.79GiB회복을확인했다. 영상입력·예산263ca977원격고정후vehicleR1만ENC→PROBE→S→D를진행한다. 참조6leaf만변경·10leaf보존,새T5/driving인코딩0. 영상품질은아직미관측이며시간품질UNVERIFIED다.

### B-031 종료: 앵커 실패와 영상 보호 장면 실패를 분리

이미지6회와 조건부 차량 영상1회(40step80forward, final latent 및17frame MP4)를 완료했다. 동물/사람 R1은 참조 자세 복사로 영상 NOT_RUN, R2 대체0이다. 차량은 target형 차체와 원본의 거친 회전 흐름을 유지했지만 A0에 없던 큰 차량 그래픽이 도로에 생겨 보호 장면 FAIL·결합 목표 FAIL이다. temporalUNVERIFIED, 일반 기준선 NOT_ADOPTED다. [RESULTS](experiments/B-031-source-aligned-edit-anchor/RESULTS.md), [COSTS](experiments/B-031-source-aligned-edit-anchor/COSTS.md). 다음 한 가설은 영상 생성 중 비대상 원본 문맥 보존이며 제안만 남긴다. 추가 모델·학습·seed·긴 영상은 실행하지 않았다.

## B-032 착수: 기존 raw의 CPU 원본 보존 합성

B031 동물/사람 앵커 자세 실패와 차량 영상의 도로 그래픽 FAIL을 보존한다. 생성 중 문맥 고정에 앞서 같은 차량 raw의 FIXED_ENVELOPE와 output-mask-assisted 합성 두 개를 만든다. 원본 밖 복사는 합성식의 성질이며 모델 성능으로 주장하지 않는다. 최신 a05b098에서 중복 실행 없음을 확인했고 사용자 승인 범위는 CPU90분·mask30분·GPU/생성/설치0이다. [고정계약](experiments/B-032-source-preserving-composite-baseline/EXECUTION_CONTRACT.md).

### B-032 CPU 비교 종료

사전1754536 뒤 고정 envelope와 output-mask-assisted 합성을 완료했다. source/A0 고정bbox [147,162,754,423), radius11/outer4px를 바꾸지 않았고 float/PNG endpoint exact·입력불변을 확인했다. 큰 도로 그래픽은 크게 줄었으나 FIXED의 긴 strip과 MASK의 뒤 바퀴 아래 조각은 남는다. 주요 차체·거친 회전은 보존, 완전 그래픽 제거FAIL·접촉/얇은경계UNCERTAIN·temporalUNVERIFIED. Agent mask345초/CPU runner3.90초, GPU·생성·설치0. [RESULTS](experiments/B-032-source-preserving-composite-baseline/RESULTS.md). 다음은 편집 내부의 source 문맥 제약 가설 하나이며 자동 실행하지 않는다. B031 원래FAIL은 보존한다.

## B-033 착수 — clean prediction 제약 대 마지막 latent 혼합

2026-10-27 사용자 통합 의뢰서를 원문 보존했다. 최신aaf40a9와 실제Spark상태에서 중복B033이없음을확인했다. B032저비용MASK_ASSISTED와기존mask불확실성을유지하고,동일영역에서마지막latent혼합과생성중clean제약을비교한다. 차량context축이며animal/human앞단자세FAIL은미해결이다. [PLAN](experiments/B-033-clean-prediction-constraint/PLAN.md). 신규sampler최대1/encode1/decode3,2시간,학습/설치0. 현재PREPARING이며실행·품질성공은아직아니다.

## 2026-10-27 B-033 종료 — 동일 후합성 이후의 국소 개선 PARTIAL

사전 계획 4eba8318, 코드/입력 고정 d893c618 이후 source encode1·decode3·sampler1을 실행했다. 실제40step/80forward/40finite clean constraints와 final latent 보존·D 완료를 확인했다. 기존 B031 조건/초기noise와 B032 source/target support/E를 보존했다. 저장 PNG의 E0 float 왕복 오차는 별도9eee71bc CPU export 보정으로 명시적 source byte 복사했으며 GPU 코드·mask는 변경하지 않았다.

전체17장 및 고정local0/8/16 정적 비교에서 STEP+동일RGBPOST는 B032/FINALONLY에 남은 바퀴 아래 적색·검정 조각을 작은 밝은 잔여로 줄였다. 높은 은색 target 외형과 거친 회전은 유지되고 뚜렷한 sourceMini 회귀는 미관찰이다. 접촉·그림자는 UNCERTAIN, temporal은 UNVERIFIED이며 완전 성공으로 합치지 않는다. GPU 단계 합1041.763초, S CUDApeak33.832GiB, minMemAvailable52.619GiB/swap0. 새 설치·학습·재시도0, 자체 worker 종료 및 기존 서비스 보존.

B032 저비용 기준선과 B031/과거 실패는 보존한다. 국소 이득의 후속 검증 후보지만 추가17분대 비용으로 기본 채택하지 않는다. 다음 한 가설은 같은 고정 제약이 다른 공개 사례에도 target 회귀 없이 국소 오염을 줄이는가이며 미실행이다. 결과·수식·조건·비용·재현을 [B-033 RESULTS](experiments/B-033-clean-prediction-constraint/RESULTS.md)에 연결한다. 이번 비교 이후 추가 작업을 예약하지 않았다.

## 2026-10-27 B-034 착수 — 고정 방법의 새 공개 두 과제 검증

시작 원격 d401b018과 실제 Spark의 중복 실행 부재를 확인했다. [전체 의뢰서](work_orders/20261027-B034-fixed-method-transfer-validation.md)는 제공 파일과 SHA256이 일치한다. B033 국소 PARTIAL/기본 채택 보류와 B032 저비용 기준선, B031 앵커/장면 실패를 보존한다. 새 source/target 두 조합을 생성 전에 고정하고 같은 clean_constraint와 support 규칙으로 BASE+RGB_POST, FINAL_ONLY+동일POST, STEP+동일POST를 비교한다. 기존 차량 잔여 제거를 위한 튜닝은 하지 않는다.

현재 입력/코드 준비이며 신규 이미지0/2·sampler0/4다. 새 모델/패키지/학습0, 앵커 부적합 시 해당 영상 NOT_RUN으로 남기고 사례를 대체하지 않는다. [PLAN](experiments/B-034-fixed-method-transfer-validation/PLAN.md), [결정](experiments/B-034-fixed-method-transfer-validation/DECISION.md). 실제 output-assisted 주석과 두-pass 비용, 방법의 국소 이득 및 target 회귀를 분리한다.

### B-034 앵커 단계 종료와 조건부 범위 축소

사전 입력 94c3341 이후 고정 두 이미지 모두40step/80forward로 생성했다. 차량은 source 전면 접근 배치와 어두운 클래식 외형을 유지해 ELIGIBLE, 인물은 source 측면 보행 대신 큰 뒷모습으로 바뀌어 ANCHOR_UNSUITABLE이다. 인물 영상은 전부 NOT_RUN이며 추가 사진/과제로 대체하지 않는다. Qwen 정상 종료·메모리 회복 후 9b821a7에 고정한 차량 영상 경로만 진행한다. 이 범위 축소는 방법 성능에 따른 선별이 아니라 사전 앵커 적합성 규칙이며, 인물 앞단 실패도 전체 시스템 결과에 포함한다. [ANCHORS](experiments/B-034-fixed-method-transfer-validation/ANCHORS.md).

### B-034 종료 — BASE latent 보존 / downstream BLOCKED

차량 ENC1과 BASE sampler1은 실제40step/80forward 및 finite FP32 final latent 저장을 완료했다. 종료 watchdog의 reason은 `other_service_work`, returncode0/MainPID0이다. 마지막 cgroup.procs가 빈 종료 시점이지만 발동 GPU PID/queue 응답은 기록되지 않아 원인 UNKNOWN으로 남겼다. 이후 자원 회복·허용 서비스만 남은 사실은 과거 이유를 무효화하지 않는다. predecessor gate를 완화하지 않고 BASE_D/CONTROL/STEP은 모두 NOT_RUN, sampler 재시도0이다.

이번 실제 이미지2/조건1/sampler1/영상decode0/학습0. GPU worker wall 합35.65분이며 주석·검토·패키징은 별도다. 인물 앞단 실패와 차량의 비교 미실행을 모두 보존하므로 B033 국소 개선의 전이·회귀는 판단하지 못했다. source MP4의 Chrome 색상 오류는 원본 불변의 PNG 기반 새 preview로 분리했고 temporalUNVERIFIED다. 자체 worker는 종료했다. 다음은 저장된 BASE latent를 활용한 제한된 decode 가능 여부 하나로 남기며, 이번에 가드 수정·추가 생성·후속 예약을 하지 않는다. [RESULTS](experiments/B-034-fixed-method-transfer-validation/RESULTS.md), [COSTS](experiments/B-034-fixed-method-transfer-validation/COSTS.md), [LATENT_REUSE](experiments/B-034-fixed-method-transfer-validation/LATENT_REUSE.md).

### 2026-10-27 B-034 RECOVERY_01 착수

저장된 BASE final latent만 소비하는 VAE-only 복구를 별도 승인 범위로 시작한다. 기존 BLOCKED_AT_BASE_TEARDOWN/other_service_work와 비강체 ANCHOR_UNSUITABLE은 보존한다. 과거 원인 확인과 현재 자원 안전을 분리하고 전역 predecessor 검사는 변경하지 않는다. 최대1decode·600초 worker, 총60분이며 새 sampler/encoder/학습/설치/재시도0이다. [복구 계획](experiments/B-034-fixed-method-transfer-validation/recovery/RECOVERY_PLAN.md). 현재 PREPARING이며 방법 비교는 NOT_RUN이다.

### B-034 RECOVERY_01 실행 종료 — decode PASS / 종료 감시 NOT_CLEAN

사전 계획 a4ffd286와 실행 코드 ac5aceef 이후 저장된 BASE final latent를 exact hash/FP32 shape·finite·40/80 계보로 검증했다. 새 live safety CLEAR에서 WanVAE만 1회 적재·decode해 finite `[3,17,512,896]` raw·PNG17장·24fps MP4를 확보했다. 신규 이미지/encoder/sampler/학습/설치/재시도0이다.

종료 시 queue0/0이지만 빈 cgroup와 GPU PID 관측 차이로 UNKNOWN_GPU_PID가 기록됐다. 같은 표본의 systemd MainPID와 GPU PID는 같았으며 최종 관측은 허용 서비스만 남고 자체 unit inactive였다. decode PASS와 종료 감시 NOT_CLEAN을 함께 보존하고 기존 other_service_work/과거 UNKNOWN을 소급 변경하지 않는다. 실제 decode6.645초·supervisor14.962초, CUDApeak8.908GiB·최소MemAvailable76.526GiB·swap0이다. [복구 결과](experiments/B-034-fixed-method-transfer-validation/recovery/RECOVERY_RESULTS.md).

차량 출력의 외형/동작/장면 검토는 복구 보고서에 분리하며 CONTROL/STEP 방법 비교는 계속 NOT_RUN이다. 비강체 ANCHOR_UNSUITABLE·B033 PARTIAL과 기존 B034 중단은 그대로다. 추가 생성·예약은 하지 않는다.

RECOVERY_01 정적 검토에서는 전17장 BASE가 target/A0의 클래식 노출 바퀴 차량을 유지하지 못하고 현대적인 닫힌 SUV/왜건형으로 돌아갔다. 원본의 거친 접근과 도로·산 배치는 대략 유지되지만 target 외형 FAIL, 세부 장면/접촉 UNCERTAIN, temporal UNVERIFIED다. 큰 별도 도로 그래픽은 이번 배열에서 미관찰이며 이를 전체 교체 성공으로 올리지 않는다. STEP 효과는 여전히 NOT_RUN이다.

### 2026-10-27 B-034 CONTINUATION_01 착수

RECOVERY_01의 decode PASS/종료 NOT_CLEAN 및 BASE target 외형 FAIL을 보존한다. 최신 원격00da734에서 사용자 승인된 종료 신원 최소 보완과 남은 CONTROL/STEP 비교를 시작한다. 동일 프로세스의 정상 종료만 bounded 관측하며 기존 queue/PID/memory 보호와 전역 predecessor는 유지한다. 같은 source·BASE에서 고정한 E/M으로 FINAL_ONLY decode1 및 STEP sampler1/decode1만 허용한다. BASE 재생성/재decode·encoder·학습0이다. [실행 amendment](experiments/B-034-fixed-method-transfer-validation/continuation/PLAN_AMENDMENT.md). 현재 PREPARING이며 영상 비교 성공은 미실행이다.
