# B-019 — 마지막 Transformer block의 실제 backward·LoRA와 제한된 토큰 길이 검사

작성: 2026-10-24 · parent B-018 · 상태 **PLANNED / NOT_RUN**.
문서 등록은 GPU 실행이 아니다. 사용자가 이 계획을 실행 담당자에게 전달하여 수행을 지시할 때 아래 한정 범위를 적용한다.

## 0. 목적·증거·연구 경계

B-018 commit `19890bea9172db288960de2463b8a9f6c9233140`의 RESULTS/ATTENTION_CONTRACT/실제 component_runner/runtime_guard 및 고정 공식 block 소스를 읽었다. B-018은 실제 `blocks.39.self_attn.` 104,888,320개 base parameter에서 Q/V LoRA81,920개를 synthetic x/target `[1,36,5120]`로 3update했다. 공식 FA2 backward·base 불변·fresh reload·OFF 출력 검사를 통과했다. 이것은 학습 배선의 구성요소 증거이며 video/FM 목적함수·전체40block·개체분리 성공은 아니다.

다음 질문: self-attention 뒤에 공식 residual·timestep modulation·image/text cross-attention·FFN까지 붙어도, block 최종 출력의 loss가 기존 self-attention Q/V LoRA까지 전달되는가? 또한 실제17프레임 입력과 같은 토큰 길이에서 **한 block**의 forward/backward 비용은 어느 정도인가?

이번은 SYNTHETIC_BLOCK_CONTRACT_TEST다. B-017의 데이터 권한·실제 Lab target·cross-ID pair 부족은 해결되지 않았으며 개인 영상·이전 생성·inference cache를 학습에 사용하지 않는다. A/기존 모델·추론·모든 실패 이력은 동결한다. ALG OFF/H0의 기본 animation 위치 계약을 유지한다.

## 1. 범위·상한

- 총 작업 최대2시간. 기존 정상 Python/Torch/FA/upstream을 사용. 새 패키지/모델/데이터 다운로드0, 전체 SCAIL 로드0, T5/CLIP/VAE 인스턴스0, 영상 sampler/decode0, 외부생성/imagegen0.
- 실제 GPU worker 최대1회, 자동 재시도0. 소형 full-block forward 최대8회, backward3회, AdamW update3회. 성공 후 조건부 대형 synthetic resource-only forward/backward 각각1회, optimizer update0. 합계 최대9forward/4backward/3update. 이는 block forward 수이며 내부 attention kernel 호출 수와 다르다.
- 기존 입력 데이터 없이 fixed synthetic tensor만 사용한다. test adapter는 TEST_ONLY/NOT_FOR_INFERENCE이며 production에 연결하지 않는다.
- 보호 서비스/다른 GPU 작업 비간섭, 시작 MemAvailable≥72GiB·swap0, 실행 headroom24GiB·swap0 유지. 다른 프로세스 종료·sudo/driver/OS/clock/swap 변경·drop_caches 금지.
- **이 제안의 worker memory.max 상한은16GiB, memory.high14GiB**다. B-018 구성요소의8GiB cap과 다른 명시적 한정 자원안이며 실제 수행 지시 전 적용하지 않는다. 물리 headroom 보호는 완화하지 않는다. snapshot/기존 user scope에서 가능한 범위만 사용한다. 큰 길이의 보수적인 사전 비용이 이 한도를 넘으면 LONG_NOT_RUN으로 남기고 임의 cap 확대나 중간 길이 탐색을 하지 않는다.
- worker deadline/unit을 현재 실행에 맞게 고정한다. 과정 종료/실패 시 자기 프로세스만 정리한다. 2시간 초과로 새 작업 예약·백그라운드 잔류 금지.

## 2. 실제 공식 block을 최소 로딩

고정 upstream `78fe19576bb06be96c2375e088574a262a300edb`의 `wan/modules/model_scail2.py` `WanAttentionBlock`을 사용한다. `blocks.39.` prefix 전체의 header를 먼저 읽고 실제 키/shape/dtype/count를 사전 manifest에 고정한다. self-attention10개만 읽고 full block을 검사했다고 하지 않는다. 약4억 규모라는 코드 추정과 실제 계수를 분리한다.

`safe_open`으로 선택 prefix만 읽는다. 전체65GB load_file, 전체40block 초기화, SAT recipe 교체는 하지 않는다. 메타 초기화와 strict key/shape load를 사용하고 다른 block의 파라미터를 잘못 가져오지 않는다.

공식 config: dim5120, heads40/head_dim128, FFN13824, i2v_cross_attn, qk_norm/cross_attn_norm과 eps는 실제 config·state를 확인한다. 자기 임의로 residual/MLP/cross path를 지우거나 축소한 surrogate block을 만들어 통과시키지 않는다.

runtime casting은 Linear weight/bias BF16, norm·modulation 및 공식 FP32 연산 경계를 보존한다. 모든 state를 BF16으로 먼저 캐스팅했다 FP32로 되돌려 round-off를 숨기지 않는다. 원래 hostF32/실행cast후 해시를 구분한다. 기반 전체 requires_grad=False, optimizer에 포함하지 않음. trainable은 B-018와 같은 **self_attn.q/v의 rank4·alpha4·dropout0 LoRA만**이다. cross-attention/FFN까지 LoRA를 새로 추가하지 않는다.

## 3. 인공 입력 계약: 기존 값은 재사용, 추가 조건만 생성

- 소형 x·pseudo target은 B-018 synthetic-fixture.safetensors의 실제값·dtype·해시를 그대로 재사용한다. 같은seed로 재생성하면 된다고 가정하지 않는다. P/개인조건캐시는 사용하지 않는다.
- adapter는 새 Bzero 상태로 시작한다. 가능하면 B-018의 initial A/B를 값 그대로 재사용하되 저장 prefix·schema는 명시한다. B-018 final test adapter를 이어 학습하지 않는다.
- 공식 block 입력 x는 `[1,36,5120]`; toy token grid T1/H4/W4=ref16+video16+pose4. 기존 공식 RoPE/animation T/H/W와 frequency dimension을 유지한다. 입력 x에 `requires_grad=True`를 사용해 앞쪽 블록으로 전할 입력 gradient까지 확인하되 이는 B-018과 다른 검사 범위임을 기록한다. 매 update마다 x.grad도 None으로 비운다.
- **context는 이미 projection된 hidden5120 공간**의 synthetic `[1,769,5120]`로 만든다. 앞257토큰=image, 뒤512=text다. 공식 `WanI2VCrossAttention`은 마지막512개를 text로 분리하므로 context를 임의36토큰으로 줄여 의미를 바꾸지 않는다. 원시 T5 4096 또는 원시 CLIP1280을 여기 넣지 않는다. context_lens는 고정 소스의 실제 None 계약을 따른다.
- `e:[1,6,5120]`는 FP32 synthetic timestep-modulation 입력이다. 실제 t→time-MLP 결과라고 하지 않는다. 사전 fixed 별도 CPU RNG를 사용해 shift/scale은 작은 유한값, self/FFN gate 성분은 비영값을 갖도록 고정한다(예: gate 입력1, 나머지 bounded0.05-scale 값). learned modulation 원본은 수정하지 않는다. 실험 결과 후 gate를 바꿔 gradient를 만들지 않는다.
- context/e는 pseudo condition으로 파일·해시·스케일을 보존하며 실촬영·실제 neural activation 분포를 대신한다고 하지 않는다. baseline·initial·모든 update·reload/OFF에서 같은값을 사용한다.
- loss는 **공식 block 최종 출력과 synthetic target의 FP32 MSE**다. attention 중간 출력에 loss를 붙이면 뒤 cross/FFN backward를 검사한 것이 아니다. B-018의 loss와 함수가 다르므로 숫자를 성능 개선으로 직접 비교하지 않는다. FM/동물 loss로 부르지 않는다.

## 4. 소형 forward/backward/update/reload

CPU fixture에서 metadata·LoRA freeze·shape·dtype·context partition·gate 조건·기대 call count를 먼저 검사한다. B-018 helper/가드를 재사용하고 대형 framework를 만들지 않는다. 정적 타입 진단 중 실제 tensor/경로/optimizer 잘못 연결 가능 항목을 우선 수정하되 무관한 전수 typing 작업에 시간을 소모하지 않는다. NOT_CLEAN이면 그대로 남긴다.

같은 worker에서 B-018의8forward 구조를 유지한다: baseline1, Bzero1, update forward3, trained1, fresh reloaded1, adapterOFF1. backward3, AdamW lr1e-4/wd0·update3이다. 기존allclose atol/rtol1e-3를 사전 기준으로 두고 결과를 본 뒤 완화하지 않는다. zero output error를 새 필수조건으로 삼지 않고 실제 오차를 함께 보고한다.

- 실제 공식 FA2를 유지하고 self/cross_image/cross_text 경로의 실행 및 autograd 연결을 검사한다. backend fallback을 조용히 사용하지 않는다. forward8이 FA kernel8이라는 뜻이 아니므로 구별한다.
- 전체 forward를 no_grad/inference_mode에 넣지 않는다. baseline/reload 검증은 no_grad 가능하지만 학습 경로는 필요 graph를 유지한다. frozen cross/FFN도 그 입력에 대한 derivative는 필요하다. `.eval()`은 gradient OFF가 아니다.
- self-attention 결과→residual→cross-attention→FFN→loss 사이에 detach가 없는지 확인한다. submodule output tensor의 gradient hook에서 **스칼라 finite/norm만** 기록하고 tensor·graph를 리스트로 유지하지 않는다. residual 우회만으로 self LoRA gradient가 존재하는 것을 cross/FFN derivative 증거로 대신하지 않는다.
- trainable 집합과 optimizer parameter ID 집합이 정확히 동일함을 검사한다. 모든 기반 grad=None·runtime hash 불변, adapter finite gradient/parameter delta·input x finite gradient를 보고한다. Bzero에서 첫 A gradient0은 정상일 수 있다. 두 번째 이후 A/B를 실제 관측한다.
- loss 단조감소를 PASS의 필요조건으로 삼지 않는다. gradient/update/serialization 계약과 영상 품질을 구별한다. 이전 실패 로그를 지우거나 추가 update를 수행하지 않는다.
- 새 block 인스턴스를 하나만 순차 적재해 final adapter를 읽고 trained 출력 비교, OFF와 baseline 비교. 둘을 GPU에 동시에 보관하지 않는다. 원본 checkpoint의 선택값 보존과 full65GB rehash 미수행을 정확히 구분한다.

## 5. 조건부 실제 길이 resource-only backward 1회

소형결과·adapter를 먼저 원자저장한다. runtime object/optimizer/graph·grad·출력 검증 복사본을 정리하고 단계별 memory peak를 reset한다. **capacity 검사에서는 optimizer를 삭제한 상태**임을 기록한다. 이 검사가 실패해도 소형 PASS/산출물은 유지한다.

사전 비용 계산이16GiB cap/headroom과 충돌하지 않을 때만 같은 fresh block에 final TEST_ONLY adapter를 활성화해 synthetic x `[1,12992,5120]`와 synthetic target으로 forward/backward1회, step0을 한다. 이 activation은 앞39층 출력이 아니다. 새 deterministic fixture seed와 생성 규칙을 사전 고정하고 전량 공개/ZIP 대형 첨부는 불필요하다.

grid T5/H56/W32, ref1792+generated8960+driving2240=12992를 사용한다. 실제17프레임 추론과 **토큰 길이만 같은** 자원 시험이다. context769·e/원래 precision·RoPE 규약은 유지한다. 큰 영상/모델/조건인코더는 로드하지 않는다. checkpointing·backend 변경·quantization·다른 길이 retry를 자동 추가하지 않는다.

기반/adapter optimizer update는0이며 검사 전후 adapter hash도 유지한다. input 및 adapter gradient finite, 실제 FA backward 여부를 보고한다. 단일 backward 실패/메모리 guard는 원인 단계에 따라 LONG_CAPACITY_BLOCKED로 기록한다. 이것은40block 전체 학습 불가능 판정이 아니다.

memory 기록은 적재, fw 종료, bw 종료, update 후, reload, long stage를 분리한다. CUDA allocated/reserved/peak와 RSS/cgroup/OS memory를 더하지 않는다. 동기화·검사/hash 시간은 순수 kernel benchmark와 구분한다. 283.63MiB×40 또는 한block 측정×40으로 전체 학습 가능을 보증하지 않는다.

## 6. 이론·다음 결정

`lessons/B-019-block-gradient-and-memory.md`에 실제 고정 코드의 흐름을 설명한다.

- time-conditioned normalization/modulation/gate와 residual, self-attention 및 image/text cross-attention·FFN의 차이. 자기 attention의 참조 token 교환과 cross의 CLIP/T5 context를 혼동하지 않는다.
- frozen W의 y=Wx에서는 dL/dW를 저장하지 않아도 dL/dx=W^T(dL/dy)가 필요할 수 있다. LoRA gradient가 뒤쪽 frozen block 연산을 통과하는 chain rule을 유도한다.
- trainable parameter/optimizer state 절감과 activation memory는 다른 문제다. FP32/BF16/norm/gate의 수치 경계 및 FA forward/backward를 코드와 연결한다.
- 전체 layer에 LoRA를 넣는 경우와 마지막 layer만 학습하는 경우의 계산 graph/activation 요구가 다름을 설명한다. 이번 예제는 둘 중 어느 전체 학습도 실행하지 않는다.
- toy token36과 실사용 길이12992, synthetic condition과 실제 encoder activation, pseudo MSE와 Flow Matching loss를 구별한다.
- 직관→식→실제shape/code→gradient/메모리→한계→질문3개와 별도해설.

B-019 후에 block수/토큰을 조금씩 늘리는 감사 시리즈를 자동 생성하지 않는다. 관측값으로 다음 단계의 결정 표 한 개를 남긴다: 사용 가능한 실데이터가 있고 메모리가 타당하면 bounded 실제target/FM pilot 설계; 자료가 없으면 DATA_PENDING을 유지하며 정확한 자산 확보를 우선한다. 근거가 없는데 품질개선 학습을 시작하거나 synthetic loss를 더 줄이는 실험을 반복하지 않는다. B-017 paired-data 경계와 현재 사용자의 로컬 생성/메커니즘/논문 목표를 유지한다.

## 7. 기록·보존·제출

시작 전 CHARTER/ROADMAP/HISTORY/RECORDING_PROTOCOL, B-017/018 RESULTS·TRAIN_INTERFACE·ATTENTION_CONTRACT를 읽는다. 실제 checkout/upstream/weights·dirty 상태를 확인하고 본PLAN의 구현·fixture·예산·dtype/선택키·중지조건을 생성 전에 commit/push한다. 날짜/실행ID는 실제 값으로 고정하며 과거deadline을 재사용하지 않는다.

HISTORY/ROADMAP에 데이터 확보와 구성요소 학습 검증을 분리해 착수/종료를 추가한다. 본 실험의 실제 stage 결과: SMALL_BLOCK_UPDATE_RELOAD, LONG_BLOCK_BACKWARD(PASS/NOT_RUN/BLOCKED)를 별도 보고하고 FULL_MODEL_TRAINING/VIDEO_QUALITY/IDENTITY_POSE_DISENTANGLEMENT=NOT_RUN을 유지한다.

실행 code/비민감config/결과요약/이론/재현만 연구브랜치에 commit/push·remote SHA 확인. 개인 media·private path/IP·모델가중치·condition/latent·secret은 공개하지 않는다. test adapter와 작은 fixture는 비공개 ZIP에만, source weights나 full long tensor는 제외하고 규칙·해시로 남긴다. 로컬 /tmp/의 한ZIP을 Mac/Spark로 보존할 때 전송 여부·CRC·manifest·SHA를 실제 확인한 범위에서 보고한다. 실행이 없는데 완료라고 쓰지 않는다. 자기프로세스 종료를 확인하고 다음 하나만 제안한다.

## 원자료

- B-018 RESULTS/ATTENTION_CONTRACT/component_runner/runtime_guard: commit `19890bea9172db288960de2463b8a9f6c9233140`의 동일 실험 디렉토리.
- 공식 block: https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/modules/model_scail2.py#L331-L471
- PyTorch autograd(개념 확인; runtime 업그레이드 지시 아님): https://docs.pytorch.org/docs/stable/notes/autograd
- LoRA: https://arxiv.org/abs/2106.09685
