# B-015 재현 계약과 읽기 전용 검토

이 문서는 이번 한정 실행의 코드·입력 연결과 명령을 기록한다. 명령 공개는 추가 sampler 승인이나 사용한 attempt 파일 삭제 허가가 아니다. 실제 실행·실패·미실행은 최종 장부와 RESULTS를 따른다.

## 고정된 부모와 환경

- `B015_ROOT`: 신규 실험 루트. 실제 개인 경로는 비공개 매핑에 있다.
- `B013_STILL`: B013의 `cases/LAB_STILL`. P 성공 코드·입력·종료 장부 및 실제 conditions/metadata/noise를 읽기 전용 재사용한다.
- `B014_ROOT`: 기존 ALG_MOV 결과·MOV 조건·filtered reference. 원본을 변경하지 않는다.
- `B007E_ROOT`: 기존 검증된 환경·upstream·가중치. 설치·다운로드·변환을 반복하지 않는다.

STILL 조건 파일 SHA는 `1e8f065e70bfef8cd723d70575a4a04f472567950a1b2d6ba0c61d189c53e87b`다. [parent binding](configs/parent_binding.json), [실제 pair 비교](PAIR_AUDIT.json), [코드 고정](PREREGISTERED_CODE.json)을 함께 검증한다. 파일 전체 SHA만으로 양 CFG의 의미상 조건 일치를 가정하지 않고 실제16leaf에서4개 변경/12개 동일을 검사한다.

B014의 MOV sidecar는 새 worker에 그대로 붙이지 않는다. 새 STILL-bound sidecar에는 생성 시각·기존 MOV metadata SHA·원래 reference/filtered 값 SHA·filter code SHA를 기록한다. 필터 값은 같지만 parent cache SHA가 다르다. `configs/allowed_gpu_processes.json`은 기존 서비스의 호스트 식별 정보라 공개 파일에서 제외하며 비공개 실행 자료에는 포함한다. 공개 manifest의 해당 SHA는 이 파일을 가리킨다.

## CPU 준비 명령

다음은 이번 새 루트에서 수행한 준비 단계다. 원본 캐시와 MOV sidecar에 쓰지 않는다. CPU preparation log와 이전 정적 진단을 보존하며 최종 검사는 CPU_VALIDATION을 따른다.

```sh
CUDA_VISIBLE_DEVICES='' "$B007E_ROOT/environment/bin/python" \
  "$B015_ROOT/code/prepare_filter.py" "$B015_ROOT"
CUDA_VISIBLE_DEVICES='' "$B007E_ROOT/environment/bin/python" \
  "$B015_ROOT/code/pair_audit.py" "$B015_ROOT"
CUDA_VISIBLE_DEVICES='' B015_ROOT="$B015_ROOT" \
  SCAIL_SOURCE="$B007E_ROOT/upstream/wan/scail.py" \
  "$B007E_ROOT/environment/bin/python" -m pytest "$B015_ROOT/code/test_alg.py" -q
CUDA_VISIBLE_DEVICES='' "$B007E_ROOT/environment/bin/python" \
  "$B015_ROOT/code/audit_parent_cache.py" "$B015_ROOT"
"$B007E_ROOT/environment/bin/python" "$B015_ROOT/code/prepare_layout.py" \
  "$B015_ROOT" "$B007E_ROOT"
```

실제 tensor 확인, sidecar 연결과 코드/config/input hash를 고정한 뒤 GitHub prereg commit을 확인하고 GPU에 진입한다. CPU fixture 성공은14B counterfactual 수치 동일성이나 영상 품질 성공을 뜻하지 않는다.

## 한정 GPU 경로

```sh
launch_recorded() {
  STAGE_NAME="$1"
  SECONDS_CAP="$2"
  STAGE_ROOT="$B015_ROOT/stages/$STAGE_NAME"
  "$STAGE_ROOT/environment/bin/python" "$STAGE_ROOT/code/runtime_launch.py" \
    "$STAGE_ROOT" "$SECONDS_CAP" /usr/bin/env \
    PYTHONDONTWRITEBYTECODE=1 CUDA_MODULE_LOADING=LAZY \
    OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
    IMAGEIO_FFMPEG_EXE=/usr/bin/ffmpeg \
    "$STAGE_ROOT/environment/bin/python" "$STAGE_ROOT/code/run_phase.py" \
    "$STAGE_ROOT" "$STAGE_NAME"
}
launch_recorded PROBE 300
# PROBE 정상 종료, 값/device 복원, 자원 회복을 확인한 뒤만 진행
launch_recorded S 7200
# 실제40step88forward와 finite final latent 저장·readback,
# S 정상 종료/PID0·자원 회복을 확인한 뒤만 진행
launch_recorded D 1800
```

각 phase 최대1회이며 어느 실패에서도 자동 재시도하지 않는다. P는0회다. worker 절대 deadline은 **2026-10-23 21:25UTC**, 전체 작업 상한22:00UTC보다 이르다. 시간 인자보다 절대 deadline이 우선한다. 기존72GiB 시작/24GiB 실행 headroom·swap0·타 서비스 보호·cgroup 제한을 유지하며 supervisor는 CUDA 객체를 갖지 않는다.

S는 tiny CUDA 실제 연산·anchor 이후 기존 mixed loader로 DiT를 적재한다. 부모 cache의 원래 device를 유지해 restore하고 CPU generator state/sigmas를 임의로 CUDA에 옮기지 않는다. 초기0..7은 u_orig/u_low/c_low, 후반8..39는 c_orig/u_orig 순서다. 예측값 CPU offload와 scheduler 계산 위치를 유지한다. filtered reference는 별도 tensor이며 원본 reference/cache를 in-place 수정하지 않는다. final latent는 마지막 update 뒤 decode 전에 저장하고 S 종료 후 D를 실행한다.

branch trace의 reference SHA는 restore 때 실제 값을 확인한 tensor와 branch 선택을 기록한다. 매 forward마다 GPU tensor 전체를 해시했다는 뜻은 아니다. prediction norm은 추가 forward 없이 계산하며 norm만으로 cosine·벡터 상쇄·조건 기여도를 추정하지 않는다.

## 읽기 전용 비교

[review_code/README](review_code/README.md)의 CLI를 사용한다. 기존3셀의 raw-derived PNG51장은 바이트 그대로 복사하고, 신규 raw만 같은 원래 정규화로 PNG화한다. 여섯 열 SOURCE/reference/CFG_MOV/CFG_STILL/ALG_MOV/ALG_STILL의 full canvas 배율과17프레임24fps를 맞춘다. 전체17장과local0/12/14/16을 포함한다. UI 재생/seek 성공은 실제 연속 재생 품질 검토가 아니다.

이미지 확대·warp·보간·프레임 선별·속도 변경·배경 수정·추가 생성은 하지 않는다. 전체 결과를 정성적2×2로 해석하며 실제 새 출력과 terminal 판정은 종료 후 RESULTS에 기록한다.

## 이번 실행의 종료 증거

PROBE/S/D 각각1회 COMPLETED·실패/재시도0, P0. 실제40step88forward와 final latent→S종료→D순서를 확인했다. [RUN_LEDGER](RUN_LEDGER.json), [실측](MEASUREMENTS.json), [품질·제한](RESULTS.md)을 함께 읽는다. 위 명령은 당시 재현 규약이지 이미 소진한 시도를 다시 실행하라는 지시가 아니다. 디코딩 재사용은 preserved final_latent 및JSON의VAE/shape/crop/FPS/model/config계약을 따른다. 초기noise/조건cache는final대체물이아니다.
