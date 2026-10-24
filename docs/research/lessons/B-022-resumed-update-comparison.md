# B-022 — 재현 실패를 보존하며 같은 checkpoint에서 학습을 이어가기

작성 시점 상태: **복원·추가80update·matched 영상 생성 완료, 목표 품질 개선 미입증**. 아래 원리·고정 계약은 코드와 공식 문서를 확인했다. B-022의 실제 진단 receipt를 반영했으며, 두 endpoint의 실제 receipt와 전체17장 정적 관측을 반영했다. B-021의 STOPPED_AT_REPLAY_20과 adapter replay FAIL을 소급 변경하지 않는다.

## 1. seed는 출발 번호이고, 결정론은 계산 과정의 성질이다

### 직관

같은 seed는 같은 환경에서 난수열을 맞추는 데 쓰인다. 계산 중 난수가 없는 연산도 병렬 합산 순서에 따라 마지막 비트가 달라질 수 있다. 따라서 같은 seed·같은 입력을 확인하는 것과 같은 kernel이 같은 비트를 내는지를 확인하는 것은 별도다. PyTorch 공식 문서는 release·platform·CPU/GPU 사이의 완전 재현을 보장하지 않으며, 난수 통제와 비결정적 알고리즘 통제를 구분한다. 이 문서는 조회 시 PyTorch2.14로 연결되었다. 이것을 현재 Spark binary 버전으로 간주하지 않는다. [PyTorch 재현성 문서](https://docs.pytorch.org/docs/2.14/notes/randomness.html)

### 수식

유한정밀도 덧셈을 $\operatorname{fl}(a+b)$라 쓰면 일반적으로

$$\operatorname{fl}(\operatorname{fl}(a+b)+c)\ne\operatorname{fl}(a+\operatorname{fl}(b+c)).$$

이를 설명하는 FP32 예는 $a=10^8,b=-10^8,c=1$이다. 한 괄호 순서는1을 남기고 다른 순서는 작은1이 반올림되어0을 남길 수 있다. 이는 계산 순서가 다르면 결과가 달라질 수 있다는 예시이며, B-021의 실제 kernel 내부 순서를 관측한 증거는 아니다.

연산의 실제 출력을

$$\widehat v=F(\theta,x,c;\mathcal E,\mathcal R,\pi)$$

라고 적자. $\mathcal E$는 binary·dtype·device 환경, $\mathcal R$는 RNG 상태, $\pi$는 연산·합산 순서다. seed를 복원해도 $\mathcal E$나 $\pi$를 모두 고정했다는 뜻은 아니다. 반대로 RNG 상태를 저장하지 않고 seed만 다시 넣으면 이미 소비된 난수열의 위치는 복원되지 않는다.

### 실제 경로와 검사

기존 tail 경로는 FP32 prefix에서 공식 마지막 block을 거쳐 BF16 Linear/attention과 FP32 norm·head 경계를 유지한다. FA2를 SDPA로 바꾸지 않는다. 공식 FlashAttention v2.8.3의 `flash_attn_func`와 `flash_attn_varlen_func`는 `deterministic=False`가 기본값이다. 이 옵션은 backward 구현을 고르는 인자로 전달되며, 공식 설명은 deterministic backward가 추가 시간·메모리를 쓸 수 있다고 명시한다. 이번에는 값을 켜거나 새 kernel을 설치하지 않는다. 공식 API 설명과 실제 tail 전체 반복성을 구분한다. [v2.8.3 `flash_attn_func`](https://github.com/Dao-AILab/flash-attention/blob/v2.8.3/flash_attn/flash_attn_interface.py#L1096), [varlen 함수](https://github.com/Dao-AILab/flash-attention/blob/v2.8.3/flash_attn/flash_attn_interface.py#L1320)

반복 진단은 같은 checkpoint·같은 tuple·같은 RNG에서 gradient를 매번 지우고 forward/backward를 최대3회 실행한다. 매회 optimizer update는0이다. 이때 달라진 값은 **해당 tail+head 경로의 반복 차이**다. self-attention·cross-attention·FFN·norm·head·LoRA 연산을 모두 거쳤으므로 FA2 단독 원인이라고 결론낼 수 없다. 세 번 같아도 과거20회 학습 경로의 차이가 없었다는 증명은 아니다.

실행 담당자의 읽기 전용 설치 확인은 **Torch2.14.0+cu130, flash-attn2.8.4**다. 위 링크는 FA2 v2.8.3의 공식 API 설명이며 실제 설치 binary2.8.4와 같은 revision이라고 표현하지 않는다. 보존된 실제 model_scail2.py SHA는 `bbcfc38ee8c4dc8e9f31987e617b57af267c46e8bd25ee046f76e7426d6f5d6c`, attention.py SHA는 `23fe7c6f6e4065242d95e5e188cb2d1a16bd283f05dca7e7e878977158fcfdbc`다. 이번에 backend·deterministic 옵션은 바꾸지 않았다.

## 2. LoRA factor 차이와 실제 선형 연산 차이는 다르다

### 직관과 수식

LoRA는 frozen $W_0$ 위에 저랭크 변화량을 더한다. [LoRA 원논문](https://arxiv.org/abs/2106.09685v2)

$$W_{eff}=W_0+\Delta W,\qquad\Delta W=\frac\alpha r BA.$$

이번 Q/V 각각 $A\in\mathbb R^{4\times5120}$, $B\in\mathbb R^{5120\times4}$, $\alpha=r=4$다. 두 projection의 총 trainable scalar는 $2(4\cdot5120+5120\cdot4)=81920$이다. factor가 다르면 반드시 선형함수도 다르다는 결론은 성립하지 않는다. 가역 $Q\in\mathbb R^{4\times4}$에 대해

$$A'=QA,\qquad B'=BQ^{-1}\quad\Longrightarrow\quad B'A'=BA.$$

이 대수적 비유일성이 B-020/B-021 차이의 원인이라는 뜻은 아니다. 실제로 같은 $BA$였는지는 측정해야 한다. 또한 factor 좌표를 바꾸면 AdamW moment의 의미가 바뀌므로 함수가 같아도 optimizer 상태까지 동등하다고 할 수 없다.

작은 고정 입력 $X\in\mathbb R^{n\times5120}$에서 비교할 수 있는 작용은

$$D(X)=\frac\alpha r (XA^\top)B^\top.$$

거대한5120×5120 delta 행렬을 저장하지 않고도 두 adapter의 $D_1(X)-D_2(X)$를 측정할 수 있다. 이는 해당 $X$에서의 작용 비교이며 모든 입력에 대한 동일성 증명은 아니다. 필요하면 저랭크 Gram 행렬로 Frobenius norm을 계산할 수 있다.

$$\|B_1A_1-B_2A_2\|_F^2=
\operatorname{tr}(B_1^\top B_1A_1A_1^\top)+
\operatorname{tr}(B_2^\top B_2A_2A_2^\top)-
2\operatorname{tr}(B_1^\top B_2A_2A_1^\top).$$

가까운 두 값의 뺄셈은 cancellation에 민감하므로 계산 dtype·negative roundoff 처리·원시값을 밝혀야 한다. 이번 코드가 작용 검사를 채택했다면 이를 Gram 측정으로 바꾸어 서술하지 않는다.

### 코드와 정밀도

[B-020 `LowRankLinear.forward`](https://github.com/hyunlord/make-meme/blob/13ac7727e501913ed7e765f44f1d8f6385a19178/docs/research/experiments/B-020-real-fm-tail-overfit/code/lora_component.py#L34)는 `F.linear(F.linear(x.float(), A), B)`를 FP32로 계산하고 base output dtype으로 delta를 변환해 더한다. `enabled=False`이면 base만 반환한다. 따라서 FP32의 작은 $BA$ 차이와 BF16 경계 뒤의 prediction 차이가 단순 비례한다고 가정하지 않는다. adapter OFF는 A/B를 지우는 행위가 아니며 저장된 학습 상태를 보존한 기능 비교다.

## 3. scalar MSE가 같아도 velocity tensor는 다를 수 있다

### 직관과 수식

정답까지의 거리 하나만 같다고 두 예측의 위치가 같은 것은 아니다. 벡터 정답 $v^*$와 단위벡터 $e$에 대해 $p=v^*+ae$, $q=v^*-ae$는 같은 MSE를 가지지만 $p-q=2ae$다.

실제 FM 입력과 target은 다음이다.

$$z_\sigma=(1-\sigma)z_Y+\sigma\epsilon,\qquad v^*=\epsilon-z_Y,$$
$$\ell(\theta)=\frac1M\|v_\theta(z_\sigma,1000\sigma,c_+)-v^*\|_2^2.$$

이번 latent와 최종 velocity는 FP32 `[16,5,64,112]`, $M=573440$이다. B-020 `mix_velocity`와 `velocity_mse`가 같은 규약을 사용한다. [고정 FM 정의](https://github.com/hyunlord/make-meme/blob/13ac7727e501913ed7e765f44f1d8f6385a19178/docs/research/experiments/B-020-real-fm-tail-overfit/code/fm_contract.py#L61)

따라서 세 종류의 차이를 따로 적는다.

| 비교 | 답하는 질문 |
|---|---|
| $v_{21,20}-v_{20,20}$ | 독립학습 두 run의 같은 평가 입력 예측 차이 |
| $v_{21,20}-v_{OFF}$ | 저장된20회 adapter가 baseline에서 바꾼 양 |
| $v_{22,100}-v_{21,20}$ | 같은20회 상태에서 추가80회가 바꾼 양 |

각 차이에 max absolute, RMS, relative L2를 보고한다. $\operatorname{RMS}(p-q)=\|p-q\|_2/\sqrt M$, relative L2는 $\|p-q\|_2/\|q\|_2$다. 분모가0이거나 사전 정의상 너무 작으면 UNDEFINED로 두며, 임의 작은 상수를 넣어 큰 개선율을 만들지 않는다. B-021에 남은 OFF 대비 RMS는 독립 두 run prediction 차이의 대체값이 아니다.

prefix는 FP32 `[1,12992,5120]`, context는 `[1,769,5120]`, block modulation은 `[1,6,5120]`, head embedding은 `[1,5120]`다. 같은4개 tuple에서 official last block→head→unpatchify를 끝까지 실행한 velocity로 비교해야 한다. self-attention 중간 hidden의 MSE를 최종 FM 결과로 바꾸지 않는다. [B-021 `predict`](https://github.com/hyunlord/make-meme/blob/62f853b087e7b48baf3401818bfec152110bfe63/docs/research/experiments/B-021-fixed-tuple-update-budget/code/phase_train.py#L108)

## 4. checkpoint 재개는 독립 재학습과 다른 실험이다

### 직관과 수식

학습 상태는 weight만이 아니다. 이번 상태를

$$S_n=(\theta_n,m_n,s_n,n,\mathcal R_n,k_n,\mathcal O)$$

으로 쓴다. $\theta$는 q.A/q.B/v.A/v.B, $m,s$는 AdamW의 `exp_avg`,`exp_avg_sq`, $n$은step, $\mathcal R$은 CPU/CUDA RNG 상태, $k$는 다음 tuple cursor, $\mathcal O$는 optimizer 옵션이다.

$$g_{n+1}=\nabla_\theta\ell_{k_n}(\theta_n),\quad
m_{n+1}=\beta_1m_n+(1-\beta_1)g_{n+1},\quad
s_{n+1}=\beta_2s_n+(1-\beta_2)g_{n+1}^2.$$

동일 $\theta_{20}$에서도 $m=s=0$으로 새 optimizer를 시작하면21번째 update가 달라진다. B-022는 정확한 B-021 $S_{20}$을 복원해80회만 더 수행하는 질문이다. B-020의 독립20회와 엄격한 A/B 일치 여부를 다시 합격시키는 실험이 아니다.

B-021의 `save_checkpoint`는 tensor/primitive schema로 adapter·moment·step·RNG·cursor를 보존했다. [실제 저장 코드](https://github.com/hyunlord/make-meme/blob/62f853b087e7b48baf3401818bfec152110bfe63/docs/research/experiments/B-021-fixed-tuple-update-budget/code/budget_contract.py#L37)

재개 시 새 module의 parameter 객체와 저장 ID 사이를 `q.A,q.B,v.A,v.B`의 이름·shape·dtype·optimizer 순서로 연결한다. 저장 ID의 숫자만 같다고 연결이 맞는 것은 아니다. capturable=False의 step tensor 등 원래 CPU state 계약까지 확인하고 모든 state를 CUDA로 몰아넣지 않는다. 복원 후 $n=20,k=2$이므로 update21은 `train_2`다.

진단은 module 생성·temporary loading·gradient 계산 때문에 RNG나 상태를 건드릴 수 있다. 그러므로 진단을 끝낸 뒤 exact checkpoint를 다시 복원하고 gradient를 비워 실제 학습을 시작한다. 이전B-021에서 누락된20번째 scalar row는 만들지 않는다. 새로운20회 평가와 과거20번째 train loss는 다른 관측이다.

### 서로 다른 네 가지 수용 수준

| 수준 | 확인할 것 | 뜻하지 않는 것 |
|---|---|---|
| 저장물 exactness | payload hash·tensor값·dtype·이름·step·moment | GPU 함수 실행 성공 |
| 같은 상태 기능 parity | fresh reload/OFF velocity, 기존 atol=rtol1e-3와 원시차이 | B-021의 엄격한 독립 replay PASS |
| 독립학습 replay | 서로 다른 run의20회 A/B·prediction | 같은 checkpoint에서 추가학습할 수 없다는 판정 |
| 영상 결과 | 같은noise·source·조건의20/100 실제영상 | loss만으로 품질·일반화 수용 |

기반가중치는 원래 고정 모델에서 다시 로딩하고 이번 worker의 시작/종료 hash를 비교한다. 이번 PASS가 나오더라도 B-021에서 미도달한 종료 hash를 소급 PASS로 바꾸지 않는다. frozen head의 parameter gradient는 없어도 입력에 대한 미분은 유지해야 LoRA까지 chain rule이 이어진다.

## 5. loss와 영상은 같은 질문이 아니다

학습은 같은Lab clip의 고정3개 $(\sigma,\epsilon)$ 조합에 대한 경험손실이다. holdout은 같은 clip의 네 번째 noise/time이며 독립영상test가 아니다. 생성은 UniPC가 이전 예측에서 만든 상태를 순회하며40step에 positive/negative80forward를 수행한다. 새80optimizer update와80forward는 서로 다른 수량이다.

생성은 $v_{CFG}=v_-+5(v_+-v_-)$를 쓰고, 두 branch의 시각조건은 공유한다. 학습은 positive fixed tuple을 감독했으므로 fixed loss가 줄어도 생성 상태·sigma·negative prediction에서 같은 개선이 보장되지 않는다. D=Y 자기재구성 shortcut도 유지된다.

영상은 SOURCE / 같은B-021 STEP20 / 이어학습한 STEP100의17장을30fps로 비교한다. 실제목표는 사족 자연동작이지 두발춤이 아니다. reference 착석·장면복사, 사족서기, 머리방향/순서, 얼굴·귀·목 손상, reference영역 잘림/padding은 분리한다. 작은loss를 동작·개체 성공으로 표현하지 않는다. 실제 연속 재생을 관찰하지 못하면 temporal=UNVERIFIED다.

## 6. 실제 진단 관측과 아직 남은 비교

### 같은20회 상태의 기능 복원

`function-parity20.json`의 네 tuple 모두 fresh reload와 adapterOFF가 기존 atol=rtol1e-3에서 PASS했고, 원시 max_abs도 각각0이었다. 이는 **이번에 같은 저장 상태로 구성한 함수**의 복원 근거다. B-021의 엄격한 독립 A/B replay FAIL이나 미도달한 종료후 기반hash를 바꾸는 근거가 아니다.

B-022 `resume_contract.py`의 `named_parameters`(18행), `checkpoint`(24행), `restore`(43행)는 q.A/q.B/v.A/v.B 객체 순서와 optimizer ID0..3을 연결하고, moment값·dtype·device, step20·cursor2, CPU/CUDA RNG를 복원한다. `restore`는 진단후 실제학습전에 다시 호출해야 하는 계약이다. 실제 학습완료 여부는 별도 receipt로 확인한다.

### 독립20회는 loss가 가까워도 velocity가 같지 않았다

`velocity-comparison.json`에서 같은 네 cached tuple의 최종 velocity를 직접 비교했다.

| tuple | B02120−B02020 RMS | relative L2 | max_abs | B02120−OFF RMS |
|---|---:|---:|---:|---:|
| train_0 | 0.0007679161 | 0.0006439868 | 0.03125 | 0.0051003140 |
| train_1 | 0.0006053058 | 0.0004898015 | 0.03125 | 0.0035460647 |
| train_2 | 0.0005375784 | 0.0004288769 | 0.03125 | 0.0029831463 |
| holdout | 0.0005662294 | 0.0004548281 | 0.03125 | 0.0032071446 |

이번 재평가의 B020 train_0 loss는0.14547252655029297이며, 보존된 과거값0.14547254145145416과도 미세하게 다르다. 새 평가값을 역사값으로 덮어쓰지 않는다. 가까운 scalar loss와 작은 상대차이가 관측됐지만, prediction은 exact 같지 않았다. 표의 서로 다른 열을 서로의 대체 지표로 사용하지 않는다. 이 차이가 실제 영상에서 얼마나 보이는지는 이 표만으로 판단할 수 없다.

`lowrank-action.json`은 `resume_contract.lowrank_action`(74행)의 고정 비난수 linspace 입력 `[4,5120]`을 사용했다. Q작용의 RMS는1.9059915e-7, max_abs3.4095719e-6, relativeL2 0.0003123865였고, V작용은 각각9.8839600e-8,2.0045263e-6,0.0001581798이었다. 이는 네 probe에서의 실제 작용 차이이며 **전체 BA 행렬 동등성 검사나 모든 모델입력 coverage가 아니다**. 위 Gram 식은 가능한 해석 방법을 설명한 수식이며 이번 실측 알고리즘이라고 보고하지 않는다.

### 같은tail 반복은 prediction exact, gradient에는 미세차이

`repeatability.json`은 동일 train_2의 무update forward/backward3회를 기록했다. 세 loss는 모두0.031494442373514175이고, 각 backward에서3개의 실제 FA backward node와 유한한 head입력gradient를 확인했다. 반복1·2를 첫 반복0과 비교한 prediction의 max_abs/RMS는0이었다. 반면 gradient는 exact 같지 않았다.

| parameter | 반복1−반복0 max_abs | 반복2−반복0 max_abs |
|---|---:|---:|
| q.A | 4.5474735e-12 | 6.3664629e-12 |
| q.B | 1.1220891e-10 | 9.8580699e-11 |
| v.A | 1.4551915e-11 | 2.1827873e-11 |
| v.B | 2.2828317e-10 | 1.4415491e-10 |

이 표는 **첫 반복 대비 두 비교**이며 3×3 전체 pairwise matrix가 아니다. gradient norm 하나만 비교한 것이 아니라 tensor 차이 요약이지만, 전체tail을 거쳤으므로 **FA2 단독 원인은 여전히 미확정**이다. 같은출력이었다고 같은미분값까지자동으로exact라고생각할수없음을이번범위에서관측했다. 실제default연산의반복차이를측정했으며 deterministic 모드나새kernel로해결한실험은아니다.

### 같은 상태에서 실제80update를 이어간 결과

`review-training-final.json`의 독립 CPU artifact/log 검토는 B-02120회 checkpoint의18개 tensor값과 B-022출발 저장물이 byte단위로 같음을 확인했다. 새 학습 row는21..100의80개이고 첫 tuple은train_2였으며 전체순서도 일치했다. 누적100은 새로운100update가 아니라 **기존20+추가80**이다. 50/100 checkpoint의 네 optimizer step은 각각50/100, 다음cursor는2/1이고, 별도 adapter파일과 restart안의 A/B값이 일치했다.

고정 tuple별 평가는 다음과 같다. 서로 다른sigma의 loss를 하나의 시간하강곡선으로 연결하지 않는다.

| tuple / sigma | step20 | step50 | step100 |
|---|---:|---:|---:|
| train_0 /0.2 | 0.14547225832939148 | 0.145207017660141 | 0.14487498998641968 |
| train_1 /0.5 | 0.050671838223934174 | 0.05058841407299042 | 0.05047983303666115 |
| train_2 /0.8 | 0.031494442373514175 | 0.03116587921977043 | 0.030845951288938522 |
| sameclip holdout /0.65 | 0.03837939724326134 | 0.03829119727015495 | 0.038225315511226654 |

네 고정평가점의 loss는20→50→100에서 감소했다. 이는 **이번 clip·조건·sigma/noise의 경험손실 감소**이며, 독립영상일반화나 생성품질개선의 증거는 아니다. holdout에도 같은clip/조건이 남는다.

step100의 OFF대비prediction RMS는 train_0/1/2/holdout 각각0.0226572603/0.0160594210/0.0186106227/0.0163208544였다. adapter가baseline보다더큰변화를만들었다는관측이지,그변화량자체를좋은동작이라고세지않는다. 이수치는100대20직접차이가아니며 두RMS를빼서tensor차이의RMS를구할수없다.

실제비학습tail진단/평가forward는33회(상한40), 업데이트없는진단backward는3회(상한3), 추가optimizerupdate는80회였다. 학습에필요한80forward/backward와비학습33회는별도집계다. 최종100checkpoint의 freshcomponent reload와adapterOFF는기존atol=rtol1e-3에서PASS,원시max_abs0이었다.

`final-base-check.json`은 **이번B-022worker의** 기반parameter값과원본selectedstorage불변을PASS로기록했다. 이것은B-021의종료후검사NOT_REACHED를소급해소하지않는다. 독립검토도기존FAIL을보존했다. 100endpoint를고정했고더좋은중간checkpoint를골라대체하지않았다.

### 영상은 별도 결과다

| 관측 | 현재 문서 상태 |
|---|---|
| matched20/100 sampler·decode | 각40step/80forward 및1회decode 완료,17f30fps |
| 동작·개체·형상 | 양쪽착석/배경복사/후반얼굴손상·잘림잔존, 개선미입증 |
| temporal | 실제연속시청없으면UNVERIFIED |

실제100회영상도참조의착석·침실·padding을유지하고후반얼굴번짐·머리잘림이남았다. 추가학습의고정tupleloss감소가target의사족자세·고개돌림품질개선으로이어졌다는증거는확보하지못했다. 모든17프레임을검토했으며연속시청은미확인이다. 기존B02020영상은새matched20결과를대신하지않는다.

B-021의 기존FAIL은고정된역사이고, B-022의질문은새계약이다. 결과가없거나실패한항목을개념설명으로PASS시키지않는다. 후속200/500회·커널최적화·새학습층은이번승인에포함되지않는다.

## 이해 확인 질문

1. 같은seed와같은dropout0인데세번의backward gradient가미세하게달랐다. 이사실만으로FA2버그라고말할수없는이유는무엇인가? 어떤것을통제했고어떤것을아직분리하지못했는가?
2. 두adapter의A/B가다르지만고정입력에서velocity가매우가깝다. 이것이모든입력과영상에서동일함을뜻하는가? $A'=QA,B'=BQ^{-1}$와optimizer moment를함께설명하라.
3. 저장된20회adapter에freshAdamW80회를더하는것과restart20에서80회를재개하는것은어떻게다른가? scalarloss가같아도두prediction이다를수있는간단한예를들어라.

## 별도 해설

1. 난수상태·입력·adapter·optimizerupdate0은통제할수있지만실제계산은attention만이아닌tail전체다. 합산순서·dtype경계·다른backward연산도포함된다. FA2경로사용은관측할수있어도단독원인격리실험이아니므로원인은단정하지않는다. 세번일치한경우에도과거20step의모든실행순서를재현한것은아니다.
2. factor비유일성은실수대수에서같은BA를만드는다른분해가가능하다는뜻이다. 소수입력의근접출력은전입력동일성도영상품질동일성도보장하지않는다. AdamW는factor좌표별moment를기억하므로동일BA라도연속학습상태는달라질수있다. B-022는분해를재선택하지않고저장된실제factor와moment를그대로복원한다.
3. freshAdamW는moment와bias-correctionstep을0으로되돌린다. 정확한재개는step20과cursor2·RNG·모든옵션까지복원해train_2부터시작한다. $v^*+ae$와$v^*-ae$는같은정답MSE지만서로$2ae$다르다. 그래서loss와velocity차이를별도로측정한다.
