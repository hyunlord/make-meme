# 재현 자료와 미실행 상태

이 문서는 새 실행 권한이 아니다. C-003은 기존 시작 guard `START_SWAPOUT_OBSERVED`로 중단됐다. 자동재시도/예약은 없다.

부모 C001/C002의 INPUTS/ANCHORS/CONDITIONS와 lossless source33, selected SAM33, 실제layout33을 그대로 참조한다. 공식 scribble weight 한 파일의 immutable provenance는 ANNOTATOR.md에 있다. 모델이나 기존 결과를 다시 받거나 만들지 않는다.

코드 인터페이스:

- `scribble_extract.py ABS_CONFIG [--cpu-only]`: config는 source_dir,weights,output,device. 기존 보호 run_guarded.py가 실제경로를 호출한다. CPU는 모델을 올리지 않는다.
- `prepare_internal.py ABS_CONFIG`: source,masks,layouts,scribble,output. 완료 extraction receipt와 파일hash를 확인하고 조건을 만든다. 이번 실제자료로 호출하지 않았다.
- `video_generate.py ABS_CONFIG [--cpu-only]`: 부모 config에 condition_mode,internal_dir,interior_dir을 추가하고 기존 layout_dir을 유지한다. 이번 영상모델은 호출하지 않았다.
- `test_prepare_internal.py`: 합성 CPU geometry 불변 검사. 실제 source33의 I/bbox zero-edge도 독립 CPU 확인했다.
- `build_review.py`: 기존자료/새자료 검토용. 이번 전달은 blocked 경로를 사용한다.

첫 CPU import실패의 raw로그와 수정후 안전차단 start-samples는 비공개 full 경로에 보존한다. 공개 NUMERICS는 개인경로/프로세스신원 없는 요약이다. guard/adapter는 C002에서 쓰던 파일 그대로이며 source receipt/freeze에 hash를 보존한다. 최초계획2e115dd, import수정13aa084는 추출 전 원격SHA가 일치했다. 후속 변환코드는 미실행 구현으로 구분한다.

Compact는 기존source/target/anchors/OUTLINE_ONLY와 상태·코드·보고서이며 신규영상/구조선/raw/latent는 없다. 기존full/weight는 재포장하지 않는다. 보존/전송검증은 DELIVERY.json을 따른다.
