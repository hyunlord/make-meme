# B-015 읽기 전용 CPU 비교 도구

기존 B-014 renderer의 최소6열 확장이다. SOURCE/ref/CFG_MOV/CFG_STILL/ALG_MOV/ALG_STILL을 같은 canvas로 표시한다. D 종료·finite·해시 확인 뒤 CPU renderer와 browser QA를 각각 한 번 실행했다. 기존 PNG 51/51 바이트 동일 복사, 비교 영상 3072×928·17프레임·24fps·0.708333초를 확인했다. 아래 명령은 실제 사용한 경로를 별칭으로 표현한 재현 기록이며 재생성을 실행하는 명령이 아니다.

```sh
CUDA_VISIBLE_DEVICES='' PYTHONDONTWRITEBYTECODE=1 "$CPU_PYTHON" "$TOOLS/output_review.py" \
  "$B013_LAB_MOV_INPUTS" "$B013_LAB_MOV_ARTIFACTS" \
  "$B013_LAB_STILL_ARTIFACTS" "$B013_OUTPUT_REVIEW" \
  "$B014_ALG_MOV_ARTIFACTS" "$B014_OUTPUT_REVIEW" \
  "$B015_ALG_STILL_ARTIFACTS" "$OUT"
"$BROWSER_PYTHON" "$TOOLS/check_review_ui.py" "$OUT/review.html"
```

별칭은 비공개 기존 경로이며 OUT은 새 경로다. 이전3개 결과의 PNG51장을 파일 그대로 복사하고 새 ALG_STILL raw만 기존 clamp/make_grid/uint8 방식으로 변환한다. model generation, mask 수정, pose warp, 안정화, 보간, 시간 변경은 없다. 전체17장·local0/12/14/16·grouped sheets·rawPNG·24fps MP4를 보존한다. 인코딩용 큰 collage는 저장하지 않고 pipe로 전달한다.

미디어는 비공개 결과 폴더에만 쓴다. manifest의 실제 SHA/변환과 browser 기능·CJK·desktop/mobile 확인을 남기며 자동 재생 이벤트를 실제 연속 영상 품질 검토로 주장하지 않는다. 시간 품질은 별도 관찰 없으면 UNVERIFIED다. 새 dependency/framework를 설치하지 않는다.

실제 산출물: `review.html`, `source-reference-four-cells.mp4`, `all17.png`, `selected.png`, `group-00-04.png`·`group-05-08.png`·`group-09-12.png`·`group-13-16.png`, `frames/000..016.png`, 네 셀의 raw PNG 폴더, `manifest.json`, `media-integrity.json`, `UI_QA.json`, `ui-desktop.png`, `ui-mobile.png`. 기능 검사와 두 viewport의 직접 스크린샷 확인은 PASS다. 모바일 여섯 열은 개요 크기이므로 세부 품질 판단에는 개별 PNG/큰 시트를 사용한다. 시간 품질은 UNVERIFIED다.
