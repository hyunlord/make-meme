# 실제 Lab 입력 감사

GPU 실행 전 CPU에서 기존 B-007B/E의 Lab 입력을 읽기 전용으로 재확인했다. 새 사진·mask·생성물은 만들지 않았다. 개인 파일 경로와 이미지는 비공개 보고서에만 보존한다.

## 파일·시간·공간 계약

실제 검은 Lab의 착석 사진과 RED 참조 mask, 원본 f0~f16의 단일 직립 개체 RGB/RED mask를 재사용한다. 참조/참조 mask는 512×896이며 RGB와 mask 동영상 모두 512×896, 17프레임, 24fps다. t_i=i/24초; 파일 길이17/24초와 sample span16/24초를 구분한다. driver/mask PNG는 각각 000~016의 17개이며 크기가 같다.

| 별칭 | SHA256 | bytes |
|---|---|---:|
| `reference.png` | `703884c8e2a657d4294cf4e74efeb463c9cd6e05e1ad582f99d6546b954cfdce` | 498994 |
| `reference-mask.png` | `281d5d7ebacfc510b2eba8cedc2b12cc9e5399c5024715e67a5006859cf8d6f3` | 4349 |
| `driver-24fps.mp4` | `e08b0f08155ff9da9a0f9322a15fa5adf665b6857ba1c84cc8e5e65e6891fc27` | 2487365 |
| `mask-24fps.mp4` | `cd13899eecf7ca29e2063975dbae7fab733fe9667195bfc29c2dae1cade451c2` | 40485 |

## 실제 전처리 독립 계산

고정 upstream의 `load_image_to_tensor_chw_normalized`와 `resize_for_rectangle_crop` 함수만 AST로 추출해 기존 PyTorch/torchvision CPU에서 실행했다. 전체 모델 import·가중치 로드·CUDA 연산은 하지 않았다. ffmpeg RGB24 decode 후 기록된 bicubic center crop 경로를 적용했다. 현재 입력은 이미 목표 크기여서 새로운 framing을 추가하지 않는다. 이미지/영상의 정규화 순서 차이를 기존 코드 그대로 보존했다.

| 입력 tensor | shape | dtype | value SHA256 |
|---|---|---|---|
| `img` | `[3, 896, 512]` | `torch.float32` | `816a470d3c9c665b3775d2915712609c2df9b1bb42b9e568e9f78e56ac5da602` |
| `ref_mask_img` | `[3, 896, 512]` | `torch.float32` | `3db4b9af4beec7cb7664d24b8e1fe1db512f9e79e6979f635587579628aacb31` |
| `pose_video` | `[17, 3, 896, 512]` | `torch.float32` | `65db3b40ae4055568df327131c1690e5505bb0622f0458a51b4ff3e4f975d245` |
| `driving_mask_video` | `[3, 17, 896, 512]` | `torch.float32` | `7a855687cb97c22b0e4a5e7cfde9e8adfedb114927c1b7e052a83cdf269f3e6f` |

upstream helper 파일 SHA256: `59de115e3b61a3aae7c7e1bf8a2f1be8abc76efff58ec2fbe463af3a24e956f6`. 실제 P worker의 `preprocessed_inputs.json`과 사전 CPU 계산을 대조한 결과 네 tensor의 shape/dtype/value SHA256이 모두 정확히 일치했다. 이 비교는 조건 인코더 이후 값이나 생성 품질 승인을 뜻하지 않는다.

## 정적 관찰과 한계

참조/마스크 시트 및 전체17 RGB/mask 시트를 실제 열어 확인했다. 참조에는 검은 Lab의 얼굴·귀·혀·넓은 앞몸과 침실/침대 배경이 보인다. 원본은 가는 밝은색 개체 한 마리의 직립 자세이며 작은 머리·앞발 변화 구간이다. 큰 회전·전체 안무·두 개체 평가 구간이라고 부르지 않는다.

참조 및17개 mask PNG palette는 BLACK `[0,0,0]`과 RED `[255,0,0]`다. 같은 RED instance 슬롯을 사용하며, 압축 동영상 decode의 경계색까지 완전 binary라고 가정하지 않는다. 초반 발/바닥 부분의 덩어리와 얇은 앞발·꼬리·반사 경계 불확실성이 남는다. **Mask quality는 PARTIAL_UNRESOLVED**이며 이번에 수정하지 않았다. 이 그림은 mask 정확도 승인이나 3D 접촉 정답이 아니다.

실제 모델 생성·개체·동작 품질은 이 입력 감사만으로 승인하지 않는다. 연속 재생 관찰은 하지 않았으며 시간 품질 UNVERIFIED다.
