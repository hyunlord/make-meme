# B-011 재현 계약

현재 P는 **PASS**(121.123초), PROBE는 **PASS**(6.055초), S sampler는 **RUNNING**이다. 출력은 **NOT_AVAILABLE**, D와 출력 품질 검토는 **NOT_RUN**이다. [PLAN](PLAN.md)과 [RUNNING](RUNNING.md)의 새 B-011 범위만 사용한다. B-010은 DIAGNOSTIC_INSUFFICIENT, P/PROBE/S/D 각 0회 상태로 보존한다. S 완료와 D 실행은 아직 주장하지 않는다.

## 입력과 불변 조건

B-010에서 준비한 processed source f0 RGB, 동일 RED support+WHITE background reference mask를 사용한다. driving 17프레임과 mask는 B-009/B-010 그대로다. 512×896·24fps·seed 20261022·UniPC 40step·shift 3·CFG 5·empty negative·replace_flag=False·history=None·LoRA/enhancer OFF다. positive는 PLAN에 명시된 문장을 그대로 사용한다.

원본 512×288의 기존 확대·crop을 유지한다. 더 좋은 입력이나 seed를 찾지 않는다. STATIC COPY는 f0의 CPU 반복 대조군이며 생성물로 보고하지 않는다. 공개 설정은 자산 별칭과 해시만 사용하고 실제 경로·원본·mask·좌표는 비공개로 보관한다.

## 순서와 판정

1. 최대 30분 source-only 관측에서 실제 화면상 변화와 평가 가능한 항목을 고정한다. 보수적 반경과 반복 판독 차이는 별도다. 부위 상대 운동 불확실성만으로 탐색 A를 일괄 차단하지 않는다.
2. 실행 코드·입력·관측 계약을 사전 고정한다. 새 P에서 B-009 대비 7leaf 변경/9leaf 보존을 실제 비교한다. 기존 tolerance/exact 정책을 유지한다.
3. P 종료와 자원 회복 후 PROBE, S, D를 각각 최대 한 번 실행한다. full sampler 실패도 한 번이며 재시도는 없다. S의 최종 latent 저장·재로딩 검증과 종료 후에 D를 실행한다.
4. source / STATIC COPY / raw output 전체 17장을 같은 좌표·24fps에서 비교한다. 원본 위치 정합을 바꾸는 warp·시간 재정렬·보간을 넣지 않는다.

실제 runtime 명령 형식은 아래에 연결한다. P·CPU 조건 비교·PROBE는 완료됐으며 S 완료와 D 실행 이력은 후속 receipt로 확인해야 한다. 전체 deadline은 2026-10-23 09:21 UTC, worker는 보수적으로 09:15 UTC를 사용한다. 종료 후 재현 명령이 남아도 추가 실행 승인이 되지 않는다. 기존 headroom·swap0·다른 작업 보호를 유지한다.

## 제출 판정

실행 완료와 화면상 변화 A, 부위 상대 운동 B, 외형 및 관측 불확실성을 분리한다. 실제 출력이 없으면 품질 NOT_RUN, 연속 재생을 보지 못하면 temporal UNVERIFIED다. Lab·cross-identity·전체 춤·Kling 수용은 이번에 수행하지 않는다. 수식과 측정의 의미는 [학습 문서](../../lessons/B-011-measurement-and-generative-diagnostics.md)에 정리한다.

## 실제 P와 실행 인터페이스

[CONDITION_COMPARISON](CONDITION_COMPARISON.json)은 7개 예상 변경과 9개 bit-exact control 보존을 확인했다. positive `[27,4096]` BF16, noise `[16,5,112,64]` FP32를 포함한 실제 shape와 입력 hash를 기록한다. 새 cache SHA256은 `2af5acb5e3835e1e3f23609dcf83a326980818075aff3c11c36cbd5a095583cb`다. P를 다시 실행해 사용 기록을 초기화하지 않는다.

고정 [runtime_launch.py](code/runtime_launch.py)와 [run_phase.py](code/run_phase.py)의 명령 형식은 아래와 같다. `RUN_ROOT`는 비공개 경로 매핑, `STAGE`는 `P`, `PROBE`, `S`, `D` 중 해당 단계다. 각 단계는 별도 `stages/<STAGE>`에서 한 번만 예약되며 앞 단계 종료·검증·자원 회복이 선행한다. 명령 형식이 후속 실행 승인은 아니다.

```sh
STAGE_ROOT="${RUN_ROOT}/stages/${STAGE}"
"${STAGE_ROOT}/environment/bin/python" \
  "${STAGE_ROOT}/code/runtime_launch.py" "${STAGE_ROOT}" "${SECONDS_CAP}" \
  /usr/bin/env PYTHONDONTWRITEBYTECODE=1 CUDA_MODULE_LOADING=LAZY \
  OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  IMAGEIO_FFMPEG_EXE=/usr/bin/ffmpeg \
  "${STAGE_ROOT}/environment/bin/python" \
  "${STAGE_ROOT}/code/run_phase.py" "${STAGE_ROOT}" "${STAGE}"
```

P 다음 CPU 조건 비교는 stage root가 아닌 experiment root를 받는다. 실제 완료된 비교의 재실행을 요구하지 않는다.

```sh
/usr/bin/env CUDA_VISIBLE_DEVICES='' PYTHONDONTWRITEBYTECODE=1 \
  "${RUN_ROOT}/environment/bin/python" \
  "${RUN_ROOT}/code/compare_conditions.py" "${RUN_ROOT}"
```

모든 cap은 [runtime_guard.py](code/runtime_guard.py)의 09:15 UTC 절대 deadline에 의해 추가 제한된다. 고정 환경·가중치·입력은 별도 로컬 준비물이 필요하며 공개 문서만으로 개인 자산이 제공된다고 주장하지 않는다.
