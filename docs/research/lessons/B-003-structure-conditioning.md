# B-003: 구조 영상을 검게 바꾸는 것은 무엇을 제거하는가

이 문서는 실행 결과를 미리 가정하지 않는 코드·이론 설명이다. 고정 upstream은 `f39d731a3e318d25b725eb3389cfddb184619842`다. [B-002 결과](../experiments/B-002-reference-background/RESULTS.md)에서는 흰 배경 Lab 참조 R-bg에서도 착석 자세가 남았다. B-003은 같은 R-bg를 유지하고 구조 입력만 실제 Canny와 전부 검은 RGB 영상으로 바꾸는 비교다. 새 모델이나 학습 효과를 평가하는 실험이 아니다. [사전 계획](../experiments/B-003-structure-condition/PLAN.md)에 따라 C-real/C-null × seed20261022/20261023의 네 셀을 모두 신규 실행하며 실패 포함 최대4회, 자동 재시도와 학습은0회다. 기존 B-002 결과는 네 셀의 대체물이 아니다.

[이해 질문](../experiments/B-003-structure-condition/QUESTIONS_KO.md)과 [별도 해설](../experiments/B-003-structure-condition/ANSWERS_KO.md)을 분리했다. 결과는 실행 담당자의 실제 장부와 RESULTS에서 연결하며 여기서 생성 성공이나 관측값을 만들어 넣지 않는다.

## 1. 직관: 제거하는 것은 Canny 윤곽 정보다

실제 Canny를 S, 모든 프레임의 모든 RGB 채널이0인 입력을 S_black이라 하자. 후자는 윤곽 변화가 없는 일정한 검은 화면이다. 하지만 모델에는 여전히 영상 tensor, 흰 video mask, R-bg reference, text가 전달된다. 따라서 이것을 'VACE를 끈 실험'이나 '아무 조건도 없는 생성'으로 부르면 틀린다.

입력의 순서는 다음과 같다.

`RGB 구조 영상 → [-1,1] 정규화 → inactive/reactive 분리 → 각각 VAE encode → mask/reference latent 결합 → VACE hints → DiT → scheduler → RGB decode`

근거는 [BasePipeline.preprocess_image/video](https://github.com/modelscope/DiffSynth-Studio/blob/f39d731a3e318d25b725eb3389cfddb184619842/diffsynth/diffusion/base_pipeline.py#L118), [WanVideoUnit_VACE](https://github.com/modelscope/DiffSynth-Studio/blob/f39d731a3e318d25b725eb3389cfddb184619842/diffsynth/pipelines/wan_video.py#L674)다.

## 2. RGB zero, 정규화 zero, latent zero를 구분한다

정규화 함수는 `p(x)=2*x/255-1`이다. RGB0은 p(0)=−1, RGB255는+1이다. 정규화 tensor0은 중간 회색에 해당하며 RGB0과 다르다. 실제 구현은 dtype 변환 뒤 산술을 하므로 일반적인 float32 계산과 세부 rounding이 같다고 전제하지 않는다. 단, 입력 RGB0의−1 대응은 명확하다.

생성 video mask M은 두 조건 모두 white여서 정규화 후1이다. 따라서

- `inactive=p(S)*(1-M)=0`
- `reactive=p(S)*M=p(S)`
- black 조건에서는 `inactive=0`, `reactive=-1`이다.

이때 inactive의0은 이미 정규화된 공간의 값이다. VAE encoder E는 convolution, bias, nonlinear 연산과 latent normalization을 포함하므로 `E(0)=0`이나 `E(-1)=0`이라고 할 수 없다. 두 branch를 encode한 결과를 그대로 보존해야 하며 새 latent를 수동으로0으로 덮어써서는 이 비교가 아니다.

또한 `vace_video=None`이면 upstream은 정규화 RGB 검정이 아니라 **정규화 공간의 zeros tensor**를 만든다. reference나mask가 있으면 VACE context 자체는 계속 존재한다. S_black, video=None, VACE context=None, vace_scale0은 서로 다른 개입이다. 이번에는 첫 번째만 비교한다.

[실제 VAE encode](https://github.com/modelscope/DiffSynth-Studio/blob/f39d731a3e318d25b725eb3389cfddb184619842/diffsynth/models/wan_video_vae.py#L984)는 mu를 반환한다. posterior sampling이 없다는 사실이 E(0)=0이라는 뜻은 아니다.

## 3. 무엇이 고정되고 무엇이 달라져야 하는가

생성기를 `Y_s=G_theta(epsilon_s;S,R_bg,T,M,lambda)`라 쓴다. theta는 pretrained 가중치, epsilon_s는 seed s의 초기 noise, T는 text, M은 video mask, lambda는 scheduler·CFG·VACE scale·크기·dtype 등의 실행 설정이다. 같은 seed의 paired 비교에서 S만 바뀌어야 한다.

R-bg의 reference alpha는 B-002에서 사진 배경을 교체하는 데 사용한 자료다. 그것을 이번 video mask M으로 넣는 것은 추가 변수를 바꾸는 일이다. R-bg 픽셀·resize/pad·장수, 모든 흰 video mask, prompt/negative prompt, seed별 실제 noise, 모델과 실행 경로를 고정해야 한다.

VACE context는 inactive16 + reactive16 + mask64 =96channel이다. reference 시간 slice는 `[E(R_bg), zeros16, zeros64]`, 나머지 video slice는 `[E(inactive),E(reactive),mask64]`다. 같은 처리라면 reference slice, inactive branch, mask는 같고 reactive video branch가 달라지는 것이 예상된다. **예상과 실측은 구분한다.** 실제 hash나 수치 비교가 없으면 '동일 확인'이라고 쓰지 않는다.

## 4. shape와 실제 관측의 연결

|항목|고정 설정에서 코드가 예측하는 shape|증거 수준|
|---|---|---|
|RGB 구조 입력|`(1,3,17,288,512)`|코드 유도|
|video latent|`(1,16,5,36,64)`|코드 유도|
|reference 한 장을 포함한 noise|`(1,16,6,36,64)`|B-002에서 관측; B-003은 별도 확인|
|VACE context|`(1,96,6,36,64)`|B-002에서 관측; B-003은 별도 확인|
|patch embedding|`(1,1536,6,18,32)`|코드 유도 및 B-002 기록|
|flattened tokens|`(1,3456,1536)`|6×18×32 계산|

[NoiseInitializer](https://github.com/modelscope/DiffSynth-Studio/blob/f39d731a3e318d25b725eb3389cfddb184619842/diffsynth/pipelines/wan_video.py#L395)는 reference 장수에 따라 시간 길이를 늘리고 noise slice를 이동한다. reference 장수는 그대로여야 noise layout도 유지된다. [generate_noise](https://github.com/modelscope/DiffSynth-Studio/blob/f39d731a3e318d25b725eb3389cfddb184619842/diffsynth/diffusion/base_pipeline.py#L183)는 전용 CPU Generator를 seed로 초기화한다. seed 문자열 일치뿐 아니라 실제 tensor hash를 비교해야 한다.

물리 영상 시간은 프레임 축이다. 17frames@24fps의 container 길이는17/24초이고 첫~마지막 샘플 시각 차이는16/24초다. diffusion 시간 sigma나20sampling steps와 다른 개념이다.

## 5. 조건 차이가 생성 경로를 바꾸는 방식

Wan은 `z_sigma=(1-sigma)*z_clean+sigma*epsilon`을 사용하고 velocity target은 `epsilon-z_clean`이다. sampling은 sigma를 내리며 `z_next=z+(sigma_next-sigma)*v_theta(z,sigma,c)`를 계산한다. [scheduler](https://github.com/modelscope/DiffSynth-Studio/blob/f39d731a3e318d25b725eb3389cfddb184619842/diffsynth/diffusion/flow_match.py#L436).

구조 입력 변경은 c의 일부를 바꾼다. 초기 z가 같아도 첫 velocity가 달라질 수 있고, 이후에는 달라진 z를 다시 넣으므로 경로 차이가 누적된다. 같은 가중치라는 사실이 같은 출력을 보장하지 않는다. 출력 차이가 있다는 것만으로 구조가 올바르게 사용됐다고 볼 수도 없다.

[CFG sampling](https://github.com/modelscope/DiffSynth-Studio/blob/f39d731a3e318d25b725eb3389cfddb184619842/diffsynth/pipelines/wan_video.py#L339)의 positive/negative text branch는 같은 shared VACE context를 받는다. CFG5는 두 예측의 차이를 결합하고, [vace_scale1](https://github.com/modelscope/DiffSynth-Studio/blob/f39d731a3e318d25b725eb3389cfddb184619842/diffsynth/pipelines/wan_video.py#L1760)은 DiT에 추가하는 hint를 곱한다. black 조건에서도 hint forward는 계속 실행된다.

## 6. 두 seed로 알 수 있는 것과 없는 것

같은 seed에서 `Delta_s=q(Y_black,s)-q(Y_Canny,s)`를 비교한다. q는 직립 여부, 보이는 발 위치, 머리 방향, 프레임 간 동작 등의 관측 항목이다. 수동 순서척도의 차이를 물리적 효과량이나 통계적 유의성으로 포장하지 않는다.

- 두 조건이 다르면: 이 입력 개입에 출력이 반응했다는 근거다. 올바른 안무 전달 여부는 별도다.
- 둘 다 앉으면: R-bg의 착석과 text/모델 prior가 남은 상태에서 직립 실패가 지속됐다는 관측이다. S가 전혀 사용되지 않는다고 즉시 결론내릴 수 없다.
- Canny가 더 직립하면: 이 두 seed와 이 source에서 구조 condition의 유용성에 관한 국소적 근거다. 다른 개체·긴 안무 일반화가 아니다.
- black이 더 좋아 보이면: 구조 정보 제거가 항상 유리하다는 증거가 아니다. 구조 표현의 편향·조건 경쟁·특정 noise가 후보 원인으로 남는다.

black은 유효한 고정 대조 입력이지만 학습 분포와의 거리가 달라질 수 있다. 이 실험은 모델 내부의 순수 motion channel을 분리하지 않는다. 두 seed의 paired 결과는 탐색적이며 서비스·논문·전체 반려동물 품질을 입증하지 않는다. 실제 연속 재생을 보지 못하면 시간 품질은 UNVERIFIED다.

## B-003 실측 연결 자리

작성 시점에는 이 작성자가 B-003 추론을 실행하거나 결과를 관측하지 않았다. 실행 담당자가 실제 run ID, 재사용 여부, noise/text/reference/mask 일치, reactive/context 변화, 두 seed의 정적·시간 관측을 RESULTS와 연결한다. 이 문단의 상태는 실측 자료를 확인한 뒤 갱신하며 예상 shape만으로 성공을 채우지 않는다.
