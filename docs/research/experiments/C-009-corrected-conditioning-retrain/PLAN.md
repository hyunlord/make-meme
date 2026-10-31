# C-009 PLAN — 흰 마스크 조건 cache 재생성 · 동일 설정 재학습 · 생성 비교

- experiment_id: C-009-corrected-conditioning-retrain
- 작성: 2026-10-31, GPU 실행 전 커밋
- parent: C-008 ecaa65356ede3a1c4e6a0d0c546e2de61f88c821 / C-006 c4aef32 / C-007 19e1104
- 의뢰서: [work_orders/C009_CORRECTED_CONDITIONING_RETRAIN_KO.md](../../work_orders/C009_CORRECTED_CONDITIONING_RETRAIN_KO.md)

## 질문
`vace_context`만 흰 마스크로 정상화하고 같은 초기 상태·자료·설정으로 256회 재학습하면 C-006/C-007의 회귀가 줄어드는가? 줄어든다면, 화면 손상 감소를 넘어 실제 궤적 제어 이득이 있는가?

## 변경 / 고정
- 변경: 13개 cache(`cache-v2` 12개 + `cross-cache` dog)의 `vace_context` 키 하나. 새 이름공간 `cache-white/`, `cross-cache-white/`와 `CACHE_MANIFEST.json`(mask_contract `white_v1`, 파일 sha, legacy sha).
- 고정: 나머지 key/tensor 전부(byte 비교), adapter 구조, split, exclusions, TRAIN_CONFIG, 생성 설정, guard.
- 기존 cache-v2·cross-cache·train-v2 checkpoint는 읽기 전용이다.

## 단계와 코드 (`code/`)
1. `rebuild_cache.py`: 원래 payload를 `weights_only` torch.load로 읽는다(load_cache와 exclusion은 쓰지 않음).
   - 11개 자료는 흰 마스크로 재인코딩한다(22 encode). 인코딩 직전에 33×240×416×3 uint8, R=G=B, 양끝 0, 중간 255, 정규화 후 0/1·채널 동일을 검사한다.
   - elephant/goat는 C-008 `cache-fixed`의 `vace_context`를 재사용한다. 단, C-008 PARITY의 파일 sha가 맞아야 한다. 그 파일의 추가 key `c008_provenance`는 옮기지 않는다.
   - `vace_context` 외 key 집합, tensor shape/dtype/byte, 비tensor 값이 원본과 같은지 검사하고, 원자 저장 후 readback한다.
2. live parity: C-008 `encode_probe.py`를 G 모드로 elephant·goat에 다시 실행한다(4 encode). 결과를 새 cache와 비교하고, elephant는 C-007 저장 context와도 비교한다. 기대값은 exact이며 tolerance는 늘리지 않는다.
3. `train_white.py`: CACHE_MANIFEST의 white_v1 계약과 모든 파일 sha를 확인한다. legacy sha가 하나라도 있으면 즉시 실패한다. 그 뒤 **원본 C-006 `train_adapter.py`를 수정 없이** 실행한다.
   - config는 train-v2와 같고, 다른 것은 `cache_root`, `output`, `deadline_epoch`뿐이다.
   - `adapter_checkpoint` = C-006 `outputs/train/checkpoint-000.pt`. train-v2도 이 파일에서 resume했다(adapter·optimizer·CPU/CUDA RNG·generator·order·cursor·counts 복원).
   - 생성되는 C-009 step000을 train-v2 step000과 CPU에서 비교한다.
   - updates.jsonl의 step/clip/grid_index/null/negative_text를 train-v2와 비교한다.
4. `probe_white.py`: elephant/goat × C-007 probe_grid 5σ × positive/negative × {BASE, OLD_ON_256(train-v2), NEW_ON_256} = 60 forward. 입력은 white context, C-007 noise seed 20261101+clip_index.
5. `gen/generate_video.py`: C-007 사본에 NULL(C-006 `make_null`)만 추가했다. NEW_ON CFG1, NEW_ON CFG5, NEW_NULL CFG5 영상 3개를 만든다.
   - 입력: elephant, C-007 sidecar(clean_latent 없음), 같은 prompt/seed/Euler50/shift5.
   - 첫 model_fn의 vace_context·latents sha를 새 white cache와 C-007 BASE1/BASE5 기록과 대조한다. 맞으면 BASE를 재사용한다.
6. 검토 뷰어, 문서, 전달.

## 판정
- 계산 판정: WHITE_MASK_CONTRACT_VERIFIED, CACHE_REBUILD_COMPLETE, NONCONTEXT_FIELDS_UNCHANGED, CACHE_LIVE_PARITY_VERIFIED, INIT_PARITY_VERIFIED, TRAIN_SCHEDULE_MATCHED, TRAIN_COMPLETE_256, CHECKPOINT_RELOAD_VERIFIED, MATCHED_GENERATION_COMPLETE.
- 품질 판정: 의뢰서 12–13절의 A/B/C/D 비교, 그리고 CONDITION_FIX_REDUCES_DAMAGE / OBSERVED_TRAJECTORY_GAIN / COMMON_ADAPTER_GAIN_ONLY / TRADE_OFF / NO_ESTABLISHED_GAIN / INCONCLUSIVE.
- 최종 checkpoint는 256(마지막 완료분)이며 결과를 보고 고르지 않는다.

## 예산
cache·prepare encode ≤30, 학습 256 update(active ≤9000s), probe 60 forward, sampler 3(+BASE 복구 2, 기계 복구 1, 상한 6), decode 복구 ≤1. 전체 4시간. 품질 재시도 0, seed 탐색 0.
