# B-012 재현 계약

source [7,24) 선정과 양 P·pair 비교는 **PASS**다. MOV/STILL 각각 P/PROBE/S/D 1회가 완료됐다. 후반 머리 roll에 대한 MOV의 유용한 대응 근거가 관측됐으며 시간 품질은 UNVERIFIED다. [PLAN](PLAN.md)의 MOV/STILL 각각 1회, 실패 포함 full sampler 최대 2회·retry 0 경계를 유지한다. B-011 사용1회와 B-010 사용0회는 보존한다.

## 입력 고정

기존 원본에서 최대 3개의 연속 17프레임 후보를 source-only로 검토하고 최초 적합 구간을 고정한다. 선택 구간은 [7,24)이며 실제 근거는 [SOURCE_SELECTION](SOURCE_SELECTION.md)과 [사전 평가](PREREG_EVALUATION.md)에 있다. 512×896·24fps·동일 crop을 유지하며, reference는 선택 구간 첫 processed RGB다.

MOV는 실제 17장 RGB+대응 mask, STILL은 RGB f0+mask f0의 17장 반복이다. STATIC COPY는 생성 없이 f0를 반복한 별도 출력이다. reference mask는 동일 f0 RED support+WHITE 배경이고 prompt도 두 조건에 동일하다. 같은 source 개체를 묘사하며 과거 Lab prompt/cache를 재사용하지 않는다.

## 조건·실행 검사

seed20261022·UniPC40·shift3·CFG5·negative empty·replace_flag=False·history=None·LoRA/enhancer OFF, 기존 pinned SCAIL/weights/FlashAttention/mixed loader/64-byte CUDA anchor 경로를 유지한다. 조건별 새 P가 실제 17장 영상을 encode한다. STILL latent를 MOV 첫 slice 반복으로 만들지 않는다.

양 CFG의 pose_latents/driving_masks 4leaf는 변경 기대, 나머지 12leaf는 보존 계약이다. 실제 noise bytes/shape·RNG·timesteps/sigmas를 비교했다. float tolerance와 exact 정책을 사전 고정하고 observed exact 여부도 기록한다. 조건 비교 실패는 sampler 전에 중단한다. 출력 품질이 나쁘다는 이유로 안전한 둘째 대조군을 생략하거나 추가 retry하지 않는다.

조건마다 P→조건 비교→PROBE→S→D의 기존 분리 경로를 사용하며 GPU-heavy 실행은 순차다. final latent 저장·재로딩 검증과 S 종료·자원 회복 뒤 D를 실행한다. D 실패가 S 재실행 권한이 되지 않는다. 실제 stage 경로·명령 형식은 아래와 같고 [RUN_LEDGER](RUN_LEDGER.json)가 완료 이력이다.

## 평가·종료

SOURCE / STATIC COPY / MOV / STILL의 17장 전체와 사전 이벤트를 같은 24fps로 비교한다. 움직임 양이 아닌 source 대응을 보고 부위 관측 불확실성·coverage를 유지한다. 출력별 warp·zoom 보정·시간 이동·보간은 없다. 실제 연속 시청이 없으면 temporal UNVERIFIED다.

실제 결과·hash·자원·소유 프로세스 종료는 완료 receipt로 확인한다. 공개에는 비민감 코드·집계·자산 별칭만 남기고 실제 원본·mask·조건cache·latent·개인 경로는 공개하지 않는다. [학습 문서](../../lessons/B-012-driving-information.md)는 STATIC COPY와 STILL, 시간 압축 및 공동 driving 개입의 의미를 설명한다. 이 문서는 추가 생성이나 다음 실험의 자동 실행 승인이 아니다.

## 실제 P pair 근거

고정 runtime commit은 `8e80bdc`다. [CONDITION_COMPARISON](CONDITION_COMPARISON.json)에서 4 changed/12 bit-exact control PASS, 동일 positive `[91,4096]` BF16을 확인했다. MOV cache SHA256은 `715099fba103415f48138669d72e1da650215dcb275171f119cdf884402e11ad`, STILL은 `86f143e450c38c8a3457b335cd3cb2ad5c58256d87cf1152e521e8b8eb138734`다. `[16,5,112,64]` FP32 noise와 RNG/schedule은 동일하다. 허용 float rtol1e-5/atol1e-6과 exact mask/noise 정책을 유지했으며 12개 control의 실제 차이는 모두0이었다. 실제 실행은 양 조건 40step·80forward, finite final latent readback와 decode까지 완료됐다.

## 실행·검토 명령과 보존

고정 runtime commit은 `8e80bdcfb9351bde5960cea4655f95ffaf22e98b`다. 아래는 실제 사용한 인터페이스를 경로 별칭으로 표현한다. 이미 소진된 2회 예산을 재실행하는 지시가 아니다. `CASE`는 MOV/STILL, `STAGE`는 P/PROBE/S/D이며 `SECONDS_CAP`은 각각 1800/300/7200/1800이었다. 실제 worker deadline은 2026-10-23 17:10 UTC, 전체 작업 deadline은 17:19 UTC다. 두 P·pair 검증 후 각 조건 PROBE/S/D를 순차 실행했다.

```sh
STAGE_ROOT="${RUN_ROOT}/cases/${CASE}/stages/${STAGE}"
"${STAGE_ROOT}/environment/bin/python" \
  "${STAGE_ROOT}/code/runtime_launch.py" "${STAGE_ROOT}" "${SECONDS_CAP}" \
  /usr/bin/env PYTHONDONTWRITEBYTECODE=1 CUDA_MODULE_LOADING=LAZY \
  OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  IMAGEIO_FFMPEG_EXE=/usr/bin/ffmpeg \
  "${STAGE_ROOT}/environment/bin/python" \
  "${STAGE_ROOT}/code/run_phase.py" "${STAGE_ROOT}" "${STAGE}"
```

실제 guard 시간(P/PROBE/S/D)은 MOV 119.013/6.059/1102.221/16.189초, STILL 97.792/5.078/1055.610/15.171초다. 두 raw `[3,17,896,512]`와 MP4 17장·24fps·17/24초를 보존했다. sample 시각은 local0~16/24초이며 원본 index7~23이다. final latent `[16,5,112,64]` FP32 finite/readback 후 D에서 decode했다. 최종 latent 파일 SHA는 MOV `7f407b8d2acf3c8b8b30d73732676be7ac9a7c964e0646f477c70b98f63f177d`, STILL `bb1ab69a6684d8d25f515da78664f60403be279eb790bd7f43798cfca2e53971`다. 전체 파일 해시·자원 회계는 RUN_LEDGER/MEASUREMENTS를 따른다.

후처리 소스 [review_tools](review_tools/output_review.py)는 frozen runtime과 별도다. 모델 실행 코드를 바꾸지 않으며 신규 의존성 설치가 없다. 기존 Spark Python에서 CPU 렌더를 실제 실행했다. `REVIEW_TOOLS`는 이 세 도구의 디렉터리, `PYTHON`은 기존 torch/torchvision 환경이다.

```sh
CUDA_VISIBLE_DEVICES='' PYTHONDONTWRITEBYTECODE=1 "$PYTHON" \
  "$REVIEW_TOOLS/output_review.py" \
  "$RUN_ROOT/cases/MOV/inputs" "$RUN_ROOT/cases/MOV/inputs/driver" \
  "$RUN_ROOT/cases/STILL/artifacts" "$RUN_ROOT/cases/MOV/artifacts" \
  "$RUN_ROOT/reports/output-review"
```

양 raw는 `weights_only=True` CPU load와 동일 upstream clamp/make_grid로 PNG 변환했다. 영상 비교는 양 MP4 decode 후 같은 24fps로 4열 인코딩한다. 따라서 PNG와 영상의 압축 경로 차이를 manifest에 기록한다. source 첫 PNG와 MOV decoded f0가 같은지 검사한다. all17·group 시트, 사전 이벤트 `[0,12,14,16]` selected 시트, 대칭 MOV/STILL 전체 시트를 남긴다. 피사체별 확대·warp·보간·시간 변경은 없다.

```sh
"$BROWSER_PYTHON" "$REVIEW_TOOLS/check_review_ui.py" \
  "$RUN_ROOT/reports/output-review/review.html"
```

기존 Mac Playwright/Chrome로 실제 버튼·slider0..16·경계·1×재생 종료·loop/autoplay false·오류0·모바일 overflow0를 확인했다. desktop/mobile 스크린샷도 직접 확인했다. UI_QA.json의 기능 PASS는 영상 시간 품질 PASS가 아니다. review 산출물과 도구는 양 호스트에 복사했으며 개인 미디어는 공개하지 않는다.

## 최종 해석과 다음 하나

전체 17장의 정적 검토에서 MOV는 local14→16 후반 머리 roll의 방향·순서를 따라갔고 STILL은 초기 자세 부근에 머물렀다. 이 입력의 동적 RGB+mask 공동 기여에 대한 탐색적 근거이며 RGB 단독 인과 효과나 일반화는 아니다. 후반 MOV 얼굴·귀·주둥이의 흐림/형태 차이와 mask PARTIAL을 유지한다. 정밀 앞발·3D접촉·Lab 전이는 미수용, 실제 연속 시청이 없어 temporal UNVERIFIED다.

다음 제안은 같은 [7,24)의 Lab cross-identity 한 가지이며 NOT_RUN이다. 이번 2회 생성 이후 자동 실행하지 않는다.
