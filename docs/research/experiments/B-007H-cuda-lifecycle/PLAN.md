# B-007H — CUDA 실제 연산의 초기화 순서 진단과 조건 캐시 기반 S→D 재개

작성: 2026-10-23 · parent: B-007G · 상태: **PLANNED / NOT_RUN**
이 문서의 GitHub 등록은 실행이나 예산 사용이 아니다. 사용자가 실행 담당자에게 전달해 지시할 때 아래 제한 범위를 적용한다. 이번 기록은 G 결과 검토와 다음 방향의 사전 기록을 포함한다.

## 0. 목표·검토 근거·지금까지의 결론

장기 목표는 DGX Spark급 로컬 장비에서 이미지·영상 생성 메커니즘을 이해하고, 개체·체형·동작·시간적 일관성이 높은 생성 방법을 연구하는 것이다. 현재 인프라 문제를 새 생성 기법이나 논문 기여로 포장하지 않는다. A(imagegen 전용)와 B(로컬 모델)는 독립이며 A를 변경하지 않는다.

G 기준 commit: `7f1c639777df4fece3047fdba5aa04d229b28cce`. 검토자는 원격 RESULTS, MEASUREMENTS, phase_sample.py, artifacts.py, run_phase.py, runtime_guard.py, runtime_launch.py를 읽었다. 실제 Spark/GPU 재실행은 하지 않았다. 제출 ZIP을 정확한 업로드 경로에서 container/Python으로 읽으려 했으나 ClientError로 실패해 CRC/99파일/SHA를 독립 검증하지 못했다. ZIP 검증값은 실행 담당자 보고와 구분한다.

- P: 조건 준비·저장 성공 143.331초. 캐시 17,365,660 bytes / SHA256 `1f1e0b68495b2276a5b6d12eaf160897a16acb2bd2a089e616a55c40bf590308`, 16 tensor와 metadata. 실제 초기 noise는 E와 동일하다.
- S: CPU DiT 적재 완료 후 `artifacts.load_tree`가 저장된 device 문자열대로 텐서를 복원하는 `.to(...)`에서 `cuDevicePrimaryCtxRetain returned CUDA_ERROR_OUT_OF_MEMORY`. DiT device 이동·sampler·첫 forward 전 실패. stage 시도 예산1/1은 보존하되 실제 sampler/forward 완료 횟수를 만들어내지 않는다.
- S 전체 관측 최소 MemAvailable 62,726,045,696 bytes(약58.4GiB), 마지막 CPU 적재 phase는 62,777,077,760 bytes. E/F의24GiB guard 종료와 다른 오류다.
- 같은 phase의 cgroup current66,564,358,144 bytes, anon33,082,748,928 / file33,285,410,816, MemoryMax64GiB 및 MemoryHigh62GiB. 마지막 high2660, max/oom/oom_kill0. high는 reclaim/throttle 신호이지 강제 OOM 횟수나 원인 증명이 아니다.
- `cuda_initialized=true`와 allocator0이 이미 기록돼 있다. 'CUDA가 전혀 초기화되지 않았다'고 단정하지 않는다. 이 상태만으로 primary context의 건강한 확보·실제 allocation·H2D copy·kernel 실행이 성공했음을 입증할 수도 없다.

이번 질문: **같은 S 실행 환경에서 CPU 가중치 적재 전에 실제 CUDA allocation/copy/연산을 완료해 두면, 이후 조건 복원·DiT 이동을 통과하는가?**
대안 가설은 cgroup/상위 cgroup 압박·file-backed residency·드라이버 메모리 제약·환경 차이다. 초기화 시점이 원인이라고 확정하지 않는다.

## 1. 범위와 종료 기준

- 전체 최대3시간. 새 모델/가중치 다운로드0, 학습/LoRA0, imagegen·외부 생성 API0.
- 기존 G의 P 캐시를 읽기 전용 재사용. **P 재실행0**, 원본 SAT 변환·전체 감사 재실행0, Lab0.
- 모델 없는 작은 CUDA/cache 복원 probe: 최대1개 fresh worker, 최대5분. 작은 자체 tensor payload는1MiB 이하, 실제 조건 캐시 복원은 허용. 무의미한 대형 CPU/GPU pressure allocation 금지.
- 앞 probe가 성공할 때만 기존 DiT CPU 로딩을 최대1회. 이 새 worker에서도 먼저 실제 작은 CUDA 연산을 하고, 기존 S 코드와 같은 로더로 진행한다.
- 조건 복원·모델 이동을 통과하면 같은 worker에서 공식17프레임 full sampler 최대1회(실패 포함). 최종 latent가 저장되고 S 종료·자원 회복이 확인되면 별도 D decode 최대1회. 단계마다 중간 승인 요청으로 멈추지 않지만 실패 뒤 대체 설정/재시도는 없다.
- 기존 E/F/G 장부 보존. H의 probe/model-load/S/sampler/D를 분리 기록하고 과거 '1회 소진'을 소급 변경하지 않는다.
- 기존24GiB global headroom, 시작 최소72GiB/swap0, cgroup cap 산식과 MemoryHigh 차이2GiB, 타 작업 보호를 유지. 새 deadline/unit만 정한다. 상위 cgroup 제한도 읽되 변경하지 않는다.
- sudo, 재부팅, driver/CUDA/PyTorch 전역 변경, GPU/context reset, 타 프로세스 종료, drop_caches, 강제 reclaim, swap 변경, 자동 quantization/해상도 축소/tiling 금지.

## 2. Probe — 같은 서비스 환경, 모델 없이 실제 CUDA 검증

새 exec 프로세스와 같은 Python·import 순서·환경·device 가시성·systemd/cgroup 정책을 사용한다. 셸에서만 성공한 결과를 실제 worker 성공으로 대체하지 않는다. CUDA를 초기화한 부모를 fork해서 넘기지 않는다.

1. 캐시는 CPU에서 해시·16개 tensor·dtype/shape·provenance를 확인한다. `load_tree(..., device='cpu')`는 검증용이며 generator state 등 최종 device 계약을 바꾸지 않는다.
2. import 전후 `is_initialized`, 현재 프로세스의 driver/device 상태, 허용된 cgroup ancestor의 memory.high/max/events/pressure, MemAvailable/Swap/RSS/file-backed 상태를 기록한다. 진단 API 자체가 CUDA를 초기화하는지 구분한다. 이미 설치된 바인딩/검증된 ctypes wrapper로 `cuDevicePrimaryCtxGetState`를 읽을 수 있으면 관측하되 reset/release를 외부 라이브러리 대신 호출하지 않는다.
3. 단순 `torch.cuda.init()`/`is_available()` 확인만으로 통과시키지 않는다. RNG를 소비하지 않는 tiny CPU→CUDA copy, `fill_` 또는 `add_`, device synchronize, CPU 값 readback을 실제 수행한다. 예상 결과가 일치해야 한다. device allocation과 kernel의 각 단계 전후를 기록한다.
4. 이제 캐시 leaf별 저장된 원래 device로 복원하고 synchronize/finite·CPU roundtrip hash를 확인한다. 모든 tensor를 일괄 CUDA로 옮기지 않는다. CPU generator_state/CPU scheduler 관련 tensor는 기존 계약을 따른다. leaf 이름, byte 수, target device, 시작/완료를 기록한다.
5. probe 종료·PID0·자원 회복 확인. 여기서 실패하면 모델을 올리지 않고 정확한 실패 API/환경 근거만 보고한다. OOM 발생 후 같은 프로세스에서 무한 재시도하지 않는다.

## 3. 실제 S — 유일한 주개입은 대형 CPU 로딩 전 실제 CUDA 연산

Probe와 별도의 fresh worker에서 위 tiny 실제 연산을 먼저 수행한 후, 기존 G의 CPU DiT staged loader를 그대로 호출한다. 초반의 작은 CUDA tensor 하나만 보존해 context 수명 단서를 유지할 수 있으나 크기를 기록한다. driver context 예약을 수동 대량 확장하지 않는다.

주개입은 **실제 첫 CUDA 작업의 순서**다. precision·loader·checkpoint·mask·scheduler·초기 noise·reference·해상도·step을 동시에 바꾸지 않는다. 별도의 cache API 계측은 값·dtype·original device를 그대로 보존해야 한다.

로딩 후 CPU 캐시 검증→원래 device로 leaf별 복원→DiT `.to(cuda)`의 전후에 phase를 추가한다. 같은 tiny 연산을 다시 검사해 CUDA 상태를 구분한다. 이를 핑계로 모델을 두 번 GPU로 옮기지 않는다. model CPU tensor의 mmap 공유·FP32 passthrough를 조용히 clone하거나 full checkpoint를 다시 만들지 않는다.

`torch.cuda.mem_get_info`는 명시적인 CUDA 성공 뒤에 기록한다. UMA에서 MemAvailable·CUDA free·RSS·cgroup anon/file·allocator allocated/reserved는 서로 다른 관측이며 더해서 총 소비량으로 쓰지 않는다. fresh process의 cold/warm cache 차이를 숨기거나 warmup 성공을 근본 원인 확정으로 부르지 않는다.

조건 복원 또는 모델 이동이 실패하면 그 지점에서 STOP. no-model probe PASS인데 CPU 적재 후 FAIL이면 '모델 적재 이후의 메모리/컨텍스트 상호작용'이라는 범위까지만 말한다. pressure 원인을 구별할 실제 데이터가 부족하면 UNKNOWN이다. 무조건 cache 누수나 하드웨어 불량이라고 결론 내리지 않는다.

## 4. 성공한 경우에만 같은 공식 S→D baseline

G의 P 캐시·현재 mixed BF16/FP32 가중치·UniPC40step/shift3/CFG5·공식17프레임512×896·16fps를 고정한다. 첫 noise 해시는 `9d26386e01a5dce6b0dc21e3df26aab79b65a4403e11b6c8fc5a71873dd3c950`. 전역 RNG를 warmup에서 소비하지 않는다.

모델 실제 첫 forward finite와 step/call counter를 기록하고, 마지막 scheduler 이후 VAE에 넘길 final latent를 atomic 저장한다. shape/dtype/value hash, history=None/reference prefix 없음, 정확한 VAE scale 규약을 기록한다. 캐시나 초기 noise를 final latent로 대신하지 않는다.

S 종료와 메모리 회복을 확인한 뒤 VAE-only D를1회 수행한다. G D는 실물 미검증이므로 이를 숨기지 않는다. raw/MP4가 없으면 예제를 생성했다고 표시하지 않는다. 최종 latent가 있으면 D 실패에도 보존하고 sampler를 반복하지 않는다. G의 이전 P 완료 receipt를 '이번 P 성공'으로 조작하지 말고 명시적 parent artifact로 연결한다.

성공해도 공식 예제 성공이며 Lab identity/안무 성공이 아니다. 실제 연속 재생이 없으면 temporal quality UNVERIFIED.

## 5. 학습과 연구 해석

한국어 lesson은 이번에 필요한 한두 주제만: CUDA runtime initialized vs primary context vs 실제 allocation/kernel, UMA/cgroup/file cache 회계. 간단한 모형은 M(t)=W_live(t)+A_live(t)+C_cache(t)+D_driver(t)+O(t)로 설명하되 이는 분해 목표이지 서로 겹치는 RSS/cgroup/CUDA 수치를 더하는 공식이 아니다.

실제 cache-first P/S/D 관계를 c=E(inputs), z=Sample(v,c,noise), video=D(z)로 연결한다. 실행 순서 변경이 계산값을 보존하려면 eval/precision/RNG/device 계약을 유지해야 함을 설명한다. 기존 sample과 byte-identical 결과를 재실행 없이 보장하지 않는다.

현재 작업은 생성 연구를 위한 실행 기반이며, 이 초기화 workaround 하나를 새로운 생성 아키텍처/상용급 품질/1티어 논문 기여로 주장하지 않는다. 성공 시 후속 우선순위는 실제 출력의 motion/identity 평가와 학습 가설이며, 감사 도구를 계속 만드는 일이 아니다.

## 6. GitHub와 종료 산출물

RECORDING_PROTOCOL/CHARTER/ROADMAP/HISTORY/활성 PLAN을 읽고 실행 전 code/config와 이번 변경 diff를 commit/push. branch가 이동했으면 최신 내용을 보존·정상 통합하고 reset/force push 금지. 시작·종료에 HISTORY/ROADMAP을 갱신하되 과거 상태는 삭제하지 않는다. 연구 프로그램 별도 문서 브랜치를 임의로 통째 merge하지 않는다.

RESULTS에 probe/weight load/context restore/device move/first forward/sampler/latent/decode/video를 구분하고 실제 단계별 반환코드·guard reason을 기록한다. 만료된 과거 deadline을 재사용하지 않는다. 큰 새 프레임워크/모델 전환/정적 검사 전체 청소를 이번 작업에 묶지 않는다.

공개에는 비민감 code/config·MD·요약·해시만 올린다. 개인 입력/조건 캐시/latent/raw 영상·가중치·비밀경로는 비공개 ZIP에 보존하고, 대형 가중치는 ZIP에서 제외한다. Mac/Spark 실제 경로·전송 여부·CRC/manifest/SHA를 구분하며 자신이 관측하지 않은 host 일치를 주장하지 않는다. 종료 후 자기 프로세스 확인, 다음 실험 하나만 제안.

## 공식 근거

- NVIDIA primary context API: https://docs.nvidia.com/cuda/cuda-driver-api/group__CUDA__PRIMARY__CTX.html
- PyTorch runtime 초기화 상태: https://docs.pytorch.org/docs/stable/generated/torch.cuda.is_initialized.html
- Linux memory.high/max/events: https://docs.kernel.org/admin-guide/cgroup-v2.html
- Spark UMA 메모리 보고 차이: https://docs.nvidia.com/dgx/dgx-spark-porting-guide/optimization.html

위 문서는 의미를 설명하는 근거이며 G 오류의 원인을 증명하는 것은 아니다. 설치 버전 코드와 실제 런타임을 기준으로 검증한다.
