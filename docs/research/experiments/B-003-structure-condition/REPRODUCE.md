# B-003 재현 범위

실제 개인 사진·source·출력은 공개 저장소에 없다. 입력 파일 해시는 input_audit.json, 실제 decoder RGB 해시는 decoded_input_audit.json에 있다. 허용된 동일 원본 자산과 pinned 로컬 환경이 필요하다. 임의의 다른 개체/사진으로 동일 실험이라고 부르지 않는다.

## 실행 환경과 설정

DiffSynth commit `f39d731a3e318d25b725eb3389cfddb184619842`, Wan-AI/Wan2.1-VACE-1.3B revision `574e6a744642ce3bee319afc31496b88bde8aac4`를 기존 격리 환경에서 사용한다. 새 다운로드/설치는 이번 범위가 아니다. `${BASELINE_ROOT}`,`${B002_ROOT}`,`${RUN_ROOT}`는 공개 설정의 경로 별칭으로 실제 JSON 사용 전 개인 실행 호스트 경로로 치환해야 한다. 코드가 자동 환경변수 확장을 하는 것은 아니다.

`code/`의 runner 파일을 private RUN_ROOT/scripts에, validate_runs.py를 reports에 둔다. C-real은 기존 source Canny17장, C-null은 같은512×288 크기의 RGB0 PNG17장이다. `check_inputs_cpu.py`로 실제 VideoData 결과를 대조한다. source는 저장/비교용 target이고 모델 구조 입력은 condition_video다. 학습 target으로 사용하지 않는다.

private policy.json에는 deadline,attempt_cap4,공유GPUlock,기존큐endpoint를 기록한다. PREREGISTRATION.json에는 실제 고정commit과 pushed 상태를 기록한다. 실험 후 재실행은 기존 장부를 초기화하지 않고 새 승인 범위에서만 한다. 공개 설정의 오래된 deadline을 조용히 늘려 현재 실험을 재개하지 않는다.

```sh
CUDA_MODULE_LOADING=LAZY OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 \
  "$VENV/bin/python" "$RUN_ROOT/scripts/launch_video.py" \
  "$RUN_ROOT/configs/C-real-20261022.json" C-real-20261022
```

같은 명령 구조로 C-null20261022,C-real20261023,C-null20261023 순서다. 모델 실행은 단일프로세스 순차,실패 포함4회 상한이다. 코드가 이 문서 자체로 추가 승인받은 것은 아니다.

## resolved defaults

직접 전달값 외 pinned `WanVideoPipeline.__call__` 기본값은 sigma_shift5,denoising_strength1,vace_scale1,cfg_mergeFalse,tiledTrue(명시),tile_size(30,52),tile_stride(15,26),TeaCache/sliding_window없음,framewise_decodingFalse다. 저장된 config와 고정 함수 signature를 함께 읽어야 하며 모델마다 다른 defaults를 추정하지 않는다. BF16·SDPA·nooffload·adapternull은 runtime 기록으로 확인한다.

## 검증과 한계

실제 sampler 입력의 noise/text/context 및 reference/inactive/reactive/mask slice 해시를 비교한다. CPU synthetic observer 검사는 원본 tensor를 바꾸지 않는지 보는 배선 검사다. 실제 영상 품질이나 모델 전체 재현성을 대신하지 않는다. 동일seed GPU byte동일성은 일반적으로 보장하지 않는다.

출력은17프레임24fps이다. 보간/복제/시간변경 없이 원본과 가로로 붙인 비교를 사용한다. 정적 시트와 실제 연속 재생의 근거를 구분한다. 공개 run_summary는 비민감 요약이며 전체 private config/로그·입출력은 검토 ZIP에 있다.
