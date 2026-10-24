# B-016 — RoPE 위치 조건과 reference의 공간 관계

상태: **문헌·고정 코드 확인 완료 / CPU 계약 결과 대기 / 신규 model 실행·출력·영상 검토 NOT_RUN**. [PLAN](../experiments/B-016-reference-rope-h/PLAN.md)에 따라 ALG는 OFF이며, animation에서 reference H offset만 0→120으로 바꾼다. B013의 CFG_MOV_H0는 그대로 재사용한다. 이는 이미지 이동·자세 retargeting·학습된 개체/자세 분리가 아니다.

## 1. 직관과 출처

같은 reference 내용도 attention이 참조 token과 영상 token의 위치 관계를 다르게 읽으면 다른 조건이 된다. [RoFormer](https://arxiv.org/abs/2104.09864v5)는 Q/K를 위치별 회전하여 상대 위치가 내적에 들어가는 구성을 제시한다. 이것이 특정 frozen 영상 모델에서 자세 전이를 개선한다는 보장은 아니다.

[SCAIL-2 §3.3](https://arxiv.org/html/2606.10804v1#S3.SS3)는 mode-specific RoPE와 mask 조건으로 과제를 구별한다. 이번에는 animation mask와 시간 offset을 그대로 둔 채 reference 높이만 replacement의 값으로 바꾸므로 공식 replacement 재현이 아닌 hybrid다. 이 조합의 학습분포 적합성은 UNKNOWN이다. 공개 논문의 일반 결과를 이번 Lab 사례의 검증으로 대신하지 않는다.

## 2. 회전과 상대 위치: 무엇이 불변인가

한 주파수 θ의 2차원 회전을 R(pθ)라 하자. q와 k는 회전 전 projection 벡터이며 d는 head 차원이다.

\[
R(a)^T R(b)=R(b-a),\qquad
s_{ij}=\frac{(R(h_i\theta)q_i)^T(R(h_j\theta)k_j)}{\sqrt d}
=\frac{q_i^T R((h_j-h_i)\theta)k_j}{\sqrt d}.
\]

reference의 모든 h에 Δ=120을 더하면 ref-ref의 차이 h_j−h_i는 그대로다. **고정 Q/K의 ref-ref pre-softmax logit과 reference Q/K norm**은 수치 오차 범위에서 보존된다. ref↔video, ref↔driving의 상대 위치는 바뀐다. 특정 벡터에서는 cross logit이 우연히 같을 수도 있으므로 모든 원소의 변화가 수학적 필수조건은 아니다.

\[
 a_{ij}=\frac{\exp s_{ij}}{\sum_k\exp s_{ik}},\qquad y_i=\sum_j a_{ij}V_j.
\]

ref-ref s가 같아도 다른 key의 s가 달라지면 분모가 달라진다. 따라서 ref-ref 확률·attention 출력·다음 층 Q/K는 불변이 아니다. V를 직접 수정하지 않는 것과 V의 가중합이 같다는 것도 다르다. cosine은 주기적이므로 offset 증가가 모든 참조 영향을 단조 감소시킨다고 단정할 수 없다. 이것은 reference pose만 제거하는 필터가 아니다.

## 3. 실제 T/H/W 분할과 좌표 단위

고정 SCAIL commit은 `78fe19576bb06be96c2375e088574a262a300edb`다. [rope_params와 rope_apply_ref](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/modules/model_scail2.py#L32-L80)는 실수 d=128을 complex64로 보고 `[c−2(c//3),c//3,c//3]`으로 나눈다. 실제 T/H/W는 complex22/21/21, 실수44/42/42차원이다. 각 축의 주파수를 이어 붙여 동일 token의 서로 다른 차원 쌍에 적용한다. 세 축을 영상의 RGB 채널로 해석하면 안 된다.

부모 B013에서 관측된 shape와 이번 동일 입력으로 예상되는 geometry는 다음과 같다. B016 runtime 확인은 별도로 남긴다.

| 항목 | shape / token 수 | 의미 |
|---|---|---|
| 생성 noise latent | `[16,5,112,64]` FP32 | 17 물리 프레임의 압축 시간 5 |
| reference latent | `[16,1,112,64]` FP32 | 정지 reference 1개 |
| patch(1,2,2) 후 reference | 1×56×32=1792 | h=0..55 →120..175 |
| generated patch | 5×56×32=8960 | reference와 별도 시간 구간 |
| driving latent / patch | `[16,5,56,32]` / 5×28×16=2240 | 원래 낮은 공간 해상도 조건 |
| 전체 self-attention | 12992 token, 40 heads, d128 | 1792+8960+2240 |
| CLIP / positive text | `[1,257,1280]` / `[108,4096]` | 별도 context 경로 |

H120은 pixel120, latent120 또는 영상 crop 이동이 아니라 **회전에 쓰는 위치 table의 index offset120**이다. 원본 pixel canvas는 896×512이며 그대로다. T는 noise scheduler step도 physical fps도 아니며 여기서는 latent token의 시간 좌표다.

[rope_apply_scail](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/modules/model_scail2.py#L183-L218)은 ref/video/pose 구간을 나누어 처리한다. driving 경로의 [복소 주파수 평균](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/modules/model_scail2.py#L145-L180)은 실수·허수 성분을 2×2 average pool한다. 평균의 크기가 반드시 1은 아니므로 모든 driving 연산을 순수 unitary 회전으로 설명하지 않는다. 이번에는 그 경로를 수정하지 않는다.

## 4. self-attention과 cross-attention을 구분한다

[WanSelfAttention.forward](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/modules/model_scail2.py#L275-L306)는 Q/K projection·norm 뒤 같은 rope 함수로 둘을 변환하고 V는 직접 회전하지 않는다. FlashAttention 경로와 head 수는 유지하며 전체12992² attention map을 새로 계산하지 않는다.

[mask/patch 결합](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/modules/model_scail2.py#L751-L764), [CLIP context 결합](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/modules/model_scail2.py#L798-L800)은 그대로다. CLIP에 실루엣·배경·자세 정보가 없다고 가정하지 않는다. H 변경만으로 identity 경로와 pose 경로가 분리되었다고 주장할 수 없다.

[mode별 offset](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/modules/model_scail2.py#L830-L865)의 animation baseline은 ref(T,H,W)=(0,0,0), generated=(1,0,0), driving=(1,0,120)이다. 이번에는 ref만 (0,120,0)이다. replace_flag를 True로 바꾸면 시간과 입력 의미까지 달라지므로 그렇게 구현하지 않는다. additional_ref=None 조건을 유지한다.

CFG는 `v=u+5(c−u)`로 유지한다. 두 text branch는 시각 조건과 H120 개입을 공유한다. 40 scheduler update는 80 forward이며, 17개 physical frame과 서로 다른 수다. 초기 noise·scheduler·RNG·16개 cache leaf는 동일해야 한다. 출력 trajectory 차이는 이 초기 동일성 아래 관찰할 결과이지 같은 z에서의 attention 차이 실측과 동일하지 않다.

## 5. 검증 계층과 미관측 경계

CPU fixture는 작은 고정 Q/K의 OFF/0 동일성, reference norm·내부 logit 보존, 다른 token의 RoPE 출력 보존, cross logit 변화와 table 범위를 검사한다. 실제 CPU 수치·runtime resolved offset·block/step coverage·이미지 결과는 receipt 도착 뒤 기록한다. 작은 fixture PASS가 full model 의미 보존이나 생성 품질 PASS는 아니다.

검토 도구는 네 열의 같은 canvas·17장·24fps와 local0/12/14/16을 준비했다. 실제 렌더는 D 완료 전 NOT_RUN이다. 전신 직립/앞발, 국소 roll, 얼굴·체형, source appearance 누수, 배경 변화, 시간 품질을 분리한다. 연속 시청이 없으면 temporal UNVERIFIED이며 정적 이미지로 자동 승격하지 않는다. 이번 문서는 다음 실험이나 offset 탐색을 제안·실행하지 않는다.

## 이해 확인 질문

1. reference의 모든 H를 같이 옮겼는데 ref-ref attention 확률은 왜 같지 않을 수 있는가?
2. H120을 이미지에서120픽셀 이동한 것으로 볼 수 있는가?
3. 얼굴이 좋아졌지만 움직임이 사라졌다면 동작 전이가 개선된 것인가?

## 별도 해설

1. 고정 Q/K의 ref-ref logit만 보존된다. 다른 key의 logit이 바뀌어 softmax 분모·출력·다음 층 Q/K가 달라질 수 있다.
2. 아니다. 회전 table index이며 현재 patch grid의 높이 좌표에 더한다. 이미지·latent 내용·mask를 이동하지 않는다.
3. 아니다. 정적 외형 보존과 source의 자세·순서·방향 대응을 따로 판정해야 한다. 같은 한 사례의 변화가 학습된 disentanglement나 일반화 증거도 아니다.
