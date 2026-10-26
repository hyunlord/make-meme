# B-029 해설 — 이미지 attention 출력의 위치별 재가중

상태: **사전 선택 완료 / 실행·효과 미판정**. [B-028 결과](../experiments/B-028-object-reference-normalization/RESULTS.md)에서 부분 외형 개선과 차량 방향·자세 회귀, human R2 형태 결함을 확인한 뒤 [B-029 결정](../experiments/B-029-spatial-image-conditioning/DECISION.md)으로 분기 A를 선택했다. 전 6case의 공통 기준선은 B-027이다. 아래는 선택한 방법의 원리이며 영상 품질 개선을 미리 주장하지 않는다.

## 1. 직관: 무엇을 어디로 전달하는가

기존 SCAIL은 각 query token에 대해 텍스트 조건과 CLIP 이미지 조건의 attention 출력을 따로 계산한 뒤 더한다. 이번 방법은 이미 계산된 이미지 출력에 위치별 계수를 곱한다. 목표 가설은 “교체 대상 주변에 참조 특징을 더 배정하고, 그 밖에서는 줄이는 것이 도움이 되는가?”다. 참조의 자세를 제거하거나 객체를 분리해서 생성한다는 뜻은 아니다.

이 방법은 FlashAttention의 Q/K/V 또는 softmax를 수정하지 않는다. output projection 뒤의 전체 출력을 조절하는 것도 아니다. **이미지 attention 출력만, 텍스트 항과 합치기 전에** 조절한다. 공간 masking 자체는 IP-Adapter 계열에도 선례가 있으므로 새 기법의 독창성을 주장하지 않는다. [IP-Adapter §3.2.2](https://arxiv.org/html/2308.06721v1#S3.SS2.SSS2), [Diffusers 공식 구현](https://github.com/huggingface/diffusers/blob/v0.35.1/src/diffusers/models/attention_processor.py#L4361-L4395)

## 2. 수식과 가정

한 layer의 query 위치를 \(j\), hidden channel을 \(c\)라 하자. 텍스트와 이미지 attention 출력을 각각 \(T_j,I_j\in\mathbb R^C\)라 두면 기존 계산과 이번 변경은 다음과 같다.

\[
O_j=W_o(T_j+I_j)+b_o,\qquad
O'_j=W_o(T_j+g_j I_j)+b_o.
\]

\(W_o\)는 기존 학습된 출력 projection이며 고정한다. PyTorch `Linear`는 같은 연산을 행벡터 기준으로 `input @ weight.T + bias`로 표현한다.

generated token의 시간 인덱스 \(t\), 공간 위치 \((h,w)\)에서 부드러운 support 지도 \(E_{t,h,w}\in[0,1]\)를 사용할 때 계수는

\[
\mu_t=\frac1{HW}\sum_{h,w}E_{t,h,w},\qquad
 g_{t,h,w}=1+0.5(E_{t,h,w}-\mu_t).
\]

따라서 각 시간 slice에서 \(\operatorname{mean}_{h,w}(g)=1\)이다. 그러나 이는 **계수 평균**만 유지한다. 각 channel에 대해

\[
\operatorname{mean}(gI_c)-\operatorname{mean}(I_c)
=0.5\operatorname{mean}((E-\mu)I_c)
\]

이며 일반적으로 0이 아니다. 예를 들어 \(E=(1,0), I_c=(2,0)\)이면 \(g=(1.25,0.75)\)이고 특징 평균은 1에서 1.25로 바뀐다. 특징의 norm, 예측 속도장의 크기, 출력 밝기 또는 계산 경로를 보존한다는 보장도 없다.

reference·driving 등 generated 이외 token에는 \(g=1\)을 둔다. 같은 지도를 양 CFG branch에 적용해도 두 branch의 hidden 특징은 같지 않으므로 영향이 상쇄된다고 가정할 수 없다. sampling이 진행되면 METHOD와 기준선의 noisy latent 궤적도 달라진다.

## 3. 텐서와 좌표 계약

attention의 head를 합친 `img_x`는 `[B,L,C]`, 전체 gate는 `[1,L,1]`이다. gate를 실제 `img_x`의 device/dtype에 맞추고 channel에 broadcast한다. `L`에는 reference와 generated, driving token이 모두 포함되므로 전체 길이를 generated 길이로 오인하면 안 된다.

공식 순서는 `additional_ref → ref → generated → driving`이다. generated 범위는

\[
 j_0=\texttt{additional_ref_length}+\texttt{ref_length},\qquad
 j_0\le j<j_0+\texttt{seq_length}.
\]

예를 들어 latent `[16,5,64,112]`, patch `(1,2,2)`이면 generated grid `[5,32,56]`와 generated 8,960 token을 예상한다. 이번 실제 forward에서도 grid `[5,32,56]`, generated 시작1,792·길이8,960·driving suffix2,240을 관측했다. 이 값은 해당 공개 패널의 runtime 값이며 모든 입력에 통하는 상수가 아니다. 실제 grid와 `[t,h,w]` flatten 순서를 읽어 지도를 맞춘다.

17개 source mask를 latent 시간축으로 대응시키는 첫 프레임+4개씩의 시간 합집합은 관측용 공간 배정의 근사다. VAE는 학습된 시공간 convolution 등을 사용하므로 이 규칙을 정확한 receptive field라고 부를 수 없다. 이번에는 시간 합집합 → clip 전체 bbox 긴 변의 10%를 올림한 반경의 정사각 dilation → 7×7 zero-padded 평균 필터 → `[0,1]` 제한 → area resize 순서를 사전 고정했다. 이 연산도 target의 실제 새 실루엣 정답을 만들지는 않는다. 결과를 본 뒤 수치나 순서를 조절하지 않는다.

## 4. 실제 코드 접점과 남는 경로

고정 SCAIL revision: `78fe19576bb06be96c2375e088574a262a300edb`.

| 확인한 접점 | 코드상 의미 | 이번에 필요한 확인 |
|---|---|---|
| [`WanI2VCrossAttention.forward`, L348–375](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/modules/model_scail2.py#L348-L375) | 이미지/텍스트 attention 분리, flatten, 합산, `self.o` | L372 이후 합산 전 `img_x`만 조절 |
| [`WanAttentionBlock.forward`, L424–460](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/modules/model_scail2.py#L424-L460) | block은 길이 metadata를 받지만 cross 호출에는 전달하지 않음 | 정확한 generated 범위를 좁게 연결; 고정 token 상수 금지 |
| [token/context 구성, L741–823](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/modules/model_scail2.py#L741-L823) | reference VAE와 generated를 결합; CLIP은 `img_emb` 후 text와 context 구성 | 입력·가중치·token 순서 불변, 이미지 출력 경로만 변경 |
| [`unpatchify`, L870–899](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/modules/model_scail2.py#L870-L899) | generated offset에 해당하는 출력을 복원 | 게이트의 범위와 실제 출력 범위 대조 |

**reference VAE 경로는 그대로 남는다.** 참조 latent가 joint self-attention에 참여하며, 이후 layer는 공간 사이 정보를 다시 섞는다. CLIP 이미지 항의 공간 재가중은 reference OFF, 배경 완전 차단, identity-only 표현과 다르다. 경로 설명은 공식 코드에 근거하며, 이번 runtime에서 기록한 generated 범위·적용 횟수와 별도로 구분한다. 이미지 항의 실제 dtype은 FP32였고 그대로 유지했다.

이번 실험의 함수 연결은 [`support_map`](../experiments/B-029-spatial-image-conditioning/code/build_support_maps.py) → [`install(..., GateConfig(...))`](../experiments/B-029-spatial-image-conditioning/code/spatial_image_gate.py) → block prehook의 길이/grid 전달 → `compile_forward`의 합산 직전 image-only 변환이다. `GateInstallation.report()/assert_complete()`로 첫 호출의 범위·통계와 최종 적용 횟수를 남긴다. 작은 CPU 계약6개와 기존 계약4개를 통과했고, 완료된 실제 실행은40block×80 gate 적용을 기록했다. CPU fixture는 전체14B OFF 수치 동등성 검증이 아니며 코드 적용 성공도 영상 품질 성공이 아니다. 소스 SHA나 실제 token 범위가 다르면 이름만 같은 함수라고 간주해 계속 진행하지 않는다.

## 5. 대조와 반례: 어떤 주장을 반박할 수 있는가

OFF 검사는 코드 변경 없이 기존 계산을 사용하는 기능 계약이다. 작은 fixture의 OFF 일치는 14B 전체 모델의 수치 동일성이나 시각 품질을 보장하지 않는다.

CONTROL은 token 공간 지도를 H/W 절반만큼 cyclic shift한다. 같은 계수 histogram·평균·시간 순서를 유지하면서 대상 위치와의 관계를 바꾼다. animal R1과 vehicle R1을 사전 선택했다. METHOD가 CONTROL보다 유용해야 “위치에 맞춘 배정”이라는 설명에 제한된 근거가 생긴다. 지도가 크게 겹치면 대조력이 낮고, 단일 seed의 차이를 통계적 유의성으로 해석할 수 없다.

가능한 반례는 다음과 같다.

- 참조 자세 복사가 VAE 경로에 크게 의존한다면 CLIP 출력 재가중 효과가 작을 수 있다.
- 대상 부근의 이미지 정보를 강화해 오히려 참조 정지 자세 복사를 키울 수 있다.
- target 체형이 source support 밖으로 넓어지면 필요한 특징을 약화할 수 있다.
- 외형만 좋아지고 source 동작·장면이 나빠지면 결합 목표의 성공이 아닌 trade-off다.
- METHOD와 shifted CONTROL이 비슷하면 공간적 정합이 개선 원인이라는 설명은 미입증이다.

선택한 공통 기준선은 B-027이다. B-028에서 좋아진 case를 혼합한 best-of를 만들지 않는다. 이 개발 패널은 방법 선택에 사용되므로 미사용 일반화 평가가 아니다. METHOD6와 CONTROL2의 신규 sampler는 실패 포함 최대8회이며 추가 관측용 forward는 없다.

## 6. 기존 관측과 새 검증의 경계

- 기존 관측: B-028은 일부 target 외형을 더 반영했지만 차량 두 참조에서 방향·자세가 회귀했고 human R2의 형태 결함이 남았다. 이는 [기존 결과 문서](../experiments/B-028-object-reference-normalization/RESULTS.md)의 정적 검토이며 이 해설 작성자가 독립 반복 평가한 결과가 아니다.
- 사전 결정: B-027을 공통 기준선으로 두고 이미지 조건 전달 위치의 가설을 한 번 검사한다. 실패 원인이 해당 경로라고 확정한 것은 아니다.
- 코드/조건 연결: 기존 B027의16leaf/noise 계보를 유지하고 generated 구간의 이미지 항에만 적용했다. 첫 실제 dtype은 FP32이며 각 완료 case의40step/80forward와40×80 gate count를 별도 확인한다. LSP transport는 닫혀 NOT_CLEAN이며 runtime 근거와 혼동하지 않는다.
- 외형·동작·형태·장면·비용의 변화: **[비교 후 작성]**
- 핵심 CONTROL과의 차이 및 반례: **[비교 후 작성]**
- temporal: **UNVERIFIED — 실제 연속 재생 관찰 여부를 별도로 기록**
- 다음 검증으로 넘김/보류/기각: **[결과 후 결정; 자동 후속 실행 없음]**

## 7. 이해 확인 질문

1. 왜 `mean(g)=1`이어도 이미지 조건 특징과 최종 출력의 평균·norm은 유지되지 않는가? 두 위치의 수치 예로 설명해 보자.
2. generated token의 `img_x`만 조절했는데도 보호 배경과 참조 자세 복사가 남거나 달라질 수 있는 경로는 무엇인가?
3. METHOD와 cyclic-shift CONTROL이 모두 baseline보다 좋아졌지만 둘의 품질 차이가 불명확하다면 무엇을 말할 수 있고 무엇은 말할 수 없는가?

---

## 별도 해설

1. 가중치와 특징이 위치별로 상관될 수 있기 때문이다. 위 예에서 계수 평균은 1이지만 큰 특징이 있는 위치를 더 강화해 특징 평균이 증가했다. 이후 projection·residual·비선형 layer·sampler도 있으므로 계수 평균에서 최종 영상 통계를 도출할 수 없다.
2. reference VAE의 joint self-attention 경로가 유지되고, 이미지 조건의 바깥 계수도 0이 아니며, 후속 attention은 위치 사이 정보를 전달한다. 따라서 한 지점의 CLIP 출력 제어는 모든 참조 경로의 차단이나 픽셀 보호 계약이 아니다.
3. 해당 입력·seed에서 계수 재배정이 영향을 준 탐색 근거는 보고할 수 있다. 하지만 source 대상 위치와 맞춘 것이 핵심 개선 원인이라는 설명은 입증되지 않았다. 실제 항목별 차이와 불확실성을 남기고 추가 forward·seed를 자동 실행하지 않는다.
