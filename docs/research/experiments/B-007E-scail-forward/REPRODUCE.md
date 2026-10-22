# B-007E 재현 절차

이 문서는 실행된 경로를 재현하기 위한 설명이다. **기존 실행을 다시 시작하라는 명령이 아니다.** 실제 결과와 종료 여부는 RESULTS 및 private `reports/`를 확인한다. 원래 실행의 마감은 2026-10-22 18:49 UTC이며, 아래 코드의 마감 상수는 이후 실행에서 그대로 재사용할 수 없다.

## 1. 입력과 실행 권한

다음 변수는 실제 Spark의 확인된 경로로 지정한다. 개인 자료 경로와 GPU PID 목록은 공개 저장소에 기록하지 않는다.

- `B007B_ROOT`: 기존 B-007B private 폴더. `source-original`, `environment`, `models`, `inputs`를 읽기 전용으로 재사용한다.
- `B007D_ROOT`: 검증된 변환 결과가 있는 private 폴더.
- `B007E_ROOT`: 이번 실행의 private 폴더.
- `PUBLIC_EXPERIMENT`: 고정된 공개 B-007E 문서/code/config 폴더.
- `PRIVATE_SNAPSHOT`: 기존에 검토·고정한 `PREREGISTERED_INPUTS.json` 및 private `configs/allowed_gpu_processes.json`이 있는 위치.

원본 source commit은 `78fe19576bb06be96c2375e088574a262a300edb`다. 변환 가중치 `B007D_ROOT/output/conversion/wan-model.safetensors`의 SHA256은 `8b844f026510f0b94d3209d66444b403a089ec179dc149d85513c13b2fa37118`이다. 이전 실행의 `fresh_hashes.json`, dependency/FA binary 기록과 실제 파일을 다시 대조한다. 이 문서의 명령은 다운로드·설치·가중치 재변환을 하지 않는다.

새 실행에는 별도의 명시적 실행 권한, 기존 시도 장부와 연결된 새 실행 기록, 재검토한 마감·자원 정책이 필요하다. 경로를 바꿔 시도 한도를 초기화하지 않는다. 기존 예약 파일을 삭제하거나 이름을 바꾸어 재실행하지 않는다. `runtime_guard.py`의 마감 변경은 새로운 실행 계약과 코드 고정 후에만 한다.

## 2. 준비 순서 — 최초 실행에만

다음은 원래 준비 순서다. 현재 결과가 있는 폴더에 반복 적용하지 않는다. 먼저 `B007E_ROOT/upstream` 및 예약 파일이 없고, 필요한 입력·환경·가중치가 존재하는지 확인한다.

```sh
mkdir -p "$B007E_ROOT/code" "$B007E_ROOT/configs" "$B007E_ROOT/reports" "$B007E_ROOT/outputs"
cp "$PUBLIC_EXPERIMENT"/code/*.py "$B007E_ROOT/code/"
cp "$PUBLIC_EXPERIMENT"/configs/*.json "$B007E_ROOT/configs/"
cp "$PRIVATE_SNAPSHOT/PREREGISTERED_INPUTS.json" "$B007E_ROOT/PREREGISTERED_INPUTS.json"
cp "$PRIVATE_SNAPSHOT/configs/allowed_gpu_processes.json" "$B007E_ROOT/configs/allowed_gpu_processes.json"
/usr/bin/python3 "$B007E_ROOT/code/runtime_prepare.py" "$B007B_ROOT" "$B007D_ROOT" "$B007E_ROOT"
```

`runtime_prepare.py`는 원본 source를 새 `upstream`으로 복사한 뒤, DiT 로더·단계 관측·기존 T5/CLIP의 CPU mmap 로딩 부분만 수정한다. 새 venv의 `.pth`로 기존 B-007B site-packages를 참조하며 기존 환경에 패키지를 설치하지 않는다. 모델 파일과 inputs는 symlink로 연결한다. 원본 `source-original`, 모델, 입력은 수정하지 않는다. `reports/prepare.json`에 패치된 소스 해시를 남긴다.

`configs/input_config_hashes.json`은 두 실행 config와 실제 reference/mask/driver 파일의 고정 해시다. `PREREGISTERED_INPUTS.json`은 `inputs` 아래 case별 파일의 alias·bytes·sha256 목록이다. 실제 추론 진입점이 둘 다 검사한다. 해시 불일치를 통과시키려고 현재 파일에서 새 해시를 계산해 기준을 덮어쓰지 않는다.

GPU allowlist는 PID뿐 아니라 `/proc/<pid>/stat`의 starttime 및 cmdline SHA256을 포함한다. 기존 private 스냅샷의 PID를 새 실행에 그대로 승인해서는 안 된다. 운영자가 실제 프로세스·역할·서비스의 idle 상태를 확인하고 현재 실행 계약에서 허용한 목록만 새로 고정한다. 관측 실패나 새 GPU 작업은 시작 차단 또는 자기 서비스 종료 사유다.

## 3. 작은 CPU 검증과 watchdog 검증

아래 fixture는 작은 랜덤 가중치와 실제 공식 architecture 축소본만 사용한다. 전체 모델 로드나 GPU 추론이 아니다. `--basetemp`와 report 경로는 기존 결과가 없는 위치여야 한다. pytest는 지정한 basetemp를 정리할 수 있으므로 과거 증거 폴더를 지정하지 않는다.

```sh
env CUDA_VISIBLE_DEVICES='' OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH="$B007E_ROOT/code:$B007B_ROOT/source-original" \
  "$B007B_ROOT/environment/bin/python" -m pytest -q \
  "$B007E_ROOT/code/test_staged_loader.py" \
  "$B007E_ROOT/code/test_guard_policy.py" \
  --basetemp="$B007E_ROOT/reports/fixture-fresh"
/usr/bin/python3 "$B007E_ROOT/code/runtime_sentinel.py" "$B007E_ROOT/reports/sentinel.json"
```

Sentinel은 별도의 `make-meme-b007e-sentinel-*` user units에서 sleep 프로세스를 실행해 외부 timeout이 내부 자기 unit까지 종료하는지 검사한다. 가중치를 열거나 GPU 연산을 하지 않는다. unit 이름 충돌과 기존 report 존재 여부를 실행 전에 확인한다. fixture 성공은 실제 모델 적재·forward·영상 성공을 뜻하지 않는다.

## 4. 실제 실행 — 공식 예제 후 Lab, pipeline 한 번 적재

실행 직전 MemAvailable ≥72 GiB, swap 사용 0, 기존 서비스 queue idle, GPU PID/시작시각/명령 해시, 디스크 여유, 실제 환경과 입력·가중치·코드 해시를 확인해 `prelaunch` 증거로 보존한다. 원래 실행은 다음 명령 형태였다. **현재 실행 또는 종료된 시도에 다시 실행하지 않는다.**

```sh
/usr/bin/python3 "$B007E_ROOT/code/runtime_launch.py" "$B007E_ROOT" 14400 \
  /usr/bin/env CUDA_MODULE_LOADING=LAZY OMP_NUM_THREADS=1 \
  OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 \
  IMAGEIO_FFMPEG_EXE=/usr/bin/ffmpeg HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
  "$B007E_ROOT/environment/bin/python" "$B007E_ROOT/code/runtime_infer.py" \
  "$B007E_ROOT" "$B007E_ROOT/configs/official.json" "$B007E_ROOT/configs/lab.json"
```

`runtime_launch.py`가 durable outer watchdog을 만들고 그 안에서 `runtime_guard.py`가 pipeline unit을 감독한다. 요청 시간은 고정 마감의 남은 시간에 의해 더 줄어든다. pipeline cap은 `min(64 GiB, 시작 시 available−24 GiB)`, MemoryHigh는 cap−2 GiB, MemorySwapMax는 0이다. 실행 중 available <24 GiB, swap 증가, 다른 작업 시작, 마감 도달 또는 관측 오류 시 **이번 pipeline unit만** 종료한다. 다른 서비스를 종료하지 않는다. 이는 정책이며 모든 메모리 위험을 없앤다는 보장이 아니다.

`runtime_infer.py`는 전체 pipeline을 한 번 만들고 공식 예제→Lab 순서로 사용한다. 공식 예제 실패가 예외를 발생시키면 Lab로 자동 진행하지 않는다. 공식 예제 17 frames/16 fps/H512×W896, Lab 17 frames/24 fps/H896×W512다. 두 case 모두 seed 20261022, UniPC 40 steps, shift 3, CFG 5, overlap 5, LoRA 없음이다. 원본 RGB driving을 사용하며 보간·프레임 복제·프롬프트 확장은 하지 않는다.

## 5. 예약·기록·실패 보존

다음 파일은 exclusive 생성된다. 존재하면 덮어쓰지 않고 중단하는 것이 정상이다.

- `reports/watchdog-launch.json`: 감독 명령 예약.
- `reports/pipeline-process.json`: 자기 pipeline 서비스 예약 및 최종 상태.
- `reports/model-load-attempt.json`: 실제 mixed-BF16 모델 로드 예약.
- `reports/official-sampler-attempt.json`, `lab-sampler-attempt.json`: 해당 sampler 호출 직전의 case별 1회 예약.
- `reports/loader.json`: 실제 strict/assign 결과 및 dtype/shape/byte 관측.
- `outputs/official`, `outputs/lab`: case별 새 출력 폴더.

실패·중단·결과 불명도 그대로 보존한다. 모델 로드 예약과 sampler 예약은 서로 다른 단계를 의미하며, 모델 로드 실패를 완료된 영상 생성으로 세지 않는다. 이번 경로는 단일 mixed-BF16 loader이고 자동 fallback/재호출이 없다.

`reports/model_phases.jsonl`, `resource_metrics.jsonl`, `pipeline.log`, `pipeline-process.json`, 각 output의 run 기록과 raw tensor/MP4를 함께 확인한다. `systemctl --user show make-meme-b007e-pipeline -p MainPID -p Result -p ActiveState`로 실행 상태를 읽을 수 있다. MP4의 존재·재생 가능성, 첫 finite forward, 실제 Lab 개체·동작 품질, 연속 재생 관찰은 서로 별도 판정이다. B-007A에서 남은 마스크 경계 문제는 PARTIAL_UNRESOLVED로 유지한다.
