# V-004 재현 경로

이 문서는 현재 코드와 준비된 실행 helper의 호출 계약이다. 명령이 있다는 사실을 실행 완료 증거로 쓰지 않는다. 앵커 호출은 `ANCHOR_LEDGER.json`, 생성·측정·전달은 실제 receipt와 결과 기록을 기준으로 갱신한다. 문서 작성 시 여섯 영상의 완료를 확인하지 않았으며 후속 명령은 필요한 입력과 성공 receipt가 생긴 뒤에만 실행한다.

## 경로 역할과 고정 입력

`$V004`는 Spark의 비공개 V-004 실행 루트, `$SCENE`은 그곳의 `V004_SCENE_CONFIG.json`, `$RESEARCH_PYTHON`은 기존 연구 Python, `$SYSTEM_PYTHON`은 기존 시스템 Python이다. `$C001_ADAPTER`는 기존 C-001 `code/run_guarded.py`, `$LOCAL_GUARD_HELPERS`는 Mac의 비공개 준비 helper 폴더다. 개인 경로·사진·영상·모델은 공개 Git에 넣지 않는다.

부모 V-003 commit `8bb131081540e0c10a92d56889af7b63d13e7eff`의 원본 73프레임, source SAM, 수용 앵커 7개, canny와 참조 자산을 hash로 확인해 재사용한다. 장면별 값은 `$SCENE`에서만 읽는다. LTX 공식 코드 commit `e98f6d927d83c92ef2be6aec76c8440b19306e39`, 기존 가중치·정밀도·11 scheduler step·1152×640·24fps·guide 강도·seed는 유지한다. 모델 입력 geometry는 1280×720 → 1152×648 → 위아래 4px crop이다.

## 신규 앵커와 CPU 윤곽

native imagegen에 원본 해당 프레임, Lab 원본 사진, IG 원본 사진, 수용 앵커0을 **실제 이미지 입력**으로 제공한다. 프롬프트와 프레임별 관측 자세는 설정에서 읽는다. 원출력·프롬프트·1280×720 입력 PNG를 보존한 후 기존 준비 helper가 immutable bundle과 SAM stage를 만든다.

```sh
"$SYSTEM_PYTHON" "$LOCAL_GUARD_HELPERS/prepare_anchor.py" \
  "$FRAME" "$ATTEMPT" "$LOCAL_ASSET_FOLDER"
```

준비 폴더에는 `raw.png`, `prompt.txt`, `frames/000.png`가 있어야 한다. helper는 모델을 실행하지 않고 CPU guard·heavy·gate 호출 경로를 출력한다. 신규 16/20/28/32를 순서대로 처리하고 키프레임별 보정은 최대 한 번이다. SAM 완료 후 CPU gate와 G8을 계산한다.

```sh
"$RESEARCH_PYTHON" "$V004/code/anchor_gates.py" "$SCENE" "$GATE_RUNTIME" "$GATE_REPORT"
"$RESEARCH_PYTHON" "$V004/code/anchor_direction.py" "$SCENE" "$DIRECTION_RUNTIME" "$DIRECTION_REPORT"
"$RESEARCH_PYTHON" "$V004/code/scaled_control.py" "$SCENE" "$SCALED_CONTROL_RUNTIME"
```

G6는 하한 0.8만 실패이며 상한은 참고다. G1/G6 최종 실패 앵커만 제외한다. G8은 게이트가 아니다. `scaled_control.py`는 수용 앵커에서 고정 배율, 원/확대 윤곽 시트, `scaled.mkv`, `scaled-repeat.mkv`, 파생 마스크와 `SCALED_CONTROL.json`을 만든다. 출력은 모델 생성물이 아니라 CPU 조건 파생물이다. 생성 전에 앵커·윤곽 시트를 먼저 전달한다.

## guarded 생성

설정·가중치 역할·수용 앵커·조건 hash·메모리 산정 근거를 포함하는 비공개 spec으로 기존 assembler를 호출한다. 이는 stage 준비이며 생성 호출이 아니다.

```sh
"$SYSTEM_PYTHON" "$V004/code/prepare_ltx.py" "$LTX_SPEC" "$RUN_NAME"
"$RESEARCH_PYTHON" "$C001_ADAPTER" "$V004/stages/$STAGE-cpu"
# CPU COMPLETE/returncode0/normal_exit와 freeze를 확인한 뒤 Spark tmux 안에서 실행:
/bin/bash "$V004/code/run_one_heavy.sh" "$STAGE" 1793919360
```

`$STAGE`는 assembler가 출력한 `v004-` 식별자를 그대로 사용한다. helper는 기존 시작 표식 재사용을 거절하고 외부 GPU·배치 부모의 180초 관측, cache helper, 기존 100GiB worker와 NVRM/OOM/PSI/가용 메모리 보호를 유지한다. guard 사본 변경은 V-004 식별자와 중복 실행 표식 인식에 한정한다. 모델 실행은 root 한 흐름이며 SSH 수명에 의존하지 않는다.

순서는 S2-s1 → S1-s1 → S3-s1 → seed1 중간 전달 → S2-s2 → S1-s2 → S3-s2다. S3는 별도 메모리 추정을 확인하고 시작한다. 메모리 중단이면 남은 S3 seed를 생략하며 품질 재시도하지 않는다. 현재 cutoff epoch는 1793919360(2026-11-06 07:56 KST), 종료는 1793921160(08:26 KST)다. 실제 외부 GPU 대기만 승인 범위에서 별도 계산하며 의무 idle 관측 전체를 자동으로 예산 연장에 더하지 않는다.

## 원출력 보존, SAM, POST와 지표

완료 receipt가 있는 원 MP4만 기존 CPU decode helper로 처리한다. S3의 native 145프레임은 보존하고 설정의 배수에 따라 짝수 73프레임 비교본을 만든다. decode PNG는 MP4에서 얻은 RGB이며 인코딩 전 모델 RGB라고 부르지 않는다.

```sh
"$SYSTEM_PYTHON" "$V004/code/decode_output.py" "$V004" "$RUN_NAME" --check-only
"$SYSTEM_PYTHON" "$V004/code/decode_output.py" "$V004" "$RUN_NAME"
"$SYSTEM_PYTHON" "$V004/code/prepare_output_sam.py" "$OUTPUT_SAM_SPEC"
```

output SAM assembler는 생성 supervisor COMPLETE/returncode0/normal_exit, GENERATED receipt와 step 수를 검사한다. 새 CPU stage 후 위 guarded heavy 경로로 비교 73프레임에 SAM을 한 번 실행한다. 직접 unguarded 모델 호출로 바꾸지 않는다. 실제 SAM summary가 완성된 뒤 CPU 파생과 측정을 수행한다.

```sh
"$RESEARCH_PYTHON" "$V004/code/post_composite.py" "$SCENE" "$POST_RUNTIME"
"$RESEARCH_PYTHON" "$V004/code/output_metrics.py" "$SCENE" "$METRICS_RUNTIME"
"$RESEARCH_PYTHON" "$V004/code/scaled_output_metrics.py" "$SCENE" "$SCALED_METRICS_RUNTIME" "$SCALED_METRICS_REPORT"
"$RESEARCH_PYTHON" "$V004/code/collect_run_evidence.py" "$SCENE" "$EVIDENCE_RUNTIME" "$NEW_EVIDENCE_DIR"
```

POST는 원본·출력 개와 반사 마스크 합집합, 개체 높이 15% 팽창, 8px feather를 쓰는 별도 CPU 파생물이다. RAW를 덮어쓰지 않는다. G7 및 출력 embedding은 기존 로컬 모델과 `prepare_embed.py`가 만든 guarded stage로 별도 측정하고 미실행 값을 채우지 않는다. 하드웨어·가드 극값은 표본 관측이며 연속 관측 보증이 아니다.

## 검토물

```sh
"$RESEARCH_PYTHON" "$V004/code/package_review.py" "$PACKAGE_RUNTIME"
```

각 전달은 새 review 폴더와 ZIP 경로를 사용한다. 기본 전달은 Mac Downloads의 압축 해제 폴더와 `index.html`이며 ZIP은 같은 payload의 보조본이다. package helper의 Spark 복사 hash·CRC·실제 추출 검증과 Mac 전달 검증은 별도로 기록한다. 미생성 열은 이유와 함께 NOT_RUN, 사용자 양식은 빈 상태로 둔다. 자동 지표로 우열을 결정하지 않고 HUMAN_REVIEW_PENDING, 연속 지각 검수 전 temporal=UNVERIFIED를 유지한다. 후속 실험을 예약하지 않는다.
