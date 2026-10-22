# B-005 — 참조와 구조 조건의 상호작용

[사전 계획](../experiments/B-005-factorial/PLAN.md)의 마지막 작은 2×2 비교다. 신규 허용은 R-gray+C-null의 두 seed뿐이며, 기존 6개 결과는 호환성 검증 뒤 재사용한다. 학습은 없다. 신규2회 완료·실패0·기존6개 재사용으로 전체8셀 비교를 마쳤다. [질문](../experiments/B-005-factorial/QUESTIONS_KO.md)과 [해설](../experiments/B-005-factorial/ANSWERS_KO.md)은 분리했다.

## 1. 직관: 한 조건의 효과가 다른 조건에 따라 달라지는가

B-003에서 R-bg를 고정하면 real Canny는 착석, 검정 입력은 사족이었다. B-004에서 real Canny를 고정하면 회색 참조의 두 seed 중 하나에 직립 실루엣이 나타났으나 실제 Lab 외형·원본 안무는 수용되지 않았다. 이제 남은 회색+검정 조합을 넣어 두 입력의 조합 효과를 본다.

|참조/구조|C-real|C-null|
|---|---|---|
|R-bg|B-003 두 결과 재사용|B-003 두 결과 재사용|
|R-gray|B-004 두 결과 재사용|이번 신규 두 결과|

각 칸에는 같은 두 seed가 있다. 8개 영상은 서로 독립적인8개 장면이 아니며, 신규8회 실행도 아니다.

## 2. 수식과 조건부 생성 분포

`Y_{s,r,c}=Gθ(ε_s;R_r,C_c,T,M,λ)`에서 θ는 고정 가중치, ε_s는 seed s의 초기 noise, R은 참조, C는 구조 입력, T는 positive/negative text, M은 mask, λ는 scheduler·크기·정밀도 등 설정이다. `pθ(video|R,C,T,M,λ)`는 ε~N(0,I)를 sampler와 decoder Gθ에 통과시킨 출력 분포다. 실제 데이터의 조건부 분포와 동일하다고 보장되지 않는 학습된 근사다.

Wan의 noise 시간 σ는 영상 frame index와 다르다. `zσ=(1−σ)zclean+σε`, velocity target은 `ε−zclean`이다. 추론에서는 `znext=z+(σnext−σ)vθ(z,σ,conditions)`를 반복한다. σ가 내려가므로 step의 부호는 음수다. 조건이 달라지면 같은 초기 z라도 velocity와 이후 경로가 달라진다. 이번에는 loss나 가중치를 갱신하지 않는다. [실제 scheduler](https://github.com/modelscope/DiffSynth-Studio/blob/f39d731a3e318d25b725eb3389cfddb184619842/diffsynth/diffusion/flow_match.py#L436).

## 3. Factorial contrast와 interaction의 의미

q가 의미 있는 수치 관측치일 때만 다음을 계산할 수 있다.

`ΔC(r,s)=q(Ys,r,real)−q(Ys,r,null)`

`Is=ΔC(gray,s)−ΔC(bg,s)`.

이는 참조가 바뀔 때 구조 효과가 얼마나 달라지는지를 나타내는 difference-of-differences다. 여기에는 시간상의 전후 집단이 없으므로 관찰연구의 정책평가에서 쓰는 parallel-trends 가정을 적용하는 설계가 아니다. 대신 비교 셀 간 모델·실행 설정·noise·조건 전처리의 호환성과 의도한 두 입력 이외 변화가 없다는 검사가 필요하다.

착석/사족/직립은 순서 없는 범주다. 착석=0,사족=1,직립=2로 임의 코딩하면 숫자 간격과 순서에 근거가 없어 I의 크기가 자의적이 된다. 따라서 이번에는 범주표와 seed별 전환을 우선 보고한다. 사전에 명시한 binary 직립 여부를 사용할 수는 있지만 두 seed의 작은 차이를 통계적 유의성이나 일반적 효과 크기로 주장하지 않는다. 외형·형태·동작을 임의로 더한 품질 점수도 만들지 않는다.

Is≠0인 수치 관측이 있더라도 모델 내부에 독립된 '상호작용 모듈'이 있다는 증거는 아니다. 비선형 생성 경로 전체의 결과다. 참조 대체는 자세·개체·털 정보를 함께 바꾸므로 그 각각의 독립 역할은 식별하지 못한다.

## 4. Paired noise와 실제 tensor 통제

같은 seed의 네 셀은 실제 초기 noise hash가 같아야 한다. seed 숫자만 같아도 shape·reference 수·코드가 다르면 noise layout이 달라질 수 있다. [NoiseInitializer](https://github.com/modelscope/DiffSynth-Studio/blob/f39d731a3e318d25b725eb3389cfddb184619842/diffsynth/pipelines/wan_video.py#L395)는 reference 수를 시간 길이에 반영한다. 같은 seed는 불필요한 noise 차이를 줄이지만 GPU 비결정성까지 없앤다는 보장은 아니다.

고정512×288·17frames·reference1장에서는 noise `(1,16,6,36,64)`, text 각각 `(1,512,4096)`, VACE context `(1,96,6,36,64)`다. B-003/B-004와 신규 B-005에서 실제 관측한 shape다.

[WanVideoUnit_VACE](https://github.com/modelscope/DiffSynth-Studio/blob/f39d731a3e318d25b725eb3389cfddb184619842/diffsynth/pipelines/wan_video.py#L674)의 context는 inactive16+reactive16+mask64 channel이다. reference prefix 전체는 `(1,96,1,36,64)`이고 `[E(R),zeros16,zeros64]`다. 나머지 video의 inactive/reactive는 각각 `(1,16,5,36,64)`다.

검사 기대는 다음과 같다. 같은 R이면 prefix가 같고, 같은 C이면 reactive가 같다. full-white mask 때문에 inactive는 정규화 공간0을 encode하므로 네 셀 모두 같다. mask·text·동일 seed noise도 같아야 한다. R과 C가 둘 다 바뀌는 대각선 비교에서는 prefix와 reactive가 모두 바뀌므로 단일 입력 효과로 읽지 않는다. 실제 hash가 기대와 다르면 원인을 조사하고 '통제된 비교'라고 먼저 결론내리지 않는다.

## 5. 회색·검정은 branch-off가 아니다

[실제 정규화](https://github.com/modelscope/DiffSynth-Studio/blob/f39d731a3e318d25b725eb3389cfddb184619842/diffsynth/diffusion/base_pipeline.py#L118)는 dtype 변환 뒤 `x*(2/255)−1`이다. RGB0은−1이다. RGB128은 이상적인 실수 연산에서1/255이고, B-004의 Spark CPU BF16 실제 전처리에서는0.0078125였다. GPU tensor의 새 실측이라고 옮겨 적지 않는다.

E는 VAE encoder다. bias·비선형·latent normalization 때문에 `E(gray)=0` 또는 `E(black)=0`을 가정할 수 없다. 회색 reference1장은 prefix와 noise 길이를 유지한다. 검정 video도 reactive VAE branch에 들어간다. `reference=None`, `vace_video=None`, context제거, `vace_scale=0`과 각각 다른 개입이다. 특히 vace_scale0은 reference뿐 아니라 구조를 포함한 hint 전체 기여를 바꾼다.

회색+검정 조합은 자연스러운 학습 조건 분포 밖일 수 있다. 따라서 이를 '순수 무조건 prior'라고 부르지 않는다. 텍스트·mask·reference/구조 인코딩 경로가 모두 남는다.

## 6. Text prior, CFG, 영향과 유용성

고정 prompt는 검은 Labrador와 reference photo의 identity를 요구한다. 회색 사진에는 그 개체 정보가 없으므로 이 지시는 충돌할 수 있다. 검은 개가 나왔다는 것만으로 사진 개체를 유지했다고 볼 수 없다.

[CFG 두 branch](https://github.com/modelscope/DiffSynth-Studio/blob/f39d731a3e318d25b725eb3389cfddb184619842/diffsynth/pipelines/wan_video.py#L339)는 같은 VACE context를 사용한다. `vCFG=vneg+5(vpos−vneg)`이며 [VACE hint](https://github.com/modelscope/DiffSynth-Studio/blob/f39d731a3e318d25b725eb3389cfddb184619842/diffsynth/pipelines/wan_video.py#L1760)는 scale1로 DiT에 더해진다. 회색+검정에서도 이 경로는 실행된다.

출력 자세가 달라지는 것은 입력 민감도의 근거다. 유용한 motion transfer에는 원본의 동작 단계·발 위치·시점과 실제 개체가 함께 맞는지가 필요하다. 회색에서 직립만 나타나도 안무·identity 성공이 아니다. 거의 정지한 결과가 흔들림 점수에서 유리하더라도 원본의 동작 크기를 잃었다면 성공으로 세지 않는다.

## 7. 실제 8셀 비교와 한계

신규 R-gray+C-null 두 run 모두 완료·실패0이며 기존6개를 재사용했다. 같은 seed의 noise/text/inactive/mask hash는 네 셀에서 같았다. reference prefix는 R에 따라서만, reactive는 C에 따라서만 달라졌고 전체 factorial tensor 검사는 통과했다. 이는 입력 통제의 근거이며 생성 품질 통과는 아니다.

실행 담당자가 전체17프레임 시트와 대표 원본 이미지를 정적으로 검토한 자세 범주는 다음과 같다.

|seed|R-bg+C-real|R-bg+C-null|R-gray+C-real|R-gray+C-null|
|---|---|---|---|---|
|20261022|착석|사족|착석, 만화적인 얼굴|사족|
|20261023|착석|사족|뒷발 직립 실루엣|사족|

새 gray-null22는 넓은 검은 개가 정면에서 측면 쪽으로 몸 방향을 바꾸며 앞다리를 벌렸다. 플라스틱 같은 푸른 광택, 후반 특히 f15~16의 얼굴 흐림이 보였다. gray-null23은 측면의 걷는 듯한 자세, 든 앞발과 꼬리 위치 변화가 있었으나 뒷발 직립은 아니었다. 청록 경계, 넓은 몸통, 화면 아래 발 잘림과 방/나무 바닥이 보였다. 이러한 정적 변화가 자연스러운 보행이나 시간 일관성을 증명하지 않는다.

범주 관측상 seed22에서는 두 참조 모두 구조를 real→null로 바꾸면 착석→사족이었다. seed23에서는 R-bg의 착석→사족과 R-gray의 직립 실루엣→사족이 달랐다. 따라서 **구조 입력 교체에 대한 범주 반응이 참조와 seed에 따라 달랐다**고 기술할 수 있다. 범주를 임의의 숫자로 바꾼 품질 interaction 점수나 통계적 유의성은 보고하지 않는다. 한 seed의 직립 실루엣도 원본 안무·실제 Lab 외형과 함께 맞은 결과가 아니다.

전체8개에서 실제 개체와 원본 안무를 함께 충족했다는 판정은 **NOT_ACCEPTED**다. 입력에 영향이 있다는 사실은 확인했지만 원하는 동작에 유용한 전이라는 결론으로 바꾸지 않는다. 회색+검정도 text/prior와 인코딩된 조건이 남아 있는 인위적 입력이며, 순수한 무조건 생성이 아니다.

17frames@24fps의 파일 길이는17/24초이고 첫~마지막 샘플 간격은16/24초다. 실제 연속 재생을 보지 못했으므로 시간 품질은 **UNVERIFIED**다. 두 seed·한 장면의 제한된 결과이며 서비스·논문·전체15초·두 개체·Kling 수용 근거가 아니다.

다음 방향은 제거 실험을 더 늘리는 대신, 원본의 동물 keypoint 궤적·가시성·발 접촉을 명시하는 움직임 표현의 실현 가능성을 검토하는 것이다. 이것은 후속 제안이며 이번에 실행하지 않았다. 표현을 만들 수 있다는 사실과 모델이 그것을 조건으로 받아 원본 동작을 생성할 수 있다는 사실도 구분해야 한다.
