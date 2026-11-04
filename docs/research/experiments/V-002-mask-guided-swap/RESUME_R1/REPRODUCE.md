# V-002 r1 재현 기록

이 문서는 완료된 호출과 준비된 후속 명령을 구분한다. 현재 실행 상태의 기준은 `RUNS.json`과 개별 receipt다. 첫 실행 `9f78153`의 입력·`BLOCKED_EXTERNAL_GPU` 판정은 보존하며, r1 출력과 admission은 별도 디렉터리를 쓴다. 아래 경로 변수는 비공개 인수 manifest에서 해석한다. 개인 경로·미디어·가중치는 공개 Git에 넣지 않는다.

## 경로와 공통 계약

- `$V002`: 기존 V-002 비공개 실행 루트, `$R1`: 그 아래 `RESUME_R1`.
- `$RESEARCH_PYTHON`: 기존 연구 Python, `$SYSTEM_PYTHON`: 기존 시스템 Python.
- `$C001_ADAPTER`: 기존 C-001 `code/run_guarded.py`.
- 설정은 `$R1/configs`, stage freeze는 `$R1/stages`, 결과는 `$R1/outputs`에 둔다. 기존 모델·venv·입력은 복제하거나 재설치하지 않는다.

입력 hash 재사용 검사는 준비 입력 808개, 부모 자산 369개, 역할 파일 6개 모두 일치했다. M1–M3는 832×480, 73프레임, 24fps, seed 20261103, 50 step, CFG 5, shift 16을 쓴다. 수치 설정은 공식 기본값이며 샘플러는 검증된 기존 DiffSynth native Euler다. 공식 VACE UniPC와의 차이를 숨기지 않는다. 원본 RGB가 마스크 밖 **조건**으로 들어가는 것이며 출력 픽셀 동일성을 보장하거나 후합성으로 복원하지 않는다.

## Stage 준비와 실행

초기 baseline 첫 seed는 `v002-r1-sam-baseline-e1-20261103` stage로 완료했다. 계약 연결 수정 후에는 새 `guard-r1-contract`와 `v002-r1c-` stage를 사용한다. 과거 거절 stage를 덮어쓰지 않는다. 비공개 builder의 다음 호출은 baseline 두 번째 seed, M1, M2, M3, LTX canny의 CPU/heavy **10개 stage**를 만드는 준비 명령이며 모델을 실행하지 않는다. 이미 만들어진 stage에는 재호출하지 않는다.

```sh
"$SYSTEM_PYTHON" "$R1/configs/build_stages_r1c.py" 1793841153
```

각 heavy 직전 외부 GPU와 외부 배치 부모가 모두 없는 최소 180초 구간을 확보한다. 표본 간격 60초, 마지막 3표본 연속 비어 있어야 한다. 정상적으로 t0/60/120/180초의 4표본을 남긴다. 단계 120분·누적 180분 대기를 넘기거나 관측 오류가 있으면 해당 기록에 따라 진행을 멈춘다. admission ID는 새 시도마다 고유해야 한다.

```sh
"$SYSTEM_PYTHON" "$R1/code/wait_external.py" \
  --stage "$ADMISSION_ID" \
  --ledger "$R1/reports/wait-ledger.json" \
  --public-log "$R1/reports/WAIT_LOG.json"
"$RESEARCH_PYTHON" "$C001_ADAPTER" "$R1/stages/$STAGE-cpu"
# CPU receipt, admission, freeze, 메모리 추정을 모두 확인한 뒤에만 실행한다.
"$RESEARCH_PYTHON" "$C001_ADAPTER" "$R1/stages/$STAGE-heavy"
```

`STAGE`는 `v002-r1c-sam-baseline-e1-20261104`, `v002-r1c-m1`, `v002-r1c-m2`, `v002-r1c-m3`, `v002-r1c-ltx-canny` 중 해당 단계다. 실제 heavy 실행 직전 가드는 허용된 `sudo -n /usr/local/sbin/drop-caches`를 호출한다. helper 실패 시 SAM·1.3B만 진행할 수 있고 14B·LTX는 생략한다. 모든 heavy worker의 `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True`, `MemoryHigh=MemoryMax=100GiB`를 freeze한다. 다음 단계를 자동 시작하는 루프는 사용하지 않는다.

## 완료된 호출과 후속 준비

기록 작성 시 baseline 두 출력의 SAM 및 CPU 측정은 완료됐고 M1은 976.877초에 73프레임을 생성했다(50 scheduler step, 100 model_fn call). M2는 2026-11-04T19:02Z Spark SSH timeout 및 Tailscale offline 이후 상태가 UNKNOWN이다. 마지막 확인은 21/50 scheduler step, 44 model_fn call이며 완료 receipt가 없다. 당시 마지막 가드는 CLEAR, 관측된 MemAvailable 최저값은 95239196672 bytes, NVRM 이벤트는 없었다. 연결 상실만으로 OOM·재부팅·worker 종료를 추정하지 않는다. M1 출력 SAM의 CPU 검증은 완료됐지만 heavy 측정 완료를 뜻하지 않는다. 이후 M3·14B·LTX 및 새 출력 SAM은 NOT_RUN이다. 후속 상태는 실제 관측이 복구된 뒤 기록한다.

출력 SAM stage는 실제 연속 PNG와 프레임 수를 확인한 뒤 만든다. 아래는 M1 준비 명령이며 생성·SAM 완료 증거가 아니다.

```sh
"$SYSTEM_PYTHON" "$R1/configs/build_output_sam.py" M1 1793841153
```

이후 `v002-r1c-sam-m1-cpu`와 `v002-r1c-sam-m1-heavy`를 위 adapter로 순서대로 실행한다. M2/M3도 각 출력이 실제 존재한 뒤 별도 stage를 만든다. LTX는 원 MP4를 보존하고, SAM용 PNG만 CPU로 decode한다. resize·fps 변환·보간을 하지 않는다.

```sh
mkdir "$R1/outputs/LTX_CANNY/frames"
/usr/bin/ffmpeg -v error -i "$R1/outputs/LTX_CANNY/output.mp4" \
  -vsync 0 -start_number 0 -threads 1 "$R1/outputs/LTX_CANNY/frames/%03d.png"
```

## CPU 측정과 선택

완료된 baseline 측정의 실제 비공개 파일은 `reports/metrics-baseline-e1-20261103.json`, `reports/metrics-baseline-e1-20261104.json`과 대응 `reports/sheet-baseline-e1-*.jpg`다. 공개 요약은 `metrics/baseline-e1-*.json`에 보존한다. 후속 출력은 준비된 다음 경로를 쓴다.

```sh
"$RESEARCH_PYTHON" "$V002/code/metrics.py" \
  "$R1/configs/metrics/$ID.json" "$R1/metrics/$ID.json"
"$RESEARCH_PYTHON" "$V002/code/metrics_sheet.py" \
  "$R1/configs/metrics/$ID.json" "$R1/sheets/$ID.jpg"
"$RESEARCH_PYTHON" "$V002/code/selection.py" \
  "$R1/configs/metrics/selection-all-measured.json" "$R1/metrics/selection.json"
```

`ID`는 실제 SAM이 `SAM_ANALYSIS_COMPLETED`인 M1/M2/M3/LTX_CANNY 등에만 적용한다. all-measured 설정은 세 측정이 모두 있을 때만 쓴다. 기술 실패가 있으면 별도 선택 입력에 해당 변형을 null로 기록한다. 검출 실패는 전체 프레임 IoU와 관측값·누락 범위를 함께 남기되, 미실행 SAM을 가짜 0점 측정으로 바꾸지 않는다. 14B는 선택된 변형의 `V14B-M1.json` 등으로 측정하고, 49프레임인 경우 없는 t54/63/72 출력은 NOT GENERATED다.

## 14B 변환: 준비와 실행을 구분

현재 확인한 것은 원본 header 7 shard/1,331 tensor 및 변환 코드·로더의 정적 계약이다. 실제 변환·모든 tensor bit 비교·14B probe는 아직 실행하지 않았다. 후보 선택 후에만 아래 명령을 사용할 수 있다.

```sh
CUDA_VISIBLE_DEVICES="" "$RESEARCH_PYTHON" "$R1/code/convert_vace_bf16.py" \
  --config "$R1/configs/convert-vace-bf16.json" --cpu-only
# 실제 변환: CPU 순차, 내부 nice +10, 원본 보존, 저장 후 전 tensor bit 검증.
CUDA_VISIBLE_DEVICES="" "$RESEARCH_PYTHON" "$R1/code/convert_vace_bf16.py" \
  --config "$R1/configs/convert-vace-bf16.json"
```

`--cpu-only`는 header/schema 확인이며 torch import·변환을 하지 않는다. 실제 receipt가 `COMPLETE_VERIFIED_CPU_CAST`이고 page cache를 포함한 peak 추정이 100GiB 이하인 경우만 변환본을 모델 config에 연결한다. 14B stage는 후보·변환·추정 확인 전에는 생성하지 않는다. 자세한 적재 추정과 불확실성은 `BF16_PREPARATION.md`를 따른다.

모든 출력은 `HUMAN_REVIEW_PENDING`, 연속 지각 검수는 `temporal=UNVERIFIED`다. 자동 측정·decode·뷰어 동작은 사용자 품질 판정을 대체하지 않는다.

## 2026-11-04T19:02Z 관측 상실

현재 Spark 연결을 제한된 범위에서 재확인 중이다. M1 원 MP4는 Spark에 생성됐지만 Mac으로 복사되지 않았다. 생성 완료와 Mac 전달 완료를 구분하며, 검토 ZIP 전달·호스트 간 무결성·자체 worker 종료는 아직 확인하지 못했다. M2가 계속 실행 중인지도 확인되지 않아 중복 실행하지 않는다. 이 문서는 종료 보고가 아니다.
