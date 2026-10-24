# B019 — 고정된 block 뒤를 통과하는 LoRA gradient와 activation 메모리

상태: 공식 소스 판독 및 CPU 계약 검사 완료, B019 SMALL_BLOCK_UPDATE_RELOAD_PASS 및 LONG_BLOCK_BACKWARD_PASS. 최종 통합 CPU 검사는18 PASS이며, 별도 최종 contract/helper 검사는14 PASS다. 순수 contract helper typing은0 errors/0 warnings, hook 포함 계약 테스트는0 errors/4 warnings, runner typing은0 errors/145 warnings로 NOT_CLEAN이다. B018의 한 self-attention 성공을 이번 full block 성공으로 대신하지 않는다. 모든 입력은 수치 fixture이며 실제 영상·FM target·Lab 정답이 아니다.

## 1. 이번 질문

LoRA가 있는 self-attention 뒤에 고정된 image/text cross-attention과 FFN이 붙는다. 마지막 출력 loss에서 시작한 gradient가 그 연산들을 거쳐 LoRA까지 도착하는지 검사한다. 고정된 parameter가 있다는 것과 그 연산을 미분하지 않는다는 것은 다르다. 실제 실행 근거는 stage별 receipt이며 아래 식은 고정 코드의 해석이다.

공식 source revision은 `78fe19576bb06be96c2375e088574a262a300edb`다. [WanAttentionBlock L384–461](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/modules/model_scail2.py#L384-L461)를 기준으로 한다.

## 2. block 식과 세 종류의 조건

m은 저장된 modulation parameter, e는 외부 timestep embedding의 block 입력이며 둘 다 `[1,6,5120]`이다. 여섯 조각을 `(a_s,b_s,g_s,a_f,b_f,g_f)=chunk(m+e)`라 쓰면 실제 흐름은

\[
y_s=SA(LN_1(x)(1+b_s)+a_s),\quad r=x+g_s y_s,
\]
\[
z=r+CA(LN_3(r),c),\quad o=z+g_f FFN(LN_2(z)(1+b_f)+a_f).
\]

실제 순서는 self→residual→cross→residual→FFN→residual이다. g_s/g_f는 training fixture의 gate 입력과 저장된 m이 합쳐진 값이다. 이번 e의 shift/scale 입력은 uniform[-0.05,0.05], 두 gate 입력(index2/5)은1로 고정한다. 저장된 m은 수정하지 않는다. e는 고정 수치 tensor이며 실제 diffusion sigma에서 time MLP가 계산한 activation이 아니다.

SA는 reference/video/driving token들이 함께 정보를 교환하는 joint attention이다. CA는 별도의 image/text context를 읽는다. 이 둘의 reference 경로를 혼동하면 안 된다. [WanI2VCrossAttention L331–375](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/modules/model_scail2.py#L331-L375)는 context 마지막512개를 text로, 앞부분을 image로 나눈다. 이번 synthetic context `[1,769,5120]`에서 앞257=image, 뒤512=text다. 원시 CLIP1280/T54096가 아니라 이미 hidden5120으로 projection됐다고 가정한 수치 입력이다.

CA는 하나의 Q에 대해 image K/V와 text K/V로 FA를 두 번 수행하고 두 출력을 더한 다음 o projection을 한다. 단일 softmax 안에서 image/text를 concatenate한 방식과 다르다. 한 block forward에는 SA1+CA2로 FA 호출3개가 있다. 따라서 block8forward가 FA8회라는 뜻이 아니다.

## 3. chain rule: freeze는 input derivative를 없애지 않는다

고정 y=Wx의 parameter gradient를 저장하지 않아도 `dL/dx=W^T(dL/dy)`가 필요할 수 있다. self LoRA parameter를 φ라 하면

\[
\frac{\partial L}{\partial\phi}
=\frac{\partial L}{\partial o}
\frac{\partial o}{\partial z}
\frac{\partial z}{\partial r}
\frac{\partial r}{\partial y_s}
\frac{\partial y_s}{\partial\phi}.
\]

residual 때문에 `∂z/∂r=I+J_CA J_LN3`다. CA가 detach됐어도 I 경로를 통해 gradient가 남을 수 있다. ‘LoRA grad가 있다’만으로 CA 내부 미분까지 통과했다고 주장하지 않는다. 현재 runner는 self_attn/cross_attn/ffn의 full backward hook에서 입력·출력 gradient의 finite/norm을 기록한다. cross 입력 derivative가 비영인지 검사해 block 외부 residual만 통과한 경우를 구분한다. context.requires_grad=True로 앞257 image와 뒤512 text의 gradient norm도 각각 검사하고, loss graph의 FA backward node3개를 확인한다. 개별 K/V projection hook을 설치한 것은 아니며 해당 수준의 계측을 했다고 주장하지 않는다. hook은 스칼라만 남기고 tensor/graph를 누적 보관하지 않는다. 입력 x gradient는 앞쪽 block으로 전달할 수 있는 미분 연결의 구성요소 증거이며, 앞39개 block을 실행했다는 뜻은 아니다.

LoRA는 `W=W0+(alpha/r)BA`, q/v 각각 rank4다. Bzero에서 첫 A gradient0은 정상일 수 있다. 후속 A/B gradient와 실제 delta, optimizer 객체 집합, base hash, fresh reload를 함께 본다. `requires_grad=False`, `no_grad`, `eval`은 서로 다른 개념이다. [PyTorch autograd](https://docs.pytorch.org/docs/2.14/notes/autograd.html#locally-disabling-gradient-computation), [LoRA v2](https://arxiv.org/abs/2106.09685v2).

## 4. 정확한 dtype와 작은/큰 shape

공식 norm은 내부 FP32 계산을 사용하고 modulation/gate/residual에는 FP32 경계가 있다. 저장 F32 state 중 Linear weight/bias만 BF16로 내리고 norm/modulation은 F32를 보존한다. 먼저 모두 BF16으로 내렸다 norm만 FP32로 되돌리면 잃어버린 정밀도가 복원되지 않는다. source에는 backward를 끊는 no_grad/detach가 없지만 실제 추가 wrapper와 hook도 별도로 검사해야 한다.

| 입력 | 작은 fixture | 조건부 긴 fixture |
|---|---|---|
| x, target | `[1,36,5120]` | `[1,12992,5120]` |
| context | `[1,769,5120]` | 동일 |
| e | `[1,6,5120]` FP32 | 동일 |
| token 분할 | ref16/video16/pose4 | ref1792/video8960/pose2240 |
| grid | T1/H4/W4 | T5/H56/W32 |
| optimizer | 최대3 update | 없음, backward1회만 |

RoPE는 animation/H0이며 pose W offset120을 보존한다. Q/K normalization은 head reshape 이전5120축이다. Q/K RoPE는 complex 연산 후 FP32 반환, FA wrapper는 Q/K/V를 half dtype에 맞춘다. 이를 BF16 kernel과 FP32 residual 전체가 모두 같은 dtype이라는 말로 줄이지 않는다. [RoPE/SA](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/modules/model_scail2.py#L31-L305), [FA wrapper](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/modules/attention.py#L24-L136).

## 5. 자원 산술과 실측의 차이

N12992,D5120,F13824일 때 ND개 FP32 tensor 하나는266,076,160 bytes(0.2478GiB), NF개 FP32는718,405,632 bytes(0.6691GiB)다. 단순 self-attention score `[1,40,N,N]` FP32는25.152GiB지만 공식 FA 경로는 이 전체 score를 저장하는 단순 구현이 아니다. 반대로 score를 피한다고 QKV·norm·RoPE·FFN backward activation이 사라지는 것도 아니다.

계산용 보수적 예산 후보로 `16×ND×4 + 4×NF×4 + 4×ND×8`을 두면 activation 약8.624GiB다. 이는 여러 FP32 잔여값·FFN saved tensor·RoPE 복소/배정도 임시값을 여유 있게 포함하려는 **휴리스틱**이지 코드가 보장하는 최대치가 아니다. 실제 base residency, source F32 사본, BF16 cast, gradient와 allocator/kernel workspace 여유를 별도로 포함해야 한다. 중복 lifetime을 정확히 모르므로 이 수치만으로16GiB 통과를 선언하지 않는다. 실제 사전 gate와 관측값이 우선이다.

long 단계는 optimizer와 작은 graph를 지운 뒤 수행하므로 training 전체 optimizer footprint를 측정하지 않는다. memory.max16GiB는 cgroup charged memory의 제한이며 UMA CUDA 전체 사용량의 수학적 상한이 아니다. CUDA allocated/reserved/peak, RSS, cgroup, 시스템 available을 서로 더하지 않고 함께 기록한다. 단일 block peak×40 계산은 전체 모델 학습 가능성의 증명이 아니다. 여러 층에 adapter가 있으면 더 앞에서부터 graph/activation이 필요하고, 마지막 층만 학습하는 실제 pipeline은 앞층 cache/no_grad 가능성도 별도 계약으로 검증해야 한다.

## 6. 실제 관측과 수용 경계

실제 `reports/result.json`, `updates.json`, `long-result.json`을 읽어 두 단계의 PASS를 확인했다. 작은 stage는8 block forward/3 backward/3 optimizer update, 긴 stage는1 forward/1 backward/0 update로 총9 forward/4 backward/3 update다. 각 backward graph에 FA2 node3개가 있었으며 self/cross/FFN input·output gradient와 image/text context gradient가 finite·비영이었다. 작은 첫 step의 cross input norm은0.0219127, FFN input norm은0.329816, image/text context norm은0.00454079/0.0706191이었다. 따라서 residual 경로만으로 gradient 존재를 추론한 판정이 아니다.

작은 MSE는7.10797405→7.10766220→7.10631132였고, Bzero/baseline·fresh reload·adapter OFF 비교의 max error는 모두0이었다. 첫 A gradient0 이후 후속 A/B update가 관측됐고, 기반 runtime 값과 선택 저장 payload가 보존됐다. 이 loss 감소는 동물·영상 품질 개선이 아니다.

| 실제 stage | 시간 | CUDA peak allocated | CUDA peak reserved | 범위 |
|---|---:|---:|---:|---|
| small | 24.2899초 | 976,793,088 bytes | 별도 receipt 참조 | update3·reload/OFF 포함 |
| long | 6.80278초 | 6,244,993,024 bytes | 7,249,854,464 bytes | synthetic12992token, optimizer 없음 |

시간에는 validation·동기화·hash 등 runner 작업이 포함되며 pure kernel benchmark가 아니다. 긴 stage는 입력 gradient norm0.0829872, image/text gradient norm0.00448821/0.0600237을 기록했다. adapter와 base는 변하지 않았으며 long optimizer update는0이다. 사전 estimate13,830,425,600 bytes는 허용 gate용 휴리스틱이었지 측정 peak의 예언이나 상한 증명이 아니다. CUDA peak와 cgroup/RSS/OS accounting을 더하지 않는다. 이 결과는 단일 block 조건에 한정된다. 현재 구현의 재현 연결은 [`block_runner.py`](../experiments/B-019-transformer-block-backward/code/block_runner.py)의 `install_hooks`, `partition_gradients`, `run_long` 및 `configs/smoke.json`이다. 작은 x/target은 B018 저장 fixture를 읽으며 새 조건의 context_seed는20261025, 긴 수치 입력 long_seed는20261026이다. 코드·config SHA는 `reports/code-freeze.json`, CPU 증거는 `reports/cpu-contract-validation.json`과 `reports/cpu-tests-final.log`에 연결된다. 이 경로는 새 실험 wrapper이며 공식 SCAIL API에 원래 존재하는 학습 runner라고 부르지 않는다. synthetic MSE는 `mean((block(x,e,c)-target)^2)`이며 σ 경로·noise−Y target이 없으므로 FM loss가 아니다. B018과 이번은 함수가 달라 loss 숫자를 모델 개선량으로 비교할 수도 없다. FULL_MODEL_TRAINING, VIDEO_QUALITY, IDENTITY_POSE_DISENTANGLEMENT는 NOT_RUN이다.

다음 결정은 더 많은 block/token 감사 시리즈가 아니다. 허용된 실제 Y와 R/D·scene 분할이 없으므로 현재 DATA_PENDING을 유지한다. 자료와 자원 근거가 함께 준비됐을 때만 별도 한정 실제 target/FM pilot을 설계한다. B017의 source 권리 UNKNOWN·실제 Lab Y 부재를 synthetic gradient 성공으로 없애지 않는다.

## 이해 확인 질문

1. LoRA gradient가 비영이면 frozen cross-attention 미분도 검증됐는가?
2. 긴 fixture backward가 통과하면 같은 길이40block LoRA training도 fit하는가?
3. projection과 norm을 모두 BF16으로 바꿨다가 norm만 FP32로 복원하면 원래 경계와 같은가?

## 별도 해설

1. 아니다. residual I 경로가 우회할 수 있다. cross/FFN 입력 derivative와 image/text context gradient를 구분한 증거가 필요하다. 현재 runner는 이 범위를 계측하며 개별 K/V hook은 아니다.
2. 아니다. 여러 layer의 activation lifetime, optimizer/caches/encoder residency와 저장 정책이 다르다. 이번 long은 optimizer도 없다.
3. 아니다. 최초 BF16 round-off로 사라진 값은 FP32로 다시 바꿔도 돌아오지 않는다. 원 F32에서 norm/modulation을 직접 보존해야 한다.
