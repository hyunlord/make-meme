# B-007 — 작은 attention 성공과 모델 실행 가능성 사이

## 1. 직관: 모든 위치를 비교하지만 모든 비교표를 저장할 필요는 없다

SCAIL은 생성 영상·reference·driving의 latent patch를 token으로 만든다. 각 query가 다른 token의 key와 얼마나 맞는지 비교하고 value를 가중 합산한다. Q와 K는 비교 기준, V는 가져올 정보이며 동물의 관절 좌표 자체가 아니다. RGB driving을 token으로 넣는다고 source의 정확한 안무가 자동 보장되지는 않는다.

batch B, query 길이 Nq, key 길이 Nk, head 수 H, head 차원 d를 정의하면 wrapper의 Q shape는 `(B,Nq,H,d)`, K/V는 `(B,Nk,H,d)`다. head별 attention은

`S_ij = (q_i · k_j)/sqrt(d)`

`p_ij = exp(S_ij) / Σ_k exp(S_ik)`

`o_i = Σ_j p_ij v_j`

이다. 출력은 query 길이를 유지한다. SCAIL14B config는 H=40, d=128이다. noncausal이므로 미래 physical video frame의 token도 참조할 수 있다. 영상 프레임 시간과 diffusion noise timestep은 다른 축이다. self attention은 reference/생성/driving token끼리, cross attention은 이 query에서 text 또는 CLIP context로 향한다. [실제 호출·flags·코드 링크](../experiments/B-007-scail-preflight/MODEL_RESOURCE_AUDIT.md).

## 2. N²와 FlashAttention IO를 구분한다

dense self attention은 각 head에서 N×N개의 비교를 수행한다. N=12,992이면 heads40의 score BF16 저장만 약13.50GB다. 이것은 naive 구현의 한 tensor 크기이며 이번 GPU 측정값이 아니다. QKV 세 묶음은 약399.11MB이고, hidden activation·FFN·RoPE·weight·VAE는 따로 필요하다.

FlashAttention은 score 전체를 GPU 메모리에 쓰지 않고 SRAM에 들어가는 tile을 순서대로 계산한다. 한 query 행에 대해 이전까지의 최대값 m, 지수합 l, 정규화 전 weighted sum a를 보관한다. 새 tile의 최대값 m_b를 만나면

`m' = max(m,m_b)`

`l' = exp(m−m') l + Σ_j exp(s_j−m')`

`a' = exp(m−m') a + Σ_j exp(s_j−m') v_j`

로 갱신하고 마지막에 `o=a/l`을 얻는다. 수학적으로 같은 softmax를 tile로 누적하되 부동소수점 순서 차이는 가능하다. IO 절약과 exact attention이라는 의미이지 모든 입력에서 byte 동일하거나 dense FLOPs가 O(N)이 된다는 뜻은 아니다. [FlashAttention 원 논문](https://arxiv.org/abs/2205.14135).

## 3. 실제 작은 smoke가 증명하는 것

고정 SCAIL wrapper는 CUDA BF16 QKV를 varlen 형식으로 포장한다. self의 key length와 cross의 서로 다른 query/key 길이를 지원해야 한다. head_dim128, causal=False, dropout=0, full window, 기본 scale을 유지한 작은 연산에서 finite·shape·SDPA 수치 비교를 확인하는 이유다. import 성공은 kernel 실행 성공이 아니다. SDPA가 같은 값을 준다고 실제 SCAIL backend를 바꾼 것도 아니다.

실제 모델 조건의 예상은 H512,W896,T17에서 latent T=5, reference T=1, patch1×2×2다. reference+생성 `6×32×56=10,752`, 절반 공간 driving `5×16×28=2,240`, 총12,992 tokens다. 이것은 pinned 코드 유도이며 모델 runtime hook 실측은 아니다. 작은 L의 커널 성공으로 이 큰 N의 peak나 속도를 예측하지 않는다.

FA 공식 소스의 SM121 빌드 분기, 실제 ARM64 binary, torch/CUDA ABI, 실제 연산 성공은 각각 다른 증거다. FA3/FA4가 Blackwell이라는 이름과 함께 언급돼도 pinned SCAIL의 FA2/FA3 varlen signature와 맞는지 확인해야 한다. 최종 커널 실행 상태는 [B-007 결과](../experiments/B-007-scail-preflight/RESULTS.md)에서 별도로 보고한다.

## 4. 디스크 파일·weight·activation·변환 peak

14B×2bytes=28GB는 '정확히14B BF16 parameter만 있다'는 가정의 weight 계산이다. 전체 모델 저장소는 비선택 파일만80.002GB이며 디스크 저장형식·T5·CLIP·VAE가 섞여 있다. 파일 크기에서 dtype 분포와 모든 activation을 역산할 수 없다.

SAT→Wan 변환은 전체 checkpoint를 `torch.load`하고 mapping한 dictionary를 `save_file`한다. mapping의 chunk는 view이고 일반 tensor는 참조이므로 dictionary가 두 개라고 weight가 두 배가 되지는 않는다. 그러나 원본 checkpoint 전체가 살아 있고 loader/serializer의 임시 복사와 device 복원 비용은 남는다. `map_location`·mmap·streaming·dtype 축소가 명시되지 않았다. 실제 peak는 미측정이며 file bytes를 곧 RAM 상한으로 쓰면 안 된다.

통합 메모리에서 CPU offload는 저장 위치·allocator·연산 시점을 바꾸지만 총 물리 메모리를 추가하지 않는다. weight가 들어가더라도 attention/MLP·VAE·conditioning과 OS 여유까지 있어야 inference가 가능하다. training은 gradient·optimizer·저장 activation이 더 필요하므로 이번 inference kernel smoke와 별개다. [실제 conversion/resource audit](../experiments/B-007-scail-preflight/MODEL_RESOURCE_AUDIT.md).

## 5. 시간축: 17장의 파일 길이와 관측 간격

원본 sample time은 `t_i=i/24`, i=0…16이다. 첫 장에서 마지막 장까지 관측 간격은16/24=0.666667초이며, 각 frame을1/24초씩 표시하는 파일 길이는17/24=0.708333초다. 동일17장을 기본16fps로 저장하면 파일은17/16=1.0625초이고 동작 속도는 원본의2/3이 된다. 장수를 유지한 채 fps만 바꾸는 것은 속도 보존이 아니다.

pinned SCAIL loader는 모든 frame을 읽고 writer는 기본16fps를 쓴다. 24fps를 보존할 후속 baseline에서는 최소 writer override와 동일 RGB/mask 공간 변환을 기록해야 한다. 이번에는 diffusion 영상을 생성하지 않았다. 중간 결과가 부족하다고 frame 복제·보간으로 품질 수용을 만들지 않는다.

## 6. 실제 결과와 해석 경계

실제 CPU mask 검사는 Mac PyTorch2.14.1에서 pinned helper로 실행됐다. 세로 reference에 맞춘 H896/W512 입력에서 reference 출력은 `(28,1,112,64)`, 17장 driver 출력은 `(28,5,56,32)`다. driver는 bilinear half 후 helper `additional_spatial_downsample=1`이다. threshold한 뒤 helper의 공간 축소를2로 두는 것과는 순서가 달라 같은 경계값을 보장하지 않는다. red slot `[1,8,15,22]`만 활성이고 다른 색은0이었다. area 보간 때문에 reference1,052개·driver2,380개 cell에0~1 사이 분수 점유율이 남았다. binary라는 함수 주석과 실제 출력은 구분해야 한다. [실측](../experiments/B-007-scail-preflight/MASK_TENSOR_CHECK.json).

Spark MemAvailable은06:07:46 UTC에95,932,358,656 bytes,06:10:56 UTC에94,136,250,368 bytes였다. 이는 컴파일 전후의 자원 기준선이며 모델 peak는 NOT_MEASURED다. 총 통합 메모리를 CPU/GPU 별도로 더하지 않는다.

HF metadata는 이전 revision과 동일함을 이번 HTTP 조회로 확인했다. 공식 attention 및 변환 경로를 읽었지만 가중치는 받지 않았다. kernel 담당자의 실행 결과가 확정되기 전까지 이 강의는 커널 성공을 주장하지 않는다. 실제 모델 로딩·peak·영상 품질·Lab 개체/안무 수용은 NOT_RUN 또는 NOT_MEASURED다.

[이해 질문](../experiments/B-007-scail-preflight/QUESTIONS_KO.md)을 먼저 풀고 [해설](../experiments/B-007-scail-preflight/ANSWERS_KO.md)을 확인한다.
