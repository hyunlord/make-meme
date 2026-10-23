# B-011 재현 계약

현재 P/PROBE/S/D는 각각 1회 **PASS**, guard wall time은 121.123/6.055/1062.421/15.219초다. 실제 출력과 전체 17장 정적 검토가 있다. 화면 변화 대응은 서술적으로 뒷받침되지만 부위 상대 운동은 **INCONCLUSIVE**, 시간 품질은 **UNVERIFIED**다. [PLAN](PLAN.md)과 [RUNNING](RUNNING.md)의 새 B-011 범위만 사용한다. B-010은 DIAGNOSTIC_INSUFFICIENT, P/PROBE/S/D 각 0회 상태로 보존한다. 이번에 허용된 sampler 1회는 소진됐으며 재시도는 0회다.

## 입력과 불변 조건

B-010에서 준비한 processed source f0 RGB, 동일 RED support+WHITE background reference mask를 사용한다. driving 17프레임과 mask는 B-009/B-010 그대로다. 512×896·24fps·seed 20261022·UniPC 40step·shift 3·CFG 5·empty negative·replace_flag=False·history=None·LoRA/enhancer OFF다. positive는 PLAN에 명시된 문장을 그대로 사용한다.

원본 512×288의 기존 확대·crop을 유지한다. 더 좋은 입력이나 seed를 찾지 않는다. STATIC COPY는 f0의 CPU 반복 대조군이며 생성물로 보고하지 않는다. 공개 설정은 자산 별칭과 해시만 사용하고 실제 경로·원본·mask·좌표는 비공개로 보관한다.

## 순서와 판정

1. 최대 30분 source-only 관측에서 실제 화면상 변화와 평가 가능한 항목을 고정한다. 보수적 반경과 반복 판독 차이는 별도다. 부위 상대 운동 불확실성만으로 탐색 A를 일괄 차단하지 않는다.
2. 실행 코드·입력·관측 계약을 사전 고정한다. 새 P에서 B-009 대비 7leaf 변경/9leaf 보존을 실제 비교한다. 기존 tolerance/exact 정책을 유지한다.
3. P 종료와 자원 회복 후 PROBE, S, D를 각각 최대 한 번 실행한다. full sampler 실패도 한 번이며 재시도는 없다. S의 최종 latent 저장·재로딩 검증과 종료 후에 D를 실행한다.
4. source / STATIC COPY / raw output 전체 17장을 같은 좌표·24fps에서 비교한다. 원본 위치 정합을 바꾸는 warp·시간 재정렬·보간을 넣지 않는다.

실제 runtime 명령 형식은 아래에 연결한다. P·CPU 조건 비교·PROBE·S·D가 완료됐으며 실제 이력은 [RUN_LEDGER](RUN_LEDGER.json)와 [MEASUREMENTS](MEASUREMENTS.json)에 있다. 전체 deadline은 2026-10-23 09:21 UTC, worker는 보수적으로 09:15 UTC를 사용한다. 종료 후 재현 명령이 남아도 추가 실행 승인이 되지 않는다. 기존 headroom·swap0·다른 작업 보호를 유지한다.

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

## 실제 종료와 산출물

사전 runtime commit은 `ee730af08a29ecfce3d0b6a243e18f04a2c64584`다. P/PROBE/S/D 각각 attempts 1/1, failed 0, retry 0이고 40step·80forward를 완료했다. 최종 latent `[16,5,112,64]` FP32 finite/readback PASS, raw `[3,17,896,512]` finite, MP4 17프레임·24fps·0.708333초 및 전체 decode PASS다. 소유 unit은 모두 inactive/MainPID0이며 남은 자체 프로세스가 없다.

- 최종 latent 파일 SHA256: `269034da7059f9aef955491de829d2fa399c34b8b705a492dba8593a1c8626b3`.
- raw 파일 SHA256: `3501d9d395609408c1e7ad9a40e537551d43a35bea0be7fe0e371770dedc18ed`.
- MP4 SHA256: `3dbad6c70ed39636c9bfb47b7865c84b806600815a017d7742009148101ab11c`.

파일 hash와 tensor value hash는 다른 대상이다. 정확한 값 hash·조건 hash·크기는 RUN_LEDGER를 따른다. S 최소 MemAvailable 56,757,710,848 bytes, cgroup peak 66,577,969,152 bytes, CUDA peak 36,325,965,824 bytes는 서로 다른 회계다. high 이벤트 3357, OOM 0, swap 0이며 메모리 합산이나 품질 수용으로 해석하지 않는다. 생성물의 외형·움직임은 아래처럼 별도 제한을 붙여 판정했다.

## 실제 출력 평가와 해석 범위

[OUTPUT_EVALUATION](OUTPUT_EVALUATION.json)은 고정 25개 위치/20개 변위를 모두 유지한다. 머리 15위치는 VISIBLE, 앞발 10위치는 UNCERTAIN이며 8개 불확실한 변위도 집계에서 제외하지 않았다. E_copy 평균 16.5407px, E_gen 평균 3.5212px, 출력 변위 평균 17.0948px다. 머리는 18.0420→2.2804px, 앞발은 14.2887→5.3823px다. 이 raw 수치 감소는 output uncertainty NOT_CALIBRATED 상태의 기술 통계이며 보정된 우월성·신뢰구간·개선율이 아니다.

전체 17장 정적 시각 검토는 작은 source 방향·크기 변화와 큰 형상 붕괴의 부재를 뒷받침한다. 수준 A는 서술적 화면 변화 대응, B articulation은 INCONCLUSIVE, gain은 UNDEFINED다. STATIC COPY 비교만으로 driving 조건 사용의 인과성을 입증하지 않는다. 실제 연속 재생은 관찰하지 않았으므로 temporal UNVERIFIED다. Lab 전이·접촉·일반화 수용으로 확대하지 않는다.

이번 한 번의 생성 비교는 종료됐다. 다음에는 기존 원본 중 더 명확한 움직임을 가진 짧은 구간을 source-only로 고르는 후속 실험만 제안하며, 여기서는 추가 생성·구간 변경을 실행하지 않는다.
