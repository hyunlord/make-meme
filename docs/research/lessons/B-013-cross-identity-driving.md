# B-013 — 개체가 달라졌을 때 driving 활용을 어떻게 읽는가

현재 B-013의 실제 생성·품질은 **NOT_RUN**이다. [계획](../experiments/B-013-lab-driving-transfer/PLAN.md)은 기존 B-012 source [7,24) MOV/STILL을 보존하고, 실제 Lab reference를 쓰는 LAB_MOV/LAB_STILL만 한 번씩 생성한다. 다음 shape는 기존 동일 규격 경로의 예상이며 새 P 실측으로 갱신한다.

## 1. 두 비교의 질문이 다르다

Lab 내부에서는 reference·text·noise·가중치를 고정하고 driving RGB+mask의 시간 정보만 바꾼다. 반면 B-012 행에서 Lab 행으로 바꾸면 얼굴뿐 아니라 reference의 착석 자세·체형·배경·CLIP/latent와 text도 함께 달라진다. 네 셀을 나란히 표시해도 순수 identity 효과나 통계적 2×2 상호작용을 추정하는 설계는 아니다.

\[
v_\theta(z_\tau,\tau;c_{ref},c_{drive},c_{mask},c_{text}),\qquad
Y=\operatorname{Decode}(\operatorname{Sample}(\epsilon,c)).
\]

Lab pair의 조건은 \(c^{MOV}=(R_{Lab},E(D_{0:16}),M_{0:16},T_{Lab})\), \(c^{STILL}=(R_{Lab},E(D_0^{repeat}),M_0^{repeat},T_{Lab})\)다. 동일 초기 \(\epsilon\)을 실제 bytes·shape로 확인한다. 여기서 \(\Delta_{drive}\)는 단순 픽셀 차이가 아니라 **사전 source 사건에 어느 출력이 더 대응하는가**라는 평가 질문이다. 두 출력이 다르다는 사실만으로 유용한 제어를 주장하지 않는다.

## 2. 전체 자세와 국소 제어는 동시에 다른 결과를 낼 수 있다

source는 뒷발 직립·앞발을 든 자세이고 reference Lab는 착석이다. LAB_MOV가 앉은 채로 후반 머리만 source 방향으로 기울일 수 있다. 그 경우 전신 자세 전이는 실패하지만 국소 driving 활용의 부분 근거는 남는다. 둘을 하나의 PASS/FAIL로 합치면 무엇을 배웠는지 잃는다.

평가 축은 전신 직립/앞발 배치, 몸통 대비 머리 roll 방향·순서, 실제 개체·넓은 몸통/굵은 사지, 세부 형태/가림/접촉이다. 검은 털과 Lab 유사성만으로 실제 반려견 identity를 수용하지 않는다. source와 Lab의 형태가 달라 절대 pixel landmark 일치를 주 정답으로 쓰지 않는다. 신뢰할 눈·몸통 관측이 없으면 각도나 gain을 만들지 않는다.

`replace_flag=False` animation에서는 reference 침실이 유지될 수 있다. 이는 source 스튜디오의 배경 보존을 요구하는 replacement 과제가 아니다. 침실 유지와 착석 유지 실패는 분리한다. source에 맞춘 사후 warp·zoom·시간 이동으로 차이를 없애지 않는다.

## 3. 실제 조건 경로와 예상 shape

고정 [scail.py L435–453](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/scail.py#L435-L453)은 RGB driving을 공간 절반 크기로 줄여 VAE encode한다. `pose_latents`라는 이름은 이번 입력이 skeleton이라는 뜻이 아니다. [VAE encode L515–542](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/modules/vae.py#L515-L542)는 첫1장 이후4장씩 temporal cache로 처리한다. STILL도 반복 RGB 비디오를 실제 encode하며 MOV latent 첫 slice 반복으로 대체하지 않는다.

| 조건 | 예상 tensor | Lab pair 내부 |
|---|---|---|
| noise | `[16,5,112,64]` FP32 | 동일 |
| reference | `[16,1,112,64]` FP32 | 동일 |
| reference mask | `[28,6,112,64]` FP32 | 동일 |
| driving | `[16,5,56,32]` FP32 | 변경 기대 |
| driving mask | `[28,5,56,32]` FP32 | 변경 기대 |
| CLIP | `[1,257,1280]` FP16 | 동일 |
| text | `[L,4096]` BF16 | 동일, L은 새 P에서 확인 |

[두 CFG dictionary L480–508](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/scail.py#L480-L508)에는 같은 visual 조건이 연결된다. 따라서 Lab 내부 cache는 양 branch driving/mask 4leaf 변경, 나머지12leaf 보존이다. 이것은 두 의미 조건의 양 branch 연결이지 네 독립 개입이 아니다. B-012 대비는 reference latent2·reference mask2·CLIP2·positive1의 변경을 별도 허용하며, driving·noise 등 대응 control을 실제로 비교한다. mask는 shape가 같아도 값이 달라질 수 있다.

[모델 결합 L741–803](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/modules/model_scail2.py#L741-L803)은 reference/generated/driving patch와 text/CLIP 문맥을 사용한다. 이 구조에서 여러 단서가 함께 처리된다는 사실만으로 특정 attention이나 feature가 실패 원인이라고 단정하지 않는다. 이번에는 내부 attention 개입이나 학습을 하지 않는다.

## 4. CFG와 물리 시간

[CFG L389–410](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/scail.py#L389-L410)는 \(v_{cfg}=v_u+5(v_c-v_u)\)다. empty-text branch도 visual 조건을 공유한다. CFG를 높이면 motion만 선택적으로 강화된다고 가정할 수 없다. 이번 값은5로 고정한다.

noise time \(\tau\)와 frame time \(t_k=k/24\)는 다른 축이다. UniPC40step·CFG80forward는 영상80장이 아니다. 출력은17장·24fps, sample 간격은0~16/24초, 파일 길이는17/24초다. 원본 index7~23을 그대로 쓰며 이번에는 새 촬영 해상도·속도·보간·재학습을 도입하지 않는다. 출력 fps 기본값만으로 모델 전체의 학습 fps를 단정하지 않는다.

## 5. 결과를 읽기 전에 고정하는 한계

B-012의 local0/12/14/16 사건과 전체17장 coverage를 유지한다. 두 Lab 조건은 가능하면 동일 크기 A/B 패널로 먼저 읽을 수 있지만 source를 본 같은 에이전트의 검토를 독립 인간 blind 평가로 부르지 않는다. mask 경계 결함과 흐린 발끝은 숨기지 않는다. 실제 연속 재생이 없으면 temporal=UNVERIFIED다.

현재 새 P·sampler·decode·시각 결과는 근거 대기다. 같은 seed 한 pair는 탐색 증거이며 여러 개체/동작/seed의 일반화나 새로운 학습 방법의 기여가 아니다. 이번은 학습0 baseline이다. 결과 후 다음 가설 하나를 고르되 자동 실행하지 않는다.

## 이해 확인 질문

1. LAB_MOV만 앉은 채 머리 roll을 재현했다면 전체 목표와 조건 활용을 어떻게 구분하는가?
2. B-012와 B-013의 차이를 identity 하나의 인과 효과라고 할 수 없는 이유는 무엇인가?
3. STILL에도 같은 reference와 text가 있는데 움직이면 계약 위반인가?

## 별도 해설

1. 전신 자세 전이는 실패다. 그러나 LAB_STILL 대비 source 방향·순서에 대응하는 국소 머리 제어는 별도 부분 근거다. 원인을 attention 수준으로 확정하지 않는다.
2. reference의 자세·체형·배경·인코딩과 text까지 함께 바뀐다. 통제된 비교는 같은 Lab task 안의 MOV/STILL이다.
3. 아니다. 생성 prior와 text/reference에서 변화가 나올 수 있다. STATIC COPY는 비생성 정지 출력이고 STILL은 정적 driving을 받은 생성 출력이다.
