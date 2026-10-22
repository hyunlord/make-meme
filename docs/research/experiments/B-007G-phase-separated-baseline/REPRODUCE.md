# B-007G 재현 범위와 순차 실행

최종: **P CONDITION_CACHE_PASS / S_BLOCKED / D NOT_RUN**. 이번 실행은 종료됐으며 아래 명령은 당시 재현 계약이다. 남은 단계나 sampler를 자동 실행하지 않는다. 이 문서는 [PLAN](PLAN.md)의 한정된 공식 예제 P/S/D 실행을 설명한다. 명령이 있다는 사실은 실행 완료를 뜻하지 않는다. deadline이 지났거나 stage reservation이 이미 존재하면 실행을 반복하지 않는다. 이후 재실행에는 별도의 승인된 예산과 새 기록이 필요하다.

## 고정 계약

- SCAIL source `78fe19576bb06be96c2375e088574a262a300edb`; 기존 E의 검증된 weights·환경·공식 inputs를 읽기 전용으로 재사용한다.
- 공식 예제 한 개, H512×W896, 17프레임·16fps, seed20261022, UniPC40 step, CFG5, shift3, adapter 없음.
- 실제 P 한 번, S 최대 한 번, 그 final latent의 D 한 번. 실패 시 후속 중지, 자동 재시도 없음. Lab/새 seed/tiling/해상도 변경/학습 없음.
- 24GiB 시스템 headroom·swap0 가드를 유지한다. cgroup cap만으로 전체 CUDA unified memory를 제한했다고 간주하지 않는다.
- G 실행 checkout/code/config 해시는 실제 사전 등록 manifest를 확인한다. 문서가 최신이라고 다른 checkout의 code를 섞지 않는다.

## 실행 전 확인

각 stage root에는 `code/`, `environment/`, `upstream/`, `models/`, `configs/`, `reports/`, `artifacts/`와 해당 입력 계약이 필요하다. 실제 stage root는 `${RUN_ROOT}/stages/P`, `${RUN_ROOT}/stages/S`, `${RUN_ROOT}/stages/D`이며 공유 artifact는 `${RUN_ROOT}/artifacts`다. 각 worker는 독립 프로세스이며 tensor IPC는 없다. 경로를 추측해 새 모델을 설치하거나 기존 디렉터리를 덮어쓰지 않는다.

[run_phase.py](code/run_phase.py)는 `ROOT P|S|D`를 받는다. stage별 `reports/attempt.json`은 exclusive 생성이므로 기존 기록을 삭제하거나 같은 stage를 재실행하지 않는다. [runtime_launch.py](code/runtime_launch.py)는 `ROOT SECONDS COMMAND...`를 받아 남은 절대 deadline보다 짧게 실행 시간을 제한한다. 다음은 경로를 외부에서 지정하는 명령 형식이며 실제 사용한 root/시간은 launch receipt가 기준이다.

```sh
# RUN_ROOT는 승인된 G 실행 root다. 각 단계 직전에 설정한다.
STAGE=P
PHASE_ROOT="${RUN_ROOT}/stages/${STAGE}"
# STAGE=P, 그다음 성공/종료 확인 후 S, 마지막 성공/종료 확인 후 D.
"${PHASE_ROOT}/environment/bin/python" \
  "${PHASE_ROOT}/code/runtime_launch.py" "${PHASE_ROOT}" 7200 \
  /usr/bin/env PYTHONDONTWRITEBYTECODE=1 CUDA_MODULE_LOADING=LAZY \
  OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  IMAGEIO_FFMPEG_EXE=/usr/bin/ffmpeg \
  "${PHASE_ROOT}/environment/bin/python" \
  "${PHASE_ROOT}/code/run_phase.py" "${PHASE_ROOT}" "${STAGE}"
```

이 형식을 세 번 무조건 실행하는 shell loop로 바꾸지 않는다. 각 단계의 return code, guard 판정, durable artifact readback, worker PID/context 종료와 메모리 회복을 확인한 뒤 다음 단계를 시작한다. 기존 E/F의 부족한 trace를 새로운 실행 관측인 것처럼 채우지 않는다.

## 단계별 검증 자료

| 단계 | 실제 검증할 파일/값 | 후속 조건 |
|---|---|---|
| P | `conditions.safetensors`와 sidecar의 hash/shape/dtype/container, E initial noise 값/SHA, generator state, timesteps/sigmas | `CONDITION_CACHE_PASS` + worker 종료 |
| S | 실제 condition provenance, first forward, progress의40 step/80 call, finite final generated latent와 readback | `SAMPLER_LATENT_PASS` + worker 종료 |
| D | 같은 latent provenance, 기본 VAE decode, raw `[3,17,512,896]` finite, MP417프레임·16fps·896×512 | `VIDEO_OUTPUT_PASS`; 시각/시간 품질은 별도 |

[phase_prepare.py](code/phase_prepare.py)는 encoder만 생성하고 공식 조건 경계를 추출한다. [phase_sample.py](code/phase_sample.py)는 같은 staged DiT loader와 추출된 loop를 사용하며 final latent 저장 후 종료한다. [phase_decode.py](code/phase_decode.py)는 VAE만 생성한다. 저장/재로딩 계약은 [artifacts.py](code/artifacts.py), 공식 함수 경계 검사는 [extract.py](code/extract.py)에 있다.

P/S/D tensor와 원본 영상은 private 산출물이다. 공개 GitHub에는 코드·sanitized receipt와 재현 계약만 둔다. final latent가 없으면 D 재개가 가능하다고 보고하지 않는다. 모델 가중치, 환경, 원본 media, latent를 공개 문서 패키지에 넣지 않는다.

## 현재 결과

P는 guard 정상 종료, PID 0/inactive, 조건 readback을 확인했다. 전체 guard 시간 143.331초, phase 완료 140.53초다. 조건 파일은 17,365,660 bytes, SHA256 `1f1e0b68495b2276a5b6d12eaf160897a16acb2bd2a089e616a55c40bf590308`이며 initial noise는 E raw tensor와 값·hash가 같다. S는 stage 시작 후 115.742초에 CPU DiT 적재 완료를 기록했다. 적재 start/end 간격은 111.869초, 전체 guard 시간은 121.054초다. 조건 cache의 첫 CUDA 복원 경로 `artifacts.load_tree`에서 `cuDevicePrimaryCtxRetain`이 `CUDA_ERROR_OUT_OF_MEMORY`를 반환했다. DiT device 이동 hook, sampler loop, 첫 forward, final latent 저장 모두 미도달이다. D는 실행하지 않았고 final latent/raw/MP4가 없다.

S 슬롯은 1/1 예약됐으며 실패로 보존한다. forward/step counter는 초기화 전 실패로 NOT_RECORDED이며, 재시도는 없다. 마지막 관측은 `cuda_initialized=true`, allocator 0이지만 driver 가용 메모리나 실패 순간 peak를 증명하지 않는다. global headroom guard는 발동하지 않았고 cgroup high2660/oom0, swap0이었다. 정확한 driver/context/통합 메모리 원인은 UNKNOWN이다. [RUN_LEDGER](RUN_LEDGER.json)와 [MEASUREMENTS](MEASUREMENTS.json)를 확인한다.

새 sampling 없이 기존 P cache를 활용한 CPU 적재·context 준비·조건 복원 순서의 한정 조사가 다음 제안이다. 해당 제안은 이 문서의 명령을 다시 실행하라는 승인이 아니다. CPU fixture 통과는 full-model 수치 동등성이나 영상 성공이 아니다. [이론 문서](../../lessons/B-007G-component-lifetime.md)의 E 관측값과 G 예상값을 구분한다. 연속 재생을 직접 확인하지 못하면 시간 품질은 UNVERIFIED다.
