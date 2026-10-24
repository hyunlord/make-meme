# B-018 — 실데이터와 분리한 SCAIL attention LoRA 배선·역전파 smoke

작성: 2026-10-24 · parent: B-017 · 상태: **PLANNED / NOT_RUN**

계획 등록은 GPU 실행 승인이 아니다. 사용자가 실행 담당자에게 이 계획의 수행을 지시할 때만 아래 범위를 실행한다. 기존 B-017 RIGHTS_PENDING/DATA_GAP·training-ready0 기록은 변경하지 않는다.

## 0. 목표와 방향

B-017은 하나의 기존 source target에 reference를 두 가지로 붙인 검토 case2개를 만들었으나 학습-ready0, 실제Lab target0, cross-ID pair0였다. 이것은 현재 등록 자산의 진단이며, 모든 모델 연구나 gradient 검사에 실제Lab 촬영이 선행해야 한다는 뜻은 아니다. source 진위 미확인과 합성 source 판정도 구분한다. 합성 데이터 자체가 원천적으로 불가능한 것은 아니나 출처·사용 범위·생성/렌더링 방법·동작 대응 오류를 명시해야 한다. A imagegen 산출물이나 외부 생성 API를 B 학습에 넣는 경계는 유지한다.

다음 두 과제를 분리한다.
- 실제 개체·동작 학습: 허용된 R/D/Y와 개발·검증 분할이 필요. 현재 미확보.
- 학습 코드의 연결: 합성 수치 fixture로 adapter 주입·gradient·optimizer·기반 가중치 불변·save/reload를 검증할 수 있음.

**이번은 두 번째 과제만 실제 실행한다.** 전체 SCAIL의 Flow Matching 학습, 17프레임 backward, 개체·자세 분리나 품질 개선을 증명하는 실험이 아니다. 공식 self-attention 한 모듈의 작은 입력에서 실제 학습 커널과 LoRA 연결을 확인한다. B-001의 VACE LoRA 성공을 현재 SCAIL의 LoRA/backward 성공으로 대체하지 않는다.

## 1. 근거·범위

기준 B-017 commit `d2ba0f42cb26d5bfdd9ba6c5e5c0e59efde4a10e`의 RESULTS/TRAIN_INTERFACE/RIGHTS_AND_SPLITS를 읽는다. 실제 inference checkpoint와 pinned Wan `78fe19576bb06be96c2375e088574a262a300edb`를 재사용한다. SAT `ac63f8eb369e2f4fac2ce273ead0ae7e602c3919`의 LoRAMixin/lora_train 존재와 이름 필터 불일치 가능성을 참고하되, 이번에 SAT 전체를 실행하거나 공식 LoRA recipe가 완성됐다고 주장하지 않는다.

공식 config의 dim5120/heads40/head_dim128/blocks40을 실제 파일로 확인한다. 체크포인트의 **마지막 block self_attn 모듈 하나**(예상 prefix `blocks.39.self_attn.`)의 q/k/v/o와 norm·bias가 존재하는지 먼저 header로 확인한다. 실제 prefix가 다르면 추측하지 말고 mapping 근거를 기록한다.

- 총 상한2시간. 새 패키지/대형 가중치/데이터 다운로드0, 영상 생성 sampler0, 전체DiT/인코더/VAE 적재0.
- checkpoint 원본 read-only. safetensors의 per-tensor 접근으로 선택 모듈만 가져온다. full load_file로65GB 전체를 로딩하지 않는다. 선택 tensor payload1GiB 상한. 실제 읽은 키·shape·dtype·bytes 기록.
- GPU worker 최대1회, 실제 adapter optimizer update **최대3회**, 재시도0. CPU 단위검사에는 full 모델 학습을 넣지 않는다. 이것은 새로운 제한적 optimizer update를 포함한 제안이지, 학습0 계획이 아니다.
- 기존 FA/torch/환경과 다른 서비스 보존. 새 driver/compile/전역설치/다른 프로세스종료/drop_caches/swap 변경 금지. 기존24GiB 시스템 headroom·swap0 보호 유지, 작은 worker 자원 사용을 별도 제한·관측. 단일 self_attn 구성요소 성공을 full-model 메모리 성공으로 일반화하지 않는다.
- FlashAttention backward가 실패하면 원인을 기록하고 이번 worker는 종료한다. 다른 backend로 조용히 바꿔 PASS 처리하지 않는다. CPU SDPA는 단위검사 기준용일 수 있으나 실제 GB10 FA backward 판정과 분리한다.

## 2. 학습 없는 CPU 검증

얇은 LowRankLinear 모듈을 만든다. 기존 W0/bias를 고정하고 q와 v에만 rank4, alpha4, dropout0을 주입한다. 이 위치·rank는 작은 배선검사용 선택이며 동작 전이에 최적이라는 가정이 아니다. 파라미터 이름에 'lora'가 있다는 이유만으로 optimizer에 넣지 말고, 실제 adapter parameter 객체만 명시적으로 수집한다.

작은 FP32 CPU fixture에서:
- deltaW=(alpha/r)BA, A random/B zero 초기화에서 기존Linear와 출력 일치.
- base requires_grad=False, adapter만 requires_grad=True, optimizer group membership의 정확한 집합.
- train/eval 전환 시 자동 weight merge를 하지 않음. merge를 구현하지 않는 것이 이번 기본이다.
- backward graph가 adapter까지 연결됨. no_grad/inference_mode 안에서 학습 branch를 실행하지 않음.
- B=0인 첫 backward에서 A gradient가0일 수 있음을 정상 사례로 검증. B gradient·이후 A gradient를 구분.
- 저장·재로딩 스키마와 원본 비수정 테스트.

여기서 작동한 코드는 별도 격리 파일로 남기고, 현재 inference 모듈·checkpoint에 adapter를 영구 적용하지 않는다. hook으로 실행 중 모델을 무작정 바꾸는 대신 explicit wrapper를 사용한다.

## 3. 실제 self-attention과 작은 수치 입력

가능하면 pinned WanSelfAttention/rope_apply_scail/FlashAttention wrapper를 그대로 사용해, 선택 모듈의 실제 가중치·실제 head dimension·q/k normalization·RoPE를 유지한다. decoder/head/40개 block을 적재하지 않는다. 작은 exact import가 불가능하면 광범위한 package 수정 대신 BLOCKED_IMPORT로 기록한다.

예시 toy token 구성은 ref1×4×4=16, generated1×4×4=16, driving1×2×2=4로 총36token이다. 실제 helper에서 유효한 shape/offset인지 CPU에서 먼저 검사해 실행 전에 고정한다. animation/H0, additional_ref0을 유지하고 기존 driving W offset을 변경하지 않는다. 이는 token algebra를 시험하는 인공 입력으로, 실제17프레임·512×896 영상 latent가 아니다.

x는 fixed seed의 synthetic hidden tensor [1,36,5120]이다. 원본사진·source·기존조건cache는 읽지 않는다. 고정 pseudo target은 같은 shape의 별도 수치 배열이다. manifest에 **SYNTHETIC_TENSOR_CONTRACT_TEST**라고 표기한다. 임의 MSE target을 실제 Flow Matching target/동물GT라고 부르지 않는다.

GPU 업데이트 직전에는 원래 projection module과 Bzero adapter module의 동일 입력 출력차를 검사한다. dtype/FA 재현성에 맞는 허용오차를 실행 전에 정하고 exact 여부·max error를 같이 보고한다. 원본 FP32 저장 값과 실행 BF16 cast 값을 구분하고, base 불변 해시는 실행 cast 이후 값끼리 비교한다.

기존 tiny CUDA 선행 연산은 사용 가능하되 65GB loader나 encoder stage를 실행하지 않는다. 실제 FA path/dtype/kernel 선택 및 forward/backward가 어디에서 수행됐는지 기록한다.

## 4. 정확히 제한된 optimizer update

정의: L_smoke=mean((F_theta,phi(x)-y_synthetic)^2). FP32 loss, 기존 지원 BF16 연산, FP32 adapter master params를 명시한다. AdamW lr1e-4, weight_decay0, rank4/alpha4/dropout0, 고정 입력·target, 최대3 update로 사전 고정한다. 결과 후 optimizer나 lr을 튜닝하지 않는다.

각 step에서 실제 loss, Q/V adapter A/B의 grad 존재·finite·norm, parameter delta, frozen-base grad None, allocator/RSS/cgroup/시간을 기록한다. base 파라미터가 optimizer에 들어가거나 실제로 바뀌면 즉시 FAIL. loss가3회 내 단조감소하지 않았다고 추가 학습하지 않는다. loss감소는 참고이며 단순 gradient·업데이트 검사의 성공과 구별한다.

adapter A gradient가 첫 step0인 것은 Bzero 초기화로 가능하다. 반대로 모든 adapter gradient가 영원히 None/0인데 loss가 계산됐다는 이유만으로 PASS하지 않는다. finite B gradient·실제 adapter delta·손실/출력에 연결되는 graph를 검증한다.

3 update 이전에 OOM/nonfinite/kernel error가 발생하면 즉시 중단하고 실제 사용량을 보고한다. false→true requires_grad만 바꿨다고 FlashAttention backward/전체 train recipe가 검증됐다고 하지 않는다.

## 5. 저장·복원과 수용 경계

- adapter state만 별도 저장하고 frozen subset 원본·이전모델은 보존한다.
- fresh component instance에 같은 frozen subset+saved adapter를 로딩해 고정 입력 출력의 tolerance 일치, adapter OFF에서 baseline 복귀를 확인한다. 이 과정은 optimizer update가 아니지만 forward 수를 별도 집계한다.
- 선택한 frozen tensors의 전후 해시, adapter key/rank/alpha·base revision/key map·dtype·fixture seed/shape·실행 코드hash를 기록한다.
- 테스트 adapter는 TEST_ONLY/NOT_FOR_INFERENCE로 라벨링하고 사용자 영상 생성 경로에 활성화하지 않는다. 개인데이터를 쓰지 않았어도 artifact의 모델 이용조건은 기존 가중치 조건을 따른다. 공개 repo에는 실제 adapter/base weights를 기본적으로 넣지 않는다.

가능한 완료 판정: COMPONENT_BACKWARD_PASS / COMPONENT_UPDATE_RELOAD_PASS / BLOCKED_KERNEL / FAIL_GRADIENT / FAIL_BASE_MUTATION 등. **FULL_MODEL_TRAINING=NOT_RUN, VIDEO_QUALITY=NOT_RUN, IDENTITY_POSE_DISENTANGLEMENT=NOT_RUN**을 함께 표시한다. 전체40block/17f가 학습가능하거나 연구가 성공했다는 주장 금지.

## 6. 별도 실데이터 안내 — 수집 실행 아님

기존 Lab를 위한 최초 소형 자료는 같은 개체의 편안한 앉기·자연고개돌림·걷기·자연 앉았다일어나기 영상과, target과 다른 시간의 사진이다. 제안 규모는 촬영session2개에 총6~10clip(각5~10초)와6~10장 사진. 이는 시작용 제안이지 데이터충분성/논문성능 보장이 아니다. 원본fps/해상도/PTS를 보존하고 사람·위치·민감배경은 최소화한다. 전신과 발이 잘리거나 큰 카메라회전이 없도록 하되 동물을 억지로 직립·춤추게 하지 않는다.

촬영주체·실제동일개체·session·private training 사용범위를 간단한 manifest에 기록한다. 같은 clip을 train/test로 쪼개지 않고 session 기준으로 나눈다. 다른session의 같은Lab는 새로운identity 일반화가 아니다. 자연동작만으로 의인화직립춤/cross-ID motion pair가 확보됐다고 하지 않는다.

확보 안내 문서만 만들며 외부 메일·수집·웹스크래핑·촬영요청 전송을 실행하지 않는다. 현재 사용자가 새 자료를 제공하지 않아도 이 문서의 구성요소 smoke는 진행 가능하다. 나중에 허용된 실제자료가 들어오면 full-model 작은 학습 pilot의 별도 PLAN에서 R/D/Y를 연결한다.

## 7. 학습 노트와 GitHub

직관→수식→shape→실제코드→CPU fixture→GB10 관측→한계→질문과해설 순서로 작성한다. 주요 내용:
- LoRA h=W0x+(alpha/r)BAx, rank와 parameter수, Bzero일 때 dL/dA=0 가능성.
- requires_grad=False와 no_grad/inference_mode, eval의 차이. frozen layer라도 upstream adapter에 gradient를 전달해야 할 경우가 있음을 설명.
- forward PASS와 backward PASS, 실제 full Flow Matching loss와 인공 component MSE의 차이.
- 실제dataset이 필요한 모델학습과 숫자fixture로 가능한 소프트웨어검증의 차이.

공식 근거: LoRA https://arxiv.org/abs/2106.09685 , PyTorch autograd https://docs.pytorch.org/docs/stable/notes/autograd.html , pinned SCAIL model_scail2.py/config-14b.json. 원논문 범위를 영상모델의 성능보장으로 확대하지 않는다.

시작 전에 HEAD/git상태·CHARTER/ROADMAP/HISTORY/RECORDING_PROTOCOL·B017/TRAIN_INTERFACE를 읽고 실험설정과정지기준을 commit/push한다. 기존 inference checkout과 모델·A·실험 history 보존. 종료 후 RESULTS/REPRODUCE/한국어해설·HISTORY/ROADMAP 갱신·remote SHA 확인. 불필요한새framework/전체typing정리/문서중복을 피한다.

비공개 ZIP 하나에 runner·fixture·선택키manifest·검증/실패로그·학습curve·adapter(작으면)·재로딩기록을 넣고 큰가중치/원본media는 제외한다. /tmp의 Mac/Spark 실제경로·CRC·내부해시·전송상태를 구분한다. 이번작업 프로세스 종료를 확인하고 다음 하나만 제안한다. 전체모델학습·데이터확보·추가생성은 자동으로 시작하지 않는다.
