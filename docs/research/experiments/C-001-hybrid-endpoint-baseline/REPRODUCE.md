# C-001 재현 정보

이 문서는 결과를 재검토하기 위한 기록이다. 새 imagegen·SAM·sampler 호출 권한을 부여하지 않는다. 원본 가중치와 개인 경로는 공개하지 않는다. 기존 A/B 환경을 수정하지 않고 별도 C 디렉터리를 사용했다.

## 저장된 결과부터 보기

compact ZIP을 한 디렉터리에 추출하고 `index.html`을 연다. SOURCE / TARGET REFERENCE / START ANCHOR / END ANCHOR / GENERATED VIDEO 순서와33프레임 슬라이더가 있다. MP4는16fps이며 실제 원본 FPS를 알 수 없다. 브라우저 재생 가능성과 시간 품질 인간 판정은 별개다. full raw·latent는 ZIP에 포함하지 않고 원래 연구 저장소에 보존한다.

## 동일 입력과 모델 확인

`INPUTS.json`과 각 EditSpec은 DAVIS 프레임번호, source/reference 계보와 해시를 고정한다. `ANCHORS.json`에는 실제 native 도구의 네 프롬프트·호출시각·이미지 해시·크기 변환이 있다. 내장 도구의 동일 프롬프트 재호출은 같은 이미지의 재현을 보장하지 않는다. 후속 동일 앵커 비교는 저장한 PNG를 그대로 사용해야 한다.

`BACKEND_CONTRACT.md`의 checkpoint, tokenizer, helper, 기존 DiffSynth 코드 해시를 대조한다. 기존 research Python과 설치 패키지를 재사용했다. 네트워크 자동 다운로드는 `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`, model config `skip_download=True`로 차단했다. 새 package·weight 설치는 없다.

## 실행 경로

개인 경로를 대신하여 아래 이름을 사용한다. `PYTHON`, `CROOT`, `UPSTREAM`, `WEIGHTS`, `TOKENIZER`는 실제 존재하는 절대경로여야 한다. 상대경로를 worker에 전달하면 안 된다.

1. `prepare_inputs.py`로 고정된33장 source와 참조를 동일 aspect fit으로 만든다. native anchor raw를 보존하고 네 장 모두 같은1652×952→832×479 + 아래1행 패딩을 적용한다.
2. `video_generate.py` config에는 `upstream`, `weights`, `tokenizer`, `helper`, `helper_sha256`, `start_anchor`, `end_anchor`, `output`, `prompt`를 넣는다. 두 사례의 실제 caption과 수치는 실행 결과의 설정 기록에 보존한다. `seed=20261028`,33frames,832×480,50steps,CFG5,sigma_shift5,16fps가 코드에 고정돼 있다.
3. 같은 `run_guarded.py` 경로에서 `--cpu-only`인 target args로 CPU systemd 진입과 정상 종료를 검증한다. 이 flags만 제외한 target 경로·args·입출력·environment·코드해시가 heavy와 같아야 한다. heavy는 일치하는 `supervisor-result.json`과 `path-validation.json` 없이는 실행되지 않는다.
4. stage에는 config, frozen files, 현재 boot/deadline과 결합된 OPTIONAL_EXPECTED_ABSENT service policy, reports 디렉터리, adapter를 가리키는 `code/worker.py`가 있다. 모든 C stage는 같은 research lock을 쓰며 각 별도 작업의 memory baseline은 분리한다. 하나의 영상 sampler→decode 동안은 같은 baseline을 유지한다.
5. SAM 분석을 먼저 완료·회수하고 두 영상 작업을 순차 실행한다. 실제 entry는 `PYTHON CROOT/code/run_guarded.py ABSOLUTE_STAGE_ROOT`다. 보고서의 실제 CPU·heavy 영수증을 확인한다. 안전 실패를 무시하거나 외부 프로세스를 종료하지 않는다.

영상 target은 `PYTHON CROOT/code/video_generate.py ABSOLUTE_CONFIG_JSON [--cpu-only]`다. CPU-only는 조건33장·실제 양끝 RGB·mask·기존 import·ffmpeg 경로를 검사하고 CUDA를 초기화하지 않는다. actual model_fn/scheduler counts와 마지막 latent readback은 runtime 결과로 따로 기록한다.

## 보존과 검증

`build_review.py PRIVATE_ROOT NEW_REVIEW_OUTPUT VIDEO_OUTPUT_ROOT`는 실제 입력·출력을 복사하고 JPEG contact sheet를 추가한다. 영상 MP4는 생성 후 만든 원본 파일을 그대로 복사한다. source preview와 모델 output MP4의 최초 인코딩, JPEG sheet 생성은 별도 변환이며 전체 작업을 ‘재인코딩0’으로 부르지 않는다.

`package_review.py ABS_REVIEW_DIR ABS_NEW_ZIP ABS_NEW_EXTRACT_DIR`는 ZIP64를 만들고 실제 CRC 검사·추출·각 payload SHA-256 대조를 수행한다. 전송 후 다른 호스트에서도 ZIP hash와 실제 추출 payload를 확인한다. 이 검증 범위는 compact payload이며 제외한 raw tensor 검증을 뜻하지 않는다.
