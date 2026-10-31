# C-011 PLAN — 동적 윤곽 제거(endpoint-only) 조건에서의 동일 재학습

- experiment_id: C-011-endpoint-only-trajectory-ablation
- 작성: 2026-11-01. 새 수치 분석·VAE·GPU 실행 전에 커밋한다.
- parent: C-010 33255333bd608b73bc44ffae4ebc7e29ce870a77 / C-009 fbb07f11af7da0d81b7c72e951ac90e93b1d8189 / C-008 ecaa65356ede3a1c4e6a0d0c546e2de61f88c821 / C-006 c4aef32 / C-007 19e1104
- 의뢰서: [work_orders/C011_ENDPOINT_ONLY_TRAJECTORY_ABLATION_CLAUDE_KO.md](../../work_orders/C011_ENDPOINT_ONLY_TRAJECTORY_ABLATION_CLAUDE_KO.md)

## 한 가지 변경
VACE 중간 조건 RGB(프레임 1–31)를 동적 윤곽에서 **(127,127,127) 회색**으로 바꾼다.

| 계열 | 중간 RGB | 고정 요소 | 학습 |
|---|---|---|---|
| L | 동적 윤곽 | | C-009 white cache, C-009 ckpt256 |
| E | gray127 | | C-011, 같은 step000에서 새로 256 update |

두 계열이 공유하는 고정 요소: 양끝 = source 0/32(= anchors, byte 동일 확인), 흰 마스크 G, prompt·negative.

나머지는 모두 고정한다: adapter, loss, scale, point 자료, exclusion, optimizer, seed, 학습량, 생성 설정.

## 코드 (`code/`)
- `rebuild_endpoint_cache.py`: C-009 white cache 10개(train8 + validation2)에서 `vace_context`만 E로 바꾼다.
  - 인코딩 직전에 검사한다: 중간 127 전 채널, 앵커 byte, 마스크 3채널, 정규화 마스크 0/1.
  - L 대비 검사한다: inactive exact, mask64 exact, reactive는 달라야 함.
  - 나머지 key는 byte 단위로 보존한다.
  - manifest: `condition_family=endpoint_gray127_v1`, L 부모 manifest sha. `legacy_sha256`에 L 부모 파일 sha를 넣어, 학습이 L cache를 읽으면 C-009 wrapper가 거부하게 한다.
  - encode 20회.
- `live_parity_endpoint.py`: C-009 `gen/generate_video.py`의 `condition()`(endpoint, layout_dir=None)과 C-008 prepare-only runner로 elephant·goat를 독립 인코딩한다(encode 4회). E cache와의 exact를 기대한다.
- `train_endpoint.py`: `condition_family`를 확인한 뒤 C-009 `train_white.py`(white_v1·sha·legacy 거부) → C-006 `train_adapter.py`(수정 없음) 순으로 넘긴다.
  - config는 C-009 `train-white.json`에서 `cache_root`/`output`/`deadline_epoch`만 바꾼다.
  - resume은 C-006 `outputs/train/checkpoint-000.pt`에서 한다(C-009와 같은 step000 파일).
  - 끝나면 C-009 `train_replay_check.py`로 step000과 256행 schedule을 대조한다.
- `probe_families.py`: 72 forward + 16 gradient(아래).
- 영상: C-009 `gen/generate_video.py`를 **수정 없이** 쓴다(endpoint 모드와 NULL을 이미 지원).
- 사후 CPU: 첫 model_fn context와 cache sha를 대조하고, 시트와 객체 ROI 보조 지표를 만든다.

## Probe 행렬 (C-010 seed·grid 재사용)
- 사례: bear, dance-twirl (train), elephant, goat (validation). σ: 0.95(208), 0.50(833), 0.05(990). positive text만.
- noise seed: bear 20261201, dance-twirl 20261202, elephant 20261101, goat 20261102.
- L·E 모두 같은 z0·ε·σ·target을 쓴다. 계열 안에서는 BASE/ON/NULL이 같은 context를 쓴다. 교차 checkpoint 실험은 하지 않는다.
- 수치: L_BASE/ON/NULL(obj/bg/W), Δ_F = L_ON − L_NULL, I = Δ_E − Δ_L, `||δ||²_W − 2⟨δ,e_N⟩_W` 분해.
- gradient: elephant/goat × σ0.50/0.05 × L/E × ON/NULL = 16 + 16 VJP. 모듈별 norm, ON−NULL norm, cos. optimizer는 0.

## 영상 행렬 (CFG5, seed 20261028, Euler50, shift5, 416×240×33, 16fps preview)
| 사례 | E (신규) | L |
|---|---|---|
| elephant | E-BASE → E-ON → E-NULL | 재사용: C-007 `BASE_5`, C-009 `NEW_ON_5` |
| goat | E-BASE → E-ON → E-NULL | **보완 2개(사전 고정): L-BASE_5, L-ON_5 (C-009 ckpt256, layout_mov)** |

신규는 정상 8개, 예비 1개다. 각 영상의 첫 model_fn에서 vace_context sha를 해당 계열 cache와 대조한다(E는 E cache, L은 L cache). point sidecar는 C-007 `sidecars/{clip}.pt`(clean_latent 없음)다.

## 사전 판정 규칙
**수치** (중심: validation σ0.50, 보조: 나머지 셀 전부 보고)
- `PROBE_POINT_GAIN`: 중심 2셀 모두 Δ_E < 0, 그리고 보조 10셀 중 Δ_E < 0이 과반.
- `NO_PROBE_GAIN`: 중심 2셀 모두 Δ_E ≥ 0.
- 그 밖에는 `MIXED_PROBE_EFFECT`.
- I는 보조 정보로만 쓴다. gradient cos·출력 크기는 통과선이 아니다. C-010의 섭동 반응이나 그 3배는 쓰지 않는다.

**영상** (사례별, 사건표 기준; 사건은 GPU 실행 전 `OBSERVATIONS_PRE.md`에 고정)
- `ENDPOINT_POINT_GAIN_OBSERVED`: 같은 E에서 ON이 BASE와 NULL보다 OBSERVED 사건(큰 움직임·내부 진행)에서 BETTER가 더 많고 WORSE가 없으며, 큰 외형·장면 회귀가 없다.
- `COMMON_ADAPTER_EFFECT_ONLY`: ON과 NULL이 서로 SIMILAR이고 둘 다 BASE와 다르다.
- `SENSITIVITY_ONLY`: ON ≠ NULL이지만 사건 정확도가 BETTER가 아니다.
- `NO_ESTABLISHED_GAIN`: ON ≈ NULL ≈ BASE이거나 ON이 WORSE다.
- 시스템 비교에서는 E-ON vs L-BASE/L-ON을 같은 축으로 본다. 위 point gain이 있고 L보다 SIMILAR 이상이면 `SYSTEM_GAIN_CANDIDATE`, 낮으면 `CONDITION_USE_WITH_SYSTEM_TRADEOFF`다.
- 판정은 사례별로 유지하고 하나로 합치지 않는다. agent 시트 검토는 독립 human 평가가 아니며, 연속 시청이 없으면 temporal=UNVERIFIED다.
- 이름을 가린 시트를 먼저 판정하고 그 뒤 라벨을 연결한다.

## 예산
- public VAE encode: cache 20 + parity 4 + 영상 조건 16 = 40 (예비 4).
- 학습 256 update, validation 18, 진단 약 5.
- probe 72, gradient 16 + 16 VJP, 기계 복구 forward 8.
- sampler 8 (+1 예비), decode 8 (+VAE-only 1).
- 다운로드·imagegen·SAM·CoTracker·14B·업스케일·후합성 0.
- 4시간 상한, active 학습 9000초 상한. guard·실행기는 C-009/010 그대로 쓴다.
