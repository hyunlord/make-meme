# E/F CPU-only 메모리 비교

판정: **F에서 정확히 어느 할당 연산이 시스템 메모리를 감소시켰는지는 UNKNOWN**이다. F의 post-sampler 정책은 실행되지 않았다. 동일 가중치·입력·초기 noise는 확인되지만, 시작 메모리·page cache·allocator 상태까지 동일한 대조 실험은 아니다. 이번 감사는 기존 파일 읽기와 JSON 계산만 수행했고 모델을 적재하지 않았다.

## 같은 단계에서 확인한 값

단위는 GiB다. 아래 수치를 더해 총메모리를 계산하지 않는다. OS 가용량, 프로세스 RSS, cgroup charge, CUDA allocator는 서로 다른 회계다.

| 단계 | E 가용량 | F 가용량 | E RSS anon/file | F RSS anon/file | E CUDA allocated/reserved | F CUDA allocated/reserved |
|---|---:|---:|---:|---:|---:|---:|
| 첫 resource 표본 | 88.302 | 87.453 | 미제시 | 미제시 | UNOBSERVED | UNOBSERVED |
| pipeline 적재 완료 | 42.744 | 40.216 | 42.191 / 19.477 | 42.548 / 19.638 | 1.693 / 2.984 | 1.693 / 2.984 |
| 전처리 뒤 pipeline_loaded | 42.326 | 40.077 | 42.523 / 18.244* | 42.849 / 18.342 | 1.693 / 2.984 | 1.693 / 2.984 |
| 첫 DiT forward 진입 | 41.331 | UNOBSERVED | 15.337 / 1.609* | UNOBSERVED | 31.736 / 31.789 | UNOBSERVED |
| 첫 DiT forward 완료 | 37.731 | UNOBSERVED | 14.550 / 0.073* | UNOBSERVED | 31.761 / 34.748 | UNOBSERVED |
| guard 마지막 표본 | 23.899 | 23.913 | JSON 참조 | JSON 참조 | UNOBSERVED | UNOBSERVED |

`*` E의 run-level phase는 VmRSS만 저장하므로 anon/file은 가장 가까운 resource 표본이다. 동일 시각 측정인 것처럼 해석하지 않는다. [JSON](E_F_COMPARISON.json)은 표본 시차, phase별 cgroup anon/file/high/max/oom, swap, CUDA peak와 증거 파일 SHA를 포함한다. E 모델 phase에는 cgroup 측정이 없어 가까운 표본을 연결했고, F 모델 phase는 직접 cgroup snapshot을 저장했다. 서로 다른 시점/회계의 차이는 교정하거나 평활화하지 않았다.

적재 소요는 E 268.587초, F 331.441초다. E 첫 forward는 finite로 완료했으며 최종 실제 model-call counter는 남아 있지 않다(저장된 1은 첫 forward snapshot). E의 40/40은 progress log 증거이며 최종 latent 완료의 증거가 아니다. F는 저장된 forward_calls=0, 첫 forward phase 없음이다. 두 실행 모두 최종 latent·decoded raw·MP4가 없다.

## 관측 가능한 경계와 없는 경계

Text encode, reference VAE encode, CLIP encode, driving VAE encode, 초기 noise 생성, DiT CPU→device 이동의 개별 start/end 메모리는 **양쪽 모두 UNOBSERVED**다. 초기 noise 파일은 양쪽에 있고 SHA가 같다. 이는 정확한 operation별 peak 기록을 대신하지 않는다.

실제 E runtime `wan/scail.py`에서 reference encode L292 → text L329–339 → CLIP L341–344 → driving encode L441–444 → noise L477–484 → sample_func 호출 L517 → DiT 이동 L387–389 → 첫 forward L397 순서다. F는 이 앞부분을 유지했다. 따라서 noise 저장과 첫 forward 부재는 실패 범위를 좁히지만, `.to(device)` 내부의 어떤 allocation이 실패 원인인지 특정하지 않는다. Noise 이후 dict/조건 구성, empty_cache, model 이동, 첫 호출 앞의 latent/timestep 작업이 있으며 세부 hook이 없다.

F 마지막 구간에서 cgroup/RSS가 감소하는데 MemAvailable도 감소한다. CUDA의 이 구간 연속 표본은 없다. 이를 누수, CUDA 증가 또는 CPU/GPU 복사 peak의 직접 증명으로 보고하지 않는다. F의 실제 cap은 68,140,400,640 bytes로 `min(64 GiB, initial available−24 GiB)`다. E의 64 GiB cap과 숫자가 다르지만 guard 식은 같다. 양쪽 swap0/OOM0이며 headroom 위반으로 종료했다. 종료 코드0은 영상 성공이 아니다.

타 작업에 대해서는 사전/사후 기존 서비스 1개와 queue idle 기록만 확인했다. phase마다 모든 외부 프로세스의 메모리를 기록하지 않았으므로 타 작업 메모리가 완전히 일정했다고 주장할 수 없다.

## 객체·storage 수명

[객체 수명 표](OBJECT_LIFETIME.md)는 실제 E runtime 위치와 F 계승 경로를 구분한다. 핵심은 다음과 같다.

- `cast_state`와 assign된 model은 같은 payload를 가리킨다. dict 두 개를 DiT 두 사본으로 세지 않는다. FP32 passthrough는 mmap storage를 참조할 수 있어 safe_open context 종료만으로 페이지가 모두 사라진다고 보장하지 않는다.
- T5/CLIP checkpoint dict는 load 호출의 임시 값이며 default `load_state_dict`는 생성된 model에 복사한다. mmap 페이지·캐시가 즉시 회수되는지는 별도다. 생성 후에도 pipeline은 T5, CLIP, VAE, DiT를 계속 보유한다.
- 조건 인코딩 뒤 CLIP `.cpu()`는 객체 제거가 아니다. T5는 CPU, VAE는 CUDA, DiT는 CPU에서 시작한다. 조건과 CPU encoder weights가 살아 있는 상태에서 DiT 이동이 일어난다. 이 동시 수명은 코드로 확인되지만 E/F 실패 차이의 원인 증명은 아니다.
- 후크는 shape/dtype/device와 숫자·hash를 저장한다. wrapper closure 및 condition dict는 참조를 더하지만 큰 tensor clone을 자동 생성하지 않는다. 초기 noise 관측에는 작은 명시적 CPU copy가 있으며, 호출 후 전역에 GPU tensor를 누적하는 코드가 없다.
- VAE encode/decode는 각각 시작/정상 종료 시 cache를 비운다. 새 decode 프로세스에 이전 encode feature cache를 옮길 필요가 있다는 근거가 없다. scaling·dtype·원형 wrapper는 그대로 보존해야 한다.

단계 분리는 이미 확인된 component 동시 수명을 줄이는 engineering 가설로 진행할 수 있다. 알려지지 않은 F allocation 원인을 증명했다고 전제하지 않는다. 다음 코드에는 condition 인코딩과 DiT 이동 전후의 명시적 phase가 필요하며, 관측을 추가해도 E/F와 완벽한 통제 성능 비교가 되지는 않는다.

## 근거와 범위

- [E RESULTS](../B-007E-scail-forward/RESULTS.md), [E MEASUREMENTS](../B-007E-scail-forward/MEASUREMENTS.json), [F RESULTS](../B-007F-post-sampler-memory/RESULTS.md), [F MEASUREMENTS](../B-007F-post-sampler-memory/MEASUREMENTS.json).
- Private E `reports/model_phases.jsonl`, `resource_metrics.jsonl`, `outputs/official/run.json`; F 같은 파일을 `cases/official`에서 읽음. 공개 JSON에는 개인 경로나 PID를 넣지 않았다.
- 코드 위치는 공식 commit `78fe19576bb06be96c2375e088574a262a300edb`에 E의 제한적 loader/phase 패치를 적용한 실제 복사본의 줄 번호다. 원본 GitHub 줄 번호와 혼동하지 않는다. F 변경은 [SOURCE_PATCH.diff](../B-007F-post-sampler-memory/SOURCE_PATCH.diff)와 대조했다.
- 결과는 CPU 감사이며 생성·품질·메모리 개선 수용이 아니다. A와 E/F 기록은 변경하지 않았다.
