# B-007G 재현 범위와 순차 실행

현재: **실물 실행 결과 대기**. 이 문서는 [PLAN](PLAN.md)의 한정된 공식 예제 P/S/D 실행을 설명한다. 명령이 있다는 사실은 실행 완료를 뜻하지 않는다. deadline이 지났거나 stage reservation이 이미 존재하면 실행을 반복하지 않는다. 이후 재실행에는 별도의 승인된 예산과 새 기록이 필요하다.

## 고정 계약

- SCAIL source `78fe19576bb06be96c2375e088574a262a300edb`; 기존 E의 검증된 weights·환경·공식 inputs를 읽기 전용으로 재사용한다.
- 공식 예제 한 개, H512×W896, 17프레임·16fps, seed20261022, UniPC40 step, CFG5, shift3, adapter 없음.
- 실제 P 한 번, S 최대 한 번, 그 final latent의 D 한 번. 실패 시 후속 중지, 자동 재시도 없음. Lab/새 seed/tiling/해상도 변경/학습 없음.
- 24GiB 시스템 headroom·swap0 가드를 유지한다. cgroup cap만으로 전체 CUDA unified memory를 제한했다고 간주하지 않는다.
- G 실행 checkout/code/config 해시는 실제 사전 등록 manifest를 확인한다. 문서가 최신이라고 다른 checkout의 code를 섞지 않는다.

## 실행 전 확인

각 stage root에는 `code/`, `environment/`, `upstream/`, `models/`, `configs/`, `reports/`, `artifacts/`와 해당 입력 계약이 필요하다. 실제 stage root 구성과 공유 artifact 연결은 실행 담당자의 고정 layout을 따른다. 경로를 추측해 새 모델을 설치하거나 기존 디렉터리를 덮어쓰지 않는다.

[run_phase.py](code/run_phase.py)는 `ROOT P|S|D`를 받는다. stage별 `reports/attempt.json`은 exclusive 생성이므로 기존 기록을 삭제하거나 같은 stage를 재실행하지 않는다. [runtime_launch.py](code/runtime_launch.py)는 `ROOT SECONDS COMMAND...`를 받아 남은 절대 deadline보다 짧게 실행 시간을 제한한다. 다음은 경로를 외부에서 지정하는 명령 형식이며 실제 사용한 root/시간은 launch receipt가 기준이다.

```sh
# PHASE_ROOT와 STAGE는 승인된 stage layout에서 설정한다.
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

실제 stage launch와 완료 receipt는 아직 이 문서에 반영되지 않았다. CPU fixture 통과는 full-model 수치 동등성이나 영상 성공이 아니다. [이론 문서](../../lessons/B-007G-component-lifetime.md)의 E 관측값과 G 예상값을 구분한다. 연속 재생을 직접 확인하지 못하면 시간 품질은 UNVERIFIED다.
