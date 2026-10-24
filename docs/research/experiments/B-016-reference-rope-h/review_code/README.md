# B016 CPU 비교 도구 — 준비 상태

기존 B015 renderer를 SOURCE / 실제 Lab reference / B013 CFG_MOV_H0 / 신규 CFG_MOV_H120 네 열로 축소했다. D 완료 후 실제 렌더·브라우저 QA를 각각 한 번 완료했다. H0 PNG17/17 byte identity, 비교 영상2048×928·17f24fps를 확인했고 desktop/mobile 스크린샷을 직접 검토했다. 기존 환경과 동일 quantization을 사용하며 새 의존성·UI 구조를 추가하지 않는다.

```sh
CUDA_VISIBLE_DEVICES='' PYTHONDONTWRITEBYTECODE=1 "$CPU_PYTHON" "$TOOLS/output_review.py" \
  "$B013_INPUTS" "$B013_MOV_ARTIFACTS" "$B013_OUTPUT_REVIEW" "$B016_ARTIFACTS" "$OUT"
"$BROWSER_PYTHON" "$TOOLS/check_review_ui.py" "$OUT/review.html"
```

OUT은 존재하지 않는 새 검토 폴더여야 한다. 기존 H0 PNG17장을 바이트 복사하고 H120 raw만 기존 clamp/make_grid/uint8으로 변환한다. 영상은 17프레임·24fps·0.708333초, 동일 canvas의 4열이다. source local0은 원본f7이다. all17·그룹·local0/12/14/16 시트를 보존한다. 프레임별 확대·정렬·warp·보간·시간 변경은 없다. UI 기능과 시간 품질을 구분하며 실제 연속 관찰 없으면 UNVERIFIED다. 미디어는 비공개 OUT에만 기록한다.

실제 산출물은 `review.html`, `source-reference-h0-h120.mp4`, `frames/`, `h0-raw/`, `h120-raw/`, `all17.png`, `selected.png`, 그룹4개, `manifest.json`, `media-integrity.json`, `UI_QA.json`, desktop/mobile 스크린샷이다. 원격 도구 복사 전 첫 명령은 파일 부재로 renderer 진입 없이 종료됐으며 실제 성공 렌더는1회다.
