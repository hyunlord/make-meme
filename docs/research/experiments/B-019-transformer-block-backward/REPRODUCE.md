# B-019 재현과 실행 경계

사전 고정 commit: `26c085635c41f77d26bd9f75a5c0976389b7ee3a`. 실제 실행 파일은 `CODE_FREEZE.json`, 작은 입력 파일과 payload는 `configs/fixtures.json`, 선택32키는 `configs/selected-tensors.json`으로 확인한다. 개인 경로는 공개하지 않으며 private ZIP의 runtime 설정을 사용한다.

## CPU

```sh
python -m pytest -q code/test_block_contract.py code/test_lora_component.py code/test_guard.py
python code/cpu_rope_contract.py "$UPSTREAM/wan/modules/model_scail2.py" "$RUN_ROOT/reports/cpu-rope-review.json"
```

실제 CPU 결과와 명령은 검토 ZIP의 logs/receipt를 우선한다. CPU fixture는 실제14B/FA 수치 검증을 대신하지 않는다.

## GPU 실행 계약

기존 격리 Python과 upstream·checkpoint를 로컬 `runtime-private.json`에 연결하고 실제 기존 서비스 PID·시작시간·cmdline hash를 고정한다. 경로와 비밀은 공개하지 않는다. 기존 결과를 지우거나 예약 파일을 초기화하지 않는다. 이번 사용량은 아래 명령의 worker 한 번이며 문서 재현 명령 자체는 추가 실행 승인이 아니다.

```sh
"$ENV_PY" code/runtime_launch.py "$RUN_ROOT" 1800 \
 /usr/bin/env PYTHONDONTWRITEBYTECODE=1 CUDA_MODULE_LOADING=LAZY \
 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
 "$ENV_PY" code/block_runner.py "$RUN_ROOT"
```

`runtime_launch`는 독립 watchdog을, `runtime_guard`는 이번 worker 전용 systemd unit을 사용한다. cap16GiB/high14GiB·swap0·72GiB 시작·24GiB 실행 headroom과 deadline을 유지한다. 다른 서비스는 관측만 한다.

`block_runner`는 CPU `safe_open`으로 `blocks.39.`32개만 읽는다. `load_file` 사용은 작은 fixture/adapter에 한정한다. 전체 checkpoint SHA는 기존 변환 기록을 인용하며 이번 전체65GB 재해시를 수행했다고 주장하지 않는다. 선택 tensor payload hash·source F32 norm 보존·원본 size/mtime를 실제 검사한다.

소형 fixture는 B-018의 실제 x/target과 **초기** adapter를 재사용한다. 새 context/e 파일은 seed20261025, 긴 x/target은 seed20261026이다. 긴 tensor는 저장·ZIP하지 않으며 recipe/hash만 남긴다. adapter는 TEST_ONLY로 실제 영상 추론에 연결하지 않는다.

소형 8forward/3backward/3update, 조건부 긴1forward/1backward/update0. 모든 실제 계산은 같은 worker에서 수행한다. `small-result.json`은 긴 단계 전에 원자적으로 저장되므로 긴 실패가 소형 성공 기록을 없애지 않는다. `result.json`과 stage별 결과, guard reason, counter, output hash를 함께 확인한다. returncode0만으로 수용하지 않는다.

## 재로딩 검증 범위

기반 parameter를 동결한 fresh block에 adapter만 다시 로딩하고 동일 입력 출력을 비교한다. 이후 adapter OFF의 기준선 복귀를 별도로 확인한다. 같은 worker 내 새 component 객체이며 fresh OS 프로세스 재로딩이나 전체모델 학습 검증이라고 부르지 않는다.
