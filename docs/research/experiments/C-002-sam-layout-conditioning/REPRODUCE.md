# C-002 재현과 보존

새 실행 권한을 추가하는 문서가 아니다. 기존 C-001 앵커·source·SAM selected masks·ENDPOINT를 재사용한다. 동일 native 프롬프트 재호출이나 ENDPOINT 재생성은 이번에 하지 않았다.

1. C-001 `INPUTS.json`, `ANCHORS.json`, `BACKEND_CONTRACT.md`와 C-002 `CONDITIONS.json`의 source/anchor/mask/layout hash를 대조한다. source/anchor는 832×480이고 마스크도 이미 같은 좌표다.
2. 기존 Spark research Python으로 `prepare_layouts.py ABS_C001_PRIVATE_ROOT ABS_C002_CONDITIONS_DIR`를 실행하면 기존 source 마스크에서 두 사례의 33개 layout을 만든다. OpenCV 5.0.0 external/simple 3px의 흰 바탕 검정 선이며, 무증강 uint8 PNG다. 기존 mask를 수정하거나 GT로 대체하지 않는다.
3. C-001의 실제 video config를 복사하고 `condition_mode`, `layout_dir`, 새 `output`만 바꾼다. mode는 layout_mov/layout_still이며, layout_dir에는 000..032.png가 있다. 기존 caption/negative/anchor/helper/weights/upstream/tokenizer 경로는 그대로다. 모든 경로는 절대경로다.
4. 동일한 C-001 `run_guarded.py`와 4개 guard 모듈을 그대로 사용하고 cell별 stage/freeze/현재 boot/deadline 정책을 만든다. worker symlink도 같은 adapter를 가리킨다. 같은 target entry에서 args에 `--cpu-only`만 추가한 실제 systemd 검사가 COMPLETE여야 matching heavy를 실행할 수 있다. C-001과 같은 연구 lock을 공유한다. unit/attempt의 C001 접두어는 기존 adapter 검사를 유지하기 위함이며, 추가 C002/cell 이름으로 구분한다.
5. 실행 순서는 rigid MOV, rigid STILL, nonrigid MOV, nonrigid STILL이다. 각 50step, seed20261028, CFG5, shift5, BF16/SDPA/tiled다. 셀 완료와 자원 회수를 확인한 뒤 다음 셀로 간다. 품질 재시도/추가 SAM/imagegen/다운로드는 없다.

CPU 검사는 `test_prepare_layouts.py`와 `test_video_condition.py ABS_C001_ROOT/code/frameref.py`에 있다. `video_generate.py ABS_VIDEO_CONFIG --cpu-only`는 실제 condition과 기존 import를 검사하며 CUDA를 초기화하지 않는다. CPU용 별도 모델 호출은 없다.

각 output의 `first-model-input.json`은 원래 첫 model_fn 직전의 실제 noise/context/마스크 64채널 관측이다. 같은 사례의 MOV/STILL noise SHA가 같은지 대조한다. context SHA 차이는 입력이 달랐음을 보여주지만 모델이 유용하게 활용했다는 증거가 아니다. 기존 C-001은 초기 noise hash가 없다.

Full에는 실제 condition 33 PNG·G 33 PNG·raw decoded tensor·atomic/readback한 final latent·무손실 33개 출력 PNG·원 MP4·원 관측/설정이 남는다. C-001 full과 weights를 새 ZIP에 반복 포장하지 않는다. Compact의 JPEG slider/crop/contact sheet와 조건/SAM preview는 명시한 검토 파생본이다. 생성 MP4는 기존/신규 모두 원바이트 그대로 복사한다.

`build_review.py ABS_C001_PRIVATE_ROOT ABS_C002_PRIVATE_ROOT ABS_NEW_REVIEW_DIR`로 동일 index 비교를 만든다. 전체 33장과 고정 0/4/8/12/16/20/24/28/32, 기존 C-001의 동일 crop을 쓴다. 시간 재정렬·공간 정합은 없다. 패키징은 기존 C-001 `package_review.py`의 CRC/실제 추출/payload hash 검사를 재사용하며 전송 후 두 호스트에서 다시 대조한다. raw가 제외된 compact 검증을 raw 전송 검증이라고 하지 않는다.
