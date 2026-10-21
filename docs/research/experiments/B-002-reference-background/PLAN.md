# B-002 의뢰서 — 참조 배경과 구조 조건의 역할을 분리한다

작성: 2026-10-22 · 상태: **PLANNED / NOT_RUN** · 계획 revision: 1

이 문서는 코딩 에이전트에게 전달할 실제 다음 실험 지시다. 문서 등록은 완료됐지만 이번 실험의 새 추론·학습이 실행됐다는 뜻은 아니다.

## 0. 목표와 이전 결과

B-001에서는 toy Flow Matching과 VACE LoRA의 학습 경로가 실행됐다고 보고됐다. LoRA는 도시 한 장면 복원을 학습했으며, 그 장면에서 복원이 개선됐다. Lab 춤은 adapter=null인 별도 baseline에서 원본의 직립 동작보다 참조 사진의 착석 자세와 실내 배경에 가까운 결과가 나왔다. 도시 LoRA를 Lab에 100회 학습한 실험이 아니다.

이번 질문은 하나다.

> **가중치·원본 구조·텍스트·초기 노이즈를 고정하고, 같은 Lab 사진의 배경만 대체하면 출력의 실내 배경 복사와 자세가 어떻게 달라지는가?**

가설: 참조의 배경 정보가 출력 배경에 영향을 줄 수 있다. 배경을 제거해도 앉은 자세는 참조에 남으므로, 그것만으로 춤 전이가 해결된다고 가정하지 않는다. 이는 frozen 모델에서의 입력 개입 실험이며 새 학습 방법이나 논문 기여의 검증이 아니다.

## 1. 트랙과 실행 범위

- B만 실행한다. A는 동결하고 기존 코드·자산·시도·선택을 보존한다.
- native imagegen, 외부 생성 API, A 생성물, 새 모델 다운로드를 사용하지 않는다.
- 기존 Wan2.1-VACE-1.3B와 기존에 고정한 DiffSynth-Studio commit/환경을 재사용한다.
- 학습 optimizer update는 **0회**. 도시 LoRA를 포함해 모든 adapter는 off/null이다.
- 신경망 분할·복원·보간 모델을 새로 추가하지 않는다. 사진 mask는 수동 또는 기존 비학습식 방법으로 만든다.
- DGX Spark에서 무거운 GPU 작업은 한 번에 하나. 기존 메모리 가드와 다른 작업을 존중한다.
- sudo, 재부팅, 클럭/swap/드라이버 변경, 무관한 프로세스 종료, 유료 GPU/API는 금지한다.
- 총 작업 시간 상한 **2시간**, 새 전체 inference 시도 **최대 5회**. 실패·재시도도 횟수에 포함한다. 자동 반복·seed 탐색 금지.
- 문서 작성이나 inference 전 encoder shape 확인을 별도 생성 성공으로 세지 않는다. 전체 sampler 실행 시도는 반드시 장부에 남긴다.

## 2. 이번 작업의 GitHub 기록은 필수다

먼저 `docs/research/README.md`, `CHARTER.md`, `ROADMAP.md`, `HISTORY.md`, `RECORDING_PROTOCOL.md`를 읽는다. 이번 PLAN을 현재 작업의 기준 문서로 삼는다.

초기 문서는 원격 main scaffold 기반의 문서 branch다. 로컬 B 실행 코드가 원격 main에 있다고 가정하지 마. 기존 실험 checkout을 보존하면서 별도 문서 worktree 또는 명시적인 문서 반입으로 사용한다. dirty checkout에서 강제 checkout/reset/clean을 하지 않는다.

실제 작업 시작 전:
- 기존 B 실행 폴더와 upstream commit·모델 경로를 확인한다. 이미 제공된 설정을 먼저 읽고 이름으로 새로운 폴더를 추측하지 않는다.
- 실행용 코드와 문서 branch의 관계, HEAD와 변경 파일을 기록한다.
- 계획과 resolved config를 결과 보기 전에 고정하고 커밋한다.
- root 또는 적절한 연구 범위의 AGENTS.md/CLAUDE.md에 RECORDING_PROTOCOL을 읽도록 짧은 규칙을 추가하되 기존 지시를 보존한다. 두 도구의 전역 설정은 바꾸지 않는다.

주요 단계 후와 종료 시 RESULTS/HISTORY/ROADMAP을 갱신한다. 연구용 branch에 commit/push하고 원격 반영을 확인한다. main 직접 변경·force push·자동 merge는 하지 않는다. push가 불가능하면 로컬 commit/patch와 `SYNC_PENDING`을 남기며 실험 결과를 잃지 않는다.

공개 저장소에는 개인 사진/영상/음원, private 경로·주소, 모델·adapter·cache·전체 로그를 올리지 않는다. 비민감 MD·코드·설정·요약·자산 별칭·해시만 명시적으로 올린다. 공개 문서의 링크는 실제 존재하는 것만 작성한다.

## 3. 생성 전 입력 경로 확인 — 새 영상을 만들기 전에 한다

기존 `lab-single-before.json`과 실제 pinned pipeline 코드를 읽고 다음을 확인한다.

1. 가중치와 checkpoint가 맞게 로드됐는가? VACE condition 경로가 실제 forward에 연결되는가? `vace_scale`의 resolved 값은 무엇인가?
2. condition 영상이 원본 f0~f16에서 만든 동일한 Canny인지, RGB/정규화 값 범위와 mask의 의미가 맞는가?
3. src mask의 white/black 의미와 reference 전처리에서의 foreground mask를 혼동하지 않았는가? 이번 reference mask는 배경을 바꾸는 도구이며, 생성용 video mask를 함께 바꾸라는 뜻이 아니다.
4. reference가 resize/pad/crop되는 실제 방식, latent shape·순서, 내부 시간 길이가 무엇인가?
5. 모든 adapter가 빠져 있는가? 이전 학습 프로세스의 LoRA가 in-memory에 남아 있지 않은가?
6. noise와 reference encoding이 RNG를 소비하는 순서, dtype/device, scheduler 설정이 무엇인가?

테스트 대상은 사전 학습 VACE의 저해상도 진단 설정이다. 공식 품질 상한을 재현했다고 부르지 않는다. 기존 도시 OFF 결과의 네온화 원인도 아직 확정하지 않는다.

실제 입력 계약 위반이 발견되면 그 근거를 기록하고 해당 설정으로 나머지 호출을 낭비하지 않는다. 조용히 mask·prompt·step을 고친 뒤 기존 결과와 한 실험으로 섞지 마. 실행 결함을 고치는 최소 패치는 별도 revision으로 남기고, 이번 5회 상한에서 비교 가능한 쌍을 구성할 수 없으면 BLOCKED/부분 완료로 종료한다. 전체 환경을 재구축하지 않는다.

## 4. 3조건 × 2seed 설계

| 조건 | reference | 목적 |
|---|---|---|
| P | 원본 춤 영상 첫 RGB 프레임 | source-reference 일치도의 진단군 |
| R | 기존 실제 Lab 사진 | 기존 baseline 재현/재사용 |
| R-bg | R과 같은 전경·자세·위치·크기에서 배경만 흰색으로 대체 | 배경 개입의 주 비교 |

주 비교는 **R vs R-bg**다. 한 조건에 대한 통제 효과를 보려는 목적이다.

### P 조건의 중요한 한계

기존 prompt는 검은 Lab를 요구하지만, source 첫 프레임은 다른 강아지다. P에서도 prompt를 동일하게 유지하므로 **P는 순수한 동일 개체 복원 positive control이 아니다.** 이를 결과 보고에서 명시한다. P 실패만으로 구조 경로가 고장났다고 단정하지 않는다. prompt까지 source에 맞춰 바꾼 진짜 재구성 대조군은 다른 실험이며 이번에 자동 추가하지 않는다.

### R-bg 제작

- 원래 Lab 사진의 EXIF 회전·RGB decoding을 R과 같은 방식으로 적용한다.
- Lab 픽셀과 위치·크기·앉은 자세를 유지한다. crop·rescale·upright 변환·얼굴/몸 편집은 금지한다.
- 사진의 배경만 사전 지정한 **RGB (255,255,255)**로 대체한다. 이는 공식 reference 전처리 가이드의 흰 배경 예를 따른 고정 개입이다. 결과를 보고 배경색을 고르지 않는다.
- 식: `R_bg = alpha * R + (1-alpha) * white`.
- alpha=1인 foreground interior의 RGB가 원래 decoded RGB와 같은지 확인한다. 저장은 lossless PNG를 사용한다.
- 경계의 soft-alpha가 바꾸는 픽셀, resize filtering의 경계 영향은 별도로 기록한다. 전처리 후까지 모든 경계 픽셀이 동일하다고 주장하지 않는다.
- 실제 mask·작업 시간·원본/교체 참조·최종 모델 입력을 로컬에 보존한다.
- R와 R-bg의 모델 입력 dimensions와 reference 장수는 같아야 한다. reference 존재 여부까지 바꾸는 실험으로 만들지 않는다.

배경 대체는 객체 주변 대비와 입력 분포도 바꾼다. 결과를 모델 내부의 특정 semantic background channel에 대한 인과 증명으로 확대하지 않는다.

## 5. 고정할 설정

기존 resolved config를 확인하고 다음을 고정한다.

- 모델·upstream commit·dtype·attention backend·device·offload/tile 설정.
- source f0~f16, 17프레임, 원본 24fps 시간축, 512×288.
- 동일 Canny 영상, 동일 생성 video mask, 동일 text embedding.
- 동일 prompt/negative prompt, sampling steps=20, CFG=5.0.
- 실제 resolved vace_scale, scheduler와 time shift 등 생략된 기본값도 명시한다.
- adapter=null, 학습 0회.
- seed는 **20261022 / 20261023**로 사전 고정한다.

기존 prompt의 `bright room`은 흰 스튜디오를 엄밀히 지정하지 않는다. 이 실험에서는 prompt를 더 좋게 바꾸지 말고 그대로 유지한다. 출력의 방 배경을 평가할 때 텍스트가 허용하는 범위와 실제 참조 장면의 특징 재현을 구분한다.

같은 seed의 P/R/R-bg에는 가능한 경우 **같은 initial noise 텐서**를 사용한다. shape/hash를 남기고, 실제 VAE reference encoding이나 전처리 RNG의 차이도 기록한다. 같은 seed라는 사실만으로 완전 결정론·같은 noise를 주장하지 않는다.

reference shape가 바뀌어 noise layout까지 달라지면 이를 숨기지 않는다. 의도한 통제 조건이 성립하도록 sampler 이전 입력을 확인하되, 지원되지 않는 API 인수를 만들어 넣지 않는다.

## 6. 실행 순서와 재사용

기존 R/seed20261022 결과가 모델·실행 코드·condition·prompt·resolved setting·noise까지 호환되는지 확인한다. 호환성이 확인되면 재사용으로 표시한다. path와 seed만 같다고 재사용하지 않는다.

재사용 가능할 때 권장 새 실행 순서:
1. R-bg / seed20261022
2. P / seed20261022
3. R / seed20261023
4. R-bg / seed20261023
5. P / seed20261023

재사용이 불가능하면 새 6회를 자동 허용하지 않는다. 최대 5회에서 R와 R-bg의 paired 비교를 우선한다:
1. R / seed20261022
2. R-bg / seed20261022
3. R / seed20261023
4. R-bg / seed20261023
5. P / seed20261022
P/둘째 seed는 NOT_RUN과 사유를 남긴다.

실패가 있으면 성공 샘플 수를 맞추려고 상한을 늘리지 않는다. 재시도도 최대 5회 안에 포함한다. 새로운 seed로 좋은 샘플을 찾지 않는다. sampler를 돌리지 않은 input 검사와 실제 시도 수를 구분한다.

초기 두 결과가 원하는 방향이 아니어도 입력 계약이 정상이라면 계획된 조건을 임의로 바꾸지 않는다. 장비 오류·OOM·시간 상한·명백한 입력 결함은 안전하게 중단한다. 기존 무관한 프로세스를 종료하지 않는다.

## 7. 평가 — 결과를 보기 전에 기록

raw 출력, 참조, 구조 condition, 원본을 같은 시각에 비교한다. 17프레임을 24fps로 표현하고 마지막 sample 시각과 container duration을 혼동하지 않는다. 반복 재생 끝→처음의 점프와 구간 내부 변화를 구분한다.

| 항목 | 기록할 것 |
|---|---|
| 참조 배경 반영 | 침대·커튼·창/방 배치 등의 구체적 재현 여부; 단순히 흰 픽셀 비율만 보지 않음 |
| 자세/구도 | 앉음 vs 직립, 주체 위치·크기, 보이는 발과 원본 동작 단계 |
| 개체 외형 | 검은 털·귀·주둥이·가슴과 실제 사진의 대응; 일반 검은 개와 정확한 개체 일치를 분리 |
| 구조 조건 | 큰 윤곽과 head/body 움직임이 원본과 연결되는가 |
| 형상 | 사지·얼굴·귀·목 붕괴와 원본 개체 잔존 |
| 시간 | 실제 재생 관찰 여부; 안 봤다면 UNVERIFIED |
| 자원 | 전체 process time, sampler time, allocator peak, OS MemAvailable 최소, 실패 원인 |

정량값을 쓰면 정의·단위·분모·관측 방법을 먼저 적는다. cross-identity 출력에 PSNR을 정답 점수처럼 쓰지 않는다. static 출력의 낮은 flicker를 높은 동작 품질로 해석하지 않는다. 사람 얼굴용 identity metric을 동물 정답 판정기로 사용하지 않는다.

가능하면 같은 seed의 R/R-bg를 이름을 가린 순서로 먼저 보고 관측을 적고, 이후 조건을 공개한다. 두 seed와 한 원본/한 참조는 탐색용이다. 통계적 유의성·전체 반려동물 일반화를 주장하지 않는다.

## 8. 이번 이론 학습 자료

`docs/research/lessons/B-002-conditioning.md`에 아래를 한국어로 남긴다. 수식·텐서 shape·실제 고정 코드 함수·이번 관측이 연결되어야 한다. 단순 용어사전이나 논문 초록 요약으로 채우지 않는다.

### 8.1 조건부 생성과 개입

`Y = G_theta(epsilon; S,R,T,M,lambda)`로 표현하고 각 항을 정의한다. theta, S, T, M, lambda, epsilon을 고정한 R/R-bg가 무엇을 비교하는지 설명한다. reference 전체에 포함된 외모·자세·배경을 모델이 자동으로 분리한다고 가정할 수 없는 이유를 설명한다.

관측 함수 q에 대해 같은 seed의 차이 `Delta_s = q(Y_bg,s) - q(Y_R,s)`를 정의할 수 있다. q가 수동 ordinal rubric이면 정확한 물리량처럼 계산하지 않는다. 두 개의 paired 관측이 모델 전체 인과 구조나 보편적 평균 효과를 추정하는 것은 아님을 설명한다.

### 8.2 Flow Matching 복습과 조건의 영향

교육용 노이즈→데이터 규약:
`X_t=(1-t)X_0+tX_1`, `U=X_1-X_0`, `v*(x,t,c)=E[U|X_t=x,t,c]`.

제곱오차의 최적 예측이 조건부 기대값이 되는 이유를 짧게 유도한다. 조건 c가 바뀌면 같은 x,t에서도 예측 방향과 적분 경로가 달라질 수 있다. 실제 Wan scheduler의 sigma 방향·부호와 target은 pinned 코드로 확인하고 이 식을 그대로 대입하지 않는다.

선택 설명: 작은 조건 변화에서 `d(delta z)/dt ≈ (partial v/partial z) delta z + (partial v/partial c) delta c`로 경로 차이를 생각할 수 있다. 배경 대체는 큰 입력 변화일 수 있으므로 이 선형화가 실제 효과를 정량 예측한다고 주장하지 않는다. 새 gradient/Jacobian 실험을 추가 실행할 필요는 없다.

### 8.3 실제 VACE 입력 경로

reference/condition/mask의 전처리→VAE latent→context adapter→DiT의 연결을 pinned 함수와 실제 shape로 설명한다. inactive/reactive/mask/reference의 실제 배치는 upstream 코드에서 확인한다. video time과 diffusion time을 구분한다.

CFG의 conditional/unconditional branch에 어떤 조건이 실제로 남는지도 확인한다. reference까지 무조건 제거된다고 가정하지 않는다. vace_scale과 CFG를 같은 조절값으로 설명하지 않는다. 이번 실험에서 두 값은 변경하지 않는다.

학습 질문 3개와 별도 해설:
1. 모델 가중치가 고정인데 왜 출력이 달라지는가?
2. 같은 seed와 같은 initial noise는 언제 다를 수 있는가?
3. 배경 제거로 침대가 사라져도, 춤을 배웠다고 말할 수 없는 이유는 무엇인가?

질문은 결과 문서에 남기고 실행을 중단하는 승인 절차로 만들지 않는다.

## 9. 결과 해석과 다음 한 가지 결정

- 방 배경이 줄고 착석은 유지: 배경 개입의 부분적 효과. 동작 전이 성공 아님.
- R-bg에서 자세도 달라짐: 이 reference intervention에서의 관찰. 배경 픽셀만이 자세를 독립적으로 결정한다는 증거 아님.
- P에서 구조가 좋아짐: reference/source 정합성이 조건 경쟁에 영향을 줄 가능성. 텍스트와 개체가 충돌하는 진단군이라는 제한 유지.
- P도 실패: 전처리·작은 설정·프롬프트 충돌·조건 수용의 후보를 남긴다. 즉시 모델 무능력으로 단정하지 않는다.
- 입력 계약 결함: 결과의 의미를 제한하고 수정 전후를 섞지 않는다.

한 번 비교하면 종료한다. 새 학습·새 모델·추가 scale sweep·새 seed·prompt 수정으로 자동 확장하지 않는다. 다음 실험 하나를 이유와 함께 제안한다.

## 10. 제출·기록·동기화

로컬 새 실험 폴더에 다음을 남긴다.
- run_manifest.jsonl, resolved configs, hashes, resource_metrics.csv
- R/R-bg/mask와 reference foreground 보존 검사
- 모든 실제 출력 MP4와 source/condition/reference 비교 시트
- 재현 script, REPRODUCE.md, 실제 사용 commit와 private 경로 매핑
- 간결한 REPORT_KO.md와 이론 설명

GitHub에는 공개 가능한 다음만 기록한다.
- 이번 PLAN과 실제 변경 amendment
- `experiments/B-002-reference-background/RESULTS.md`
- `lessons/B-002-conditioning.md`
- HISTORY의 실행·실패·결론과 ROADMAP의 현재 상태
- 필요한 비민감 연구 script와 placeholder 경로 config, 요약 지표·해시

기본 모델·사진·미공개 동영상·집 내부·음원·비밀키·절대 개인 경로·cache는 push하지 않는다. 참조 이미지는 이번 의뢰로 공개 허가된 것이 아니다.

코드/문서 commit 후 연구 branch로 push하고 remote SHA를 확인한다. push가 막히면 로컬 commit/patch를 유지하며 SYNC_PENDING으로 보고한다. main merge와 force push는 하지 않는다.

작업 종료 시 작은 ZIP 하나를 실제 실행 호스트의 `/tmp/`에 만들고 CRC·내부 manifest 해시를 검사한다. 실행자가 검토할 로컬 ZIP에는 필요한 입력·영상이 들어갈 수 있으나 이 ZIP을 공개 GitHub에 올리지는 않는다. 큰 모델·adapter·optimizer·기존 전체 실험은 다시 담지 않는다. 목표 100MB 이하. Mac/Spark 어느 호스트에 있는지와 실제 전송 여부를 명시한다.

최종 답변에는 반드시 다음을 포함한다.
1. 원래 질문, 실제 완료/실패/재사용/미실행 run 수
2. 주 비교에서 관측한 변화와 아직 모르는 것
3. 추론 시간·메모리와 신규 학습 0회 확인
4. 다음 연구 질문 하나
5. GitHub branch·commit SHA·문서 위치·실제 push 확인 또는 SYNC_PENDING
6. ZIP의 실제 호스트·경로·크기·SHA256

## 11. 공식 출처와 기존 자료

아래 공식 자료는 개념·입력 의미 확인용이다. 실행은 기존에 고정한 commit을 사용하며, 최신 main으로 자동 업그레이드하지 않는다.

- VACE 논문: https://arxiv.org/abs/2503.07598
- VACE 입력 가이드: https://github.com/ali-vilab/VACE/blob/main/UserGuide.md
- DiffSynth-Studio pipeline: https://github.com/modelscope/DiffSynth-Studio/blob/main/diffsynth/pipelines/wan_video.py
- Flow Matching 논문: https://arxiv.org/abs/2210.02747

기존 로컬 근거: B-001 아침 보고서·실험 설정·raw 출력·noise 기록·고정 upstream. 이전 `NEXT_CONDITION_ABLATION_KO.md`는 본 PLAN으로 구체화되며, P의 의미와 흰 배경 처리 및 GitHub 기록 요구는 본 문서를 따른다.

## 실행 지시

계획만 답하고 끝내지 말고, 기록 확인→무생성 입력 점검→참조 준비→최대 5회 통제 비교→이론 해설→결과·히스토리·로드맵 commit/push→검토 ZIP까지 진행한다. 이 범위 안에서는 중간 질문을 기다리지 않는다. 권한·장비·입력 문제가 있으면 위험한 우회 없이 가능한 독립 작업을 수행하고 미완료를 정확히 보고한다.
