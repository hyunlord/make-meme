# B-014 — 조건부 속도장의 차분을 바꾸는 ALG 이식

공식 수식·소스 확인과 실제 CPU 계약 검증은 완료됐다. 최종9개 검사와 부모 cache binding은 PASS이며 실제 GPU pilot·시각 품질 결과는 아직 대기다. [계획](../experiments/B-014-alg-scail-pilot/PLAN.md), [정확한 이식 감사](../experiments/B-014-alg-scail-pilot/ADAPTATION_AUDIT.md)를 함께 읽는다. 새로운 학습이나 알고리즘 발명을 보고하는 실험이 아니다.

## 1. 직관: 이미지를 흐리게 만드는 것과 guidance를 바꾸는 것

B-013에서는 동적 driving을 받아도 Lab가 착석했고, 후반 머리 반응에는 심한 얼굴 번짐이 동반됐다. 이것만으로 고주파 reference가 실패 원인이라고 단정할 수 없다. 이번 질문은 기존 결과를 보존하면서 **초기 sampling의 reference 기반 차분만** 바꾸면 전신·국소 충실도와 형태가 어떻게 달라지는가다.

[ALG Eq.(2)](https://arxiv.org/html/2506.08456v2#S3.E2)는 원본 reference의 negative 예측을 기준항으로 남기고, low-pass reference에서 positive와 negative의 차이를 계산한다. low-pass는 세부 정보를 줄이지만 자세 제거기가 아니다. 앉은 실루엣, 가슴 폭, 침실 배치처럼 큰 구조가 남을 수 있다. 따라서 더 움직였다는 사실은 목표 자세 성공을 뜻하지 않는다.

## 2. 식: 세 예측은 같은 noisy latent에서 계산한다

`zσ`는 현재 생성 latent, `σ`는 noise 수준, `R`은 원래 reference latent, `L(R)`은 공간 필터 결과다. `K`에는 고정 driving·mask·CLIP·history 등이 들어간다. `c+`, `c-`는 positive/negative text, `w=5`다.

\[
u_R=v_\theta(z_\sigma,\sigma;R,K,c_-),\quad
u_L=v_\theta(z_\sigma,\sigma;L(R),K,c_-),\quad
c_L=v_\theta(z_\sigma,\sigma;L(R),K,c_+).
\]

기존 CFG는 `u_R+w*(c_R-u_R)`이고, 이번 활성 구간은 다음과 같다.

\[
v_{ALG}=u_R+w(c_L-u_L)
=\underbrace{u_L+w(c_L-u_L)}_{\text{low-pass CFG}}
+\underbrace{(u_R-u_L)}_{\text{원본 negative 기준항 보정}}.
\]

단순 low-low CFG와의 차이는 정확히 `u_R-u_L`다. 예를 들어 scalar fixture에서 `u_R=2,u_L=5,c_L=11,w=5`이면 ALG는32, low-low는35다. 이 숫자는 학습 모델 관측이 아니라 식을 구분하는 설명용 예다. 모든 예측은 같은 `zσ`에서 얻은 뒤 scheduler를 한 번만 갱신한다.

논문 Eq.(2) 뒤의 별도 재표현은 `w-1`을 쓰지만 표시된 식을 더하면 Eq.(2)와 어긋난다. 여기서는 Eq.(2)와 [공식3-chunk 조합 L919–924](https://github.com/choi403/ALG/blob/3657bfd0d408631db2443b491498c44e1cb2e5c6/pipeline_wan_image2video_lowpass.py#L919-L924)을 기준으로 위 항등식을 직접 전개했다. 이 차이를 숨기거나 CFG 값을 임의로 바꾸지 않는다.

## 3. tensor와 실제 코드의 연결

SCAIL의 [arg_c/arg_null](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/scail.py#L480-L506)은 text가 달라도 visual 조건을 공유한다. negative는 사진이나 driving을 제거한 branch가 아니다. 이번에는 원본 두 dictionary를 보존하고 low branch의 reference leaf만 바꾼다.

| 부모 B-013에서 확인된 조건 | shape·dtype | B-014 개입 |
|---|---|---|
| 생성 noise/latent | `[16,5,112,64]` FP32 | 초기값 보존, 이후 trajectory는 달라질 수 있음 |
| reference | `[16,1,112,64]` FP32 | 활성 low branch만 공간 필터 |
| reference mask | `[28,6,112,64]` FP32 | 그대로 |
| RGB driving latent | `[16,5,56,32]` FP32 | 그대로 |
| driving mask | `[28,5,56,32]` FP32 | 그대로 |
| CLIP | `[1,257,1280]` FP16 | 원래 reference의 특징 유지 |
| positive/negative text | `[108,4096]` / `[1,4096]` BF16 | 그대로 |

이 표는 부모 cache의 실제 shape를 바탕으로 한 개입 경계이며 새 GPU 관측을 뜻하지 않는다. [model_scail2.py L741–803](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/modules/model_scail2.py#L741-L803)의 reference는 생성 시간축 앞의 조건 token으로 결합된다. 출력 첫 프레임을 reference로 덮는 조작은 포함하지 않는다.

공식 Wan ALG는 조건을 batch3으로 연결하지만 이식은3회 순차 single-sample 예측이다. 같은 수식을 계산하더라도 실행 순서·배치·정밀도에 따른 부동소수점 차이까지 byte-identical하다고 보장하지 않는다. 원래 reference의 CLIP을 그대로 남기는 것은 공식 코드와 맞고, SCAIL semantic mask를 전혀 필터하지 않는 것은 명시적 architecture 이식 차이다.

## 4. 공간 필터는 무엇을 잃고 무엇을 남기는가

`[C,T,H,W]`에서 T를 batch 위치로 옮긴 뒤 H/W에만 down-up한다. 이번 `C=16,T=1,H=112,W=64`, ratio0.4이므로 중간 크기는 `round(44.8)=45`, `round(25.6)=26`이다. bilinear·antialias=True·align_corners=False를 두 번 적용한다. [공식 필터 코드](https://github.com/choi403/ALG/blob/3657bfd0d408631db2443b491498c44e1cb2e5c6/lp_utils.py#L49-L54)에 연결되는 연산이다.

VAE encoder E는 일반적으로 비선형이므로 `E(L(I))`와 `L(E(I))`는 같지 않다. 여기서는 기존 reference latent R에 L을 적용하며 사진을 다시 encode하지 않는다. latent의 빠른 공간 변화가 RGB의 털 세부와 일대일 대응한다고 가정하지 않는다. signed latent 값은 RGB가 아니므로0~1 clamp나 새 정규화도 하지 않는다.

## 5. noise 시간과 영상 시간, 호출 비용

공식 [step schedule](https://github.com/choi403/ALG/blob/3657bfd0d408631db2443b491498c44e1cb2e5c6/lp_utils.py#L81-L98)은 index `i/(N-1)`를 쓴다. N40, interval[0,.20]이면 i0..7에서만 활성이다. 이는 처음8개의 **denoising step**이며 처음8개의 영상 프레임이 아니다. 총 예상 forward는 `8×3+32×2=88`, scheduler update40, 출력17frame·24fps다.

이번 UniPC의 [flow prediction 변환](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/utils/fm_solvers_unipc.py#L316-L323)은 `x0_pred=zσ-σ*v`다. 선형 경로 `zσ=(1-σ)x0+σε`에서 `v=ε-x0`와 일치하는 해석이다. 높은 noise에서 낮은 noise로 sample한다. 논문의 진행 시간이나 영상 `k/24`와 σ를 같은 축으로 쓰지 않는다.

i8에서 원래 reference로 돌아가도 초기8step의 개입으로 zσ 자체가 이미 달라졌다. 비선형 속도장과 multistep scheduler의 이력 때문에 후반 출력이 baseline으로 되돌아간다고 가정할 수 없다. NFE10% 증가는 walltime이나 peak memory10% 증가 보장이 아니다.

## 6. 필요한 증거와 남는 한계

CPU 검사는 no-op, branch별 실제 kwargs, 원본 storage/hash 불변, channel/frame isolation, schedule 경계0/7/8/39,88회 합계, 정확한 세 항 조합을 구별해야 한다. 이는14B 실행이나 얼굴 품질 증명이 아니다. 실제 pilot에서는 step40/forward88·원래 noise/scheduler·초기/후반 branch 전환·final latent finite/readback을 별도로 확인한다. CPU 관측은 아래와 같고 GPU pilot 관측은 아직 대기다.

reference 저주파·CLIP·mask가 남아 착석이 지속될 수도 있고, 얼굴 단서가 줄어 원본 개체가 약해질 수도 있다. 한 seed의 baseline80NFE 대 pilot88NFE 비교는 compute-matched 검증이 아니다. 개선·악화 어느 쪽도 ALG 전체, 모든 reference 개입, 고주파 단일 원인, 일반화를 입증하지 않는다. 실제 연속 재생을 관찰하지 못하면 시간 품질은 UNVERIFIED다.

### 실제 CPU 결과를 수식과 연결하기

[최종 CPU receipt](../experiments/B-014-alg-scail-pilot/CPU_VALIDATION.json)는9개 검사 PASS(0.69초), 실제 부모16leaf의 hash 보존, RNG·원본 reference 불변,45×26 필터와88회 계획을 확인했다. [alg.py](../experiments/B-014-alg-scail-pilot/code/alg.py)의 `guided_prediction`은 세 항 식을, `branch_condition`은 reference만 바뀌는 조건 경계를, `low_pass_reference`는 채널/시간 평면 분리를 담당한다. [alg_extract.py](../experiments/B-014-alg-scail-pilot/code/alg_extract.py)는 고정 소스의 prediction block만 한 번 치환하고 역치환 AST를 검사한다. [alg_runtime.py](../experiments/B-014-alg-scail-pilot/code/alg_runtime.py)는 sidecar를 실제 부모 cache/reference hash에 연결한다.

이 결과는 모델 출력을 mock으로 둔 식 검사와 실제 입력 cache 연결 검사다.14B DiT를 OFF/ratio1로 다시 생성해 같은 영상을 얻었다는 검증이 아니다. exhaustive match 뒤의 `assert_never` 배치 수정 후 helper typecheck는0 errors/0 warnings로 통과했다. 전체 legacy runtime의 strict typing까지 검증했다는 뜻은 아니다. 새로운 영상·전신 자세·개체·시간 품질은 실제 출력 뒤 별도로 판단해야 한다.

## 이해 확인 질문

1. 왜 세 항 모두 low reference를 넣는 것은 이번 식과 다른가?
2. i8에서 reference를 복구했는데도 baseline과 다른 이유는 무엇인가?
3. 필터 후 더 크게 머리를 흔들지만 얼굴이 무너지면 성공인가?

## 별도 해설

1. 원본 negative 기준항이 사라져 `u_R-u_L` 보정이 없어지기 때문이다. negative가 visual-unconditional인 것도 아니다.
2. zσ와 scheduler 이력이 초기 개입으로 달라진다. 같은 조건을 나중에 넣는다고 다른 상태의 trajectory가 같아지지 않는다.
3. 아니다. source 방향·순서·전신 자세와 개체/형태 보존을 따로 평가한다. 움직임 크기는 목표 충실도의 대체 지표가 아니다.
