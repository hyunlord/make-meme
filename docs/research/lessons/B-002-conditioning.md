# B-002: 배경을 바꾸면 왜 같은 모델의 출력도 달라지는가

이론은 결과를 대신하지 않는다. 실제 관측과 실행 상태는 실험의 RESULTS.md, 입력 구현 근거는 [CODE_AUDIT](../experiments/B-002-reference-background/CODE_AUDIT.md), 사전 질문은 [QUESTIONS](../experiments/B-002-reference-background/QUESTIONS_KO.md), 해설은 [ANSWERS](../experiments/B-002-reference-background/ANSWERS_KO.md)에 분리한다. 아직 RESULTS가 작성되지 않았다면 관측 판정은 미완료다.

## 직관과 실험 변수

생성기를 `Y=G_theta(epsilon;S,R,T,M,lambda)`라 쓰자. Y는 출력 RGB 영상, theta는 고정 모델 가중치, epsilon은 초기 latent noise, S는 Canny 구조 영상, R은 실제 참조 사진, T는 text 조건, M은 생성용 video mask, lambda는 CFG·VACE scale·scheduler·해상도 같은 실행 설정이다. 영상의 frame축은 별도로 tau라 부른다.

주 비교는 R과 `R_bg=alpha*R+(1-alpha)*255`다. alpha=1인 전경 내부 RGB는 그대로 두고 배경을 흰색으로 바꾼다. 흰색은 새로운 영상 내용을 생성한 것이 아니라 고정 픽셀 개입이다. resize filtering과 soft-alpha 경계에서는 전경 가장자리 RGB도 달라질 수 있으므로 따로 기록한다. reference의 앉은 자세는 그대로 남는다.

모델은 reference를 '얼굴', '자세', '배경'이라는 서로 독립적인 정답 슬롯으로 받지 않는다. 전체 RGB를 VAE로 encode한다. 따라서 R의 방 배경이 생성에 영향을 주어도 이상하지 않으며 배경 제거가 외형·자세에 함께 영향을 줄 수도 있다.

## 조건부 기대값에서 경로 변화까지

설명용 시간 t는 noise→data 방향이다. 독립 noise X0와 데이터 X1에 대해 `X_t=(1-t)X0+tX1`, target `U=X1-X0`라 하자. 조건 c에서 제곱오차를 최소화하는 예측은 `v*(x,t,c)=E[U|X_t=x,t,c]`다.

증명은 mu=E[U|x,t,c]를 넣어 `E[||U-a||²|x,t,c]=E[||U-mu||²|x,t,c]+||mu-a||²`로 분해하면 된다. 교차항은 `E[U-mu|x,t,c]=0`이라 사라진다. 조건 c가 달라지면 같은 x,t의 최적 velocity도 달라질 수 있다. 고정 가중치 network에서도 conditioning이 달라지면 forward 값과 ODE 경로가 달라진다. 새 학습을 했다는 뜻은 아니다.

실제 pinned Wan은 sigma=1−t 방향을 사용한다. `z_sigma=(1-sigma)z_clean+sigma*epsilon`, target `epsilon-z_clean`, sampling은 `z_next=z+(sigma_next-sigma)*v_theta`다. delta sigma가 음수인 점을 빼먹으면 정반대로 움직인다. 근거: [scheduler](https://github.com/modelscope/DiffSynth-Studio/blob/f39d731a3e318d25b725eb3389cfddb184619842/diffsynth/diffusion/flow_match.py#L436), [실제 loss](https://github.com/modelscope/DiffSynth-Studio/blob/f39d731a3e318d25b725eb3389cfddb184619842/diffsynth/diffusion/loss.py#L5). B-002는 loss 계산이나 optimizer update 없이 pretrained velocity만 사용한다.

작은 변화라면 `d(delta z)/dt ≈ (partial v/partial z)delta z+(partial v/partial c)delta c`로 경로 차이를 설명할 수 있다. 흰 배경 대체는 큰 변화일 수 있어 이 선형화로 실제 효과 크기나 방향을 예측하지 않는다. Jacobian 실험도 이번 범위가 아니다.

## 실제 조건의 tensor 경로

17frame×288×512 RGB는 `(1,3,17,288,512)`다. VAE 시간압축4·공간압축8로 video latent는 `(1,16,5,36,64)`다. reference1장은 별도 latent slice로 앞에 붙어6이 된다. 이는 물리 영상에 정지 참조 프레임을 추가한다는 뜻이 아니다. 마지막 decode 전에 reference slice를 제거한다.

VACE는 inactive16channel + reactive16channel + mask64channel =96channel context를 사용한다. reference 부분은 `[ref_latent,zeros]`와zero mask로 만든다. [공식 VACE unit](https://github.com/modelscope/DiffSynth-Studio/blob/f39d731a3e318d25b725eb3389cfddb184619842/diffsynth/pipelines/wan_video.py#L674). mask white는 reactive이고 미지정도 all-one이다. 이 M은 R-bg를 만들 때 쓴 alpha와 다른 tensor다.

patch(1,2,2) 뒤 6×18×32=3456tokens, hidden1536이다. 이 전체 sequence에서 시간·공간 문맥이 함께 작용한다. 참조 배경은 VAE context에 들어오며 VACE hints가 DiT에 더해진다. [VACE model](https://github.com/modelscope/DiffSynth-Studio/blob/f39d731a3e318d25b725eb3389cfddb184619842/diffsynth/models/wan_video_vace.py#L27), [hint 주입](https://github.com/modelscope/DiffSynth-Studio/blob/f39d731a3e318d25b725eb3389cfddb184619842/diffsynth/pipelines/wan_video.py#L1714).

CFG의 negative branch에도 동일 S/R/M이 남는다. `v_cfg=v_neg+5*(v_pos-v_neg)`는 text 차이를 증폭하는 결합이고, VACE scale1은 각 block hint에 곱하는 값이다. 둘을 '참조 강도' 하나로 설명하면 틀린다. [CFG 코드](https://github.com/modelscope/DiffSynth-Studio/blob/f39d731a3e318d25b725eb3389cfddb184619842/diffsynth/pipelines/wan_video.py#L339).

## 무엇을 인과적으로 말할 수 있는가

같은 seed의 paired 차이를 `Delta_s=q(Y_bg,s)-q(Y_R,s)`라 정의할 수 있다. q가 수동 순서척도이면 숫자 차이를 정확한 물리량처럼 읽지 않는다. 두 seed는 방향 반복성을 탐색하는 정도다. 배경 대체는 대비와 입력 분포까지 바꾸므로 모델 내부의 순수 '배경 뉴런' 효과를 분리했다고 할 수 없다.

침대가 줄어도 직립 동작이 생기지 않으면 배경 개입의 부분 효과다. P는 source RGB를 참조하지만 text는 검은 Lab를 요구하므로 순수한 동일 개체 reconstruction positive control이 아니다. P 실패만으로 구조 경로가 죽었다고 결론내릴 수 없다. 정적 자세 붕괴와 실제 속도 시간 품질도 구별하며 재생을 직접 보지 않으면 시간 품질은 UNVERIFIED다.

## 이번 관측으로 식을 읽기

[실제 결과](../experiments/B-002-reference-background/RESULTS.md)에서 새 run의 text hash는 모두 같고 같은 seed의 noise hash도 같았다. R-bg의 VACE context hash는 R와 달라졌다. 따라서 고정 theta에서 c의 reference 성분을 바꾸어 생성 경로가 달라졌다는 실측 연결이 있다. 결과의 두 seed 모두 침대/커튼/창 배치 재현이 줄고 착석은 남았다. 이는 q를 '참조 침실 배치 재현 유무'와 '직립 여부'로 나누어 읽을 이유다. 임의의 숫자 점수를 더해 통계적 개선량을 만들지 않았다.

reference가 바뀌는 P에서 직립했어도 그 참조 자체가 직립 자세를 갖는다. S(Canny)의 독립 효과와 R의 자세 영향은 아직 분리되지 않았다. P의 text도 참조 개체와 충돌한다. 따라서 다음에는 R-bg를 유지하고 S만 실제/무정보로 바꾸는 한 비교를 제안한다. 질문의 답은 추가 학습 성공이 아니라 조건이 forward와 출력에 어떻게 연결되는지에 관한 것이다. 시간 품질은 실제 연속 재생을 관찰하지 못해 UNVERIFIED다.
