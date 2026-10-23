# B-015 — guidance와 driving의 네 셀을 어떻게 해석하는가

상태: **문서·CPU 검토 도구 준비 / 신규 출력 미관측**. [PLAN](../experiments/B-015-alg-driving-control/PLAN.md)의 목적은 이미 실패한 ALG_MOV의 설정을 튜닝하는 것이 아니라, ALG_STILL 한 셀로 대조군을 완성하는 것이다. B-014의 전신 FAIL·후반 얼굴 손상·개체 UNCERTAIN은 보존한다. 이번 문서는 실제로 얻지 않은 tensor·영상·정량 개선을 주장하지 않는다.

## 1. 직관: 변화가 생겼다는 것과 원본 동작을 따랐다는 것은 다르다

MOV는 시간에 따라 변하는 RGB driving과 mask, STILL은 첫 프레임을 반복한 RGB/mask를 인코딩한 조건이다. STILL은 생성 모델 자체를 끄거나 영상 파일의 첫 프레임을 복제한 STATIC COPY가 아니다. reference·text·모델 prior만으로도 영상 변화가 생길 수 있다.

| guidance | MOV | STILL |
|---|---|---|
| CFG | B-013 기존 결과 | B-013 기존 결과 |
| ALG | B-014 기존 결과 | 이번 신규1회 대상 |

모든 셀은 같은 Lab reference·text·seed·해상도·물리 시간축을 사용한다. MOV/STILL은 RGB와 mask를 함께 바꾸므로 RGB만의 인과 효과를 따로 추정하지 않는다. 17프레임은 한 영상의 상관된 시점이지 독립17회 실험이 아니다.

## 2. 같은 z에서만 성립하는 차이 식

현재 noisy latent를 z, noise 수준을 σ, 원본 reference를 R, 공간 low-pass를 L(R), 고정 driving을 D라 하자. mask·CLIP·history 등은 표기에서 생략하지만 실제로 유지된다. `u`는 negative text, `c`는 positive text 예측이다.

\[
u_R=v_\theta(z,\sigma;R,c_-,D),\quad c_R=v_\theta(z,\sigma;R,c_+,D),
\quad u_L=v_\theta(z,\sigma;L(R),c_-,D),\quad c_L=v_\theta(z,\sigma;L(R),c_+,D).
\]

\[
v_{CFG}=u_R+w(c_R-u_R),\qquad v_{ALG}=u_R+w(c_L-u_L),
\]
\[
v_{ALG}-v_{CFG}=w\big[(c_L-u_L)-(c_R-u_R)\big],\quad w=5.
\]

이는 **z·σ·D가 같은 네 예측**에 대한 항등식이다. [ALG Eq.(2)](https://arxiv.org/html/2506.08456v2#S3.E2)와 [공식 Wan 조합](https://github.com/choi403/ALG/blob/3657bfd0d408631db2443b491498c44e1cb2e5c6/pipeline_wan_image2video_lowpass.py#L919-L924)에 근거한다. 이 식을 이번 실제 두 영상 사이에서 측정했다고 주장하지 않는다.

실제 실행은 첫 개입 이후 `z_ALG≠z_CFG`가 된다. 비선형 속도장과 UniPC의 이력도 다르므로 서로 다른 실행의 branch 숫자를 빼면 위 동일-z 차이가 아니다. 후반 원래 reference로 돌아가는 것도 baseline trajectory 복귀가 아니다. 이번에는 같은-z counterfactual을 위한 추가 model forward를 허용하지 않는다.

## 3. norm으로 방향이나 상쇄를 추정할 수 없는 이유

B-014 [alg_runtime.py](../experiments/B-014-alg-scail-pilot/code/alg_runtime.py)는 실제 호출의 prediction norm을 기록한다. 활성 구간에는 c_R를 별도로 계산하지 않고, 전체 예측 벡터나 두 벡터의 내적도 보존하지 않는다.

\[
\|a-b\|^2=\|a\|^2+\|b\|^2-2\langle a,b\rangle,\qquad
\cos(a,b)=\frac{\langle a,b\rangle}{\|a\|\|b\|}.
\]

norm 두 개만으로 내적을 알 수 없다. 예를 들어 `(1,0)`과 `(1,0)`, `(1,0)`과 `(-1,0)`은 각각 norm이 같지만 차이와 방향은 반대다. “positive/negative가 함께 비슷하게 변하면 차분이 작아질 수 있다”는 대수적 가능성은 설명할 수 있으나, 이번 기록만으로 실제 상쇄량·cosine·개체 loss 기여를 계산하면 증거를 넘어선다.

## 4. 무엇이 여전히 reference를 전달하는가

SCAIL의 [positive/negative kwargs](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/scail.py#L480-L506)는 시각 조건을 공유한다. negative는 visual-unconditional이 아니다. 초기 ALG에서도 원래 u_R가 남고, CLIP·reference mask·큰 저주파 실루엣이 유지된다. 따라서 이번 개입은 참조 전체 제거도 자세만 제거하는 연산도 아니다.

부모에서 확인된 reference는 `[16,1,112,64]` FP32다. [필터 구현](../experiments/B-014-alg-scail-pilot/code/alg.py)은 시간/채널과 공간을 구분해112×64→45×26→112×64 bilinear AA를 적용한다. 색상 mask `[28,6,112,64]`, CLIP `[1,257,1280]`, text `[108,4096]`는 바꾸지 않는다. RGB driving `[16,5,56,32]`와 mask `[28,5,56,32]`만 MOV/STILL 두 branch에서 달라야 한다. 이 표기는 부모 cache 계약이며 B-015의 실제 비교 receipt가 나와야 새 검증 완료라고 쓴다.

같은 reference라면 filtered 값은 같아야 하지만 sidecar의 parent cache는 다르다. MOV parent SHA를 가진 sidecar를 STILL에 그대로 붙이지 않는다. 값의 동일성과 provenance의 동일성은 다른 조건이다. 원본 cache는 읽기 전용으로 두고 STILL parent에 연결한 새 sidecar를 만든다.

## 5. 시간·계산량과 해석 경계

고정 ratio0.4·step interval[0,.20]에서 index `i/39` 기준 초기0..7은3회, 후반8..39는2회 예측한다. `8×3+32×2=88`이며 scheduler update는40회다. 두 CFG 셀은80forward, ALG 셀은88forward이므로 같은 계산량 대조가 아니다. 공식 [schedule](https://github.com/choi403/ALG/blob/3657bfd0d408631db2443b491498c44e1cb2e5c6/lp_utils.py#L81-L98)을 유지하며 새 강도·구간은 검색하지 않는다.

noise 수준 σ와 물리 영상 시간 `k/24`는 다르다. 초기8sampling step은 영상의 초기8프레임이 아니다. 출력은17장·24fps, 첫/끝 sample 간격16/24초, 파일 길이17/24초다. 추가 보간·복제·warp로 모션이나 실패를 감추지 않는다.

q가 사전에 의미 있게 측정된 경우에만 `I=[q(ALG,MOV)-q(ALG,STILL)]-[q(CFG,MOV)-q(CFG,STILL)]`를 계산할 수 있다. 이번에는 고정밀 q가 없으면 전신·방향/순서·얼굴·개체·접촉의 정성 표를 쓴다. 범주에 임의 점수를 붙여 개선율이나 유의성을 만들지 않는다.

## 6. 실제 결과 자리와 종료 원칙

신규 ALG_STILL은 아직 관측하지 않았다. 실제 receipt와 전체17장 검토 후 이 절을 갱신한다. 가령 두 MOV만 손상되고 두 STILL은 상대적으로 안정적이면 이 입력의 동적 전이가 어려움을 보였다는 단일 사례 근거다. 그러나 reference 단일 원인이나 특정 신경망 경로를 증명하지 않는다. ALG_STILL이 안정적이어도 B-014의 목표 품질 실패를 성공으로 바꾸지 않는다.

이 네 셀 완료 후 현재 ratio0.4/초기20% pilot은 종료한다. 새 seed·강도·학습·모델을 자동 실행하지 않는다. 실제 연속 재생을 관찰하지 못하면 시간 품질은 UNVERIFIED이며 UI 기능 성공은 지각 품질의 증거가 아니다.

## 이해 확인 질문

1. norm이 비슷한 두 예측에서 guidance 차분이 작다고 결론낼 수 있는가?
2. filtered tensor 값이 MOV/STILL에서 같아도 sidecar를 그대로 복사하면 안 되는 이유는 무엇인가?
3. ALG_STILL이 선명하게 앉아 있으면 ALG의 동작 전이가 성공한 것인가?

## 별도 해설

1. 아니다. 내적/방향이 없으므로 같은 norm에서 차이는0부터 큰 값까지 가능하다. 실제 두 실행의 z도 다르다.
2. tensor 값과 parent cache 계보는 별개다. STILL cache에 결합되는 계약을 검증해야 하고 MOV용 parent SHA 검사를 삭제하면 안 된다.
3. 아니다. STILL은 동작 목표 대조군이다. MOV에서 원본의 자세·방향·순서와 실제 개체를 유지했는지 별도로 판단한다.
