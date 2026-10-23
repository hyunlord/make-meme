# B-011 — 측정 불확실성과 탐색적 생성 진단

현재 P 조건 생성·비교와 PROBE는 **PASS**, S sampler는 **RUNNING**이다. 출력은 **NOT_AVAILABLE**, D와 출력 품질 검토는 **NOT_RUN**이다. [B-011 계획](../experiments/B-011-exploratory-self-reenactment/PLAN.md)은 화면상 시간 변화(A)와 부위 상대 운동(B)을 분리한다. B가 불확실해도 입력·안전 계약과 실제 source 변화가 확인되면 A의 탐색 생성 한 번을 허용한다. B-010의 DIAGNOSTIC_INSUFFICIENT와 GPU 0회 기록은 그대로다.

## 1. 반경은 표준편차가 아니다

관측 위치를 \(\hat p\in\mathbb R^2\), 미지의 실제 표면점 위치를 \(p\)라 하자. 보수적 반경 \(u\)는 \(\|p-\hat p\|_2\le u\)라는 제한을 가정한 것이다. 이 반경을 반복 측정으로 검증한 확률분포와 혼동하지 않는다. B-006의 2px/4px는 에이전트 시각 주석의 보수적 설정이며 경험적으로 보장된 오차 상한도 아니다.

- 표준편차는 분포의 산포다. 보수적 반경을 곧바로 표준편차로 사용할 수 없다.
- 신뢰구간은 표본 추출·추정 절차의 포함률과 연결된다. 반경 안에 95%가 들어간다는 근거는 없다.
- tracker RMSE는 정답과의 제곱오차 평균의 제곱근이다. 이번에는 tracker와 독립 정답을 비교하지 않았다.
- Type B 표준불확실성도 단순한 임의 반경의 다른 이름이 아니다. 가용 정보와 분포 가정으로 표준불확실성을 평가하는 절차다. [NIST TN1297](https://www.nist.gov/pml/nist-technical-note-1297/nist-tn-1297-4-type-b-evaluation-standard-uncertainty)

같은 에이전트가 두 번 비슷하게 읽어도 반복성만 확인한다. 두 판독이 같은 체계적 편향을 공유할 수 있으므로 인간 독립 ground truth나 정확도 검증이 아니다.

## 2. 좌표 변환과 최악 경우 전파

\(q=Ap+b\)에서 \(A\)는 확대·축 변환, \(b\)는 crop 이동이다. \(\hat q=A\hat p+b\)라면

\[
\|q-\hat q\|_2=\|A(p-\hat p)\|_2\le\|A\|_2u.
\]

대각 확대 \(A=\operatorname{diag}(s_x,s_y)\)에는 \(\|A\|_2=\max(|s_x|,|s_y|)\)다. 고정 crop 이동은 위치를 바꾸지만 이 식의 반경을 늘리지 않는다. B-010의 [실제 관측 전파 코드](../experiments/B-010-animal-self-reenactment/code_review/evaluate_preflight.py)는 \(s_x=1592/512,s_y=896/288\)에 추가 표시 오차 1px를 더했다. 입력 좌표 규약·변환 자체의 편향은 이 단순 반경만으로 검증되지 않는다.

두 시점 변위 \(d=q_t-q_0\)의 관측 오차는 삼각부등식으로 \(u_t+u_0\) 이하다. 따라서 측정된 변위 길이가 이 합보다 작으면 보수적 구간에서 실제 0 변위와 구별되지 않을 수 있다. 이것이 실제 무동작이라는 뜻은 아니다.

\(\sqrt{u_t^2+u_0^2}\)로 바꾸면 반경을 줄이지만 근거가 없다. 분산 전파에서는 \(\operatorname{Var}(X-Y)=\operatorname{Var}(X)+\operatorname{Var}(Y)-2\operatorname{Cov}(X,Y)\)를 쓴다. 반경을 분산으로 바꿀 분포도, 공분산도 측정하지 않았다. 모든 변위가 같은 f0를 공유하므로 서로 독립인 20회 측정도 아니다. [NIST의 분산·공분산 전파 설명](https://www.itl.nist.gov/div898/handbook/mpc/section5/mpc55.htm)

## 3. 큰 canvas가 더 많은 촬영 정보를 뜻하지 않는다

실제 입력은 기존 512×288을 bicubic으로 1592×896에 확대하고 512×896으로 crop한 것이다. 확대 픽셀은 기존 주변 픽셀에서 계산되며 새로 촬영한 독립 표본이 아니다. OpenCV도 기하 변환을 좌표 대응과 비정수 위치의 보간 문제로 설명한다. [공식 변환 문서](https://docs.opencv.org/4.x/da/d54/group__imgproc__transform.html)

확대 표시에서 코를 더 편하게 읽거나 좌표 반올림을 줄일 수는 있다. 흐린 경계·압축·가림의 원래 정보가 복원됐다고 할 수는 없다. 이번 입력은 그대로 두고 원본 좌표계, 처리 canvas, 표시 배율, 읽기 방법을 따로 기록한다.

## 4. 전체 이동과 상대 운동은 다른 측정량이다

표면점 \(p_j(t)\)의 절대 변위 \(d_j(t)=p_j(t)-p_j(0)\)는 물체 전체 이동·카메라·크기 변화와 부위 운동을 함께 담는다. source의 전체 이동을 정확히 재현하는 것은 수준 A의 유효한 관측이다. 그러나 관절 운동의 증거로 대신하지 않는다.

두 점 사이 벡터 \(r_{jk}(t)=p_j(t)-p_k(t)\)는 공통 translation을 제거한다. \(r_{jk}(t)-r_{jk}(0)\)에는 scale·시점·roll 영향이 여전히 남는다. 각도나 비율을 쓰더라도 짧은 기준선과 가려진 점은 불안정하다. 표면 proxy는 골격 joint가 아니며, 이번 문서는 새 지표나 관절 추정기를 추가하지 않는다. 적용할 상대 측정량은 source만 보고 먼저 고정해야 한다.

B-010의 전체 평균은 15.5107px 대 반경합 평균 19.4222px였다. 머리 12항목 평균은 16.3814px/14.4444px, 앞발 8항목은 14.2045px/26.8889px다. 머리 7항목의 반경 초과는 일부 절대 위치 변화의 근거이며, 통계적 유의성·articulation PASS가 아니다. 이 사후 분리는 B-010을 소급 통과시키지 않는다.

## 5. 생성 모델이 reference를 복사하는가, driving을 이용하는가

생성 과정은 \(v_\theta(z_\sigma,\sigma,c)\), \(c=(reference,driving,mask,text)\)에 의존한다. 정적 reference에는 이미 초기 자세가 들어 있다. 직립 출력 한 장만으로 시간적 driving을 사용했다고 판단할 수 없다. source / STATIC COPY / 생성 시퀀스를 같은 시간·canvas에서 비교해야 한다. 단순 flicker나 source와 반대 방향의 zoom도 시간 변화는 있지만 동작 재현은 아니다.

고정 SCAIL [조건 구성](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/scail.py#L436-L510)은 driving RGB를 절반 해상도 VAE 경로에 넣고 reference·mask·text·CLIP 조건을 구성한다. RGB가 semantic mask로 alpha-cut되는 것은 아니다. [모델 입력 결합](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/modules/model_scail2.py#L741-L803)에서 reference+generated patch와 driving patch를 함께 처리한다.

B-011 P의 **실측** noise는 `[16,5,112,64]` FP32, reference는 `[16,1,112,64]` FP32, driving은 `[16,5,56,32]` FP32다. reference mask `[28,6,112,64]`, driving mask `[28,5,56,32]`도 FP32다. positive text는 B-009의 `[44,4096]`에서 `[27,4096]` BF16으로 바뀌었고 negative `[1,4096]` BF16은 동일하다. CLIP은 `[1,257,1280]` FP16이다. 새 P는 121.123초에 완료했고, B-009 Lab cache를 새 이름으로 재사용하지 않았다.

[실제 조건 비교](../experiments/B-011-exploratory-self-reenactment/CONDITION_COMPARISON.json)에서 예정된 7leaf만 변경됐고 9개 control은 모두 bit-exact, 최대 차이 0이었다. 허용 tolerance에 겨우 들어온 결과가 아니다. 변경은 positive text 1, 양 branch reference 2·CLIP 2·reference mask prefix 2다. driving/mask, negative, noise/RNG/schedule은 보존됐다. noise의 실제 SHA256은 `9d26386e01a5dce6b0dc21e3df26aab79b65a4403e11b6c8fc5a71873dd3c950`, 새 cache는 `2af5acb5e3835e1e3f23609dcf83a326980818075aff3c11c36cbd5a095583cb`다. 이는 입력 계약의 증거이며 동작 전이 성공은 아니다.

[실제 sampler](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/scail.py#L375-L426)의 CFG는 \(v_{cfg}=v_u+5(v_c-v_u)\)다. 두 branch에 visual 조건이 공유되므로 \(u\)가 reference/driving 제거 실험은 아니다. UniPC 40step은 CFG 80forward를 계획하지만 완료 횟수는 실제 장부로 판정한다. \(\sigma\)는 noise time이고 영상 frame \(k\)의 물리 시각 \(k/24\)와 다르다. 17장의 파일 길이 17/24초와 첫·끝 프레임 표본 간격 16/24초도 구분한다.

## 6. 현재 근거와 해석 한계

B-011 S sampler는 **RUNNING**이며 출력은 **NOT_AVAILABLE**이다. PROBE는 6.055초에 완료됐고, D와 출력 품질 검토는 **NOT_RUN**이다. 사전 source 관측과 새 P의 7leaf 변경/9leaf 보존 검증은 완료됐으며, sampler·decode·출력 검토와 구분한다. [생성 전 평가 계약](../experiments/B-011-exploratory-self-reenactment/PREREG_EVALUATION.md)은 수준 A를 OBSERVABLE_SCREEN_CHANGE, B를 INCONCLUSIVE로 고정했다. 현재 source 변위 평균 16.5407px와 기존 반경합 19.4222px를 함께 남겼고 통합 gain은 UNDEFINED다. 이전 대비 판독 차이는 머리 평균 2.5607px, 앞발 평균 5.6347px이며 정확도나 새 신뢰구간이 아니다. B-009 대비 reference와 text가 함께 바뀌므로 순수 단일요인 인과 실험이 아니다. 한 seed의 자기 재현 성공도 cross-identity, Lab 체형 전이, 동물 일반화나 접촉 물리를 증명하지 않는다.

생성 후 유리한 점·프레임·시간 lag를 고르거나 출력별 warp로 오차를 줄이지 않는다. 가려지거나 무너진 대응점은 coverage 실패로 남긴다. 작은 정적 오차를 분모로 나누는 개선율은 불안정하므로 필요하면 UNDEFINED다. 실제 속도 연속 재생을 관찰하지 못하면 시간 품질은 **UNVERIFIED**다.

## 이해 확인 질문

1. 두 시점의 위치 반경이 각각 3px일 때 변위 반경을 왜 자동으로 √18px라고 쓰면 안 되는가?
2. 512×288 source를 확대해서 코를 세 번 같은 곳에 표시했다. 무엇을 확인했고 무엇은 확인하지 못했는가?
3. 생성물이 직립하고 프레임마다 조금 달라졌다. 이것만으로 driving 동작 전이가 성공했다고 할 수 있는가?

## 별도 해설

1. 반경은 표준편차가 아니고 독립성·분포도 없다. 보수적 삼각부등식은 6px다. 실제 편향이나 반경 설정의 타당성은 별도 문제다.
2. 해당 표시 조건에서 판독 반복성이 좋다는 근거다. 원본 정보 증가, 위치의 진실성, 독립 평가자 일치나 오차분포는 검증하지 않았다.
3. reference부터 직립이므로 정적 복사로도 직립은 가능하다. 변화 방향·순서가 source와 대응하는지, STATIC COPY 대비 무엇이 개선됐는지 봐야 한다. 부위 상대 운동과 개체 수용은 별도로 유보할 수 있다.
