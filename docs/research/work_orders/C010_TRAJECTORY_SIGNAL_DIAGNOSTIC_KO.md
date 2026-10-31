# C-010 통합 작업 의뢰서
## 새 Claude Code 세션용 — 정상 조건 adapter의 궤적 신호 전달·보정 방향 진단

- 저장소: `hyunlord/make-meme`
- 실행 장비: 기존 DGX Spark. 새 Claude Code 세션이 인수·구현·계측·해석을 수행한다.
- 직전 결과: `fbb07f1`, `C-009-corrected-conditioning-retrain`
- 연구 브랜치 단서: `docs/c-research-20261028` — 실제 현재 branch/worktree를 확인한다.
- 권장 실험 경로: `docs/research/experiments/C-010-trajectory-signal-diagnostics/`
- 의뢰서 보존 경로: `docs/research/work_orders/C010_TRAJECTORY_SIGNAL_DIAGNOSTIC_KO.md`

> **이번 작업은 추가 학습이나 품질 튜닝이 아니다. C-009의 정상 조건 checkpoint를 동결하고, 실제 궤적 정보가 입력에서 최종 예측까지 어디서 약해지는지, 남은 변화가 정답 오차를 줄이는 방향인지 확인한다. 진단 한 번으로 다음에 바꿀 요소 하나를 선택할 근거를 남긴다.**

---

## 1. 인수할 연구 배경과 이번 질문

최종 연구 목표는 원본 영상·텍스트·선택적 참조 이미지에서 소수의 편집 앵커를 만들고, 원본 움직임과 대상 외형을 연결해 개인 Spark에서 완성도 높은 편집 영상을 만드는 것이다. 객체별 대응·가시성·특징 전달과 학습 방법을 연구한다.

현재 사용하는 기반은 VACE 1.3B다. C-006에서는 1,275,072 parameter의 Point–Anchor Adapter를 DiT 마지막 네 block 앞에 연결했다. 점 궤적·가시성·양끝 VAE patch를 작은 MLP로 변환하고 점 주변에 배치한 뒤 residual로 주입한다.

C-008에서 학습 cache의 생성 마스크 오류를 확정했다. `Image.new('RGB', size, 255)`가 흰색이 아닌 빨강을 만들어 학습 조건을 잘못 분리했다. 정상 생성 경로는 흰색 마스크를 사용했다.

C-009는 `vace_context`만 정상화하고 같은 step 0·학습 선택 순서에서 256회 재학습했다. 큰 붉은 번짐·투명화는 사라졌지만 elephant의 NEW_ON은 BASE 및 NEW_NULL과 유사했고 동작 이득은 미입증이었다. 따라서 **입력 오류 수정은 완료됐지만, 현재 방법의 유용성은 확인하지 못한 상태**다.

이번 핵심 질문:

> 실제 중간 궤적과 양끝 기반 궤적의 차이가 `입력 → MLP → 공간 배치 → 시간 집계 → projection → 실제 hidden 변화 → 최종 속도 예측`을 거치면서 어디서 줄어드는가? 최종 변화는 BASE가 틀린 방향을 실제로 보정하는가?

미리 가정하지 않을 것:
- 잔차가 작다는 것이 원인이다.
- BF16이 신호를 없앴다.
- 256 update가 부족했을 뿐이다.
- 마지막 네 block이 너무 늦다.
- gradient가 없어서 학습하지 못했다.
- ON과 NULL의 출력이 비슷하므로 궤적은 불필요하다.
- 낮은 FM loss이므로 동작도 이미 충분히 맞다.

**전체 화면 픽셀 차이는 국소 동작의 정확도 지표가 아니다.** 이번에는 입력 차이와 영향 영역을 나누고, 수치상의 조건 민감도와 유용한 동작 제어를 구분한다. 기존 영상의 정적 판정과 temporal=UNVERIFIED는 유지한다.

## 2. 새 세션의 최소 환경 인수와 범위

이전 세션의 cwd·변수·SSH·venv가 유지된다고 가정하지 않는다. 현재 host·사용자·저장소 root·remote·branch·HEAD·worktree·미커밋 변경 및 적용되는 CLAUDE.md/AGENTS.md를 확인한다.

기존 SSH 별칭 `dgx-spark`와 과거 Mac 연구 경로는 단서일 뿐이다. 현재가 Spark면 SSH를 중첩하지 않는다. 기존 인증과 git/SSH CLI로 진행할 수 있으며 Codex 전용 도구나 imagegen은 필요 없다. 비밀값을 출력하거나 새 인증·venv·실행기를 만들지 않는다.

C-009 REPRODUCE/DELIVERY/비공개 실행 설정에서 다음을 찾는다.
- 실제 Python·DiffSynth·VACE 1.3B 경로
- `white_v1` 정상 cache와 manifest, point exclusion sidecar
- **C-009 정상 조건 학습의** checkpoint 000/128/256
- C-007/C-009의 probe grid·기존 source·영상·trace
- 정상 작동한 공통 guard와 Mac 전달 방식

`fbb07f1`을 전체 SHA로 해석해 기록한다. 이 SHA는 근거이며 강제 reset 지시가 아니다. 현재 변경을 보존한다. 같은 C-010이 이미 완료됐으면 중복 실행하지 않는다. /tmp 자료가 없으면 DELIVERY의 원본 보존 경로를 찾고 과거 실험을 재실행하지 않는다.

읽을 파일:
- C-009: RESULTS, REPRODUCE, TRAIN_CONFIG, PARITY, CACHE_REBUILD, TRAIN_REPLAY_CHECK
- C-006의 현재 보존 코드: point_adapter.py, point_features.py, wan_adapter_forward.py, training_state.py
- C-007: INPUT_PARITY, INFERENCE_INPUT_MANIFEST 및 one-step/계측 코드
- C-008: ROOT_CAUSE와 정상 마스크 검사 — 원인 규명을 다시 수행하지 않음
- 실제 HISTORY/ROADMAP

**새 GPU 실행 전에** 의뢰서·PLAN·사례·probe·관측 경계·예산을 commit한다. 원격에 push가 안 되면 local commit과 지연을 기록한다. 실행 후 PLAN을 사전 계획처럼 작성하지 않는다. 이번 파일만 stage한다.

### 이번 허용과 금지

허용: 저장 checkpoint를 읽는 forward, 제한된 gradient 계산, 파라미터를 바꾸지 않는 계측, 사전 고정 좌표 perturbation의 진단, 기존 영상 재사용, 결과·한국어 해설 작성.

금지: optimizer 생성/step, 추가 학습, residual scale 변경, 삽입 위치 변경, kernel 폭·정밀도·loss 변경, 새 모델·데이터·패키지 다운로드, imagegen/SAM/CoTracker 실행, VAE 재인코딩·decode, 신규 full sampler, 14B 복구, 가드·서비스 변경.

단순 진단 코드·경로·logging 오류는 같은 의뢰 안에서 수정한다. 기존 계산을 수정해야 하는 새 결함을 발견하면 증거를 보존하고 방법 변경으로 자동 확장하지 않는다. 실제 자원 위험·외부 작업 충돌은 우회하지 않는다.

## 3. 고정 사례·checkpoint·probe

### 사례: 총 네 개

| 역할 | 영상 | 목적 |
|---|---|---|
| train 진단 | bear | 학습에 사용한 사족 동물에서 신호 활용 확인 |
| train 진단 | dance-twirl | 학습에 사용한 비강체 움직임에서 확인 |
| validation | elephant | 기존 생성 결과와 연결 |
| validation | goat | 하나의 validation에만 의존하지 않는 확인 |

원래 split/33프레임/마스크/점 제외를 유지한다. 해당 파일이 없으면 유리한 사례로 교체하지 말고 그 셀을 MISSING으로 남긴다. 두 train 사례의 결과를 일반화 성능으로 부르지 않는다. validation도 이미 개발 진단용이다. test·cross-ID 자료를 새로 사용하지 않는다.

### checkpoint와 계산 조건

- **C-009 정상 조건** step 000/128/256만 사용. C-006의 오류 조건 128/256과 이름을 혼동하지 않는다.
- 원래 adapter 303→192→192, 네 192→1536 projection, block 26~29, FP32 master.
- 기존 VACE 1.3B backbone BF16·SDPA·고정 가중치, 실제 모델 경로 유지.
- 416×240·33frames, latent `[1,16,9,30,52]`, token `[9,15,26]`, 3510 tokens.
- 같은 정상 96채널 VACE context, text, point 조건, loss mask.
- 메인 진단은 **positive text 단일 예측**. 이번에는 CFG 연구나 negative 분기 비교를 늘리지 않는다.
- 목표 sigma는 **0.95, 0.50, 0.05** 세 곳. C-007의 같은 1000-step grid/shift5에서 가장 가까운 실제 값과 BF16 timestep을 사용한다. 새 schedule을 만들지 않는다.

기존 validation probe의 noise 생성 규칙을 재사용한다. train 두 영상에는 PLAN에 고정한 독립 CPU generator seed를 부여한다. 같은 사례·sigma의 모든 모델은 **같은 z_sigma·noise·target·조건 tensor**를 사용한다. 저장물이 있으면 hash를 대조한다. 같은 seed만으로 과거 bitwise 일치를 주장하지 않는다.

정답에서 만든 probe:
`z_sigma=(1-sigma)*z0+sigma*epsilon`, `u_star=epsilon-z0`.
이 식은 현재 설치 scheduler로 확인하고 기존 구현을 사용한다. clean latent는 이 진단의 정답 구성에만 사용하며 생성은 하지 않는다.

## 4. 단계 A — 모델 실행 전 입력 차이를 먼저 측정

정상 cache를 원본 그대로 읽고, C-009 학습과 같은 point exclusion을 진단용 복사본에 적용한다. 원래 tensor는 변경하지 않는다. `make_null()`을 그대로 호출한다.

ON과 NULL이 달라지는 항목은 좌표만이 아니다. 중간 visibility/validity, 속도, endpoint offset, motion bit도 다를 수 있다. 다음을 분리한다.

1. **공통 유효·가시 점**에서 좌표·속도 차이: pixel 단위, 정규화 단위, endpoint 보간 bbox 대비 단위.
2. 한 조건에만 유효하거나 보이는 점: 수와 시점. 위치 차이에 0으로 섞지 않는다.
3. ON의 실제 궤적이 endpoint 선형 경로에서 벗어나는 정도: 평균·중앙·상위 분위·최대.
4. 두 endpoint의 patch/anchor_valid와 kernel 폭은 두 조건에서 같은지.
5. 관측한 내부 움직임을 실제 선택점이 대표하는지: source 위에 기존 track을 그려 소수의 시점을 확인.

point ID는 영상 내부의 표면점 ID이지 공통 해부학적 부위 ID가 아니다. 코·발 등 의미가 명확한 경우에만 해당 부위라고 표현한다. gate에서 제외되는 점·부위를 숨기지 않는다.

입력이 거의 같으면 출력 유사성만으로 모델의 무시를 판정하지 않는다. 반대로 점 궤적이 다르다고 더 많은 유용한 정보가 있다고 확정하지 않는다. 동적 윤곽과의 중복은 가능한 설명이며 이번에는 이를 제거하는 추가 ablation을 실행하지 않는다.

## 5. 단계 B — adapter 내부의 ON/NULL 차이를 추적

adapter-only 계산은 DiT 없이 CPU 또는 작은 GPU phase로 먼저 할 수 있다. 네 사례·세 sigma·세 checkpoint의 ON/NULL 총72회가 기본이다. 같은 값이 메인 forward에서 관측되면 중복 계산 대신 재사용한다. 변경된 연산의 진단용 사본은 원래 forward 값과 일치해야 한다.

관측 경계:

| 경계 | 실제 내용/shape |
|---|---|
| P0 | PointCondition: 좌표·가시성·패치·bit |
| P1 | concatenated features `[33,K,303]` |
| P2 | MLP point features `[33,K,192]` |
| P3 | Gaussian weights `[33,390,K]`, gate, support |
| P4 | frame별 splat `[33,390,192]` |
| P5 | group 평균 `[9,390,192]` → `[1,3510,192]` |
| P6 | 각 projection의 FP32 residual `[1,3510,1536]` |

각 경계에서 같은 공간의 ON/NULL을 비교한다. 서로 차원이 다른 P1/P2/P6의 원시 norm을 직접 나눠 “신호가 몇 배 줄었다”고 해석하지 않는다. RMS·차이 RMS·정의한 상대 차이·cosine을 해당 경계 안에서 계산한다. 영벡터 cosine은 null로 남긴다.

전체 평균만 보지 말고 **ON 또는 NULL의 실제 kernel support 합집합**, support 교집합, 시간별 값을 함께 기록한다. support는 결과를 보고 고른 threshold가 아니라 기존 gate 및 radius²≤9로 정의한다. 구조적으로 0인 공간이 많은 것은 자연스러울 수 있다.

### 시간 평균의 감소와 상쇄

P4에서 `d_t = splat_ON,t - splat_NULL,t`라 하자. 기존 group `[0]`, `[1..4]`, … `[29..32]`에 대해:

`eta = sqrt( sum_g |g| * ||mean_{t in g} d_t||_F² / sum_t ||d_t||_F² )`.

분모가 0이면 null이다. 동일 차원의 특징에서 정의한 이 지표는 평균 뒤 남는 ON/NULL 차이 에너지 비율이다. 필요하면 각 group·0 제외 구간을 함께 보고한다. 서로 반대인 차이가 상쇄되는지, 입력이 원래 작았는지 구분한다.

eta가 낮다는 것만으로 시간 집계가 최종 실패의 원인이라고 확정하지 않는다. 평균이 의미 있는 움직임을 손상했는지 또는 불필요한 변화를 줄였는지는 후속 증거가 필요하다. 이번에는 mean을 바꾸지 않는다.

## 6. 단계 C — 동일 noisy state에서 실제 전달 경로 측정

메인 표는 네 사례 × 세 sigma =12 probe다. 각 probe에서 아래 7개 prediction을 얻는다.

1. native BASE
2. custom adapted_forward bypass
3. C-009 checkpoint000 ON
4. checkpoint128 ON
5. checkpoint128 NULL
6. checkpoint256 ON
7. checkpoint256 NULL

정상 **84 full model forward**. 처음 세 조건은 관측 경로 및 zero-init 보존 확인이면서 BASE 비교다. step000 ON/NULL 모두 projection이0인지 CPU에서 확인하고 NULL용 full forward는 추가하지 않는다.

native/bypass/zero는 기존 정해진 tolerance를 그대로 적용한다. 원래 exact인 조건은 exact를 기록한다. 불일치가 나타나면 진단 코드가 기존 의미를 바꿨는지부터 확인한다. 결과에 맞춰 tolerance를 늘리지 않는다.

### 관측 지점과 실제 가산값

block 26/27/28/29 각각에서 아래를 관측한다.

- `h_l`: adapter addition 직전 hidden
- `r_l`: FP32 projection 결과
- `r_cast`: backbone dtype으로 변환한 residual
- `h_plus`: 실제 BF16 addition 직후 hidden
- `d_eff = float(h_plus)-float(h_l)`: 실제 가산된 차이
- block 연산 후 hidden, VACE hint 가산 후 hidden(해당 시)
- head 직전 hidden, 최종 predicted velocity

보고:
- residual/hidden RMS 비율: 전체 및 support
- r_l→r_cast의 양자화 차이
- r_cast→d_eff의 addition rounding 차이
- intended residual이 비영인 항목 중 실제 hidden이 변하지 않은 비율
- zero는 gate 밖의 구조적0과 수치적으로 소실된0을 분리
- ON/NULL의 각 경계 차이와 시간별·token별 영향

**전체 precision을 FP32로 바꿔 새 forward를 만들지 않는다.** 관측·통계만 FP32/필요한 합산은 FP64로 한다. 실제 계산은 원래 BF16 경로를 유지한다. `d_eff/r_l`가 항상 0~1이어야 한다고 가정하지 않는다. rounding으로 일부 값이 커지거나 방향이 바뀔 수도 있다.

ON/NULL은 block 26 이후 서로 다른 hidden 경로다. 후속 hidden 차이는 이전 block의 누적 영향도 포함한다. 이 표만으로 특정 block 하나의 독립 인과효과를 확정하지 않는다.

생성 특징 주입이 국소적이어도 이후 attention으로 배경까지 영향을 줄 수 있다. 최종 속도 차이는 객체·배경 영역별로도 기록한다. 상대 차이가 작은 것과 정답을 향한 변화가 작은 것은 별도로 판단한다.

### 계측의 비간섭

기존 함수의 순서·dtype·state/RNG를 유지하는 observer를 우선한다. 내부 local 변수 관측에 얇은 진단 사본이 필요하면 변경 diff를 남기고, 원래 함수와 같은 입력에서 출력 일치를 검증한다. 작동을 바꾸는 monkeypatch나 global 상태 변경을 두지 않는다.

bear/elephant, sigma≈0.50, checkpoint256 ON/NULL에서 관측 OFF 원본 호출과 비교하는 최대4 forward를 허용한다. 같은 상태 반복의 수치 바닥 확인으로 최대2 forward를 허용한다. 계측 수치 차이가 같은 경로 반복 오차보다 유의하게 큰지도 기록한다. 임의의 통계적 유의성은 주장하지 않는다.

## 7. 가장 중요한 수학 진단 — 잔차 크기와 정답 방향 분리

현재 `balanced_loss`와 동일한 가중 내적을 정의한다. 영상 latent의 channel 수를 C, soft loss mask를 M이라 하자.

`<a,b>_obj = sum(M*a*b)/(C*sum(M))`

`<a,b>_bg = sum((1-M)*a*b)/(C*sum(1-M))`

`<a,b>_W = <a,b>_obj + <a,b>_bg`.

실제 broadcast·채널 평균 순서를 기존 코드와 맞춘다. 두 항을 다시2로 나누지 않는다.

BASE 예측을 v_B, adapter 예측을 v_A, 알려진 FM target을 u*로 놓고:

`e_B = u* - v_B`

`delta = v_A - v_B`

그러면:

`L_A - L_B = ||delta||_W² - 2<delta,e_B>_W`.

각 probe에서 다음을 같이 남긴다.
- L_BASE, L_ON, L_NULL, 객체/배경별 값
- ||e_B||_W², ||delta||_W², <delta,e_B>_W
- 가중 cosine과 undefined 처리
- 직접 계산한 loss 차이와 분해식의 수치 일치

**ON이 NULL보다 유용한 변화인지도 별도로 계산한다.**

`delta_motion = v_ON - v_NULL`

`e_NULL = u* - v_NULL`

`L_ON - L_NULL = ||delta_motion||_W² - 2<delta_motion,e_NULL>_W`.

이 분해는 같은 정상 context·state·text·target에서만 사용한다. 다른 checkpoint, sigma, clip은 각각 독립 비교다. FP32로 cast한 예측을 이용하고 합산 오차가 크면 reduction만 FP64로 처리한다. 직접 loss 값과 실제 의미는 유지한다.

해석:
- delta≈0: 현재 예측 개입이 작음.
- delta가 있으나 dot가0/음수: 정답 오차를 줄이는 방향의 보정이 약함.
- dot가 양수여도 ||delta||² 항이 더 크면 loss는 증가할 수 있음.
- ON–NULL이 더 작아졌다는 것만으로 source trajectory를 불필요하다고 결론내리지 않음.

이것은 one-step FM 보정의 방향이다. 발 접촉·정체성의 직접 점수나 최종 영상의 개선 증명으로 올리지 않는다. 더 큰 residual이 자동 해법이라는 결론도 금지한다.

## 8. 단계 D — parameter gradient 진단, optimizer update는 0

네 사례 × sigma≈0.50/0.05 × ON/NULL × checkpoint256만 수행한다.
정상 **16 forward + 16 backward-equivalent VJP**다. 메인과 같은 probe에서 실행해 예측값을 비교한다.

- 전체 backbone 고정, 기존 parameter의 `.grad`는 None 유지.
- adapter parameter에 대한 미분만 허용하되 값은 불변.
- 첫 adapter 이후의 frozen blocks/head는 입력 미분을 전달해야 함.
- C-006/C-009의 training forward·non-reentrant checkpointing 경로 재사용.
- optimizer를 만들지 않는다. optimizer.step/EMA/weight_decay 실행0.
- gradient clearing과 checkpoint parameter hash의 전후 일치 확인.
- `.eval()` 상태와 autograd 활성 여부를 구분한다.

balanced FM loss로 다음을 계산한다.
- MLP와 projection별 gradient norm/RMS
- 같은 parameter shape 안의 ON/NULL gradient cosine·차이
- `RMS(g*parameter)` 같은 보조 scale-aware 통계, 단 의미 과장 금지
- 실제 주입 residual 및 공통 motion context에 대한 gradient: 필요한 소수 텐서만

첫 linear의 입력 column 그룹은 실제 concat 순서를 확인한 뒤 나눈다.
- endpoint patches: 0:288
- anchor validity: 288:290
- q: 290:292
- delta q: 292:294
- endpoint offsets: 294:298
- time: 298:299
- visibility/validity: 299:301
- motion bit: 301:302
- sigma: 302:303

그룹 크기가 다르므로 norm 합만 비교해 288차원 외형이 지배한다고 주장하지 않는다. 입력 자체 RMS, gradient 원소당 RMS, 차원 수를 함께 기록한다. 첫 layer weight gradient는 **원래 좌표 tensor에 대한 미분이 아니며**, 좌표가 Gaussian weight로 들어가는 경로도 전부 설명하지 않는다.

좌표 입력은 코드에서 `.detach()`된다. `condition.positions.grad is None`를 궤적 무시의 증거로 쓰지 않는다. 데이터 입력의 detach는 adapter parameter 학습 단절과 다르다.

gradient의 크기만으로 “몇 update 더 하면 된다”고 예측하지 않는다. 같은 자료의 gradient가 남았어도 일반화·수렴·지각 품질을 보장하지 않는다. 실제 parameter update나 가상 1-step optimizer를 실행하지 않는다.

## 9. 단계 E — 좌표 유한 차분으로 실제 함수 민감도 확인

입력 detach를 제거해 학습 함수를 바꾸지 않는다. 별도의 진단 condition 복사본에서 좌표를 바꿔 실제 forward 반응을 측정한다. 이것은 원본과 다른 동작의 합성을 성공시키는 테스트가 아니라 **함수 민감도 검사**다.

고정 범위:
- 네 사례, sigma≈0.50, checkpoint256 ON, positive text
- 사례당 한 track
- 수평 x 방향만
- perturbation 크기 4px와8px 두 개는 사전 고정된 수치 분해능 확인용
- 각 크기의 +/− 두 방향, 총 최대16 forward
- 기준 ON forward는 메인 결과 재사용

track 선정은 GPU 결과를 보기 전에 입력만으로 결정한다.
1. 양끝 anchor_valid이고 중간 공통 유효·가시 프레임이12개 이상.
2. ±8px perturbation이 영상 범위 안에서 가능한 track.
3. 후보 중 ON–NULL의 가시 위치 RMS 차이가 가장 큰 track; 동률이면 낮은 ID.
4. 후보가 없으면 해당 사례는 FD_NOT_AVAILABLE. 새 tracker나 다른 사례로 바꾸지 않는다.

고정 변위:
`q'_x(t,k)=q_x(t,k) ± (epsilon_px/416)*sin²(pi*t/32)`.
끝점 t=0,32의 변위는 코드에서 정확히0으로 둔다. 나머지 점은 동일하다. patch·anchor_valid·visibility·validity·motion bit·bbox/kernel width·sigma는 고정하고, native adapter가 현재 위치로부터 velocity와offset을 원래대로 다시 계산하게 한다.

out-of-range를 조용히 clamp하지 않는다. 발생하면 그 perturbation을 무효로 남긴다. Gaussian cutoff support가 바뀌었는지 별도로 기록한다. Boolean gate와 cutoff가 있으므로 해석을 부드러운 Jacobian 하나로 과장하지 않는다.

계산:
`D_epsilon = [v(q_plus)-v(q_minus)]/(2*epsilon_px)`.

- 출력 sensitivity의 단위는 velocity/pixel.
- 객체·배경별 RMS와 adapter-only 각 경계의 변화.
- 4px/8px의 차분 방향 cosine과 크기 관계.
- 같은 경로 반복 오차·BF16 addition 분해능보다 반응이 큰가.

하나의 epsilon에서 변화가0이라고 완전한 불감성을 선언하지 않는다. 국소 scale/선정 track 범위로 한정한다. 임의 궤적으로 바꿨으므로 원본 target을 이 perturbation의 정답이라고 쓰지 않는다. 새로운 motion target의 품질·접촉 정확도를 이 검사로 판정하지 않는다.

## 10. 선택적 기존 rollout 상태 확인 — 새 생성은 하지 않는다

one-step 진단을 실제 생성과 연결할 때는 한계를 명확히 둔다. C-009 NEW_ON_5에 이미 저장된 정밀한 pre-step latent·실제 sigma·context가 있는 경우에만 다음을 수행할 수 있다.

- elephant의 기존 NEW_ON_5 경로에서 sigma≈0.95/0.50/0.05에 가장 가까운 저장 상태 최대3개.
- 각 동일 저장 state에 BASE/NEW_ON256/NEW_NULL256, positive text만 적용.
- 최대9 forward, 별도 선택 예산.
- 상태의 pre/post-step 구분과 해당 timestep을 반드시 확인.

자료가 없거나 저장 상태가 새 white checkpoint의 경로인지 불명확하면 ROLLOUT_NOT_AVAILABLE로 생략한다. old/red checkpoint나 BASE의 저장 경로를 NEW_ON rollout이라고 바꾸어 부르지 않는다. 저장물을 얻기 위한 새 sampler는 승인 범위가 아니다.

여기서는 ground-truth velocity가 없다. target latent를 이용해 epsilon을 역산한 뒤 FM 정답이라고 만들지 않는다. 예측 변화·잔차 전달만 보고한다. one-step 상태와 생성 상태의 차이가 어떤 원인인지 확정하지 않는다.

## 11. 계측 구현과 수치·메모리 원칙

경량 단계부터 수행한다. 먼저 CPU/adapter-only 자료가 유효한지 확인한 뒤 DiT 진단을 진행한다. 기존 학습용 VAE/T5 cache가 있으므로 encoder를 다시 올릴 필요 없다. 실제 분석 단계에는 기존 DiT/VACE와 작은 adapter를 사용한다.

- 원래 forward의 native 수학·힌트 순서·dtype·sigma를 유지한다.
- 입력과 캐시를 in-place 변경하지 않는다.
- observer 저장은 detach+필요한 clone으로 mutable view 문제를 막는다.
- forward graph는 한 셀씩 해제한다. 12개 probe의 모든 activation graph를 동시에 잡지 않는다.
- 비교에 필요한 hidden은 한 probe의 쌍별로 CPU에 잠깐 보관하고 통계 후 해제한다.
- 전 attention map·매 layer 대형 dump는 하지 않는다.
- 기존 white-mask manifest 확인을 재사용하고 C-008 전체 encoder 감사를 반복하지 않는다.
- prefix를 재사용하려면 같은 z/sigma/text/VACE 조건인 셀 안에서만 기존의 안전한 방식으로 한다. probe 사이에 noisy-state-dependent prefix를 재사용하지 않는다. 새로운 cache runtime은 만들지 않는다.

진단용 관측 파일은 최소 summary·일부 재현 tensor로 제한한다. normal tensor 범위에서 finite인지 먼저 확인하고, NaN/Inf이면 그 이후 크기/방향 해석은 중단한다. 의도된 fault를 넣어 가드를 시험하지 않는다.

## 12. 계산 예산과 종료 범위

| 단계 | 정상 상한 |
|---|---:|
| adapter-only | 72회 + 유한 차분에 필요한 소수 호출; 실제 수 기록 |
| main native/bypass/zero/128/256 | 84 full forward |
| 관측 OFF 비교 | 4 full forward |
| 같은 경로 repeat | 2 full forward |
| gradient 진단 | 16 forward +16 backward/VJP |
| 좌표 유한 차분 | 16 full forward |
| 선택적 저장 rollout replay | 최대9 full forward |
| **정상 full forward 합계 상한** | **131회** |
| 기계적 복구/재측정 예비 | **8 full forward** |
| **총 full forward 상한** | **139회** |

gradient checkpointing의 backward 내 block 재계산은 full model_fn forward와 별도로 기록한다. “16 backward”를 계산비용0처럼 취급하지 않는다. standalone projection·prefix 재사용 호출도 장부에서 구분한다.

Optimizer update0, 신규 sampler0, VAE encode/decode0, 모델/자료 다운로드0, 새 imagegen0, SAM/CoTracker0. 기존 원영상으로 overlay·시트·검토용 재생물을 만드는 CPU 처리만 허용한다. 파생물을 신규 생성 성과로 세지 않는다.

전체 작업 상한3시간. 마지막20분은 결과·해설·전달에 남긴다. 이는 승인 범위이지 예상 완료시간이 아니다. 모든 상한을 소진하는 것이 목표가 아니며 입력 차이가 거의 없거나 자료가 없으면 해당 결론을 좁게 기록한다.

단순 경로·import·observer 오류는 같은 작업에서 고친다. 이미 성공한 진단을 품질상 마음에 들지 않는다는 이유로 반복하지 않는다. 실제 안전 중단·OOM·외부 작업은 자동 우회하지 않는다. 기존 PSI/headroom/worker swap/allowlist를 변경하거나 예전 절대0 swap 가드를 복원하지 않는다. 새 launcher·서비스 정책을 만들지 않는다.

예산 부족 시 선택적 replay부터 생략하고, 단계별 실측과 명확한 결론 범위를 남긴다. 정해진 자료를 확인할 수 없으면 임의 생성 자료로 채우지 않는다.

## 13. 해석 규칙과 다음 변경 하나 선택

최종 결론은 한 숫자나 전체 gradient norm이 아니라 증거 사슬로 작성한다.

| 지지되는 관측 | 가능한 다음 방향 — 이번에는 실행하지 않음 |
|---|---|
| ON/NULL의 관측 가능한 입력 차이부터 작다 | 움직임 사건·선택점·대조 설계 개선 |
| 입력은 다른데 MLP나시간 집계에서 차이가 크게 줄어든다 | 표현·시간 집계 방식 하나 변경 검토 |
| context는 다른데 projection이 거의 같은 residual을 만든다 | projection 학습·목적·앵커 의존성 검토 |
| intended residual은 있으나 실제 addition이 상당부분 지워진다 | 수치/정규화/주입 방식 검토; 무작정배율증대 금지 |
| hidden은 달라지나 예측 변화는 작다 | 주입 위치·현재 hidden을 활용하는 구조 검토 |
| 예측 변화가 정답 오차와 정렬되지 않는다 | 목적함수·조건 중복·상태 의존적 보정 검토 |
| train에서 유용하나 validation에서는 약하다 | 소표본 일반화·데이터 다양성 검토 |
| 모든 경계의 영향은 있으나 작고 유용성도 미입증 | 병목 하나를 확정하지 말고 우선 가설·반증 조건 제시 |

주의:
- step128과256의 차이가 있다고 미래 update의 결과를 예측하지 않는다.
- 큰 gradient는 “더 오래 학습하면 해결”의 증거가 아니다.
- 작은 weighted FM error는 발/접촉이 맞다는 뜻이 아니다.
- 입력·representation norm은 feature 좌표계에 의존한다. 다른 층 사이 직접 크기 비교를 원인으로 삼지 않는다.
- 네 block 모두를 연쇄 주입하므로 후반 변화는 누적 효과다.
- 입력 detach 때문에 생긴 None gradient와 기능상의 불감성을 구분한다.
- NULL에는 여전히 endpoint 정보와 동적 윤곽이 있다. 이 실험은 point condition의 **추가적 기여**다.
- 입력한 noisy state 자체가 중간 target 정보를 포함하는 학습형 probe라는 점을 명시한다. 모델이 point를 덜 사용하는 것이 곧 생성 시 point가 불필요하다는 결론은 아니다.

판정 예시: INPUT_CONTRAST_LIMITED, FEATURE_ATTENUATION_OBSERVED, EFFECTIVE_UPDATE_ROUNDING_OBSERVED, READOUT_INSENSITIVE_AT_PROBES, MISALIGNED_CORRECTION, TRAIN_VALIDATION_GAP, DIAGNOSTIC_INCONCLUSIVE. 증거가 허용하는 범위에서만 쓰고 강제 단일 원인 분류는 하지 않는다.

**완료 기준은 잔차 숫자 몇 개가 아니라, 다음에 바꿀 요소 하나와 그 선택 근거·반증 조건을 제시하는 것이다.** 근거가 약하면 약하다고 명시하되, 같은 검사를 무한 반복하는 로드맵은 만들지 않는다. 실제 구조/학습 변경은 사용자와 다음 의뢰에서 결정한다.

## 14. 산출물·한국어 해설·전달

실행 전 PLAN·probe seed/grid·사례·예산을 고정한다. 작은 기록 세트로 끝낸다.
- PLAN.md: 고정 계약과 새 세션 인수 정보(민감 경로는 private)
- RESULTS.md: 원인 후보·근거 사슬·다음 변경 하나
- METRICS.json 또는 동등한 구조화 파일: input/feature/block/prediction/gradient/finite-difference
- PROVENANCE.json: white cache·checkpoint·probe·코드 hash
- LESSON_KO.md: 아래 수식과 실제 결과 연결
- REPRODUCE.md, COSTS.json, DELIVERY.json

LESSON_KO 필수 내용:
1. 표면점 추적·관절 의미·가시성의 구분.
2. 입력이 다른 것, 모델이 반응하는 것, 정답으로 좋아지는 것의 차이.
3. FP32 residual·BF16 cast·실제 addition의 차이.
4. 시간 평균의 에너지 감소와 그것이 의미적 손실을 바로 증명하지 않는 이유.
5. `L_A-L_B=||delta||²-2<delta,e>`와 ON–NULL 분해, 객체·배경 가중 내적.
6. parameter gradient·입력 Jacobian·유한 차분의 차이; 원래 detach의 의미.
7. unit/feature scale이 다른 gradient norm을 무턱대고 비교하면 안 되는 이유.
8. 같은-state one-step과 실제 rollout·최종 영상의 한계.
9. 현재 adapter가 sigma·조건은 보지만 residual 생성 MLP에 현재 hidden을 직접 입력하지 않는 사실과, 그것이 실패 원인이라는 단정은 별개임.
10. 이번에 확인한 것과 확인하지 못한 것을 실제 함수·shape·수치에 연결.

검토 뷰어는 기존 C-009 영상을 참고 패널로 재사용하고, 새 생성이 아님을 표시한다. 다음을 보기 좋게 정리한다.
- source 위 ON/NULL 궤적과 가시성
- sigma·checkpoint별 전달 경계 그래프
- 객체/배경의 보정 방향·loss 분해
- train과validation의 비교
- residual 의도값/실효값·유한 차분 결과
- 결론의 확실성과 한계

과거의 temporal=UNVERIFIED를 수치 진단만으로 바꾸지 않는다. 기존 영상을 이번에 실제 연속 시청한 경우에만 누가·무슨 속도·어떤 범위를 검수했는지 별도 기록한다.

원본 cache·checkpoint와과거 판정은 보존한다. C-010에서는 adapter 채택·품질 PASS를 새로 주장하지 않는다. 새 checkpoint를 만들지 않는다(필요하면 불변 state hash 영수증만 보존).

compact는 뷰어·작은 시트·구조화 결과·해설·필요한 기존 MP4만 포함한다. 대형 activation·가중치·과거 ZIP은 중복 포장하지 않는다. 실제 생성 MP4의 화질을 낮추어 파일을 줄이지 않는다. 필요한 재현 tensor는 비공개 경로와 hash만 연결한다.

Spark/Mac의 실제 /tmp 또는 기존 승인 위치에 보존하고 CRC·manifest·실제 추출·전송 hash를 확인한다. 접근하지 못한 호스트까지 PASS라고 쓰지 않는다. 공개 Git에는 비민감 코드·문서·hash만, 개인 경로·PID·token·영상·latent·가중치는 자동 공개하지 않는다.

HISTORY/ROADMAP에 정상 캐시 이후의 진단이라는 위치를 연결하고, 해당 파일만 commit/push한다. branch와 remote SHA를 확인한다. 자기 프로세스만 종료하고 다른 서비스를 건드리지 않는다.

### 최종 보고의 첫 질문

1. 네 영상의 ON/NULL 입력에 구별할 만큼의 내부 움직임 차이가 있었는가?
2. 그 차이가 어느 계산 경계까지 전달됐는가?
3. 의도한 residual과 실제 hidden 변화는 어떻게 달랐는가?
4. 최종 예측 변화는 정답 오차를 줄이는 방향이었는가?
5. train과validation, sigma, checkpoint별로 일관된가?
6. gradient와유한 차분은 무엇을 지지하며 무엇을 설명하지 못하는가?
7. 이제 바꿀 요소 **하나**는 무엇이며 왜 그것인가?

검사 개수·파일 해시보다 위 답을 먼저 제시한다. 이번 작업 뒤에는 추가 학습·scale/seed 탐색·새 sampler를 자동 시작하지 않는다.

---

## 근거 자료

이 문서의 새로운 probe·통계·예산은 C-010의 제안 설계다. 아래는 기존 구현/결과 확인 근거이며, 링크의 존재가 현재 Spark 파일 검증을 대신하지 않는다.

- [R1] C-009 결과: https://github.com/hyunlord/make-meme/blob/fbb07f1/docs/research/experiments/C-009-corrected-conditioning-retrain/RESULTS.md
- [R2] 현재 adapter: https://github.com/hyunlord/make-meme/blob/fbb07f1/docs/research/experiments/C-006-motion-point-adapter-pilot/code/point_adapter.py
- [R3] PointCondition와make_null: https://github.com/hyunlord/make-meme/blob/fbb07f1/docs/research/experiments/C-006-motion-point-adapter-pilot/code/point_features.py
- [R4] block/VACE/gradient 경로: https://github.com/hyunlord/make-meme/blob/fbb07f1/docs/research/experiments/C-006-motion-point-adapter-pilot/code/wan_adapter_forward.py
- [R5] 기존 loss와상태: https://github.com/hyunlord/make-meme/blob/fbb07f1/docs/research/experiments/C-006-motion-point-adapter-pilot/code/training_state.py
- [R6] C-009 재현: https://github.com/hyunlord/make-meme/blob/fbb07f1/docs/research/experiments/C-009-corrected-conditioning-retrain/REPRODUCE.md
- [R7] detach: https://docs.pytorch.org/docs/stable/generated/torch.Tensor.detach.html
- [R8] autograd 모드: https://docs.pytorch.org/docs/stable/notes/autograd.html

stable 문서는 설명용이다. 현재 설치 버전을 자동 업그레이드하지 않고 실제 로컬 API·실행 코드를 사용한다.
