# C-008 해설 — 빨간 마스크 하나가 학습 조건 전체를 바꾼 이유

## 1. 직관
VACE는 "이 픽셀은 지키고(inactive), 이 픽셀은 새로 만들어라(reactive)"를 마스크로 받는다.
마스크는 픽셀마다 하나의 값이어야 한다. 그런데 학습 cache는 같은 픽셀에서 빨강 채널만 "새로 만들 곳"으로,
초록·파랑 채널은 "지킬 곳"으로 받았다. 모델은 한 장면이 채널별로 찢어진 조건을 보고 학습했다.

## 2. 수식
X: 조건 RGB (layout과 양끝 앵커), G: 생성 마스크, N(X) = X/127.5 − 1 ∈ [−1,1].

    I = (1 − G) ⊙ N(X),   R = G ⊙ N(X)
    c = Concat(E_VAE(I), E_VAE(R), MaskEncode(G[:, 0]))

의도한 G는 픽셀마다 스칼라를 RGB로 복제한 G = g·[1,1,1]이다. C 경로의 실제 값은 G_C = g·[1,0,0]이었다.

    I_C = [0, N(X)_g, N(X)_b],   R_C = [N(X)_r, 0, 0]          (중간 프레임, g=1)
    I_G = [0, 0, 0],             R_G = N(X)

N(X)의 0은 uint8 127(회색)이다. uint8 0(검정)이 아니다. 따라서 I_G의 중간 프레임은 "회색 화면"이다.
I_C는 거기에 layout의 G/B 채널이 그대로 들어간 영상이다.

학습:  L_C = E[‖v_{θ,ψ}(z_σ, σ, c_C) − v*‖²]
생성:  z_{next} = z + Δσ · v_{θ,ψ}(z, σ, c_G),   c_G ≠ c_C

ψ(adapter)는 c_C에서만 최적화됐다. 생성에서는 c_G가 들어가므로, 학습에서 본 적 없는 조건 분포에서 adapter가 쓰였다.

## 3. 실제 함수와 상태
- `cache_conditions.py:56`: `Image.new('RGB', (416,240), 255)` → PIL은 int를 0xBBGGRR로 해석해 (255,0,0)을 만든다.
- `generate_video.py:condition()`: 공식 helper가 만든 마스크를 `convert('RGB')` → (255,255,255).
- `WanVideoUnit_VACE.process`: `inactive = vace_video*(1-mask)`는 채널별 곱이다. `vace_mask_latents`는 `vace_video_mask[0,0]`, 즉 채널0만 쓴다.

## 4. 최초 차이와 관측의 연결
- **파일 픽셀 일치 ≠ 인코더 입력 일치**: 조건 RGB PNG는 byte로 같았다. 하지만 C는 마스크를 저장하지 않았으므로 "마스크 PNG가 같다"는 G 쪽 사실일 뿐이었다.
- **mask64 exact**: 채널0은 두 경로 모두 255이다. 채널0만 보는 비교는 버그를 볼 수 없다.
- **latent0 exact의 뜻과 한계**: Wan VAE는 첫 1프레임을 따로, 이후 4프레임씩 causal로 묶는다. latent0은 프레임0만 보고, 프레임0의 마스크는 0이다. 0은 빨강이든 흰색이든 (0,0,0)이다.
  즉 "latent0 exact"는 "프레임0 입력이 같았다"는 단서일 뿐, 이후 latent의 차이가 시간 cache 때문이라는 증거가 아니었다.
- 시간 cache 가설은 직접 관측으로 반증했다. 두 경로 모두 tile마다 CausalConv3d 호출 232회 중 176회가 이전 chunk 특징을 받았다.
- **eval / no_grad / inference_mode**: 모든 encode는 grad=False, inference_mode=False, autocast=False, VAE eval이었다. 이번 원인과 무관함을 기록으로 확인했다.

## 5. 수정 근거와 독립 검증
- 바꾼 것은 마스크 fill 한 줄뿐이다. 수정한 C와 G를 다른 프로세스, 다른 적재 형태로 실행했고 elephant·goat에서 bit-exact였다.
- **parity만으로는 부족한 이유**: 두 경로가 같은 잘못된 계산을 공유하면 parity가 나와도 틀릴 수 있다. 공유 부품인 VAE는 causal 계약으로 따로 검사했다.
  (첫 프레임 단독 = 전체 t0, prefix5 = 전체 t0..1, 프레임17~32를 바꿔도 t0..4는 불변)
  마스크의 의미는 공식 helper와 mask latent 구현(채널0 = 픽셀 스칼라)으로 정했다. 영상을 보고 "더 좋아 보이는 쪽"을 고른 것이 아니다.
- **target·endpoint도 확인한 이유**: 원인이 VAE였다면 target과 patch도 오염됐을 것이다. 다시 인코딩해 보니 둘 다 저장본과 exact였다.
  영향 범위는 `vace_context` 하나로 한정되고, 재생성 비용은 encode 24+2회로 작다.

## 6. 잘못된 조건으로 학습한 checkpoint 읽기
- checkpoint는 "c_C라는 조건에서의 해"다. c_G에서 결과가 나쁘다는 것은 adapter 구조가 나쁘다는 증거가 아니다.
- 반대로 c_G에서 우연히 좋아져도 학습이 성공했다는 뜻이 아니다. 방법을 평가하려면 c_G 의미의 cache로 같은 설정의 재학습이 필요하다.
- C-007의 one-step probe(PROBES/CFG/BLOCK)는 c_C로 계산됐다. rollout/replay는 c_G로 계산됐다. 둘 사이의 차이에는 조건 shift가 섞여 있다.

## 7. 남은 한계
- 입력 일치가 회복돼도 adapter 회귀가 남을 수 있다. 1.27M parameter, 256 update라는 규모, 학습 목표, 낮은 sigma 오차는 이번 원인과 독립적일 수 있다.
- train 8개, test, cross-ID는 코드 경로가 같아서 영향받았다고 추정한 것이다. 직접 재인코딩은 elephant·goat만 했다.
- R 검사는 단일 공간 tile(30×52 latent = 전체 프레임) 조건에서만 했다. 여러 tile의 합성은 이번 해상도에서 쓰이지 않는다.
- 일반 교훈: PIL `Image.new(mode, size, int)`는 다채널 mode에서 int를 packed 색으로 읽는다. 마스크는 `(v,v,v)`나 `'L'`로 만든 뒤 변환하고, 인코더 직전 텐서를 채널별로 비교해야 한다.
