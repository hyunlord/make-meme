# C-010 PLAN — 정상 조건 adapter의 궤적 신호 전달·보정 방향 진단

- experiment_id: C-010-trajectory-signal-diagnostics
- 작성: 2026-10-31, GPU 실행 전 커밋. 단계 A(CPU, 입력만 사용)는 이 PLAN 작성 전에 실행했다. 그 결과는 아래 "입력 고정"에 그대로 옮겼다.
- parent: C-009 fbb07f11af7da0d81b7c72e951ac90e93b1d8189
- 의뢰서: [work_orders/C010_TRAJECTORY_SIGNAL_DIAGNOSTIC_KO.md](../../work_orders/C010_TRAJECTORY_SIGNAL_DIAGNOSTIC_KO.md)

## 고정 계약
- checkpoint: **C-009 white** `train-white/checkpoint-000/128/256`. sha는 비공개 config에 고정하고 실행 시 검증한다. C-006 red checkpoint는 쓰지 않는다.
- cache: C-009 `cache-white`(white_v1 manifest 확인). load_cache로 exclusion을 사본에만 적용한다.
- 사례: bear, dance-twirl (train), elephant, goat (validation).
- σ: C-007 probe_grid의 0.95 (index 208), 0.50 (833), 0.05 (990). 1000-step grid, shift5.
- noise seed (CPU generator): elephant 20261101, goat 20261102 (C-007 규칙), bear 20261201, dance-twirl 20261202 (이번에 고정).
- positive text만 사용한다. z_σ = add_noise(z0, ε, t), u* = training_target (설치된 scheduler 그대로).
- 코드: `code/signal_common.py`, `code/input_contrast.py`(단계 A), `code/diagnose_signal.py`(B–E + 선택 rollout).
  - adapter 내부 관측은 `adapter_trace` 사본으로 한다. 원본 출력과 `torch.equal`인지 매 호출 assert한다.
  - block 관측은 `observed_forward` 사본으로 한다. 원본 adapted_forward와 4회 대조하고, 반복 바닥 2회를 잰다.

## 입력 고정 (단계 A 결과, GPU 전)
| 사례 | 공통 가시 중간 점·프레임 | ON–NULL 위치 차 평균/중앙/p90 (px) | NULL에서만 gate | FD track |
|---|---|---|---|---|
| bear | 380 | 7.0 / 4.8 / 15.8 | 122 | 0 |
| dance-twirl | 105 | 23.8 / 17.4 / 62.6 | 343 | **없음 → FD_NOT_AVAILABLE** |
| elephant | 315 | 3.7 / 2.4 / 7.7 | 93 | 6 (주의: 시트상 코끼리 몸이 아닌 발 근처 물줄기/지면 점으로 보임. 규칙대로 유지) |
| goat | 227 | 14.3 / 14.6 / 20.5 | 149 | 1 |

ON에서만 gate인 점은 0이다. NULL은 양끝이 보이면 중간을 전부 visible로 둔다. patch·anchor_valid·kernel box는 ON/NULL이 같다(단계 A에서 확인).

## 단계와 예산 (full forward)
- 단계 B: adapter-only 72 + FD용 소수 호출(기록).
- 단계 C main: 84 = 12 probe × (native, bypass, zero000, 128 ON/NULL, 256 ON/NULL).
- observer OFF 4 (bear/elephant σ0.5 256 ON/NULL), 반복 2 (bear/elephant σ0.5 256 ON).
- 단계 D 기울기: 16 forward + 16 VJP (σ0.5/0.05 × ON/NULL × 4 사례, ckpt256). optimizer는 만들지 않는다.
- 단계 E FD: dance-twirl을 뺀 3사례 × {4,8}px × ± = 12.
- 선택 rollout: C-009 NEW_ON_5 trace에 저장된 pre-step latent 중 σ에 가장 가까운 상태 최대 3개 × BASE/ON256/NULL256 = 9.
- 정상 합계 예정 127 (상한 131, 예비 8). 학습·sampler·VAE·다운로드는 0이다.

## 사전 고정한 판정 규칙
모든 상대 차이는 **같은 경계 안**의 `rel_diff = RMS(ON−NULL) / mean(RMS(ON), RMS(NULL))`로 잰다. support는 gate & r² ≤ 9 합집합이다. 아래 기준은 ckpt256에서 네 사례 중 **3개 이상**이 만족할 때만 그 판정을 낸다.

1. **INPUT_CONTRAST_LIMITED**: P1(gated points) rel_diff < 0.01.
2. **FEATURE_ATTENUATION_OBSERVED (집계)**: P5 support rel_diff < 0.25 × P2 gated rel_diff, 그리고 η < 0.5.
3. **PROJECTION_INSENSITIVE**: P6 block26 support rel_diff < 0.25 × P5 support rel_diff.
4. **EFFECTIVE_UPDATE_ROUNDING_OBSERVED**: block26에서 실효/의도 RMS < 0.5, 또는 nonzero 중 hidden 불변 비율 > 0.5.
5. **READOUT_INSENSITIVE_AT_PROBES**: block26 h_plus의 support rel_diff 대비 최종 예측 ON–NULL 상대 차이(= RMS(v_ON−v_NULL)/RMS(v_BASE))가 0.1배 미만.
   - 다른 공간의 비교이므로 이 기준은 경고와 함께 쓴다.
6. **MISALIGNED_CORRECTION**: σ별 `<δ, e_B>_W` 가중 cosine(ON vs BASE)이 대부분 ≤ 0.02이고, ON vs NULL의 loss 차이가 0 이상(ON이 NULL보다 낫지 않음).
7. **TRAIN_VALIDATION_GAP**: train 두 사례에서는 ON이 NULL보다 loss가 낮은데(L_ON−L_NULL < 0) validation 두 사례에서는 그렇지 않음.

## 다음 변경 하나 고르기 (실행 금지, 제안만)
신호 사슬의 앞에서부터 처음으로 만족한 감쇠 판정(1→2→3→4→5)을 병목 후보로 하나 고른다. 의뢰서 13절 표에서 그에 대응하는 변경 하나를 제안한다.
- 감쇠 판정이 없고 6만 성립하면 → 목적함수·조건 중복(동적 윤곽이 같은 정보를 이미 줌) 검토.
- 아무것도 성립하지 않으면 → DIAGNOSTIC_INCONCLUSIVE와 우선 가설 하나.

반증 조건: 고른 후보마다 "다음 실험에서 어떤 수치가 나오면 이 선택이 틀렸는가"를 RESULTS에 적는다.

## 금지
optimizer·학습·scale/위치/kernel/precision/loss 변경, sampler, VAE, imagegen/SAM/CoTracker, 다운로드, guard 변경.
