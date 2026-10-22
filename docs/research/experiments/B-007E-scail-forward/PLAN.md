# B-007E — SCAIL-2 실제 모델 로딩 및 첫 RGB driving 영상 baseline

작성: 2026-10-22 · 상태: **PLANNED / NOT_RUN** · parent B-007D

## 0. 목표와 기준 증거

B-007D에서 공식 SAT 원본65,582,563,395 bytes를 1,307개 tensor/65,582,313,560-byte Wan safetensors로 변환, 1,307개 전체 key/dtype/shape/value/hash와 원본 SHA를 검증했다. 출력 고정 SHA256: `8b844f026510f0b94d3209d66444b403a089ec179dc149d85513c13b2fa37118`. 메모리 cgroup cap32GiB 도달/RSS 약53GiB/OOM0은 **변환 당시** 관측이다. 전체 SCAIL 모델 인스턴스 적재·DiT forward·영상 생성은 여전히 NOT_RUN.

이번은 **실제 Spark에서 공식 SCAIL-2 모델을 가중치와 함께 적재하고, 안전한 경우 원본 RGB driving으로 짧은 기준 영상 1개 이상 생성**하는 최초 전체 추론 실험이다. 우선 실질적인 MP4와 raw frame/비교·메모리 측정의 확보. 구현이 어렵다면 코드/프로세스 환경만 많이 만들고 완료 선언하지 않는다.

## 1. 경계·상한

- B 트랙만. A(native imagegen only)·기존 VACE/ComfyUI/타 작업/가중치와 연구 기록은 보존. native imagegen·외부 생성 API·유료 GPU 금지.
- **새 전체 checkpoint 다운로드 0GB**, 추가 대형 모델 설치/LoRA 0, optimizer update **0**.
- 기존 SCAIL-2 Wan source commit `78fe19576bb06be96c2375e088574a262a300edb`, 공식 model metadata/revision 및 B-007A에서 GB10 실측한 FlashAttention2.8.4 binary/hash를 고정. 격리 환경·다른 작업 영향을 확인.
- 모델 적재는 사전 자원 가드하에 최대 **2가지 명시한 로딩 경로**만 시험(실패 기록 포함). 비호환/메모리 위험 시 바로 중단. GPU full diffusion sampler 시도 **최대 2회(실패 포함)**: 공식 예제 17frame 1회, 실제 Lab/reference+원본17f 1회. 원본 2개체나 전체15초·다른 seed 탐색 금지.
- 총 연구 작업 **최대 5시간**. 무거운 GPU 작업은 1개만. sudo/driver/reboot/swap/clock/global pip 변경, 타 작업 종료, 임의 대량 offload 통한 시스템 swap 압박 금지. 자기 프로세스만 종료·cleanup, 시작/후 리소스 비교.
- 모델 로드 실패는 GPU diffusion inference 호출 0회로 분리 기록. 공식 예제 경로/권한 없으면 미리 정한 Lab 단일 구간 1회만 진행 가능하되 공식 품질 기준선으로 잘못 표기 금지.

## 2. Gate 0 — 원본/계약/환경 사전 확인

- GitHub CHARTER/ROADMAP/HISTORY/RECORDING_PROTOCOL와 B-006, B-007A/B/C/D RESULTS·CODE_AUDIT/실행 스냅샷을 읽고 실제 HEAD·repo/worktree/dirty 상태 확인.
- Spark에서 변환본의 정확한 파일 경로·길이·SHA256, T5/CLIP/VAE/토크나이저 파일·B-007A의 FA binary를 fresh 검사. 경로·파일을 추측하거나 대형 체크포인트를 다시 다운로드하지 않는다.
- 공식 `SCAIL2Pipeline` 로더의 `SCAIL2Model.from_config` → `safetensors.load_file` → `load_state_dict` → `.to(device)`/dtype 전환을 실제 pinned 코드에서 추적. F32 65.58GB **두 사본의 중복 상주 가능성**과 T5/CLIP/VAE/활성값이 128GB 통합 메모리에 미치는 효과를 산정.
- 원본 source f0~16 17frame/24fps, reference Lab 사진, 동일 인물 red ID인 RGB/driving 색상 마스크를 읽기 전용으로 확인. B-007A의 얇은 발/바닥/꼬리 경계 마스크 문제 **PARTIAL_UNRESOLVED** 보존. 새 segmentation 모델·무한 수동 보정 금지.
- 512p 인풋의 실제 crop: Lab 관련 H896/W512, 공식 가로 예제 H512/W896. RGB/mask 동일 변환, visible landmark가 잘리지 않는지 확인. B-006 119점 annotation은 RGB 퀄리티 정답 pose가 아니므로 평가 참고만.
- 시간축: source sample `t_i=i/24`, 17장 출력 24fps 파일 길이17/24초. 공식 sample_fps16와 model motion prior의 차이 별도. 공식 예제 native16fps와 실제 Lab 24fps writer를 구분. fps만 바꿔 생성 모델의 시간적 일반화를 입증했다고 주장하지 않는다.

## 3. Gate 1 — 모델 로딩 메모리 안전성 및 실제 로드

- 실행 직전 시스템 `MemAvailable`, GPU/GB10 사용, page-cache/file_mapped, disk, 기존 작업·swap을 fresh 측정한다. 기존 CPU 변환의 cgroup32GiB/RSS53GiB를 모델 load 필요량으로 가정하지 않는다.
- **성공한 B-007D output은 FP32 약65.58GB**다. 공식 `safetensors.load_file`은 텐서를 실제 materialize할 수 있고 `load_state_dict`는 초기화된 모델 사본을 추가로 유지할 수 있다. 체크포인트 크기만으로 로딩 안전하다고 판단 금지.
- 실행 전 소형 model/fixture로 `safe_open` per-tensor access / meta-init + assign / dtype cast / CPU staged load와 원본 코드의 state_dict key/dtype/shape/값·model strict loading semantics를 검증한다. **실제 공식 architecture와 호환된다고 확인한 경로만** 실제 모델에 적용. 소형 fixture PASS는 full load 성공 증거 아님.
- 필요한 경우 격리된 실험 복사본에서 제한적 FP32→BF16 로딩 또는 스트리밍 텐서 변환을 검토하되 원본 safetensors와 변환 SHA 보존, 정확한 변경점/손실 가능성 별도 configuration으로 선언. B-007D의 수치 동일성 검증을 BF16 모델 출력 동일성으로 바꾸지 않는다. quantization/distilled LoRA/새 모델은 이번에 추가 안 함.
- OS cgroup 메모리 한도와 watchdog/프로세스 종료를 별도 서비스에 영향 없이 실제 설정·검증. 시스템 headroom(예: 기존 작업 포함 최소24GiB)과 swap0을 지키기 어렵다면 stage STOP. cap은 실제 fresh available 기준으로 결정하며 초기 불확실성 때문에 CPU+GPU 통합 메모리를 이중 계산하지 않는다.
- 실제 모델은 반드시 **CPU/GPU memory·시간을 단계별** 측정: T5/CLIP/VAE, DiT architecture initialization, weight mapping/load, device/dtype cast, post-load peak, 첫 forward. `nvidia-smi` GPU mem N/A 환경에서는 그것을 GPU 여유값으로 추정하지 말고 `torch.cuda` allocator + OS/cgroup/RSS를 함께 기록.
- 모델 로드/DiT 첫 forward에서 OOM, CPU/GPU 메모리 압박, 원본/타 서비스 간섭이 생기면 본 실험 자기 프로세스만 중단. **OOM을 줄이려 무제한 재시도/step 변화/미검증 weight 분할을 반복하지 않는다.** 모델 적재 단계만 통과하고 forward가 실패할 수 있음.

## 4. Gate 2 — 최대 2회 공식/실제 영상 생성

- **공식 예제** 1건 (17 frames, 512p, 공식 RGB/ref/mask와 해당 프롬프트를 정확히 확인), 사용 가능하다면 먼저. native official 16fps는 시간을 명시.
- **실제 Lab 1건**: 실제 Lab photo + B-007A 대응 red mask, RGB source f0~16, 512p 및 사전 결정된 24fps 출력, 기준 seed20261022, `sample_steps=40`, UniPC, `shift=3`, CFG5, optional LoRA OFF, prompt enhancer OFF. source/ref 배역과 identity·geometry 맞춤.
- 모델 로딩·첫 forward/entire generation 간 RAM·allocator·cgroup peak, 실제 동작 시간, output frames/dtype/shape/crop/camera 영역을 기록. 17 프레임 원본 시간축과 마스크 정합 유지. 원본 안무를 위한 프레임 복제·보간·비학습 warp·crossfade는 raw baseline에 사용하지 않는다.
- raw MP4와 모든 프레임·source/ref/mask 비교 sheet. 실제 17/24 파일 길이0.70833초와 endpoint 16/24 간격을 구분. 짧은 클립 loop의 되감기 점프와 내부 불연속 구분.
- 평가: 실제 Lab 개체얼굴/귀/털/체형, source 정체성 누수, 뒷발직립과 머리·앞발 동작 타이밍, 바닥 접촉·마스크/반사·cropping, 프레임 간 identity/temporal consistency. **연속 재생을 사람/실행자가 실제로 관찰하지 못했다면 temporal=UNVERIFIED**. 실사 품질/제품/논문/Kling 성공 자동 승인 없음.
- 공식 예제가 BLOCKED라면 Lab를 억지로 공식 확인 성공이라 하지 않는다. 두 번의 새 diffusion 호출 상한을 넘지 않는다.

## 5. 연구 산출물·수학

`docs/research/lessons/B-007E-full-model-forward.md` 한국어:
- Tensor checkpoint sizes와 FP32/BF16 casting/parameter vs activation/모델 load transient, unified memory/cgroup RSS vs file cache.
- torch.nn.Module meta-init/state_dict/assign 의미, safetensors safe_open/load_file 메모리 경로 및 key·dtype parity.
- SCAIL14B token lengths(reference+generated+RGB driving), attention O(N^2)/FlashAttention 실제 sample forward, FA kernel tiny-smoke와 full sample의 차이.
- Flow Matching noise time vs physical fps, denoising scheduler/CFG의 model call count 및 real sample24fps prior mismatch.
- 모델 load PASS, first forward PASS, end-to-end MP4 PASS, Lab identity/motion PASS를 각각 따로 정의; 근거 없는 성공 수치 금지.
- 수식 → 실제 tensor / trace 위치 → 관측치/추정치 분리 → 질문·답안 3개.

## 6. 기록/정지

시작 전 실제 resolved code/config/weights hashes와 자원 예산을 연구 branch에 커밋. 종료 뒤 `docs/research/experiments/B-007E-scail-forward/RESULTS.md`, run ledger/재현/실측, `lessons/B-007E-full-model-forward.md`, HISTORY, ROADMAP을 기록하고 원격 HEAD 확인.

개인 reference/원본/마스크/raw 생성 영상·weights/로그의 비밀 경로/토큰/원본 모델은 공개 GitHub에 올리지 않는다. private review ZIP에 작은 대표영상(있으면), 모든 시도·실패 요약, scripts/config, 체크포인트 경로·SHA만 남기고 대형 weights 제외. ZIP CRC/file manifest/hash 검증 후 Mac/Spark 위치 구별.

새 모델·학습·추가 생성 반복으로 자동 확대 금지. 종료 후 다음 한 실험 제안만. 결과 상태는 LOADING_BLOCKED / LOAD_PASS_FORWARD_NOT_RUN / FIRST_FORWARD_PASS / VIDEO_OUTPUT_PASS / QUALITY_NOT_ACCEPTED 등 정확히 기록.
