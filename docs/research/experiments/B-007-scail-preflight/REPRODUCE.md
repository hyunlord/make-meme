# B-007A 재현과 실행 범위

실제 자료는 비공개 review ZIP에 있다. 공개 저장소에는 개인 입력과 절대 경로를 넣지 않는다. `${RUN_ROOT}`, `${B002_ROOT}`, `${B006_ROOT}`, `${BASE_PYTHON}`, `${CUDA_HOME}`, `${NINJA_BIN_DIR}`, `${PINNED_SCAIL_ROOT}`는 로컬 mapping으로 제공한다. 모델 가중치 다운로드·diffusion·학습 명령은 이 실험에 없다.

## 입력 CPU 검사

```sh
python code/input_preflight.py "$B002_ROOT" "$B006_ROOT" "$RUN_ROOT"
python code/input_preflight_local_trim.py "$RUN_ROOT"
python code/input_preflight_verify.py "$RUN_ROOT"
python code/test_fps_override.py
python code/input_mask_tensor.py "$PINNED_SCAIL_ROOT" "$RUN_ROOT"
```

첫 명령은 기존 source/photo 해시를 확인한다. 두 번째는 private `annotations/input-mask-trim.json`의 수동 검토 좌표가 필요하다. 새 자료에 좌표를 그대로 적용하지 않는다. v1과 v2를 모두 보존한다.

## 소형 attention 검사

사전 고정 `kernel_methods.json`에 두 source pin과 byte 상한이 있다. `kernel_download.py`는 정확한 filename/url/bytes/sha256 JSON과 누적 장부를 사용한다. `kernel_guard.py`는 이 실행의 절대 deadline을 고정하므로 과거 실행 종료 뒤 무심코 재실행할 수 없다. 다음 재현은 별도 승인된 deadline/ledger를 명시해야 하며 원본 기록을 덮어쓰지 않는다.

방법1은 `kernel_build.py`의 격리 prefix와 기존 torch 읽기 참조를 사용했다. 방법2는 `kernel_method2.py`의 고정 공식 source와 CUTLASS archive를 사용한다. `kernel_method2_resume.py`는 기존 Ninja 경로 탐지 실패만 수정하며 원래 `KERNEL_METHOD_DEADLINE`을 유지한다. 새 source/backend/세 번째 방법이 아니다. 원래 guard 종료 후 사전 등록한 단 한 번의 같은 object-cache continuation은 최종 07:15:33 UTC deadline을 사용했고 성공 종료했다. RUNNING과 각 process ledger에 원래 timeout 및 모든 sub-invocation을 보존했다.

```sh
"$RUN_ROOT/environment/bin/python" code/kernel_smoke.py \
  "$RUN_ROOT/kernel/scail_attention.py" "$RUN_ROOT/reports/kernel_smoke.json"
```

실제 실행은 반드시 `kernel_guard.py`로 감싼다. 작은 random BF16 QKV만 사용하며 SCAIL package/model을 import하지 않는다. 고정 wrapper 파일을 직접 로드하고 그 내부 FA 선택과 varlen 호출을 사용한다. SDPA MATH FP32는 오차 비교용일 뿐 SCAIL backend 대체가 아니다.

빌드/실행 명령과 PID·exit·elapsed·메모리 장부 원본은 private reports에 있다. 모델 로딩·실제 긴 sequence·VAE·mask conditioning 전체 forward는 NOT_RUN이다.

## ZIP 검증

`package_review.py RUN_ROOT /tmp/review.zip`은 가상환경·다운로드·소스 빌드·weights를 제외하고 파일별 SHA256을 만들며 ZIP을 다시 열어 CRC와 모든 포함 파일 hash를 확인한다. 원본 private 입력이 포함되므로 GitHub에 ZIP을 올리지 않는다.
