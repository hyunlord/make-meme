# B017 — paired data가 어떤 조건의 사용을 가르치는가

상태: **공식 소스 감사 완료 / 완전한 source-file case 2개·불완전한 Lab 후보 1개 / training-ready 0 / 모델 인코딩·학습·생성 NOT_RUN**. 실제 dataset 계약은 [TRAIN_INTERFACE](../experiments/B-017-paired-animal-data/TRAIN_INTERFACE.md), 권한은 [PUBLIC_DATA_AUDIT](../experiments/B-017-paired-animal-data/PUBLIC_DATA_AUDIT.md)에 분리했다.

## 1. 직관: 정답이 있다는 것과 원하는 문제를 학습한다는 것은 다르다

R은 목표 개체 reference, D는 motion driving, Y는 supervised target, M은 correspondence/environment mask, T는 text다. 목표는 p(Y|R,D,M,T)를 근사하는 것이다. 학습 데이터에서 D=Y라면 D 안에 target의 개체·자세·배경이 모두 들어 있다. 모델이 R을 무시하고 D를 복원해도 loss가 낮아질 수 있다. 단순 loss 감소는 reference 사용이나 개체/자세 분리의 증거가 아니다.

한 Y에 서로 다른 자세의 R_a/R_b를 붙이면 reference pose의 변화에 대응할 기회를 주지만, D=Y인 shortcut까지 없애지는 않는다. cross-ID motion pair는 R/Y가 목표 개체A, D는 다른 개체B이고 motion event·방향·시간이 맞아야 한다. 임의의 두 ‘걷는 개’ 영상은 이 계약이 아니다. 체형이 다를 때 픽셀 좌표의 완전 일치도 올바른 목표가 아니다.

현재 원본의 track 일관성은 생물학적으로 동일한 실사 개체의 증명이 아니다. 제3자 원본의 synthetic origin과 training rights가 미확인이면 REAL_GT/학습-ready로 쓰지 않는다. Lab reference 사진이 실제여도 Lab의 target 동영상 Y가 존재하는 것은 아니다. 과거 실패한 생성물을 positive target으로 승격하지 않는다.

## 2. 수식과 조건부 기대값

교육용 표기 x=E(Y), ε~N(0,I), σ∈(0,1)에서

\[
z_\sigma=(1-\sigma)x+\sigma\epsilon,\quad u=\epsilon-x.
\]

이는 data→noise 방향의 선형 경로다. 조건 c=(R,D,M,T)에서 제곱오차 최적해는

\[
v^*(z,\sigma,c)=\mathbb E[u\mid z,\sigma,c].
\]

고정 관측 a=(z,σ,c)에 대해 m=E[u|a]라 두면 `E[||u-v||²|a]=E[||u-m||²|a]+||m-v||²`다. 교차항은 E[u−m|a]=0으로 사라진다. 따라서 여러 표본 경로가 교차해도 단일 network는 각 경로를 식별해 외우는 대신 조건부 평균 속도를 근사할 수 있다. 실제 finite model/최적화/데이터에서는 이 이상적 최적해에 도달한다고 보장하지 않는다.

학습에는 Y가 필요하지만 추론에는 학습된 v와 초기 noise, 조건을 사용한다. 생성은 높은σ에서 낮은σ 방향이다. noise 시간σ와 영상 시간 k/fps는 다른 축이며 optimizer update와 inference의40 scheduler step도 다르다.

## 3. 실제 pinned loss는 어디가 다른가

SAT commit `ac63f8eb369e2f4fac2ce273ead0ae7e602c3919`의 [RFLoss](https://github.com/zai-org/SCAIL-2/blob/ac63f8eb369e2f4fac2ce273ead0ae7e602c3919/sgm/modules/diffusionmodules/loss.py#L653-L766)는 B,T,C,H,W latent에서 ε−x target을 사용한다. σ는 LogisticNormal 표본에 spatial patch 수 기반 shift를 적용하며 model timestep은1000σ다. 논문 introductory ε-prediction 식으로 실제 구현을 덮어쓰지 않는다.

history H 영역은 noisy 경로 대신 깨끗한 x를 제공한다. 실제 loss는 `(1−H)(1−OCR)(prediction−(ε−x))²`를 **전체 tensor 원소 수**로 나눈다. 유효 원소 수로 재정규화하지 않으므로 history/OCR 비율이 다른 batch의 loss를 곧바로 품질 차이로 해석하면 안 된다. 위 조건부 기대값 설명은 표본별 가중이 없는 기본 MSE의 유도이며, 일반적인 target 의존 가중 MSE에서는 최적해가 E[w u|a]/E[w|a]로 달라질 수 있다. 실제 mask/dropout 계약도 함께 확인해야 한다.

[cache writer](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/cache_scail2_wds.py#L208-L302)는 Y latent, D latent, R latent와 RGB reference, masks를 분리한다. 17pixel프레임은 latent T5다. `first_frame_pth`는 R 뒤 zero RGB를 이어 인코딩한 tensor이며 GT첫프레임이 아니다. 현재 SAT forward는 그 필드의 존재를 gate로 쓰고 실제 x에는 history mask를 concatenate한다. generic inference16leaf cache를 supervised dataset으로 그대로 바꾸면 Y·history·loss mask 계약이 빠진다.

실제 CPU에서 관측한 Y/D는 RGB `[17,896,512,3]`에 대응하는17장의512×896 영상이다. 아래 latent shape는 고정 writer의 stride 규약에서 계산한 예상값이며 이번에 VAE를 실행해 관측한 값이 아니다.

| 경로 | 예상 writer shape | SAT batch 관점 |
|---|---|---|
| Y latent | `[16,5,112,64]` | `[B,5,16,112,64]` |
| R latent | `[16,1,112,64]` | reference prefix 1시점 |
| D latent, spatial half encode | `[16,5,56,32]` | `[B,5,16,56,32]` |

mask의7색상 채널/시간 packing과 history4채널은 RGB alpha와 다르다. 이 데이터 계약을 지킨 후에야 train forward/loss와 연결할 수 있다. 이번에는 실제 latent 값/gradient를 생성하지 않았다.

## 4. 사례가 식별하는 것과 못 하는 것

| 자료 | 가능한 질문 | 입증하지 못하는 것 |
|---|---|---|
| 같은 clip 복원 D=Y | data→forward→loss 배선, 제한 overfit | reference 활용·cross-ID 전이 |
| 같은 Y, 다른 시점 R_a/R_b | reference pose 민감도 | D 외형 shortcut 제거 |
| 정렬된 다른 개체 D와 목표 Y | identity/motion 조합 학습 후보 | 권한·event alignment 없이는 유효 pair 아님 |
| 다른 source/identity held-out | 제한 일반화 평가 | 같은 clip 인접 프레임 random split은 해당 안 됨 |

실제 파일 준비와 정적 검토 결과는 다음과 같다. 여기서 ‘완전’은 source-file 구성의 완전성이며 학습 실행 가능성이나 권리 확보를 뜻하지 않는다.

| 실제 후보 | R / D / Y | 관측과 판정 |
|---|---|---|
| `self_f7` | R=f7, D=Y=f7..23 | source-file 구성 완료. D=Y인 self-reconstruction 배선 후보이며 독립적인 motion/identity 분리 증거가 아님 |
| `pose_f0` | R=f0, D=Y=f7..23 | R은 Y 시간 구간 밖이다. 그러나 f0/f7은 전반적으로 비슷한 직립 자세이고 화면상 크기·위치 차이가 있어, 충분한 독립 pose variation은 NOT_ESTABLISHED |
| Lab 후보 | 실제 Lab 사진 R만 있음 | Lab Y가 없으므로 incomplete. source의 다른 강아지 Y를 Lab 정답으로 대체하지 않음 |

Y의 후반 f23에서는 뚜렷한 머리 roll이 관측되지만, 이것만으로 f0와 f7 reference의 자세 다양성이 입증되지는 않는다. 두 완전 case는 동일 제3자 clip의 development 자료다. 원본의 synthetic origin과 학습 권리가 UNKNOWN이므로 둘 다 training_ready=false다. 실제 cross-ID motion pair는 0개이고, 권한을 포함한 training-ready case도 0개다. ‘private CPU smoke용 파일 준비 YES’와 ‘model/loss/optimizer smoke 실행 NOT_RUN’을 분리한다. 이미 반복 관찰한 source를 이름만 바꿔 held-out test로 삼지 않는다.

다음 제안은 하나다. 소유자가 직접 촬영했거나 사용을 승인한 실제 Lab의 자연스러운 움직임 영상과 다른 자세의 사진을 확보하고, 촬영 scene을 나눠 hold-out을 구성하는 데이터 수집이다. 강제로 춤추게 하거나 즉시 LoRA를 실행하는 제안이 아니며, 아직 수행하지 않았다.

## 5. LoRA와 메모리

LoRA는 W_eff=W0+(α/r)BA로 일부 update를 제한한다. 작은 rank가 backward activation·frozen base residency·optimizer state를 없애지는 않는다. 공식 SAT에는 generic LoRAMixin과 lora_train 분기가 존재하지만, 공개 SCAIL 예제의 adapter 주입과 이름 기반 optimizer 선택이 완성된 recipe라는 증거는 없다. [감사 §5](../experiments/B-017-paired-animal-data/TRAIN_INTERFACE.md#5-lora-판정-문자열-존재와-실행-경로를-구별)를 따른다. 이번에는0 update다.

향후 허가된 소형 pilot이라도 실제 trainable 이름/수·초기화·2–3step gradient/weight delta·base 보존·save/reload를 검증해야 한다. B가 zero 초기화일 때 첫 step의 일부 A gradient가0인 것은 자연스러우며 모든 tensor에 즉시 nonzero를 요구하면 잘못된 검사다. 기존 no_grad 추론 메모리로 학습 fit을 보장하지 않는다.

## 이해 확인 질문

1. D=Y에서 loss가 내려가면 reference 개체 활용을 입증한 것인가?
2. 17프레임 입력에 공개 latent bucket17을 그대로 쓰면 되는가?
3. history가 많은 batch의 loss가 작아졌다면 모델 품질이 나아진 것인가?

## 별도 해설

1. 아니다. D만 복사하는 shortcut으로도 목표가 설명된다. reference 변화와 독립 identity/motion 평가가 필요하다.
2. 아니다. VAE 시간 압축 후 T5이며 공개 bucket17/21과 다르다. 실제 loader/config 계약을 별도로 맞춰야 한다.
3. 아니다. 현 loss는 mask0 영역을 포함한 전체 원소 평균이다. mask 비율·조건·평가 task가 같아야 제한적으로 비교할 수 있다.
