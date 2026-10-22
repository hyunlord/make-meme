# B-007A 모델 저장·변환·attention 감사

2026-10-22 재확인. 이 문서는 공식 소스와 소형 HTTP metadata 조사다. 새 가중치 다운로드·모델 로딩·diffusion·학습은 0회다. 커널 실행 결과는 별도 실행 담당자의 최종 기록과 결합한다. **실제 모델 peak memory는 NOT_MEASURED**다.

## 실제 attention 계약

[모델 self attention](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/modules/model_scail2.py#L276)은 projection과 Q/K RMSNorm, RoPE 뒤 `flash_attention`을 직접 호출한다. [I2V cross attention](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/modules/model_scail2.py#L347)은 text와 CLIP image에 각각 호출하고 결과를 더한다. generic `attention()`의 SDPA fallback을 거치지 않는다.

|항목|고정 코드의 값|
|---|---|
|Q/K/V wrapper layout|`[B,Lq 또는 Lk,heads,head_dim]`|
|14B config|hidden5120, heads40, head_dim128, layers40|
|dtype|기본 BF16. FP16/BF16 입력은 유지하고 다른 dtype은 기본 dtype으로 변환|
|flags|causal=False, dropout_p=0, window_size=(-1,-1), deterministic=False|
|scale|softmax_scale=None → backend 기본 1/√128; q_scale=None|
|lengths|self는 k_lens=seq_lens, cross는 context_lens; image cross는 k_lens=None|
|FA 선택|FA3 import 가능하면 우선, 아니면 FA2 존재 assert; varlen 함수 호출|

[wrapper](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/modules/attention.py#L24)는 CUDA와 head_dim≤256을 검사한다. 입력을 `(sum lengths,heads,128)`로 flatten/pack하고 int32 cumulative lengths를 전달한 뒤 원래 shape로 복원한다. 작은 BF16 smoke는 동일 head_dim·noncausal·unequal cross lengths·실제 length packing을 확인해야 한다. 작은 커널 성공은 12,992-token 모델 실행의 자원 수용이 아니다.

공식 FlashAttention main을 별도 조회해 `2bdeddd15af6f1c44cd41e6f5b08b9e544398397`로 고정했다. [setup.py](https://github.com/Dao-AILab/flash-attention/blob/2bdeddd15af6f1c44cd41e6f5b08b9e544398397/setup.py#L102)는 CUDA≥12.9에서 명시적으로 SM121 gencode를 생성한다. 하지만 [기본 architecture 목록](https://github.com/Dao-AILab/flash-attention/blob/2bdeddd15af6f1c44cd41e6f5b08b9e544398397/setup.py#L75)은 `80;90;100;110;120`으로121이 없다. 이는 빌드 코드에 SM121 경로가 있다는 근거이며 ARM64 wheel·현재 torch ABI·실제 GPU kernel 성공을 보장하지 않는다. README의 [FA3 Hopper / FA4 Blackwell 설명](https://github.com/Dao-AILab/flash-attention/blob/2bdeddd15af6f1c44cd41e6f5b08b9e544398397/README.md#L29)도 SCAIL이 요구하는 FA2/3 import API와 별도로 봐야 한다. FA4를 조용히 backend로 바꾸지 않는다.

## HF 파일 metadata 재확인

[HF revision](https://huggingface.co/zai-org/SCAIL-2/tree/150cc0ca4e98e50e60b9295dacde39442fdccab2)은 B-006과 동일하다. 파일 자체를 다운로드하거나 payload SHA를 재계산하지 않았다.

|구성|bytes|
|---|---:|
|SAT `model/1/fsdp2_rank_0000_checkpoint.pt`|65,582,563,395|
|UMT5 encoder|11,361,920,418|
|CLIP visual|2,528,485,611|
|VAE|507,609,880|
|tokenizer 4파일|21,454,081|
|README + .gitattributes|4,889|
|비선택 파일 합계|80,002,038,274|
|DPO LoRA (선택)|1,227,381,060|
|relighting LoRA (선택)|1,227,381,060|
|전체 repository metadata 합계|82,456,800,394|

코드는 Apache-2.0, HF card metadata는 MIT이며 구성요소별 권리와 서비스 사용 허용을 자동 통합하지 않는다. 모델 이름14B는 전체 pipeline parameter 수나 다운로드량을 나타내지 않는다.

## 변환은 왜 별도 위험인가

[convert.py182–189](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/convert.py#L182)는 `checkpoint=torch.load(path)` → `checkpoint["module"]` → key mapping → `save_file`이다. `map_location`, `mmap`, dtype 축소를 지정하지 않는다. 저장된 storage device에 따른 복원과 torch 버전의 load 기본 동작도 영향을 줄 수 있다. payload를 읽지 않았으므로 실제 storage device/dtype/optimizer 포함 여부는 미확인이다. [PyTorch2.14 torch.load 문서](https://docs.pytorch.org/docs/2.14/generated/torch.load.html)에 따르면 storage를 먼저 CPU에 역직렬화한 뒤 저장 당시 device로 옮기며, map_location으로 이 동작을 바꿀 수 있다. 따라서 CUDA 저장 checkpoint라면 변환만 하려 해도 GPU 복원과 일시적인 추가 storage 비용이 생길 수 있다. 이번에는 converter를 수정하거나 실행하지 않았다.

[변환 mapping](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/convert.py#L172)은 새 dictionary를 만들지만 tensor 전체를 clone하지 않는다. QKV/KV 분리는 `chunk` view이며 일반 key는 같은 tensor를 참조한다. 따라서 dictionary 두 개를 이유로 무조건 두 배의 tensor resident memory라고 계산하면 틀린다. 반대로 원본 `checkpoint`는 저장 완료까지 살아 있으므로 불필요한 checkpoint 내용이 있더라도 자동 해제되지 않는다. serializer의 CPU 이동·contiguous 처리·임시 byte buffer 비용은 실제 설치 버전과 tensor 배치에 따라 달라지므로 0으로 가정하지 않는다.

표기: S=원본 tensor storage의 실제 resident bytes, E=checkpoint 부가 객체, W=직렬화 임시 작업공간, C=파일 cache/allocator/런타임 비용. peak의 계획식은 `S+E+W+C`이며 실제 중첩과 계수는 **UNKNOWN**이다. 파일65.58GB 자체를 S의 정확한 값이나 peak 상한으로 쓰지 않는다. 출력 safetensors 크기 O도 아직 미측정이다.

디스크에는 최소한 비선택 입력80.002GB와 변환 출력 O가 동시에 남는다. `80.002 + 65.583 ≈145.585GB`는 **출력 크기를 입력 checkpoint와 같다고 가정한 공간 시나리오**이며 상한 보장이 아니다. 다운로드 임시 파일·별도 캐시·filesystem 여유는 추가다. 기존50GB 다운로드 예산으로 시작할 수 없고 B-007B 별도 승인이 필요하다.

## Resident와 activation을 나눈다

14×10⁹개 parameter가 모두 BF16이라는 단순 예라면 weight만28GB다. 실제 총 parameter 수·dtype가 확인되지 않았고 T5/CLIP/VAE·mask/history/conditioning도 있으므로 이것은 SCAIL 총 메모리 예측이 아니다. [실제 token 구성](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/modules/model_scail2.py#L741)에서 H512,W896,T17, reference1장의 예상 N은12,992이다. self QKV BF16 세 tensor만 `3×1×12992×5120×2=399,114,240 bytes`다. 이는 임시 projection/RoPE·MLP·attention workspace·decode를 제외한다.

모든 heads의 N×N score를 BF16으로 materialize하면 `40×12992²×2=13,503,365,120 bytes`가 된다. FlashAttention은 이 전체 score를 저장하지 않고 tile별 online softmax로 계산해 IO와 저장량을 줄인다. dense attention의 pair 계산량 자체를 선형으로 만드는 것은 아니다. 이 단순 score 계산을 실제 Flash peak라고 쓰면 안 된다. [원 논문](https://arxiv.org/abs/2205.14135).

통합 메모리에서는 CPU offload가 별도의 추가128GB를 만들지 않는다. GPU allocated/reserved, 시스템 MemAvailable, CPU storage, file cache를 같은 총자원 관점에서 본다. 현재 시스템 관측은 최종 RESULTS의 fresh 계측을 참조한다. 작은 커널과 실제 모델 로딩·변환·full attention·영상 수용은 각각 별도 판정이다.

## 이번 실측: 자원 기준선과 CPU mask

Spark 실행 담당자의 2026-10-22 06:07:46 UTC 관측은 MemTotal128,524,300,288 bytes, MemAvailable95,932,358,656 bytes, swap total/used0, 디스크 가용1,228,038,549,504 bytes, GB10 utilization0%, nvcc13.0.88이다. unified memory 환경의 nvidia-smi memory.used는 N/A이므로 0bytes로 읽지 않는다. 06:10:56 UTC의 다음 compilation 기준선 MemAvailable은94,136,250,368 bytes다. 서로 다른 시점의 값이며 모델 peak 측정이 아니다. 설치·커널 결과는 최종 RESULTS에서 따로 보고한다.

실제 입력 preflight는 세로 reference 방향 때문에 H896/W512를 사용했다. 앞 절 H512/W896은 token 수 설명을 위한 코드 예이며, 동일 면적의 H/W 교환은 이 token 수를 바꾸지 않는다. 하지만 crop의 시야는 달라진다. [INPUT_PREFLIGHT](INPUT_PREFLIGHT.md)에 동일 RGB/mask geometry와 남은 경계 오염을 기록했다.

[실제 helper 검사](MASK_TENSOR_CHECK.json)는 Mac CPU PyTorch2.14.1에서 실행했다. reference 입력 `(3,1,896,512)` → 출력 `(28,1,112,64)`, driver `(3,17,896,512)` → bilinear half `(3,17,448,256)` → helper 출력 `(28,5,56,32)`다. **driver를 먼저 bilinear half한 다음 helper의 additional_spatial_downsample=1**을 사용한다. helper에2를 넣는 방식과 같다고 가정하면 안 된다. resize 전/후 threshold 순서가 바뀌기 때문이다.

두 출력은 float32이고 red slot `[1,8,15,22]`만 활성이다. reference fractional cells1,052개, driver2,380개이며 범위0~1이다. bright는 정규화된225보다 strict greater-than이다. area 평균의 분수 점유율을 binary로 다시 threshold하지 않았다. 이것은 색상 packing 실행 증거이며 full pipeline import·VAE·모델 실행·경계 정확도 수용은 아니다.
