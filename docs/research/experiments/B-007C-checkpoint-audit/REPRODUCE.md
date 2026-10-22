# B-007C 재현과 실행 경계

실제 경로는 비공개 manifest에서만 해석한다. B-007B의 기존 환경과 검증된 공식 checkpoint를 사용하며 새 다운로드는 없다. 사전 코드 commit: 그래프 `003c733`, 최초 fixture `180dc79`, 첫 amendment `92d644f`. 최종 코드와 실행 파일 SHA는 evidence summary 및 private manifest를 참조한다.

## 비실행 그래프 감사

```sh
"${B007C_PYTHON}" -m unittest discover -s "${CODE_ROOT}" -p 'test_pickle_graph.py' -v
"${B007C_PYTHON}" "${CODE_ROOT}/graph_guard.py" "${RUN_ROOT}" graph-audit \
  "${B007C_PYTHON}" "${CODE_ROOT}/checkpoint_graph_audit.py" \
  "${SAT_CHECKPOINT}" "${RUN_ROOT}/reports/checkpoint_graph.json" "${DOWNLOAD_LEDGER}"
```

guard의 원래 deadline은 해당 실행일 12:21 UTC다. 다른 날 재현하려면 별도 실행 승인과 deadline을 기록해야 하며, 이미 종료된 실행이 자동 재개되지는 않는다. 입력 파일은 고정 크기/SHA와 기존 VERIFIED 장부가 모두 일치해야 한다. ZIP 구조와 data.pkl만 분석하고 tensor storage payload는 변환하지 않는다. 파일 전후 전체 SHA를 읽는 I/O는 포함된다. ZIP CRC 필드는 관측값이며 모든 storage CRC를 따로 재계산했다는 뜻은 아니다.

## Synthetic-only restricted loading

```sh
CUDA_VISIBLE_DEVICES='' OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 \
 timeout 180 "${B007B_PYTHON}" "${CODE_ROOT}/fixture_rng.py" \
 "${NEW_FIXTURE_OUTPUT}" "${B007B_CODE_ROOT}" "${PINNED_OFFICIAL_CONVERT}"
```

실제 실행은 별도 제한 프로세스에서 수행한다. fixture 스크립트는 checkpoint 입력 인자를 받지 않고, 새 출력 폴더에 직접 만든 작은 tensor/RNG 파일만 로드한다. legacy NumPy GLOBAL 변경도 이 작은 자체 생성 파일에만 적용하며 모든 다른 ZIP member가 동일한지 검사한다. 이 helper를 실제 파일 재작성 도구로 재사용하지 않는다.

strict gate 거부, 동적 dtype 누락 거부, 예상 밖 class 거부는 의도한 negative 결과다. 실패한 시험의 로그와 각 수정 전 코드는 private evidence에 보존한다. 실제 SCAIL checkpoint에 scoped allowlist를 적용하는 명령은 이번 재현 범위에 포함하지 않는다.

최종 fixture 코드 사전 commit은 `542399b`다. 최초/두 번째 실패 코드도 git과 비공개 ZIP의 snapshots에 보존한다. 공개 실행 코드 SHA는 [execution_manifest.json](execution_manifest.json)에 있다.

저장된 graph에서 공개 요약 재계산:

```sh
"${B007C_PYTHON}" "${CODE_ROOT}/summarize_graph.py" \
 "${RUN_ROOT}/reports/actual_graph_private.json" "${NEW_SUMMARY_JSON}"
```

이는 이미 기록한 JSON만 읽으며 원본 checkpoint를 다시 로드하지 않는다. 요약에는 raw pickle 내용이나 개인 경로를 포함하지 않는다. Private 실행의 실제 출력 이름은 `actual_graph_private.json`이며 위 최초 감사 명령의 report 인자는 원하는 새 이름으로 지정할 수 있다.
