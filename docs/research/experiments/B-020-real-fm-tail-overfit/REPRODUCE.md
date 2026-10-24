# B-020 재현 계약과 실행 기록

사전 등록 commit: `e8d32f7baed33fe8057ac79e1faa724e93a3577f`. 실제 비공개 입력과 기존 모델 환경은 검토 ZIP의 private manifest 경로로 연결한다. 공개 저장소만으로 개인 영상·가중치를 복구할 수는 없다.

## 고정 환경과 입력

- Wan upstream `78fe19576bb06be96c2375e088574a262a300edb`; SAT loss 판독 `ac63f8eb369e2f4fac2ce273ead0ae7e602c3919`.
- 변환 base SHA256 `8b844f026510f0b94d3209d66444b403a089ec179dc149d85513c13b2fa37118`.
- 실제 실행 코드와 upstream 파일별 SHA는 [PREREGISTERED_CODE.json](PREREGISTERED_CODE.json), 입력/config 해시는 [input_config_hashes.json](configs/input_config_hashes.json)에 있다.
- 기존 격리 Python·Torch·FA2·mixed loader를 재사용한다. 패키지나 모델 설치 명령은 이번 실행에 없다.
- source f126~142,30fps,896×512. reference/driver mask와 RGB 전처리 계보는 비공개 입력 manifest에 보존한다. 공개 사진/좌표/마스크는 없다.

## 실행 표면

아래는 이번 실행의 표면을 설명한 명령이다. `RUN_ROOT`, `BASELINE_ROOT`, `PYTHON`은 비공개 manifest의 실제 값을 사용했다. 기존 시도를 덮어쓰거나 재실행하는 명령이 아니다. guard에는 해당 실행의 절대 deadline과 시도 배제가 있으므로, 종료 후 재현은 별도 승인·사전 등록이 필요하다.

```sh
"$PYTHON" "$RUN_ROOT/code/prepare_layout.py" "$RUN_ROOT" "$BASELINE_ROOT"
"$PYTHON" "$RUN_ROOT/code/runtime_launch.py" "$RUN_ROOT/stages/P" 1800 "$PYTHON" "$RUN_ROOT/code/run_phase.py" "$RUN_ROOT/stages/P" P
```

P → PREFIX → BASE_S → BASE_D → TRAIN → TRAIN_S → TRAIN_D를 순서대로 실행한다. 각 fresh worker는 이전 worker의 정상 종료·자원 회복·실제 완료 receipt를 요구한다. 해당 단계의 명령/시간/시도/종료 사유는 private `stages/*/reports/pipeline-process.json`에 기록한다. 전체 GPU 실행을 병렬로 하지 않는다.

P는 실제 target와 조건을 저장한다. PREFIX는 고정4tuple 각각 한 번의 positive 전체 forward에서 마지막 block 입력과 기준 velocity를 함께 저장한다. BASE_S/TRAIN_S는 같은 조건·noise·RNG·scheduler를 재사용하며40step/80forward를 검사한다. D는 해당 final latent만 decode한다. TRAIN은 prefix/target/noise의 해시 연결과4개 split parity를 먼저 검사하고 최대20update 후 저장/reload/OFF를 검사한다.

## 검사와 재사용 한계

CPU 계약은 `python -m pytest code/test_fm_contract.py -q`로 실행했다. helper10검사 통과는 실제 GPU parity나 학습 성공을 대신하지 않는다. 전체 runtime typing은 NOT_CLEAN이며 raw 진단은 private ZIP에 보존한다.

prefix cache는 sigma/noise/조건/geometry/model/code가 모두 같은 tuple에서만 유효하다. 새 noise로 생성하면서 이전 h38을 사용할 수 없다. 4tuple 중 평가1개도 같은 clip이며 독립 영상 validation이 아니다.

최종 기록에는 실제 완료 단계, loss·parity·adapter/base·샘플링 결과와 자원 측정값을 별도로 남긴다. 개인 미디어·cache·latent·adapter는 공개하지 않는다.
