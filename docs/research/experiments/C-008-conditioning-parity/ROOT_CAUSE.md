# C-008 ROOT CAUSE

## 결론
C-006 `cache_conditions.py:56` (그리고 `cross_cache.py:58`)의 생성 마스크:

```python
masks = [Image.new('RGB', (416, 240), 0 if t in (0, 32) else 255) for t in range(33)]
```

PIL은 `'RGB'` 모드에서 정수 fill을 packed RGB 정수로 해석한다. `255`는 흰색이 아니라 **(255, 0, 0) 빨강**이다
(Spark의 PIL 12.3.0에서 직접 확인). 실제 생성 경로(G)는 공식 `FrameRefExpandAnnotator`가 만든 마스크를
`convert('RGB')`하므로 (255,255,255)이다.

`WanVideoUnit_VACE.process`는 마스크를 채널별로 곱한다.

```python
inactive = vace_video * (1 - vace_video_mask)   # 채널별
reactive = vace_video * vace_video_mask
vace_mask_latents = rearrange(vace_video_mask[0, 0], ...)   # 채널 0만 사용
```

따라서 C의 중간 프레임 31장은 R 채널이 reactive로, G/B 채널이 inactive로 갈라진 채 인코딩됐다.

| 관측 | 설명 |
|---|---|
| mask64 exact | mask latent는 채널0만 읽고 채널0은 두 경로 모두 255 |
| RGB 특징 latent0 exact | 프레임0은 마스크 0 → (0,0,0)=흰/빨강 구분 없음, latent0은 프레임0만 봄 |
| latent1~8 mismatch, 공간적으로 균일 | 프레임1~31 전부에서 채널 분리가 달라짐 (프레임32는 마스크0이지만 latent8은 29~32를 함께 봄) |
| inactive/reactive 모두 큰 차이 (rel≈1) | 다른 의미의 입력을 인코딩한 것이지 수치 오차가 아님 |

## 경계
- 마지막으로 같았던 경계: P0 파일 픽셀의 **조건 RGB** (33장 byte 동일), 마스크 채널0.
- 최초로 달라진 경계: P0 **마스크 PIL 이미지의 채널 1·2** → P1 `preprocess_video(mask)` → P2 inactive/reactive.
- C-007 INPUT_PARITY의 "logical_rgb_masks_same"에는 C 경로가 실행 중 만든 마스크 객체의 채널별 값 비교가 포함돼 있지 않다 (C는 마스크를 저장하지 않았다).

## 반증한 후보 (같은 실행에서 직접 관측)
| 후보 | 증거 |
|---|---|
| 모델 적재 형태 (T5+VAE vs DiT+VACE+T5+VAE) | 전체 적재된 G 프로세스 안에서 C식 직접 호출 → C_old와 exact |
| VAE 시간 cache reset/전달 | 모든 encode에서 encoder CausalConv3d 26개, 33프레임 tile당 cache 사용 176/미사용 56회로 동일; clear_cache 정상 |
| wrapper/dispatch | encoder 모듈 타입 집계 두 경로 동일, `vram_management_enabled=False` |
| grad/inference_mode/autocast/dtype | 모든 호출 grad=False, inference_mode=False, autocast=False, BF16 |
| 공간 tile | 30×52 latent tile = 전체 프레임, 두 경로 모두 1 tile |
| 저장·직렬화·stale cache | C_new(현재 코드) == cache-v2 저장물 exact; G_new == C-007 저장 context exact |
| 비결정성 | 같은 경로 반복 exact |

## 단일 개입
마스크 fill만 `(v, v, v)`로 바꾼 C 경로(`mask_fill='white'`) → 별도 프로세스의 G 결과와 elephant·goat 모두 **bit-exact**.
되돌린 상태(`legacy_int`)는 elephant·goat 모두 원래 크기의 불일치를 재현한다 (goat rms 0.7615, elephant 0.7668).

판정: MISMATCH_REPRODUCED · FIRST_DIVERGENCE_LOCALIZED · ROOT_CAUSE_CONFIRMED.
