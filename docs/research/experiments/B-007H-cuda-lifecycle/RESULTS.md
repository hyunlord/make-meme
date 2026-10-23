# B-007H 결과 — 공식 RGB driving MP4 확보

**PROBE_PASS / CPU_LOAD_PASS / CACHE_RESTORE_PASS / DIT_MOVE_PASS / FIRST_FORWARD_PASS / SAMPLER_LATENT_PASS / VIDEO_OUTPUT_PASS.** 공식 인간 예제의 실제 MP4와 재사용 가능한 final latent를 확보했다. Lab은 NOT_RUN, 연속 재생 품질은 UNVERIFIED다.

## 실행 계약과 변경

시작 원격 HEAD는 `51daacac291f161a21edeac3a551375fdd24f08c`, 실제 실행 사전 고정은 `80f51ffacdb0b20a75e3ff8b1625784f7ded1d37`이다. [PLAN](PLAN.md), [실행 장부](RUN_LEDGER.json), [재현](REPRODUCE.md), [코드 차이](RUNTIME_DIFF.diff)를 함께 보라.

G의 조건 캐시 SHA `1f1e0b68495b2276a5b6d12eaf160897a16acb2bd2a089e616a55c40bf590308`와 sidecar를 읽기 전용으로 재사용했다. P 0회, probe 1/1, DiT CPU 적재 1/1, sampler 1/1, VAE decode 1/1, 재시도 0회다. 다운로드·SAT 재변환·학습·Lab·imagegen·외부 생성 API는 실행하지 않았다.

주된 변경은 큰 CPU 가중치를 읽기 전에 64-byte 비무작위 CUDA copy/add/synchronize/readback을 실제 완료한 것이다. 작은 allocation을 유지하고 적재·캐시 복원·DiT 이동 후 다시 검사했다. 기존 staged loader와 decoder를 그대로 재사용했으며 가중치·mixed BF16/FP32·FlashAttention·seed·noise·scheduler·CFG·입력은 바꾸지 않았다. 진단과 allocation 유지 자체도 실행 순서에 영향을 주므로 순수한 단일 원인 실험이라고 과장하지 않는다.

## 실제 완료 증거

| 단계 | guarded 시간 | 실제 증거 |
|---|---:|---|
| PROBE | 6.062초 | 16 FP32 값 3에 2를 더해 CPU에서 5 확인, 동기화, 캐시 16 leaf 원래 device/값/dtype/shape 복원 |
| S | 1,199.009초 | 첫 forward, 실제 80 model calls, 40 scheduler steps, final latent 원자 저장 및 정확한 재읽기 |
| D | 15.228초 | 유한 raw `[3,17,512,896]`, 실제 MP4 전체 decode 및 ffprobe 통과 |

CPU generator state와 sigma는 CPU, 저장된 timesteps는 CUDA 계약을 유지했다. tiny 연산 전후 CPU RNG는 불변이다. CUDA RNG의 비교 기준은 tiny 이후에 취득했으므로 tiny 이전 CUDA RNG의 동등성까지 실측했다고 주장하지 않는다.

출력은 **896×512, 17프레임, 16fps, 1.0625초**다. 40step UniPC·shift3·CFG5·seed20261022·history=None을 유지했다. final latent는 FP32 `[16,5,64,112]`, finite/readback exact이며 initial noise와 다르다.

- final latent 파일 SHA256: `d9014a440d1c5998d720310935b039a4bddde876f92567b28949ecd0773a9aec`
- final latent 값 SHA256: `f129057bb2cbaca33cc0e494eb472c6ccf03a753fcf37afc48e0649ddf075bd6`
- initial noise 값 SHA256: `9d26386e01a5dce6b0dc21e3df26aab79b65a4403e11b6c8fc5a71873dd3c950`
- MP4 SHA256: `9f5b04d9c4e0798330423ed90a12b3cb3ae2b7c9e7f84200474b9af6ec4dac8f`

S 종료·PID0·자원 회복 후 D만 실행했다. 모든 H service는 exit0/inactive/PID0이다. 기존 ComfyUI 서비스는 보존했다. 코드·upstream·캐시 287개 사후 검사가 일치했다. 대형 가중치 전체는 이번 H에서 다시 해시하지 않았으며 G의 기존 검증 계보를 재사용했다.

## 메모리 관측

[MEASUREMENTS.json](MEASUREMENTS.json)과 [시계열](resource_summary.csv)은 시스템·RSS·cgroup·CUDA를 별도 계정으로 기록한다. 서로 겹치는 수치를 더하지 않는다.

| 단계 | 최소 MemAvailable | 기록된 cgroup peak | 기록된 CUDA peak allocated |
|---|---:|---:|---:|
| PROBE | 95,122,866,176 B | 751,427,584 B | 17,364,992 B |
| S | 56,311,533,568 B | 66,577,215,488 B | 36,325,785,600 B |
| D | 81,109,180,416 B | 2,340,904,960 B | 9,565,265,920 B |

S 최소 가용 메모리는 약52.44GiB로 기존24GiB 가드를 유지했다. 모든 swap 관측0, cgroup max/oom/oom_kill0이다. S의 high 이벤트2426은 숨기지 않으며 OOM과 같지 않다. CUDA peak는 기록된 관측 지점의 값이고 관측되지 않은 종료 순간의 peak까지 보증하지 않는다. RSS file은 mmap/page cache와 관련되지만 그 자체가 누수 증거는 아니다. 읽을 수 있는 상위 cgroup 제한·anon/file·CUDA free는 상세 측정과 비공개 원본 trace에 보존했다.

## 실제 정적 시각 검토

비공개 원본/처리 입력/출력의 전체17프레임 시트와 확대 시트를 직접 확인했다. 참조의 해변·파란 의상·갈색 머리라는 큰 외형은 출력에 남고, driving의 파란 벽·빨간 의상·머리 장식은 검토한 출력에 뚜렷하게 복사되지 않았다. 머리 방향과 팔 위치가 프레임에 따라 변하며 정지 참조의 팔을 교차한 자세에 고정되지 않았다.

다만 손·팔 각도는 정확한 대응으로 수용하지 않았고, 얼굴 개체 정체성·세밀한 손가락 형태·프레임 간 자연스러움은 검증하지 않았다. 발이 잘린 구도에서 발 접촉을 추정하지 않았다. 실제 연속 재생을 직접 관찰하지 못했으므로 temporal quality는 **UNVERIFIED**다. 파일 재생 가능과 시각 품질 수용은 다르다. Lab 개체·체형·동물 안무·IG·윙크·발차기·Kling 비교는 **NOT_RUN**이다.

## 해석과 남은 한계

H의 이 실행 순서에서는 G가 실패한 조건 CUDA 복원을 지나 전체 sampler와 decode까지 완료했다. G에도 이미 cuda_initialized=True 기록이 있으므로 “G는 CUDA가 전혀 초기화되지 않았다”고 말할 수 없다. driver bug, file cache leak, cgroup OOM 중 하나를 확정할 증거는 없고 G의 정확한 원인은 **UNKNOWN**으로 유지한다. warm cache와 진단 부작용을 포함해 한 번의 성공은 유일 원인의 분리를 증명하지 않는다.

CPU 계약 fixture3개와 critical Ruff 검사는 통과했다. 전체 basedpyright는 **NOT_CLEAN(520 errors)**이며 동적 upstream 타입·누락된 import stubs 등을 포함한다. 이를 타입 검사 PASS로 보고하지 않는다. 실제 실행 성공과 정적 검사 한계를 별도로 보존한다.

한국어 수식·코드 설명과 질문/해설은 [학습 문서](../../lessons/B-007H-cuda-lifecycle.md)에 있다. 비공개 ZIP에는 조건 계보·final latent 및 재사용 sidecar·raw·MP4·비교 영상·측정·재현 자료를 포함하고 가중치는 제외한다. 공개 GitHub에는 미디어·조건 텐서·latent·개인 경로를 올리지 않는다.

## 다음 작업 하나

같은 검증된 단계 분리 경로에서 **기존 Lab 참조·RGB driving·대응 마스크의 17프레임 baseline 한 번**을 별도 승인 실험으로 제안한다. 공식 인간 예제 성공이 동물 일반화를 뜻하지 않으므로 얼굴·묵직한 체형·뒷발 직립·원본 외형 누수·마스크 경계를 따로 평가해야 한다. 이번에는 실행하지 않는다.
