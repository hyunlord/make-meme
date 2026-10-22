# B-006 모델·입력 경로 감사

조사일: 2026-10-22. **소스·모델 저장소 metadata 조사만 수행했다. 새 가중치 다운로드, 설치, 모델 실행, 학습은 0회다.** SCAIL-2의 현재 Spark 실행 경로는 필수 FlashAttention 의존성 부재로 **BLOCKED**이며, 설치 후 실행 메모리·품질은 **UNKNOWN**이다. 이는 모델이 Spark에서 원천적으로 불가능하다는 판정이 아니다.

## 1. 고정한 공식 자료

|자료|고정 revision / 근거|
|---|---|
|SCAIL-2 `wan-scail2`|`78fe19576bb06be96c2375e088574a262a300edb`|
|SCAIL-2 `sat-scail2`|`ac63f8eb369e2f4fac2ce273ead0ae7e602c3919`|
|공식 HF 가중치 metadata|`150cc0ca4e98e50e60b9295dacde39442fdccab2`|
|기존 DiffSynth-Studio|`f39d731a3e318d25b725eb3389cfddb184619842`|

두 Git branch의 SHA를 확인하고 필요한 소스만 읽었다. [공식 논문 v3](https://arxiv.org/abs/2606.10804v3)은 latent visual input을 직접 결합하는 motion transfer와 MotionPair-60K 합성 학습 자료, mask conditioning/RoPE, Bias-Aware DPO를 설명한다. 이 논문의 결과는 이번 반려견·Spark 실측이 아니다.

## 2. SCAIL-2의 실제 입력: `--pose`가 반드시 skeleton은 아니다

[SAT README](https://github.com/zai-org/SCAIL-2/blob/ac63f8eb369e2f4fac2ce273ead0ae7e602c3919/README.md#L32)는 end-to-end 모드에서 `rendered_v2.mp4`가 driving RGB의 사본이며, pose 모드에서는 SMPL render라고 구분한다. 일상 추론은 Wan branch, 논문 재현·학습은 SAT branch를 안내한다.

Wan의 공개 entrypoint는 `generate.py`다. 필요한 입력은 reference RGB `--image`, reference color mask `--mask_image`, driving RGB 또는 pose render `--pose`, driving color mask video `--mask_video`, 완성 영상 내용을 서술한 `--prompt`다. 파일 존재 검사와 RGB decode/resize/정규화 후 pipeline에 전달한다. [실제 입력 경로](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/generate.py#L253).

**VACE의 full-white mask를 그대로 재사용하면 안 된다.** 공식 mask는 검정=배경 비가시, 흰색=배경 가시, 색=인물/동물 영역의 대응 ID다. 같은 개체의 reference/driving 영역에 일관된 색을 사용해야 한다. 동물 사용을 위해 human NLF/DWPose를 반드시 돌려야 하는 것은 아니다. RGB driving은 그 pose 추정 단계를 우회하지만 올바른 mask 자료는 여전히 필요하다. 공식 자동 전처리의 SAM3 등 추가 모델은 이번에 설치하거나 실행하지 않았다. [공식 mask 설명](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/README.md#L84).

실제 mask 함수는 RGB threshold로 white/red/green/blue/yellow/magenta/cyan의 7개 채널을 만들고, 공간 area downsample과 4시점 packing으로 28채널을 만든다. **VAE로 mask를 encode하지 않는다.** area 평균이므로 함수 주석의 binary라는 표현과 달리 경계에서는 분수 coverage가 가능하다. [함수](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/utils/scail_utils.py#L106).

외부 Gemini를 쓰는 `prompt_enhancer.py`는 선택 기능이다. B에서는 사용하지 않는다. 사람이/코딩 에이전트가 작성한 텍스트 prompt를 직접 전달하면 되며 외부 생성 서비스가 필수 의존성은 아니다.

## 3. 실제 조건 결합과 예상 shape

[Pipeline](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/scail.py#L286)은 reference를 VAE encode하고, driving은 공간 크기를 절반으로 줄인 뒤 VAE encode한다. reference CLIP visual feature도 별도로 계산한다. [driving encode](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/scail.py#L435), [CLIP](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/scail.py#L335).

예를 들어 공식 예제 크기 H=512,W=896,T=17, reference1장에서는 아래가 **코드에서 유도되는** shape다. 이번 런타임 hook 실측은 아니다.

|값|shape (batch 없는 pipeline tensor 기준)|
|---|---|
|reference latent|`(16,1,64,112)`|
|생성 noise|`(16,5,64,112)`|
|driving RGB latent|`(16,5,32,56)`|
|driving mask|`(28,5,32,56)`|
|reference+생성 mask|`(28,6,64,112)`|

DiT에 들어갈 때 latent16에 known/history mask4를 붙여20채널로 만든다. reference와 생성 영역은 시간축으로 붙이고, driving은 별도 patch embedding 뒤 token축으로 붙인다. 1×2×2 patch라면 reference+생성 token은6×32×56=10,752, driving token은5×16×28=2,240, 합계12,992이다. hidden5120, 40layers/40heads 설정이다. VACE의 96채널 context와 다른 구조이며 단순히 기존 VACE keypoint PNG 슬롯으로 치환하는 방식이 아니다. [모델 결합](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/modules/model_scail2.py#L717), [config](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/configs/config-14b.json).

## 4. 17프레임·해상도·시간축 함정

- 공식 안내는 RGB end-to-end 512p/704p, pose-driven은704p가 더 낫다고 한다. H/W는32 배수다. 기존288p 실험을 SCAIL 공식 품질 조건으로 부르지 않는다.
- `resize_for_rectangle_crop`는 중심 crop을 사용하므로 원본 aspect ratio와 target이 다르면 시야가 바뀐다. 정확한 원본 시야를 유지하려면 향후 전처리에서 비율·padding·변환을 명시하고 모든 mask와 같은 변환을 적용해야 한다. 이번에 수정하지 않았다.
- 짧은 segment는 `keep=floor((T−1)/4)*4+1`로 **내림 절단**한다. 17은 조건을 충족하여 그대로17이다. 일반 입력의 끝을 자동 padding해 보존한다고 설명하면 틀린다. 기본 segment_len81/overlap5이며 긴 입력의 마지막 불완전 segment가 제외될 수 있다. [segment 코드](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/scail.py#L255).
- loader는 모든 프레임을 읽고 fps로 재표본화하지 않는다. 그런데 writer는 `cfg.sample_fps=16`을 사용한다. 우리17프레임24fps를 그대로 넣으면 파일 길이가0.708333초에서1.0625초로 변한다. **향후 24fps 원본 비교에는 출력 fps를 명시적으로 보존하는 최소 수정/설정 기록이 필요하다.** 이번에 적용하거나 영상 생성하지 않았다. [loader](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/utils/scail_utils.py#L26), [writer](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/generate.py#L358), [기본 fps](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/configs/shared_config.py#L18).

## 5. 가중치 크기와 라이선스: resident memory와 구분

[고정 HF revision 파일](https://huggingface.co/zai-org/SCAIL-2/tree/150cc0ca4e98e50e60b9295dacde39442fdccab2)의 API metadata에서 확인한 크기다. 파일 내용 다운로드/해시 재계산은 하지 않았다.

|파일|bytes|선택 여부|
|---|---:|---|
|`model/1/fsdp2_rank_0000_checkpoint.pt`|65,582,563,395|기본 SAT 가중치; Wan 변환 입력|
|`umt5-xxl/models_t5_umt5-xxl-enc-bf16.pth`|11,361,920,418|T5|
|`Wan2.1_VAE.pth`|507,609,880|VAE|
|`models_clip_open-clip-xlm-roberta-large-vit-huge-14-onlyvisual.pth`|2,528,485,611|실제 pipeline가 로드하는 CLIP|
|`umt5-xxl/spiece.model`|4,548,313|tokenizer|
|`umt5-xxl/tokenizer.json`|16,837,417|tokenizer|
|`umt5-xxl/special_tokens_map.json`|6,623|tokenizer|
|`umt5-xxl/tokenizer_config.json`|61,728|tokenizer|
|`model/bias-aware-dpo-lora.pt`|1,227,381,060|선택, 첫 baseline에 자동 추가 안 함|
|`model/relighting-lora.pt`|1,227,381,060|선택, 첫 baseline에 자동 추가 안 함|

현재 metadata의 전체 합계는82,456,800,394bytes, 두 선택 LoRA 제외 합계는80,002,038,274bytes이며 README와 .gitattributes도 포함한다. `model/latest`는 README 도식에는 있지만 현재 metadata 목록에는 없다. Wan 변환은 `.pt`를 로드해 새 safetensors를 저장하므로 추가 디스크와 변환 중 peak 메모리가 필요하다. [convert.py](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/convert.py#L182)는 dtype 축소·스트리밍 변환을 명시하지 않는다. 변환 후 정확한 크기는 미측정이다.

`14B`라는 이름, 디스크 checkpoint 크기, 실제 총 parameter 수, BF16 resident memory, inference activation peak는 서로 다르다. 모델을 로드하지 않았으므로 이번 정확한 parameter 수·dtype 분포·peak 메모리는 UNKNOWN이다. 128GB 통합메모리로 가능하다고 단정하지 않는다. CPU offload도 같은 통합 메모리를 새로 늘려 주지 않는다.

코드 [LICENSE](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/LICENSE)는 Apache-2.0, [HF card](https://huggingface.co/zai-org/SCAIL-2/blob/150cc0ca4e98e50e60b9295dacde39442fdccab2/README.md)는 MIT metadata다. 두 표시와 기반 구성요소/데이터 권리는 별도로 확인해야 하며 이번 조사는 서비스의 법적 이용 수용이 아니다.

## 6. Spark 의존성 판정

Wan requirements는 Python3.10–3.12 안내, torch≥2.4, torchvision≥0.19, diffusers≥0.31, transformers≥4.49, NumPy<2와 **flash_attn** 등을 요구한다. `decord`는 loader가 직접 import하지만 Wan requirements에 명시되지 않는다. cache 도구는 `zstandard`도 직접 import한다. 현재 환경을 그대로 덮어 설치하면 안 된다. [requirements](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/requirements.txt).

중요한 호출 경로: `model_scail2.py`는 `flash_attention`을 직접 import하고 self/cross attention에서 호출한다. 같은 파일군의 일반 `attention()`에는 SDPA fallback이 있으나 **이 모델의 실제 직접 호출은 그 fallback을 지나지 않는다.** FA3가 없으면 FA2 존재를 assert한다. [모델 import/calls](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/modules/model_scail2.py#L11), [FA assertion](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/modules/attention.py#L112).

B-006 환경 확인 담당자의 fresh 읽기 전용 결과: Spark Python3.12.3, torch2.14.0+cu130, compute capability12.1; `flash_attn`과 `flash_attn_interface` distribution/spec 모두 없음. Sage/Triton 설치는 이 import를 대체하지 않는다. 따라서 **현재 그대로의 공식 Wan 실행은 BLOCKED**다. ARM64/Blackwell용 FA 설치·실제 kernel 동작은 이번에 검사하지 않았고 UNKNOWN이다. 이전 VACE의 SDPA 성공을 SCAIL 성공으로 대체하지 않는다.

offload_model, t5_cpu, FSDP 옵션은 코드에 있다. single-process offload 기본True지만 이것은 peak 메모리 실측이나 실행 시간 보장이 아니다. torch의 architecture 목록과 device compute capability 차이만으로 실행 가능/불가를 단정하지 않고 실제 kernel smoke가 필요하다.

## 7. 학습 interface와 loss: 존재와 Spark 실행 가능성을 분리

SAT branch는 `train_video.py`와 DeepSpeed ZeRO-2/FSDP2 예제를 공개한다. 기본 MPI launch는8GPU이며 config는 batch1, accumulation2, BF16 params/FP32 reduction, train_iters1000 등의 예다. 그대로 Spark 한 장에 적합하다고 읽지 않는다. [학습 README](https://github.com/zai-org/SCAIL-2/blob/ac63f8eb369e2f4fac2ce273ead0ae7e602c3919/README.md#L81), [FSDP config](https://github.com/zai-org/SCAIL-2/blob/ac63f8eb369e2f4fac2ce273ead0ae7e602c3919/configs/training/wan_pose_14Bsc_xc_latent_fsdp_example.yaml).

Wan `cache_scail2_wds.py`는 **target/GT video**, driving video, reference, 두 mask, prompt를 받아 VAE latent와 mask를 WebDataset에 저장한다. `video_pth.zstd`, `smpl_render_downsample.zstd`, `ref_frame_pth.zstd`, `latent_sam_mask.zstd`, `latent_ref_mask.zstd` 등 실제 field가 있다. SMPL이라는 field 이름이 RGB driving을 금지하는 것은 아니다. [cache 입력](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/cache_scail2_wds.py#L216).

SAT config는 `RFLoss`를 선택한다. σ는 LogisticNormal sample이며 선택된 schedule_shift는 공간 token 수에 따른 shift다. `input`은 B,T,C,H,W latent; 생성 영역은 `(1−σ)input+σnoise`, history는 깨끗한 input을 유지한다. target은 `noise−input`, loss는 `(1−history_mask)*(1−ocr_mask)`로 가중한 MSE의 전체 원소 평균이다. mask 유효 면적으로 다시 나누는 평균이라고 설명하면 틀린다. [실제 RFLoss](https://github.com/zai-org/SCAIL-2/blob/ac63f8eb369e2f4fac2ce273ead0ae7e602c3919/sgm/modules/diffusionmodules/loss.py#L653), [sigma sampler](https://github.com/zai-org/SCAIL-2/blob/ac63f8eb369e2f4fac2ce273ead0ae7e602c3919/sgm/modules/diffusionmodules/sigma_sampling.py#L110).

LoRA 적용·변환과 SAT generic LoRA 모듈은 있으나, 확인한 공식 FSDP 예제를 완성된 animal-specific LoRA recipe라고 부를 수 없다. 실제 Lab target 동영상도 현재 없다. 다른 개의 원본을 Lab 정답으로 삼아서는 안 되며, frozen base/adapter만 업데이트 여부를 별도 검증해야 한다. 이번 forward/backward/optimizer 검증은 NOT_RUN이다.

## 8. APT·Kirin·기존 VACE와의 역할 비교

|항목|SCAIL-2 RGB driving|기존 VACE-1.3B|APT-36K / Kirin|
|---|---|---|---|
|과제 적합성|reference+실제 driving 영상의 motion transfer라는 직접적 interface|reference+control video/mask; 현재 Canny는 영향 있지만 원본 춤0/8|APT는 추적/pose benchmark, Kirin은 image+text에서3D motion/mesh 생성|
|동물 지원 근거|공식 논문/README의 animal-driving 주장; 우리 직립 개는 미검증|현재 반려견 동작/identity 동시 수용 실패|동물 표현 연구 근거이며 사진 개체를 원본 안무로 교체하는 실행 증거 아님|
|다중 개체|mask color 대응과 multi-reference 코드 있음; 품질 미검증|이번 단일 컷에서 성공 못함; 다중 미검증|이번 배역 문제를 바로 해결하는 interface로 확인 안 됨|
|학습 데이터|공식 합성 MotionPair-60K; 상세 animal 분포는 이 감사에서 미확인|기존 pinned pipeline/code 확보; animal skeleton 조건 학습 근거 미확인|APT 동물 keypoint/track annotation, Kirin 복원3D motion 자료|
|장비|현재 FA dependency BLOCKED, peak UNKNOWN|기존512×288/17프레임 실측 있음; 이를 SCAIL에 대입 불가|설치/실행 안 함|

[APT-36K 논문](https://arxiv.org/abs/2206.05683)과 [공식 저장소](https://github.com/pandorgan/APT-36K)는 동물 keypoint와 시간 추적을 함께 다룬다. 공식 annotation schema와 이번 수동 눈/목/관절 후보를 같은 것으로 간주하지 않는다. 특히 보이지 않는 관절을 보간한 좌표를 관측 ground truth로 만들지 않는다. 저장소의 프로젝트 라이선스를 수집 영상 전체의 서비스 이용 허가로 확대하지 않는다.

[Kirin 공식 페이지](https://kirin-ani.github.io/)는 image+text로 quadruped3D motion과 rigged mesh를 만드는 과제를 설명하며, 조회 시 code release는 아직 진행 중이라고 표시한다. 원본 RGB 영상의 동작을 그대로 reference 개체에 옮기는 공개 inference 경로로 확인된 것은 아니다. 이번에는 데이터도 받지 않았다. 이 차이 때문에 바로 실행할 B-007 후보로 선택하지 않는다.

기존 [VACE unit](https://github.com/modelscope/DiffSynth-Studio/blob/f39d731a3e318d25b725eb3389cfddb184619842/diffsynth/pipelines/wan_video.py#L674)은 RGB control을 받지만, API가 RGB PNG를 받는 사실은 임의 animal keypoint heatmap에 대한 훈련된 해석 능력을 증명하지 않는다. 수동 landmark는 우선 움직임 정보 감사/평가 자료다. skeleton PNG를 바로 넣으면 해결된다는 가정을 배제한다.

## 9. 다음 한 경로

**B-007 후보는 공식 `wan-scail2` RGB driving의 제한된 baseline 하나**다. 단, 현재 BLOCKED를 먼저 해소해야 한다. 별도 승인 하에서 격리 환경의 ARM64/GB10 FlashAttention·video IO 최소 kernel/import 검증 → 디스크/변환 peak 계획과 필요한 모델 파일만 확보 → 공식 single-GPU smoke → 올바른 color masks·aspect·24fps를 기록한 실제 단일 컷 순서가 적절하다. 이는 실행 완료나 다운로드 승인 요청을 이미 받은 것으로 해석하지 않는다.

첫 단계 kernel이 안 되면 중단 원인을 제출하고 모델을 계속 바꾸거나 ComfyUI로 자동 전환하지 않는다. 14B의 성공/학습 가능, 두 반려견 일반화, 자연스러운 동작·Kling 수용은 모두 미검증이다.
