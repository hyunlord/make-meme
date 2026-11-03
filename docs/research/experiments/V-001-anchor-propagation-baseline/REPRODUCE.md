# V-001 실제 실행 경로

기준c55ff976,사전8ad08a9,배역/해상도개정32e2371,SAM/가드185e769. 실제경로는 private manifest/settings에만 보존한다.

```sh
# 입력 원본에서 각 고정73프레임을1280×720으로 추출
ffmpeg -i "$SOURCE_VIDEO" -vf 'select=between(n\,96\,168),scale=1280:720' -fps_mode passthrough -start_number 0 "$PRIMARY/%03d.png"
ffmpeg -i "$SOURCE_VIDEO" -vf 'select=between(n\,240\,312),scale=1280:720' -fps_mode passthrough -start_number 0 "$FALLBACK/%03d.png"
# 기존 C012make_stage.py를 V private settings로 사용, 새 launcher 없음
C012_STAGE_SETTINGS="$V_SETTINGS" "$PYTHON" "$C012_CODE/make_stage.py" "$RUN_ROOT" sam-primary "$V_CODE/sam_analysis.py" "$PRIMARY_CONFIG"
# 각 stage의 policy attempt_id=C001_V001_APPROVED_01,authorization갱신 후 freeze hash갱신
"$PYTHON" "$C001_CODE/run_guarded.py" "$RUN_ROOT/stages/sam-primary-cpu"
"$PYTHON" "$C001_CODE/run_guarded.py" "$RUN_ROOT/stages/sam-primary-heavy"
# primary미달 후 같은절차로 sam-fallback CPU/heavy 각1회
```

동일 V가드사본이CPU/heavy에 적용되고 실제파일sha가freeze에 포함됐다. 과거 memory state를 덮어쓰지 않았다.
SAM3.1 기존 Comfy commit5cc4b870094c89090db54bd8d12649dcaf89f2ba,querydog,threshold.5,maxobjects4,detectinterval1.
전트랙을 보존했다. 최초에는 source tracking만 실행했다. 개정2에서 image mode로 앵커1회 추가 분석했다. 생성 출력 평가는 NOT_RUN.
표준연구Python torch2.14.0+cu130,최초 종료 시 추가설치0;개정2의 격리 설치는 RUNTIME_DIFF에 기록했다. 생성 seed는미사용. 구간미달 뒤 자동재시도나신규구간 탐색 없음.

뷰어 검증: 설치된Chrome headless의실제미디어4개metadata와재생/정지/프레임이동/0.5배속/구간전환을CDP로확인했다. 스크린샷을직접확인했다. 연속지각품질은UNVERIFIED. 추가browser패키지설치0.

## 개정2 실제 실행

```sh
# 기존 fallback SAM summary를 CPU 재판정, source SAM 재실행 없음
python3 code/test_reflections.py
# source/anchor summary와 이미지 역할은 private config로 전달
"$CPU_PYTHON" code/anchor_gates.py "$ANCHOR_GATE_CONFIG" "$ANCHOR_GATE_RESULT"
# imagegen은 native tool에 실제 세 이미지 경로를 전달; ledger에 raw/hash 보존
# sam-anchor1은 기존make_stage/run_guarded의 CPU와heavy로 각1회 실행
"$E2_PYTHON" -m pip install --no-deps transformers==4.57.3 tokenizers==0.22.1 huggingface-hub==0.36.0 diffusers==0.35.2 accelerate==0.34.2 imageio-ffmpeg==0.6.0
"$E2_PYTHON" -m pip install --no-deps git+https://github.com/ByteDance-Seed/VeOmni.git@v0.1.11
# E2 checkout 안에서 patch 적용, compat를bernini/decord_compat.py로복사
git apply "$V_CODE/e2_runtime.patch"
"$E2_PYTHON" -c 'import torch; print(torch.__version__, torch.__file__); import bernini.cli; print("E2_IMPORT_OK")'
```

설치 중 torch 미발견→공유Comfy경로추가,시스템OpenSSL충돌→격리venv system-site-packages=false로해결했다. 위 경로변수는 재현 문서용 역할명이며 실제절대경로·명령·로그는private에보존한다. 가중치download는고정revision을사용했지만memorycap확인후자체downloader를종료해미완료다. 생성 명령을 실행한 것처럼 기록하지 않는다. E2probe와모든sampler는NOT_RUN이다.
