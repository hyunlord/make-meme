# B-013 재현 계약

양 P/PROBE/S/D는 모두 **COMPLETED**다. [실행 장부](RUN_LEDGER.json)의 sampler 사용량은 **2/2회·실패0·재시도0**이며 이미 소진됐다. 아래는 실행 기록과 재현 설명이며 추가 실행 승인이 아니다. B-012 MOV/STILL은 기존 결과를 재사용했다. [Lab pair](CONDITION_COMPARISON.json)와 [계보](LINEAGE_COMPARISON.json)는 PASS지만 전신 동작 품질은 FAIL, 국소 반응은 PARTIAL, 시간 품질은 UNVERIFIED다.

## 입력과 실행 통제

B-012 실제 processed source index7~23 및 mask를 해시 검증 후 그대로 사용한다. LAB_STILL은 대응 B-012 STILL과 동일한 RGB/mask f0 반복 비디오다. 새 decode나 다른 고해상도 파일로 교체하지 않는다. reference는 기존 실제 Lab 사진, mask는 B-009 RED foreground+WHITE background다. 새 mask 개선·배경 삭제·시각 생성은 없다.

두 Lab 조건의 text/reference/noise/scheduler는 동일하다. source→Lab prompt 변화는 사전 diff와 실제 T5 길이로 남긴다. Lab 내부 4변경/12보존, B-012 대비 reference/task7변경 및 대응 control 검증을 구분한다. key 번호보다 실제 tree location을 따른다.

512×896·17장·24fps·seed20261022·UniPC40·shift3·CFG5·negative empty·replace_flag=False·history=None·LoRA/enhancer OFF다. 기존 mixed loader/FlashAttention/tiny64-byte anchor/P→PROBE→S→D 경로를 유지한다. STILL도 RGB를 실제 VAE encode하고 latent 첫 slice를 반복하지 않는다. 새 P cache가 필요하다. 각 S의 최종 latent 저장·finite·재읽기 검증과 종료 후 D에서 decode한다.

전체 deadline은 시작부터4시간, 이번 작업은19:43 UTC까지다. 실제 단계별 시간·hash·종료는 RUN_LEDGER.json에 보존했다. 모두40step·80forward를 마친 finite final latent를 D에서 decode했으며 첫 latent slice 대체나 프레임 복제는 없다. 종료된 승인으로 sampler를 자동 재실행하지 않는다.

## 실제 runtime 명령과 단계 순서

아래는 완료된 실행의 argv를 개인 경로 대신 별칭으로 나타낸 기록이다. **재실행 허가가 아니며, 이미 사용한 디렉터리에서 실행하지 않는다.** 각 stage의 `attempt.json`과 `watchdog-launch.json`은 exclusive-create이고 덮어쓰거나 삭제해 재시도하면 안 된다. frozen [runtime_guard.py](code/runtime_guard.py)의 실제 worker deadline은 **2026-10-23 19:30:00 UTC**다. 의뢰서의 19:43보다 보수적이며 종료된 실험의 deadline을 이 문서 때문에 연장하지 않는다.

별칭과 준비물:

- `B013_ROOT`: 두 case와 `code/`, `configs/`, `reports/`, 두 prereg manifest를 가진 해당 비공개 실행 루트.
- `B007E_ROOT`: 검증된 기존 `environment/`, `models/`, `upstream/`, `configs/allowed_gpu_processes.json`을 가진 읽기 전용 재사용 루트.
- `CPU_PYTHON`: 실제 사용한 `B007E_ROOT/environment/bin/python`. CPU 검사에는 `CUDA_VISIBLE_DEVICES=''`를 사용했다.
- 대응 B-012 루트는 `B013_ROOT`와 같은 부모 아래 `B-012-clear-motion-driving-control`이다. 이 상대 위치와 이전 cache/metadata/noise·driving 입력 SHA는 [lineage_baseline.json](configs/lineage_baseline.json)에 고정됐다.
- prepared inputs는 `cases/LAB_MOV/inputs`와 `cases/LAB_STILL/inputs`에 있어야 한다. 공개 [PREREGISTERED_INPUTS.json](PREREGISTERED_INPUTS.json), [PREREGISTERED_CODE.json](PREREGISTERED_CODE.json) 및 조건별 [LAB_MOV config](configs/LAB_MOV/self.json)/[LAB_STILL config](configs/LAB_STILL/self.json)를 실제 바이트와 대조했다. 개인 입력과 대형 가중치는 공개 저장소에 포함되지 않으므로 저장소 clone만으로 실행 가능한 패키지가 아니다.

실제 layout 준비 명령은 다음 argv였다. 기존 환경에 설치하거나 기존 case를 수정하지 않고 새 case/stage 폴더에 frozen code/config를 복사하고 읽기 전용 재사용 대상의 symlink를 만들었다.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 "$B013_ROOT/code/prepare_pair_layout.py" \
  "$B013_ROOT" "$B007E_ROOT"
```

실제 각 단계는 아래 동일한 launcher argv로 실행했다. `launch_recorded`는 문서에서 반복을 줄인 shell 표기이며 새로운 실행 API가 아니다. `CASE_NAME`, `STAGE_NAME`, `SECONDS_CAP`에 아래 순서표의 실제 값을 대입한 것이 각 private `watchdog-launch.json`/`pipeline-process.json`의 명령이다. GPU worker에는 `CUDA_VISIBLE_DEVICES=''`를 넣지 않는다.

```sh
launch_recorded() {
  CASE_NAME="$1"
  STAGE_NAME="$2"
  SECONDS_CAP="$3"
  STAGE_ROOT="$B013_ROOT/cases/$CASE_NAME/stages/$STAGE_NAME"
  "$STAGE_ROOT/environment/bin/python" "$STAGE_ROOT/code/runtime_launch.py" \
    "$STAGE_ROOT" "$SECONDS_CAP" /usr/bin/env \
    PYTHONDONTWRITEBYTECODE=1 CUDA_MODULE_LOADING=LAZY \
    OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
    IMAGEIO_FFMPEG_EXE=/usr/bin/ffmpeg \
    "$STAGE_ROOT/environment/bin/python" "$STAGE_ROOT/code/run_phase.py" \
    "$STAGE_ROOT" "$STAGE_NAME"
}
```

실행은 자동 병렬 loop가 아니라 아래 순서로, **각 명령의 종료와 gate를 확인한 뒤** 다음 명령을 호출했다. SSH는 Spark에서 이 명령을 전달하는 기존 연결일 뿐이며 호스트 이름·계정은 공개하지 않는다.

```sh
launch_recorded LAB_MOV P 1800
# P COMPLETED + service_exit/0 + MainPID=0 + resource recovery 확인
launch_recorded LAB_STILL P 1800
# 두 P 모두 정상 종료한 후, 아래 두 CPU comparator를 실행
CUDA_VISIBLE_DEVICES='' PYTHONDONTWRITEBYTECODE=1 timeout 120 \
  "$CPU_PYTHON" "$B013_ROOT/code/compare_conditions.py" "$B013_ROOT"
CUDA_VISIBLE_DEVICES='' PYTHONDONTWRITEBYTECODE=1 timeout 120 \
  "$CPU_PYTHON" "$B013_ROOT/code/compare_lineage.py" "$B013_ROOT"
# pair4/12 + B012 lineage7/9 모두 PASS, receipt 검토 후 잔여 실행 승인 확인
launch_recorded LAB_MOV PROBE 300
launch_recorded LAB_MOV S 7200
# S 정상 종료 + 실제 40 step/80 forward + final latent CPU readback/finite/hash 확인
launch_recorded LAB_MOV D 1800
# raw finite + MP4 17frames/24fps + ffmpeg decode + 정상 종료 확인
launch_recorded LAB_STILL PROBE 300
launch_recorded LAB_STILL S 7200
# 동일 S final-latent gate와 정상 종료/자원 회복 확인
launch_recorded LAB_STILL D 1800
# 두 번째 D 검증 후 종료. 추가 sampler 없음.
```

각 화살표에서 이전 worker 종료/PID0 및 새 headroom을 확인했다. [run_phase.py](code/run_phase.py)는 이전 stage receipt, P cache receipt, pair/lineage의 실제 cache SHA·코드 manifest·정책 SHA를 검사한다. P는 실제 영상 인코딩을 수행하며 두 comparator는 CPU로 저장된 tensor를 읽는다. 7/9 비교의 positive T5 길이 변화는 실제 `[91,4096]→[108,4096]`이고 강제로 길이를 맞추지 않는다. ref-mask prefix는 pinned helper와 exact, 생성 프레임 suffix는 기존 값 및 zero와 exact여야 한다.

[runtime_launch.py](code/runtime_launch.py)는 durable outer systemd watchdog와 종료 시 owned inner unit 정리를 적용한다. [runtime_guard.py](code/runtime_guard.py)는 72GiB 시작·24GiB 실행 headroom, swap0, 다른 GPU 작업/queue 보호, cgroup/시간 상한을 유지한다. 위 7200초 등은 **단계 요청 상한**이고 실제 상한은 남은 absolute deadline에 의해 더 짧아진다. 자원/조건/단계 오류에서 다음 명령을 실행하지 않으며 어떤 stage도 재시도하지 않았다.

최종 latent 검증은 기존 [artifacts.load_tree](code/artifacts.py)를 `device='cpu'`로 호출해 파일 SHA·각 tensor의 shape/dtype/value SHA를 재검증했다. `x0[0]`은 finite FP32 `[16,5,112,64]`, counters는 `model_calls=80, completed_steps=40`이어야 했다. P noise와 저장된 `initial_noise.pt`는 exact이고 최종 value SHA는 초기 noise와 달랐다. 실제 검증 결과는 각 case의 private `reports/final-latent-gate.json`과 공개 [RUN_LEDGER.json](RUN_LEDGER.json)에 들어 있다. D는 [phase_decode.py](code/phase_decode.py)에서 저장된 실제 x0만 읽고, 영상 검증 후에만 COMPLETED를 기록했다.

## 읽기 전용 비교와 판정

SOURCE와 실제 Lab reference, 기존 B-012 MOV/STILL, 새 LAB_MOV/LAB_STILL을 같은 canvas로 표시한다. raw 전체17장 및 local0/12/14/16 이벤트를 보존하고 24fps 시간축을 바꾸지 않는다. 좋은 프레임 선별·피사체별 확대·warp·보간·얼굴 복원은 없다. 비교 도구는 기존 CPU review UI를 최소 재사용하며 frozen runtime과 분리한다.

전신 직립/앞발 배치와 몸통 대비 국소 머리 roll을 따로 평가한다. 착석 유지 중 국소 제어가 관측돼도 전체 목표 성공으로 승격하지 않는다. Lab 유사성과 실제 개체 일치를 구분하며 숨은 부위·접촉은 UNKNOWN일 수 있다. UI 기능/ffmpeg decode PASS가 시간 품질 수용은 아니고, 실제 연속 검토가 없으면 UNVERIFIED다.

실제 code/input/condition/output hash와 자체 프로세스 종료는 완료 receipt로 확인한다. 개인 영상·사진·mask·좌표·경로는 공개하지 않는다. 수학과 코드 연결은 [학습 문서](../../lessons/B-013-cross-identity-driving.md)에 있다.

사전 고정 runtime commit: `f02896f825703a321c84127d4ef8135720176811`. CPU 검토 도구는 frozen runtime 밖에 두며 새 sampler 결과를 만들지 않는다. 비공개 A/B 패널의 대응표는 별도 JSON에 두고 관측 기록 전에는 공개하지 않는다. 같은 에이전트가 source를 본 점은 독립 인간 blind 평가와 구분한다.

실제 Lab pair는4변경/12bit-exact 보존, 각 B-012 대비는7변경/9bit-exact 보존을 확인했다. positive T5는91→108tokens, 양 Lab pair에서는 `[108,4096]` BF16으로 동일하다. 조건별 cache hash·tensor shape/dtype와 actual max_abs는 위 receipt를 따른다. 이를 출력 품질 통과로 해석하지 않는다.


## 완료된 읽기 전용 검토

공개된 CPU 검토 도구는 [output_review.py](review_code/output_review.py), [HTML template](review_code/review-template.html), [browser checker](review_code/check_review_ui.py)다. frozen runtime과 별도이며 개인 미디어나 경로를 포함하지 않는다. 실제 CPU 검토 명령은 아래 구조다. 별칭은 해당 비공개 원본 디렉터리를 가리킨다. `OUT`은 새 비어 있는 경로여야 하며, 생성 모델을 실행하지 않는다.

```sh
CUDA_VISIBLE_DEVICES='' PYTHONDONTWRITEBYTECODE=1 "$CPU_PYTHON" "$TOOLS/output_review.py" \
  "$LAB_MOV_INPUTS" "$B012_MOV_ARTIFACTS" "$B012_STILL_ARTIFACTS" \
  "$B012_OUTPUT_REVIEW" "$LAB_MOV_ARTIFACTS" "$LAB_STILL_ARTIFACTS" "$OUT"
"$BROWSER_PYTHON" "$TOOLS/check_review_ui.py" "$OUT/review.html"
```

검토 렌더는 Spark CPU에서1회 완료했다. 기존 B-012 PNG34장은 raw 양자화와 pixel 완전 일치(max_abs0)를 별도 확인하고 파일 그대로 복사했다. 새 Lab raw2개만 동일 clamp/make_grid/uint8 양자화로 PNG화했다. source/ref/기존2/신규2의 동일 canvas6열, 신규 pair4열, 기존/신규4셀, 전체17장·local0/12/14/16·A/B 그룹을 보존했다. 비교 MP4는 기존 MP4 decode 후6열 encode이며3072×928·17장·24fps·0.708333초다. warp·피사체별 확대·보간·속도 변경은 없다.

비공개 `manifest.json`은 실제 입력/output/tool SHA와 변환을 기록한다. `UI_QA.json`은 frame0/16 경계·slider·이전/다음·loop/autoplay OFF·한 번 재생 종료·desktop1280×960/mobile400×900·CJK 표시를 확인했다. 이는 연속 영상 품질 검증이 아니다.

두 blind 관측 기록을 저장한 뒤에만 mapping을 읽었다: A=LAB_STILL, B=LAB_MOV. 양쪽 전신 직립/앞발 들기는 FAIL이고, LAB_MOV의 후반 머리 반응은 심한 눈·주둥이·귀 번짐과 함께 나타나 PARTIAL이다. 깨끗한 roll·실제 개체의 후반 일치·전체 안무 성공은 수용하지 않았다. 같은 에이전트 계열의 정적 검토를 독립 인간 blind 실험이나 통계 검증으로 부르지 않으며 temporal은 UNVERIFIED다.
