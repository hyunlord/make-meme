# B018 공식 attention 계약 감사

소스: Wan commit `78fe19576bb06be96c2375e088574a262a300edb`. 이 문서는 소스 판독이며 GPU backward 결과가 아니다. 실행 관측은 별도 receipt로 갱신한다.

## 실제 계산 경로

[WanSelfAttention L251–305](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/modules/model_scail2.py#L251-L305): 입력 x는 `[B,S,dim]`이다. docstring의 4D 설명보다 실제 q/k/v Linear 입력과 view를 따른다. q,k,v,o는 모두 bias가 있는 dim→dim Linear다. Q/K normalization은 head별128이 아니라 reshape 전 전체 dim5120 RMSNorm이다. 결과를 `[B,S,40,128]`로 바꾸고 Q/K만 RoPE에 통과시킨다. V에는 RoPE를 적용하지 않는다.

[RoPE helpers L31–219](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/modules/model_scail2.py#L31-L219): d128의 complex64채널을 T22/H21/W21로 나눈다. ref/video는 complex unit multiplier, pose는 full spatial grid의 실수/허수 각각을 2×2 average pool한 multiplier다. 따라서 pose multiplier를 단순 unit rotation과 동일시하지 않는다. helpers는 FP64/complex128 계산 후 FP32를 반환한다.

공식 [offset L825–855](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/modules/model_scail2.py#L825-L855)에서 animation(`replace_flag=False`), additional_ref0이면 ref T/H/W=(0,0,0), video=(1,0,0), pose=(1,0,120)이다. toy T1/H4/W4에서 ref16+video16+pose4=36이고 ref/video T slice는 서로 다르다. pose W에는120 offset이 유지되므로 frequency table은 적어도 W index123까지 있어야 한다. 이 token grid는 실제17프레임 latent가 아니다.

## FA wrapper와 dtype

[attention.py L24–136](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/modules/attention.py#L24-L136)는 CUDA와 head_dim≤256을 검사한다. half 변환 뒤 Q/K를 V dtype에 맞춘다. RoPE가 반환한 FP32 Q/K와 BF16 V가 들어오면 backend Q/K/V는 BF16이지만 wrapper output은 원래 Q dtype인 FP32로 되돌아온다. 이후 o projection의 BF16 가중치와 연결하는 autocast 경계도 실제 실행 코드에서 확인해야 한다.

기본 dropout0, causal=False, window=(-1,-1), deterministic=False, softmax_scale=None이다. q_lens가 없으면 전체36이며 k_lens는 `[36]` int32 CUDA로 일치시켜야 한다. FA3 import가 있으면 version=None은 FA3를 우선한다. 현재 FA2 실행 판정에는 availability와 실제 호출 backend 기록이 필요하다. WanSelfAttention은 `attention()`의 SDPA fallback이 아니라 `flash_attention()`을 직접 호출한다. FA backward 실패를 SDPA로 교체한 결과로 덮으면 안 된다.

## 판정할 경계

CPU 계약 fixture, FA forward, FA backward, adapter update, frozen-base hash, fresh reload는 각각 다른 증거다. 작은36token/한 self-attention의 성공은 전체40block/실제 영상 training 메모리·학습 목적·개체 분리를 증명하지 않는다. 원 FP32 checkpoint와 BF16 실행 cast의 hash가 다른 것은 자연스럽다. 불변성 비교는 실행 cast 직후와 update 후 같은 tensor를 대상으로 한다.

## 실제 header 확인

선택 prefix `blocks.39.self_attn.`의10 tensor, 모두 F32, payload419,553,280 bytes를 `reports/header-discovery.json`에서 확인했다. 네5120×5120 weight와 네5120 bias, 두5120 RMSNorm weight다. 로컬 pinned model_scail2.py 및 attention.py SHA는 receipt의 Spark 파일 SHA와 일치했다. payload 접근·GPU cast·backward 성공은 이 header 확인과 별개다.
