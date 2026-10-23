# B-007H — CUDA 상태와 실제 연산을 구별하기

현재 H 실물 결과는 **PROBE PASS / SAMPLER_LATENT_PASS / VIDEO_OUTPUT_PASS**다. probe는 6.062초에 service_exit0·PID0으로 종료했다. [PLAN](../experiments/B-007H-cuda-lifecycle/PLAN.md)의 개입은 큰 CPU 가중치 적재 전에 작은 실제 CUDA 연산을 완료하는 순서 변경이다. 새로운 모델이나 생성 방식이 아니다. [G 결과](../experiments/B-007G-phase-separated-baseline/RESULTS.md)는 보존하며 초기화 순서가 실패 원인이라고 미리 결론 내리지 않는다.

## 1. 초기화되었다는 말에는 여러 의미가 있다

| 관측 | 입증하는 범위 | 입증하지 못하는 것 |
|---|---|---|
| `torch.cuda.is_initialized()` | PyTorch CUDA runtime 초기화 상태 | 다음 allocation·copy·kernel의 성공 |
| primary context `active` | 해당 driver primary context의 active 상태 | 필요한 크기의 메모리 여유, 모델 실행 가능성 |
| 작은 CUDA allocation | 그 시점·크기의 할당 성공 | 전체 DiT 이동 또는 activation peak 수용 |
| CPU→CUDA copy | 해당 값의 전송 경로 성공 | kernel 계산 결과 |
| kernel + synchronize + CPU readback | 해당 작은 연산의 완료와 값 | 전체 sampler·VAE·영상 품질 |

[PyTorch is_initialized](https://docs.pytorch.org/docs/2.14/generated/torch.cuda.is_initialized.html)는 runtime 상태를 반환한다. 따라서 G의 `true`를 무시하고 “CUDA 초기화가 전혀 없었다”고 쓰면 안 된다. 반대로 그 값만으로 정상 allocation과 연산을 이미 검증했다고 써도 안 된다.

[NVIDIA primary context API](https://docs.nvidia.com/cuda/cuda-driver-api/cuda_driver_api/group__CUDA__PRIMARY__CTX.html)는 device별 primary context를 runtime과 공유한다고 설명한다. `GetState`는 active와 flags를 조회하고 `Retain`은 context 사용을 확보한다. 문서상 이 API들은 이전 비동기 작업의 오류를 전달할 수도 있다. 어떤 함수 이름에서 오류가 보였다는 것과 내부 원인 할당을 특정했다는 것은 다르다. PyTorch 등 다른 라이브러리가 소유한 context를 진단 코드가 임의 reset/release하지 않는다.

진단 API 자체도 실행 순서에 포함된다. import, device 조회, `init`, memory 조회가 상태를 바꿀 가능성을 구분하여 호출 전후를 남긴다. “관찰만 했다”는 이름으로 초기화 개입을 숨기지 않는다. H는 실제 작은 copy와 계산을 주개입으로 명시한다.

## 2. 작은 probe는 무엇을 검증하는가

실제 [cuda_probe.py](../experiments/B-007H-cuda-lifecycle/code/cuda_probe.py)는 값3인 FP32 tensor `[16]`을 CUDA로 복사하여 `add_(2)`를 수행하고 synchronize 뒤 CPU 값이 모두5인지 확인했다. 보존하는 anchor payload는64 bytes다. 이것은 seed를 소비하는 `randn` warmup과 다르다. payload는 승인된 1MiB 이내다. tiny 연산 전후에는 CPU RNG 상태의 동일성을 확인했다. CUDA RNG 상태 조회 자체가 초기화에 영향을 줄 수 있어 tiny 이전에는 조회하지 않았다. 실제 CUDA RNG 비교 범위는 tiny 성공 후부터16개 cache leaf 복원 이후까지이며 같았다. 이를 tiny 전후 CUDA RNG 상태를 직접 측정한 증거로 확대하지 않는다. tiny 코드에는 RNG 연산이 없고 initial noise hash 계약은 별도로 유지한다.

CUDA 연산은 비동기일 수 있다. launch 함수 반환은 완료 증거가 아니므로 synchronize와 readback을 구분한다. 동기화는 완료 경계를 만들지만 살아 있는 tensor를 해제하지 않는다. allocator allocated는 live tensor, reserved는 allocator가 확보한 block에 관한 관측이고 driver 비용 전체가 아니다. [PyTorch CUDA semantics](https://docs.pytorch.org/docs/2.14/notes/cuda.html#asynchronous-execution).

모델 없는 probe가 통과해도 모델 적재 뒤 같은 연산이 실패할 수 있다. H는 fresh worker의 동일 서비스 환경에서 작은 probe를 한 번 수행하고, 성공한 경우에만 다른 fresh worker에서 작은 연산→CPU DiT 적재→조건 복원→device 이동 순서를 한 번 실행한다. 셸 probe의 성공을 systemd worker 성공으로 대체하지 않는다.

## 3. UMA와 cgroup 수치를 합산하지 않는 이유

개념적으로 `M(t)=W_live(t)+A_live(t)+C_cache(t)+D_driver(t)+O(t)`라고 나누어 생각할 수 있다. W는 가중치, A는 activation, C는 cache, D는 driver 비용, O는 나머지다. 이는 중복 없는 물리적 원인을 찾기 위한 모형이다. **RSS+cgroup+CUDA allocated를 더하는 계산식이 아니다.**

G 마지막 CPU 적재 phase에서 cgroup current는 66,564,358,144 bytes, anon은 33,082,748,928 bytes, file은 33,285,410,816 bytes였다. 시스템 MemAvailable은 62,777,077,760 bytes이고 CUDA allocator는 0이었다. 이 서로 다른 회계는 “RAM은 충분하니 CUDA 오류가 거짓”이나 “allocator가 0이니 driver도 메모리를 안 쓴다”를 입증하지 않는다. 물리 메모리 공유는 tensor storage의 무조건적인 zero-copy 계약도 아니다.

[Linux cgroup v2](https://docs.kernel.org/admin-guide/cgroup-v2.html)는 high를 reclaim/throttling 경계로, max를 hard limit로 구분한다. G의 high2660과 oom/oom_kill0은 서로 다른 사건이다. 하위 service 제한 외에 상위 cgroup 제한도 영향을 줄 수 있다. 제한을 읽는 것과 완화하는 것은 별개이며 H는 변경하지 않는다.

동일 checkpoint와 seed도 file page residency, allocator 상태, 다른 작업의 상태를 같게 만들지는 않는다. CPU weight 적재 전에 작은 CUDA 연산을 넣고 성공하더라도, 단 한 번의 비교로 G 오류의 유일한 원인이 초기화 순서였다고 증명할 수 없다.

## 4. 캐시 재사용은 같은 생성 계약을 유지하는가

계산은 `c=E(inputs)`, `z=Sample(v_theta,c,noise)`, `video=D(z)`로 나눌 수 있다. H는 G에서 실제 저장한 c를 재사용한다. c는 text/CLIP/reference/driving/mask와 branch별 구조를 포함하고, noise와 generator state도 별도로 보존됐다. G 캐시 SHA는 `1f1e0b68495b2276a5b6d12eaf160897a16acb2bd2a089e616a55c40bf590308`이다. 이 캐시는 denoised z가 아니므로 바로 decode할 수 없다.

조건부 벡터장 `v_theta(z_sigma,sigma,c)`에 같은 값을 주려면 dtype·device·list/None·mask 순서를 보존해야 한다. CPU 검증을 위해 읽은 tensor를 전부 CUDA로 옮기면 원래 device 계약이 달라진다. H는 실제16개 leaf를 원래 device로 복원하고 roundtrip 값 hash를 확인했다. 공유 값이 별도 storage로 저장된 G의 alias 한계도 유지한다.

공식 [sample loop](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/scail.py#L375-L426)의 CFG5, UniPC40 step, shift3 및 CPU solver 계산을 유지한다. 작은 warmup은 수학적 noise를 바꾸지 않아야 한다. eval·precision·입력 값이 같다는 계약 검사는 GPU 전체 출력의 byte-identical 증명을 대신하지 않는다. encoder를 학습한다면 캐시 파일은 gradient graph를 보존하지 않으므로 이 추론 논리를 그대로 적용할 수 없다.

## 5. 결과를 해석할 경계

H의 probe, CPU weight load, cache device restore, DiT device move, first forward, sampler, final latent, decode, video는 각각 별도 결과다. P는 H에서 실행하지 않으며 G의 성공 artifact를 parent로 연결한다. 실제 probe에서는64-byte copy/add/synchronize/readback과16개 leaf의 원래 device 복원·값 hash가 모두 통과했다. `cuDevicePrimaryCtxGetState`는 새 driver binding을 추가하지 않아 NOT_CALLED였다. S는 실제80회 forward와40 step을 완료했다. D도 완료해 raw/MP4를 확보했다. 시간 품질은 UNVERIFIED다. 작은 probe 자체가 이를 보장한 것은 아니며 S의 별도 실행 기록이 근거다. 실패한 뒤 재시도하거나 다른 backend로 바꾸는 계획이 아니다. 성공해도 공식 사람 예제의 baseline이며 Lab 개체·안무·Kling 품질 수용은 아니다. 직접 연속 재생이 없으면 시간 품질은 UNVERIFIED다.

### S 실제 관측

S는 약204초에 CPU 적재를 완료한 뒤 tiny 재검사와16개 original-device 조건 복원에 통과했다. DiT device 이동도 통과했고 stage 시작240.642초에 `first_forward_start`가 관측됐다. 해당 시점 CUDA allocated는33,268,072,448 bytes, 시스템 MemAvailable은59,302,164 KiB였다. G에서 실패한 복원 경계를 이번 실행에서는 넘었다는 증거이며, 초기화 순서가 유일한 원인이라는 증명은 아니다. 이후 S는80회 forward·40 step을 완료하여 stage_S_complete가1196.45초에 기록됐다. S의 전체 guard 시간은1199.009초이며, final latent 값 hash는 initial noise와 다르다. S 종료와 자원 회복 뒤 별도 D가 phase 기준13.262초에 완료해 VIDEO_OUTPUT_PASS를 기록했다. D 전체 guard 시간은15.228초이며 decode 구간은6.720초다. 단계 완료13.262초와 guard 전체 시간을 혼동하지 않는다. 실제 연속 재생 품질은 UNVERIFIED다. 실행 순서 변경이 관측된 실패 경계를 넘게 한 사실은 새 생성 방법이나 G 원인 확정의 근거가 아니다.

다음 제안은 기존 입력을 사용하는 Lab17프레임 고정 baseline 한 가지이며 이번에는 실행하지 않았다. 공식 사람 예제의 출력 확보는 Lab identity·안무 수용이나 초기화 순서의 유일한 인과 증명이 아니다. 추가 sampler·decode·실험은 실행하지 않는다.


최종 [장부](../experiments/B-007H-cuda-lifecycle/RUN_LEDGER.json)와 [실측](../experiments/B-007H-cuda-lifecycle/MEASUREMENTS.json)을 대조했다. S의 CPU load 구간은201.431초, DiT device 이동35.968초, 첫 forward14.291초다. S 최소 MemAvailable은56,311,533,568 bytes, 관측 cgroup peak66,577,215,488 bytes, phase snapshot의 CUDA peak allocated36,325,785,600 bytes였다. D의 같은 세 항목은 각각81,109,180,416 / 2,340,904,960 / 9,565,265,920 bytes다. 서로 중복되는 회계를 합산하지 않으며 phase snapshot을 미관측 순간의 절대 peak라고 하지 않는다. S high2426에도 oom/oom_kill0, 모든 stage swap0이었다.

최종 latent는 finite FP32 `[16,5,64,112]`, readback exact다. 값 SHA는 `f129057bb2cbaca33cc0e494eb472c6ccf03a753fcf37afc48e0649ddf075bd6`으로 initial noise와 다르며, 파일 SHA와 별개다. 실제 raw는 finite `[3,17,512,896]`, MP4는17프레임·16fps·1.0625초다. 모든 자체 worker는 PID0/inactive이며 retry0, P 재실행0, model load1, sampler1, decode1이다.

## 이해 확인 질문

1. `is_initialized=true`, allocator0, `cuDevicePrimaryCtxRetain` 오류가 동시에 기록돼도 모순이라고 단정할 수 없는 이유는 무엇인가?
2. 작은 copy/add/readback probe가 통과했는데 DiT 이동은 실패했다면 무엇까지 결론 내릴 수 있는가?
3. 같은 G cache와 seed를 사용해도 실행 동등성을 위해 추가로 보존해야 하는 것은 무엇인가?

## 해설 — 질문과 분리해서 읽기

1. runtime 상태, allocator tensor 회계, driver context 작업은 서로 다른 층이다. allocator0은 driver의 모든 비용이나 다음 할당 가능성을 나타내지 않는다. 실제 오류 시점의 내부 원인은 추가 증거 없이 UNKNOWN이다.
2. 작은 연산 경로가 해당 시점에 동작했다는 사실만 확정한다. 모델 적재 뒤의 메모리·context 상호작용 범위를 조사할 수 있지만 high events 하나로 누수·OOM 원인을 확정할 수 없다.
3. 실제 noise 값과 RNG state/소비 순서, leaf device·dtype·shape·branch 구조, scheduler state와 solver 계산 위치, precision/eval 정책을 유지한다. seed나 파일명만 같다는 것은 부족하다.
