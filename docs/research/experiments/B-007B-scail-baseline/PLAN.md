# B-007B — SCAIL-2 실제 로컬 모델 baseline (조건부 실행 계획)

작성: 2026-10-22 · **PLANNED / NOT_RUN** · parent: B-007A
이 문서는 다음 Codex 지시를 위한 실행 계획이다. GitHub에 계획을 올린 사실은 다운로드·변환·추론을 실행했다는 뜻이 아니다.

## 0. 연구 목적과 성공 기준

B-007A에서 DGX Spark GB10(CC12.1)의 SCAIL 공식 attention wrapper 기반 FlashAttention2.8.4/BF16 small QKV 4/4 PASS(최대 abs 차이 0.00465846) 및 입력 mask packing/FPS 기본 계약을 확인. 다만 실제 14B 모델 로딩/변환 peak/긴 sequence 커널과 원본 춤의 재현 품질은 NOT_RUN.

이번 B-007B에서 **실제 SCAIL-2 Wan RGB driving baseline 1개 이상**을 확보하는 것이 목표. “모델이 올라갔다”와 “Lab 정체성+안무가 일치한다”는 별도 판정이다. 연구 목적(이론·텐서·코드 이해 및 Spark 실측)을 우선하며, 서비스/논문 성과를 선언하지 않는다.

## 1. A/B 경계 및 범위

- B만 진행. A의 imagegen-only 모델·MCP·자산·장부 동결. native imagegen·외부 생성 API 사용 금지.
- 공식 고정 Wan SCAIL2 commit 78fe19576bb06be96c2375e088574a262a300edb, HF metadata revision 150cc0ca4e98e50e60b9295dacde39442fdccab2, B-007A 성공한 격리 FlashAttention extension binary hash 확인. 다른 FA 버전/실험 브랜치로 조용히 교체하지 않는다.
- 새 전체 모델 학습/LoRA 업데이트 0회, optional bias-aware/relighting LoRA 사용 안 함.
- 총 작업 상한 6시간. 새로운 전체 diffusion inference는 **최대 2회(실패 포함)**: 공식 예제 17프레임 smoke 가능 시 1회, 실제 원본17프레임+실제 Lab 1회. 공식 예제를 구할 수 없으면 실제 단일 구간 먼저 1회만 실행하고 차단/품질 해석 범위를 남긴다. 해상도는 공식 단일 개체 512p, 최초 생성 단계부터 두 개체/15초로 확대 금지.
- 추가 모델 다운로드는 선택적 LoRA 제외 필요한 모델/토크나이저 파일만 **최대 85GB(decimal)**; 중복 다운로드·무제한 재시도·다른 모델 다운로드 금지. 설치 도구 및 소스의 소규모 자산은 별도 기록하고 불필요한 환경 변경 금지.
- 디스크는 원본 체크포인트 약80.002GB + 변환 output + 캐시·로그/임시 파일을 충분히 수용해야 한다. 최소 **300GB free 유지**를 우선 안전가드로 사용하고, 현재 값은 시작할 때 다시 측정.
- CPU/GPU 통합 메모리 가용량 fresh 실측, 기존 다른 작업·OS의 headroom을 확보. 예: pre-stage MemAvailable >=80GiB 권장, 실행 중 MemAvailable 30GiB 이하 지속·swap 급증/OS memory pressure/다른 서비스 영향 감지 시 **자기 프로세스만 중단**. 이 숫자는 시스템 안전 보장의 증명이 아니므로 cgroup/job limits, watchdog와 단계별 상한을 추가한다. sudden OOM 가능성 고지.
- sudo, OS/driver/CUDA 글로벌 변경, swap/클럭 변경, 다른 프로세스 종료, 원격 유료 GPU/API 금지. 기존 VACE/ComfyUI 환경 보존.

## 2. Gate 0 — 원본/설치/추론 동작 고정 (no download)
- B-007A ZIP/RESULTS/INPUT_PREFLIGHT/MODEL_RESOURCE_AUDIT 및 공식 source 코드 읽기. 실제 성공한 GB10 FlashAttention4케이스를 동일 격리 경로에서 다시 한 번 bounded 확인(필요시); 작은 연산 PASS만으로 full sequence PASS 판정 금지.
- B-007A reference/driving 17개 RGB+red color mask가 존재하고, 모두 decode/색상 ID 해시 및 동일 geometry가 일치하는지 확인. f0/f1의 바닥 반사·얇은 마스크 잔여 **PARTIAL** 판정 그대로 유지. 수동 수정은 눈에 보이는 명확한 국소 오류에 한정하고 전후/비용 기록; 무한 마스크 보정 금지.
- 실제 준비 사이즈 H896×W512(사진 방향 때문에 가로 원본이 center crop)와 모든 관찰점·발의 시야를 재검토. **원본의 좌우 장면 전체 재현 성공**이라는 주장은 금지.
- 모델 입력 FPS는 원본 프레임 시각 t_i=i/24. 공식 writer cfg.sample_fps=16이므로 **단순 output metadata 변경과 training prior**를 구분한 explicit 24fps writer patch를 isolated tree에서 실제 integration test(최종 저장 ffprobe)하도록 한다. 17 프레임 24fps 파일 길이 17/24, 첫~끝 간격16/24. 학습된 native16fps prior 때문에 입력24fps의 속도/움직임 품질은 별도 한계다.
- official convert.py는 checkpoint=torch.load(path) 후 전체 state_dict를 key mapping하여 safetensors.save_file. official wan/scail.py는 safetensors.load_file 후 self.model.load_state_dict. **변환과 로딩 모두 메모리 2차 피크 위험**이 있으므로 분리해서 설계.

## 3. Gate 1 — 대용량 데이터 다운로드 전에 메모리 안전 변환 방식 검증
- 65.582GB SAT .pt를 기본 torch.load로 바로 읽기 전에 conversion을 작은 synthetic fixture로 검사한다. checkpoint serialization 구조가 mmap/fake loading을 지원하는지는 실제 파일을 확보한 뒤 metadata-only로 확인할 수 있다.
- 공식 get_new_mappings/get_new_state_dict와 동일한 key mapping, QKV/KV 분할, dtype/shape/contiguity를 유지하는 **저피크 변환 방법**을 먼저 검토한다. 작은 fixture에서 공식 출력과 키 목록·dtype·값·해시 비교 통과 후에만 대형 변환으로 확장한다. safe mmap/streaming 등이 불가능하면 “변환 peak UNKNOWN / 메모리 OOM 위험”으로 STOP하고 변환을 무작정 실행하지 않는다.
- 파일 format이 허용된다면 map_location=cpu/weights_only/mmap/FakeTensorMode 등의 방법을 실제 API/serialization 규칙에 맞게 비교 검증한다. 이 옵션이 언제나 문제를 해결한다고 가정 금지. 불신 가능한 pickle의 무검증 실행 금지.
- 고정 모델 convert.py를 직접 덮어쓰기보다 격리 wrapper/변환기를 마련하고 정확한 차이를 기록. 전체 모델이 진짜 동작하는지 보려면 변환 결과 key/dtype/shape가 SCAIL expected state와 맞아야 한다.
- 변환 중에도 S+E+W+C 메모리 추정과 보수적 headroom이 마련되지 않으면 저장공간만 충분하다는 이유로 진행하지 않는다. 실패한 변환은 원본을 보존하고 partial result를 공식 가중치로 보고하지 않는다.

## 4. Gate 2 — 선택 파일 다운로드·검증
- Gate 1의 저피크 conversion 경로가 타당하고, GPU·시스템 가용 자원이 안전하다는 판단일 때만 pin HF revision으로 모델 필수 80.002GB를 선택 다운로드. optional LoRA 제외. files SHA256, 길이/ETag/Hub revision과 resume 정보 기록. 별도 cache 중복을 확인해 다운로드 상한 유지. 접근 거절 시 우회하지 않음.
- 실패/일시중단 시 범위 내 이어받기는 가능하지만 다운로드의 무한 반복, 원격 API 기반 이미지·영상 생성 전환 금지.
- 다운로드 완료를 모델 실행/추론 성공으로 보고하지 않는다.

## 5. Gate 3 — bounded 변환과 로딩·추론
- B-007A에서 확인한 attention extension을 사용. 압박 상황에서 65GB checkpoint를 한 번에 GPU로 복원하려 들지 않는다. 로딩 단계 최대 메모리와 OS MemAvailable/다른 작업 간섭을 관측한다.
- 변환 output safetensors에 checkpoint key mapping/shape/dtype/count를 확인하고 원본 파일 보존. conversion이 막히면 **전체 모델 생성은 NOT_RUN** 처리.
- 전체 모델 load 중 실제 peak/baseline and post-load memory, DiT/T5/CLIP/VAE 구성, CPU offload time·memory, processed tokens/actual frame shape를 기록. 통합메모리를 CPU/GPU 별도 두 배로 합산하지 않는다. 기존 소스의 init_on_cpu/offload/t5_cpu 옵션을 검토하고 설정 변경은 하나씩 문서화.
- 공식 예제 자산이 실제 호환되면 17프레임 공식 example **최대1회** smoke 후 Lab 단일 컷 1회. official example의 실제 reference/mask/driver를 다른 사용자/데이터로 임의 대체하지 말고 공식 입력 여부를 기록. 모델이 조건을 충족하지 못하면 다음으로 확대 금지.
- 실제 Lab 17프레임은 동일 red instance ID, 정적 검토한 512p RGB/crop/mask, 선택적 prompt enhancer OFF, optional LoRA OFF. 실제 output fps를24로 명시하고 source t_i alignment 및 frame count 확인. 샘플러/step/seed/solver를 결과 본 뒤 튜닝하거나 재시도하지 않는다.
- CUDA OOM/unsafe pressure/other workload interference 발생 시 자기 프로세스만 중단 후 BLOCKED 이유·측정값과 복구 상태 남김. 모델 병렬 작업 금지.

## 6. 평가와 학습
- 출력 MP4와 source/reference/driving masks를 side-by-side로 제공. 실제 연속 속도에서 직접 재생한 주체와 검수 결과를 명시. agent가 재생 못하면 UNVERIFIED; static frame만으로 시간 PASS 금지.
- 동물 개체(실제 Lab facial/body/coat), body shape, upright pose, f0~f16 head/paw phase, foot-ground contact, mask leakage, temporal identity, 배경/반사, crop을 분리 평가. 마스크 손실로 인한 실패 vs 모델의 retarget 실패도 분리. 품질 목표를 충족하지 못하면 그대로 FAIL.
- 수학 lessons/B-007B-conversion-and-model-forward.md: SAT→Wan weight remapping, safetensors tensor layout/peak memory, scaled dot product attention actual sequence vs 64 token smoke, sampling step & model calls, temporal prior mismatch 16/24 fps. 실제 traced tensor shape와 code source/가정 구분, 질문/답안 별도.

## 7. GitHub와 산출물
- 시작 전 PLAN 및 코드/config hash를 연구 브랜치에 commit/push; 기존 README/CHARTER/ROADMAP/HISTORY/RECORDING_PROTOCOL 준수. B-007A 코드/빌드/연구 환경과 A 보존.
- 종료 후 docs/research/experiments/B-007B-scail-baseline/RESULTS.md, logs/재현/메모리 측정 요약, 이론, HISTORY/ROADMAP 갱신·commit/push, remote HEAD 직접 확인. 공개 저장소에 실제 사진/영상/원본·mask·개인 IP/path·토큰, 대형 weights/cache/adapter/raw logs를 올리지 않는다.
- private outputs·지표·실제 실행의 자원수치와 성공/실패 모두 보존. Mac/Spark private review ZIP 하나에 작은 대표 영상/정적 frame/재현/요약 포함, 크기·SHA256/CRC·manifest 검사. 큰 weights/전체 checkpoint를 ZIP에 넣지 않는다.
- **이번 승인 이후 자동 B-008 장기 학습·모델 변경/새 14B 재다운로드/추가 추론 금지.** 결과 기반 다음 한 경로만 제안.
