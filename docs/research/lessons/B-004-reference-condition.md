# B-004 — 참조의 내용을 바꾸면 조건부 벡터장은 어떻게 달라지는가

[사전 계획](../experiments/B-004-reference-neutral/PLAN.md)의 한 요인 비교를 설명한다. B-004는 신규 추론 2/2 완료·실패0, 호환성을 확인한 B-003 C-real 두 결과 재사용으로 비교를 마쳤다. 학습은 없다. 정적 관측과 실제 연속 재생의 검증 범위를 구분한다. 질문은 [별도 파일](../experiments/B-004-reference-neutral/QUESTIONS_KO.md), 해설은 [다른 파일](../experiments/B-004-reference-neutral/ANSWERS_KO.md)에 있다.

## 1. 직관: 자세 지시와 외형 참조는 독립적인 손잡이가 아니다

Canny는 원본의 윤곽·배치 정보를, 사진은 외형뿐 아니라 착석 자세·조명·배경 정보도 제공한다. 모델이 이를 완벽하게 분리한다는 보장은 없다. B-003에서는 같은 R-bg를 유지한 두 seed 모두 C-real이 착석, C-null이 사족이었고 원본 직립 춤은 0/4였다. 구조 입력이 영향을 준다는 사실과 올바른 동작 전달은 다르다.

B-004는 C-real을 고정하고 R-bg의 모든 픽셀을 회색으로 바꾼다. 따라서 참조의 자세만 제거한 실험이 아니다. 개체·털·체형·자세 정보가 함께 사라진다. 가중치나 구조 경로를 고치는 실험도 아니다.

## 2. 수식: 조건부 기대값은 왜 velocity 학습의 목표가 되는가

교육용 설명에서 깨끗한 영상 latent를 Z, 독립 표준정규 noise를 ε, noise time을 σ∈[0,1]이라 하자. 조건 C=(C_struct,C_ref,C_text,M)는 구조·참조·텍스트·마스크다. 고정 Wan scheduler의 규약은

`Z_σ=(1−σ)Z+σε`, `U=ε−Z`, `L=E[||vθ(Z_σ,σ,C)−U||²]`다.

이는 B-004가 새로 학습한다는 뜻이 아니다. pretrained velocity model의 역할을 설명하는 식이다. 실제 학습의 시간별 weighting이나 데이터 분포는 이 단순화와 별도로 확인해야 한다.

Q=(Z_σ,σ,C), m(Q)=E[U|Q]라 두고, 임의의 예측 a(Q)에 대해 제곱을 전개한다.

`E[||U−a||²|Q] = E[||U−m||²|Q] + ||m−a||²`.

교차항은 `E[U−m|Q]=0`이므로 사라진다. 따라서 충분한 함수 공간과 유한 2차 모멘트 아래 MSE 최적해는 m이다. 개별 sample의 U가 서로 달라도 같은 입력 근방에서는 조건부 평균 방향을 학습할 수 있다. 양의 시간별 가중치가 Q로 결정된다면 이 점별 최적해는 같지만, 실제 유한 network·최적화·조건 분포가 이 이상적 해와 같다는 보장은 없다.

추론 시 정답 Z는 없다. 현재 latent와 조건을 넣어 학습된 방향을 계산하고 `z_next=z+(σ_next−σ)vθ(z,σ,C)`로 적분한다. σ가 감소하므로 step 부호는 음수다. σ는 17개 영상 프레임의 물리적 시간이 아니다. 근거: [scheduler step/add_noise/target](https://github.com/modelscope/DiffSynth-Studio/blob/f39d731a3e318d25b725eb3389cfddb184619842/diffsynth/diffusion/flow_match.py#L436).

## 3. 회색 128은 normalized zero도 latent zero도 아니다

이상적인 실수 정규화는 `p(x)=2x/255−1`이므로 RGB128은 `1/255≈0.00392157`이다. 실제 upstream은 먼저 BF16으로 변환하고 곱셈·덧셈을 한다. Spark의 기존 PyTorch 2.14.0+cu130 환경에서 실제 `BasePipeline.preprocess_video`를 CPU로 실행한 값은 **0.0078125**였다. 실제 회색 파일을 RGB decode/pad한 `(288,512,3)` 값은 모두128이며, inference가 저장한 reference RGB와 byte 단위로 같았다. 정규화 결과는 BF16 `(1,3,1,288,512)`, min=max=0.0078125였다. 곱셈 중간값의 BF16 반올림 때문이다. `gray_preprocessing.json`에 입력·pad·tensor hash를 남겼다. CUDA를 숨기고 가중치 없이 CPU 전처리만 실행했으며, GPU 전달 tensor나 VAE latent를 새로 측정한 것은 아니다.

[preprocess_image](https://github.com/modelscope/DiffSynth-Studio/blob/f39d731a3e318d25b725eb3389cfddb184619842/diffsynth/diffusion/base_pipeline.py#L118)의 실제 dtype/연산 순서를 보존해야 한다. 정규화가 0에 가깝더라도 encoder E는 bias·비선형·latent 정규화를 포함하므로 `E(gray)=0`은 성립하지 않는다. [VAE encode](https://github.com/modelscope/DiffSynth-Studio/blob/f39d731a3e318d25b725eb3389cfddb184619842/diffsynth/models/wan_video_vae.py#L984)는 정규화된 mu를 반환하며 무작위 posterior sample을 뽑지 않는다.

균일 회색은 유용한 고정 대조 입력이지만 학습 분포에서 자연스러운 reference인지는 미확인이다. 따라서 '내용 중립'이라는 명칭이 모델 내부 효과까지 중립임을 보증하지 않는다.

## 4. 실제 경로와 tensor: reference 한 장을 계속 넣는다

`reference RGB → pad/정규화 → VAE encode → reference prefix → VACE context → hint → DiT`가 실제 경로다. 별도의 이번 학습용 identity encoder를 추가하지 않는다.

|항목|512×288, 17프레임, reference 1장|증거 수준|
|---|---|---|
|정규화 reference|`(1,3,1,288,512)`|B-004 Spark CPU 실제 전처리 관측; GPU hook 아님|
|reference latent|`(1,16,1,36,64)`|코드 유도|
|video inactive/reactive 각각|`(1,16,5,36,64)`|B-003/B-004 실제 context slice 관측|
|reference 포함 noise|`(1,16,6,36,64)`|B-003/B-004 실제 관측|
|전체 VACE context|`(1,96,6,36,64)`|B-003/B-004 실제 관측|
|reference prefix 전체|`(1,96,1,36,64)`|B-003/B-004 실제 관측; prefix hash 변경 확인|
|positive/negative text 각각|`(1,512,4096)`|B-003/B-004 실제 관측; paired hash 동일|

[WanVideoUnit_VACE](https://github.com/modelscope/DiffSynth-Studio/blob/f39d731a3e318d25b725eb3389cfddb184619842/diffsynth/pipelines/wan_video.py#L674)는 video의 inactive/reactive 16+16 channel과 mask64 channel을 합친다. reference prefix는 `[E(R),zeros16,zeros64]`이다. 이번에는 이 prefix의 앞16 channel 내용만 달라질 것으로 예상한다. 구조 inactive/reactive와 mask는 같아야 한다. reference를 제거하면 prefix 길이와 [NoiseInitializer](https://github.com/modelscope/DiffSynth-Studio/blob/f39d731a3e318d25b725eb3389cfddb184619842/diffsynth/pipelines/wan_video.py#L395)의 noise layout까지 달라질 수 있으므로 이번 대조와 다르다.

`vace_scale=0`도 reference만 제거하는 조작이 아니다. 구조를 포함한 VACE hint 전체의 기여를 바꾼다. 이번에는 scale1을 유지한다. [hint 합산](https://github.com/modelscope/DiffSynth-Studio/blob/f39d731a3e318d25b725eb3389cfddb184619842/diffsynth/pipelines/wan_video.py#L1760).

## 5. 같은 noise의 paired comparison과 식별 한계

출력을 `Y_s(R)=Gθ(ε_s;S,R,T,M,λ)`라 쓰자. s는 seed, S는 고정 C-real, λ는 scheduler·dtype·크기 등 설정이다. 같은 s의 `q(Y_s(gray))−q(Y_s(R-bg))`는 초기 noise 차이를 줄인 비교다. q는 수동 자세 범주·발 위치 등이며 통계적 유의성을 주는 점수로 바꾸지 않는다.

확률적 표현으로 `pθ(video | structure, reference, text, M, λ)`는 ε~N(0,I)를 고정 sampler/decoder Gθ에 통과시킨 출력의 분포다. 즉 집합 A에 대해 `Pθ(Y∈A|C)=Pε(Gθ(ε;C)∈A)`인 noise의 pushforward다. 이는 데이터의 실제 조건부 분포 `pdata(video|C)`와 동일하다고 보장되지 않는 학습된 근사이며, 두 고정 seed의 출력만으로 전체 분포를 추정할 수 없다. 회색처럼 학습 분포와 다른 조건에서는 이 차이가 특히 중요하다.

seed 숫자만 같아서는 충분하지 않다. 모델·정밀도·코드·reference 수·실제 초기 noise hash, text와 구조 latent hash를 함께 확인해야 한다. GPU kernel의 비결정성이나 환경 차이가 남을 수 있어 seed가 같다는 이유로 byte 단위 결정론을 선언하지 않는다. 기존 결과 재사용의 호환성이 깨지면 승인되지 않은 추가 baseline 생성으로 메우지 않는다.

관측 가능한 것은 **이번 조건에서 참조 RGB 내용 교체의 총 효과**다. posture, identity, texture 각각의 독립 효과나 전체 모델에서 reference 영향 크기는 식별하지 못한다. 두 seed와 한 장면의 탐색 결과다.

## 6. 텍스트와 참조의 충돌, 직립과 개체 수용

고정 prompt는 black Labrador와 'reference photo'의 identity를 요구한다. 회색 reference에는 실제 개체가 없다. 모델이 검은 개를 만들어도 text/prior만으로 그럴 수 있으며 실제 Lab의 얼굴·귀·체형을 유지했다는 증거가 아니다.

[CFG 경로](https://github.com/modelscope/DiffSynth-Studio/blob/f39d731a3e318d25b725eb3389cfddb184619842/diffsynth/pipelines/wan_video.py#L339)의 두 text branch는 같은 shared VACE context를 사용한다. `v_cfg=v_neg+5(v_pos−v_neg)`는 사진 정보가 사라진 상황에서도 텍스트 영향을 유지한다. 이번에는 prompt까지 바꾸면 두 번째 개입이 되므로 유지하고 충돌을 해석에 남긴다.

회색에서 직립이 나타나면 구조의 자세 전달 가능성에 관한 제한적 증거다. 실제 개체 전이 성공은 아니다. 사족으로 바뀐 것을 뒷발 직립으로 세지 않는다. 둘 다 착석해도 reference 영향이 0이라는 결론은 나오지 않는다.

## 7. 실제 관측과 연구 결론의 경계

신규 R-gray 두 run 모두 완료했고 실패는0이었다. 기존 R-bg 두 결과를 재사용했다. 같은 seed에서 noise/text/inactive/reactive/mask hash는 같고 reference prefix와 전체 VACE context hash는 달랐다. 즉 이번 변경은 실제 조건 tensor에 반영됐으며 구조 조건이 우연히 바뀐 비교는 아니었다. reference latent 자체의 모든 의미가 이 해시만으로 해석되는 것은 아니다.

실행 담당자는 source와 네 결과의 대표 시트, 각 run 전체17프레임 시트, gray23의 f16 원본 이미지를 정적으로 확인했다. 아래는 그 관측 기록이며 이 문서 작성자가 별도의 연속 재생 검수를 했다는 뜻이 아니다.

|조건|정적 자세 관측|개체·형태·장면의 한계|
|---|---|---|
|R-bg / seed20261022|전체 시트에서 착석|B-003의 실제 Lab 동작 전이 미수용을 유지|
|R-bg / seed20261023|전체 시트에서 착석|B-003의 실제 Lab 동작 전이 미수용을 유지|
|R-gray / seed20261022|전체 시트에서 착석|둥근 흰 눈·열린 입이 만화적으로 보임. 털/표면 세부 감소, 밝게 날아간 방. 사진 같은 Lab 외형 미수용|
|R-gray / seed20261023|17프레임에서 뒷발 직립 실루엣, 앞발은 가슴 가까이 유지|원본의 정면과 달리 옆을 보는 머리. 실제 Lab보다 가늘고 어두움. 꼬리·발 위치 변화, f16의 발은 화면 아래로 잘림. 얼굴 개체 일치 확인 불가|

R-gray의 직립 관측은 **1/2**, R-bg는0/2였다. 이것은 수동 자세 범주 관측이며 원본 안무·지지발의 정확한3D상태·실제 Lab identity 성공이 아니다. gray23의 직립은 참조 내용 교체 후 가능한 출력이 달라졌다는 제한적 근거다. 이번 실험은 C-real을 고정했으므로 직립의 원인이 Canny라고 독립적으로 증명하지 못한다. 텍스트·모델 prior·참조와 구조의 상호작용은 분리되지 않았다. gray22의 계속된 착석도 참조 영향이 없다는 증거는 아니다.

17프레임@24fps는 container 길이17/24초, 첫~마지막 샘플 간격16/24초다. 실제 연속 재생을 보지 못했으므로 시간 품질은 **UNVERIFIED**다. 정적 시트에서 위치 변화가 보였다는 사실을 자연스러운 안무나 시간 일관성 통과로 바꾸지 않는다. 전체제작·IG·윙크·발차기·Kling 수용은 NOT_RUN이다. 다음 실험의 제안과 실행 승인은 [결과 기록](../experiments/B-004-reference-neutral/RESULTS.md)에서 별도로 관리하며 이번 비교로 자동 확장하지 않는다.
