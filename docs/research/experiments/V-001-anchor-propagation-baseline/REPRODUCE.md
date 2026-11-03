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

## 개정2 실제 실행 — 당시 중단 기록

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


## 개정3 실제 실행과 현재 제한

사전 개정 기록은 `abf48fd`다. 기존 Gemma 403과 개정2 E2 다운로드 중단은 과거 기록으로 보존한다. 개정3에서는 같은 `google/gemma-3-12b-it`의 기존 인증 접근을 다시 확인하여 성공했고, 고정 revision의 E1 가중치를 내려받았다. E2에만 worker 100GiB 예외를 적용하며 E1은 기존 64GiB다. 정확한 패키지·revision은 `RUNTIME_E1.md`, `RUNTIME_DIFF.md`, `LICENSES.json`을 참조한다.

고정 source는 LTX `e98f6d927d83c92ef2be6aec76c8440b19306e39`, Video Depth Anything `4f5ae23172ba60fd7bc11ef671cca678842c7072`, Bernini `e6c2cf11843470b08491745947abcba9c3c6b079`다. 공통 1280×720 앵커와 확정 fallback 73프레임에서 E1 입력 1024×576을 만들었다. E2는 승인된 832×480 입력을 사용한다.

기존 stage runner를 사용한 실행 순서는 depth CPU 검사 → depth heavy → CPU 포장 복구 → E1 probe CPU 검사 → E1 probe heavy였다. 각 stage의 설정·freeze·실제 명령·원본 로그는 private 실행 기록에 있다. 아래는 경로 역할을 사용한 검증 인터페이스이며 GPU 작업을 직접 실행하는 우회 명령이 아니다.

```sh
# 기존 stage 설정에서 entry/config를 지정하고 run_guarded.py로 CPU/heavy를 분리한다.
"$E1_PYTHON" "$V_CODE/e1_entry.py" --config "$E1_PROBE_CONFIG" --cpu-only
"$PYTHON" "$C001_CODE/run_guarded.py" "$RUN_ROOT/stages/v001-e1-probe-amend3-cpu"
# 당시 heavy 실행은 아래 stage로 수행했으며 geometry 실패 후 재실행하지 않았다.
"$PYTHON" "$C001_CODE/run_guarded.py" "$RUN_ROOT/stages/v001-e1-probe-amend3-heavy"
```

E1 private config의 키는 `mode`, `receipt`, `official_args`, `output`이다. `official_args`에는 distilled checkpoint, spatial upscaler, Gemma root, `--lora UNION 1.0`, `--video-conditioning DEPTH 1.0`, `--image ANCHOR 0 1.0`, 높이 576·너비 1024·73프레임·24fps·seed 20261103·고정 prompt·출력 경로를 넣었다. Probe는 공식 8+3 step schedule을 그대로 유지하고 첫 denoising step 완료 뒤 종료하도록 계측했으나, 실제로는 그 첫 step에 도달하지 못했다.

Depth 모델은 1회 호출(내부 forward 4회), 44.7085초였다. raw NPZ와 정규화 PNG 73개를 보존했지만 공식 writer가 Matplotlib 3.11.2의 제거된 `cm.get_cmap` 때문에 실패했다. `vda_package.py`의 CPU 복구는 기존 raw에서 동일한 정규화 PNG를 확인하고 `cm.get_cmap`을 현재 colormap API로 연결한 뒤 공식 writer(libx264, CRF18, grayscale)로 포장했다. 새 depth 호출·모델 적재는 각각 0회였으며 원래 실패 receipt를 보존했다. 포장 receipt는 `CPU_PACKAGING_RECOVERED`, 73프레임·1024×576·24fps다.

E1 probe는 조건 VAE에서 약 18.9813초 뒤 실패했다. reference tensor `[1,1024,20,9,16]`의 높이 9를 stride 2로 나눌 수 없었다. 공식 half-resolution stage와 LoRA의 `reference_downscale_factor=2`가 결합해 최종 공간 크기에 **128 배수**가 필요하지만 사전 CPU 검사는 64 배수까지만 확인하여 이를 놓쳤다. 1024×576에서 내부 reference는 256×144가 된다. Denoiser 호출 0, 완료 scheduler step 0, 생성 영상 0이므로 시간 probe 완료나 생성 비용으로 계산하지 않는다. 해상도·reference 배율·모델 연산을 바꾸지 않고 고칠 수 없어 `ENGINE_BLOCKED_ENV`로 남겼다.

E2는 고정 코드의 renderer-only RV2V 경로를 준비했다. 원본은 case의 video 역할, 공통 앵커는 reference images 역할로 전달하고 prompt enhancer를 비활성화한다. 공식 `BerniniRendererPipeline`이 원본과 참조를 각각 VAE encode해 `multi_video_vae_latents`와 `multi_image_vae_latents`를 sampler에 전달하는 것을 정적으로 확인했다. 이후 E2 snapshot 126,200,552,703 bytes와 index 참조 shard 27개를 모두 확보해 기존 guarded heavy 경로에서 적재를 시작했다. 두 번째 expert 5/12 지점, 약 75.6초에 `SYSTEM_PSI_FULL_PRESSURE`로 중단됐고 denoising은 0회다. 정확한 압박 구간은 guard 원본 로그와 RUNS 감사 기록을 따른다. 모델 적재 시작을 sampler 실행이나 영상 생성 성공으로 간주하지 않으며 동일 단계 재시도는 하지 않았다.
