# 복구 r2 실제 실행 경로

M1의 출력 SAM·CPU 측정, Spark 검토물 포장 및 Mac 전달 무결성 확인은 완료했다. M2·M3의 `r2e` CPU stage는 COMPLETE이며 Spark 내부 tmux에서 나머지 생성과 후처리를 진행한다. **이 기록은 M2·M3 생성·측정 완료를 주장하지 않는다.** 최신 완료 증거는 각 supervisor와 batch receipt를 함께 확인한다.

`$V002`는 비공개 V-002 실행 루트, `$R1=$V002/RESUME_R1`, `$RESEARCH_PYTHON`은 기존 연구 Python, `$C001_ADAPTER`는 기존 C-001 `code/run_guarded.py`다. 실제 절대경로·실행 식별자는 비공개 설정에만 보존한다. 아래 명령은 이미 시작한 실행의 재현 기록이며 중복 호출 지시가 아니다.

## 기존 결과와 가드 보존

이전 M2의 STARTED receipt, 22 scheduler step / 45 model_fn call 기록과 미완성 출력 경로는 그대로 보존했다. 승인된 한 번의 재시작은 별도 `outputs/M2-recovery-r2`를 쓴다. M3는 `outputs/M3-r2`를 쓴다. 재부팅 사실은 확인했지만 공개 incident 원인은 **UNKNOWN**이다.

정상 종료 직후 RSS 전용 관측을 새로 수행하는 경로의 문제는 별도 가드 사본에서 수정했고 CPU 검사 45개를 통과했다. 과거 실패 기록은 보존하며 그 정확한 원인이 모두 확정됐다고 표현하지 않는다. 이 수정으로 OOM·NVRM·MemAvailable·PSI 보호나 100GiB 한도를 바꾸지 않는다. 새 stage는 새 부팅과 해당 가드 사본으로 freeze한다.

## 생성: Spark 내부 tmux

root 실행 담당이 먼저 다음 두 CPU stage의 COMPLETE receipt를 확인했다.

```sh
"$RESEARCH_PYTHON" "$C001_ADAPTER" "$R1/stages/v002-r2e-m2-cpu"
"$RESEARCH_PYTHON" "$C001_ADAPTER" "$R1/stages/v002-r2e-m3-cpu"
```

Spark 내부 tmux 세션 `v002-r2-remaining`에서 실제 실행하는 명령은 다음 순서다. M2가 성공한 경우만 M3로 넘어간다. SSH 연결과 작업 수명을 분리하되 무한 반복·재시도는 하지 않는다.

```sh
/bin/bash "$R1/configs/recovery-r2/run_one_heavy_r2e.sh" v002-r2e-m2 && \
/bin/bash "$R1/configs/recovery-r2/run_one_heavy_r2e.sh" v002-r2e-m3
```

단계별 스크립트는 기존 시작 표식이 있으면 거절하고, 고유 admission으로 `wait_external.py`를 실행한 뒤 기존 guarded adapter의 `-heavy`를 호출한다. 외부 작업 대기와 시작 전·대기 후 cutoff를 모두 검사한다. 각 단계의 `reports/<stage>-batch-exit.json`과 `stages/<stage>-heavy/reports/supervisor-result.json`을 보존한다.

## 후처리: 생성 receipt 이후에만

별도 tmux 세션 `v002-r2-postprocess`에서 아래 스크립트를 명시적으로 한 번 시작했다.

```sh
/bin/bash "$R1/configs/recovery-r2/postprocess_r2.sh"
```

이 스크립트는 M2와 M3 **모두** supervisor `COMPLETE`, worker return code 0, batch exit code 0이 될 때까지 receipt만 확인한다. 실패가 확인되면 중단하며 생성 성공을 가정하지 않는다. 두 생성과 SAM 모델 적재를 병렬로 하지 않는다.

완료 조건이 충족되면 M2, M3 순으로 다음을 수행한다. 새 SAM stage는 실제 출력 73프레임, 현재 부팅·가드를 확인하고 기존 출력과 stage 덮어쓰기를 거절한다.

```sh
"$SYSTEM_PYTHON" "$R1/configs/recovery-r2/build_output_sam_r2e.py" M2 1793841955
"$RESEARCH_PYTHON" "$C001_ADAPTER" "$R1/stages/v002-r2e-sam-m2-cpu"
/bin/bash "$R1/configs/recovery-r2/run_one_sam_r2e.sh" v002-r2e-sam-m2
# M3도 같은 순서로 M3 / v002-r2e-sam-m3에 적용한다.
```

SAM runner도 외부 GPU 대기·cutoff·기존 가드를 적용한다. summary가 `SAM_ANALYSIS_COMPLETED`이고 73프레임임을 확인한 후에만 CPU 측정과 시트를 만든다. M2의 실제 명령은 다음과 같고, M3에서는 key를 `M3-r2`로 바꾼다.

```sh
"$RESEARCH_PYTHON" "$V002/code/metrics.py" \
  "$R1/configs/recovery-r2/metrics-M2-recovery-r2.json" \
  "$R1/reports/metrics-M2-recovery-r2.json"
"$RESEARCH_PYTHON" "$V002/code/metrics_sheet.py" \
  "$R1/configs/recovery-r2/metrics-M2-recovery-r2.json" \
  "$R1/reports/sheet-M2-recovery-r2.jpg"
```

생성·SAM·후처리 시작 표식과 종료 receipt는 별도 보존한다. 후처리 스크립트 자체는 ZIP 포장·자동 selector·14B·LTX를 시작하지 않는다. 이 복구에서 14B/LTX는 명시적으로 NOT_RUN이며 다음 선택은 결과 전달 후 사용자가 한다.

## 시간과 판정

새 heavy 착수 cutoff는 **2026-11-05T00:55:55Z**(epoch 1793840155), 최종 stage deadline은 **2026-11-05T01:25:55Z**(1793841955)다. 마지막 30분은 기록·전달에 남긴다. 미측정 결과를 0점으로 채우지 않으며 현재 진행 중인 M2·M3는 실제 receipt로만 갱신한다. 자동 IoU는 춤 동작의 독립 품질 판정이나 후속 모델 선택 근거로 사용하지 않는다. 품질 HUMAN_REVIEW_PENDING, temporal=UNVERIFIED를 유지한다.
