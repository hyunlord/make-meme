# B-007G — E/F 메모리 수명 비교와 단계 분리형 공식 baseline

작성: 2026-10-23 · parent: B-007E/F · 상태: **PLANNED / NOT_RUN**

이 문서는 다음 작업의 제안과 사전 기록이다. GitHub 등록만으로 GPU 실행을 승인하거나 실행하지 않는다. 사용자가 이 계획을 실행 담당자에게 전달해 수행을 지시할 때 아래 한정 범위를 적용한다. 이전 E/F 예산의 잔여 슬롯을 자동 재사용하지 않는다.

## 0. 검토 결과와 이번 방향 결정

검토 기준은 F `ecb618558825c53a259a4e684a12a4f6bf162eb9`, E `aae93748cb1eebc89d68670673c301d739ebe149`, 공식 SCAIL `78fe19576bb06be96c2375e088574a262a300edb`다. 이번 문서 작성자는 GitHub의 F RESULTS/MEASUREMENTS/SOURCE_PATCH/runtime_infer 및 resource_summary, E MEASUREMENTS/staged_loader, 공식 wan/scail.py의 encode/sample/decode 경로를 직접 읽었다. Spark 재실행과 F 비공개 ZIP 무결성 검증은 하지 않았다.

- E: 전체 적재와 첫 forward PASS, sampler40/40 로그 뒤 offload/decode 경계에서 global memory guard 종료. final latent/MP4 없음.
- F: 같은 가중치·입력·초기 noise, 모델 적재331.44초, 첫 forward 관측 전 MemAvailable23.91272GiB가24GiB 미만으로 내려가 종료. post-sampler 개입은 **NOT_REACHED**. 가설이 틀렸다는 증거도, 모델의 품질 실패도 아니다.
- F resource_summary의 마지막 구간에서는 cgroup charge가 약66GB에서41GB로 감소하는 동안 시스템 MemAvailable은 하한까지 감소한다. 이를 메모리 누수·CUDA 증가의 직접 증명으로 해석하지 않는다. 서로 다른 회계/페이지 charge/실측 시점과 GPU 할당을 같이 봐야 한다.
- CPU staged loader는 전체 mixed DiT를 CPU에 적재한다. 공식 pipeline은 조건을 계산한 뒤에도 T5/CLIP/VAE 객체를 보유하고, sample_func 앞에서 DiT를 device로 옮긴다. 이 구조는 불필요한 동시 상주와 전환 peak의 **후보**이며, E/F 차이의 정확한 원인은 아직 미확정이다.

결정: 같은 monolithic sampler를 저장 없이 다시 시도하지 않는다. 기존 로그의 CPU-only 비교를 짧게 끝내고, **조건 인코딩 → DiT 샘플링 → VAE decode를 순차 프로세스로 분리**하는 실행 방법의 적합성을 검증한다. 원인 증명이 부족해도 알려진 객체 동시 상주를 줄이는 engineering 가설로 시험할 수 있지만, causal proof나 새 논문 기법이라고 부르지 않는다.

## 1. 목표·예산·중단 조건

목표는 원형과 같은 수학적 추론 계약을 유지하면서 공식17프레임 MP4를 얻는 것, 또는 실패하더라도 재사용 가능한 conditions/final latent와 정확한 실패 경계를 확보하는 것이다.

- CPU-only 기존 로그·코드 비교: 최대45분. 증거가 없으면 UNKNOWN으로 종료하고 존재하지 않는 operation trace를 복원하지 않는다.
- 전체 구현·검증·실행: 최대4시간. 새로운 heavyweight framework/MCP/state machine을 만들지 않는다.
- 새로운 대형 모델 다운로드0, 학습/LoRA0, native imagegen/외부 생성 API0. 기존 checkpoints·FlashAttention·mixed dtype·sample 설정 재사용.
- 조건부 **새 full sampler 최대1회**, E와 같은 공식 예제에만 사용. 실패도1회다. Lab/새 seed/해상도 변경/tiling/quantization/재시도는 이번 범위가 아니다.
- 조건 인코딩 실물1회, sampler 실물1회, 해당 final latent의 기본 VAE decode1회. 각 단계 실패 시 후속 중지. 큰 모델을 반복 로드하는 진단은 금지한다. 작은 CPU fixture는 별도다.
- 기존24GiB global headroom·swap0·타 서비스 보호 정책 유지. 하한 완화·위반 샘플 무시·drop_caches·swap/driver/clock 변경·다른 프로세스 종료 금지. CPU/GPU·RSS/cgroup accounting을 더해 총 메모리라고 하지 않는다.
- 기존 E1회/F1회 실패 이력과 이번 신규 sampler ID/parent 연결을 보존. 현재 없는 final latent로 decode를 재개한다고 보고하지 않는다.

## 2. 먼저 수행할 짧은 E/F CPU 감사

원본 private trace가 존재하면 새 GPU 실행 없이 동일 phase 기준으로 정렬한다. 누락 phase는 UNOBSERVED다.

필수 대조: 시작 상태, pipeline 적재 완료, text encode, reference VAE encode, CLIP encode, driving VAE encode, initial noise, DiT CPU→device 이동 전후, 최초 forward. 기존 로그에 없는 경계는 앞으로 필요한 hook으로 표시한다.

각 phase에서 시스템 MemAvailable/swap, process RssAnon/RssFile, cgroup anon/file/high/max/oom, CUDA allocated/reserved/peak 및 타 작업 snapshot을 서로 구분한다. 같은 가중치/seed라도 page cache와 allocator/다른 작업의 상태는 같다고 가정하지 않는다. F 변화는 post-loop 정책 실행 전에 발생했으므로 그 정책을 원인으로 명명하지 않는다.

loader의 cast_state, safe_open view, state_dict, hooks/closure, pipeline component의 참조 수명을 코드로 추적한다. 텐서의 Python 참조 두 개를 payload 두 사본으로 잘못 세지 않는다. 같은 물리 RAM을 사용한다는 것과 CPU/CUDA tensor가 동일 storage를 zero-copy 공유한다는 것은 다르다.

산출물은 짧은 E_F_COMPARISON.md와 객체 수명 표, source 위치다. 이 단계만으로 새 원인이 증명되지 않으면 한계 그대로 기록하고 다음 구조 검증으로 이동한다.

## 3. 한 가지 구조 변경 — 순차 프로세스 경계

### Phase P: conditions 준비, DiT 없음

T5/CLIP/VAE 및 공식 전처리·mask helper만 사용한다. SCAIL2Pipeline 전체 생성자로 DiT까지 만들어 놓고 'preprocess only'라고 부르지 않는다.

공식 단일 segment/no-history/animation 계약을 추출한다. positive/negative text context, CLIP features, reference latent/mask, driving latent/mask, replace_flag, sequence settings, 필요시 additional_ref/history의 None 여부까지 보존한다. RGB/mask resize·crop·normalization, VAE encode scaling, dtype/autocast를 고정한다. 허용된 빈 negative prompt를 임의 강화하지 않는다.

조건 tensor를 lossless safetensors+JSON으로 원자적 저장하고 값/hash/shape/dtype/구조를 다시 읽어 확인한다. 다른 dtype로 캐스팅하거나 불필요한 quantization을 하지 않는다. private 조건을 공개 GitHub에 올리지 않는다.

준비 프로세스 종료·PID/context 소멸 및 메모리 회복을 확인한 뒤 다음으로 간다. 완료 여부는 process returncode만 아니라 artifact readback과 phase log로 확인한다.

### Phase S: DiT만 로딩해 sampler 실행

DiT·scheduler·필요한 작은 조건 tensor만 적재한다. T5/CLIP/VAE는 인스턴스화하지 않는다. 동일 checkpoint·mixed BF16/FP32 island 정책·RoPE·attention backend를 유지한다.

우선 기존 검증된 staged loader를 재사용한다. CUDA 이동 전후 phase hook을 명시한다. 새 direct-device 로더, allocator 정책, group offload 등 다른 최적화를 동시에 추가하지 않는다. 이 구성도 메모리가 부족하면 가드 아래 종료하고 또 다른 로딩 방법을 자동 시도하지 않는다.

기존 공식 run의 source/ref/mask/config 및 initial_noise SHA를 유지한다. seed만 같다고 같은 RNG 소비 순서를 보장하지 않는다. initial noise를 저장본에서 불러올 경우 noise 생성 이후의 generator state까지 재현하거나, 동일 generator/noise 생성 코드를 유지하여 실제 noise를 대조한다. 이후 scheduler가 generator를 쓰는지 확인하고 CPU/CUDA RNG state의 의미를 기록한다.

실제 arg_c/arg_null의 list/container 구조, history 적용 순서, CPU step 계산 위치, dtype와 UniPC sigma/timesteps를 보존한다. 전역 offload_model=False로 바꾸며 solver 연산까지 바꾸지 않는다. sample_steps40, CFG5, shift3, seed20261022, adapter=null 등 기존 resolved config 유지.

마지막 scheduler update 후 실제 VAE 입력인 final latent를 finite/shape 검증하고 원자적으로 저장한다. 초기 noise나 reference prefix를 저장해 final로 표시하지 않는다. 완료 step 수와 forward 수를 durable하게 남기며 phase별 snapshot을 flush한다. 단일 clip에서는 필요 없는 history를 새로 생성하지 않는다.

최종 latent 저장·readback 완료 후 DiT를 CPU로 옮기지 않고 sampler 프로세스를 종료한다. 작은 부모 supervisor는 CUDA tensor를 보유하거나 CUDA 초기화 뒤 fork하지 않는다. 각 worker는 별도 exec/spawn이며 GPU tensor를 IPC로 공유하지 않는다.

### Phase D: VAE만 로딩해 decode/MP4

sampler 종료·메모리 회복 이후 VAE만 적재한다. 저장된 final latent를 같은 dtype/scale와 공식 decode wrapper로 처리한다. latent scaling을 두 번 적용하거나 reference/history 채널을 임의 포함/제거하지 않는다.

VAE decode의 autocast·시간 cache·전체17프레임 출력·clamp 규약을 원형대로 유지한다. tiling/chunk 방식 변경·보간·crop 변경·해상도 축소는 이번에 하지 않는다. 종료한 condition VAE의 feature cache가 다음 decode에 필요한지 공식 reset 경로에서 확인한다.

공식 예제는17프레임/16fps를 유지한다. Lab24fps는 이번 실행 대상이 아니다. raw 출력과 MP4 및 프레임 수/dtype/finite를 확인한다. 실패하면 final latent는 남기고 decode 재시도나 sampler 재생성을 하지 않는다.

## 4. 실행 전 동등성 검증

CPU 소형 fixtures로 phase별 argument 구조, tensor save/load byte equality, RNG 상태, scheduler timesteps, history=None, branch별 text/masks, dtype와 cache-reset, 종료 후 다음 phase 시작을 검증한다. 원형코드 함수의 추출·호출을 우선하고 영상 모델을 새로 구현하지 않는다.

이는 graph contract parity 검증이지 14B 전체 numerical/video 품질 동일성 증명은 아니다. GPU 비결정성에 대한 허용 오차와 byte parity의 적용 범위를 분리한다. 같게 유지할 수 없는 연산·dtype·입력 변화를 발견하면 GPU full sampler 전에 SETUP_BLOCKED로 기록하고 진행하지 않는다.

P 단계 인코딩과 E/F의 저장된 실제 tensor payload가 모두 있으면 비교하고, shape/hash만 남았다면 검증 가능한 항목까지만 대조한다. 과거 없던 값을 있다고 꾸미지 않는다. 긴 symbolic 문서 대신 코드 위치와 실제 입력 계약 표를 남긴다.

## 5. 측정·해석·학습

모든 phase에서 start/end/synchronized transfer start/end/first forward/final latent write/decode 시작·끝을 기록한다. hook에 큰 tensor reference를 계속 보존하지 않는다. OS/cgroup/RSS/CUDA alloc과 reserved를 별도 기록한다. 샘플링 실패의 단일 정확한 allocating operation은 관측이 없으면 UNKNOWN이다.

구조 가설은 단계별 불필요한 weight 동시 상주 제거다. 개략적으로 기존에는 여러 component weight와 temporary가 중첩되지만 분리하면 max(M_prepare,M_sample,M_decode)+공통 오버헤드 형태를 기대한다. 단, file cache·driver·타 작업·전환 temporary는 남으므로 계산상 상한이나 실측 절감량으로 부르지 않는다. 프로세스 분리는 실행 오버헤드를 늘릴 수 있다.

한국어 lesson B-007G-component-lifetime.md: encoder output을 캐시할 수 있는 이유와 gradient 학습 시 한계, 조건부 벡터장 v_theta(z_t,t,c), eval/no_grad와 cache reset, tensor reference vs storage vs allocator, attention 메모리와 파라미터 상주 메모리 차이, 같은 수학 그래프/다른 실행 계획, unified memory의 회계. 이번 엔지니어링 개선을 새 영상 생성 아키텍처/1티어 논문 기여로 과장하지 않는다. 실제 baseline 후 identity/motion/일반화 연구로 돌아간다.

## 6. 결과·GitHub·비공개 전달

시작 전 CHARTER/ROADMAP/HISTORY/RECORDING_PROTOCOL, B-007E/F 문서 및 실제 실행 checkout 상태를 확인한다. 이번 PLAN과 resolved code/config를 실행 전에 commit/push한다. 기존 main/A와 연구 결과 덮어쓰기, force push/reset/clean 금지.

종료 후 RESULTS.md, E_F_COMPARISON.md, 한 장 객체수명 표, 재현 코드·run ledger·자원 요약, lesson, HISTORY/ROADMAP 갱신 및 원격 HEAD 확인. 상태는 CONDITION_CACHE_PASS / SAMPLER_LATENT_PASS / VIDEO_OUTPUT_PASS / BLOCKED와 실제 수행을 구분하며 새로운 복잡한 승인 상태 머신은 만들지 않는다. 정적 검사 미통과는 실제 실행 결과와 별도로 기록한다.

private ZIP에는 실제 성공/실패 자료·final latent가 있으면 재사용 계약과 함께·영상이 있으면 원본 비교를 포함한다. 대형 weights·venv·개인 media/latent/경로/토큰을 공개 GitHub에 올리지 않는다. /tmp 산출물의 실제 Mac/Spark 위치·전송·CRC/manifest/SHA를 확인한다. 새 모델/seed/학습/추론 확대는 중단하고 다음 실험 하나만 제안한다.

이번 문서 등록은 PLAN 추가뿐이며 E/F 파일과 실행 예산은 변경하지 않았다. 실제 생성·프로세스 종료·ZIP 검증은 실행 담당자가 결과로 남겨야 한다.

## 근거

- [F RESULTS](../B-007F-post-sampler-memory/RESULTS.md), [F source patch](../B-007F-post-sampler-memory/SOURCE_PATCH.diff), [F resource trace](../B-007F-post-sampler-memory/resource_summary.csv)
- [E measurements](../B-007E-scail-forward/MEASUREMENTS.json), [E staged loader](../B-007E-scail-forward/code/staged_loader.py)
- [Pinned SCAIL encode/sample/decode](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/scail.py)
- [PyTorch CUDA memory semantics](https://docs.pytorch.org/docs/main/notes/cuda.html)
- [NVIDIA Spark UMA optimization](https://docs.nvidia.com/dgx/dgx-spark-porting-guide/optimization.html)
