# C-007 통합 작업 의뢰서
## 동결된 C-006 adapter의 단일 예측·CFG 결합·반복 생성 안정성 진단

- 저장소: `hyunlord/make-meme`
- 부모 커밋: `c4aef32de21de4073bd4eb1861df4d35f2eda793`
- 부모 실험: `C-006-motion-point-adapter-pilot`
- 권장 실험 경로: `docs/research/experiments/C-007-frozen-adapter-cfg-diagnostics/`
- 의뢰서 보존 경로: `docs/research/work_orders/C007_FROZEN_ADAPTER_CFG_DIAGNOSTIC_KO.md`

**이번 의뢰를 전달하면 아래의 동결 모델 진단과 신규 영상 최대 네 개 생성을 승인하는 것이다. 학습·모델 다운로드·안전 정책 변경은 승인 범위가 아니다.**

---

## 0. 목적과 완료 조건

C-006에서는 point–anchor adapter 1,275,072개 parameter를 256회 학습했다. 고정 validation probe의 one-step FM loss는 감소했지만, BASE보다 ON/NULL의 색 번짐·중복 윤곽·배경 회귀가 컸고 동작 이득은 미입증이었다. 이는 부모의 기록이며 이번에 소급 변경하지 않는다. [R1–R3]

이번 질문은 다음이다.

> 같은 checkpoint를 고정했을 때, 회귀는 단일 텍스트 분기의 예측에서도 나타나는가, positive/negative 분기의 CFG 결합에서 커지는가, 아니면 반복 생성이 진행되면서 더 커지는가?

이 세 원인은 동시에 존재할 수도 있다. 처음부터 CFG, 학습량, residual 크기 중 하나를 정답으로 선언하지 않는다.

완료 산출물은 다음을 함께 포함한다.

1. 두 validation 영상에서 높은·중간·낮은 sigma를 포함한 동일 입력 예측 진단.
2. 한 validation 영상의 **BASE/ON × CFG 1/5** 신규 영상 네 개.
3. 생성 경로의 같은 latent에 BASE와 adapter를 각각 평가한 동결 상태 비교.
4. 원인이 확인된 부분, 지지된 가설, 여전히 미확정인 부분을 나눈 결과와 한국어 해설.

CPU 검사나 loss 표만 제출하고 끝내지 않는다. 유효한 실행 계약과 안전 조건 아래에서 실제 네 영상을 생성·비교한다. 반대로 수치 차이를 줄이기 위해 학습·scale 탐색·새 모델을 시작하지 않는다.

## 1. 현재 작업과 과거 기록 보존

현재 C 트랙의 branch/worktree·HEAD·중복 실행 여부를 확인한다. 부모 커밋으로 reset하거나 기존 파일을 덮어쓰지 않는다. 최신 HEAD가 부모 이후라면 관련 변경만 읽고 기록한다.

읽을 부모 자료:

- `RESULTS.md`, `METHOD.md`, `TRAIN_CONFIG.json`, `DATA_SPLIT.json`, `NUMERICS.json`
- `code/train_adapter.py`, `training_state.py`, `point_adapter.py`, `point_features.py`
- `code/wan_adapter_forward.py`, `generate_video.py`, `runtime_common.py`
- 실제 설치 DiffSynth의 `model_fn_wan_video`, CFG loop, `FlowMatchScheduler(Wan)`
- C-006에서 실제 정상 완료한 공통 실행·보호 경로
- HISTORY·ROADMAP

현재 실행되는 1.3B 환경을 그대로 사용한다. C-005 14B 복구, 과거 가드 수정, 새로운 launcher·supervisor·서비스 관리자 개발은 하지 않는다.

C-006의 NO_ESTABLISHED_GAIN과 다른 A/B/C 판정, 실패·UNKNOWN·NOT_CLEAN 기록을 유지한다. 이번은 C-006의 checkpoint를 분석하는 후속 실험이지 과거 결과의 정정이나 재채점이 아니다.

## 2. 입력·checkpoint·평가 자료 고정

### 2.1 가중치

- 기존 `Wan2.1-VACE-1.3B`, T5, VAE, tokenizer, adapter 구현을 재사용한다.
- 저장된 `checkpoint-000.pt`, `checkpoint-128.pt`, `checkpoint-256.pt`를 읽기 전용으로 사용한다.
- 주 영상 네 개 중 ON에는 **checkpoint-256만** 사용한다.
- 128의 probe가 좋아 보여도 이번 영상 checkpoint를 128로 교체하지 않는다.
- 모든 parameter를 평가 모드로 두고 이번 작업의 optimizer 생성·backward·update는 0회다.
- checkpoint hash를 한 번 기록한다. 매 forward마다 전체 가중치를 재해시하지 않는다.
- step 0/128 파일이 없으면 해당 열을 NOT_AVAILABLE로 두고 새 학습으로 복원하지 않는다. step 256이 없으면 요청한 핵심 실험을 수행할 수 없으므로 구체적으로 보고한다.

### 2.2 데이터

C-006의 실제 분할은 validation=`elephant`, `goat`다. [R4]

- one-step 진단: **elephant와 goat 두 영상**.
- 주 영상 2×2: **elephant 한 영상**. validation 이름 사전순 첫 항목으로 선택한 것이다.
- source·실제 양끝 앵커·동적 layout·text·mask·point exclusion·궤적 cache를 그대로 재사용한다.
- 결과를 보고 goat나 C-006 test 영상으로 교체하지 않는다.
- `horsejump-low`, `lucia`, 기존 편집 개 영상은 이번 신규 생성 대상이 아니다.
- 이번 결과는 개발용 validation 진단이다. 새 held-out 최종 평가나 일반화 성능으로 부르지 않는다.
- 33프레임을 33개의 독립 사례로 세지 않는다.

### 2.3 정답 접근과 생성 입력을 분리

one-step 진단에서는 validation cache의 `clean_latent`와 loss mask를 읽어도 된다. 그것은 진단용 정답이며, sampler 초기값·중간 입력으로 사용하지 않는다.

C-006 validation cache에는 clean target latent가 있으나, 기존 생성 코드는 이를 포함한 cache를 거부하도록 되어 있다. **이 assertion을 삭제해서 validation cache를 그대로 생성기에 넘기지 않는다.**

생성 전, 기존 검증 함수를 이용해 필요한 point·독립 endpoint patch·validity·bbox·메타데이터만 복사한 whitelist 기반 inference sidecar를 만든다. clean latent, 정답 중간 RGB 특징, loss mask 등 진단 전용 값은 제외한다. 정확한 허용 key 목록과 원본 cache 계보를 기록한다.

영상 생성의 VACE 조건은 이전처럼 실제 양끝과 동적 layout에서 다시 인코딩한다. clean target을 재사용한 생성 결과를 동작 제어 성공으로 보고하지 않는다.

## 3. 이번에 바꾸는 것과 바꾸지 않는 것

변경 가능:

- 읽기 전용 수치·residual 관측.
- CFG 1 또는 5를 실제 pipeline 호출에 전달하는 설정.
- 새로운 출력·진단 파일 경로.
- 진단용 point mode ON/NULL 전환과 저장 checkpoint 로드.

변경 금지:

- adapter scale, kernel 폭, point 수·선택, 시간 pooling, block 주입 위치.
- prompt·negative prompt·앵커·동적 윤곽·생성 마스크.
- learning rate·학습 횟수·loss·weight decay 등의 재학습.
- timestep/solver/sigma shift·해상도·프레임 수.
- CFG rescale·clamp·dynamic thresholding·양끝 덮어쓰기.
- attention backend·dtype·양자화·새 backbone.
- tracker/SAM/VAE cache의 불필요한 재추출.
- 이미지/영상 후합성·색보정·업스케일·보간.

CFG를 낮춰 좋은 영상을 고르는 최적화가 아니다. **두 CFG 수준에서 adapter의 증분 효과가 어떻게 달라지는지 비교**한다.

## 4. 구현에서 반드시 확인할 두 지점

### 4.1 CFG 설정이 실제 호출까지 전달되는가

C-006 `generate_video.py`는 `guidance: Literal[5.0]`이고 실제 호출에도 `cfg_scale=5`가 고정되어 있다. [R5]

C-007의 작은 사본 또는 명시적인 패치에서:

- 허용 설정을 `Literal[1.0, 5.0]`로 제한한다.
- 실제 pipeline에 `cfg_scale=config.guidance`를 전달한다.
- 표시용 결과 JSON만 바꾸지 않는다.
- positive/negative 호출과 실제 effective CFG를 기록한다.
- CFG 1은 positive text branch만 호출한다. 텍스트·앵커·layout·point 조건을 끈 무조건부 생성이 아니다.
- CFG 5는 기존 비결합 positive/negative 호출 경로를 유지한다.

예상 정상 호출:

| 셀 | scheduler step | 생성에 사용한 model_fn call |
|---|---:|---:|
| BASE / CFG 1 | 50 | 50 |
| ON-256 / CFG 1 | 50 | 50 |
| BASE / CFG 5 | 50 | 100 |
| ON-256 / CFG 5 | 50 | 100 |
| 합계 | 200 | 300 |

추가 진단 forward는 별도 장부다. CFG 1의 추가 negative 평가를 정상 sampler 호출처럼 숨기지 않는다.

### 4.2 같은 sigma와 timestep을 쓰는가

원래 Wan training grid를 CPU에서 만들어 exact sigma와 timestep을 얻는다. 모델에 넣는 timestep과 adapter에 넣는 sigma를 따로 기록한다.

- training 진단용 grid: 1000개, shift 5.
- 생성용 grid: 50개, shift 5.
- grid 생성으로 inference scheduler의 상태를 몰래 덮어쓰지 않는다. phase별 scheduler를 별도로 만들거나 명시적으로 재설정한다.
- model call 횟수를 sampler step으로 착각하지 않는다. CFG 5의 두 branch는 같은 sigma와 pre-step latent를 사용해야 한다.

## 5. 실험 A — 동일 noisy state의 one-step 분해

### 5.1 probe grid

각 validation 영상에 대해 목표 sigma를 다음 다섯 값으로 고정한다.

`0.95, 0.75, 0.50, 0.20, 0.05`

현재 training grid에서 가장 가까운 index를 선택하고 exact sigma/timestep을 저장한다. 동일한 index로 중복 매칭되면 결과를 복제하지 말고 이유를 보고한다.

이는 기존 index 200/500/800이 높은 쪽에 치우쳤던 관측 범위를 낮은 sigma까지 넓히는 것이다. 기존 6개 loss 값의 정확한 재현 실험은 아니다.

noise는 영상별 독립 CPU Generator로 한 번 생성하고 다섯 sigma에서 재사용한다. 기본 seed는 `20261101 + validation 영상의 사전순 index`로 고정한다. 다른 checkpoint·mode·text branch에서도 동일한 z0, epsilon, z_sigma를 쓴다.

실제 noisy state와 target은 설치 scheduler로 만든다.

\[
z_\sigma=(1-\sigma)z_0+\sigma\epsilon,\qquad v^*=\epsilon-z_0.
\]

### 5.2 각 state의 평가 조건

두 text context를 각각 사용한다.

- `+`: 해당 영상의 기존 positive caption.
- `−`: 기존 negative prompt `blurry, distorted, deformed, watermark`.

negative는 빈 문자열·무조건부 branch·TRACK_NULL과 다른 개념이다. 정답 v*에 대한 negative branch loss는 기존 학습에서 사용한 감독 목적의 진단이지, 일반적인 negative conditioning의 참 정답이라고 해석하지 않는다.

한 state마다 아래 8개 predictor를 두 text context에서 평가한다.

1. native BASE
2. custom adapted_forward의 adapter bypass
3. checkpoint-000 / ON
4. checkpoint-000 / NULL
5. checkpoint-128 / ON
6. checkpoint-128 / NULL
7. checkpoint-256 / ON
8. checkpoint-256 / NULL

정상 상한: **2영상 × 5 sigma × 8 predictor × 2 branch = 160 core forward**.

한 번 계산한 prediction으로 여러 수치를 구한다. 지표마다 모델을 다시 돌리지 않는다. 큰 tensor는 state별 순차 처리하고 필요 요약 후 해제한다.

### 5.3 기본 계산 동등성

native BASE ↔ bypass ↔ step-0 adapter를 같은 state·branch에서 비교한다. zero-init 검사를 고잡음 한 지점에서만 통과한 것으로 끝내지 않는다.

C-006의 `atol=rtol=1e-3`를 우선 유지하고 max_abs·RMS·상대 오차를 함께 기록한다. 허용오차를 결과를 본 뒤 넓히지 않는다. 명확한 차이가 나타나면 해당 계산 경로·sigma·branch·입력 hash를 남긴다.

입력 준비의 단순 오류는 같은 작업 안에서 수정할 수 있으나, **기존 C-006 custom model 연산 자체의 실질적인 불일치가 확인되면 이를 조용히 고쳐 새 결과를 원래 C-006 checkpoint의 성능으로 보고하지 않는다.** 해당 경우 이번 primary causal 진단은 IMPLEMENTATION_MISMATCH로 한정하고 수리·재학습을 자동 시작하지 않는다.

검증된 범위에서만 기본 계산 보존을 주장한다. 전 입력에 대한 함수 동등성 증명이라고 쓰지 않는다.

## 6. one-step에서 측정할 값과 해석

### 6.1 분기별 예측 오차

positive와 negative 각각에 대해 기록한다.

- 전체 latent MSE.
- 객체 영역 평균 MSE, 배경 영역 평균 MSE.
- C-006의 `객체 평균 + 배경 평균` balanced loss.
- 각 분기의 native BASE 대비 변화량.
- diagnostic clean estimate `z_hat0 = z_sigma − sigma * prediction`의 정답 latent 오차.

clean estimate는 정답에서 만든 noisy state에만 이 의미로 평가한다. latent MSE를 영상의 동작·정체성 점수로 부르지 않는다. sigma별 값의 크기가 다른데 한 평균만 보여 개선이라고 하지 않는다.

### 6.2 CFG 변화의 정확한 분해

같은 z_sigma에서 BASE의 두 예측을 b+, b−, adapter의 두 예측을 a+, a−라 정의한다.

\[
\delta_+=a_+-b_+,\quad \delta_-=a_--b_-.
\]

\[
v_w=v_-+w(v_+-v_-),\qquad
\Delta_w=w\delta_++(1-w)\delta_-.
\]

따라서:

\[
\Delta_5=5\delta_+-4\delta_-=
\delta_++4(\delta_+-\delta_-).
\]

이 식은 **같은 입력 상태에서의 차이**다. 서로 다른 rollout의 같은 step prediction을 빼서 위 항으로 사용하면 안 된다.

기록:

- RMS(delta+), RMS(delta−), RMS(delta+−delta−).
- 두 delta의 cosine similarity와 norm.
- RMS(Delta1), RMS(Delta5).
- 각 CFG BASE prediction 크기 대비 변화 비율.
- 실제 guided prediction과 FP32로 재구성한 식의 차이.

통계는 FP32 이상으로 계산하되 기존 sampler의 BF16 연산을 FP32로 교체하지 않는다. 식의 수학적 동일성과 native BF16 rounding 차이를 구분한다. 분모/두 norm이 사실상 0이면 비율·cosine을 null로 두고 원시 norm을 보여 준다. 작은 분모로 큰 비율이 나왔다는 이유만으로 불안정 원인이라고 결론내리지 않는다.

`delta+=delta−`이면 추가 차이 증폭이 없으므로, CFG 5가 모든 adapter 오류를 무조건 5배 증폭한다고 쓰지 않는다.

**guided output을 unguided FM target v*에 맞춘 MSE만으로 CFG 오류를 판정하지 않는다.** CFG는 별도의 조건 강조 조합이다. 분기별 감독 목적과 CFG 변경량·실제 영상 품질을 구분한다. [R6–R7]

### 6.3 block residual의 실제 영향 크기

원래 26~29번 block 직전 residual 연산에서 다음을 읽기 전용으로 관측한다.

- 추가 전 hidden h의 RMS.
- FP32 projection residual r의 RMS.
- BF16 cast 이후 residual과 실제 덧셈 차이 `(h+r)-h`의 RMS.
- residual/hidden norm 비율.
- 전체 token뿐 아니라 실제 point splat support의 통계.
- 과도한 국소값을 찾을 수 있는 token별 norm의 p50/p95/max.

관측을 위해 projection을 두 번 계산하지 않는다. 원래 결과를 hook 또는 진단용 경로에서 받아 요약한다. hidden·output을 수정하거나 in-place 정규화하지 않는다.

ratio가 크면 곧바로 해롭다고 판정하지 않고, 분기·sigma·checkpoint·객체/배경의 예측 회귀와 함께 해석한다. 작은 local residual도 뒤의 attention을 통해 넓게 영향을 줄 수 있으므로 local 주입=local 출력이라고 가정하지 않는다.

## 7. 실험 B — validation elephant의 2×2 실제 생성

새 full sampler는 아래 네 셀만 수행한다.

| 순서 | predictor | guidance | 목적 |
|---|---|---:|---|
| 1 | native BASE | 1 | 단일 분기 기준 |
| 2 | adapter-256 ON | 1 | 단일 분기에서 adapter 영향 |
| 3 | native BASE | 5 | 기존 CFG 설정의 기준 |
| 4 | adapter-256 ON | 5 | adapter와 CFG 결합 |

NULL·128·다른 CFG의 full video는 이번에 추가하지 않는다. one-step 결과가 좋거나 나쁘다는 이유로 셀·checkpoint를 변경하지 않는다. 단, 실제 안전·수치·입력 오류는 기존 정책대로 처리한다.

고정 설정:

- C-006과 같은 VACE 1.3B·실제 DiffSynth 파일.
- 실제 source 양끝 앵커 + 동적 dataset-mask layout.
- 416×240·33프레임·preview16fps.
- Euler 50step, shift5, VACE scale1.0.
- BF16, SDPA, tiled VAE, TeaCache 등 근사 OFF.
- 기존 positive/negative text.
- inference seed20261028, CPU generator.
- 원래 양끝0/중간255 VACE mask와 33→9 압축 한계 유지.
- 원본이나 앵커로 출력 프레임을 덮어쓰지 않음.

네 셀의 실제 초기 noise, 논리 RGB/mask/text 조건, VACE context를 대조한다. cache 기반 진단과 실제 pipeline 인코딩의 context가 다른 경우 원인을 기록한다. input dtype·tile 설정 등의 차이를 검증 없이 무시하지 않는다.

원래 validation cache에서 whitelist로 만든 inference sidecar만 읽는다. 생성기에 source clean latent를 전달하지 않는다.

BASE는 original native model_fn, ON은 C-006의 adapted_forward를 사용한다. 학습 코드와 다른 연산을 신규 생성기에 만들지 않는다. .eval()/no_grad를 사용하고 신규 gradient를 만들지 않는다.

코드의 guided scale이 runtime까지 연결되고 CFG1은50call, CFG5는100call인지 반드시 확인한다. metadata와 실제 호출이 다르면 품질 해석 전에 오류를 표시한다.

## 8. 실험 C — 실제 생성 경로의 동결 상태 진단

### 8.1 rollout 관측

네 영상에서 각 scheduler step의 index, exact sigma, next sigma, latent RMS/범위, prediction RMS, Euler update norm을 기록한다. tensor를 전부 dump하지 않고 요약을 남긴다.

기존 결과는 읽기 전용이다. 이번 새 생성에서만 다음 다섯 **pre-step** 상태를 저장한다.

`0, 25, 40, 47, 49` — 0-based, exact sigma와 함께 저장.

현재50step shift5에서는 마지막 두 지점이 낮은 sigma 구간에 해당한다. index가 영상의 프레임 번호인 것처럼 쓰지 않는다.

저장 대상은 기본적으로 네 셀의 작은 latent snapshot과 해당 단계의 실제 branch/combined prediction이다. 최대20상태, 별도 raw trace 총량 목표256MiB 이하. 학습 가중치·attention tensor·모든 중간 activation을 반복 저장하지 않는다.

정상 sampler 중에는 추가 model call을 넣지 않는다. context/hash 기반 branch 식별과 step index를 함께 기록하며, call 번호의 짝홀만으로 분기를 추정하지 않는다. trace 저장·통계는 RNG를 소비하거나 tensor를 수정하지 않게 한다.

### 8.2 같은 상태에서 비교

CFG5의 두 경로 BASE_5와 ON_5에서 저장한 다섯 상태씩, 총10상태를 사용한다.

각 상태 z, sigma, text/VACE condition을 고정한 뒤:

- native BASE positive/negative.
- adapter-256 ON positive/negative.

를 평가한다. **최대40 core forward**다. 새 sampler를 진행하거나 진단 결과를 원래 trajectory에 되먹임하지 않는다.

각 상태에서 위 6절의 delta·CFG 변화·residual 요약을 구한다. 저장된 원래 branch prediction과 대응하는 재평가 prediction도 대조하여 replay의 수치 오차 범위를 기록한다.

다음 두 종류의 차이는 반드시 구분한다.

1. `같은 z에서 adapter와 BASE의 예측 차이`: adapter의 국소적 효과를 진단.
2. `각자 생성해 온 z_ON과 z_BASE의 차이`: 이전 단계의 누적 효과까지 포함.

두 경로가 멀어졌다는 사실만으로 현재 step adapter가 과도하다고 결론내리지 않는다. 반대로 같은 상태의 작은 차이도 반복될 수 있으므로 한 step의 norm만으로 전체 안정성을 보장하지 않는다.

### 8.3 생성 상태에 정답 velocity가 있다고 가정하지 않는다

생성 중 z에는 학습 probe처럼 고정된 `(z0, epsilon)` 경로가 알려져 있지 않다. reference z0를 억지 대입해 정답 velocity를 만들거나 generated state의 FM MSE라고 부르지 않는다.

생성 상태에서는 BASE 대비 변화·분기 불일치·update 크기·관측 영상 손상을 연결한다. 데이터 noisy-state에서의 작은 loss와 rollout에서의 차이를 같은 정답 오차로 직접 비교하지 않는다.

## 9. 실제 품질 비교와 원인 해석

원본·실제 양끝·동적 layout·네 출력을 나란히 보여 준다. source의 관측 가능한 사건을 생성 전에 짧게 고정한다. 큰 이동, 보이는 머리/다리의 순서, 가림, 배경 객체를 기록하고 가려진 관절·접촉 정답을 만들지 않는다.

전체33장과 `0/4/8/12/16/20/24/28/32`를 같은 인덱스로 비교한다. 시간 정렬·warp·출력별 다른 crop·좋은 프레임 선별을 하지 않는다.

평가 축:

- 대상 식별 가능성·외형.
- 원본의 거친 이동과 관측 가능한 부위 진행.
- 색 번짐·중복 윤곽·새 객체·배경 회귀.
- 첫/끝 앵커 충실도.
- 정적 인접 프레임 변화와 실제 연속 지각 품질의 구분.

CFG1의 ON만 CFG5 BASE와 비교해 좋아졌다고 쓰지 않는다. 핵심은 같은 CFG 안의 ON−BASE 차이가 두 CFG 수준에서 어떻게 달라지는지다.

수치 Q를 사용한다면 `D_w=Q(ON,w)−Q(BASE,w)`와 `D_5−D_1`을 제시할 수 있으나, 측정 불가능한 미세 동작에 가짜 점수를 만들지 않는다. 한 seed·한 영상의 차이이므로 통계적 상호작용이나 일반화를 증명한 것으로 쓰지 않는다.

가능한 해석은 중복 선택하며 근거를 함께 적는다.

- **BRANCH_REGRESSION:** CFG1에서도 같은 BASE 대비 명확한 회귀.
- **CFG_INTERACTION_SUPPORTED:** 동일 CFG 비교에서 CFG5의 증분 회귀가 커지고, 같은-state 분기 차이 측정도 그 설명과 양립함.
- **LOW_SIGMA_REGRESSION:** 낮은 sigma에서 분기 예측 오차·잔차 영향의 회귀가 일관되게 관측됨.
- **ROLLOUT_SENSITIVITY_OBSERVED:** teacher-forced probe에서는 제한적 변화지만 실제 생성 상태·경로에서 더 큰 이탈을 관측함. 곧바로 distribution shift의 유일 원인으로 확정하지 않음.
- **COMMON_ADAPTER_EFFECT:** ON/NULL의 변화가 유사해 궤적 이외의 공유 부분이 주요 후보.
- **IMPLEMENTATION_MISMATCH:** native/bypass·zero 또는 입력/branch 연결 차이가 원인 해석을 방해함.
- **INCONCLUSIVE:** 결과가 서로 다르거나 판단 근거가 부족함.

CFG1에서 회귀가 줄어도 동작 제어 성공이나 CFG1 기본 채택으로 올리지 않는다. 두 수준의 비교만으로 최적 CFG를 찾았다고 하지 않는다. 모든 가설에 반례·대안 설명을 남긴다.

실제 연속 재생의 지각 검수를 할 수 있으면 주체·속도·범위를 적는다. ffmpeg decode·브라우저 재생 성공·정적 시트만 확인했다면 `temporal=UNVERIFIED`를 유지한다. 한계 확인을 위해 사용자의 응답을 기다리며 나머지 결과 제출을 막지는 않는다.

## 10. 계측 때문에 동작을 바꾸지 않기

- 원래 함수의 실제 tensor를 읽어 요약한다. residual을 수정하거나 clamp하지 않는다.
- FP32 통계 계산은 분리하고 sampler 계산 dtype은 유지한다.
- read-only hook이 메모리를 계속 붙잡지 않도록 detach·요약 후 참조를 정리한다.
- no_grad와 .eval을 유지한다. checkpoint load 시 optimizer는 복구하지 않는다.
- module 재생성·진단 RNG는 별도의 generator 또는 fork_rng로 분리한다.
- 실제 sigma/context 선택은 추론 loop가 쓰는 값과 동일해야 한다.
- 새 진단용 scheduler가 sampler grid나 `.training` 상태를 오염시키지 않는다.
- inference sidecar의 clean-target 배제를 검사한다.
- 이전처럼 hook·가드·새 launcher 자체를 장기 별도 프로젝트로 만들지 않는다.

hook 변경으로 결과가 달라질 만한 연산이 들어갔다면 계획과 다르므로 기록한다. 결과를 보기 전 짧은 fixture에서 원래 반환값을 그대로 통과시키는지 확인한다. 무의미한 full-video 재현 호출은 추가하지 않는다.

## 11. 예산·안전·오류 처리

| 항목 | 정상 범위 |
|---|---:|
| one-step core forward | 최대160 |
| 실제 생성 중 core forward | 300 |
| 저장 rollout state의 추가 core forward | 최대40 |
| 정상 core forward 합계 | 최대500 |
| 정상 full sampler | 4회 |
| 정상 영상 decode | 4회 |
| 학습·backward·optimizer update | 0회 |
| imagegen·SAM·CoTracker 재추론 | 0회 |
| 모델·패키지·자료 신규 다운로드 | 0회 |

small fixture와 replay 차이 확인을 위한 예비 forward는 전체최대16회다. 500회와 따로 기록한다. 기준 없는 probe 추가나 다른 sigma/seed의 탐색에 쓰지 않는다.

정상 full sampler4회에 기계적 실패 복구 예비1회를 포함해 최대5회다. 예비가 실행되면 실제 step/call을 별도 합산한다. 완료한 셀은 다시 만들지 않는다. 품질이 나쁘다는 이유로 재생성하지 않는다.

final latent를 decode 전에 원자 저장·readback한다. decode/포장만 실패하면 저장물을 재사용한다. VAE-only 기계적 복구는 최대1회, sampler 재실행으로 대체하지 않는다.

- 단순 경로·인자·import·관측 코드 오류는 같은 범위 안에서 고치고 이어갈 수 있다.
- 기존 adapter의 본질적인 연산 오류를 발견하면 원본 증거와 영향을 기록한다. 임의로 알고리즘까지 바꿔 원래 실험의 연속으로 취급하지 않는다.
- 기존 C-006 성공 실행 경로와 보호 정책을 재사용한다.
- 가드·PSI·메모리·swap·allowlist·다른 서비스 설정은 변경하지 않는다.
- 실제 자원 위험·외부 작업 충돌은 자동 재시도나 우회하지 않는다.
- 모델은 순차 사용하고 진단 tensor만을 위해 추가 모델 상주를 만들지 않는다.

전체 작업 상한4시간, 마지막30분은 비교·문서·전달에 남긴다. 이는 승인 범위이지 예상 완료시간이 아니다. 대규모 관측 도구를 만들다가 영상 비교 예산을 소진하지 않는다.

모든 phase에서 model load 횟수, standalone forward, sampler forward, step, decode, 파일 준비 시간을 각각 기록한다. 관측 overhead를 원래 모델 속도처럼 보고하지 않는다. CUDA/host/cgroup 지표는 서로 합산해 전체 메모리라고 하지 않는다.

## 12. 결과 파일·GitHub·검토물

실행 전 다음을 고정한다.

- 의뢰서와 PLAN.
- validation 두 영상과 주 영상 elephant 선택.
- checkpoint0/128/256의 실재·hash.
- exact sigma grid·probe seed·inference seed.
- 2×2 셀과 실행 순서.
- context/정답 분리, 함수·설정 변경 diff.
- 예산과 품질 평가 기준.

권장 문서/수치:

- `PLAN.md`, `METHOD.md`, `RESULTS.md`, `LESSON_KO.md`
- `PROBES.jsonl` 또는 CSV, `BLOCK_STATS.jsonl`, `ROLLOUT_STATS.jsonl`
- `INFERENCE_INPUT_MANIFEST.json`, `COSTS.json`, `REPRODUCE.md`, `DELIVERY.json`

내용을 여러 파일에 중복 복제하지 않는다. HISTORY/ROADMAP에는 이번 진단이 무엇을 확인했고 다음에 어떤 한 가지 변경을 검토할지 연결한다. 새로운 이득이 없으면 진단 정보와 품질 성과를 분리한다.

뷰어:

- source·앵커·layout.
- 2×2 네 영상, 동기화된 같은 인덱스 slider·16fps 재생.
- 전체 프레임과 고정9장.
- sigma별 positive/negative MSE, CFG delta, residual/hidden 통계.
- rollout 단계별 변화와 같은-state 비교.
- 조건·checkpoint·모델명이 표시된 표와 블라인드 별칭을 함께 제공 가능.

영상용 시간 인덱스 t와 생성 step j를 화면에서 명확히 구분한다. 같은 step의 hidden/velocity 차트가 그 번호의 영상 프레임을 뜻하지 않는다.

compact에는 실제 영상·작은 시트·요약표·문서만 넣는다. checkpoint·cache·대형 raw·latent trace는 별도 비공개 보존 경로에 둔다. 기존9영상과 원본 가중치를 반복 포장하지 않는다. 생성 원 MP4를 용량 때문에 저화질로 재인코딩하지 않는다.

Spark와 Mac의 실제 `/tmp`에 compact를 저장하고 CRC·manifest·추출·전송 동일성을 실제로 검사한다. 하지 않은 검증은 PASS로 쓰지 않는다. 공개 GitHub에는 비민감 코드·문서·필요한 hash만 올린다. source/개인 경로·PID·token·checkpoint·조건 tensor·latent를 자동 공개하지 않는다.

완료 후 자체 프로세스 종료, commit/push·원격 SHA, 기존 작업 보존을 확인한다. 같은 과거 실패 문서를 매번 새 ZIP에 복제하지 않는다.

## 13. 한국어 수식·코드 해설

아래 순서로 실제 값과 영상에 연결한다.

1. one-step FM 검증과 반복 생성이 답하는 질문의 차이.
2. sigma와 model timestep, 영상 프레임·latent 시간·sampler step의 차이.
3. 기존 세 probe가 낮은 sigma를 직접 검사하지 않았다는 한계.
4. positive, negative prompt, TRACK_NULL, adapter bypass의 네 가지 구분.
5. `Delta5 = delta+ + 4(delta+−delta−)`의 유도와 상쇄 사례.
6. 같은 상태에서의 예측 변화와 서로 달라진 생성 경로의 비교 차이.
7. zero-init의 초기 보존과 학습 후 보존이 다른 이유.
8. BF16 rounding 전 residual과 실제 hidden 변경량의 차이.
9. 국소 주입이 최종 배경까지 영향을 줄 수 있는 경로.
10. C-007의 관측으로 다음 수정 후보를 어디까지 좁힐 수 있는지.

Flow Matching은 정당한 벡터장 학습 틀이다. 이번 유한 데이터·제한된 probe에서의 loss 개선이 최종 품질을 보장하지 않는다는 점을 설명하지, one-step 목적 자체가 잘못됐다고 단정하지 않는다. CFG도 단순히 “오류를 5배”라고 가르치지 않는다.

실제 관측으로 지지되지 않은 원인·이론적 안정성 보장·논문 신규성은 주장하지 않는다. 가벼운 이해 확인 질문과 해설을 붙여 사용자가 코드와 수식을 함께 공부할 수 있게 한다.

## 14. 최종 보고와 다음 단계의 경계

최종 보고는 다음 질문부터 답한다.

1. CFG1에서도 ON이 같은 CFG의 BASE를 손상시키는가?
2. CFG5에서 adapter의 증분 회귀가 더 커지는가?
3. 어떤 sigma·branch·block에서 변화가 커지는가?
4. one-step noisy state와 실제 생성 경로의 관측은 어떻게 다른가?
5. ON/NULL의 공유 효과와 실제 중간 궤적 효과를 구분할 근거가 있는가?
6. 코드·입력 불일치가 있었는가, 없었다면 어디까지 검증했는가?
7. 다음에 바꿀 것은 학습 목적·분기 균형·잔차 제약·표현 중 무엇 하나인가?

다음 후보는 관측에 맞춰 하나만 제안한다. 예를 들어 잔차 보존 정규화, 낮은 sigma의 학습/평가, negative branch의 적응 차이, 생성 경로상의 안정성 등이 후보일 수 있으나 이번에는 실행하지 않는다.

네 영상이 더 좋아 보여도 C-006의 기존 품질 판정을 뒤집거나 새로운 CFG를 기본값으로 자동 채택하지 않는다. 진단을 마친 뒤 사용자와 실제 결과를 검토하고 후속 학습 의뢰를 별도로 정한다.

---

## 참고 근거

- [R1] C-006 결과: https://github.com/hyunlord/make-meme/blob/c4aef32de21de4073bd4eb1861df4d35f2eda793/docs/research/experiments/C-006-motion-point-adapter-pilot/RESULTS.md
- [R2] C-006 학습 구현: https://github.com/hyunlord/make-meme/blob/c4aef32de21de4073bd4eb1861df4d35f2eda793/docs/research/experiments/C-006-motion-point-adapter-pilot/code/train_adapter.py
- [R3] C-006 모듈·연산 계약: https://github.com/hyunlord/make-meme/tree/c4aef32de21de4073bd4eb1861df4d35f2eda793/docs/research/experiments/C-006-motion-point-adapter-pilot/code
- [R4] C-006 데이터 분할: https://github.com/hyunlord/make-meme/blob/c4aef32de21de4073bd4eb1861df4d35f2eda793/docs/research/experiments/C-006-motion-point-adapter-pilot/DATA_SPLIT.json
- [R5] C-006 실제 생성 호출: https://github.com/hyunlord/make-meme/blob/c4aef32de21de4073bd4eb1861df4d35f2eda793/docs/research/experiments/C-006-motion-point-adapter-pilot/code/generate_video.py
- [R6] Classifier-Free Diffusion Guidance: https://arxiv.org/abs/2207.12598
- [R7] Flow Matching for Generative Modeling: https://arxiv.org/abs/2210.02747
- [R8] 기존 기록 revision의 scheduler: https://github.com/modelscope/DiffSynth-Studio/blob/f39d731a3e318d25b725eb3389cfddb184619842/diffsynth/diffusion/flow_match.py
- [R9] 기존 기록 revision의 pipeline: https://github.com/modelscope/DiffSynth-Studio/blob/f39d731a3e318d25b725eb3389cfddb184619842/diffsynth/pipelines/wan_video.py

참고 코드의 기록 revision과 실제 설치 파일의 관계를 확인하되, 문서를 읽는 과정에서 환경을 최신 버전으로 자동 업그레이드하지 않는다. 이 문서는 실행 의뢰이며 이번 대화에서 GPU 실행이 완료됐다는 보고가 아니다.
