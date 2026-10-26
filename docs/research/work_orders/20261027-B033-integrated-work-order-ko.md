# B-033 제안 — 생성 중 원본의 clean-latent 예측 제약과 마지막 혼합 대조

작성: 2026-10-27. 상태: **PROPOSED / NOT_RUN**.
저장소 `hyunlord/make-meme`, 연구 브랜치 `docs/b-research-20261022`.
검토한 결과 기준 커밋: `aaf40a92cdc2c85259ad239ab455b2f3124e9b98`.
이 문서는 다음 수행 의뢰의 제안이다. 문서 작성만으로 GPU 실행·모델 변경·학습을 수행한 것은 아니다.

## 0. 상위 목표와 지금 바꿀 것

다양한 영상 V·참조 이미지 R·편집 지시 P에서 참조 대상의 외형과 원본 동작·장면을 함께 보존하고, 이를 개인 DGX Spark에서 실행 가능한 품질·비용으로 구현한다. 특정 반려견·특정 모델에 연구를 종속시키지 않는다. A의 native imagegen 트랙은 독립 보존한다.

B-031의 동물·사람 앵커 자세 실패는 미해결이며 영상 NOT_RUN을 유지한다. 차량에서는 참조형 차체와 거친 동작을 얻었지만 보호 장면에 큰 그래픽이 생겼다. B-032의 단순 합성은 대부분을 없앴지만 작은 조각·접촉·경계 불확실성을 남겼다.

이번 질문은 하나다.

> **같은 source, 앵커, 입력 조건, 초기 noise와 같은 편집 영역을 두고, 마지막에만 원본을 섞는 것보다 생성 과정에서 원본의 알려진 배경을 제약하는 것이 편집 내부·접촉 주변 품질에 도움이 되는가?**

새 reference gate·RoPE·학습·Qwen 이미지 생성으로 돌아가지 않는다. 가장 단순한 생성 중 제약을, 값싼 출력 합성과 마지막 latent 혼합 모두에 비교한다. 합성·known-region conditioning은 기존 방법 계열이며, 이번 이식을 새 논문 알고리즘으로 부르지 않는다.

## 1. 결과 해석의 출발점

B-032의 small wedge는 실제 차체 내부라고 확정된 것이 아니다. 공개 SUPPORTS는 수동 target polygon의 얇은 구조·접촉부 오차가 최대 약 15px까지 있을 수 있다고 기록한다. E는 source와 target union에 radius11 dilation과 4px feather를 적용했다.

따라서 잔여 오염이 **합성에서 E=1인 영역**에 있다는 것과, **실제 target 본체 내부**라는 것은 다르다. 부정확한 boundary/그림자와 정책 margin도 원인 후보다. 이를 보고 마스크를 좁혀 조각을 지우면 이번 방법 비교가 바뀐다.

이번에는 B-032 mask와 정책을 동결한다. 기존 결과를 보고 만든 출력 보조 마스크라는 사실, 5.75분 주석 비용과 불확실성을 남긴다. 이 실험은 기존 출력에 의존하는 mask-assisted 진단이며 자동 편집·새 입력 일반화 평가가 아니다.

## 2. 기존 입력과 결과 재사용

최신 HEAD·실제 worker·완료 상태를 먼저 확인한다. 이미 B-033이 존재하면 번호를 덮어쓰거나 중복 실행하지 않는다. 다른 GPU 작업을 끊지 않는다.

다음을 읽는다.
- CHARTER, RESEARCH_V2_SOURCE_PRESERVING_EDITING, HISTORY, ROADMAP
- B-031 RESULTS/ANCHORS/STAGES 및 실제 vehicle_R1 조건
- B-032 RESULTS/SUPPORTS/EXECUTION_CONTRACT와 compositor 코드
- pinned SCAIL `78fe19576bb06be96c2375e088574a262a300edb`
- `wan/utils/fm_solvers_unipc.py`의 `convert_model_output`, `step`, `multistep_uni_p_bh_update`

기존 vehicle_R1만 사용한다. 원본 sequence/frame index는 B-027/B-031 실제 manifest에서 확인한다. 개인 Lab 자연동작 영상과 섞지 않는다.

유지할 것:
- source lossless 전처리 RGB 17장, 가로896×세로512
- B-031의 A0에서 구성한 R_star·semantic mask·reference VAE/CLIP
- source driving RGB/mask, positive/negative text, 실제 초기 noise·RNG·scheduler 배열
- replacement=True, history/additional_ref=None
- LoRA/ALG/B029 gate/manualRoPE OFF
- UniPC40, shift3, CFG5, 기존 정밀도·loader·FlashAttention
- source_fps=null, preview24fps, timebase_assumed=true

기존 B-031 raw/final latent 및 B-032 두 합성 결과는 재사용한다. 기존 raw·조건·mask·영상·checkpoint를 덮어쓰지 않는다. compact에 raw가 없으면 이미 보존한 로컬 full 산출물에서 읽는다. 새 추론으로 복원하지 않는다.

## 3. 비교 구성 — full sampler는 한 번만

| 이름 | 구성 | 신규 full sampler |
|---|---|---:|
| RAW_BASE | 기존 B-031 생성 영상 | 0 |
| RGB_POST | 기존 B-032 MASK_ASSISTED | 0 |
| FINAL_LATENT_ONLY | 기존 B-031 final latent에서만 원본 latent를 같은 지도로 혼합 후 decode | 0 |
| STEP_CONSTRAINED | 매 sampling step의 clean prediction에 원본 latent 제약을 적용 | 최대1 |

FINAL_LATENT_ONLY와 STEP_CONSTRAINED는 각각 raw decode와 **동일한 B-032 E를 사용한 RGB_POST 버전**을 함께 만든다. 새 합성 코드를 만들지 말고 기존 CPU compositor를 재사용한다.

주 비교는 다음 두 가지다.
1. STEP_CONSTRAINED raw 대 FINAL_LATENT_ONLY raw: 마지막 latent 교체 이상의 효과가 있는가?
2. STEP_CONSTRAINED+RGB_POST 대 FINAL_LATENT_ONLY+RGB_POST 대 B-032 RGB_POST: 원거리 배경을 똑같이 복원해도 편집 내부·경계에서 이득이 남는가?

새 방법이 단순히 편집 외부에서 원본을 복사했다는 이유로 성공하지 않는다. 대상 외형·회전이 source 차량으로 되돌아가면 실패다.

## 4. 원본 latent를 정확한 해상도로 준비

`z_src = official_WanVAE.encode(source_full_resolution)`를 기존 wrapper의 normalization과 mean/std 규약으로 최대1회 계산한다. 같은 입력·스케일링의 기존 full-resolution latent가 실제로 있으면 재사용한다.

필요 shape는 generated model space와 같은 `[16,5,64,112]`다. driving의 half-resolution `[16,5,32,56]`를 resize하여 원본 latent라고 쓰지 않는다. reference의 `[16,1,64,112]`도 대체값이 아니다.

source decode `D(z_src)`를 최대1회 만들어 차량 경계·도로 질감의 VAE 재구성 오차를 관찰한다. 원본과 VAE 복원이 같다고 가정하지 않는다. 새로운 학습 target이 아니며 optimizer는 없다.

원본 픽셀은 compact MP4나 브라우저 녹색/자홍색 재생 화면에서 얻지 않는다. 보존된 lossless/preprocessed RGB와 실제 hash를 사용한다.

VAE worker와 DiT worker는 순차 실행한다. T5/CLIP/Qwen은 이번에 올리지 않는다.

## 5. 마스크는 결과를 보기 전에 고정

### 픽셀 합성 지도 E_px

B-032 MASK_ASSISTED의 float E를 기존 source support·target polygon·compositor로 재현한다. 검토용 uint8 support PNG를 정밀 float의 원본처럼 사용하지 않는다. float 재현 결과와 PNG의 기록된 양자화를 대조한다.

r=11, feather4, H=empty, source/target support를 유지한다. 오염을 지우려고 polygon·r·feather를 줄이지 않는다. source GT와 output polygon이 다른 의미의 파일이므로 semantic RED/WHITE를 단순한 `gray>0`로 읽지 않는다.

### latent 지도 M_lat

E_px에서 아래 한 규칙으로 만들고 source/target을 원본으로 복원할 위험을 줄이기 위한 보수적 guard를 둔다.
- temporal group: f0, f1..4, f5..8, f9..12, f13..16의 pixelwise max
- 각 그룹에 공간 8×8 max pooling으로 VAE latent H64×W112 매핑
- 공간 3×3 max pooling(stride1,padding1) 한 번, 즉 latent 한 칸의 여유
- 최종 shape `[1,1,5,64,112]`, 범위[0,1], channel broadcast

1은 생성/편집 자유 영역, 0은 원본을 제약하는 영역이다. source·기존 target core가 1에 포함되는지 확인한다. spatial frame/axis/좌표 순서를 검사한다.

이 temporal group과 1칸 guard는 명시적인 근사이며 실제 VAE의 완전한 시공간 receptive field가 아니다. 더 넓거나 좁은 mask sweep은 하지 않는다. GPU 생성 전 지도·면적·코어 coverage를 고정한다.

새 target이 기존 support밖으로 이동하면 새 output에 맞춰 mask를 다시 그리지 않는다. MASK_INCOMPATIBLE/잘림 위험을 별도로 기록하고, 그런 합성으로 개선을 주장하지 않는다.

## 6. 방법 — noisy state에 clean source를 직접 붙이지 않는다

pinned scheduler는 `predict_x0=True`, `prediction_type=flow_prediction`에서 다음을 계산한다.

`x0_hat = sample - sigma_k * guided_flow`

여기서 sigma_k는 실제 scheduler의 `sigmas[step_index]`다. 정수 timestep을1000으로 나눈 값을 대신 쓰지 않는다. sampler의 끝에서 쓰는 x0 변수 이름과 매 step clean prediction을 구분한다.

고정 M=M_lat에 대해 제약된 clean prediction을:

`x0_constrained = M*x0_hat + (1-M)*z_src`

로 정의한다. E=1 위치는 원래 prediction, E=0 위치는 source latent를 정확히 복사하는 where 처리를 써도 된다. 수치 dtype는 원래 converter의 출력 dtype를 보존한다.

**구현 위치**는 원본 `convert_model_output`을 호출한 직후, 결과가 `step()`의 corrector와 `model_outputs` history에 들어가기 전이다. 좁은 subclass/wrapper로 구현하고 OFF에서는 원래 scheduler 경로를 호출한다.

필수 조건:
- `predict_x0=True`, flow_prediction, thresholding=False, solver_p=None, 기존 final sigma0와 lower_order_final 설정 확인
- super.convert_model_output을 중복 호출하지 않는다.
- CFG positive/negative model forward는 바꾸지 않는다. 두 예측을 기존 방식으로 결합한 뒤 scheduler의 clean prediction만 제약한다.
- 저장되는 multistep model_outputs와 corrector가 모두 같은 제약된 prediction을 사용하게 한다.
- scheduler 반환 뒤 latent를 임의로 덮어써 history와 sample을 불일치시키지 않는다.
- solver order·timesteps·sigmas·step 수·초기 latent·noise는 그대로 유지한다.
- latent에 노이즈가 큰 초반에 clean source를 직접 붙이지 않는다.
- extra repaint resampling, 새 noise 재추출, inversion, 매 step VAE encode/decode는 없다.

직관적 등가식(σ>0, 대수 설명용)은 다음이다.

`v_constrained = M*v_guided + (1-M)*(sample-z_src)/sigma`

그러나 실제 구현은 위의 clean prediction 반환 지점에 둔다. σ가 작을 때 불필요한 나눗셈·다시 곱하기·별도 velocity 캐시를 만들지 않는다.

이것은 원래 pretrained vector field를 그대로 적분하는 것이 아니라 알려진 영역을 반영하는 sampling rule 변경이다. 원래 UniPC 수렴차수나 posterior 정당성을 자동 주장하지 않는다. 원본의 forward noising 궤적을 정확히 복제한다고도 하지 않는다. 기존과 같은 초기 noise에서 시작하고 실제 step의 sigma/예측 잔차를 기록한다.

## 7. 마지막 latent 혼합 대조군

기존 B-031 final latent를 z_base라 하면:

`z_final_only = M*z_base + (1-M)*z_src`

로 한 번만 계산하고 공식 VAE로 decode한다. STEP_CONSTRAINED와 정확히 같은 z_src와 M을 쓴다. 새 DiT forward나 sampler는 필요 없다.

이 대조군은 단순 마지막 latent 교체로 생긴 변화와, 생성 내내 제약하여 다음 model 입력까지 달라진 효과를 구분하기 위한 것이다. 픽셀 합성만과 비교하면 VAE decoder의 혼합 효과까지 sampling 효과로 오인할 수 있다.

## 8. 작은 CPU 검사와 실제 실행

이번 변경에 필요한 최대4개 작은 CPU 검사로 한정한다.
1. M=1 또는 OFF일 때 원래 scheduler 경로와 같은 prediction/작은 toy trajectory
2. M=0일 때 converted clean output이 source와 같고 toy scheduler 전체가 유한하게 종결됨
3. 실제 mask/latent shape·축·기존 support coverage·dtype·broadcast
4. FINAL_LATENT_ONLY의 M=0/1 endpoint·원본 파일 불변

toy에는 작은 수치 텐서와 pinned scheduler를 쓴다. 이 검사가 전체 영상 품질이나 실제 receptive field를 검증한 것으로 쓰지 않는다. 전체 가중치 변환/FA2/backward/정체성 감사는 반복하지 않는다.

실제 sampler는 최대1회, 40step·80forward, 같은 B-031 입력·noise·CFG 설정이다. 최초 model 입력과 조건 hash, 매 step 제약 적용 횟수40, 전체 finite와 최종 latent 저장을 확인한다. step별 decode나 추가 관측 forward는0이다.

마지막 generated latent를 decode 전에 저장한다. 같은 latent의 실패 재decode/자동재시도로 범위를 늘리지 않는다.

## 9. 예산·안전·종료

- DiT full sampler: 실패 포함 최대1회
- DiT model calls:40step·80forward
- VAE encode: source 최대1회
- VAE decode: source reconstruction1, FINAL_LATENT_ONLY1, STEP_CONSTRAINED1 = 최대3회
- Qwen image calls·T5·CLIP·학습·새모델/패키지다운로드·externalAPI/imagegen:0
- 새 mask 주석·mask/radius/strength/seed sweep·추가 case:0
- 총 wall-clock 상한2시간, 문서·포장·전송 포함. 마지막15분은 종료/보존에 남긴다.

기존 MemAvailable 시작72GiB/실행 headroom24GiB, swap0, 타 서비스 보호, worker별 단계 분리를 유지한다. CPU offload가 별도 물리 메모리를 주는 것처럼 계산하지 않는다. GPU-heavy worker 하나씩 순차 실행하고 다른 프로세스·환경·driver는 변경하지 않는다.

실제 shape/수치/입력 오류나 guard 문제는 중단한다. 시간 상한이 임박하면 추가 실험을 만들지 말고 실제 산출물·미완료 상태를 보존한다. 기술적 실패를 결과 좋은 프레임 선별로 숨기지 않는다.

## 10. 평가와 방법 채택

각 비교에서 source, B031 RAW, B032 RGB_POST, FINAL_LATENT_ONLY(raw/+RGB), STEP_CONSTRAINED(raw/+RGB)를 같은17장·같은preview시간축으로 보여준다. 기존 FIXED도 참고로 보존하되 주 comparator는 더 강한 MASK_ASSISTED다.

생성 전에 B032에서 남은 영역의 고정 crop을 등록한다. SOURCE local0/8/16, 차량 차체·뒤바퀴 아래·도로 strip·배경 경계 crop을 동일 좌표로 비교한다. 이 crop은 관측용이지 그래픽의 정답 pixel mask가 아니다. 새 결과를 보고 유리한 crop·마스크를 선택하지 않는다.

반드시 따로 판정한다.
- target형 높은 차체·창·루프·후미등 유지, source Mini형으로 회귀 여부
- 기존 거친 우향 이동·후면 노출 순서 유지
- 작은 도로 그래픽과 새 오염의 크기/지속/접촉부 상태
- 경계 halo·색차·source 이중잔상·target 절단·부유·그림자
- 새 target의 frozen support밖 이동과 강제 제한 가능성
- VAE 원본복원 자체의 경계·질감 오차
- 추가 encode/decode/full sampler 및 기존 두 단계 생성·수동 support를 포함한 비용

원거리 원본 pixel exact는 RGB_POST의 정의로 얻는 특성이며 주 성과가 아니다. 핵심은 동일한 후합성을 적용한 뒤에도 편집 내부와 경계에서 이득이 남는지다. 알려진 영역 바깥을 제약하므로 자유 영역 내부 그래픽이 반드시 사라진다고 기대하지 않는다. 그곳에서 관측되는 변화는 생성 과정의 상호작용 결과이지 직접 알려진 정답 복원이 아니다.

FINAL_LATENT_ONLY와 같거나 더 나쁘면 생성 중 제약의 추가 비용을 정당화하지 못한다. 배경만 좋아지고 target 외형/동작이 손상되면 trade-off이며 미채택이다. source로 전부 돌아가면 실패다.

현재 한 차량·한 seed·기존 출력 기반 mask를 사용하는 진단이다. 개선돼도 mask-assisted context baseline 후보일 뿐, 자동화·미사용 일반화·동물/사람 문제 해결·논문 신규성·상용급 성공은 아니다. 실제 연속 시청 주체가 없으면 temporal=UNVERIFIED를 유지한다.

## 11. 이론·재현·GitHub 기록

실행 전 이 의뢰서를 docs/research/work_orders에 남기고, 중복 실험 여부 확인 후 PLAN/DECISION/입력/예산을 고정한다. CHARTER·HISTORY·ROADMAP에는 차량 context 축과 동물·사람의 앞단 자세 실패를 분리해 기록한다. 과거 FAIL은 소급 수정하지 않는다.

한국어 수업 자료는 다음을 실제 함수·텐서·결과에 연결한다.
- pixel composition 대 final latent mixing 대 per-step clean prediction constraint
- FM의 noisy latent와 clean estimate, x0_hat = z_sigma - sigma*v
- multistep solver에서 prediction history와 state를 일관되게 다뤄야 하는 이유
- VAE 시간/공간 압축, receptive field와 approximate mask, 복원오차
- 알려진 영역의 강제 일치와 자유 영역의 간접 개선은 다른 주장이라는 점

선행 근거:
- RePaint: https://arxiv.org/abs/2201.09865
- Blended Latent Diffusion: https://arxiv.org/abs/2206.02779
- pinned FlowUniPC: https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/utils/fm_solvers_unipc.py

이번 방법은 RePaint의 DDPM·재샘플링을 그대로 재현한 것이 아니다. 알려진 원본 영역을 쓰는 일반 원칙을 현재 FM/UniPC에 맞춘 제한적 baseline이다. 단순 혼합의 신규성을 주장하지 않는다.

종료 후 RESULTS/METHOD/CONTROL/COSTS/REPRODUCE/lessons와 코드·mask계보를 연구 브랜치에 commit/push하고 원격 SHA를 확인한다. 본격 결과나 code review 전에 미래 계획만 늘리지 않는다. 비민감 코드·문서만 공개하고 개인 경로·모델가중치·raw/latent·비밀정보는 공개하지 않는다.

compact에는 기존 비교 MP4·새 raw/final/control MP4·source reconstruction·고정 crop·뷰어·보고서·의뢰서·재현을 담는다. 새 MP4는 새 파생물 인코딩이며 기존 MP4는 재인코딩하지 않는다. raw/final/source latent는 full에 분리하고 대형가중치·전체 중복cache는 빼라. Spark/Mac /tmp의 실제경로·SHA·CRC·payload hash·전송동일성을 검증한다.

최종 보고는 먼저 답한다.
1. 단순 합성과 마지막 latent 혼합보다 어떤 경계/편집 내부 문제가 줄었는가?
2. target 외형·동작이 유지됐는가, 원본 객체가 다시 나타났는가?
3. 추가 GPU 비용을 정당화하는가?
4. 무엇이 미해결이며 다음 가설을 채택할 근거가 있는가?

한 번의 비교 이후 종료한다. 강도/스케줄/mask·새 모델·학습·긴 영상·개인사진 요청을 자동으로 추가하지 않는다. 미개선이면 이 고정 제약 방법을 기각하고, 결과를 사용자가 검토한 뒤 다음 방향을 정한다.
