# B020 — 실제 영상 latent의 FM target과 고정 prefix를 이용한 제한적 학습

상태: 공식 코드 계약 판독 완료, 실제 encoding·4tuple prefix·20update/reload·전후 영상 완료. 이번 입력은 사용자 제공 실제 Lab 자연동작 영상의 원본 f126..142, 17frame/30fps와 기존 별도 시점의 앉은 Lab 사진이다. 이번 처리 canvas는 landscape H512/W896이며 reference 사진은 letterbox한다. 사용자 허용 범위는 비공개 연구용이고 공개 재배포 허가로 확대하지 않는다. 실제 파일·허용 범위·geometry 판정은 입력 담당자의 manifest를 따른다. 이전 제3자 영상의 권리 미확인 기록을 이번 자료로 소급 변경하지 않는다.

## 1. 인공 hidden target에서 실제 velocity target으로

Y는 실제 목표 RGB 영상, z_Y=E_VAE(Y)는 VAE latent다. epsilon은 z_Y와 같은 shape의 독립 Gaussian noise다. 이번 규약은

\[
z_\sigma=(1-\sigma)z_Y+\sigma\epsilon,\qquad u=\epsilon-z_Y,
\]
\[
L=\frac1{CTHW}\|v_\theta(z_\sigma,1000\sigma,c)-u\|_2^2.
\]

sigma0은 data, sigma1은 noise이며 생성은 높은 sigma에서 낮은 sigma로 진행한다. 영상의 물리 시간 k/30초와 noise time sigma는 별개다.17frame의 첫·끝 표본 간격은16/30초, MP4 duration은17/30초다. 30fps를16/24fps로 표시해 속도를 바꾸지 않는다.

이는 단순히 랜덤 hidden target에 가까워지게 했던 B018/019와 다르다. 실제 Y의 latent와 sigma/noise에서 목표가 정의된다. 그러나 FM target을 쓴다고 cross-ID 학습·안무 분리가 자동 성립하지는 않는다.

## 2. 고정 소스의 부호·scale·축

SAT revision `ac63f8eb369e2f4fac2ce273ead0ae7e602c3919`의 [RFLoss L653–766](https://github.com/zai-org/SCAIL-2/blob/ac63f8eb369e2f4fac2ce273ead0ae7e602c3919/sgm/modules/diffusionmodules/loss.py#L653-L766)는 `(1-sigma)*input+sigma*noise`, target=`noise-input`이다. [RFScaling L71–79](https://github.com/zai-org/SCAIL-2/blob/ac63f8eb369e2f4fac2ce273ead0ae7e602c3919/sgm/modules/diffusionmodules/denoiser_scaling.py#L71-L79)은 c_skip0/c_out1/c_in1, c_noise=1000sigma다. epsilon prediction이나 DDPM의 v parameterization으로 바꿔 부르지 않는다.

SAT reader는 batch를 B,T,C,H,W로 바꿔 loss에 주지만 Wan inference forward는 list의 각 tensor C,T,H,W를 받는다. transpose가 필요한 경계와 실제 shape를 기록하고, 같은 원소 수라는 이유로 잘못된 축을 허용하지 않는다. 이번 실제 처리 규격 landscape H512/W896의 VAE latent 기대 shape는 `[16,5,64,112]`(C,T,H,W)다. patch1×2×2 이후 generated grid는 T5/H32/W56으로8960 token, reference는1×32×56=1792 token, 절반 공간 driving은5×16×28=2240 token이며 합12992 token이다. P 실행에서 실제 target `[16,5,64,112]` FP32를 확인했고 저장·readback은 exact였다. generated/reference/driving token 수는 해당 실제 latent shape와 공식 patch 계약에서 계산한 값이다.

실제 SAT는 LogisticNormal sigma와 spatial shift, history/OCR 제외를 포함한다. 이번은 history/OCR0, 고정 sigma3개+평가1개이며 caption dropout·augmentation도 추가하지 않는다. 따라서 실제 FM target을 사용한 제한적 tail 회귀이지 공개 SAT 전체 학습 recipe 재현이 아니다.

## 3. 왜 prefix를 캐시할 수 있고 언제 무효가 되는가

가중치가 고정된 앞39개 block과 embedding을 F라 두면

\[
h_{38}=F_{\mathrm{frozen}}(z_\sigma,1000\sigma,R,D,M,\text{text}).
\]

학습 대상이 마지막 block39의 q/v LoRA뿐이므로 앞쪽에는 parameter gradient가 필요 없다. no_grad로 계산한 h38을 일반 tensor로 저장해 학습에 재사용할 수 있다. inference_mode tensor를 무심코 학습 graph에 섞는 것은 다른 문제다. [PyTorch autograd](https://docs.pytorch.org/docs/2.14/notes/autograd.html#locally-disabling-gradient-computation).

캐시 단위는 clip이 아니라 **전체 고정 tuple**이다. sigma/noise·R/D/mask·text·crop/geometry·history/dropout·base weights·precision·position 설정이 달라지면 h38의 의미도 달라진다. sigma를 새로 뽑았다고 말하면서 예전 h38을 쓰면 해당 FM 문제를 학습하지 않는다. 같은 tuple에서 tail optimizer만 바뀌는 경우에는 frozen prefix가 그대로여서 재사용이 가능하다.

이번 train tuple은 sigma0.2/0.5/0.8와 각각 seed2026102401/2026102402/2026102403의 고정 noise, holdout은 sigma0.65와 seed2026102404의 별도 noise다. 실제 target tensor SHA는 `84379b6cb4315e3d23b727f8ffed72e013bde369080b3ec8a02948364becb54f`다. 네 noise hash는 사전 고정 `configs/fm.json`에 있다. clip/identity가 같으므로 이것은 noise/time holdout이며 독립 영상 validation이 아니다.20 update 동안3tuple을 순환해도 서로 다른20개 영상이 생기는 것은 아니다. tensor hash·dtype·shape·sigma/seed·condition hash를 함께 묶어 저장한다.

## 4. e와 e0, 공식 head와 unpatchify

Wan revision `78fe19576bb06be96c2375e088574a262a300edb`의 [time embeddings L782–799](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/modules/model_scail2.py#L782-L799)는 e=`time_embedding(sinusoidal(t))` `[B,5120]` FP32, e0=`time_projection(e).unflatten(6,5120)` `[B,6,5120]` FP32를 만든다. block은 e0, head는 e를 받는다. e0의 앞부분을 잘라 head e로 대신하면 안 된다.

[Head L464–491](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/modules/model_scail2.py#L464-L491)는 learned modulation `[1,2,5120]`에 e를 더해 scale/shift를 만들고 LayerNorm→modulation→Linear를 적용한다. patch1×2×2, out_dim16이면 token당64개 값을 출력한다. head는 고정되지만 연산 graph를 끄면 앞 LoRA gradient가 사라질 수 있다.

[forward/head/unpatchify L867–901](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/modules/model_scail2.py#L867-L901)는 head 결과에서 `offset=additional_ref_length+ref_length` 이후 `prod(grid_sizes)`개의 generated token만 잘라 reshape/einsum으로 C,T,H,W를 복원한다. reference prefix와 trailing driving token을 FM target에 포함하지 않는다. 이번 additional_ref0에서도 ref prefix 제외는 필요하다.

phi가 tail LoRA이면

\[
\nabla_\phi L=J_{\mathrm{tail},\phi}^{T}J_{\mathrm{head}}^{T}J_{\mathrm{unpatchify}}^{T}\nabla_v L.
\]

head weight gradient가 None이어도 head input derivative는 필요하다. unpatchify는 tensor 재배열·generated 선택이며 미분 연결을 보존한다. 학습 branch 전체의 no_grad나 detach는 금지다. tail split parity는 동일 tuple의 원래 전체 forward velocity와 split tail/head 출력을 비교해 검증한다. parity 실패를 loss 감소로 덮지 않는다.

## 5. 무엇을 학습했고 무엇을 입증하지 못하는가

조건 c는 R,D,M,text다. D=Y인 SELF_RECON_FM_SMOKE에서는 D가 target 개체·배경·동작을 모두 포함한다. reference를 무시하고 driving 정보를 복원해도 loss가 줄 수 있다. train3tuple loss 감소와 holdout loss 감소를 각각 기록하되 reference identity 사용·pose 분리·새 개체 일반화·춤 품질의 증거로 바꾸지 않는다.

실제 sampler 비교는 별도의 초기 noise/조건/CFG/timebase가 같은 baseline vs trained이어야 한다. training의 positive velocity1회와 CFG 두 branch×40step은 다르다. 학습 target z_Y를 최종 생성 결과로 decode해 놓고 모델 생성이 개선됐다고 하면 안 된다. 실제 연속 재생을 관찰하지 못하면 temporal quality는 UNVERIFIED다.

## 6. 관측 자리와 종료 경계

입력 encoding,4tuple prefix, split parity, 최대20update, frozen base/adapter delta, train/holdout before-after, reload/OFF, sampler/decode는 각각 실제 receipt에 따라 갱신한다. 실제 P·4tuple prefix·20update·10tail평가를 완료했다. 네 split parity와 fresh reload/OFF max_abs는0, 기반가중치는 불변이었다. 전후 전체17장의 정적 검토에서도 착석자세와 후반 머리잘림이 남아 목표품질 개선은 입증되지 않았다. 기술적 PASS를 품질 PASS로 바꾸지 않는다. 소형 단일 block의 이전 성공이 전체 training 메모리 보장도 아니다. 학습 phase에서는 prefix를 종료하고 tail/head만 두며, 영상 sampler는 전체 모델을 사용하는 별도 phase다.

## 이해 확인 질문

1. 같은 clip이면 sigma/noise를 바꿔도 h38을 재사용할 수 있는가?
2. head가 frozen이면 head forward를 no_grad로 감싸도 되는가?
3. sigma0.65 holdout loss가 내려가면 다른 Lab 영상과 cross-ID 안무 일반화가 입증되는가?

## 별도 해설

1. 아니다. z_sigma와 time conditioning이 달라져 frozen 함수의 입력이 바뀐다. 새 tuple의 prefix를 다시 계산해야 한다.
2. 아니다. LoRA까지 전할 head input derivative가 필요하다. parameter freeze와 graph 차단을 구별한다.
3. 아니다. 동일 clip의 제한된 noise/time 외삽·보간 관측일 뿐이다. D=Y shortcut과 영상/개체 독립성 문제가 남는다.

## 이번 실행 코드 연결

- [실제 Y 인코딩](../experiments/B-020-real-fm-tail-overfit/code/phase_prepare.py): `owner.vae.encode`가 실제 목표 영상을 정상 규약으로 인코딩한다.
- [FM 계약](../experiments/B-020-real-fm-tail-overfit/code/fm_contract.py): 고정 tuple과 혼합/target, FP32 MSE, 사전 parity 허용오차.
- [prefix 추출](../experiments/B-020-real-fm-tail-overfit/code/phase_prefix.py): 같은 전체 forward의 block39 입력과 head e 및 최종 velocity를 저장한다.
- [tail 학습](../experiments/B-020-real-fm-tail-overfit/code/phase_train.py): 고정 head의 derivative를 유지하고 adapter만 AdamW에 전달한다.
- [실제 생성](../experiments/B-020-real-fm-tail-overfit/code/phase_sample.py): baseline/학습 adapter 차이만 있는40step CFG 비교.

## 실제 prefix에서 관측한 경계

4tuple 각각 한 번의 전체 positive forward에서 `h38=[1,12992,5120]` FP32, post-projection context `[1,769,5120]` FP32, block e0 `[1,6,5120]` FP32, head e `[1,5120]` FP32를 저장했다. mixed precision의 Linear가 BF16이어도 residual/normalization 경계의 실제 hidden이 FP32일 수 있다. 모델 이름이나 base Linear dtype으로 cache dtype을 추정해 바꾸지 않았다. RoPE 복소수 frequency는 real view `[8192,64,2]` FP64로 lossless 저장하고 복소수로 복원한다.

## 실제 FM 수치 결과

| tuple | sigma | 학습 전 MSE | 학습 후 MSE | 해석 |
|---|---:|---:|---:|---|
| train_0 | 0.2 | 0.1455920786 | 0.1454725415 | 고정 학습 tuple |
| train_1 | 0.5 | 0.0507136025 | 0.0506716855 | 고정 학습 tuple |
| train_2 | 0.8 | 0.0315620080 | 0.0314944796 | 고정 학습 tuple |
| holdout | 0.65 | 0.0384031795 | 0.0383795351 | 같은 clip의 noise/time holdout |

감소 폭은 작다. 서로 다른 sigma의 update loss를 하나의 단조 곡선으로 읽지 않으며, 같은 tuple의 전후 값만 대응시킨다. 각 update에서 실제3개 FA backward 경로와 frozen head 입력 gradient를 관측했다. 초기 Bzero에서는 A gradient0/B gradient양수가 정상이었고 이후 A/B가 모두 변했다.20update를 끝낸 뒤에는 추가튜닝하지 않았다.

학습 worker38.8368초·CUDApeak4,854,839,808bytes는 마지막block+head와 고정 cache를 사용하는 이번 실행의 실측이다. 전체40block backward·새clip·다른토큰길이의 메모리 보증이 아니다.

## 이번 관측의 해석

실제FM target과gradient연결이맞아도20update/마지막Q/V만으로시각목표가달성되지는않았다. loss는작게줄었으나target의서있는전신은전후모두재현되지않았다. 낮은loss만으로reference사용·자세분리·안무성공을말할수없는실제예다. 최적화량·학습가능용량·조건의지배성은이번단일실험으로서로분리해식별하지못한다. temporal은실제연속재생미관찰로UNVERIFIED다.
