# B-010 실제 CPU 입력 검증

상태: CPU_INPUTS_READY, 모델 P/PROBE/S/D **NOT_RUN**. 입력 준비 성공은 생성 실행의 승인이 아니다.

Reference RGB는 기존 실제 처리된 driving MP4의 f0 RGB를 그대로 lossless PNG로 저장했다. 기존 lossless driver f0 PNG와 픽셀도 정확히 같았다. 색 변경·워핑·새 이미지 생성은 없다. 원본 source와 모델 입력의512×896 좌표 및24fps 순서를 유지한다.

Reference mask는 기존 원본 lossless f0 mask에서 pinned helper와 같은 `R>225, G<=225, B<=225` RED support를 사용했다. 이 support는 실제 decoded mask MP4 f0에서도 정확히 같다. 해당63,652픽셀은 정확한 RED, 나머지395,100픽셀은 WHITE로 저장했다. 새로운 윤곽은 만들지 않았다. 전체 driving mask는 기존 BLACK 배경 그대로이며 부분적인 발·바닥 분할 불확실성은 유지한다.

STATIC COPY는 실제 source f0를17장 반복한 CPU 대조군을 입력 준비 초기에 만들었다. 17프레임·24fps·파일 길이17/24초이며 마지막 sample시각은16/24초다. 생성 output이나 새 동작을 만든 것이 아니다.

## 실제 파일 SHA256

- `reference.png`: `2337f647648b38761ee6b0d8743030b7dfd44e478c6374bff1af7f150139208f`
- `reference-mask-white.png`: `6133de0c9df99958752554e8327dcdbef92f0c54647b340e4a54346b480a1c25`
- `driver-24fps.mp4`: `e08b0f08155ff9da9a0f9322a15fa5adf665b6857ba1c84cc8e5e65e6891fc27`
- `mask-24fps.mp4`: `cd13899eecf7ca29e2063975dbae7fab733fe9667195bfc29c2dae1cade451c2`

## 독립 CPU 전처리 값

- `img`: torch.float32 `[3, 896, 512]`, SHA256 `e50e896b508e0047a374598fe7725f676635de3d8bf34976f7cda2b83d82d536`
- `ref_mask_img`: torch.float32 `[3, 896, 512]`, SHA256 `d00dfcbfd507f9972ded3549c64d6fa3687e23305b8c6ab15d47fc89ede783a5`
- `pose_video`: torch.float32 `[17, 3, 896, 512]`, SHA256 `65db3b40ae4055568df327131c1690e5505bb0622f0458a51b4ff3e4f975d245`
- `driving_mask_video`: torch.float32 `[3, 17, 896, 512]`, SHA256 `7a855687cb97c22b0e4a5e7cfde9e8adfedb114927c1b7e052a83cdf269f3e6f`

Pinned 이미지/resize helper를 CPU에서 실행한 값이다. 실제 P는 실행하지 않았으므로 runtime VAE/CLIP/cache 입력 검증으로 바꾸어 말하지 않는다. 원본과 파일·참조 자료는 비공개 ZIP에만 포함한다.
