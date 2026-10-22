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
