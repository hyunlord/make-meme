# B-031 — 원본 자세에 맞춘 참조 앵커의 로컬 자동 생성과 조건부 영상 전이

작성: 2026-10-26. 상태: **PROPOSED / NOT_RUN / 새 다운로드·실행 미승인**.

이 문서는 B-030 이후의 수행 제안이다. 사용자가 이 계획의 실행을 지시할 때만 아래 다운로드·설치·생성 예산을 적용한다. 문서 등록 중 GPU·모델 다운로드·학습은 모두 0회다. 새 학습 방법의 효과나 Spark 적합성은 아직 검증하지 않았다.

## 1. 목표와 이번 전환

최종 목표는 원본 영상 V, 임의의 참조 이미지 R, 편집 지시 P로 대상 외형을 바꾸면서 지정한 원본 동작·장면을 보존하는 로컬 시스템이다. 개인 반려견의 추가 사진을 요구하지 않는다. A의 native imagegen 경로와 B의 로컬 모델 연구는 분리한다.

B-030은 사람의 큰 치마 배치에 VAE+mask 행 의존을 일부 관측했지만, 세부 손상과 차량 그래픽에는 조합 의존이 남았다. VAE=자세 / CLIP=정체성은 입증되지 않았다. 따라서 이 결과를 근거로 임의의 joint-attention gate·계수·RoPE·토큰 섞기를 추가하지 않는다. 기존 가설과 실패는 보존한다.

이번에는 정보를 지운다고 가정하기보다, **서로 맞지 않는 참조 자세와 원본 자세를 학습된 로컬 이미지 편집기로 먼저 맞추는 분해형 기준선**을 시험한다.

A0 = G(source_first_frame, target_reference, edit_instruction)
R_star = neutralize_background(A0, observed_target_support)
Y = H(source_video, R_star, masks, caption)

G는 다중 이미지 편집 모델, H는 기존 SCAIL replacement다. A0를 출력 첫 프레임에 덮어붙이거나 sampler에서 강제로 clamp하지 않는다. R_star는 새 참조 조건이며 실제 생성 영상의 frame0 일치를 보장하지 않는다.

이는 단일 attention 경로의 인과 실험이 아니라 **자동 참조 재구성 단계를 추가하는 시스템 기준선**이다. 새 알고리즘·pose-free identity·논문 신규성을 주장하지 않는다. 정확한 참조 생성과 동작 전파의 실패를 관찰 가능한 중간 결과로 분리하는 것이 목적이다.

## 2. 근거와 한계

- 공식 SCAIL-2 논문 v3 §3.2는 학습자료 합성 과정에서 원본 영상의 첫 프레임을 자세 참조로 이미지 생성기에 제공한다고 설명한다. 이는 이번 분해를 검토할 근거이지, inference에서 이를 반드시 해야 한다거나 우리 입력에서 성공한다는 증거가 아니다. https://arxiv.org/html/2606.10804v3
- Qwen-Image-Edit-2511 공식 model card는 다중 이미지 입력을 제공한다. 본 계획은 한 종의 공개 체크포인트만 고정하여 사용하는 제안이며 최신/최고라는 주장이 아니다. https://huggingface.co/Qwen/Qwen-Image-Edit-2511
- VideoPainter의 고정 edit.py는 편집된 첫 프레임을 영상 조건으로 전달한다. 그러나 이번에는 VideoPainter까지 설치하지 않는다. 향후 영상 전파 backend 비교를 위한 별도 후보로 남긴다. https://github.com/TencentARC/VideoPainter/blob/bbab6cd5cd5cb89f0e2444305c32fd74a010ae0a/infer/edit.py

SCAIL의 공간 정보 경쟁이 유일한 원인이라고 확정하지 않는다. G가 참조의 무늬·얼굴·세부를 잃거나 원본 객체를 유지할 수 있으며, 좋은 A0가 있어도 H가 움직임을 전파하지 못할 수 있다. 생성 앵커는 정답 GT나 oracle이 아니며, 생성 실패와 비용을 전체 성능에 포함한다.

## 3. 입력·패널 고정

B-027의 공개 animal/human/vehicle 각 R1/R2를 재사용한다. 새 개인 자료·target에 맞는 실제 standing 사진·새 웹이미지를 요구하지 않는다. 기존 원본 첫 프레임과 기존 target 원천 프레임/instance mask를 사용한다.

- animal: source dog f0..16, target dog-gooses track1 f0/f85
- human: source dance-twirl f0..16, target dance-jump track1 f0/f16
- vehicle: source car-roundabout f30..46, target car-shadow track1 f0/f39

모든 이미지는 실제 asset manifest로 확인한다. 모델이 이미 보았을 가능성 UNKNOWN, 개발 패널/단일 seed/공개 GT mask-given이라는 기존 한계를 유지한다. 사람의 실제 신원을 식별하거나 생체신원을 인증하지 않는다.

이미지 편집기의 첫 입력은 source 첫 프레임 전체다. 두 번째 입력은 같은 target 원천 RGB에서 GT bbox+고정 10% 문맥 여유로 자른 참조이며, support 밖은 RGB128로 중립화한다. 이 규칙을 결과 전에 6개에 동일하게 적용하고, 원래 native pixel 크기·가림·실제 resize를 기록한다. 누락된 털·얼굴·몸을 생성으로 미리 보완하지 않는다. B-028의 결과를 골라 참조를 바꾸지 않는다.

편집 지시는 공통 template을 사용한다. Image1의 선택 객체를 Image2의 대상으로 바꾸되, 첫 프레임의 행동/시선/방향/카메라와 보호 장면을 유지하고, target의 자연스러운 비율을 허용한다고 명시한다. target 외형을 텍스트로 대신 만들어 내지 않는다. 보호할 원본 객체/영역과 관측 가능한 target 특징 2~3개를 생성 전에 기록한다. 두 target reference에는 같은 task 지시를 사용한다.

## 4. 새 환경과 자원 — 이전의 설치0 실험과 다름

이 제안은 **Qwen/Qwen-Image-Edit-2511 한 종의 새 다운로드와 격리된 의존성 설치**를 포함한다. 실행자가 승인된 수행 지시를 받은 뒤에만 진행한다.

- 전체 모델 repo/실제 safetensors·encoder·VAE·tokenizer의 revision과 파일 목록을 고정한다. 공식 표시 총 크기 약57.7GB는 다운로드 참고값이며 실행 메모리가 아니다.
- 신규 가중치 다운로드 상한 70GiB, 추가 모델 0종. 기존 파일이 있으면 hash/revision 확인 후 재사용한다. 중복 전체 스냅샷·양자화 모델 여러 버전·VideoPainter·FLUX·추가 LoRA는 받지 않는다.
- 별도 venv와 lockfile을 사용한다. 기존 SCAIL 환경·시스템 Torch·CUDA·driver를 업그레이드하지 않는다. 현재 GB10에서 검증된 Torch를 재사용할 수 있는지 먼저 확인한다. 호환 불가 시 명시하고 기존 환경을 깨지 않는다.
- Qwen은 해당 공식 pipeline이 지원하는 attention 경로를 사용한다. SCAIL의 FA2 강제를 무조건 가져오지 않는다. 커스텀 CUDA kernel 개발은 이번 범위가 아니다.
- 원격 prompt enhancer·API·원격 inference·imagegen 호출은 0회다. 다운로드 이후 실제 추론은 로컬 파일만 사용한다.
- Qwen과 SCAIL을 동시에 상주시켜 통합 메모리를 소모하지 않는다. 이미지 단계 종료 후 해당 프로세스의 모델을 해제하고 그 뒤 기존 SCAIL worker를 사용한다. CPU offload가 별도 물리 RAM을 공짜로 제공한다고 가정하지 않는다.
- 기존 MemAvailable 시작72GiB / 실행24GiB headroom, swap0, 다른 서비스 보호를 유지한다. 정확한 모델 크기만으로 fit 또는 속도를 보장하지 않는다. 필요 공간+결과 공간+20GiB 여유의 실제 disk를 확인한다.
- 환경 준비 목표60분, 전체 hard wall-clock 상한6시간(다운로드·설치·검토·패키징 포함). 종료/보존 작업용 마지막30분을 남겨 GPU 작업을 시작한다. 이는 소요시간 약속이 아니라 실행 상한이다. 초과하면 실제 위반을 기록하고 자동 연장하지 않는다.

## 5. 이미지 앵커 단계 — 최대6회

3과제 × R1/R2 각1장, 총 최대6회 로컬 이미지 생성. 실패·중단도 예산에 포함한다. seed/프롬프트/step 탐색과 best-of 재생성은 0회다.

공식 QwenImageEditPlusPipeline 사용 예를 출발점으로 BF16, 40 image denoising steps, true_cfg_scale4.0, guidance_scale1.0, negative_prompt 단일 공백, 고정 seed20261026을 사전 기록한다. 모델·pipeline의 실제 지원 인자와 버전을 먼저 확인한다. image generation step을 SCAIL의80forward와 동일한 비용으로 계산하지 않는다. 실제 branch/NFE는 관측 범위대로 별도 기록한다.

요청 output canvas는896×512다. pipeline의 허용 크기가 다르면 불변 aspect ratio를 유지하는 공식 경로와 확정 변환을 생성 전에 기록한다. 결과를 본 뒤 좋은 crop을 고르지 않는다. 이미지 API의 다중 입력 순서는 Image1=source, Image2=target reference로 명시한다.

원본 전체·target 원본/실제 입력·raw A0를 보존한다. A0를 원본 배경에 붙여 보정하거나 face restoration/SR/변형으로 개선하지 않는다. cheap source-copy와 reference-only 정지 비교도 함께 보여준다.

앵커 판정은 다음을 분리한다.
1. 원본 객체가 target의 구분 가능한 외형으로 바뀌었는가? 단순 source 유지·recolor만으로 PASS하지 않는다.
2. source 첫 프레임의 자세·진행방향·장면 내 위치를 유지하는가? target 비율의 합당한 차이는 허용한다.
3. 얼굴/사지/차체의 큰 손상·이중 객체·큰 잘림이 없는가?
4. 보호 장면과 다른 객체에 큰 추가 그래픽/문자·삭제·카메라 변화가 없는가?

같은 target의 R1/R2에서 이 네 항목을 비교한다. 최종 영상의 시간 품질이나 정확한 사람 신원은 이미지 단계에서 판정하지 않는다. 실제 시각 관측 없이 성공 판정을 만들지 않는다. 성능 수치는 조건부 성공 subset만 보고하지 않고 전체6개와 실패를 함께 보고한다.

## 6. 조건부 영상 단계 — 최대3회, R1만 사전 지정

각 과제의 **R1 앵커만** 사전에 영상 단계 대상으로 고정한다. R1이 위 정적 목표를 만족하지 못하거나 의미 있는 형태 손상이 있으면 해당 영상 단계는 ANCHOR_UNSUITABLE로 생략한다. R2가 좋아 보인다는 이유로 바꾸지 않는다. R2는 첫 단계 참조 강건성 비교용이며 영상 일반화 증거가 아니다.

최대3개 R1이 적합할 때, 생성 A0 안의 실제 target support를 관측한다. 이미 설치된 segmentation/CPU 수동 polygon 도구만 사용하며, 원본의 다른 체형 mask를 무조건 그대로 씌우지 않는다. 새 모델 다운로드 0, mask 준비 총30분 이내. 얇은 경계·가림은 불확실성을 표시하며 완벽한 관절 GT를 요구하지 않는다.

A0의 target support 내부 RGB를 보존하고 밖은128로 중립화하여 R_star를 만든다. reference semantic mask는RED/BLACK. source driving/mask는B027 그대로 유지한다. 이 처리는 full scene을 reference 배경으로 이중 제공하는 개입과 섞이지 않도록 하기 위한 고정 contract다.

새 R_star의 VAE·CLIP·reference mask만 계산한다. source latent·driving mask·text·negative·실제 초기 noise·RNG·scheduler는B027 case의 기존 값을 재사용한다. target/학습 prefix 계산은 없다.

기존 SCAIL replacement=True, adapter/ALG/B029 gate/manualRoPE OFF, history/additional_ref=None을 유지한다. case별 최대1sampler·40step80forward·decode1, 자동재시도0. 최종 latent를decode 전에 저장한다. 생성된 앵커를 frame0으로 강제 교체하거나 history에 몰래 주입하지 않는다.

기존B027의 해당R1 영상과 비교하고, B028/B029 좋은case를섞지않는다. 17프레임·896×512, source_fps=null/preview24fps/timebase_assumed=true를 유지한다. 실제 native시간보존이라고하지않는다. 신규이미지·참조마스크가함께달라지는시스템비교이며pose단독인과효과가아니다.

## 7. 평가·연구 결정

SOURCE / TARGET / 기존B027 / A0 / R_star / 새영상의 단계별 실패를 분리한다. A0 정지 반복은무료motion-failure기준이며동영상전파성공으로세지않는다.

- A0부터실패: 로컬정지편집기/입력계약의한계. 후단영상모델탓으로돌리지않는다.
- A0는좋으나영상이실패: 원본움직임·가림·긴시점변화를전파하는경로의문제후보. 다음VideoPainter등비교를검토할수있지만이번에추가설치하지않는다.
- 둘다관측상개선: 분해형baseline후보. 새로운사진/장면에서별도평가하기전보편성·새논문기여를주장하지않는다.

sourcecopy, target정지copy, target외형과sourcemotion의공동달성을구분한다. 사람이 실제속도로볼수있는viewer와세부질문을제공한다. agent정적검토만으로temporalPASS하지않으며UNVERIFIED를유지한다. sourceFPS불명과loop경계도표시한다.

추가이미지모델로품질이좋아져도효율개선은자동주장하지않는다. 초기다운로드/coldload·anchor 생성·mask작업·조건인코딩·영상S/D·검토의비용과실패를모두합산한다. 서로다른모델의같은seed/NFE를동일조건이라고하지않는다. 한샷당소수앵커라는설계후보가프레임별생성보다싸다는것도실측전에는가설이다.

## 8. 학습·재현·기록·제출

학습update는0이다. 생성A0를GT paired영상으로등록하거나실패샘플을학습정답으로쓰지않는다. B는로컬모델only이며A imagegen/프레임별이미지생성+CPUwarp로되돌아가는실험이아니다.

한국어해설: 암묵적경로분리와과제분해, A0가oracle/GT가아닌이유, referencepose를지우는대신원본pose로맞추는가설, 순차모델메모리수명, sourcecopy/anchor정지copy반례를수식·실제함수·관측에연결한다.

착수전PLAN/입력/공통template/seed/버전/다운로드예산/앵커판정/영상R1선택을고정하고HISTORY·ROADMAP에B030종료와새질문을기록한다. 과거결과를삭제하지않고개인사진요구를재도입하지않는다. B031이이미작업중/완료라면중복실행금지.

종료후RESULTS·ANCHORS·STAGES·COSTS·REPRODUCE·환경lock·lessons와해시를commit/push하고remoteSHA확인. 실제데이터와weights·새조건·latent는공개하지않는다. 모델/데이터의이용조건도각각기록한다.

full/compact를분리해Spark와Mac /tmp에보존한다. compact에는실제입력·앵커6개·성공/실패판정·실제로생성한영상·기준선·viewer·재현요약만넣고, 중복프레임시트와큰tensor는full에둔다. 새weights를ZIP에넣지않는다. 영상재인코딩없이CRC/payloadhash/실제추출/전송동일성을검증하고실제검증범위만보고한다.

핵심보고순서: 앵커에서target+source자세가맞았는가 → 영상으로이어졌는가 → 실패포함총비용 → 연구가설의지지/기각/미결정 → 다음하나. 설치와테스트통과만을편집성과로보고하지않는다. 새로운모델/개입/seed/학습/긴영상을자동추가하지않는다.
