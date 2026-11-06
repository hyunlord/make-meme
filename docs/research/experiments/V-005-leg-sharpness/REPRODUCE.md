# V-005 재현 경로

개인 원본·참조·앵커·마스크·영상 및 runtime 절대경로는 Git에 포함하지 않는다. 아래 변수는 비공개 manifest에서 확인한 역할을 가리킨다. 기존 가중치·venv를 재사용하며 공식 LTX checkout은 `e98f6d927d83c92ef2be6aec76c8440b19306e39`이다. 장면 값은 [V005_SCENE_CONFIG.json](V005_SCENE_CONFIG.json)에서 읽고 V-004 확대 canny의 실제 파일 hash와 고정 배율을 그대로 유지한다.

작성 시 확인 상태: R1-a/b 생성 완료, 실제 양 단계 σ=0.421875·1+1step이며 두 RAW hash가 같다. R2는 [지원 확인](R2_SUPPORT.md)에 따라 NOT_SUPPORTED/생성 0회다. R3-s1은 73프레임 생성 완료(136.592초, 11step/11call, supervisor COMPLETE·반환값 0·정상 종료)이며 출력 SAM·측정은 대기 중이다. R3-s2는 중간 전달 전 NOT_RUN이다. 아래 준비·실행 명령의 존재를 완료 증거로 취급하지 않고 최종 실제 상태는 RUNS와 supervisor receipt로 확인한다.

## 실행 역할과 사전 검증

`RUN_ROOT`는 Spark V-005 비공개 실행 루트, `RESEARCH_PY`는 기존 연구 Python, `ENGINE_PY`는 기존 E1 Python, `ADAPTER`는 기존 보호 runner, `CUTOFF_EPOCH`는 사전 고정한 신규 heavy 시작 종료 시각이다. `SCENE`은 수치 정책과 부모 gate를 명시적으로 해석해 동결한 유효 장면 설정이다. 공개 설정과 해석본의 hash·계보는 runtime manifest에 기록한다.

R1 runtime은 부모 entry/hash, 모델·Gemma·업샘플러·Union LoRA, S2-s1 RAW/hash, 기존 앵커 11장, canny/hash, seed·출력·observer 경로를 포함한다. `refine_entry.py --cpu-only`는 input ffprobe와 frozen hash·앵커 위치·schedule을 검사하며 torch를 import하지 않는다.

```bash
"$ENGINE_PY" "$RUN_ROOT/code/refine_entry.py" --config "$RUNTIME" --cpu-only
```

실제 보호 worker는 `runpy.run_path`로 entry를 실행하므로 sibling import 검색 경로 보정이 반영된 entry를 사용한다. 최초 import 실패 stage는 보존하고 수정본은 별도 `importfix` stage에 동결했다. raw 실행으로 가드를 생략하지 않는다.

모든 heavy 단계는 CPU gate 완료 후 root의 단일 실행 흐름에서 Spark tmux로 시작한다.

```bash
"$RESEARCH_PY" "$ADAPTER" "$RUN_ROOT/stages/$STAGE-cpu"
# CPU supervisor COMPLETE 확인 후에만:
tmux new-session -d -s "$STAGE" \
  "bash $RUN_ROOT/code/run_one_heavy.sh $STAGE $CUTOFF_EPOCH"
```

wrapper는 외부 GPU·배치 부모의 충분한 무작업 관측 후 실행한다. drop-caches, expandable_segments, NVRM·OOM·MemAvailable·PSI 감시, MemoryHigh=MemoryMax=100GiB를 유지한다. 기존 batch-start 기록이 있으면 재실행하지 않는다. 연결 상실을 완료로 추정하지 않으며 `supervisor-result.json`의 COMPLETE·worker_returncode=0·normal_exit_recorded=true와 생성 receipt를 함께 확인한다.

## 생성 후 처리

실제 완료 출력에 대해서만 다음 CPU decode를 적용한다. 원 MP4를 보존하고 decoded PNG임을 명시한다.

```bash
/usr/bin/python3 "$RUN_ROOT/code/decode_output.py" "$RUN_ROOT" "$RUN_NAME" --check-only
/usr/bin/python3 "$RUN_ROOT/code/decode_output.py" "$RUN_ROOT" "$RUN_NAME"
/usr/bin/python3 "$RUN_ROOT/code/prepare_output_sam.py" "$SAM_PREPARATION"
```

SAM도 위와 같은 CPU/heavy 보호 절차를 각각 거친다. generation contract는 실제 성공 stage를 가리켜야 하며 실패한 이전 stage를 덮어쓰지 않는다. 73 PNG 및 SAM summary와 완료 receipt가 확인된 뒤:

```bash
CUDA_VISIBLE_DEVICES='' "$RESEARCH_PY" "$RUN_ROOT/code/process_output.py" "$PROCESS_RUNTIME" --check-only
CUDA_VISIBLE_DEVICES='' "$RESEARCH_PY" "$RUN_ROOT/code/process_output.py" "$PROCESS_RUNTIME"
```

[process_output.py](code/process_output.py)는 POST, R1 국소 합성, base/scaled/leg 지표와 처리 receipt를 만든다. 기존 출력은 덮어쓰지 않고 RAW hash 보존과 국소 합성 alpha=0 위치의 원본 byte 일치를 확인한다. R1-b 국소 합성의 별도 확인 SAM은 `prepare_local_sam.py`로 stage를 준비한 뒤 같은 보호 절차로 실행한다. RAW SAM을 국소 합성의 관측으로 대체하지 않는다.

기준 S2-s1·S2-s2·V-003 K1-s1은 기존 SAM을 재사용한다. Kling은 별도 확인 SAM 뒤 [leg_casting.py](code/leg_casting.py), [leg_metrics.py](code/leg_metrics.py)를 적용한다. 지정 luma·기하·영역 정책을 모든 기준과 출력에 동일하게 적용하고 누락은 null 및 coverage로 보존한다.

```bash
CUDA_VISIBLE_DEVICES='' "$RESEARCH_PY" "$RUN_ROOT/code/leg_casting.py" "$SCENE" "$CASTING_RUNTIME" "$CASTING_REPORT"
CUDA_VISIBLE_DEVICES='' "$RESEARCH_PY" "$RUN_ROOT/code/leg_metrics.py" "$MEASUREMENT_SCENE" "$LEG_RUNTIME" "$LEG_REPORT"
CUDA_VISIBLE_DEVICES='' "$RESEARCH_PY" "$RUN_ROOT/code/aggregate_metrics.py" "$SCENE" "$AGGREGATE_RUNTIME" "$METRICS_REPORT"
```

## R3 앵커와 생성

신규 위치·수용 규칙은 장면 설정에서 읽는다. native imagegen 원본·prompt를 보존하고 `prepare_anchor.py`가 출력하는 실제 CPU gate/launch/gate 명령을 순서대로 수행한다. imagegen 보정은 설정의 횟수와 gate 규칙 안에서만 허용한다. `aggregate_anchors.py`는 기존 11개 gate 행을 보존하고 실제 수용 신규 행을 추가해 accepted snapshot을 만든다. 배율을 재산정하거나 scaled canny를 다시 만들지 않는다. G8은 CPU 참고값, G7은 기존 SigLIP의 별도 보호 실행으로 측정한다.

```bash
/usr/bin/python3 "$RUN_ROOT/code/aggregate_anchors.py" "$ANCHOR_REQUEST" "$ACCEPTED_SNAPSHOT"
/usr/bin/python3 "$RUN_ROOT/code/prepare_ltx.py" "$R3_ASSEMBLY_REQUEST" "$RUN_NAME"
```

이후 실제 준비된 CPU/heavy stage를 위 단일 흐름으로 실행한다. 신규 앵커가 제외되면 수용된 개수와 위치를 기록하며 무조건 15개라고 기입하지 않는다. R3 실행 후 decode·SAM·POST·측정도 같은 절차를 적용한다.

## 데이터 기록과 전달

[build_sample.py](code/build_sample.py)는 비공개 manifest의 실제 경로를 읽고 hash를 검증해 출력별 SAMPLE.json을 생성한다. V-003·V-004는 같은 schema로 소급 기록하되 미디어를 복사하지 않는다. 사람 판정은 PENDING으로 시작한다. [dataset/SCHEMA.md](dataset/SCHEMA.md)를 따른다.

```bash
"$RESEARCH_PY" "$RUN_ROOT/code/build_sample.py" "$SAMPLE_MANIFEST" "$PRIVATE_DATASET_ROOT"
"$RESEARCH_PY" "$RUN_ROOT/code/package_review.py" "$PACKAGE_RUNTIME"
```

검토물은 Spark에서 먼저 완성한 뒤 Mac Downloads의 비압축 폴더로 전달한다. 중간 전달과 최종 전달을 구분하고, manifest는 자신과 ZIP을 payload에서 제외한다. 실제 추출·CRC·payload hash·호스트 간 동일성을 검증한다. 뷰어 제어 검증과 연속 지각 품질 검수는 별개이며 HUMAN_REVIEW_PENDING/temporal=UNVERIFIED를 유지한다. R2 미실행 열은 이유와 함께 표시하고 후속 실험은 예약하지 않는다.
