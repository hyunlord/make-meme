# B-015 읽기 전용 CPU 비교 도구

기존 B-014 renderer의 최소6열 확장이다. SOURCE/ref/CFG_MOV/CFG_STILL/ALG_MOV/ALG_STILL을 같은 canvas로 표시한다. 현재 syntax/CLI 준비만 수행했으며 신규 출력 렌더와 browser QA는 아직 실행하지 않았다. 새 결과의 D 종료·finite·해시 확인 뒤 한 번만 실행한다.

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
