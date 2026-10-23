# B-012 — 명확한 상대 동작 구간에서 동적/정적 driving 비교

작성: 2026-10-23 · parent: B-011 · 상태: **PLANNED / NOT_RUN**

이 문서는 다음 실행의 제안이다. 등록만으로 GPU 작업을 수행하거나 실행을 승인한 것은 아니다. 사용자가 이 계획을 실행 담당자에게 전달해 수행을 지시할 때 아래 범위를 적용한다. B-011의 사용1회와 B-010의 사용0회를 보존한다.

## 0. 방향과 검토 근거

목표는 DGX Spark의 로컬 이미지·영상 생성 모델에서 아키텍처·조건화·학습 메커니즘을 이해하고 개선하는 것이다. 상용급 품질은 장기 응용 목표이고, 한 번의 자기 재현/실행 성공을 논문 기여나 일반화로 간주하지 않는다. A(native imagegen-only MCP)는 동결하고 B에는 외부 생성 API나 A의 생성물을 넣지 않는다.

검토 기준 B-011 commit: `10d6c3a220b8212957c26a9684d0627ab4eb8927`. RESULTS, OUTPUT_EVALUATION, PREREG_EVALUATION 및 source 관측 집계 코드를 원격에서 읽었다. 공개 기록의 E_copy=16.5407px, E_gen=3.5212px는 같은 f0를 공유한 20변위의 수동 판독 요약이다. 출력 좌표의 오차는 NOT_CALIBRATED, 같은 관측자가 원본을 본 뒤 출력 좌표를 판독했고 관절 운동은 INCONCLUSIVE다. 이를 개선율·유의성·독립20표본으로 해석하지 않는다. 조건/정밀한 motion 동등성은 새로 재실행하지 않았다.

업로드 B-011 ZIP은 이번 검토 세션에서 container와 Python 모두 ClientError로 읽기 실패했다. CRC/290개 파일·개인 영상·양호스트 일치를 독립 검증하지 않았다. 사용자 보고 SHA `95da41abe97f069d345c914b317325014d8cdbfce514cda7db96b3fac60e97b0`는 보고값이다.

B-011은 정적 픽셀 복사보다 원본의 화면 변화에 대응하는 탐색적 근거를 얻었지만, 같은 모델에 정적인 driving을 넣어 생성한 대조군이 없다. reference/text/prior만으로 비슷한 움직임이 나오는 가능성을 분리하지 못한다. 다음은 새 구간을 원본만으로 짧게 선정한 뒤 **고정 reference/text/noise에서 driving RGB+mask의 시간 변화 유무를 비교**한다. 전체 움직임 크기보다 정확한 방향·이벤트 순서를 본다.

## 1. 범위·예산

- 기존 정상 SCAIL2 체크포인트/upstream/FlashAttention/mixed loader, tiny CUDA 선행 연산과 anchor, P→PROBE→S→D 분리·최종 latent 저장 경로를 유지한다. 새 CUDA/직렬화 감사·범용 MCP/framework는 만들지 않는다.
- 새로운 대형 모델/데이터 다운로드0, 학습·LoRA0, imagegen·외부 생성0. 원본은 이미 승인된 로컬 자료만 사용한다.
- 전체 최대4시간. source-only 후보 선정 최대45분, 신규 mask 준비가 필요하면 CPU 국소 작업 최대30분. 후보와 예산을 무한 확대하지 않는다.
- **신규 full sampler 최대2회(실패·중단 포함): MOV 1회, STILL 1회**. 각 조건의 P/PROBE/S/D도 각각 최대1회다. 새 seed·재시도0. 첫 생성이 품질상 나쁘다는 이유로 둘째 대조군을 생략하지 않는다. 입력 불일치·안전/자원 실패일 때만 후속을 중지한다.
- 기존24GiB 시스템 headroom/swap0/cgroup/타 작업 보호 유지. 다른 프로세스 종료·sudo·driver·clock·swap 변경·drop_caches·가드 완화 금지. GPU-heavy 작업은 순차1개.
- Lab/IG 전이 재실행, 15초 전체, 두 개체, low-pass guidance, SR, 보간, 양자화, step/CFG 탐색은 이번 범위 밖이다.

## 2. 원본만 보고 구간 하나 선정

기존 원본 전체의 실제 경로·fps·해시·프레임 범위를 기존 manifest로 확인한다. 전체 원본이 없다면 있다고 가정하지 않는다. 기존 로컬 경로 밖 개인 파일을 광범위 검색하지 않는다.

원본을 소형 시간축 시트로 살펴보고, **최대3개의 연속17프레임 후보**를 사전에 기록한다. 원본 native24fps를 유지하고 frame skip·fps 변경·속도 조절·보간으로 움직임을 키우지 않는다. RGB 전처리512×896과 동일 crop 기준을 고정한다. 확대·crop된 자료를 새 고해상도 촬영이라고 부르지 않는다.

선정 우선순위: 단일 개체 식별 가능, 컷 전환/심한 가림/급격한 카메라 변화 없음, 피사체 전체 이동만이 아닌 앞발-머리 또는 머리-몸통의 가시적 상대 변화, 주요 부위가 crop 안에 있음. 극단적인 회전·킥·복잡한 두 개체 장면부터 시작하지 않는다. 조건을 충족한 후보 중 시간상 가장 이른 구간을 선택하고 다른 후보의 제외 이유를 기록한다. 결과를 본 뒤 더 좋은 구간으로 바꾸지 않는다.

출력 생성 전에 source만으로 세 시점 이상의 관측 가능한 이벤트를 적는다. 예: 앞발이 주둥이보다 아래→비슷한 높이→다시 아래, 머리의 몸통 대비 방향 변화. 실제로 보이는 내용만 쓴다. 해부학적 관절/지면 하중을 추측하지 않는다. 기존 저해상도 좌표의 반복 재주석이나 완벽한 관절 ground truth 구축을 요구하지 않는다.

명확한 정성 이벤트는 있으나 정확한 좌표 오차를 보정하지 못했다면 탐색 실행을 허용하고 정량 항목은 UNCERTAIN으로 둔다. 세 후보 모두 순수 정지/글로벌 이동뿐이거나 필요한 원본·mask를 마련할 수 없으면 SOURCE_NOT_READY로 종료한다. 이를 모델 실패로 기록하지 않는다. 33프레임 확장이나 다른 영상 수집을 자동 시작하지 않는다.

## 3. 비교 조건 — 정적 출력과 정적 입력을 구분

공통 reference R은 **선정 구간의 첫 processed RGB 프레임**이다. reference mask는 그 f0의 단일 RED 개체 support와 WHITE 배경이다. prompt는 해당 실제 개체·장면·관측 동작을 설명하는 하나의 문장/문단을 GPU 실행 전에 고정하고 두 조건에 동일하게 넣는다. 검은 Lab/침실로 남아 있는 과거 prompt를 쓰지 않는다. text만으로도 움직임이 생길 수 있으므로 이번은 같은 text 아래 추가 driving 정보의 기여를 본다.

| 항목 | driving RGB | driving mask | 생성 |
|---|---|---|---|
| MOV | 선택한17장 순서 그대로 | 대응하는17장 그대로 | 1회 |
| STILL | 선택한f0를17장 반복 | f0 mask를17장 반복 | 1회 |
| STATIC COPY | 생성 없음, source f0 반복 출력 | 평가 표시만 | CPU 인코딩 |
| SOURCE | 선택한 원본17장 | 평가 표시만 | 없음 |

**STATIC COPY는 파일을 복제한 영상이고, STILL은 정적인 driving을 받은 모델 생성 영상이다. 둘은 다른 대조군이다.** STILL의 mask도 정지시켜 동작이 mask로 누출되지 않게 한다. 개입은 driving RGB+mask의 공동 시간 정보이지 RGB만의 효과나 branch-off가 아니다. reference/text가 동일하므로 STILL도 움직일 수 있고, 정지해야 성공이라는 기준은 없다.

기존 mask가 없다면 read-only source를 보고 한 개체의 support만 새 CPU mask로 제한 준비한다. 새 segmentation 가중치 설치/새 GPU 추론 금지. MOV의 mask f0를 STILL과 reference support에 동일 적용하고 rgb/mask 시간·공간 정합을 검증한다. 얇은 경계의 불확실성은 보존한다.

## 4. 실제 조건 통제와 실행

고정값: seed20261022, UniPC40step, shift3, CFG5, negative empty, replace_flag=False, history=None,17프레임24fps, W512/H896, LoRA/enhancer OFF. 두 조건에서 같은 디코딩/정밀도/안전 정책을 사용한다. 같은 seed만으로 noise 동일성을 주장하지 않고 실제 noise bytes/shape 및 generator state·timesteps/sigmas를 확인한다.

P는 두 조건을 실제 RGB 비디오로 각각 인코딩한다. STILL video latent를 MOV latent 첫 temporal slice 반복으로 대체하지 않는다. VAE의 시간 압축·패딩·비선형성 때문에 동일하다는 보장이 없다.

현재16leaf 계약에서 예상 변경은 양 CFG의 pose_latents와 driving_masks, 합계4개다. 나머지12개(reference latent/mask/CLIP, text/negative, noise/RNG/schedule)는 같은 뜻·shape/dtype/device를 유지한다. 변경4개가 실제로 동일한 값으로 우연히 인코딩되면 조작 불충분을 기록하고 모델의 무반응으로 해석하지 않는다. noise/RNG/schedule/mask-support 계약은 exact; 같은 encoder 입력의 허용 floating tolerance는 결과 전에 명시하고 실제 exact 여부도 보고한다.

입력·기대 변경 집합과 실행 config를 생성 전에 commit한다. B-009의 mask-only 검사나 B-011의7변경/9보존 검사를 그대로 유지해 막거나 그냥 삭제하지 않는다. 서로 다른 seed/정밀도/프로세스 캐시가 섞이지 않도록 각 조건의 새 manifest를 사용한다.

P 캐시를 저장하고 PROBE→S→D를 정상 경로로 진행한다. final latent는 decode 전에 원자적으로 보존한다. 각40step·80forward를 실제로 기록하고, D 실패 시 sampler 재실행 금지. 기존 17프레임 H/B008~011 출력은 맥락만으로 보존하며 새 구간의 동등 대조군으로 재사용하지 않는다.

## 5. 평가: 움직임 양이 아니라 목표와의 대응

SOURCE / STATIC COPY / MOV output / STILL output을 같은24fps·동일 sample 시각으로 비교한다. 전체17장과 사전 이벤트 시점을 포함한다. 정지 영상의 낮은 flicker나 단순 직립·선명함을 동작 수용으로 올리지 않는다.

사전 기록한 방향·순서·이벤트 시점·머리/앞발 상대 배치를 주 평가로 사용한다. 값으로 읽을 수 있으면 raw displacement 및 전체 이동/scale과 구분한 상대량을 같이 남긴다. 예시 u_t,j=(p_t,j-c_t)/s_t는 관측 가능한 표면 기준점 c와 고정 정의의 body scale s가 있을 때만 보조로 사용한다. 이는 pose 정답이 아니며, source에 맞춰 출력별로 warp/최적 정렬/시간 지연을 찾는 절차를 금지한다. 원좌표도 함께 공개 가능한 요약으로 보존한다.

출력 판독은 가능하면 A/B 조건명을 숨긴 동일 크기 패널로 수행하되 source를 본 동일 에이전트의 판독을 독립 인간/완전 blind라고 주장하지 않는다. 모호한 발끝은 UNKNOWN/UNCERTAIN, 누락/붕괴는 coverage와 함께 표시한다. 오차보정 전 개선율·통계적 유의성/임의 gain은 만들지 않는다. 17프레임이나 여러 점을 독립적인 실험 반복으로 세지 않는다.

해석: MOV가 STILL과 STATIC COPY보다 사전 source 이벤트에 명확히 가까우면 **이 입력에서 동적 driving pair가 유용한 추가 정보를 줬다는 탐색적 근거**다. MOV/STILL이 단지 다르거나 MOV의 움직임이 크기만 하면 유용한 동작 제어 증거가 아니다. 둘이 비슷하다고 모든 조건에서 driving을 무시한다고 단정하지 않는다. 정확한 model alignment/조건의 분포 효과도 남는다. 같은 개체 자기 재현이므로 Lab의 cross-identity/체형/일반화는 NOT_RUN이다.

실제 연속 재생을 관찰한 주체·시간·검토 항목이 없으면 temporal=UNVERIFIED 유지. 재생 이벤트/ffmpeg decode나 contact sheet는 사람의 연속 검수와 다르다. 연구자는 실시간 재생·프레임 이동으로 볼 수 있는 기존 review page를 재사용한다.

## 6. 이론·메커니즘과 다음 결정

한국어 lessons/B-012-driving-information.md에 다음을 연결한다.
- c=(c_ref,c_drive,c_mask,c_text), v_theta(z_tau,tau,c)에서 driving pair 개입을 정의. diffusion noise time tau와 video frame time t를 구분.
- 정적 copy는 학습 모델 대조가 아닌 영(0) 움직임 기준. MOV와 STILL은 같은 생성 모델·reference/text/noise 아래 입력 개입이다.
- ref/text가 같아도 image prior에서 움직임이 나올 수 있어 unconditional==static이나 STILL==정지를 가정할 수 없는 이유.
- 3D VAE로 시간 압축된 driving 조건과 두 CFG branch에 공유되는 시각 조건. 실제 pinned code의 텐서와 trace로 확인, attention map만으로 causal proof 주장 금지.
- 탐색 pair 한 번, 통제된 개입, 통계적 일반화·논문 독창성의 서로 다른 증거 수준.

결과 후 다음 연구 하나만 제안한다. MOV의 유용한 제어가 관측되면 같은 명확 구간의 Lab cross-identity를 검토한다. 동적 pair의 효과가 불명확하면 데이터/조건 경로 문제와 시간·공간 주입 위치를 점검할 가설 하나를 고른다. 이번에 reference low-pass/adapter/LoRA/SR를 함께 실행하지 않는다. source-only 검사 반복이나 감사 문서 양을 성과로 삼지 않는다.

## 7. GitHub·보존·제출

시작 전 CHARTER/ROADMAP/HISTORY/RECORDING_PROTOCOL, B-011 결과·코드를 읽고 작업 목표·시간축·선정 기준·의도된 조건 차이를 고정한다. 연구 프로그램 별도 문서 branch는 있는 경우 읽되 활성 환경·실행 코드에 자동 merge하지 않는다. 본 PLAN은 제안이며 실제 GPU 실행 전 입력 확정 amendment와 코드/config를 기록한다.

HISTORY와 ROADMAP에 B-011의 기술적 결과와 불확실성을 보존하고 B-012의 방향·선정·실행 상태를 연결한다. 종료 후 RESULTS/REPRODUCE/조건비교/자원/이론/다음 결정을 비민감 코드와 함께 commit/push하고 remote SHA 확인한다. push 실패는 SYNC_PENDING; main/force push/reset/clean 금지.

개인 사진·영상·mask·좌표·조건cache·latent·weights·private path·secret은 공개하지 않는다. 비공개 ZIP에 두 결과(실패도 포함), source/copy 비교, final latent·규약, 코드·실측·보고서를 포함하고 대형weights는 제외한다. /tmp/의 실제 Mac/Spark 위치와 전송/CRC/manifest/SHA를 검증한다. 최종 보고는 선택 구간의 관측 이벤트, 실제2조건 결과, 한계, 다음 한 가지를 우선하며 자체 프로세스 종료를 확인한다.
