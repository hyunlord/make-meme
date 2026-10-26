# B-031 사전 코드·계약 검토

## 검토 범위와 상태

읽기 전용 검토와 CPU fixture 검사다. 이미지 생성, SCAIL forward, 앵커 적합성 또는 영상 품질의 PASS가 아니다. 기존 모델 전체나 직렬화·CUDA 커널 감사를 반복하지 않았다.

검토 대상은 `code/prepare_inputs.py`, Qwen 실행·관측·가드 코드와 `video_code/`의 파생 cache, 실행 예약, sampler 및 decode 연결이다. 구현 담당자와 별도의 검토자가 확인했다. 독립 인간 시각 평가는 아니다.

## 확인된 계약

| 항목 | 코드 근거와 확인 내용 |
|---|---|
| 입력 순서·범위 | `prepare_inputs.py`, `qwen_contract.py`: 기존 공개 3과제의 R1/R2 6개 고정 순서. Image1은 처리된 source 첫 전체 프레임, Image2는 target GT bbox에 고정 10% margin을 적용한 crop. support 내부 픽셀 보존, 밖은 128. |
| 이미지 호출 상한 | `qwen_runner.py`: 전체 실행 및 case별 예약을 배타적 파일 생성으로 기록하며 pipeline 호출 전에 case 시도를 예약한다. 고정 6개 순회, 재시도 없음. 실제 40 step·80 transformer forward 및 유한한 896×512 RGB 출력 검사. |
| 관측 부작용 | 실제 첫 forward들의 작은 hash·shape와 기존 step callback을 사용한다. 관측을 위한 추가 모델 forward가 없고 hook은 finally에서 제거한다. |
| 로컬 모델 경로 | `local_files_only=True`, offline 환경 설정. `qwen_preflight.py`는 pinned revision의 파일 크기·LFS SHA256 또는 Git blob ID와 pipeline 소스 hash·패키지 버전을 기록한다. |
| 자원·종료 | `qwen_guard.py`, `qwen_launch.py`: 시작 72GiB, 실행 24GiB headroom, swap 0, 기존 GPU process identity·서비스 queue 확인. 소유 unit만 중단하며 최대 64GiB cgroup cap 및 보존 시간을 남긴 deadline을 적용한다. |
| 영상 선택 | `prepare_video.py`: R1·적합 판정·Qwen process 종료 확인을 요구한다. task별 새 디렉터리와 배타적 phase 예약으로 중복 실행을 차단한다. R2로 사후 교체하지 않는다. |
| 조건 파생 | `phase_reference.py`, `anchor_contract.py`: 새 R_star의 VAE·CLIP·공식 mask helper 결과만 양 CFG에 적용한다. 허용 변경은 reference 6 leaf, 나머지 10 leaf는 정확한 hash 보존. 허용 6개 전부가 반드시 달라야 한다고 요구하지 않는다. |
| 원래 입력 보존 | `contracts.py`: B-027 producer receipt, 원래 condition cache, 실제 initial-noise 파일과 tensor, tree의 dtype·shape·device 계약을 확인한다. producer와 새 consumer를 구분한다. |
| sampler 보존 | `phase_sample.py`를 기존 B-030 경로와 비교한 변경은 계보 관측 및 실험 식별 기록이다. 공식 sampler 추출·history=None·CFG 40 step/80 forward·replacement 경로를 유지한다. |
| 최종 latent | sampler 완료 후 synchronize·finite·shape·40/80 counter 검사를 거쳐 lossless CPU 저장물을 원자적으로 저장하고 검증한다. 별도 D가 이를 읽는다. 초기 noise를 final latent로 취급하지 않는다. |
| decode | `phase_decode.py`: VAE-only decode, finite `[3,17,512,896]`, 17프레임·preview24fps 검증. decode 실패에 따른 sampler 재시도 없음. temporal은 UNVERIFIED로 남긴다. |

## 실제 CPU 검사

다음 세 파일의 fixture 검사를 함께 실행했다.

```sh
python3 -m pytest -q \
  docs/research/experiments/B-031-source-aligned-edit-anchor/video_code/test_anchor_contract.py \
  docs/research/experiments/B-031-source-aligned-edit-anchor/code/test_prepare_inputs.py \
  docs/research/experiments/B-031-source-aligned-edit-anchor/code/test_qwen_contract.py
```

결과: **10 passed, 0.18초**. 입력 순서·고정 크기/seed, crop 픽셀 계약, 조건 leaf 변경 범위를 검증했다. 모델을 적재하지 않았으며 실제 14B 수치 동일성이나 이미지 모델의 메모리 수용성을 입증하지 않는다.

## 실행 전 남은 확인과 한계

- 최초 검토에서 Qwen runner와 preflight/환경 lock의 강제 연결이 빠져 있음을 전달했고, 후속 `qwen_freeze.py`에서 보완을 확인했다. runner는 CUDA와 모델 적재 전에 코드·입력 계약·모델 검증 보고서·환경 lock hash, pinned revision/PASS, 설치 버전과 pipeline 소스 hash 및 검증된 파일의 크기/mtime을 검사한다. 대형 가중치 전체 hash는 preflight에서 확인하며 실행 직전 stat 검사는 그 검증을 대체하는 별도 hash 검사가 아니다. 실제 preflight 완료 여부는 실행 장부에서 확인해야 한다.
- 재계산한 전처리 예시는 `equivalent_preprocess_exports`로 구분하며 실제 encoder 호출의 tensor shape/dtype/hash는 별도 hook으로 기록한다. hook은 기존 호출을 관측하고 추가 인코딩을 실행하지 않는다.
- 전체 BF16 모델을 CPU에서 적재한 뒤 GPU로 순서대로 이동한다. 64GiB cap은 안전 중단 상한이지, 파일 페이지·일시적 복사·activation을 포함한 실행 성공 보장이 아니다. 실제 phase별 계측으로 판단해야 한다.
- 이미지 pipeline 예외가 발생하면 다음 case로 넘어가거나 재시도하지 않는다. `attempt.json`과 `last-observed.json`을 실패/중단 장부 및 guard reason과 함께 해석해야 하며 systemd 종료 코드만으로 성공 판정하지 않는다.
- 실제 앵커 6개와 조건부 영상은 이 검토 시점에 검증하지 않았다. R1 적합성, 수동 support, 프로세스 종료와 자원 회복, 새 condition cache 및 최종 결과는 별도의 실행 증거가 필요하다.

사전 코드 검토에서 발견한 범위 내에는 추가 sampler나 허가되지 않은 모델·학습 경로가 없었다. 이 문서는 후속 실제 실패를 소급 PASS로 바꾸는 근거가 아니다.
