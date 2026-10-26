# 재현 계약

기존 pinned SCAIL 환경만 사용한다. 새 설치는 없다. `${B027_ROOT}`는 보존된 공개 패널 실험, `${B028_ROOT}`는 새 전용 출력, `${B025_ROOT}`는 모델/환경 계보를 가진 이전 실험 root다. 개인 절대경로는 공개하지 않는다.

```sh
python code/prepare_inputs.py "$B027_ROOT" "$B028_ROOT"
# task=animal,human,vehicle 각각:
python code/prepare_layout.py "$B028_ROOT/tasks/$task" "$B025_ROOT" "$B028_ROOT/code"
python code/freeze_run.py "$B028_ROOT/tasks/$task"
# 실제 preregistration push 확인 후, 각 task의 다음7단계 순차:
# ENC R1_PROBE R1_S R1_D R2_PROBE R2_S R2_D
python "$B028_ROOT/code/runtime_launch.py" "$B028_ROOT/tasks/$task/stages/$stage" 1800 \
  "$PINNED_PYTHON" "$B028_ROOT/code/run_phase.py" "$B028_ROOT/tasks/$task/stages/$stage" "$stage"
```

실제 실행은 단계별 소유 unit 종료/회복을 확인하며 이어간다. 기존 attempt/result가 있으면 동일 stage를 재실행하지 않는다. source_fps=null/preview24/timebase_assumed=true다. 결과를 원래 초 단위 동작 보존으로 주장하지 않는다.

## 실측 요약 재사용

완료 후 B-027의 기존 CPU reporting 함수 `reporting_code/summarize.py:summarize`를 같은 stage/task 구조에 재사용한다. 반환 객체의 experiment label만 B-028로 표시한다. 이는 GPU runtime이나 과거 결과 변경이 아니다. 예:

```sh
PYTHONPATH="$B027_REPORTING_CODE" python - "$B028_ROOT" <<'PY'
import json, sys
from pathlib import Path
from summarize import summarize
root = Path(sys.argv[1])
report = summarize(root)
report['experiment'] = 'B-028'
report['timing_context'] = 'CPU comparison rendering and artifact transfers may overlap; not isolated performance benchmarking'
(root/'reports/execution_summary.json').write_text(json.dumps(report, indent=2)+'\n')
PY
```

메모리 회계는 시스템 available·개별 process RSS·cgroup·CUDA allocator를 따로 읽으며 합산하지 않는다. CPU 비교 시트 렌더와 네트워크 전송이 일부 S 실행과 겹칠 수 있어 비용 차이를 방법 자체의 속도 개선으로 해석하지 않는다.
