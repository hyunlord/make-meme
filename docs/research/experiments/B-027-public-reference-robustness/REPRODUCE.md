# B-027 재현과 보존 경계

사전 고정 commit: `9a93aa09ed2032aebea3905e5b698388b65243c4`.
입력 선택은 [selection.json](selection.json), 원본 다운로드는 [DOWNLOAD.json](DOWNLOAD.json), 처리·실행 파일 해시는 [INPUT_MANIFEST.json](INPUT_MANIFEST.json)에 있다. 기존 모델·환경은 각 비공개 task의 `PREREGISTERED_INPUTS.json`과 `PREREGISTERED_CODE.json`으로 고정했다. 공개 저장소에는 데이터·모델을 넣지 않는다.

## CPU 확인

기존 Python 환경에서 설치 없이:

```sh
python3 -m pytest docs/research/experiments/B-027-public-reference-robustness/data_code/test_data_prepare.py docs/research/experiments/B-027-public-reference-robustness/code/test_contract.py docs/research/experiments/B-027-public-reference-robustness/media_code/test_build_review.py
```

새 공개 입력은 `data_code/data_prepare.py`가 DAVIS 원본과 instance label을 같은 aspect-fit 좌표로 옮긴다. 실제 clip은 lossless RGB로 저장하고 다시 decode하여 PNG 값과 비교한다. source의 비대상 객체는 driving mask의 WHITE 문맥으로 남는다. 참조는 선택 track RED support 안의 resize된 RGB를 유지하며 밖을128로 바꾼다. GT 마스크 제공 조건이다.

## 실제 worker 순서

`code/prepare_layout.py TASK_ROOT EXISTING_B025_MODEL_LINEAGE CODE_ROOT`는 기존 모델·고정 upstream만 연결한다. B025 개인 입력이나 조건 cache를 가져오지 않는다. `code/freeze_run.py TASK_ROOT`가 실제 입력·실행 코드·stage config를 저장한다. 둘 다 sampler가 아니다.

각 task는 다음 순서의 fresh worker로 실행한다.

```text
ENC → R1_PROBE → R1_S → R1_D → R2_PROBE → R2_S → R2_D
```

각 launch의 형태는 아래와 같다. 경로는 모두 실제 절대 경로를 전달해야 한다. `STAGE`는 예를 들어 `R1_PROBE`이며 단순 `PROBE`가 아니다.

```sh
"$PINNED_PYTHON" "$CODE_ROOT/runtime_launch.py" "$STAGE_ROOT" "$SECONDS_CAP" \
  "$PINNED_PYTHON" "$CODE_ROOT/run_phase.py" "$STAGE_ROOT" "$STAGE"
```

실제 argv·unit·PID·guard reason은 비공개 `stages/*/reports/watchdog-launch.json`과 `pipeline-process.json`에 있다. ENC900초, PROBE180초, S3600초, D900초 상한과 전체 deadline 중 먼저 도달하는 제한을 적용한다. 72GiB 시작 조건, 24GiB headroom, swap0, 보호 프로세스 확인을 유지한다. 코드의 고정 deadline과 exclusive attempt 파일은 과거 실행의 무단 반복을 막는다. **이 명령 설명은 새 GPU 실행 승인이나 자동 재시작 지시가 아니다.**

ENC는 공식 generate의 sampler 진입 직전에 실제 공통 조건·noise·RNG·scheduler를 포착하며 DiT는 올리지 않는다. R2는 같은 cache 구조에서 reference VAE/CLIP/mask만 계산한다. `pair_contract.py`가 허용6leaf 외10leaf와 device 구조의 불변성을 확인한다. R2 metadata의 `preprocessed_inputs`는 R1 포착 기록이며 R2 재측정으로 해석하지 않는다. R2의 실제 파일 hash·config·조건 tensor가 별도 근거다.

S는 tiny CUDA 연산 뒤 기존 staged loader를 사용한다. 첫 실제 CFG에서 cache 객체 전달을 검사하되 추가 forward는 없다. 40step·80forward와 유한 final latent를 검증하고 원자적으로 저장한다. S 종료와 자원 회복 후 D가 VAE만 올려17장을 복원한다. decode 실패로 S를 다시 실행하지 않는다.

## 검토물

실제 두 출력이 준비된 뒤:

```sh
python3 docs/research/experiments/B-027-public-reference-robustness/media_code/build_review.py --private-root "$PRIVATE_ROOT"
python3 docs/research/experiments/B-027-public-reference-robustness/media_code/check_viewer.py "$PRIVATE_ROOT/review"
```

이 경로는 raw tensor를 보존하고 기존 저장 규약의 clamp/정규화·uint8 표시와 비교용 인코딩만 수행한다. 자세·얼굴·시간 보정은 없다. source_fps는 미확인(null)이며 모든 preview는24fps,17프레임이다. 브라우저 controls·ffmpeg decode 통과는 사람의 시간 품질 수용이 아니다.
