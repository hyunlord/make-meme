# B017 — 공식 training interface 코드 감사

상태: **소스 확인 완료 / cache encoding·model load·backward·optimizer update NOT_RUN**. inference 환경/checkout은 수정하지 않았다. 공식 remote 조회에서 Wan `78fe19576bb06be96c2375e088574a262a300edb`, SAT `ac63f8eb369e2f4fac2ce273ead0ae7e602c3919`를 확인했다. 아래는 이 두 revision의 코드 의미이며 현재 Spark에서 training이 동작한다는 증거가 아니다. 작은 원문·파일 SHA는 private source manifest에 보존한다.

## 1. 실제 진입 경로

[Wan README training](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/README.md#L431-L486)은 case→VAE cache/WDS를 설명한다. 실제 학습은 SAT의 [train_video.py forward_step/training_main](https://github.com/zai-org/SCAIL-2/blob/ac63f8eb369e2f4fac2ce273ead0ae7e602c3919/train_video.py#L254-L332)→`DiffusionEngine.shared_step`→`RFLoss`다. 공개 FSDP example은 batch1, accumulation2, 1000 iterations인 full fine-tuning 예제다. 이 수치는 이번 예산이 아니며 그대로 실행하지 않았다.

## 2. 파일·latent·condition 대응

| case 입력 | WDS 필드 | SAT reader / train 사용 |
|---|---|---|
| `GT.mp4` (Y) | `video_pth.zstd` | `mp4`→x→loss 정답. 사진이나 R을 Y로 대체하지 않음 |
| `rendered_v2.mp4` (D) | `smpl_render_downsample.zstd` | `smpl_render`→`concat_smpl_render`; 이름이 SMPL이어도 RGB driving 가능 |
| driving mask | `latent_sam_mask.zstd` | `latent_sam`→`concat_latent_sam` |
| `ref.jpg/png` (R) | `ref_frame_pth.zstd` | `ref_frame`→`ref_concat`, 별도 reference prefix |
| 같은 R | `pixel_first_frame.zstd` | `ori_image`→CLIP visual features |
| R + 뒤 zero RGB | `first_frame_pth.zstd` | `first_frame`→`concat_images`; 아래 의미 주의 |
| ref mask | `latent_ref_mask.zstd` | `concat_latent_ref_mask`; 뒤 generated 구간에는 zero mask 채움 |
| caption | `recaption` | `txt`→T5; 빈 caption은 reader에서 skip |
| bbox mask | hands/faces/OCR fields | cache 예제는 모두 zero. 선택된 RFLoss는 OCR/history 제외 |

[cache encode/write L208–302](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/cache_scail2_wds.py#L208-L302), [reader L892–1023](https://github.com/zai-org/SCAIL-2/blob/ac63f8eb369e2f4fac2ce273ead0ae7e602c3919/data_video.py#L892-L1023), [shared_step L275–344](https://github.com/zai-org/SCAIL-2/blob/ac63f8eb369e2f4fac2ce273ead0ae7e602c3919/diffusion_video.py#L275-L344)를 연결했다.

**first_frame_pth는 GT의 첫 프레임도 reference 단일 latent도 아니다.** writer는 R 한 장 뒤에 target 길이−1만큼 zero RGB를 붙인 영상을 인코딩한다. zero는 normalized RGB0이지 latent0이 아니다. 실제 SAT forward는 `concat_images is not None`을 gate로 사용하지만 그 tensor 내용을 직접 concatenate하지 않고, history mask를 x에 붙인다. `ref_concat`은 별도로 prefix에 붙는다. 따라서 이 필드의 이름/reader의 C1HW 주석만 보고 Y 첫 프레임을 넣으면 다른 데이터 계약이 된다. [make_input L206–207](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/cache_scail2_wds.py#L206-L207), [SAT forward L1150–1206](https://github.com/zai-org/SCAIL-2/blob/ac63f8eb369e2f4fac2ce273ead0ae7e602c3919/dit_video_crossattn_sc_xc.py#L1150-L1206).

## 3. 시간·shape·생략하기 쉬운 필드

Writer는 RGB를 center resize/crop한 뒤 GT/D/mask의 최소 길이를 택하고 `4k+1`로 자른다. D RGB는 공간 절반 bilinear로 낮춰 VAE에 넣는다. cache의 C,T,H,W는 reader에서 batch 처리 후 B,T,C,H,W로 permute된다. 예를 들어17 pixel frames는 latent T5이지 T17이 아니다. 공식 [FSDP data config](https://github.com/zai-org/SCAIL-2/blob/ac63f8eb369e2f4fac2ce273ead0ae7e602c3919/configs/training/wan_pose_14Bsc_xc_latent_fsdp_example.yaml#L52-L78)의 video bucket17/21은 latent reader 기준이다. 이번 짧은17프레임을 training-ready라 부르려면 T5 bucket 등의 별도 계약이 필요하다.

reader는 `fps:16`을 기록한다. cache loader는 실제 source의 timestamp를 보존/검증하는 계약을 제공하지 않으며 세 영상의 event alignment도 증명하지 않는다. 24fps 자료를16fps로 relabel해 동작속도가 같다고 처리하면 안 된다. 원본 timestamp는 별도 manifest에서 검사해야 한다. writer에서 optional caption인 것과 reader에서 빈 caption을 거르는 동작도 다르다.

현재 cache 예제는 augmented driving/mask 필드에 원본과 같은 tensor를 복제한다. augmentation 경로가 선택돼도 실제 시각 다양성이 생겼다고 주장할 수 없다. inference의16leaf cache에는 supervised Y·OCR·train history 계약이 없으므로 WDS 학습자료로 바로 대체할 수 없다.

## 4. dropout·history와 실제 loss

[shared_step](https://github.com/zai-org/SCAIL-2/blob/ac63f8eb369e2f4fac2ce273ead0ae7e602c3919/diffusion_video.py#L281-L344)는 e2e_flag에 따라 augmented D 선택 확률0.56/0.75를 사용한다. 예제 pose_dropout은0이고, 이를 양수로 바꾸면 별도 zero-pose latent 파일이 필요하다. `image_cond_dropout` attribute는 존재하지만 이 파일의 실제 shared_step 적용은 확인되지 않는다. text conditioner의 ucg_rate0.1은 [model config](https://github.com/zai-org/SCAIL-2/blob/ac63f8eb369e2f4fac2ce273ead0ae7e602c3919/configs/video_model/Wan2.1-i2v-14Bsc-pose-xc-latent.yaml#L88-L140)에 있다.

`can_history`는 WDS key regex에서 얻는 휴리스틱이다. flag true/false일 때 확률0.5/0.15로 처음 **두 latent 시점**을 clean history로 제공한다. 즉 17pixel프레임 중 처음2장을 뜻하지 않는다. history의 clean 값은 loss 입력 Y에서 오며 해당 영역은 loss에서 제외한다. 키 이름만으로 실제 이전 clip의 연속성을 보장하지 않으므로 향후 smoke에서도 이 정책을 명시해야 한다.

실제 [RFLoss L653–766](https://github.com/zai-org/SCAIL-2/blob/ac63f8eb369e2f4fac2ce273ead0ae7e602c3919/sgm/modules/diffusionmodules/loss.py#L653-L766)는 다음과 같다. x=E(Y), ε~N(0,I), H는 history mask, O는 OCR mask다.

```
x_sigma = H*x + (1-H)*[(1-sigma)*x + sigma*epsilon]
target = epsilon - x
loss_b = mean_all_elements[(1-H)*(1-O)*(prediction-target)^2]
```

유효 영역 개수로 재정규화하지 않고 전체 원소 평균을 취한다. 따라서 mask 면적 변화는 loss 크기도 바꾼다. hands/faces를1.5배하는 별도 RFLossAmp가 있지만 선택된 config의 RFLoss로 혼동하지 않는다. `EpsWeighting` config 이름만 보고 ε prediction으로 부르면 틀린다. 선택된 loss는 위 velocity target과 mask를 사용한다.

[RFSampling](https://github.com/zai-org/SCAIL-2/blob/ac63f8eb369e2f4fac2ce273ead0ae7e602c3919/sgm/modules/diffusionmodules/sigma_sampling.py#L110-L118)은 LogisticNormal(0,1) 첫 성분에서 sigma를 뽑는다. schedule_shift=true일 때 latent spatial patch 수로 μ를 선형 보간하고 `exp(mu)/(exp(mu)+1/sigma-1)`로 이동한다. [RFScaling](https://github.com/zai-org/SCAIL-2/blob/ac63f8eb369e2f4fac2ce273ead0ae7e602c3919/sgm/modules/diffusionmodules/denoiser_scaling.py#L71-L79)은 skip0/output1/input1, model timestep=1000σ다. 학습의 noise 방향은 data→noise이고 생성은 반대로 적분한다. 이는 논문 introductory DDPM ε 식을 그대로 구현했다고 보는 것과 다르다.

## 5. LoRA 판정: 문자열 존재와 실행 경로를 구별

**LoRA 지원 코드가 전혀 없다는 주장은 틀리다.** SAT에 [LoRAMixin](https://github.com/zai-org/SCAIL-2/blob/ac63f8eb369e2f4fac2ce273ead0ae7e602c3919/sat/model/finetune/lora.py#L26-L80)이 있고 Q/K/V/O adapter와 alpha/r·A Kaiming/B zero 초기화가 있다. engine의 [lora_train 분기](https://github.com/zai-org/SCAIL-2/blob/ac63f8eb369e2f4fac2ce273ead0ae7e602c3919/diffusion_video.py#L154-L190)도 존재한다.

반면 조사한 공식 SCAIL 예제 YAML과 `DiffusionTransformer._build_modules`는 LoRA mixin 주입을 설정하지 않는다. lora_train 기본값은false이고, true 분기는 이름의 `lora_layer`를 검사해 다른 parameter의 lr_scale을0으로 설정한다. generic mixin의 실제 parameter 이름은 `lora_linear.*.Q_A/Q_B` 등의 형태이므로 이것만 켜서 adapter만 정확히 학습된다고 보장할 수 없다. [module 구성](https://github.com/zai-org/SCAIL-2/blob/ac63f8eb369e2f4fac2ce273ead0ae7e602c3919/dit_video_crossattn_sc_xc.py#L1054-L1145)과 예제에는 실제 SCAIL LoRA 배선·frozen-base optimizer delta·reload 검증이 없다.

따라서 판정은 **generic LoRA components PRESENT / 공개 SCAIL 예제의 바로 실행 가능한 LoRA recipe NOT_ESTABLISHED**다. 향후 허가된 pilot에는 adapter 주입 hook 충돌, parameter 이름과 optimizer group, base freeze, gradient/2–3 update, save/reload를 실제로 확인해야 한다. 이번에는 추가 구현도 실행도 하지 않았다. 이전 inference 메모리 측정으로 backward가 fit한다고 단정하지 않는다.
