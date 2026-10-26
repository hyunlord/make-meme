# B-030 학습: 참조 조건을 교차하면 무엇을 구분할 수 있는가?

이 문서는 새 모델이나 편집 방법의 제안이 아니다. B-027의 같은 target track 두 참조를 사용해 **VAE+semantic mask 묶음**과 **CLIP image context**의 조건부 영향을 구분하는 실험을 설명한다. 실행 계획은 [PLAN](../experiments/B-030-reference-path-crossover/PLAN.md), 최종 관측은 해당 실험의 RESULTS와 MATRIX_REVIEW에 기록한다. 이 문서의 수식은 해석 도구이며 시각 평가 점수가 아니다.

## 1. 직관: 두 통로는 외형과 자세를 독점하지 않는다

한 사진은 색·무늬·얼굴뿐 아니라 자세, 카메라 방향, 가림과 화면 배치도 담는다. VAE는 이 사진의 공간 격자를 보존한 latent를 만들고, CLIP은 사진의 image token을 만든다. 두 표현 모두 외형과 공간 정보를 포함할 수 있다. 따라서 `VAE=pose`, `CLIP=identity`라는 명명으로 결과를 미리 정하지 않는다.

같은 대상의 R1/R2에서 한 통로만 바꿔 보면 어느 관측이 유지되고 바뀌는지 알 수 있다. 다만 VAE와 함께 semantic mask도 바뀌므로 행 변화는 VAE 단독 개입이 아니다. 또한 두 통로는 모델 안에서 여러 층을 통해 상호작용한다.

## 2. 수식: 조건부 출력과 2×2 비교

원본 driving 영상과 mask를 D, caption을 P, 실제 초기 noise를 ε라 하자. 참조 사진 R_i에서 얻은 두 묶음을 다음과 같이 정의한다.

\[
Z_i=(E_{\mathrm{VAE}}(R_i),M_i),\qquad C_j=E_{\mathrm{CLIP}}(R_j),\qquad
Y_{ij}=F_\theta(D,Z_i,C_j,P;\epsilon).
\]

θ는 동결된 모델 가중치다. 이번에 학습하지 않는다. i와 j는 같은 target track의 사진 번호이며 서로 다른 사람이나 차량의 정체성을 섞는 번호가 아니다.

| VAE+mask | CLIP R1 | CLIP R2 |
|---|---|---|
| R1 | Y11, 기존 B-027 | Y12, 새 교차 |
| R2 | Y21, 새 교차 | Y22, 기존 B-027 |

- Y11↔Y12와 Y21↔Y22: VAE+mask를 고정하고 CLIP 사진만 바꾼 비교다.
- Y11↔Y21와 Y12↔Y22: CLIP을 고정하고 VAE+mask 사진 묶음을 바꾼 비교다.
- Y11↔Y22만 보면 두 묶음이 동시에 바뀌어 어느 조건을 따른 것인지 구분하기 어렵다.

신뢰할 수 있는 scalar 관측 q가 사전에 정의돼 있다면 `I=q22−q21−q12+q11`은 CLIP 변경 효과가 VAE+mask 행에 따라 얼마나 달라지는지를 나타내는 차이의 차이다. 이번의 얼굴 가림·치마 손상·차량 그래픽은 보정된 scalar 지표가 없으므로 정성적 표를 사용한다. 임의 점수, 유의성 또는 픽셀 거리 기반 identity 점수를 만들지 않는다.

## 3. 실제 cache와 shape

아래는 기존 B-027 human R1의 `conditions.json` 구조·dtype 기록과 실제 고정 코드를 읽어 확인한 값이다. B-030 새 실행의 hash·전달 확인은 별도 CONDITIONS와 runtime 기록으로 판단한다. 번호는 그 cache의 직렬화 leaf ID이며 다른 실험의 보편적 API가 아니다.

| leaf / model argument | 저장 shape | dtype | B-030 행 대비 계약 |
|---|---|---|---|
| t2/t8, 양 CFG `clip_fea` | [1,257,1280] | FP16 | 반대 참조의 값으로 교체 |
| t3/t9, `ref_latents[0]` | [16,1,64,112] | FP32 | 그대로 |
| t4/t10, `ref_masks[0]` | [28,6,64,112] | FP32 | 그대로 |
| t5/t11, `pose_latents[0]` | [16,5,32,56] | FP32 | 그대로 |
| t6/t12, `driving_masks[0]` | [28,5,32,56] | FP32 | 그대로 |
| t0, actual initial noise | [16,5,64,112] | FP32 | 그대로 |
| t1/t7, positive/empty negative | human [55,4096]/[1,4096] | BF16 | 그대로 |
| t13, generator state | [16] | uint8 | CPU 계약 보존 |
| t14/t15, timesteps/sigmas | [40]/[41] | int64/FP32 | 값과 device 계약 보존 |

차원이 `[C,T,H,W]`인 VAE latent에서16은 latent channel 수다. 영상17장은 VAE 시간 stride4에 따라5개 latent 시간 위치가 된다. 896×512 입력에서 생성 latent의 공간 크기는 H64×W112이고, 공식 driving 경로는 RGB를 공간적으로 절반으로 줄인 뒤 인코딩하므로 H32×W56이다. reference는 시간 길이1이다.

`ref_masks`의 시간 길이6은 reference prefix1 + generated5다. 뒤5개 slice는 이 입력에서 zero이며, driving mask와 혼동하면 안 된다. semantic mask는 RGB alpha를 곱하는 matte도, attention 확률에 곱하는 hard mask도 아니다. [공식 helper](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/utils/scail_utils.py#L106-L139)는 RGB 색상으로7채널을 만들고 공간 area downsample 및4시점 packing으로28채널을 만든다. 공간 평균 뒤에는 경계의 coverage 값이 생길 수 있으므로 함수 주석의 ‘이진’ 표현을 모든 최종 원소가0/1이라는 보장으로 확대하지 않는다.

## 4. 코드: 두 경로가 어디에서 만나는가?

고정 공식 revision은 `78fe19576bb06be96c2375e088574a262a300edb`다. 실행 환경의 보존된 소스와 B-027 manifest에서 이 계보를 확인했으며 새 checkout·encoder 실행·가중치 검증을 반복하지 않았다.

| 실제 함수/위치 | 연결과 의미 |
|---|---|
| [SCAIL generate, ref encode](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/scail.py#L292) | reference RGB를 VAE에 넣어 `ref_latent` 생성 |
| [driving와 mask, arg_c/arg_null](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/scail.py#L438-L511) | driving VAE, reference prefix mask, 두 CFG의 같은 시각 조건 구성 |
| [SCAIL2Model.forward](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/modules/model_scail2.py#L720-L794) | reference+generated를 시간축으로 합쳐 patch embedding; semantic mask embedding을 더함; driving embedding을 token 뒤에 붙임; CLIP을 별도 context 앞에 연결 |
| [WanI2VCrossAttention.forward](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/modules/model_scail2.py#L348-L375) | 같은 query에서 image와 text의 K/V attention을 각각 계산하고 두 출력을 더한 뒤 output projection |
| [head와 unpatchify](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/modules/model_scail2.py#L868-L899) | reference token을 제외한 generated 구간만 다시 영상 latent로 변환 |
| [B-027 phase_sample.run](../experiments/B-027-public-reference-robustness/code/phase_sample.py) | 복원 cache 객체가 실제 두 CFG forward에 전달되는지 확인;40step80forward 뒤 final latent 저장 |

추가 참조가 없고 patch=(1,2,2)인 이번 입력에서 token 수는 reference `1×32×56=1792`, generated `5×32×56=8960`, driving `5×16×28=2240`, 합계12992다. model hidden dimension은5120이다. CLIP257token은 `img_emb`를 통해 hidden 폭으로 투영되고, 최대512token의 text embedding 앞에 붙어 context 길이769를 이룬다. 이는12992개의 영상·참조 token과 다른 축이다.

VAE+mask는 joint self-attention의 token 상태에 직접 들어간다. CLIP은 image cross-attention의 K/V로 들어가지만 query는 이미 다른 조건의 영향을 받은 hidden state다. 개념적으로 각 block의 cross-attention은

\[
Q=W_QX,\quad I=\operatorname{Attn}(Q,W_K^IC_j,W_V^IC_j),\quad
T=\operatorname{Attn}(Q,W_K^TP,W_V^TP),\quad O=W_O(T+I)+b_O
\]

로 볼 수 있다. 실제 코드는 Q/K normalization과 head reshape를 포함한다. B-029는 I의 출력에 위치 계수를 곱했지만 B-030은 그 gate를 사용하지 않고 C_j 입력만 바꾼다. 이번 열 효과가 보여도 B-029의 실패 판정을 뒤집지 않는다.

## 5. CFG와 샘플링 경로의 차이

공식 sampler는 positive→negative 순서로 두 번 forward하고 아래처럼 합친다.

\[
\widehat v_{ij}(x_\sigma,\sigma)=v_\theta(x_\sigma,\sigma;D,Z_i,C_j,P_-) +5\big[v_\theta(x_\sigma,\sigma;D,Z_i,C_j,P_+) -v_\theta(x_\sigma,\sigma;D,Z_i,C_j,P_-)\big].
\]

여기서 `P_-`는 empty negative text다. negative branch도 reference·driving을 받으므로 ‘아무 조건 없는 모델’이 아니다. 교차를 한 branch에만 적용하면 이번 실험과 다른 CFG 방향을 만들게 된다. 두 branch의 `clip_fea`를 함께 바꾸는 이유다. 실제 [sampler 코드](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/scail.py#L387-L416)는 UniPC scheduler에 이 예측을 넘긴다. 변수명 `noise_pred`만 보고 ε-prediction 학습이라고 단정하지 않는다.

같은 ε·RNG·timesteps·sigmas는 시작점과 적분 규칙을 고정한다. 조건이 달라 첫 예측이 바뀌면 이후 noisy latent도 달라진다. 따라서 최종 Y12−Y11은 같은 hidden state에서 CLIP의 국소 미분값이 아니라40step 생성 경로 전체의 조건부 차이다. noise time σ는 모델의 denoising 축이고,17개 영상 frame의 시간축과 다르다. 이번 preview24fps는 원본 FPS가 확인된 시간이 아니다.

## 6. 관측을 해석하는 기준과 현재 상태

**실제4셀 실행 후 관측:** [RESULTS](../experiments/B-030-reference-path-crossover/RESULTS.md)와 [MATRIX_REVIEW](../experiments/B-030-reference-path-crossover/MATRIX_REVIEW.md)에 전체17장 정적 비교를 기록했다. 사람은 같은 CLIP의 두 비교에서 R2 VAE+mask 행의 치마 규모·높이가 더 컸다. 그러나 Y21의 원반형과 Y22의 세로 접힘은 다르고 Y12에는 수평 상체 파편이 있어 역할의 완전한 분리는 아니다. 차량의 별도 큰 그래픽은 Y11에만 나타나 두 단일 경로 중 하나로 귀속할 수 없다. 네 차량 모두 source형 비율이 남았다.

이 결과는 앞의 조건부 차이가 다른 조건 수준에 의존할 수 있다는 실제 예다. 그래픽의 이진 유무를 설명용으로만 q라고 두면 q11=1, q12=q21=q22=0이므로 대각 조합 특이성이 보인다. 이 값은 identity/motion 점수나 통계적 상호작용 추정치가 아니다. 사람의 행 경향도 mask와 VAE를 분리하지 못하며, 교차 손상은 학습분포 밖 조합 가능성과 함께 해석해야 한다. 같은 초기 noise가 이후 전체 latent 궤적까지 같게 만드는 것은 아니다.

행을 따라 치마/가림 또는 차체 배치가 반복되면 해당 입력·seed에서 VAE+mask 묶음과의 조건부 의존 근거다. mask·시점·가림도 함께 바뀌므로 VAE 단독, 공간 좌표, 모든 layer의 원인을 식별하지 못한다. 열을 따라 장식이나 외형이 반복돼도 CLIP이 identity만 표현한다는 증거는 아니다.

교차 셀만 크게 붕괴하면 두 표현의 불일치 또는 상호작용 가능성을 남긴다. 같은 대상이어도 통상 동일 사진에서 함께 생성되는 두 표현을 서로 다른 사진에서 가져왔으므로 분포 밖 조합일 수 있다. 어느 encoder가 잘못됐다고 확정하지 않는다. source-copy는 identity-change 성공이 아니며 reference 정지 복사는 motion 성공이 아니다. 미세 얼굴·접촉·가림은 UNCERTAIN, 실제 연속 시청이 없다면 temporal=UNVERIFIED다.

## 이해 확인 질문

1. Y12와 Y22에서 결과가 다르면 왜 ‘CLIP이 원인’이라고 바로 말할 수 없는가?
2. 양 CFG 중 positive의 CLIP만 R2로 바꾸면 이번 비교와 무엇이 다른가?
3. 같은 seed와 initial noise에서 두 결과가 크게 달라도 reference 경로를 분리 학습했다고 말할 수 없는 이유는 무엇인가?

## 별도 해설

1. 두 셀의 CLIP은 모두 R2다. 달라지는 것은 VAE+mask 묶음 R1/R2이며, 관측은 그 조건부 묶음 차이에 대응한다. 순수 VAE나 순수 자세 효과는 아니다.
2. negative 기준항은 R1, positive는 R2가 되어 텍스트 차이뿐 아니라 시각 조건 차이도 CFG 차분에 섞인다. B-030은 두 branch 모두 같은 교차 묶음을 전달해 이 추가 변수를 만들지 않는다.
3. 같은 초기값은 비교의 통제지만 encoder 표현이 identity/pose로 분리됐다는 보장은 아니다. 모델은 동결됐고 mixed-reference는 학습분포 밖일 수 있다. 이번에는 특정 패널의 조건부 응답과 상호작용을 관찰할 뿐 새 학습·일반화·품질 개선을 입증하지 않는다.
