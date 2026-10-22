# B-007F 재현 계약

현재 공식 실행은 첫 DiT forward 이전 headroom guard로 종료됐다. launch entry는 아래 사전 commit으로 고정됐다. [PLAN](PLAN.md)이 우선이며, 문서만으로 과거 B-007E나 새 예산을 초기화하지 않는다. 고정된 실행 명령은 아래와 같다.

## 고정할 입력과 유일한 변경

SCAIL source `78fe19576bb06be96c2375e088574a262a300edb`, B-007E parent `aae93748cb1eebc89d68670673c301d739ebe149`, 변환 checkpoint SHA256 `8b844f026510f0b94d3209d66444b403a089ec179dc149d85513c13b2fa37118`을 보존한다. 실제 입력8개와 T5/CLIP/VAE/FA hash는 [B-007E 사전 목록](../B-007E-scail-forward/PREREGISTERED_INPUTS.json)에 연결한다.

공식 H512W896·17f16fps, Lab H896W512·17f24fps, seed20261022·40steps·UniPC·shift3·CFG5·LoRA OFF를 유지한다. post-loop model.cpu만 생략하고 그 위치의 empty_cache와 앞선 offload는 그대로 둔다. isolated source exact diff와 hash, sidecar/phase observer hash를 실제 실행 전에 고정한다.

## 실행 순서

1. 승인된 환경의 resource/queue/swap과 deadline을 확인한다. private `${RUN_ROOT}`·`${MODEL_ROOT}`·`${INPUT_ROOT}`를 매핑하며 실제 경로·secret을 공개하지 않는다.
2. 작은 mock에서 선택한 post-loop 이동만 생략되는지, final latent 저장이 decode보다 먼저인지, decode 실패 때 저장물이 남는지 확인한다. 이 PASS는 GPU 메모리 결과가 아니다.
3. 기존 A·B/ComfyUI와 원본을 변경하지 않는 새 run ID로 공식 sampler 최대1회를 실행한다. B-007E의 실패 장부는 유지한다. 전체 sampler 상한2회에는 실패도 포함한다.
4. 최종 decode 인자 latent와 sidecar의 원자적 완료/hash/값 검증, 실제 completed-step·forward count, phase trace를 확인한다.
5. 공식 raw finite/shape17f·MP4 decode/fps·정상 guard 종료와 자원 회복이 모두 확인된 경우에만 새 프로세스로 Lab 최대1회를 진행한다. 실패하면 Lab NOT_RUN으로 종료한다.

원래 실행 deadline이 만료됐거나 시도가 이미 소비됐다면 명령을 재실행하지 않는다. 새로운 허가 없이 ledger 삭제·새 root로 횟수 초기화·해상도/seed 변경 재시도는 하지 않는다.

## 결과 재사용

latent 파일만 열어 shape가 맞는 것으로 decode 완료를 주장하지 않는다. VAE code/weight/scale과 payload hash, sampler 종료 증거, segment metadata가 함께 있어야 재사용 가능한 final latent다. initial_noise는 대체물이 아니다. 이번에 final latent만 남았다면 다음 별도 실험에서 sampler를 다시 실행하지 않고 decode를 연구할 수 있지만, 이 문서는 그 후속 실행까지 승인하지 않는다.

영상·latent·사진·mask는 private 산출물이다. 공개 자료에는 alias·hash·집계와 재현 코드만 둔다. 실제 raw/MP4가 없다면 review 작업을 수행한 것으로 표시하지 않는다. 연속 재생 관찰이 없다면 temporal 품질은 UNVERIFIED다.

## 실제 사전 고정 entry

실행 사전 고정 commit은 `97189c029ac298b0aded73990d1858d5df9b93bf`이며 원격 반영을 확인했다. [prepare_cases.py](code/prepare_cases.py)는 각 case의 source/code/config를 분리하고 기존 B-007E environment/models/inputs를 symlink로 참조한다. 기존 모델을 복사·변경하지 않는다. `${RUN_ROOT}`는 B-007F의 비공개 root다.

공식 예제의 실제 launcher 형태:

```sh
"${RUN_ROOT}/cases/official/environment/bin/python" \
  "${RUN_ROOT}/cases/official/code/runtime_launch.py" \
  "${RUN_ROOT}/cases/official" 7200 \
  /usr/bin/env PYTHONDONTWRITEBYTECODE=1 CUDA_MODULE_LOADING=LAZY \
  OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  IMAGEIO_FFMPEG_EXE=/usr/bin/ffmpeg \
  "${RUN_ROOT}/cases/official/environment/bin/python" \
  "${RUN_ROOT}/cases/official/code/runtime_infer.py" \
  "${RUN_ROOT}/cases/official" \
  "${RUN_ROOT}/cases/official/configs/official.json"
```

공식 완료 및 자원 회복 gate를 모두 확인한 경우에만 별도 프로세스로 실행하는 Lab entry:

```sh
"${RUN_ROOT}/cases/lab/environment/bin/python" \
  "${RUN_ROOT}/cases/lab/code/runtime_launch.py" \
  "${RUN_ROOT}/cases/lab" 7200 \
  /usr/bin/env PYTHONDONTWRITEBYTECODE=1 CUDA_MODULE_LOADING=LAZY \
  OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  IMAGEIO_FFMPEG_EXE=/usr/bin/ffmpeg \
  "${RUN_ROOT}/cases/lab/environment/bin/python" \
  "${RUN_ROOT}/cases/lab/code/runtime_infer.py" \
  "${RUN_ROOT}/cases/lab" \
  "${RUN_ROOT}/cases/lab/configs/lab.json"
```

7200초는 요청값이며 [runtime_launch.py](code/runtime_launch.py)는 전체 deadline **2026-10-22 18:50:53 UTC**에서90초를 남기는 값으로 줄인다. 한국시간으로는 다음 날이다. 기존 expired deadline을 바꾸거나 exclusive ledger를 삭제해 재실행하지 않는다. watchdog systemd unit과 guard가 자기 runtime unit만 정리한다. 명령이 고정됐다는 사실은 실행 성공을 뜻하지 않는다.

## 실제 종료와 재실행 금지

공식 새 sampler 예약1/2를 사용했고 forward0에서 종료했다. 마지막 durable phase는 pipeline_loaded, 정확한 pre-forward subphase는 UNOBSERVED다. full load331.4초, preprocess340.9초이며 initial noise는 E와 일치했다. MemAvailable25,676,087,296 bytes<24GiB, swap0/OOM0으로 중단했다.

post-loop 이동 생략과 final latent 저장은 NOT_REACHED다. raw/MP4/final latent는 없고 Lab는 NOT_RUN이다. 위 명령은 실패한 실제 실행의 기록이며 남은 슬롯을 자동 소비하라는 지시가 아니다. 같은 ledger를 유지하고 재시도하지 않는다. 다음 제안은 기존 증거·소스의 CPU-only pre-forward 이동/소유·guard trace 검토 하나다. final latent가 없으므로 decode 재개 명령도 제공하지 않는다.
