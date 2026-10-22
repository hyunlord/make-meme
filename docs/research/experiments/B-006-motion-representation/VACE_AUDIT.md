# B-006 — 기존 VACE 조건 경로와 Spark 환경 감사

**판정:** 기존 VACE의 RGB 영상·마스크·참조 입력 경로는 실제 작동한다. 그러나 임의의 동물 관절 ID/가시성/접촉을 학습 없이 이해하는 조건 인터페이스는 확인되지 않았다. 공식 pose 제어 기능이 없다는 뜻은 아니다. 이번에는 다운로드·설치·모델 추론·학습을 하지 않았다.

## 고정 코드와 입력 의미

실행 코드 기준은 DiffSynth `f39d731a3e318d25b725eb3389cfddb184619842`, 가중치는 Wan2.1-VACE-1.3B revision `574e6a744642ce3bee319afc31496b88bde8aac4`다. 추가로 공식 VACE 사용자 가이드와 annotator 코드를 HEAD `48eb44f1c4be87cc65a98bff985a26976841e9f3`에 고정해 읽었다. 이 저장소를 실행 환경으로 교체하지 않았다.

|입력/단계|실제 코드 의미|이번 판단|
|---|---|---|
|`vace_video`|PIL RGB 프레임을 정규화한 뒤 video VAE에 전달|source RGB나 skeleton render를 **형식상** 전달 가능; 의미적 동작 전이는 별도|
|`vace_video_mask`|흰색=생성할 영역, 검정=보존할 영역. 없으면 전부 1|여기서 mask는 keypoint visibility나 foot contact가 아님|
|inactive/reactive|정규화 video×(1−mask)와 video×mask를 각각 VAE encode, 16+16채널 결합|full-white면 inactive 입력은 정규화 공간 0. RGB 검정 입력과 다름|
|`vace_reference_image`|각 참조를 VAE encode하여 시간축 앞에 추가, reactive·mask 해당 부분은 0 padding|전용 animal identity encoder나 animal skeleton retargeter가 아님|
|VACE context|16+16+64채널 → Conv3d patch embedding → attention blocks → DiT hint|관절별 이름·좌우·visibility·접촉을 받는 독립 tensor 인자가 없음|

근거: [VACE unit L685–735](https://github.com/modelscope/DiffSynth-Studio/blob/f39d731a3e318d25b725eb3389cfddb184619842/diffsynth/pipelines/wan_video.py#L685), [VACE model L27–74](https://github.com/modelscope/DiffSynth-Studio/blob/f39d731a3e318d25b725eb3389cfddb184619842/diffsynth/models/wan_video_vace.py#L27). `input_video`와 `vace_video`는 구별해야 한다. 학습의 `input_video`는 target 영상을 latent로 만드는 경로이며, `vace_video`는 조건이다. source RGB를 후자에 넣는 것만으로 source appearance를 제거한 motion-only driving이 되지 않는다.

## 공식 지원 task와 동물 skeleton의 차이

공식 가이드는 depth/flow/gray/pose/scribble 제어와 reference·masked editing 조합을 설명한다. Animate Anything도 reference와 pose의 조합으로 기술한다. 따라서 “VACE는 pose를 지원하지 않는다”는 결론은 잘못이다. 다만 해당 가이드는 고정 checkpoint의 세부 훈련 데이터별 비율이나 동물 직립 pose의 성능을 입증하지 않는다. [고정 사용자 가이드](https://github.com/ali-vilab/VACE/blob/48eb44f1c4be87cc65a98bff985a26976841e9f3/UserGuide.md#L33).

실제 공식 pose annotator는 DWPose Wholebody를 호출하고 body 앞 18점, 얼굴·손 점들을 분리해 색 skeleton 영상으로 렌더한다. 우리 동물의 어깨·골반·네 사지·꼬리·contact schema와 동일하지 않다. 임의 animal keypoint heatmap의 채널 수를 RGB로 줄여도 학습된 관절 의미와 색/연결 규약까지 맞는 것은 아니다. [PoseAnnotator L35–83](https://github.com/ali-vilab/VACE/blob/48eb44f1c4be87cc65a98bff985a26976841e9f3/vace/annotators/pose.py#L35).

|표현|형식상 입력|학습된 의미/우리 동물 적용 근거|
|---|---|---|
|기존 Canny RGB|가능, B003–005 실제 실행|입력 영향은 확인, Lab identity와 원본 춤 동시 수용 0/8|
|공식 human pose render|공식 task·annotator 확인|비정상 직립 동물로의 일반화는 미확인|
|새 animal skeleton/heatmap|RGB render로 전달 자체는 가능|직접 지원·학습 분포·성능 미확인; 바로 대체 생성 계획으로 채택하지 않음|
|source RGB video|공통 VACE 조건/편집 경로로 가능|identity·배경 정보도 보존. animal motion만 분리하는 end-to-end driving 학습 여부 미확인|

새 표현을 쓰려면 기존 pose 규약과의 의미 대응 증거 또는 해당 표현–target 영상의 paired 학습/adapter 검증이 필요하다. 이것이 반드시 새 학습으로만 가능하다는 증명도 아니다. 현재 증거로 zero-shot 효과를 약속할 수 없다는 판단이다. 가시성 null을 검은 픽셀로 그려 전달해도 모델이 “관측 불가”라는 의미를 자동으로 받는 것은 아니다.

## 실제 관측과 코드 유도

B003–005의 저장된 실제 sampler context hook에서 확인한 값이다. B006에서 새 forward를 하지 않았다.

|tensor|shape|증거|
|---|---|---|
|noise|1×16×6×36×64|기존 실제 hook|
|positive/negative text|각 1×512×4096|기존 실제 hook|
|VACE context|1×96×6×36×64|기존 실제 hook|
|reference prefix|1×96×1×36×64|기존 실제 slice hash|
|inactive/reactive|각 1×16×5×36×64|기존 실제 slice hash|
|mask|1×64×6×36×64|기존 실제 slice hash|
|RGB video 정규화|1×3×17×288×512|코드 유도; 새 GPU 관측 아님|

17프레임의 시간 latent 5개에 참조 1개가 추가된다. 24fps의 실제 영상 시간과 diffusion noise time은 다르다. mask의 64채널은 8×8 공간 재배열이며 64개 관절이 아니다. [이전 실제 검증](../B-005-factorial/run_summary.json).

## 학습·LoRA 인터페이스와 부족한 데이터

공식 DiffSynth 예제는 `video`, `vace_video`, `vace_reference_image`, prompt를 사용한다. target `video` → VAE clean latent, condition `vace_video`/reference → VACE context다. [train.py L68–113](https://github.com/modelscope/DiffSynth-Studio/blob/f39d731a3e318d25b725eb3389cfddb184619842/examples/wanvideo/model_training/train.py#L68).

`FlowMatchSFTLoss`는 target latent에 noise를 섞고 scheduler target과 예측 간 float32 MSE에 시간 가중치를 곱한다. 이는 keypoint 좌표 MSE나 identity-specific loss가 아니다. [loss.py L5–33](https://github.com/modelscope/DiffSynth-Studio/blob/f39d731a3e318d25b725eb3389cfddb184619842/diffsynth/diffusion/loss.py#L5). scheduler 규약은 `zσ=(1−σ)z+σε`, target `ε−z`, sampling update `z←z+(σnext−σ)v`다. [scheduler L437–472](https://github.com/modelscope/DiffSynth-Studio/blob/f39d731a3e318d25b725eb3389cfddb184619842/diffsynth/diffusion/flow_match.py#L437).

공식 LoRA 설정은 base module `vace`, target suffix `q,k,v,o,ffn.0,ffn.2`, rank32, lr1e−4다. [실제 shell 예제 L3–19](https://github.com/modelscope/DiffSynth-Studio/blob/f39d731a3e318d25b725eb3389cfddb184619842/examples/wanvideo/model_training/lora/Wan2.1-VACE-1.3B.sh#L3). 새로운 animal representation에 대한 조건–target paired dataset과 독립 장면 검증을 마련하지 않고 이 인터페이스의 존재만으로 동물 동작 학습 성공을 주장할 수 없다. 원본의 다른 개체 영상을 실제 Lab target으로 취급하면 안 된다. B001 학습 배선 검증과 Lab 동작 일반화도 별개다.

## Spark 현재 상태 및 SCAIL와의 경계

2026-10-22 05:28 UTC 읽기 전용 관측: Ubuntu24.04.4/aarch64, NVIDIA GB10 driver580.126.09. 통합 MemTotal128,524,300,288 bytes, MemAvailable87,902,375,936 bytes, swap0, 가용 디스크1,215,876,308,992 bytes. 기존 ComfyUI 프로세스가 GPU3271MiB를 점유하며 queue0/0이었다. 중단하거나 변경하지 않았다. `nvidia-smi`의 GPU memory.total/used는 N/A였으므로 이를 별도128GB로 합산하지 않는다.

기존 격리환경은 Python3.12.3, torch2.14.0+cu130, CUDA build13.0. `nvidia-smi` compute capability12.1, PyTorch built arch list는 sm80/90/100/110/120이다. 이는 특정 외부 attention kernel의 실제 GB10 지원 검증이 아니다.

**현재 `flash_attn`과 `flash_attn_interface`는 distribution metadata와 module spec 모두 없다.** SageAttention2.2.0과 Triton3.8.0은 있지만 직접 FA2 import의 대체물이 아니다. 이번에는 FA2 import·빌드·kernel test를 하지 않았다. SCAIL 코드가 FA2를 필수로 직접 import한다면 현재 격리환경 그대로는 해당 의존성이 충족되지 않는다. 설치 가능성, ARM64 wheel/build, Blackwell kernel, 전체 추론 메모리·속도 및 LoRA 실행 가능성은 **UNKNOWN**이다. 기존 VACE SDPA 실행 성공이나 다른 GPU의 공개 성능을 SCAIL Spark 실측으로 전용하지 않는다.

모델 inventory는 기존 B001 models 디렉토리만 읽었다. 파일30개의 경로/크기 기록이며 새로운 모델 설치·대형 hash 반복은 하지 않았다. 이 범위에서 확인한 VACE 자산 외에 사용자 전체 디스크의 SCAIL 존재 여부를 주장하지 않는다. A의 기존111파일은 다시 해시 비교하여 모두 동일했다. private reports에 환경·attention metadata·inventory·A 보존 근거를 남겼으며 공개 문서에는 개인 절대 경로를 넣지 않았다.

**다음 판단에 주는 정보:** VACE에 동물 skeleton PNG를 임의 대입하는 방식은 아직 의미적 연결이 미확인이다. RGB driving에 맞춰 학습된 경로를 비교할 이유가 있지만, SCAIL 후보의 FA2/ARM64/GB10 의존성 검증은 별도 승인 단계에서 해결해야 한다. B006에서는 설치나 생성으로 자동 확대하지 않는다.
