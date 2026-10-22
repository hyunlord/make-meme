# B-007F — 통합 메모리에서 tensor의 수명 관리

현재 B-007F는 **첫 DiT forward 이전 시스템 headroom guard 종료**다. [계획](../experiments/B-007F-post-sampler-memory/PLAN.md)에 따라 실제 결과와 도달하지 못한 정책 변경을 아래에 구분한다. B-007E의 성공·실패는 선행 관측이며 이번 결과를 대신하지 않는다.

## 1. 직관: 이동·해제·캐시 반환은 다르다

`model.cpu()`는 모델을 버리는 연산이 아니다. GPU tensor 값을 CPU tensor로 옮기고 모델이 계속 그 값을 소유하게 한다. Spark의 CPU/GPU는 물리 메모리를 공유하므로 CPU로 옮겼다는 사실만으로 시스템 가용 메모리가 늘었다고 결론 내릴 수 없다. device와 allocator가 다르면 복사 중 source·destination이 함께 존재할 수 있다. [NVIDIA 구조 설명](https://docs.nvidia.com/dgx/dgx-spark-porting-guide/latest/overview.html).

`del`은 Python 참조 하나를 제거한다. 다른 객체·closure·list가 tensor를 붙들고 있으면 실제 storage 수명이 끝나지 않는다. 마지막 참조가 사라진 뒤에도 CUDA allocator가 재사용하려고 block을 보유할 수 있다. `empty_cache()`는 사용하지 않는 allocator cache를 반환하며 살아 있는 tensor를 없애지 않는다. GPU DiT를 유지한 이번 정책에서 empty_cache가 DiT parameter 자체를 반환할 것으로 기대하면 안 된다. [PyTorch CUDA memory 설명](https://docs.pytorch.org/docs/2.14/notes/cuda.html#memory-management).

## 2. 한 위치만 바꾸는 이유

[고정 scail.py421](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/scail.py#L421)의 순서는 post-loop `model.cpu()` → `empty_cache()` → `vae.decode(x0)`다. 이번 단일 정책 변경은 첫 이동만 생략하는 것이다. empty_cache와 앞선 sampler offload는 유지한다.

`offload_model=False`로 전역 변경하면 [noise_pred와 latent의 CPU 이동](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/scail.py#L391)까지 달라진다. 이는 다른 실험이다. 모든 Module.cpu를 막는 monkey patch도 해당 위치만 바꾼다는 계약을 지키지 못한다.

B-007E에서 DiT payload는33,166,820,096 bytes였다. CPU copy와 아직 allocator에 남은 GPU block이 동시에 존재할 수 있다는 가설은 있지만 실제 순간 복사량 전체를 측정한 것은 아니다. GPU에 DiT를 유지하면 이 전이를 피할 가능성이 있는 대신 decode 중 parameter가 계속 GPU allocator에 상주한다. 어느 쪽이 성공하는지는 이번 실측 문제다.

## 3. 최종 latent는 생성 영상도 initial noise도 아니다

마지막 [scheduler.step와 history 적용](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/scail.py#L410) 뒤 `x0`가 실제 decode 입력이다. 저장 대상은 reference latent·noise prediction·initial noise가 아닌 이 generated latent다. progress bar40/40만으로 durable final latent를 얻었다고 할 수 없다.

공식 예제의 예상 shape는 `[16,5,64,112]`, 원소 수는 `16×5×64×112=573440`이다. FP32 payload는2,293,760 bytes, BF16은1,146,880 bytes다. dtype와 실제 파일 overhead는 runtime에서 확인한다. 이것은 DiT33GB를 CPU로 복사하는 것과 규모가 다른 보존 작업이다.

복원된 pixel tensor `[3,17,512,896]`는23,396,352원소이며 FP32 payload는93,585,408 bytes다. 이 계산은 최종 output 크기이지 VAE peak가 아니다. decoder의 중간 feature·cache·누적 cat output이 더 클 수 있다. [VAE decode544](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/modules/vae.py#L544)는 latent scale 복원 후 시간 slice별 decoder와 feature cache를 사용한다.

Sidecar는 VAE 코드/weights와 scale 규약을 보존해야 한다. latent를 미리 inverse-scale한 뒤 같은 decode wrapper가 다시 inverse-scale하면 입력이 바뀐다. 원본 decode 인자의 값을 그대로 저장하고, shape/dtype·finite·scheduler 종료·segment/reference 포함 여부와 입력/config/noise hash를 함께 기록한다.

## 4. 저장 완료와 비동기 계산 완료

CUDA 호출은 CPU가 kernel 제출을 마쳤을 때 반환할 수 있다. wall-clock만 재면 제출 시간과 실제 계산 완료가 섞인다. 필요한 경계의 synchronize는 앞선 오류를 드러내고 완료 시점을 정하지만 실행 timing도 바꾼다. B-007E와 완전히 같은 계측 조건이라고 주장하지 않는다. [PyTorch 비동기 실행](https://docs.pytorch.org/docs/2.14/notes/cuda.html#asynchronous-execution).

저장 흐름은 sampler 완료 확인 → 제한된 CPU copy → finite/shape/value 확인 → temporary file → flush/fsync → atomic publication → hash/sidecar 확인이다. CPU copy가 끝났다고 디스크 보존까지 완료된 것은 아니다. sidecar만 있고 tensor가 partial이면 FINAL_LATENT_SAVED가 아니다. 관측 hook은 GPU tensor를 전역 list에 쌓지 않아야 한다.

## 5. peak를 측정하는 방법과 guard

parameter 이론 크기는 `Σ numel(parameter)×itemsize`이고 실행 peak는 `max_t M(t)`다. phase별 peak를 더하면 동시에 존재하지 않는 메모리를 중복 계산할 수 있다. allocated는 살아 있는 allocator tensor 중심, reserved는 allocator가 확보한 block, RSS는 프로세스 resident mapping, cgroup은 별도 charge 범위다. 이 숫자들을 더해 물리 사용량이라고 하지 않는다.

B-007E에서 cgroup 약16GB와 CUDA allocated 약34GB가 동시에 관측됐다. 따라서 cgroup cap만으로 GB10 전체 CUDA 사용을 제한했다고 말할 수 없다. 시스템 MemAvailable·swap watchdog을 유지한다. 시작72GiB·실행 중24GiB 하한은 보수적인 운영 정책이며 DGX의 공식 안전 한계라는 뜻이 아니다.

각 경계에서 monotonic/wall time, MemAvailable, swap, VmRSS/RssAnon/VmHWM, cgroup current/peak/events와 anon/file, CUDA allocated/reserved/peak를 읽는다. offload SKIPPED와 empty_cache 전후, VAE 진입/완료를 따로 남기면 실패 subphase를 분리할 수 있다. 첫 forward peak를 decode peak로 재사용하지 않는다.

## 6. 이번 판정의 범위

B-007E는 로그40/40 뒤 guard로 종료됐고 정확한 offload/decode 위치는 UNOBSERVED다. 이번에 성공하더라도 CPU offload가 유일한 원인이었다고 완전 증명되지는 않는다. 계측 비용과 시스템 상태 차이가 있고 과거 final latent도 없기 때문이다.

- final latent만 보존: FINAL_LATENT_SAVED, MP4 성공 아님.
- decode 실패: 공식 run 종료, Lab NOT_RUN, 자동 재시도 없음.
- raw finite/17f 및 실제 MP4 decode·fps·guard 정상 종료: VIDEO_OUTPUT_PASS.
- 개체·안무·시간 품질: 별도의 시각 검토. 연속 재생을 보지 못하면 UNVERIFIED.

이번 phase·메모리 관측과 미실행 항목은 아래 실제 결과에 기록했다. 원본 및 B-007E 실패를 덮어쓰지 않는다.

## 이해 질문

1. GPU model을 CPU로 옮기는 것과 마지막 참조를 지우는 것, empty_cache를 호출하는 것은 어떻게 다른가?
2. generated latent와 initial noise의 shape가 같다면 어느 것을 저장해도 VAE decode를 재개할 수 있는가? 필요한 sidecar 항목은 무엇인가?
3. cgroup current가24GiB보다 작은데 시스템 MemAvailable이24GiB 아래일 수 있는가? synchronize와 phase hook을 추가한 뒤 이전 run과 시간 차이를 어떻게 해석해야 하는가?

## 별도 해설

1. CPU 이동은 값과 모델 소유를 유지한다. 마지막 참조 제거는 storage 해제를 가능하게 하지만 allocator cache가 남을 수 있다. empty_cache는 사용하지 않는 cache를 반환하며 살아 있는 parameter를 삭제하지 않는다. 통합 메모리에서는 device 이동이 물리 용량 해방을 보장하지 않는다.
2. 아니다. initial noise는 sampler 시작 상태이고 generated latent는 scheduler/history 처리가 끝난 decode 입력이다. VAE code/weights·scale 규약, 실제 shape/dtype·finite/hash·완료 step, input/config/noise hash와 segment/reference 포함 여부가 필요하다. 파일의 atomic 완료도 확인해야 한다.
3. 가능하다. 회계 범위가 다르고 cgroup 밖의 작업 및 GPU allocation·공유 page가 있다. 시스템 가용 메모리도 직접 감시해야 한다. synchronize와 hook은 timing을 바꾸므로 완료 경계를 더 정확히 관측한 사실과 성능 개선 주장을 구분한다.

## 사전 고정 구현 연결

commit `97189c029ac298b0aded73990d1858d5df9b93bf`의 [runtime_patch.py](../experiments/B-007F-post-sampler-memory/code/runtime_patch.py)는 기존 post-loop 블록 하나와 step 완료 지점 하나가 정확히 일치해야 패치한다. [runtime_transition.py](../experiments/B-007F-post-sampler-memory/code/runtime_transition.py)는 최종 latent 보존과 선택한 이동 생략·decode 경계를 담당하며, [runtime_observe.py](../experiments/B-007F-post-sampler-memory/code/runtime_observe.py)는 phase 관측을 기록한다. 실제 시작·완료 판정은 [runtime_infer.py](../experiments/B-007F-post-sampler-memory/code/runtime_infer.py)의 durable 기록과 guard 결과를 함께 읽는다. 코드 고정과 작은 mock 검증은 이번 실제 메모리·영상 결과가 아니다.

## 실제 결과: post-loop 변경에 도달하지 못함

전체 pipeline 적재는331.4초, preprocess 완료까지340.9초였다. initial noise hash는 B-007E와 일치했고 저장된 forward counter는0이었다. 첫 forward 진입·완료 관측은 없으며, 이 값은 최종 counter 실측이 아닌 저장 스냅샷이다. sampler 예약은 새 상한2회 중1회 사용으로 보존한다. 마지막 durable phase는 `pipeline_loaded`이며 첫 forward 이전의 정확한 종료 subphase는 **UNOBSERVED**다.

MemAvailable=25,676,087,296 bytes가24GiB(25,769,803,776 bytes) 아래로 내려가 guard가 중단했다. swap0·OOM0이다. 이전 B-007E와 달리 sampler40step이나 post-loop 경계에 도달하지 않았다. 그러므로 post-loop CPU 이동 생략은 **NOT_REACHED**이며 성공도 반증도 아니다. 동일 initial noise는 동일 완료 결과의 증거가 아니다.

최종 latent·decoded raw·MP4는 없다. Lab는 NOT_RUN이고 자동 재시도는 없다. final-save 구현의 순서·실패 보존은 작은 mock으로만 검증됐으며 실제 최종 latent 보존 성공이라고 보고하지 않는다. initial noise를 final latent처럼 decode하는 것도 금지한다.

다음 한 제안은 **CPU-only 사전 forward 메모리 수명·guard trace 감사**다. 기존 로그와 고정 코드에서 pre-forward model.to(device)의 parameter 소유·이동 순서, 시스템 메모리 표본과 phase 간격을 대조한다. 이 조사에서는 GPU 적재·sampler·decode를 실행하지 않는다. 정확한 subphase를 입증할 증거가 부족하면 UNKNOWN을 유지하며, 새 sampler 예산이나 guard 완화로 자동 확대하지 않는다. final latent가 없으므로 decode-only 실험을 현재 재개 경로로 제안하지 않는다.
