# C-011 통합 작업 의뢰서
## 새 Claude Code 세션용 — 동적 윤곽 제거가 점 궤적의 추가 기여를 만드는가?

**저장소:** `hyunlord/make-meme`  
**실행:** 기존 DGX Spark / 기존 연구 Python·보호 실행 경로  
**작성 기준:** 2026-10-31. 실제 실행 파일명·로그에는 실제 실행 날짜를 사용한다.  
**이번 권한:** 조건 캐시 구성 한 요소 변경 → 같은 초기 상태의 제한된 재학습 → 수치·영상 대조 → 기록·전달.  
**최종 채택:** 이번 결과를 검토한 뒤 결정한다. 실험 수행 승인은 endpoint-only 방식의 기본 채택 승인이 아니다.

---

## 0. 이번에 답할 질문과 완료 기준

최종 연구 목표는 원본 영상·편집 지시·선택적 참조 이미지에서 소수의 편집 앵커를 만들고, 원본 동작·대상 외형·보호 장면을 개인 DGX Spark 수준에서 함께 보존하는 영상 편집 방법이다.

C-008/009에서 잘못된 RGB 생성 마스크로 학습했던 문제를 고쳤다. 정상 조건의 adapter는 더 이상 큰 붉은 번짐을 만들지 않지만, BASE나 NULL보다 동작을 잘 따르는 이득도 입증하지 못했다. C-010에서는 궤적의 차이가 실제 hidden과 최종 예측까지 전달됨을 확인했지만, 높은·중간 잡음 수준에서 그 차이가 정답 오차를 줄이지 않았다. 공식 판정은 `DIAGNOSTIC_INCONCLUSIVE`이며, 조건 중복은 아직 가설이다. [S1–S3]

**이번 질문:**

> 학습과 생성의 중간 VACE RGB 조건에서 동적 윤곽을 제거하면, 같은 점 궤적 adapter가 실제 중간 궤적을 더 유용하게 학습하는가? 그 결과는 단순히 약해진 기준선을 회복하는 수준인가, 기존 윤곽 기반 시스템보다 나은가?

이번 변경은 **VACE에 입력하는 중간 조건 RGB** 하나다. 모델·adapter·loss·학습량·점 자료·생성 마스크·앵커는 유지한다. 제거한 조건에 맞춰 **처음부터 같은 256회로 재학습**한다. 기존 layout 학습 checkpoint에서 추론 조건만 바꾸는 실험으로 대체하지 않는다.

완료에 필요한 결과:

1. Endpoint-only 조건 캐시와 실제 생성 입력의 일치.
2. 기존과 같은 step 000 상태·학습 선택 순서에서 256 update.
3. 같은 정답·noisy state에서 layout 계열과 endpoint 계열의 BASE/ON/NULL 수치 대조.
4. validation 두 사례의 endpoint BASE/ON/NULL **실제 영상 6개**.
5. 기존 layout BASE/ON과의 품질·비용 대조. 없는 goat 대조 영상은 최대 2개 보완.
6. “점 조건의 추가 기여”와 “전체 시스템 품질”을 나눈 판정, 한국어 수식·코드 설명.

진단 표만 만들고 종료하지 않는다. 안전하고 입력 계약이 맞으면 실제 재학습과 영상 비교까지 수행한다. 추가 학습량·잔차 배율·다른 표현을 탐색하는 작업으로 확대하지 않는다.

---

## 1. 새 세션 인수와 기준 자료

이전 대화, 열린 SSH, shell 변수, Python 환경이 남아 있다고 가정하지 않는다.

### 1.1 확인할 환경

- 현재 hostname·사용자·작업 디렉터리와 저장소 root/remote/branch/HEAD/worktree.
- `CLAUDE.md`, `AGENTS.md` 등 현재 적용 지침과 다른 미커밋 변경.
- 현재 Spark인지, 기존 SSH 별칭 `dgx-spark`를 통해 접속해야 하는지.
- 기존 연구 Python, 실제 DiffSynth 소스, VACE 1.3B·VAE·T5·tokenizer 경로.
- C-009 정상 white cache와 checkpoint 000/128/256, C-010 probe manifest.
- C-007/009 elephant 영상·실제 입력 trace, goat의 기존 layout 영상 유무.
- 이미 정상 동작한 guard·worker·Mac 전달 경로.

기존 `REPRODUCE`, `DELIVERY`, private config에서 경로를 찾는다. `/Users/rexxa/research/make-meme-b/`, `/tmp/C009-review-20261031.zip`, `/tmp/C010-review-20261031.zip` 등은 과거 인수 단서이지 현재 존재를 보장하는 경로가 아니다. `/tmp` 자료가 없으면 원본 보존 위치를 찾고, 이전 생성·추적을 처음부터 반복하지 않는다.

특정 Codex 도구는 필요하지 않다. 기존 git·SSH·Python으로 수행한다. 새 SSH 키·token·venv를 만들거나 가중치를 복제하지 않는다. 현재 환경이 다른 프로젝트라면 기존 make-meme 연구 worktree를 찾아 사용한다. 무제한 파일시스템 검색·새 운영 framework 개발은 하지 않는다.

### 1.2 근거 커밋과 문서

| 기준 | ref | 경로 |
|---|---|---|
| 직전 진단 | `3325533` | `docs/research/experiments/C-010-trajectory-signal-diagnostics/` |
| 정상 조건 학습 | `fbb07f1` | `docs/research/experiments/C-009-corrected-conditioning-retrain/` |
| 마스크 원인 수정 | `ecaa653` | `docs/research/experiments/C-008-conditioning-parity/` |
| 초기 학습 구현 | `c4aef32de21de4073bd4eb1861df4d35f2eda793` | `docs/research/experiments/C-006-motion-point-adapter-pilot/` |
| 실제 생성·probe | `19e110431e90931c98277b7e94d6879268929336` | `docs/research/experiments/C-007-frozen-adapter-cfg-diagnostics/` |
| upstream 기록 | `f39d731a3e318d25b725eb3389cfddb184619842` | DiffSynth-Studio |

짧은 ref는 전체 SHA로 해석해 기록한다. 현재 HEAD를 과거로 강제 reset하지 않는다. 연구 브랜치 단서는 `docs/c-research-20261028`이지만 실제 상태를 확인한다. 새로운 결과·코드는 C-011에 격리하고 역사적 코드·cache·판정을 덮어쓰지 않는다.

먼저 읽을 파일:
- C-010 `RESULTS.md`, `PLAN.md`, probe manifest, `code/diagnose_signal.py`, `code/signal_common.py`.
- C-009 `REPRODUCE.md`, `TRAIN_CONFIG.json`, `TRAIN_REPLAY_CHECK.json`, `CACHE_REBUILD.json`, `PARITY.json`.
- C-009 `code/gen/generate_video.py`의 `condition_mode=endpoint`와 실제 CFG 전달 경로.
- C-006의 실제 `train_adapter.py`, `training_state.py`, `point_adapter.py`, `point_features.py`, `wan_adapter_forward.py`, `DATA_SPLIT.json`, `TRAIN_CONFIG.json`.
- 현재 연구 HISTORY/ROADMAP과 실제 정상 실행 경로.

**C-011 경로 제안**
- 실험: `docs/research/experiments/C-011-endpoint-only-trajectory-ablation/`
- 의뢰서: `docs/research/work_orders/C011_ENDPOINT_ONLY_TRAJECTORY_ABLATION_CLAUDE_KO.md`

동일 C-011이 이미 진행·완료됐다면 중복 학습하지 않는다. 다른 작업을 정리하거나 무차별 `git add -A`로 함께 commit하지 않는다.

---

## 2. 사전 계획과 변경 통제

환경·경로를 읽기 전용으로 찾은 뒤, **새 입력 수치 분석·VAE·GPU 실행 전에** 다음을 PLAN에 고정하고 commit한다.

- 이 의뢰서 원문과 한 가지 변경.
- 데이터·초기 checkpoint·학습 설정·probe·영상 행렬.
- layout 비교 영상의 존재 여부와 보완할 최대 2개 셀.
- 사건별 평가 기준과 단계별 예산.
- 구현 diff 및 새 캐시 namespace.

원격이 가능하면 push한다. 장애가 있으면 local commit 시각과 push 지연을 그대로 기록한다. 실행 후 PLAN을 사전 계획처럼 소급 작성하지 않는다.

고정하는 것:
- VACE 1.3B와 adapter 구조·주입 위치·정밀도·scale.
- 기존 원본 구간·양끝 앵커·prompt·negative prompt.
- 정상 흰색 생성 마스크 `G`와 기존 33→9 압축.
- clean latent·endpoint patch·point tracks·visibility·valid·exclusion·bbox 정보.
- 초기 parameter·optimizer·RNG·data order, loss와 optimizer 설정.
- 학습 256 update, 생성 CFG5/Euler50/seed20261028.

바꾸는 것:
- **중간 조건 RGB**: 시간별 외곽선 대신 세 채널 값이 모두 127인 빈 프레임.
- 그 입력에서 만들어지는 `vace_context`.
- 그 조건에서 같은 절차로 학습된 새 adapter의 가중치.

하지 않는 것:
- point 선택·가시성·body-outside 점·exclusion 사후 수정.
- 좌표 단위 변경, delta_q 확대, kernel 폭 변경, 새 hidden-query 구조.
- loss·dropout·sigma sampling·학습량·precision 조절.
- 새로운 imagegen·SAM·CoTracker·다른 encoder·14B.
- 조건 dropout이라는 또 다른 방법을 추가. 기존 point NULL/text dropout은 유지.
- 가드·서비스·loader·driver 개편, 새 모델/데이터/패키지 설치.

---

## 3. 가설과 해석 범위

### 3.1 비교하는 두 조건 계열

- **L (LAYOUT):** 양끝 앵커 + 중간 동적 윤곽. 정상 white-mask 조건의 C-009와 checkpoint 256을 사용한다.
- **E (ENDPOINT):** 같은 양끝 앵커 + 중간 회색 RGB. 같은 step 000에서 이번에 새로 학습한다.

C-009 layout checkpoint를 E에서만 추론해 본 결과를 주 비교로 삼지 않는다. 이는 학습·추론 조건 이동을 섞는다. E 결과는 E에서 학습한 checkpoint와 평가한다.

### 3.2 “point만이 움직임을 준다”라고 표현하지 않는다

E에서도 양끝 자세·텍스트·기반 모델의 prior는 남는다. 학습형 noisy state는 정답 영상 구조를 일부 포함한다. 제거하는 것은 **중간 시점별 동적 윤곽이라는 추가 조건 경로**다.

E의 실제 sampler는 순수 noise에서 시작하고 clean target latent를 보지 않는다. 학습형 one-step state에 정답 성분이 포함되는 것은 FM objective의 정의이며, sampler의 정답 누출과 다르다.

ON과 NULL은 좌표뿐 아니라 중간 visibility/valid/motion bit 등이 함께 다르다. 이번 결과는 기존 **point-condition 묶음의 추가 기여**이지, 위치 하나만의 순수한 인과효과가 아니다.

### 3.3 성공 질문을 두 개로 나눈다

1. **조건 활용:** E 안에서 ON이 E-BASE·E-NULL보다 원본 동작에 가까운가?
2. **시스템 가치:** E-ON이 기존 L-BASE·L-ON보다 실제로 좋은가?

윤곽을 빼서 약해진 E-BASE를 조금 회복한 것만으로 기존 시스템보다 우수하다고 하지 않는다. 1번만 지지되면 기여의 진단 근거이지 기본 경로 교체 근거는 아니다.

높은 gradient cosine은 공통 성분이 크다는 보조 근거다. 그것만으로 궤적 학습 신호가 없다고 단정하지 않는다. C-010의 ±4/±8px 반응을 확정된 “BF16 잡음 바닥”으로 부르거나, 그 3배를 이번 성공·기각 기준으로 재사용하지 않는다.

---

## 4. 데이터와 평가 사례 고정

기존 데이터 분할·frame ID·crop/resize를 그대로 사용한다.

| 구분 | 영상 |
|---|---|
| train 8 | bear, blackswan, bmx-bumps, boat, bus, camel, cows, dance-twirl |
| validation 2 | elephant, goat |
| 과거 test | horsejump-low, lucia — 이번에는 평가·생성하지 않음 |
| cross-ID | 기존 dog — 이번에는 평가·생성하지 않음 |

**E 캐시는 train8 + validation2 = 10개만** 만든다. 이번 범위에 없는 test/cross-ID 캐시까지 재생성하지 않는다.

- 조건·학습·생성: 416×240, 33프레임.
- Preview: 16fps. source_fps가 미확인이면 null 유지.
- 파일 길이 33/16초와 양끝 표본 간격 32/16초를 구분.
- 양끝은 원본의 실제 0/32 프레임이다. 이번에는 새 이미지 편집을 하지 않는다.
- source 객체 mask는 loss 계산·기존 추적 계보·평가에서 유지할 수 있다. 이를 제거한 동적 윤곽 대신 생성 입력의 다른 채널에 넣지는 않는다.

수치 probe의 train 사례는 bear/dance-twirl, validation은 elephant/goat로 고정한다. elephant의 ON–NULL 차이가 작고 일부 track이 대상 밖이라는 한계를 그대로 표시한다. 더 좋은 결과를 위해 점이나 사례를 교체하지 않는다.

영상은 validation 두 사례를 모두 사용한다. 현재 두 validation은 반복적인 개발 판단에 쓰였으므로 새 독립 test라고 부르지 않는다. 사전학습 데이터 중복 여부도 미확인이다.

---

## 5. Endpoint-only 조건의 정확한 구현

### 5.1 기존 경로 재사용

C-009 생성 코드에 이미 `condition_mode="endpoint"`가 있다. 해당 경로는 pinned `FrameRefExpandAnnotator`의 `firstlastframe` 입력을 사용하며, 중간 RGB가 (127,127,127)인지 검사한다. [S4]

이 경로를 우선 재사용한다. E 생성 config의 `layout_dir`는 `None`이어야 한다. layout 파일을 읽고 다른 경로로 넘기는 hidden shortcut을 만들지 않는다.

정의:

\[
X^E_t=\begin{cases}
A_0 & t=0\\
(127,127,127)&1\le t\le31\\
A_{32}&t=32
\end{cases}
\]

\[
G_t=\begin{cases}(0,0,0)&t\in\{0,32\}\\(255,255,255)&1\le t\le31\end{cases}
\]

L은 중간 `X`만 동적 윤곽이고 `G`는 E와 같다.

RGB 정수 fill을 다시 쓰지 않는다. 필요하면 다음처럼 명시한다.

```python
blank = Image.new("RGB", (416, 240), (127, 127, 127))
v = 0 if t in (0, 32) else 255
mask = Image.new("RGB", (416, 240), (v, v, v))
```

`Image.new("RGB", size, 127)`나 `255`를 grayscale 복제로 가정하면 안 된다. 원래 검증된 helper가 반환한 단일 채널 mask를 RGB로 변환하는 방식도 유지할 수 있다.

중간값을 128이나 normalized exact zero로 임의 변경하지 않는다. 127은 기존 endpoint 계약이다. 실제 Normalize 이후 값과 dtype을 기록하고 “정규화된 0”이라고 부정확하게 표현하지 않는다.

### 5.2 캐시 재생성

C-009 정상 white cache를 읽고 **`vace_context`만** E 인코딩 결과로 바꾼다. 기존 C-009 파일은 보존한다.

- 전체 payload를 `weights_only=True` 등 기존 제한 로드 경로로 읽는다.
- point exclusion을 적용하는 학습용 `load_cache()`를 재생성에 사용해 다른 key를 변경하지 않는다.
- clean_latent, patches, positions, visible, valid, anchor_valid, box_wh, text contexts, loss_mask, split/prompt 등은 byte 단위로 보존한다.
- 새로운 provenance는 별도 manifest에 둔다.
- test/cross-ID와 clean target 재인코딩은 없다.

E/L 모두 흰 마스크이므로 `white_v1` 검사만으로 조건 계열을 구분할 수 없다. 새 manifest에는 최소 다음을 명시한다.

```text
mask_contract = white_v1
condition_family = endpoint_gray127_v1
source_layout_parent_manifest = C009의 실제 ID
encoder/source/anchor/helper hashes
per-clip context hash와 불변 key 검사
```

학습 config가 layout cache를 잘못 읽거나 생성 config가 layout 경로로 돌아가면 오류를 내도록 최소 검사를 붙인다. 새 캐시 관리 framework는 만들지 않는다.

### 5.3 반드시 비교할 입력 계약

- 두 앵커는 L/E 간 byte 동일.
- `G`의 세 채널 동일, 양끝0·중간255 및 mask64 동일.
- E 중간31장 모든 채널·픽셀이127. source RGB/윤곽/텍스트 그림 없음.
- L/E의 normalized inactive 입력은 동일. 동일 VAE 계약에서 inactive latent도 같아야 한다.
- reactive 입력과 그 인코딩 결과는 달라져야 한다. E의 reactive latent를 0으로 대체하지 않는다.
- 전체 context `[1,96,9,30,52]` finite, 채널 순서 유지.

E의 elephant/goat 캐시를 실제 생성 prepare 경로에서 **독립 인코딩한 context**와 비교한다. 기존 C-008과 같은 deterministic 조건에서는 exact를 기대한다. 불일치 시 직접적인 파일·mode·RGB·mask 오류부터 고치고, 원인 불명 상태로 학습하지 않는다. C-008의 VAE cache 연구를 다시 전부 반복하지 않는다.

캐시10개는 두 RGB branch씩 기본20 encode, validation live parity는4 encode다. 생성 과정에서의 추가 encode는 별도 계수한다.

---

## 6. 같은 step 000에서 다시 학습한다

사용할 초기 상태는 C-009에서 C-006 train-v2와 일치를 확인한 실제 checkpoint-000이다. 아래를 복원한다.

- Adapter의 모든 MLP·projection 초기 parameter.
- Step0 optimizer state. 학습된 moment를 가져오지 않음.
- CPU/CUDA RNG, 별도 sampling generator.
- Train order·cursor, completed_updates=0.

C-009 checkpoint256에서 이어 학습하지 않는다. 새 seed로 초기화한 모델도 이번 동일 초기화 비교의 대체물이 아니다. C-006의 오류 조건128/256을 정상 조건 checkpoint로 혼동하지 않는다.

모델·optimizer·cache를 준비한 뒤 RNG를 복원한다. 캐시 생성·사전 검사에서 소모한 RNG가 학습에 섞이지 않게 한다. 이전 config의 output/cache/deadline/elapsed 항목은 새 실행용으로 바꾸되, 학습 의미를 결정하는 필드는 유지한다. 새 step000과 원래 step000의 parameter·optimizer·RNG·cursor 비교를 남긴다.

초기 자료가 실제로 없으면 전달 기록과 원본 보존 위치부터 찾는다. 끝내 없으면 `INIT_PARITY_UNAVAILABLE`로 부분 완료하고, 다른 초기화로 몰래 실험을 바꾸지 않는다.

### 6.1 학습 설정

실제 C-009 설정과 원래 C-006 train-v2의 계약을 따른다. [S2, S5]

| 항목 | 고정값 |
|---|---|
| Backbone | 기존 Wan2.1-VACE-1.3B, revision `574e6a744642ce3bee319afc31496b88bde8aac4`의 실제 검증 파일 |
| Adapter | 1,275,072 parameter, MLP303→192→192, 네 projection192→1536 |
| 주입 | 기존 block26/27/28/29 앞 |
| Precision | BF16 backbone, FP32 adapter master·loss |
| Optimizer | AdamW, lr1e-4, betas(0.9,0.999), weight_decay0.01 |
| Batch/update | batch1, **256 optimizer update** |
| Gradient | clip norm1.0, 기존 non-reentrant checkpointing·SDPA |
| NULL/text dropout | NULL0.25, negative-text0.10 |
| Negative prompt | `blurry, distorted, deformed, watermark` |
| Grid | Wan1000-step training grid, shift5, 추가 weight1 |
| Seed | 기존 train/data seed20261030, 기존 generator/cursor 복원 |
| Loss | 객체 면적 정규화 MSE + 배경 면적 정규화 MSE, 1:1 |
| Checkpoint | 000/128/256, 최종 비교는256. 결과로 최적 checkpoint 선택 금지 |

VAE/T5/DiT/기존 VACE weight는 동결한다. Adapter 이후 frozen block·head의 입력 미분은 유지하고, 전체 inference `no_grad` 함수를 학습 함수로 사용하지 않는다. 기존 train 함수를 재사용한다.

FM 식과 timestep 전달도 그대로다.

\[
z_\sigma=(1-\sigma)z_0+\sigma\epsilon,\qquad u^*=\epsilon-z_0.
\]

새 loss·sigma oversampling·조건 contrastive loss·residual regularization을 이번에 추가하지 않는다. Endpoint-only에서 학습이 어렵다는 이유로 update 수를 늘리거나 다른 seed를 시험하지 않는다.

매 step에서 새 noise/sigma를 사용하는 기존 절차를 유지한다. Noisy state에 의존하는 prefix 결과를 다른 step에 재사용하지 않는다. Source object mask는 **loss 가중치**로만 허용된 기존 사용을 유지하며, E의 생성 조건으로 밀어 넣지 않는다.

### 6.2 학습 선택 순서와 검증

C-009 업데이트 로그와 `(step, clip, grid_index, NULL, negative-text)` 256행을 비교한다. 원래 noise 자체가 저장되지 않은 범위는 “generator와 호출 순서에 따른 재현”으로 기록한다. 모든 과거 noise의 byte 일치를 확인한 것처럼 쓰지 않는다.

추가 진단은 별도 generator 또는 RNG를 소비하지 않는 읽기 연산으로 수행한다. 실행 로그를 붙인 탓에 sample schedule이 바뀌면 먼저 바로잡는다.

기존 최소 native/bypass/zero, gradient, 동결, checkpoint reload 검사를 재사용한다. 결과가 달라져야 하는 학습 가중치까지 L과 E가 같아야 한다고 요구하지 않는다.

기존 validation index200/500/800의 step0/128/256 검사는 E cache에서 수행한다. 그 숫자를 L cache의 과거 validation loss와 바로 차감해 “adapter가 더 좋아졌다”고 부르지 않는다. 제대로 비교할 수치는 아래 matched probe다.

---

## 7. 학습 후 matched one-step 비교

이번에는 C-010의 모든 계측을 반복하지 않는다. 기존 분해 코드·좌표 계약·계측 비간섭 근거를 재사용하고, 조건 제거의 효과를 설명하는 최소 대조만 수행한다.

### 7.1 고정 probe 행렬

- 사례: train `bear`, `dance-twirl`; validation `elephant`, `goat`.
- 잡음 목표: σ≈0.95/0.50/0.05. C-010의 실제 grid index·noise seed·manifest를 사용.
- Text: positive만. Negative branch·CFG는 실제 영상에서 고정 CFG5로 사용.
- 계열: L / E.
- 각 계열: BASE / ON / NULL.
- Checkpoint: L은 C-009 정상256, E는 이번 endpoint256.

**4×3×2×3 = 최대72 core forward.** 기존 L tensor를 재사용하려면 동일 noisy state·target·context·point·checkpoint가 확인돼야 한다. 자료가 부족하면 정해진72회 안에서 재측정한다. 과거의 부호 요약만으로 새 수치를 채우지 않는다.

각 probe에서 L/E 모두 같은 clean_latent·ε·σ로 같은 z_sigma와 u*를 만든다. Context는 의도대로 다르다. 각 계열의 BASE/ON/NULL 안에서는 context까지 동일하다. E checkpoint를 L에, L checkpoint를 E에 꽂는 교차 실험은 이번에 하지 않는다.

모든 scalar에는 실제 sigma, FP32 timestep, 모델에 전달된 BF16 timestep, clean/noisy/target hash를 붙인다. 같은 seed만으로 같다고 가정하지 않는다.

### 7.2 일차 수치와 분해

현재 loss의 객체·배경 면적 가중을 동일하게 사용한다.

\[
\Delta_E=L^E_{ON}-L^E_{NULL},\qquad
\Delta_L=L^L_{ON}-L^L_{NULL}.
\]

음수일수록 같은 계열 안에서 실제 궤적이 양끝 경로보다 유리하다. 또 `ON−BASE`, `NULL−BASE`를 함께 기록한다. ON만이 아니라 NULL도 얻는 공통 보정을 point 고유 이득이라고 하지 않는다.

보조적인 조건 간 변화:

\[
I=\Delta_E-\Delta_L.
\]

`I<0`만으로 성공이라고 하지 않는다. 예를 들어 두 계열 모두 ON이 NULL보다 나쁜 상태에서도 I는 음수가 될 수 있다. 각 Δ의 절대 부호·크기, 객체/배경 항, 실제 영상을 함께 본다. 두 adapter는 각 조건에서 학습된 것이므로 I는 이 제한된 학습 절차에서의 상호작용 관측이지, 모든 원인을 분리한 일반적 인과효과는 아니다.

ON 대 NULL의 보정 방향은 같은 상태에서 정의한다.

\[
e_N=u^*-v_{NULL},\quad\delta=v_{ON}-v_{NULL},
\]
\[
L_{ON}-L_{NULL}=\|\delta\|_W^2-2\langle\delta,e_N\rangle_W.
\]

객체·배경·합계의 직접 loss 차이와 분해식을 확인한다. Norm이나 cosine만 높이는 것을 목표로 삼지 않는다. 출력 민감도가 커졌어도 오차 방향이 틀리면 유용한 제어가 아니다.

### 7.3 제한된 gradient 설명

Validation2 × σ0.50/0.05 × L/E × ON/NULL에서 **16 forward +16 VJP/backward**까지 허용한다. Parameter 업데이트는0회다.

- 같은 family의 같은 noisy state/target에서 parameter와 grouped-motion gradient를 비교한다.
- Cosine과 함께 각 gradient norm, ON−NULL gradient norm도 기록한다.
- 가능한 module별 MLP/projection summary만 남기고 전체대형 gradient를 영구 dump하지 않는다.
- High cosine을 조건 무시의 증명으로 사용하지 않는다.
- `.detach()`로 끊긴 원래 positions gradient가 없다는 사실을 모델의 입력 무반응으로 해석하지 않는다.
- 기존의 관측 후 parameter 불변 검사를 유지한다.

이 보조 진단이 영상 생성을 막는 통과 관문이 되어서는 안 된다. Gradient 일부가 관측 불가하면 그 한계를 기록하고 정해진 영상 비교를 진행한다. 새로운 유한 차분·FP32 모델·precision 실험은 추가하지 않는다.

---

## 8. 실제 생성 행렬 — point 기여와 시스템 가치를 모두 확인

모든 새로운 영상은 **CFG5, seed20261028**로 고정한다. 이번에는 CFG1·다른 seed 탐색을 하지 않는다.

| 사례 | 조건 계열 | 모델/point 모드 | 산출물 |
|---|---|---|---|
| elephant | E | BASE / ON / NULL | 신규3개 |
| goat | E | BASE / ON / NULL | 신규3개 |
| elephant | L | BASE / C-009 ON | 기존 C-007 BASE5·C-009 NEW_ON5 재사용 |
| goat | L | BASE / C-009 ON | 같은 조건 결과가 없으면 신규 최대2개 |

기본 E 영상6개 + 필요한 L 비교2개로 **정상 신규 최대8개**다. 각각 별도의 raw 결과를 남긴다. 두 계열이 보이는 것만으로 재학습 효과와 test-time context 효과를 완전히 분리했다고 하지 않는다.

기존 L elephant 자료가 유실되거나 입력 계보를 확인할 수 없으면 잘못된 재사용을 하지 않는다. 승인된 L 보완 예산은 총2개 셀까지이며, 실행 전에 어떤 부족 셀을 보완할지 고정한다. 모든 비교를 채울 수 없으면 E 안의 6개 비교는 완료하고 시스템 우열은 `COMPARATOR_INCOMPLETE`로 표시한다. 대조군 유실을 이유로 최대8개 상한을 자동 확대하지 않는다.

C-009의 **정상** layout checkpoint256을 사용한다. 빨간 마스크로 학습한 C-006 checkpoint128/256은 이번 주 대조군이 아니다. C-009 NULL 영상은 보조 역사 자료로 재사용할 수 있지만 새로운 L-NULL 영상은 추가하지 않는다.

### 8.1 공통 생성 설정

- 기존 VACE 1.3B, BF16·SDPA·tiled VAE, adapter FP32 master.
- 416×240·33프레임, preview16fps, source_fps=null 유지.
- Euler50, CFG5, shift5, vace_scale1.0, rand_device=cpu.
- 같은 source 실제0/32 이미지·prompt·negative prompt.
- 같은 G와 기존 mask 시간 압축. Endpoint clamp 없음.
- Family E는 `condition_mode=endpoint`, `layout_dir=None`.
- Family L은 `condition_mode=layout_mov`, 기존 실제 layout.

같은 사례의 여섯 가능한 셀은 같은 초기 noise를 사용한다. E-BASE/ON/NULL은 **실제 전체96채널 context도 동일**해야 한다. E와 L 사이에서는 inactive/mask/text/앵커는 고정되고 reactive 내용이 의도적으로 다르다. Context 전체가 달라지는 것을 parity 실패로 혼동하지 않는다.

첫 model_fn 직전 실제 context와 해당 cache를 비교한다. **같은 checkpoint와 같은 설정이지만 다른 cache를 읽는 오류를 막는다.** 현재 step sigma 선택·CFG 분기 count는 기존 C-007/009 코드대로 유지한다.

CFG5의 각 영상은 50 scheduler step·100 model_fn call 예상. 예산표에는 실제 값과 차이를 기록한다. Anchor 이미지 두 장을 입력으로 받는 것과 출력 양끝 픽셀을 고정하는 것은 다르므로, 양끝 강제 덮어쓰기로 비교를 꾸미지 않는다.

### 8.2 정답 누출 방지

Validation cache에는 clean_latent가 있다. 생성용 point sidecar는 기존 whitelist 방식으로 만들어 `patches/positions/visible/valid/anchor_valid/box_wh` 등 허용 key만 전달한다. Target latent나 loss_mask를 inference 힌트로 연결하지 않는다. Point exclusion sidecar는 기존 값을 그대로 적용한다.

VACE context는 실제 source 중간 RGB를 인코딩한 것이 아니라 해당 family의 선언된 조건으로 생성되어야 한다. E에서 source object mask·dynamic bbox·source frame을 추가 encoder 경로로 넘기지 않는다. Point 궤적과 visibility의 사용은 ON에 명시적으로 허용된 조건이다.

새 생성은 순수 noise에서 시작한다. Clean latent를 init이나 이전 영상 continuation으로 재사용하지 않는다.

### 8.3 보존과 평가 순서

영상의 final latent를 decode 전에 원자 저장·readback하고 raw·33PNG·MP4를 보존한다. 후합성·업스케일·interpolation·얼굴 복원·색보정 없이 raw 우선 비교한다.

사례별 E-BASE → E-ON → E-NULL, 이후 필요한 L 비교의 순서를 사전에 고정한다. 나쁜 품질이 나왔다는 이유로 NULL이나 두 번째 validation을 생략하지 않는다. 실제 안전 차단·입력 오류는 별개다.

---

## 9. 품질 평가 — 새로 흔들리는 것과 잘 제어되는 것은 다르다

### 9.1 결과를 보기 전에 사건을 고정

Source와 기존 앵커·track만 보고 두 validation 각각의 관측 가능한 사건을 적는다. 학습 결과나 새 출력에서 잘 된 부분을 골라 기준을 바꾸지 않는다. 이 입력 관측도 PLAN commit 이후에 수행하고 별도의 짧은 사전 관측표를 GPU 실행 전에 확정한다.

- `elephant`: 기존에 관측했던 이동·접근/멀어짐, 보이는 발 들림·내려옴 순서, 먼지/물줄기 가림, 건물·바위·나무 보존. 해부학적 좌우·실제 접촉을 단정하지 않는다.
- `goat`: 실제 원본을 열어 머리·몸 방향·보이는 발/다리의 순서와 이동, 배경 사건을 정한다. 보고서에 없는 사건을 상상해서 넣지 않는다.

각 사건은 `OBSERVED / OCCLUDED / AMBIGUOUS`로 표시한다. 대상 밖 점, 가림, 부정확한 track도 보존하고 한계로 기록한다. 이번에는 track을 고치지 않는다.

전체33장과 고정 `0/4/8/12/16/20/24/28/32`를 같은 인덱스로 본다. 종료부29~32와 중간부1~28을 나누어 앵커 일치와 중간 동작을 구분한다.

### 9.2 판정 축

| 축 | 질문 |
|---|---|
| 큰 움직임 | 위치·크기·방향·접근 순서가 원본에 가까운가? |
| 내부 진행 | 관측 가능한 머리·다리 배치와 사건 순서가 더 맞는가? |
| 대상 외형 | 같은 개체·무늬·형태가 유지되는가? |
| 가림·재등장 | 불필요한 부위나 중복 윤곽 없이 이어지는가? |
| 장면 | 배경과 비대상 객체가 더 손상되지는 않는가? |
| 양끝 | 앵커 충실도가 나아졌는지, 중간 동작과 분리해서 보는가? |
| 시간 품질 | 실제 연속 재생의 흔들림·급변이 있는가? |
| 비용 | 조건 추출·학습·생성·수동 검토의 비용이 어떻게 다른가? |

각 비교는 `BETTER / SIMILAR / WORSE / UNCERTAIN`으로 사건표에 기록한다. 전체 화면 MAE가 작다고 모듈 무효, 크다고 성공이라 하지 않는다. 객체 ROI의 관측을 함께 두되, 출력마다 유리한 crop이나 시간 이동을 적용하지 않는다.

이미 있는 loss object mask를 source-relative 평가 영역으로 사용할 수 있지만, 새 체형·동작의 정답 마스크로 오해하지 않는다. 이번은 실제 같은 개체의 자기재현이므로 cross-ID 일반화 성공이라고 보고하지 않는다.

새 segmentation·pose·flow 모델을 평가용으로 추가하지 않는다. 정확한 관절 GT가 없으면 수치를 억지로 만들지 않고 보이는 사건의 근거를 남긴다. 조건을 만든 tracker만을 유일한 품질 평가기로 사용하지 않는다.

가능하면 이름을 가린 비교 시트로 먼저 평가한 뒤 label을 연결한다. 같은 세션의 agent 검토를 독립 human 평가라고 부르지 않는다. 실제 사람이 연속 재생을 보았는지, 프레임 시트만 보았는지 구분한다. 재생 기능·ffmpeg decode만 확인했다면 `temporal=UNVERIFIED`를 유지한다. 이 불확실성 때문에 나머지 작업을 멈추고 사용자 응답을 기다리지는 않는다.

### 9.3 네 비교를 별도로 보고

1. **E-ON ↔ E-BASE:** 새 adapter+point 조건의 전체 이득.
2. **E-ON ↔ E-NULL:** 같은 학습 모듈에서 실제 중간 point-condition 묶음의 추가 이득.
3. **E-ON ↔ L-BASE/L-ON:** 기존 실제 시스템 대비 품질·비용.
4. **E-BASE ↔ L-BASE:** 윤곽 제거만으로 기반 모델이 얼마나 약해지거나 달라졌는지.

1번만 좋아지고 2번은 같으면 point 고유의 제어가 입증된 것이 아니다. 1·2번이 좋아져도 3번에서 크게 나빠지면 최종 시스템 개선으로 채택하지 않는다.

---

## 10. 사전 판정 규칙과 반증 범위

기술 실행, 수치 근거, 영상 품질, 원인 가설을 하나의 PASS로 합치지 않는다.

### 10.1 기술 판정

- `ENDPOINT_CONTRACT_VERIFIED`: E 중간127·정상G·앵커 고정.
- `CACHE_LIVE_PARITY_VERIFIED`: 독립 인코딩 일치.
- `NONCONTEXT_FIELDS_UNCHANGED`: 기존 target·point·text·loss 정보 유지.
- `INIT_PARITY_VERIFIED`, `TRAIN_SCHEDULE_MATCHED` 또는 정확한 제한.
- `TRAIN_COMPLETE_256`, `MATCHED_VIDEO_COMPARISON_COMPLETE`.
- 새 학습 자료를 바꿨기 때문에 기존과 checkpoint가 같을 필요는 없음.

### 10.2 수치 근거

σ0.50의 validation 두 사례를 중심 비교로 지정한다. σ0.95/0.05와 train 두 사례는 사전 지정된 보조 축이다. 모든 셀을 보고하고 좋은 sigma만 고르지 않는다.

- 정상 비교 오차 범위를 넘는 음의 Δ_E는 해당 probe의 point-condition 이득이다.
- Δ_E와 Δ_L, `I=Δ_E−Δ_L`을 같이 본다. I만 음수인데 Δ_E가 여전히 양수면 성공으로 올리지 않는다.
- 실제 motion-gradient의 cosine/norm은 설명 자료이지 0.9 통과선이 아니다.
- 출력 변화량이 커지거나 예전 섭동 반응의 3배를 넘는 것은 합격 조건이 아니다.
- 검증되지 않은 수치 “noise floor”를 사용하지 않는다. 같은 입력 반복 오차와 제어된 입력 변화의 출력 반응은 다른 측정이다.

수치 일관성은 `PROBE_POINT_GAIN / MIXED_PROBE_EFFECT / NO_PROBE_GAIN`처럼 관측 범위로 보고한다. One-step 이득만으로 영상의 동작 정확도를 선언하지 않는다.

### 10.3 영상과 시스템 판정

| 판정 | 필요한 관측과 범위 |
|---|---|
| `ENDPOINT_POINT_GAIN_OBSERVED` | 같은 E에서 ON이 BASE·NULL보다 사전 지정된 움직임을 더 정확히 재현. 큰 외형·장면 회귀 여부를 함께 기록. 사례별 근거 필요 |
| `CONDITION_USE_WITH_SYSTEM_TRADEOFF` | E 안에서는 point 이득이 있지만 기존 L 시스템보다 전체 품질이 낮거나 mixed |
| `SYSTEM_GAIN_CANDIDATE` | E 안의 point 이득과 기존 L 대비 품질·비용상의 유리한 관측이 함께 있음. 두 validation·한 seed에 한정 |
| `SENSITIVITY_ONLY` | ON/NULL은 달라지나 의도한 동작의 정확도 이득 없음 |
| `COMMON_ADAPTER_EFFECT_ONLY` | ON·NULL이 BASE 대비 비슷하게 변함. 실제 중간 궤적의 추가 기여 미입증 |
| `NO_ESTABLISHED_GAIN` | 현재 고정된256회·구조·데이터에서 유용한 추가 기여를 확인하지 못함 |
| `INCONCLUSIVE` | 계약·학습 완료·대조 자료·관측이 부족해 판단이 제한됨 |

두 validation이 다르면 하나의 승자로 압축하지 않고 사례별 판정을 유지한다. 한 사례의 분명한 관측은 해당 사례의 근거이고, 일반화나 통계적 유의성의 증명이 아니다. 33프레임을 33독립 표본으로 세지 않는다.

### 10.4 조건 중복 가설을 어디까지 말할 수 있나

E에서 실제 point 활용이 개선되면 “동적 윤곽을 제거한 이 학습 절차에서 point의 추가 기여가 커졌다”는 제한된 근거다. 그 원인이 중복 정보만인지, 학습 난이도·조건 분포·기존 모델 prior와의 상호작용인지는 완전히 분리되지 않는다.

E에서도 이득이 없으면 다음처럼 결론낸다.

> 현재 adapter·자료·256회 학습 예산에서는 동적 윤곽 제거만으로 유용한 point 제어를 만들지 못했다.

모든 가능한 조건 중복 설명을 반증했다고 하지 않는다. 그렇다고 같은 실험을 끝없이 반복하지도 않는다. 다음 개입 후보 하나와 그 반증 조건만 제안하고 종료한다.

C-010의 `DIAGNOSTIC_INCONCLUSIVE` 및 옛 사전 규칙은 유지한다. 이번에는 새 질문에 맞는 규칙을 실행 전에 새로 고정하는 것이며, 과거 규칙을 사후 변경한 것이 아니다.

---

## 11. 실행 예산·계수·안전

### 11.1 정상 계산 예산

| 단계 | 정상 범위 |
|---|---|
| 새 E cache | 10개×2 branch =20 public VAE encode |
| Validation E live parity | 2개×2 branch =4 encode |
| 학습 | 256 optimizer step, training forward/backward 각256 |
| 원래 학습 validation | 2영상×3sigma×3checkpoint =18 forward |
| 기존 초기·reload 진단 | 기존 코드 기준 약5 forward. 실제 추가가 있으면 명시 |
| Matched probe | 최대72 full forward |
| 제한 gradient 진단 | 16 full forward +16 VJP/backward, optimizer0 |
| E 영상 | 6 sampler×50step =300 step, CFG5 기준600 model_fn call |
| L 비교 보완 | 최대2 sampler,100 step,200 call |
| 신규 decode | 정상 완료 영상당1회, 최대8 |
| 모델·자료 다운로드 | 0 |

새 영상 조건 encode는 prepare/cache24회와 별개다. 최대8개 생성에서 일반적으로16 encode가 추가되므로 **정상 전체 public encode 최대40회**다. Pipeline 실제 호출을 계수하고, 타일/시간chunk 내부 호출과 public 호출을 혼동하지 않는다. T5 인코딩이나 checkpointing의 block 재계산도 필요한 별도 장부에 적는다.

기계적 복구:
- cache/prepare encode 예비 최대4회.
- full sampler 예비1회. 정상8 + 예비1 = 전체 sampler 최대9시도.
- final latent 저장 후 decode 실패는 sampler를 반복하지 않고 VAE-only 복구 최대1회.
- probe/초기 진단의 기계적 복구 최대8 forward. 별도 품질 탐색 금지.
- 학습 복구는 **C-011의 마지막 정상 상태에서 누적256회 이내**로만 한다.

모델 적재·sampler 첫 forward 전에 실패한 시작도 숨기지 않고 단계별로 기록한다. 계산을 한 “heavy stage 수”만으로 모든 학습·분기 호출을 뭉뚱그리지 않는다. Batch 크기를 늘려 호출 예산을 우회하지 않는다.

### 11.2 범위 상한

전체 작업 범위 상한4시간, 마지막30분은 비교·기록·전달에 남긴다. Active 학습 상한은 기존9000초를 유지한다. 이는 승인 범위이지 실제 걸리는 시간의 예측이나 보장이 아니다.

256회 미완료이면 `TRAIN_PARTIAL`이며 같은 예산 비교가 아니다. 남은 시간과 안전 범위에서 마지막 정상 checkpoint의 필요한 비교를 보존할 수는 있으나, 완료한 것처럼 쓰지 않는다. 문서·부가 지표만 늘려 실제 학습과 영상 생성을 뒤로 미루지 않는다.

### 11.3 안전과 실행기

C-009/010에서 정상 동작한 guard·Python·stage 경로를 재사용한다. 절대경로·기존 환경변수 계약을 확인한다. 새 worker orchestration, systemd, cgroup 정책을 만들지 않는다.

- PSI·headroom·worker swap·외부 GPU 작업 보호를 완화하지 않는다.
- 과거 system swap-out 절대0 시작 분기를 복원하지도 않는다.
- 다른 프로세스를 종료하거나 재부팅·swapoff·driver 변경을 하지 않는다.
- 경로·import·인자·dtype 전처리 같은 단순 코드 오류는 같은 의뢰 안에서 수정한다.
- 실제 OOM·메모리 압박·외부 작업 충돌은 자동 재시도하거나 임계값을 바꿔 우회하지 않는다.
- VAE/T5/DiT는 필요한 단계에서만 사용하고 불필요한 동시 상주를 피한다.

이 의뢰는 imagegen·SAM·CoTracker·새 공개 자료 없이 기존 데이터로 수행한다. 개인 강아지 자료나 새로운 외부 계정이 필요하다고 작업을 바꾸지 않는다.

---

## 12. 수학·아키텍처·코드 해설

`LESSON_KO.md`는 이번 단일 개입과 실제 결과에 연결한다. 확인한 사실과 가설을 분리하고, 기존 이론 전체를 반복하지 않는다.

기호:

\[
c_L=E_{VACE}(A_0,L_{1:31},A_{32},G),\qquad
c_E=E_{VACE}(A_0,\text{gray127}_{1:31},A_{32},G).
\]

같은 초기값·학습 schedule \(S\)에서:

\[
\psi_L=Train(\psi_0,c_L,S),\qquad
\psi_E=Train(\psi_0,c_E,S).
\]

평가:

\[
v^F_{BASE}=H_\theta(z_\sigma,c_F),\quad
v^F_{ON}=H_{\theta,\psi_F}(z_\sigma,c_F,p_{ON}),\quad
v^F_{NULL}=H_{\theta,\psi_F}(z_\sigma,c_F,p_{NULL}),\quad F\in\{L,E\}.
\]

설명할 내용:
1. 입력 경로를 하나 제거하는 ablation과 최종 시스템 설계 결정의 차이.
2. 학습 때 윤곽을 쓴 checkpoint에서 추론 때만 제거하면 왜 다른 질문이 되는가.
3. 조건 RGB와 생성 마스크 G, loss용 object mask의 서로 다른 역할.
4. 회색127과 normalized zero의 차이, RGB scalar fill 회귀 방지.
5. Noisy state·양끝·text·prior가 남으므로 “point만으로 움직임 생성”이라고 할 수 없는 이유.
6. ON/NULL의 좌표 외 visibility·motion bit 차이.
7. Δ_E, Δ_L, 상호작용 I와 잔차-오차 분해의 의미·한계.
8. E-BASE가 약해진 효과와 E-ON의 시스템 우위를 구분하는 이유.
9. Gradient cosine·출력 norm이 곧 제어 정확도가 아닌 이유.
10. FM one-step 이득과 실제 반복 생성 영상의 동작 평가를 함께 해야 하는 이유.
11. 같은256회가 충분한 학습량을 보장하지 않는다는 한계.
12. 신호의 유용성이 확인됐을 때 후속 조건 역할 분담을 검토할 수 있지만 이번에는 추가하지 않는다는 범위.

직관 → 수식 → 실제 함수·tensor → 실제 대조 결과 → 반례·한계 순서로 쓴다. 확인되지 않은 정보이론 수치나 “모델이 의도적으로 무시했다” 같은 심리적 설명을 만들지 않는다.

---

## 13. 산출물·GitHub·검토물

권장 최소 문서:
- `PLAN.md`: 사전 고정 내용·예산·commit.
- `CONDITION_CONTRACT.json`: L/E 입력 역할·pixel/context 계보.
- `CACHE_MANIFEST.json` 및 `PARITY.json`: 새 E cache·불변 필드·live parity.
- `TRAIN_CONFIG.json`, `TRAIN_REPLAY_CHECK.json`: 초기 상태·schedule 비교.
- `PROBES.json`, `OBSERVATIONS.md`: 수치와 사전 사건/사후 판정.
- `RESULTS.md`, `COSTS.json`, `LESSON_KO.md`, `REPRODUCE.md`, `DELIVERY.json`.

같은 내용을 많은 파일에 복제하지 않는다. 실행자 인수·현재 단계·남은 예산은 PLAN/private config 안에 간단히 유지하고 별도 관리 플랫폼을 만들지 않는다.

비공개 보존:
- E cache10개와 부모 L 계보.
- 새 checkpoint000/128/256, optimizer·RNG·cursor·update log.
- 실제 조건 PNG·마스크·최초 context/noise 관측.
- 신규 final latent/raw/전체33프레임/원 MP4.
- Probe·gradient summary와 계산에 필요한 작은 tensor.

Viewer는 다음 세 가지 비교 모드를 제공한다.

1. **E 내부:** SOURCE / E-BASE / E-ON / E-NULL.
2. **기존 시스템 대비:** SOURCE / L-BASE / L-ON / E-ON.
3. **조건과 근거:** 양끝 앵커, L/E 중간 입력 예시, point ON/NULL overlay, 사전 사건표, Δ와 loss 분해.

Elephant·goat 탭, 동일 인덱스 slider·고정시트·동일16fps 재생을 제공한다. 모든 영상을 작은 칸에 한꺼번에 밀어 넣기보다 같은 비교를 읽기 쉬운 크기로 제공한다. 실제 생성 결과와 조건/overlay를 명확히 구분한다.

Compact에는 원 생성 MP4·필요한 source/앵커·작은 시트·뷰어·보고서를 넣는다. Cache·optimizer·대형raw·latent·모델 가중치는 별도 private 보존하고 compact에 반복 포장하지 않는다. 원 생성 MP4를 작은 용량 때문에 낮은 화질로 재인코딩하지 않는다. 비교 MP4·thumbnail은 파생물로 표시한다.

Spark/Mac의 실제 승인된 경로 또는 `/tmp`로 전달하고, 가능한 양쪽에서 SHA256·CRC·manifest·실제 추출을 확인한다. 한쪽에 접근할 수 없으면 양호스트 PASS를 꾸미지 않는다. 날짜는 실제 실행일이다.

공개 Git에는 비민감 코드·문서·필요 hash만 올린다. 사용자 경로·PID·token·미디어·가중치·latent를 자동 공개하지 않는다. 기존 자료 이용 조건은 그대로 유지한다. 연구 브랜치에 관련 파일만 commit/push하고 원격 SHA를 확인한다.

HISTORY/ROADMAP에는 기존 판정을 그대로 보존하면서 C-011의 한 가지 개입과 실제 관측을 연결한다. 과거 실패를 소급 PASS로 바꾸거나, 오류 수정 자체를 새로운 생성 방법 성과로 세지 않는다.

---

## 14. 최종 보고 순서와 종료

최종 답은 실제 비교 뷰어·영상과 함께 다음 순서로 작성한다.

1. 같은 E 안에서 ON이 BASE·NULL보다 원본 동작을 더 정확히 따랐는가? 두 validation을 나눠 답한다.
2. ON/NULL이 단지 더 달라진 것인지, 정답 방향의 변화인지?
3. E-ON이 기존 L-BASE·L-ON보다 좋은가, 조건 제거로 잃은 품질은 무엇인가?
4. Endpoint 조건·white mask·초기 상태·256 schedule의 동일성은 확인됐는가?
5. Δ_E/Δ_L, 낮은·중간·높은 sigma, gradient가 어떤 설명을 지지하거나 제한하는가?
6. 앵커·외형·장면·가림·시간 품질의 회귀가 있는가?
7. 실측 cache/학습/추론/검토 비용과 미측정 항목은 무엇인가?
8. 다음에 바꿀 요소 **하나**와 그 반증 조건은 무엇인가?

검사 개수나 ZIP hash를 연구 성과의 맨 앞에 두지 않는다. 시각 검수가 어려우면 그렇게 밝히고, 관측한 범위만 판정한다.

성공하더라도 추가 seed·다른 모델·cross-ID·고해상도·조건 dropout 학습을 자동 시작하지 않는다. 실패하더라도 잔차 배율·학습량·좌표 scale을 즉석에서 바꿔 재생성하지 않는다. 이번 비교를 완료하고 자체 프로세스 종료·다른 작업 보존을 확인한 뒤 종료한다.

---

## 근거 자료

[S1] C-010 결과·실제 진단 코드 — 신호 전달과 정답 방향, 기존 판정의 한계.  
https://github.com/hyunlord/make-meme/tree/3325533/docs/research/experiments/C-010-trajectory-signal-diagnostics

[S2] C-009 정상 조건 재학습·계보·정상 영상 기준.  
https://github.com/hyunlord/make-meme/tree/fbb07f1/docs/research/experiments/C-009-corrected-conditioning-retrain

[S3] C-008 RGB 마스크 원인과 독립 조건 일치 검증.  
https://github.com/hyunlord/make-meme/tree/ecaa653/docs/research/experiments/C-008-conditioning-parity

[S4] C-009 생성 코드 — 기존 endpoint 모드, gray127, 생성 마스크 및 CFG 설정.  
https://github.com/hyunlord/make-meme/blob/fbb07f1/docs/research/experiments/C-009-corrected-conditioning-retrain/code/gen/generate_video.py

[S5] C-006 초기 구조·학습 설정. 학습된 오류 조건 checkpoint가 아닌 초기 상태와 고정 알고리즘의 근거다.  
https://github.com/hyunlord/make-meme/tree/c4aef32de21de4073bd4eb1861df4d35f2eda793/docs/research/experiments/C-006-motion-point-adapter-pilot

[S6] C-007 실제 generation·validation용 inference sidecar와 입력 관측 경로.  
https://github.com/hyunlord/make-meme/tree/19e110431e90931c98277b7e94d6879268929336/docs/research/experiments/C-007-frozen-adapter-cfg-diagnostics

이 문서는 실행 의뢰서다. 파일을 받았다는 사실만으로 위 경로·가중치·산출물이 현재 세션에 존재한다고 간주하지 않는다. 실제 읽은 commit·local 파일·Python·입력 계보를 확인하되, 환경 전체 재감사로 본 작업을 대체하지 않는다.
