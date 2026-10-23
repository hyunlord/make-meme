# B-014 재현과 읽기 전용 비교

공식 이식 감사·pilot1회와 CPU 검토 렌더1회·browser QA1회를 완료했다. sampler1/1은 소진됐으며 재시도0이다. 아래 명령은 완료된 실행의 기록이고 새로운 실행 승인이 아니다. frozen runtime 코드와 CPU 미디어 도구를 구분한다.

## 검토 입력과 도구

기존 B-013 LAB_MOV/LAB_STILL의 raw-derived PNG를 파일 그대로 복사한다. 새 ALG raw만 기존 upstream clamp(-1,1)·make_grid(normalize=True,value_range=(-1,1))·×255·uint8 방식으로 PNG화한다. raw를 CPU에서 weights_only=True로 읽으며 학습·생성·자세 보정은 하지 않는다. 원래 입력/출력 파일은 변경하지 않는다.

도구: [output_review.py](review_code/output_review.py), [review-template.html](review_code/review-template.html), [check_review_ui.py](review_code/check_review_ui.py). 기존 환경만 사용하며 새 패키지나 UI framework를 추가하지 않는다.

```sh
CUDA_VISIBLE_DEVICES='' PYTHONDONTWRITEBYTECODE=1 "$CPU_PYTHON" "$TOOLS/output_review.py" \
  "$B013_LAB_MOV_INPUTS" "$B013_LAB_MOV_ARTIFACTS" \
  "$B013_LAB_STILL_ARTIFACTS" "$B013_OUTPUT_REVIEW" \
  "$B014_ALG_ARTIFACTS" "$OUT"
"$BROWSER_PYTHON" "$TOOLS/check_review_ui.py" "$OUT/review.html"
```

별칭은 비공개 원본 경로를 가리키며 OUT은 새 경로여야 한다. 실제 D 종료·finite raw·17f24fps·아티팩트 해시 및 자원 회복 확인 후 Spark CPU에서 한 번 렌더하고 Mac에 동기화했다. 이전 출력으로 실패한 신규 결과를 대체하지 않는다.

## 비교 조건과 blind 절차

primary panel은 SOURCE/실제 Lab reference/B013 LAB_MOV/B013 LAB_STILL/LAB_MOV_ALG의5열이다. 전체17장과 local0/12/14/16, grouped sheets를 보존한다. 프레임별 별도 확대·crop·warp·보간·안정화·속도 변경은 없다. 모든 full canvas는 동일 배율로 표시한다. 비교 MP4는 기존17장·24fps 출력 decode 후5열 재인코딩하므로 raw PNG와 인코딩 경로를 구분한다.

A/B는 기존 MOV와 신규 ALG에 한 번 고정 무작위 배정하고 SOURCE/ref/STILL control은 고정 표시한다. mapping JSON은 두 검토 기록을 저장한 뒤 처음 읽어 공개했다. 실제 A=B013 LAB_MOV, B=LAB_MOV_ALG이며 비공개 `reports/blind-disclosure.json`에 공개 시각과 두 기록·mapping 해시를 보존했다. 같은 에이전트 계열의 검토를 독립 인간 blind 평가로 부르지 않는다.

archive에는 primary17장·rawPNG·group/selected·비교MP4를 보존하되, MP4 인코딩용 full-resolution collage는 pipe로만 전달하여 중복 PNG를 남기지 않는다. tool/input/output SHA와 변환은 manifest로 남긴다. 실제 browser 기능·CJK·desktop1280×960/mobile400×900 검증을 한 번 수행해 PASS했다. 이전/다음·slider·경계0/16·autoplay/loop OFF·한 번 재생 종료를 확인했다. 자동 ended/paused 이벤트는 시간적 영상 품질 검토를 대신하지 않으며 연속 시청이 없으면 UNVERIFIED다.

### 실제 검토 파일

비공개 `reports/output-review/`에 `review.html`, `source-reference-baseline-alg.mp4`(2560×928·17f24fps·0.708333초), `frames/000.png`~`016.png`, `all17.png`, `selected.png`, `group-00-04.png`·`05-08`·`09-12`·`13-16`을 보존했다. raw-derived PNG는 `baseline-mov-raw/`, `baseline-still-raw/`, `alg-raw/`에 있다. 기존34개 파일은 B013과 SHA가 완전히 같고 재렌더하지 않았다. `blind-frames/`, `blind-group-*.png`, `blind-selected.png`와 별도 `blind-mapping.json`도 보존한다.

`manifest.json`에는 입력/output/tool 해시·변환·기존 PNG34개 byte-copy 확인·비교 영상 ffprobe가 있다. `UI_QA.json`, `ui-desktop.png`, `ui-mobile.png`는 기능과 표시 검증 근거다. 두 blind 관찰 기록과 공개 receipt를 포함해 Mac/Spark에 동기화했다. 시간 품질은 UNVERIFIED이며 기술적 재생 성공을 전신·개체 품질 수용으로 바꾸지 않는다.

## 고정 runtime 경로와 실행 명령

다음은 이번 한정 실행의 재현 계약이다. 이미 사용한 stage를 삭제하거나 새 디렉터리로 예산을 초기화하는 재실행 승인이 아니다. 실제 완료·실패 여부는 RUN_LEDGER의 terminal receipt를 따른다. 신규 P는 **0회**이며 B013 LAB_MOV의 성공한 P를 재사용한다.

별칭 `B014_ROOT`는 이번 비공개 실행 루트, `B007E_ROOT`는 검증된 기존 `environment/models/upstream` 루트, `PARENT_CASE`는 B013의 `cases/LAB_MOV`다. 개인 입력·모델·cache는 공개 저장소에 포함되지 않는다. 새로운 `B014_ROOT/artifacts` 아래 부모의 `conditions.safetensors`, `conditions.json`, `conditions_receipt.json`, `initial_noise.pt`만 읽기 전용으로 참조하며 새 filtered/final 파일은 B014 경로에 쓴다. `configs/self.json`은 원래 Lab config의 바이트를 유지하고 ALG 설정은 별도 [alg.json](configs/alg.json)에 둔다.

[contracts.py](code/contracts.py)는 부모 cache receipt를 **부모 B013 코드 manifest/input map**에 연결한다. [parent_binding.json](configs/parent_binding.json)의 해시로 parent P result/clean-exit·pair/lineage receipt도 검증한다. 새 실행 코드 manifest는 [run_phase.py](code/run_phase.py)가 독립 검증한다. 원래 P를 B014에서 다시 성공 처리하지 않으며 최종 latent에는 원래 조건 계보와 B014 실행 계보를 따로 넣는다.

CPU 준비와 fixture에서 사용한 명령 구조는 다음과 같다. `prepare_filter.py`는 최초 1회 CPU down/up 후 safetensors/readback/hash를 저장한다. 이후 helper의 exhaustive-match 위치만 수정한 때에는 tensor bytes를 다시 만들지 않고 이전 metadata를 보존한 뒤 코드 바인딩만 명시적으로 갱신했다.

```sh
CUDA_VISIBLE_DEVICES='' "$B007E_ROOT/environment/bin/python" \
  "$B014_ROOT/code/prepare_filter.py" "$B014_ROOT"
CUDA_VISIBLE_DEVICES='' B014_ROOT="$B014_ROOT" \
  SCAIL_SOURCE="$B007E_ROOT/upstream/wan/scail.py" \
  "$B007E_ROOT/environment/bin/python" -m pytest "$B014_ROOT/code/test_alg.py" -q
CUDA_VISIBLE_DEVICES='' "$B007E_ROOT/environment/bin/python" \
  "$B014_ROOT/code/audit_parent_cache.py" "$B014_ROOT"
"$B007E_ROOT/environment/bin/python" "$B014_ROOT/code/prepare_layout.py" \
  "$B014_ROOT" "$B007E_ROOT"
```

격리 stage는 `stages/PROBE`, `stages/S`, `stages/D` 세 개뿐이다. 다음 shell 함수는 반복되는 실제 argv를 줄인 문서 표기이며 새 API가 아니다. 각 호출 후 이전 worker가 정상 종료하고 PID0, swap0, fresh72GiB 가용 메모리·idle queue를 확인해야 한다.

```sh
launch_recorded() {
  STAGE_NAME="$1"
  SECONDS_CAP="$2"
  STAGE_ROOT="$B014_ROOT/stages/$STAGE_NAME"
  "$STAGE_ROOT/environment/bin/python" "$STAGE_ROOT/code/runtime_launch.py" \
    "$STAGE_ROOT" "$SECONDS_CAP" /usr/bin/env \
    PYTHONDONTWRITEBYTECODE=1 CUDA_MODULE_LOADING=LAZY \
    OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
    IMAGEIO_FFMPEG_EXE=/usr/bin/ffmpeg \
    "$STAGE_ROOT/environment/bin/python" "$STAGE_ROOT/code/run_phase.py" \
    "$STAGE_ROOT" "$STAGE_NAME"
}
launch_recorded PROBE 300
# 정상 종료·부모 cache exact restore·자원 회복을 확인한 뒤만 진행
launch_recorded S 7200
# 40 scheduler step/88 forward, finite final latent의 SHA/value readback,
# branch trace와 sidecar 일치, S 정상 종료/PID0/자원 회복 후만 진행
launch_recorded D 1800
# 실제 raw [3,17,896,512] finite + 17f/24fps MP4와 ffmpeg decode 검증 후 종료
```

실제 worker 절대 deadline은 **2026-10-23 20:30:00 UTC**이고 요청의20:40보다 보수적이다. `runtime_launch`의 durable outer systemd와 `runtime_guard`의 owned inner unit은 기존72GiB 시작/24GiB 실행 headroom, swap0, 타 서비스 보호, cgroup·시간 상한을 그대로 유지한다. 위 초 단위 상한보다 전체 deadline이 먼저 오면 먼저 종료한다. 어떤 실패에서도 재시도·다음 생성은 없다.

S는 부모 P의 16개 leaf를 원래 device로 복원하며 CPU RNG state/sigmas를 GPU로 옮기지 않는다. 같은 CUDA noise·generator state·timesteps를 사용하고, 별도 CPU filtered reference를 원래 reference device로 복원한다. i0..7은 original-negative→low-negative→low-positive의 세 순차 forward, i8..39는 원래 positive→negative의 두 forward다. 모든 예측은 다음 호출 전에 기존처럼 CPU로 offload한다. scheduler는40회이며 `alg_branches.jsonl`은 추가 forward 없이 실제 branch/index/reference SHA와 예측 norm만 남긴다. OFF/ratio1의80회 계약은 CPU fixture로 검증했으며 별도14B baseline을 재생성하지 않았다.

### 이번 실행의 terminal 확인

사전등록 `3cd90e196307fe1f663e8533124a0cbe42f8f41e` 이후 위 PROBE→S→D를 각각1회 실행해 모두 정상 종료했다. 실제 S counter는40step/88forward이고 branch trace는 i0..7의3회·i8..39의2회 순서와 일치했다. SHA는 filter 생성/device restore 때 검증한 tensor를 실제 kwargs 선택에 따라 기록한 것이며 매 forward마다 GPU bytes를 다시 해시한 것은 아니다.

최종 latent file SHA `3d76cbc4f95e881346da2500c037d413e05e79e360f8b3ef3001d0ad2ee24594`, value SHA `d99d52d2ef1ba3c84b26289f5d740fced484072d6f91fdc453dcac861b9c8bf8`를 CPU에서 재읽어 확인했다. raw finite17f/24fps·MP4 전체 decode도 통과했다. [실행 장부](RUN_LEDGER.json), [실측](MEASUREMENTS.json), private `reports/final-latent-gate.json`, `output-artifact-receipt.json`, `postrun_integrity.json`이 근거다. 종료 후426개 보존 해시와 owned unit inactive/PID0을 확인했고, 부모/cache/가중치나 생성 결과를 덮어쓰지 않았다. 실제 영상 품질·효과 해석은 별도 검토에 따른다. 이 한정 sampler 예산은1/1로 소진됐다.
