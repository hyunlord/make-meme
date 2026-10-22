# B-007 — SCAIL-2 / DGX Spark 실행 가능성 사전 검증 (Preflight)

작성: 2026-10-22 · 상태: **PLANNED / NOT_RUN** · parent B-006

## 목적

B-002~005의 VACE frozen baseline은 입력 변화에 반응했으나 8개 조건 모두 실제 Lab identity와 원본 춤의 동시 수용 실패. B-006은 원본 17프레임의 표면점119개/미관측170개를 보존하고, Canny/2D landmarks의 정보 손실과 공식 SCAIL-2 RGB driving의 직접 과제 적합성을 검토했다.

이번 B-007A는 **대형 체크포인트를 다운로드하기 전에** DGX Spark의 GB10 SM121에서 공식 SCAIL-2의 attention 연산을 실제로 실행할 수 있는지, 모델 저장·변환 비용과 입력/mask/24fps 계약이 안전한지 확인하는 단계다. 실행 가능성이 검증되었다는 의미로 품질을 미리 수용하지 않는다.

## 허가된 작업과 상한

- A 트랙과 이전 B 자산은 보존. 새 native imagegen·외부 생성 API·대형 영상 모델 학습·추론 금지.
- 새 SCAIL-2 체크포인트 다운로드 0GB, 새 diffusion 영상 inference 0회, optimizer update 0회.
- 이전에 고정한 공식 SCAIL-2 wan-scail2 commit 78fe19576bb06be96c2375e088574a262a300edb 및 SAT commit ac63f8eb369e2f4fac2ce273ead0ae7e602c3919를 우선한다. 바뀐 upstream 사용 시 차이를 기록한다.
- **격리된 새 실험 환경**에서만 필요한 FlashAttention 의존성/소형 커널 테스트를 허용. 기존 VACE Python/ComfyUI를 변경하지 않는다. sudo, 드라이버, OS, swap, clock, 다른 프로세스 종료, 유료 GPU 금지.
- 추가 package 다운로드 합계 최대 2GB, 총 작업 최대 2시간, 빌드 worker 최대4개, 메모리 가용량 fresh 계측 후 보호. 빌드 실패 시 원인을 기록하고 최대 2가지 근거 있는 방법까지만 시도. 무한 버전 탐색/소스 패치 금지.
- 모델 다운로드를 완료하지 못했다는 이유로 가중치를 임의 생성하거나 모델을 바꾸지 않는다.

## A. 실제 GB10 Attention smoke

1. fresh CPU/OS/ARM64/GB10 CC(12,1), torch/CUDA, FlashAttention module/distribution, GPU 타 작업과 메모리·디스크를 읽기 전용 확인.
2. 공식 model_scail2.py가 직접 import/call하는 flash_attention signature, Q/K/V layout, dtype, head_dim, causal flags와 실제 경로의 FA2/FA3 선택을 고정 코드에서 확인.
3. 공식 모델의 Q/K/V 연산과 호환되는 **작은 무작위 BF16 tensor**만으로 실제 kernel import + forward를 실행하고 유한값/shape 및 참조 PyTorch SDPA와 수치 차이를 확인. tiny tensor smoke조차 안 되면 BLOCKED. 단순 pip install/import 성공은 PASS 아님.
4. SM121 GPU 관련 타 프로젝트의 FlashAttention 오류 사례는 이 모델에서도 반드시 재현된다고 일반화하지 않는다. 관련 워크어라운드는 별도 가설로 보고하고 조용히 SCAIL의 backend를 교체하지 않는다.
5. 공식 1.3B CLI 옵션이 존재해도 실제 1.3B weights와 호환성이 공식 확인되지 않으면 경량 모델이 출시됐다고 간주하지 않는다.

## B. 새 생성 없이 입력/mask/FPS 검증

- 실제 원본 RGB 17프레임(24fps)과 Lab 사진을 private local에서 읽기 전용으로 확보. 원본 경로를 추측하거나 개인 전체 디스크 검색 금지.
- 공식 --image/--mask_image/--pose(RGB driving)/--mask_video 및 --replace_flag 의미 검토.
- VACE의 full-white mask와 SCAIL의 white/black/색상 instance 대응 mask를 혼동하지 않는다. 같은 동물 ID를 reference/driver에 유지하며 가림·경계·배경의 불확실성을 기록하고 RGB/mask pair를 동일 spatial transform로 검사한다.
- 원본 프레임 sample times t_i=i/24 s, 17프레임 file duration 17/24와 endpoint interval 16/24를 구분. SCAIL 기본 writer sample_fps=16을 그대로 쓰면 출력 속도가 달라진다. 후속 baseline의 24fps 저장 override 방안을 코드와 테스트로 제시하되 이번에 diffusion MP4 생성 금지.
- 공식 512p(예:512x896, H/W=32 배수)의 center crop이 원본 머리·발을 자르는지 실제 정적 preview로 검사. 종횡비/resize/pad 선택 이유 및 원본 RGB와 reference/driving mask 동일 변환을 기록한다.

## C. 체크포인트/변환/메모리 위험

- 공식 HF metadata의 비선택 LoRA 제외 약 80,002,038,274 bytes와 SAT 65,582,563,395-byte checkpoint를 현재 revision 기준으로 다시 확인. 실제 다운로드는 안 한다.
- .pt → Wan safetensors 변환 스크립트를 읽고 변환 중 CPU RAM 피크·출력 파일을 동시에 보유할 디스크 및 통합메모리 추가 사용을 계산/추정. 코드만 보고 모르는 peak를 실측이라 부르지 않는다.
- 128GB 통합 메모리에서 CPU offload는 새로운 별도 GPU 메모리를 만드는 것이 아님. 현재 MemAvailable fresh 관측과 peak-risk 수준을 표로 기록.
- 14B BF16 DiT, T5, CLIP, VAE, conditioning attention의 resident/activation, sequence-length 영향을 구별. 실제 모델 load peak는 NOT_MEASURED.

## 결정

PASS_PRECHECK = 작은 SCAIL-specific kernel 실제 성공 + 입력/mask/FPS/리소스 사전검증 완료. 이는 SCAIL model load/inference/생성 품질 성공이 아님.

BLOCKED = 필수 SM121 kernel/ABI 또는 준비 계약·메모리/저장공간 문제. 재현 가능한 오류와 대안 하나만 보고.

**B-007B (약80GB 체크포인트 다운로드, 변환, single-GPU 공식 예제 1회 + 실제 17f 1회)는 이번 승인 범위 밖이며, 사용자가 결과를 보고 별도로 요청한 이후에만 실행한다.**

## 수학·학습 자료

한국어 lessons/B-007-attention-memory-feasibility.md: scaled dot-product attention softmax(QK^T/sqrt(d))V, attention N^2 vs tiled/FlashAttention IO, SCAIL의 reference+driving token 수, 14B model 가중치와 activation·변환 peak의 차이, unified memory/offload 제약, 24→16fps 시간축 변형을 수식과 실제 코드 위치로 설명. 이해 질문/답안 별도. 공식 kernel/weights 실제 실행 결과와 코드 기반 유도를 구분한다.

## 연구 GitHub/산출물

기존 CHARTER, ROADMAP, HISTORY, RECORDING_PROTOCOL, B-006 RESULTS/MODEL_AUDIT를 읽고 시작. 별도 비민감 실험 코드/config/검증 요약을 PLAN 실행 전 커밋. 종료 후 B-007-scail-preflight/RESULTS.md, REPRODUCE.md, lessons/B-007-attention-memory-feasibility.md 및 HISTORY/ROADMAP 갱신·push, 원격 SHA 확인. 비공개 source/overlay/video/mask, 개인 절대경로, 대형 weights, secret, raw log를 공개 repo에 올리지 않는다. Mac/Spark private review ZIP CRC+파일 hash+SHA 검증. 소요·실제 변경·BLOCKED 이유·다음 승인 단계 하나 보고, 자동 확대 금지.
