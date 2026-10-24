# B-018 재현 계약

실행 전 고정 commit: `2b562188cc0ad30cf822583d53a3d66babbd8e1e`. 모델은 pinned Wan `78fe19576bb06be96c2375e088574a262a300edb` 및 기존 SAT→Wan 변환본이며 새 다운로드는 하지 않았다.

1. 기존 격리 Python과 공식 upstream 경로를 로컬 `configs/runtime-private.json`의 `upstream`·`checkpoint`로 연결한다. 개인 경로를 공개하지 않는다.
2. `configs/selected-tensors.json`의10개 키·shape·source SHA 및 `smoke.json`을 검사한다. 원본65GB 전체 `load_file`을 실행하지 않는다.
3. CPU: `python -m pytest -q code/test_lora_component.py code/test_guard.py`. 공식 source를 읽는 `cpu_rope_contract.py`는 AST helper 검사일 뿐 GPU/FA 검사와 구분한다.
4. GPU worker는 새 실행 승인이 있을 때만 한 번 실행한다. 실제 실행은 `runtime_launch.py`→별도 watchdog→`runtime_guard.py`→`component_runner.py` 순서다. guard의 기존 GPU service 허용 목록은 실제 PID·시작시간·cmdline hash로 고정한다. 타 서비스 식별 실패는 fail-closed다.
5. 원래 실행 명령의 개인 절대경로는 private ZIP의 process receipt에 있다. portable 형태는 아래와 같다.

```sh
"$ENV_PY" code/runtime_launch.py "$RUN_ROOT" 1800 \
  /usr/bin/env PYTHONDONTWRITEBYTECODE=1 CUDA_MODULE_LOADING=LAZY \
  OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  "$ENV_PY" code/component_runner.py "$RUN_ROOT"
```

현재 worker 예약은 exclusive 파일 생성으로 재실행을 막는다. 결과 확인을 위해 파일을 지우고 다시 실행하지 않는다. 이 문서는 추가 GPU 실행 승인이 아니다.

실제 input/target/RNG는 private synthetic fixture에, adapter는 TEST_ONLY safetensors+해시 schema에 저장한다. 전체 source checkpoint 재해시는 이번에 수행하지 않으며, 기존 전체 SHA와 이번 선택 payload hash 및 원본 size/mtime를 구분한다. 실제 FP32 source norm은 반올림 없이 유지하고 projection만 BF16으로 cast한다.

종료 후 `result.json`, `updates.json`, `pipeline-process.json`, memory trace를 함께 확인한다. returncode0이나 CPU PASS만으로 실제 backward·update·reload를 인정하지 않는다.
