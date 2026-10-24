# B-016 재현 경로

이 문서는 실제 사용한 명령과 입력 계약의 기록이다. 추가 실행 예산을 승인하지 않는다. 원본 사진·영상·mask·캐시·가중치는 공개 저장소에 없으며, 아래 별칭은 승인된 로컬 자료를 가리켜야 한다. 기존 stage 디렉터리를 재사용해 attempt 파일을 지우거나 횟수를 초기화하지 않는다.

## 고정 입력과 환경

- `B016_ROOT`: 별도 실험 디렉터리. `code/`, `configs/`, `PREREGISTERED_CODE.json`, `PREREGISTERED_INPUTS.json`은 이 실험의 공개 사전 등록 내용과 일치한다.
- `ENV_ROOT`: 기존 B-007E 환경·모델·격리 upstream. 추가 설치 없음.
- `ENV_PYTHON="$ENV_ROOT/environment/bin/python"`.
- `PARENT_ROOT`: 원본 B-013 `cases/LAB_MOV`.
- `SCAIL_MODEL_SOURCE="$ENV_ROOT/upstream/wan/modules/model_scail2.py"`.

원본 SCAIL commit은 `78fe19576bb06be96c2375e088574a262a300edb`, 해당 model 파일 SHA256은 `bbcfc38ee8c4dc8e9f31987e617b57af267c46e8bd25ee046f76e7426d6f5d6c`다. P는 재실행하지 않았다. 기존 `conditions.safetensors`/metadata/receipt/initial-noise를 읽기 전용으로 연결하고, `configs/parent_binding.json`의 원래 코드·입력·P 결과·clean-exit·pair·lineage 기록을 유지한다. 부모 캐시 전체16leaf는 변경하지 않는다.

## 격리 패치와 CPU 검증

공개 `rope_h.patch_source`가 원본의 정확한 signature/site/loop 개수를 확인한 뒤 별도 파일을 만든다. upstream 원본은 수정하지 않는다.

```sh
PYTHONPATH="$B016_ROOT/code" "$ENV_PYTHON" - "$SCAIL_MODEL_SOURCE" "$B016_ROOT/patched/model_scail2.py" <<'PY'
from pathlib import Path
import sys
from rope_h import patch_source
source, target = map(Path, sys.argv[1:])
target.parent.mkdir(parents=True, exist_ok=True)
with target.open('x') as stream:
    stream.write(patch_source(source.read_text()))
PY

CUDA_VISIBLE_DEVICES="" SCAIL_MODEL_SOURCE="$SCAIL_MODEL_SOURCE" \
CPU_NUMERIC_REPORT="$B016_ROOT/reports/cpu-numeric.json" \
"$ENV_PYTHON" -m pytest "$B016_ROOT/code/test_rope_h.py" -q

CUDA_VISIBLE_DEVICES="" "$ENV_PYTHON" \
  "$B016_ROOT/code/cpu_module_fixture.py" "$B016_ROOT"
```

마지막 meta fixture는 `wan` package initializer의 T5 CUDA default를 우회하는 **그 프로세스 안의 비활성 package namespace**를 쓴다. 이것은 full-package import 또는 GPU forward 검증이 아니다. CUDA-hidden full-package import 실패를 별도 보존했다. GPU S에서는 실제 canonical import를 교체하고 strict loader 뒤 actual class file/forward globals/module SHA를 다시 검사한다.

CPU 허용치는 생성 전 `rtol=2e-5, atol=2e-5`, cross-logit 변화 최소`1e-4`로 고정했다. 실제 upstream helper와 complex1288192-frequency table 구성을 이용한다. 고정 synthetic Q/K에 대한 norm·ref-ref logit 성질이지 후속 attention probability 불변 검사가 아니다.

## 실제 worker 순서

환경·모델·upstream을 읽기 전용 재사용하고, 새 root에서만 다음 layout을 만들었다. stage마다 독립 code/config 복사와 reports 디렉터리, 부모 자산·patched source 연결이 생긴다.

```sh
"$ENV_PYTHON" "$B016_ROOT/code/prepare_layout.py" "$B016_ROOT" "$ENV_ROOT"
```

사전 등록 commit `68c5af7ee7eaad07e09769c3547b8ebe0ef7b964`와 코드 manifest SHA`1a6827e21c23197fb1aeb0bfc656c933c184ee97618c73fea890071f54db224e` 확인 뒤 사용한 실행 형태:

```sh
STAGE_ROOT="$B016_ROOT/stages/PROBE"
"$ENV_PYTHON" "$STAGE_ROOT/code/runtime_launch.py" "$STAGE_ROOT" 300 \
 /usr/bin/env PYTHONDONTWRITEBYTECODE=1 CUDA_MODULE_LOADING=LAZY \
 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
 IMAGEIO_FFMPEG_EXE=/usr/bin/ffmpeg \
 "$ENV_PYTHON" "$STAGE_ROOT/code/run_phase.py" "$STAGE_ROOT" PROBE
```

그 후 같은 명령에서 `STAGE_ROOT`와 마지막 stage를 `S`로, 초 상한을`7200`으로 변경해 S1을 실행한다. **PROBE 정상 종료·PID0·자원 회복·새 admission gate가 먼저**다. S는 CFG40steps/80forwards만 허용하며 모든40blocks×80calls의 위치값을 확인한다. 첫/마지막 step의 두 branch만 scalar trace160행으로 저장한다.

D는 `STAGE_ROOT="$B016_ROOT/stages/D"`, 마지막 stage`D`, 초 상한`1800`으로 실행한다. **S 정상 종료·40/80·finite final latent·exact readback·자원 회복이 먼저**다. 별도 VAE worker가 저장된 latent를 decode한다. S를 재실행하지 않는다.

각 launch는 durable outer systemd watchdog과 별도 worker unit을 사용한다. 시작 여유72GiB, 실행 여유24GiB, swap0, 보호 서비스 identity/idle queue, 기존 cgroup 정책을 유지한다. 설정된 초 상한보다 전역 worker cutoff`2026-10-24T03:00:00Z`가 우선한다. 한 stage 실패 시 후속 stage를 실행하지 않고 재시도하지 않는다.

## 관측·검증 파일

`stages/S/reports/loaded_module.json`, `rope_positions.jsonl`, `progress.json`, `loader.json`, 각 stage의`pipeline-process.json`/`resource_metrics.jsonl`/`phases.jsonl`이 실제 근거다. 최종 latent metadata는 실행 코드·부모 condition·RoPE 설정·40block별80call·trace SHA를 연결한다. `RUN_LEDGER`와`MEASUREMENTS`는 terminal receipt에서 집계한다. 이미지 생성 품질은 별도 시각 검토이며 파일 검증으로 자동 승인하지 않는다.
