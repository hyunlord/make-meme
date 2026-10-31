# C-008 RESULTS — 조건 인코딩 불일치 규명 (2026-10-31)

## 답
1. **최초로 달라진 곳**: C-006 `cache_conditions.py:56`이 만든 생성 마스크 PIL 이미지의 채널 1·2.
   `Image.new('RGB', size, 255)`는 (255,0,0)이다. 이것이 `WanVideoUnit_VACE.process`의 채널별 `X·(1−M)`/`X·M`에 들어가
   inactive/reactive branch 입력이 달라졌다. 조건 RGB, 마스크 채널0, VAE 상태·적재·dtype·실행 모드·tile은 모두 같았다. → [ROOT_CAUSE](ROOT_CAUSE.md)
2. **확인한 단일 개입**: 마스크 fill만 `(v,v,v)`로 바꿨다. C와 G가 elephant·goat에서 bit-exact로 일치했고, 되돌리면 불일치가 재현됐다.
3. **최소 수정**: C-008 `encode_probe.py`의 `generation_mask(t, 'white')`와 회귀 테스트 `test_generation_mask.py`. C-006 원본 코드와 cache는 역사 자료로 그대로 두었다.
   이후 cache를 재생성할 때는 이 fill을 쓴다. site-packages·DiffSynth는 수정하지 않았다.
4. **독립 일치**: 수정 C(T5+VAE만 적재)와 G(전체 1.3B 적재, 실제 `pipe(...)` 준비 경로)를 서로 다른 guard 프로세스에서 실행했다.
   elephant·goat 모두 **PARITY_EXACT**이며 max_abs는 0이다. 같은 경로의 반복 실행도 exact다.
5. **같은 오류로 맞춘 게 아닌 근거**: 기준은 공식 helper가 만든 G 마스크(흰색, 모든 채널 동일)다.
   VACE 마스크는 픽셀 단위 스칼라라는 계약이고, mask latent도 채널0만 읽는다.
   두 경로는 VAE를 공유하므로 VAE 자체는 R 검사로 확인했다. 첫 프레임 단독 encode는 전체 encode의 t0와 같고, prefix5는 t0..1과 같다.
   프레임 17~32를 검게 바꿔도 t0..4는 exact로 불변이고, t5..8만 변한다. 따라서 causal 시간 cache가 과거만 보고 미래는 새지 않는다. → **ENCODER_SEMANTICS_VERIFIED** (두 validation, 단일 tile 조건)
6. **영향**: 조건 cache의 `vace_context`만 잘못됐다. clean target latent, endpoint latent·patch, T5, loss_mask는 영향이 없다 (두 validation에서 exact로 직접 검증, 나머지는 같은 경로라서 추정).
   cross-ID dog cache는 같은 코드라서 영향을 받는다. → [AFFECTED_ARTIFACTS](AFFECTED_ARTIFACTS.json)
7. **checkpoint 재사용**: train-v2 checkpoint 128/256은 생성 시 한 번도 주어지지 않는 조건에서 학습됐다.
   기술적으로는 로드·실행되지만 방법의 유효성 평가에는 쓸 수 없다 → **RETRAIN_REQUIRED**. checkpoint-000(초기값)은 무관하다.
8. **재생성 범위**: 12개 cache-v2와 cross-cache의 `vace_context`(encode 26회, 그중 validation 2개는 완료)를 재생성한 뒤,
   같은 초기화·분할·TRAIN_CONFIG로 재학습하고 C-007 probe/생성을 다시 해야 한다. → [REBUILD_MANIFEST](REBUILD_MANIFEST.json)
9. **남은 adapter 회귀**: C-006/C-007의 ON/NULL 색 번짐·중복 윤곽과 낮은 sigma 회귀는 지금으로서는 조건 shift(학습=빨강 마스크, 생성=흰 마스크)와 분리할 수 없다.
   조건을 맞춘 재학습 전에는 adapter 구조·목표·CFG 탓으로 돌리지 않는다. 재학습 후에도 회귀가 남을 수 있으며, 그것은 그때 별도로 판정한다.

## 판정
| 항목 | 값 |
|---|---|
| MISMATCH_REPRODUCED | ✅ elephant (C_old·G_old 둘 다 현재 코드로 exact 재현), goat 추가 재현 |
| FIRST_DIVERGENCE_LOCALIZED | ✅ P0 마스크 채널1·2 → P2 branch 입력 |
| ROOT_CAUSE | CONFIRMED |
| PARITY | EXACT (elephant, goat; 서로 다른 프로세스) |
| ENCODER_SEMANTICS | VERIFIED (두 validation, 단일 공간 tile) |
| TRAIN_ARTIFACTS | REBUILD_REQUIRED (vace_context만) |
| FROZEN_CHECKPOINT_REUSE | RETRAIN_REQUIRED |
| 분기 | B — 학습 cache 오류 |

## 미실행
- 분기 A의 영상 2개: **NOT_RUN**. 분기 B이므로 해석하기 어려운 영상은 만들지 않았다.
- 선택적 one-step 재평가 (≤40 forward): **NOT_RUN**. checkpoint가 잘못된 조건에서 학습됐으므로, 수정 입력에 넣은 결과는 재학습 여부 판단에 정보를 더하지 않는다고 봤다.
- 진단용 decode: 0회. train 8개와 test cache는 재인코딩하지 않았다 (추정 범위로 표시).
- temporal 품질: 새 영상이 없으므로 해당 없음.

## 비용
public VAE encode 29회 / 64, decode 0, DiT forward 0, 학습 0, 다운로드 0. heavy stage 4개 합계 약 78초. 가드 변경 없음, 모든 stage COMPLETE. → [COSTS](COSTS.json)

## 다음 한 가지
`vace_context`만 고친 cache로 C-006 train-v2를 같은 설정에서 재학습하고, C-007 validation probe와 elephant BASE/ON을 다시 비교한다 (별도 승인 필요).
