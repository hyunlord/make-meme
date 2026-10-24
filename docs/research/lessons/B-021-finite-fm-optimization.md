# B-021 — 고정 FM 문제의 20회와 100회 최적화

이 문서는 B-020의 실제 계산 경로와 B-021의 제한된 실행을 연결한다. **B-021은 update20의 사전 replay 검사에서 중단됐으며, 20 대100update 비교는 완료하지 못했다.** 이번 대상은 사족으로 선 같은 Lab의 자연동작이며, 춤 전이·다른 개체 일반화가 아니다.

## 1. 세 개의 영상이 아니라 같은 영상의 세 회귀 입력이다

### 직관과 수식

이번 학습에서는 정답 영상 하나를 서로 다른 세 종류의 노이즈와 섞어 세 문제를 만든다. 같은 문제를 더 오래 푼다고 새로운 자세·개체·장면을 학습한 것은 아니다. Flow Matching은 정해진 확률 경로의 속도장을 회귀하는 방법이며, 일반적인 목적함수는 데이터·조건·노이즈·시간에 대한 기대값이다. 이번 세 점 회귀는 그 원리를 제한된 입력 집합에 적용한 진단이다. [Flow Matching 원논문](https://arxiv.org/abs/2210.02747v2)

실제 사용한 Wan 규약을 다음처럼 쓴다. $Y$는 정답 RGB 영상, $z_Y=E_{VAE}(Y)$는 정규화된 latent, $c_+$는 reference·driving·mask·positive text의 조건이다. $\sigma\in[0,1]$는 noise time이고, $\epsilon$은 표준정규 노이즈다.

$$x_\sigma=(1-\sigma)z_Y+\sigma\epsilon,\qquad
v^*=\frac{d x_\sigma}{d\sigma}=\epsilon-z_Y.$$

따라서 $\sigma=0$은 데이터 쪽이고 1은 노이즈 쪽이다. 생성은 큰 $\sigma$에서 작은 $\sigma$로 진행한다. 다른 교육용 예제의 noise→data 시간 $t=1-\sigma$를 쓰면 속도 부호도 바뀐다. 부호만 외워 옮기지 않고 코드의 `target=noise-z_y`와 scheduler 방향을 함께 확인한다.

일반적인 FM 목적과 이번 경험손실은 서로 다르다.

$$\mathcal L_{FM}(\theta)=\mathbb E_{Y,c,\sigma,\epsilon}
\left[\frac1M\|v_\theta(x_\sigma,1000\sigma,c)-(\epsilon-z_Y)\|_2^2\right],$$

$$\widehat{\mathcal L}_3(\theta)=\frac13\sum_{j=0}^2\ell_j(\theta),\qquad
\ell_j(\theta)=\frac1M\|v_\theta(x_j,1000\sigma_j,c_+)-v_j^*\|_2^2.$$

여기서 $M=16\cdot5\cdot64\cdot112=573{,}440$은 prediction의 scalar 수다. 학습을 늘리는 동안 $Y,c_+,\sigma_j,\epsilon_j$는 모두 고정이다. 평균 MSE가 작아져도 얼굴과 발의 작은 영역만 개선됐는지, 넓은 배경이 더 잘 맞았는지는 이 값 하나로 구별할 수 없다. 이번에는 영역 가중치를 바꾸지 않는다.

| tuple | sigma | noise seed | 역할 |
|---|---:|---:|---|
| train_0 | 0.2 | 2026102401 | optimizer에 사용 |
| train_1 | 0.5 | 2026102402 | optimizer에 사용 |
| train_2 | 0.8 | 2026102403 | optimizer에 사용 |
| holdout | 0.65 | 2026102404 | 같은 clip의 noise/time 보조 평가 |

100update는 `index % 3` 순환으로 34/33/33번 노출된다. 20update는 7/7/6번이다. 이 순서는 균등 평균을 목표로 한 순환 최적화지만, 유한한 update와 Adam moment 때문에 순서와 마지막 미완성 순환도 실행 계약의 일부다. holdout은 optimizer에 들어가지 않지만 독립 영상 test는 아니다.

### shape와 코드

`z_y`, `epsilon`, `z_sigma`, `target`, 최종 prediction은 모두 FP32 `[16,5,64,112]`다. RGB의 17프레임과 latent의 시간축 5는 같지 않다. noise time $\sigma$는 영상의 30fps 프레임 시간과도 다르다. 영상은 17/30초이고 첫·마지막 표본 사이 간격은 16/30초다.

B-020 고정 소스의 [`fm_contract.py:35–81`](https://github.com/hyunlord/make-meme/blob/13ac7727e501913ed7e765f44f1d8f6385a19178/docs/research/experiments/B-020-real-fm-tail-overfit/code/fm_contract.py#L35)에서 `fixed_tuples`, `mix_velocity`, `velocity_mse`가 위 식을 구현한다. `.square().mean()`은 generated-region latent 전체의 평균이며, synthetic hidden MSE로 대체한 것이 아니다.

## 2. frozen prefix는 모든 시간에 쓸 수 있는 영상 특징이 아니다

### 직관과 수식

앞 39개 block은 가중치가 고정됐어도 입력이 바뀌면 출력이 바뀐다. 동일한 사진·영상이라는 이유만으로 다른 noise나 timestep의 prefix 특징을 재사용할 수 없다.

$$h_j=F_{0:38}(x_j,1000\sigma_j,c_+;\theta_{base}),$$
$$\hat v_j=U\!\left(H\!\left(B_{39}(h_j,e_j,c_+;\theta_{base},A,B),e'_j\right)\right).$$

$F$는 고정 prefix, $B_{39}$는 마지막 block, $H$는 고정 공식 head, $U$는 unpatchify다. $e_j$와 $e'_j$는 block·head에 쓰는 서로 다른 timestep embedding이다. 바뀌는 parameter는 마지막 self-attention Q/V의 LoRA $A,B$뿐이다.

$$W_{eff}=W_0+(\alpha/r)BA,\qquad r=4,\quad\alpha=4.$$

Q와 V 각각 $A:[4,5120]$, $B:[5120,4]$이므로 전체 학습 parameter 수는 $2(4\cdot5120+5120\cdot4)=81{,}920$이다. $B=0$이면 adapter 효과는 0이지만, 무작위 초기 $A$의 실제 값은 첫 $B$ gradient와 이후 궤적을 결정하므로 같은 seed라는 설명만으로 초기 실물을 대체하지 않는다.

head parameter를 동결하는 것과 head의 미분을 끊는 것은 다르다.

$$\frac{\partial\ell}{\partial A}
=\frac{\partial\ell}{\partial\hat v}
\frac{\partial U}{\partial H}
\frac{\partial H}{\partial B_{39}}
\frac{\partial B_{39}}{\partial A}.$$

head의 `requires_grad=False`는 head weight gradient를 만들지 않을 뿐 입력으로 가는 chain rule은 남는다. 이 경로를 `no_grad`로 감싸거나 hidden을 detach하면 학습해야 할 adapter까지 끊긴다.

### shape와 코드

캐시 `h38`는 FP32 `[1,12992,5120]`, context는 `[1,769,5120]`, block embedding은 `[1,6,5120]`, head embedding은 `[1,5120]`다. 12992 token은 reference1792 + generated8960 + driving2240이다. FP32 cache를 사용한다는 사실과 실제 Linear/attention의 BF16 경계는 구별한다.

B-020 [`phase_prefix.py:30–53`](https://github.com/hyunlord/make-meme/blob/13ac7727e501913ed7e765f44f1d8f6385a19178/docs/research/experiments/B-020-real-fm-tail-overfit/code/phase_prefix.py#L30)는 실제 full positive forward 직전의 마지막 block 입력을 저장한다. [`phase_train.py:100–114`](https://github.com/hyunlord/make-meme/blob/13ac7727e501913ed7e765f44f1d8f6385a19178/docs/research/experiments/B-020-real-fm-tail-overfit/code/phase_train.py#L100)의 `predict`는 공식 block→head→unpatchify 경로와 head 입력 gradient hook을 연결한다. [`LowRankLinear.forward`](https://github.com/hyunlord/make-meme/blob/13ac7727e501913ed7e765f44f1d8f6385a19178/docs/research/experiments/B-020-real-fm-tail-overfit/code/lora_component.py#L34)는 FP32 adapter delta를 계산하고 base output dtype으로 되돌린다. 작은 FP32 weight 변화가 BF16 출력에서 똑같이 선형적으로 드러난다고 가정할 수 없다.

B-021은 이 캐시의 **producer=B-020** binding을 검사하면서 새 **consumer=B-021** 실행 hash를 별도로 남긴다. 새 코드 hash가 과거 producer hash와 다르다는 것은 정상이다. 과거 receipt를 바꾸거나 검사를 없애서 이를 해결하면 안 된다.

## 3. 학습에서 맞춘 입력과 생성이 실제 방문하는 입력은 다르다

### 직관과 수식

학습 입력은 실제 정답 $z_Y$와 고정 noise를 섞어 정확히 만든 점이다. 생성 중간 상태는 모델 자신의 이전 예측과 solver 계산으로 만들어진다. 학습 loss가 줄었다고 생성 궤적 전체의 오차가 줄었다는 결론은 나오지 않는다.

학습은 $\{x_j,\sigma_j,c_+\}_{j=0}^2$의 positive prediction을 감독한다. 생성의 CFG는 같은 현재 latent $\tilde x_k$에서 두 text branch를 호출한다.

$$v_{CFG}(\tilde x_k,\sigma_k)=v_-(\tilde x_k,\sigma_k)
+w\big(v_+(\tilde x_k,\sigma_k)-v_-(\tilde x_k,\sigma_k)\big),\qquad w=5.$$

두 branch는 시각 조건을 공유하지만 text가 다르다. 같은 adapter가 양쪽 모델 호출에 설치되므로 positive 학습으로 바뀐 parameter는 negative prediction에도 영향을 줄 수 있다. negative branch에 직접 정답 loss를 준 것은 아니다.

생성 상태는 일반적으로 $\tilde x_k\ne(1-\sigma_k)z_Y+\sigma_k\epsilon_j$다. $\sigma_k$도 세 학습 sigma에만 머물지 않는다. 따라서 fixed tuple loss 개선과 rollout 영상 개선 사이에는 상태·시간·text branch의 차이가 있다. 이것은 가능한 차이의 설명이지 이번 실패 원인을 확정한 진단은 아니다.

[`phase_sample.py:30–50`](https://github.com/hyunlord/make-meme/blob/13ac7727e501913ed7e765f44f1d8f6385a19178/docs/research/experiments/B-020-real-fm-tail-overfit/code/phase_sample.py#L30)는 Q/V adapter 설치, 저장된 generator state 복원, UniPC40step/shift3의 timestep·sigma 일치를 검사한다. 같은 파일의 `complete`는40step/80forward와 finite final latent를 확인한다. 100update는 학습 parameter를 바꾸는 100번의 optimizer 동작이며, 영상 생성의40step/80forward와 다른 단위다. 생성에서는 실제 full model을 다시 실행하며 네 prefix cache를 생성 전 구간에 반복 적용하지 않는다.

## 4. AdamW 재개와 adapter warm-start는 다르다

### 직관과 수식

AdamW는 현재 weight뿐 아니라 이전 gradient의 평균과 제곱 평균을 기억한다. 동일 weight에서 시작해도 이 기억을 지우면 다음 update가 달라질 수 있다. PyTorch의 일반 checkpoint 설명도 모델 state와 optimizer state를 별도로 복원한다. [공식 checkpoint 지침](https://docs.pytorch.org/tutorials/beginner/saving_loading_models.html#saving-loading-a-general-checkpoint-for-inference-and-or-resuming-training)

parameter를 $\theta$라 하고 update 번호를 $n$이라 쓰면, 이번 weight decay0의 AdamW 핵심은 다음과 같다.

$$g_n=\nabla_\theta\ell_{(n-1)\bmod3}(\theta_{n-1}),$$
$$m_n=\beta_1m_{n-1}+(1-\beta_1)g_n,\qquad
s_n=\beta_2s_{n-1}+(1-\beta_2)g_n^2,$$
$$\theta_n=\theta_{n-1}-\eta\frac{m_n/(1-\beta_1^n)}{\sqrt{s_n/(1-\beta_2^n)}+\varepsilon_{opt}}.$$

$\varepsilon_{opt}$는 optimizer 안정화 상수이며 FM noise $\epsilon$과 다르다. B-020은 `AdamW(parameters, lr=1e-4, weight_decay=0)`를 호출했다. 동일 pinned PyTorch의 CPU 사전 검사와 이번 GPU worker의 `optimizer-options.json`은 betas=(0.9,0.999), eps=1e-8, amsgrad/maximize/capturable/differentiable=False, foreach/fused=None, decoupled_weight_decay=True를 확인했다. `None`은 특정 backend를 명시적으로 False로 고정한 뜻이 아니며, 옵션 기록만으로 실제 CUDA optimizer kernel을 관측했다고 주장하지 않는다. 공식 기본값과 runtime 옵션을 대조했지만 새 backend를 강제하지 않았다. [PyTorch2.14 AdamW](https://docs.pytorch.org/docs/2.14/generated/torch.optim.AdamW.html)

B-020 final20 weight만 복원하고 optimizer를 초기화하면 $(m,s,n)=(0,0,0)$에서 다시 시작한다. 이것은 $(\theta_{20},m_{20},s_{20},20)$을 복원한 연속 학습과 다르다. 이번 B-021은 이 문제를 피해 **B-020 initial의 실제 A/B + fresh AdamW**로0→100을 계획했으나 실제로는20회 replay 검사에서 중단했다. 승인 상한100회 중 실제 사용은20회다.

0/20/50/100 저장물은 adapter·optimizer moment/step·CPU/CUDA RNG·다음 tuple cursor·parameter 이름 대응·options·producer/consumer hash를 함께 보존해야 한다. RNG를 저장해도 다른 kernel 버전이나 연산 순서까지 자동으로 일치하는 것은 아니다. 현재 실험은 이 상태를 저장할 뿐 이후 학습을 자동 재개하지 않는다.

B-020 [`phase_train.py:123–145`](https://github.com/hyunlord/make-meme/blob/13ac7727e501913ed7e765f44f1d8f6385a19178/docs/research/experiments/B-020-real-fm-tail-overfit/code/phase_train.py#L123)는 optimizer parameter 집합과 adapter-only 업데이트를 확인하지만 optimizer state를 저장하지 않았다. B-021 사전 고정 코드의 [`budget_contract.py`](https://github.com/hyunlord/make-meme/blob/62f853b087e7b48baf3401818bfec152110bfe63/docs/research/experiments/B-021-fixed-tuple-update-budget/code/budget_contract.py#L37) `save_checkpoint`는 tensor/primitive 저장과 readback, fresh optimizer에 대한 state 복원 검사를 수행한다. [`phase_train.py`](https://github.com/hyunlord/make-meme/blob/62f853b087e7b48baf3401818bfec152110bfe63/docs/research/experiments/B-021-fixed-tuple-update-budget/code/phase_train.py#L123)는 실제 initial을 로드하고0/20에서 저장한 뒤,20의 replay를21번째 update 전에 검사한다. 이번 실제 저장은0/20까지이며50/100 저장과100 endpoint의 fresh component reload/OFF는 NOT_RUN이다.

## 5. 곡선과 prediction 변화는 무엇을 말하는가

각 update에서 서로 다른 sigma의 loss가 번갈아 나타난다. 이를 하나의 선으로 연결해 출렁임을 발산, 전체 기울기를 수렴이라고 부르면 잘못된 비교다. `train_0`, `train_1`, `train_2`를 분리하고,0/20/50/100 평가에서 **같은 입력**의 값을 우선 비교한다. holdout도 별도 선이다.

같은 평가 prediction $p_{j,n}$과 adapter OFF baseline $p_{j,0}$에 대해 다음을 계산할 수 있다.

$$\Delta^{RMS}_{j,n}=\sqrt{\frac1M\sum_i(p_{j,n,i}-p_{j,0,i})^2},$$
$$\Delta^{max}_{j,n}=\max_i|p_{j,n,i}-p_{j,0,i}|,\qquad
\Delta^{rel}_{j,n}=\frac{\|p_{j,n}-p_{j,0}\|_2}{\|p_{j,0}\|_2}.$$

분모가0이면 상대값은 UNDEFINED이며 임의 숫자로 바꾸지 않는다. 변화량이 크다는 것은 target에 가까워졌다는 뜻이 아니다. 방향이 잘못된 큰 변화도 가능하다. 이 통계는 이미 계산한 평가 prediction에서 얻고 추가 full-model forward를 사용하지 않는다.

20update replay 비교는 같은 초기 상태·tuple순서·optimizer 계약이 유지됐는지 확인하는 지점이다. adapter 차이와 tuple MSE 차이를 각각 기록하고, 기존20회 개선량에 비해 replay 오차가 무시할 만한지 함께 읽는다. 같은 seed만으로 byte identity를 보장하지 않는다. 의미 있는 불일치면21회 전에 중단하며 tolerance를 결과를 본 뒤 넓히지 않는다.

## 6. 실제 관측 기록과 해석 경계

B-020의 기준값은 아래와 같다. 이것은 보존된 기록이며 B-021 결과가 아니다.

| tuple | B-020 update0 | B-020 update20 |
|---|---:|---:|
| train_0 | 0.1455920785665512 | 0.14547254145145416 |
| train_1 | 0.05071360245347023 | 0.05067168548703194 |
| train_2 | 0.03156200796365738 | 0.03149447962641716 |
| holdout | 0.03840317949652672 | 0.03837953507900238 |

출처: [B-020 TRAINING_SUMMARY](https://github.com/hyunlord/make-meme/blob/13ac7727e501913ed7e765f44f1d8f6385a19178/docs/research/experiments/B-020-real-fm-tail-overfit/TRAINING_SUMMARY.json). B-020의 parity/reload/OFF는 max_abs0으로 기록됐고, 영상 품질 개선은 미입증이었다.

### 실제 B-021: 초기 상태는 같았고,20회 adapter replay는 허용범위를 넘었다

initial 파일 SHA256은 `1a603a234d0806dcfc2738a1aaf380f0ad98baf934d543a73d7dbea307d1a56b`로 확인했다. 두 A는 FP32 `[4,5120]`, 두 B는 FP32 `[5120,4]`이며 B의 모든 값이0이었다. actual initial을 새로 추정하지 않고 로드했다. update0의 네 prediction은 보존 baseline과 max_abs0으로 같았다.

사전 고정 replay 기준은 각 원소에 대해

$$|a-b|\le10^{-7}+10^{-5}|b|$$

였다. 이는 split/reload/OFF의 기존1e-3 기준과 다른, 더 엄격한 비교 기준이다. tensor 전체의 작은 상대L2와 모든 원소의 `allclose`는 같은 판정이 아니다. 예를 들어 작은 값 근처의 몇 원소가 절대허용치를 넘으면 전체 상대L2가 작아도 실패할 수 있다.

| adapter | B-020 final20 대비 max_abs | relative L2 | 사전 replay |
|---|---:|---:|---|
| Q A | 2.191169187426567e-6 | 1.7798727337185246e-5 | FAIL |
| Q B | 5.241599865257740e-6 | 2.8730269629707357e-4 | FAIL |
| V A | 9.792856872081757e-7 | 3.567392981145133e-6 | FAIL |
| V B | 3.4683844205574133e-6 | 1.5994984099219312e-4 | FAIL |

반면 네 tuple의 scalar loss replay는 모두 같은 사전 기준을 통과했다.

| tuple | B-021 update20 MSE | B-020 update20과 절대차 | B-020의0→20 MSE 감소량 |
|---|---:|---:|---:|
| train_0 | 0.14547225832939148 | 2.8312206268310547e-7 | 1.195371150970459e-4 |
| train_1 | 0.050671838223934174 | 1.5273690223693848e-7 | 4.191696643829346e-5 |
| train_2 | 0.031494442373514175 | 3.725290298461914e-8 | 6.752833724021912e-5 |
| holdout | 0.03837939724326134 | 1.3783574104309082e-7 | 2.364441752433777e-5 |

scalar 차이는 기존 감소량보다 작다. 그렇다고 adapter replay 검사를 사후 제거하거나 tolerance를 넓혀 통과로 바꾸지 않았다. **엄격한 수치 재현 기준 실패는 확인됐지만, 이 차이가 의미 있는 영상 품질 차이를 만든다는 사실은 확인되지 않았다.** 미세 오차의 원인도 UNKNOWN이다. 이를 바로 FlashAttention 비결정성·optimizer 버그·학습량 부족의 증거로 지목하지 않는다.

같은20회 평가 prediction에서 baseline OFF 대비 변화도 이미 나타났다.

| tuple | RMS 변화 | max_abs 변화 | relative L2 변화 |
|---|---:|---:|---:|
| train_0 | 0.005100314039736986 | 0.03125 | 0.004275561217789957 |
| train_1 | 0.003546064719557762 | 0.03125 | 0.0028685127385263596 |
| train_2 | 0.002983146347105503 | 0.03125 | 0.002379239800213911 |
| holdout | 0.003207144560292363 | 0.03125 | 0.002575397209245790 |

이는 같은 평가 입력에서 adapter가 예측을 바꿨다는 관측이다. 위 표는 **B-021 prediction 대 adapter OFF**이며 **B-021 대 B-020 prediction 차이**가 아니다. 두 실행의 전체 prediction 차이를 저장하지 않은 상태에서 이 값을 replay 차이로 사용하면 안 된다.

update20에서 중단해21~100update,50/100평가,PROBE/S/D와 새 영상은 모두 NOT_RUN이다. 따라서100회면 나아지는지, 나빠지는지, 같은지 이번에는 답할 수 없다.0/20 optimizer/RNG/tuple cursor 저장 검사는 수행됐지만,100회 후 fresh component reload/OFF 검사를 완료했다고 보고하지 않는다. 기존 두 영상은 B-020 자료이며 B-021의 새 영상 결과가 아니다.

보존 로그의 최초 차이는 update1의 미세한 gradient norm 차이, update2의 scalar loss 차이까지 확인했다. 다음 검증 가설 하나는 **동일 입력의 FA2 backward 수치 반복성이 이 차이를 설명하는가**다. 원인은 UNKNOWN이며 별도 사전등록 검증이 필요하다. 이번에는 추가 backward·학습·sampling을 실행하지 않았다.

고정 loss만 줄고 영상이 그대로라면 teacher-path와 rollout의 차이, 적은 noise/time coverage, 학습 가능한 모듈 범위, 공간별 오차 분포 등이 가능한 가설이다. 한 번의 결과로 하나를 원인으로 확정할 수 없다. D=Y이므로 driving 복사 shortcut도 남는다. 새로운 영상·동물·cross-ID 검증은 이번에 없다. 직접 연속 재생을 관찰하지 못한 시간 품질은 UNVERIFIED로 남긴다.

## 이해 확인 질문

1. 동일 clip의 sigma0.2/0.5/0.8에서100update가 성공하고 sigma0.65에서도 loss가 줄었다. 이것이 새로운 Lab 영상에서도 동작을 재현한다는 증거인가? 어떤 변수가 여전히 같은가?
2. B-020 final20 adapter에 fresh AdamW로80회 더 학습하는 것과 initial에서100회 학습하는 것이 다른 이유를 $m_n,s_n,n$으로 설명해보자. 같은 seed는 무엇을 복원하지 못하는가?
3. positive fixed-tuple MSE가 줄었지만 CFG5 영상의 자세가 그대로일 수 있는 이유를 입력 상태·noise time·negative branch로 나누어 설명해보자.

## 별도 해설

1. 아니다. 같은 $Y$,reference,driving,mask,text,촬영장면이며 holdout은 같은 clip의 한 noise/time 조합이다. 학습에 직접 쓰지 않은 한 점에 대한 근거와 독립 clip 일반화는 다르다.
2. fresh optimizer는 moment와 bias-correction step을0으로 초기화한다. 같은 weight에서도 다음 gradient를 누적하고 보정하는 방식이 달라진다. seed는 과거 moment·tuple cursor·parameter 이름 매핑을 대신하지 못한다. 이번에는 실제initial을 재사용해0→100 계획으로 시작했으나20회 replay에서 중단했다.
3. fixed 입력은 정답과 noise를 섞은 세 점이고 생성은 이전 모델예측을 누적한 상태다. sampler는 세 점 밖의 sigma와 latent도 방문한다. 또한 CFG는 positive와negative prediction의 조합인데 직접 감독한 것은positive뿐이다. 이는 차이가 생길 수 있는 구조적 이유이며, 이번 실제 실패의 단일 원인 확정은 아니다.
