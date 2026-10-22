# B-007G — 같은 조건부 벡터장, 다른 구성 요소 수명

현재 상태: **실물 P/S/D 결과 대기**. 아래 실행 계획과 코드 검토는 새 sampler 성공이나 메모리 절감의 실측이 아니다. [계획](../experiments/B-007G-phase-separated-baseline/PLAN.md), [재현 범위](../experiments/B-007G-phase-separated-baseline/REPRODUCE.md)를 함께 읽는다.

## 1. 조건을 먼저 계산해도 되는 이유

SCAIL의 한 sampling step은 noisy video latent `z_sigma`, noise time `sigma`, 조건 `c`로부터 벡터장 `v_theta(z_sigma,sigma,c)`를 평가한다. 여기서 `c`는 text/CLIP/reference/driving/mask의 실제 tensor와 branch별 container 구조다. 물리적 영상 시간은 latent의 T축이며 noise time과 다르다.

고정 입력 `u`를 고정 encoder `E_phi`로 처리하여 `c=E_phi(u)`를 얻는다고 하자. 추론 동안 `u`, encoder 가중치·전처리·dtype·모드가 변하지 않고 encoder 출력이 sampling state에 의존하지 않는다면, 매번 같은 `c`를 계산하는 것과 한 번 계산해 정확한 값으로 다시 읽는 것은 동일한 함수 인자를 제공한다. 별도 프로세스에서 cache를 읽는 일 자체는 새로운 생성 모델이 아니다.

그러나 실제 동등성에는 tensor 값뿐 아니라 list/None, positive/negative branch, mask 순서, device/dtype와 scaling까지 필요하다. 단일 clip의 `history=None`을 임의 history tensor로 바꿔서는 안 된다. [P 코드](../experiments/B-007G-phase-separated-baseline/code/phase_prepare.py)는 공식 함수의 조건 준비 경계에서 저장하고, [S 코드](../experiments/B-007G-phase-separated-baseline/code/phase_sample.py)는 원래의 argument tree를 읽는다. 원형은 [조건 구성과 sampler 호출](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/scail.py#L431-L511)이다.

`eval()`은 dropout 등의 모드를 바꾸며, `no_grad()`는 autograd 기록을 막는다. 서로 대체하지 않는다. 학습에서는 `dL/dphi = (dL/dc)(dc/dphi)`가 필요할 수 있다. `c.detach()` 또는 파일 저장으로 graph를 끊으면 encoder 학습 경로가 사라진다. encoder를 동결한 경우에도 augmentation, crop, reference가 바뀌면 cache의 유효 입력이 달라진다. 이번 작업은 학습이나 gradient 동등성 검증이 아니다.

## 2. solver의 수학과 RNG는 함께 보존한다

교육용 linear path를 `z_sigma=(1-sigma)x+sigma*epsilon`으로 쓰면 velocity target은 `epsilon-x`이고, sampling은 높은 sigma에서 낮은 sigma로 간다. 이는 시간 방향을 반대로 정의한 `x-epsilon` 예제와 부호가 다르다. 실제 구현은 [flow prediction을 clean sample로 변환](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/utils/fm_solvers_unipc.py#L300-L327)하고 UniPC predictor/corrector와 이전 step 기록을 사용한다. 단순 Euler로 교체하지 않는다.

CFG는 `v_cfg=v_null+5*(v_cond-v_null)`이다. 여기의 null은 무조건 모든 조건을 제거한다는 뜻이 아니다. 실제 `arg_null`에서 유지되는 시각 조건과 negative text를 그대로 보존해야 한다. [공식 loop](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/scail.py#L375-L426)의 40 step과 두 branch는 완료 시 80 DiT 호출을 요구한다. 이 수는 계획이며 실제 G 완료 여부는 durable counter로 확인한다.

seed만 같아도 generator의 소비 순서가 다르면 noise가 달라진다. P는 E의 저장된 initial noise와 값 및 SHA를 대조하고, noise 생성 이후 generator state도 저장하도록 구현되어 있다. S는 그 state를 복원하고 resolved timesteps/sigmas의 동등성을 검사한다. pinned [UniPC step](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/utils/fm_solvers_unipc.py#L657-L750)은 `generator`를 인자로 받지만 이 함수 본문에서 사용하지 않으며 해당 파일에는 random sampling 호출이 없다. 이 사실은 다른 scheduler도 deterministic하다는 일반 명제가 아니다.

byte equality는 저장된 tensor와 noise 계약에 적용한다. 동일 입력을 GPU에서 다시 계산한 결과까지 무조건 byte 동일하다고 주장하지 않는다. cache fixture와 공식 함수 추출 검사는 전체 모델의 numerical/video parity 증명을 대신하지 않는다.

## 3. tensor 참조, storage, 장치 이동

Python의 변수 두 개가 같은 tensor/storage를 가리킬 수 있다. 예를 들어 `state_dict`와 `assign=True`로 받은 parameter가 storage를 공유하면 두 이름을 두 payload로 더하면 안 된다. 반대로 dtype cast나 CPU→CUDA 이동은 새 storage를 만들 수 있다. mmap은 파일을 address space에 연결하는 방식이며 모든 페이지가 즉시 RAM에 올라갔다는 뜻도, 읽은 페이지가 공짜라는 뜻도 아니다.

staged loader의 CPU mixed-weight tensor, mmap 파일 페이지, GPU parameter, transfer temporary는 수명이 다르다. `del name`은 참조 하나를 없앨 뿐이다. 다른 module/closure가 storage를 붙잡으면 살아 있다. CUDA allocator가 재사용을 위해 보유한 reserved block도 live tensor와 다르다. `empty_cache()`는 사용하지 않는 cache block을 반환할 수 있지만 살아 있는 parameter를 해제하지 않는다. [PyTorch memory management](https://docs.pytorch.org/docs/2.14/notes/cuda.html#memory-management).

Spark는 CPU/GPU가 같은 물리 메모리를 사용한다. 그렇다고 PyTorch CPU tensor와 CUDA tensor가 항상 zero-copy storage라는 뜻은 아니다. CPU RAM과 GPU capacity를 합산해 128GB를 두 번 세지 않는다. 또한 RSS, cgroup charged memory, CUDA allocated/reserved, 시스템 MemAvailable은 서로 다른 회계다. 합산해 총량으로 만들거나 cgroup cap을 모든 GPU 할당의 상한으로 해석하지 않는다. [NVIDIA UMA 설명](https://docs.nvidia.com/dgx/dgx-spark-porting-guide/latest/overview.html).

CUDA 작업과 복사는 비동기일 수 있다. 측정 경계의 `synchronize()`는 이전 작업의 완료를 기다려 관측 지점을 명확히 하지만 메모리를 자동 해제하거나 다음 단계의 안전을 보증하지 않는다. [PyTorch asynchronous execution](https://docs.pytorch.org/docs/2.14/notes/cuda.html#asynchronous-execution).

## 4. P/S/D 분리가 바꾸는 것

| 단계 | 큰 구성 요소 | 전달하는 값 | 성공의 증거 |
|---|---|---|---|
| P | T5·CLIP·VAE, DiT 없음 | conditions, noise, RNG state, schedule | 저장 후 readback 및 `CONDITION_CACHE_PASS` |
| S | DiT·scheduler, encoder/VAE 없음 | 최종 generated latent | 40 step/80 call, finite, readback 및 `SAMPLER_LATENT_PASS` |
| D | VAE, DiT/encoder 없음 | raw video와 MP4 | decode shape/finite, 17프레임·16fps 및 `VIDEO_OUTPUT_PASS` |

각 worker가 종료되고 PID/context 소멸과 메모리 회복을 확인한 뒤 다음을 시작한다. GPU tensor를 supervisor에 남기거나 CUDA 초기화 뒤 fork하여 공유하는 계획이 아니다. S 종료 시 DiT를 CPU로 다시 복사하지 않는다. 다만 solver의 기존 CPU 계산 위치까지 바꾸는 전역 `offload_model=False` 전환은 하지 않는다.

개략적인 기대는 `peak≈max(M_P,M_S,M_D)+overhead`다. 이것은 자연 peak의 보장된 상한도 실측 절감량도 아니다. file cache, driver, 다른 작업, device 전환 temporary가 남으며 각 단계 내부에서도 weight와 activation이 겹친다. 분리는 재로딩과 파일 I/O 비용을 늘릴 수 있다. E/F의 차이를 이 가설 하나로 소급해 설명할 수 없다.

attention의 중간 tensor는 weight 상주와 별개다. E에서 관측한 12,992 tokens, 40 heads의 naive score는 `40*12992^2` elements지만 FlashAttention은 전체 score matrix를 그대로 materialize하지 않는다. 따라서 이 식은 실제 allocator peak가 아니다. 이번 분리는 attention 알고리즘을 변경하지 않는다.

## 5. latent와 출력의 실제 의미

E에서 관측한 공식 generated latent는 `[16,5,64,112]` FP32다. 같은 설정을 사용하는 G의 예상 shape이며 G 실측으로 미리 표시하지 않는다. FP32 payload는 `16*5*64*112*4=2,293,760` bytes다. 작은 latent 파일을 보존하면 sampler와 decoder의 결과를 분리할 수 있지만, 마지막 update 이전의 noise/reference를 final latent로 부르면 안 된다.

D는 [공식 VAE decode](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/modules/vae.py#L544-L568)를 사용한다. 내부에서 cache를 reset하고 `z/scale[1]+scale[0]` 역변환을 수행한다. 외부에서 같은 scale을 다시 적용하지 않는다. P의 encoder feature cache를 D로 옮길 필요가 없다는 근거는 이 명시적 reset과 decoder의 새 temporal cache다. temporal cache 자체를 끄거나 새로운 chunk 전략으로 바꾸는 것은 이번 범위가 아니다.

예상 raw video는 `[3,17,512,896]`, 공식 출력은 16fps다. 17/16=1.0625초의 파일 재생 길이와 첫 프레임부터 마지막 프레임까지 16/16=1초의 시점 간격은 다르다. noise-time 40 step을 영상 40프레임으로 해석하지 않는다. 파일 검증 성공도 사람의 연속 재생 품질 관찰을 대신하지 않는다.

## 6. 관측과 한계

E는 첫 forward finite PASS와 sampler 40/40 로그를 남겼지만 offload/decode 경계에서 guard가 종료했다. F는 첫 forward 이전에 guard가 종료하여 post-loop 개입이 실행되지 않았다. 둘 다 final latent와 MP4가 없으며 정확한 중간 allocating operation은 UNOBSERVED다. G의 P/S/D 실물 결과, 단계별 peak와 시간은 아직 이 문서에 등록되지 않았다. 학습·LoRA·Lab·identity/motion 품질 수용은 이 구조 검증으로 통과하지 않는다.

## 이해 확인 질문

1. 같은 input을 사용하더라도 encoder cache가 학습 결과를 바꿀 수 있는 경우는 무엇인가?
2. `state_dict`와 parameter의 byte 수를 더한 값이 실제 payload보다 클 수 있는 이유는 무엇인가? 반대로 UMA에서 device 이동 peak를 무시하면 왜 위험한가?
3. final latent가 정확하게 보존됐다는 증거와 영상 품질이 좋아졌다는 증거는 어떻게 다른가?

## 해설 — 먼저 질문에 답한 뒤 읽기

1. encoder가 trainable이면 cache 파일은 `dc/dphi` graph를 끊는다. 동결해도 augmentation/crop/reference가 바뀌면 동일한 조건이 아니다. eval/no_grad는 각각 모드와 graph 기록을 다루므로 둘을 구분한다.
2. 같은 storage를 가리키는 이름은 별도 사본이 아니다. 반면 CPU/CUDA 이동이나 dtype 변환은 새 storage와 temporary를 만들 수 있다. UMA는 물리 용량의 공유이지 모든 연산의 zero-copy 계약이 아니다.
3. shape/dtype/finite/hash/readback와 완료 step/call 수는 어떤 tensor가 전달됐는지 입증한다. 실제 decode와 raw/MP4, 이어지는 형태·움직임 관찰이 있어야 시각 품질을 판단할 수 있다. 그중 어느 단계도 다른 단계를 자동 승인하지 않는다.
