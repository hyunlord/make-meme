# B-033: 같은 편집 영역에서 픽셀·최종 latent·생성 중 제약을 구분하기

## 1. 직관: 합성은 이미 생성된 오류도 보존한다

B-032는 편집 영역 밖을 원본으로 복사해 큰 도로 그래픽 대부분을 없앴다. 그러나 뒤 바퀴 아래의 조각은 합성식이 generated를 선택하는 영역에 남았다. 그 위치가 실제 차체 내부라는 뜻은 아니다. 출력 기반 polygon의 경계·접촉부 오차, radius11 margin, 불확실한 그림자도 원인 후보이다. 이번에는 이 마스크를 줄이지 않는다.

세 비교는 계산 시점이 다르다. RGB_POST는 최종 영상 픽셀을 바꾸고, FINAL_LATENT_ONLY는 기존 최종 latent를 한 번 섞은 뒤 decode하며, STEP_CONSTRAINED는 각 step의 clean estimate를 바꾸어 다음 model 입력까지 달라지게 한다. 마지막 latent 혼합 대조군이 없으면 decoder의 혼합 효과를 sampling 개선으로 오인할 수 있다.

## 2. 수식과 가정

원본 영상은 V, 기존 생성 영상은 G, 픽셀 편집 지도는 E이다. E=1은 generated를 사용하고 E=0은 source를 사용한다.

`RGB_POST_t = (1-E_t) V_t + E_t G_t`.

원본의 정식 VAE encode를 z_src, 기존 최종 generated latent를 z_base, latent 편집 지도를 M이라 하면:

`z_final_only = M z_base + (1-M) z_src`.

VAE decoder D는 비선형이고 주변 공간·시간 문맥을 사용하므로 일반적으로 `D(Mz_a+(1-M)z_b)`는 픽셀 혼합과 같지 않다. 또한 `D(encode(V)) = V`도 보장하지 않는다. 따라서 원본 VAE 복원 자체를 별도로 관찰해야 한다.

현재 pinned FlowUniPC의 flow prediction 규약은 `z_sigma=(1-sigma)z_clean+sigma*epsilon`과 대응하는 방향이다. 모델의 guided velocity v에 대해 converter는 실제 `sigmas[step_index]`를 써서 `x0_hat = z_sigma - sigma*v`를 만든다. 여기의 x0_hat은 중간 상태에서의 clean estimate이며, 마지막에 저장한 sampler latent와 같은 개념이 아니다. [고정 converter 코드](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/utils/fm_solvers_unipc.py#L283-L333).

B-033의 제약은 `x0_c = M*x0_hat + (1-M)*z_src`이다. sigma>0에서 대수적으로 같은 velocity 표현은 `v_c=M*v+(1-M)*(z_sigma-z_src)/sigma`이다. 실제 구현은 나눗셈 경로를 만들지 않고 clean prediction 반환값만 바꾼다. sigma가 작은 마지막 단계의 불필요한 나눗셈을 피하고 원래 converter 출력 dtype를 유지한다.

이는 noisy state에 clean source를 붙이는 연산과 다르다. `z_sigma ← M*z_sigma+(1-M)*z_src`는 sigma>0인 상태에 무노이즈 값을 섞어 상태 분포를 바꾸며, scheduler 후단에서 수행하면 solver history까지 맞지 않을 수 있다. 이번 방식도 pretrained vector field의 원래 적분과 같지는 않다. sampling rule을 바꾸므로 원래 UniPC 수렴차수·정확한 posterior·원본 forward-noising 경로 재현을 자동 주장하지 않는다.

## 3. 실제 tensor와 마스크의 의미

| 값 | shape / 의미 |
|---|---|
| source RGB | `[3,17,512,896]`, 보존된 RGB의 공식 normalization 입력 |
| z_src / z_base | `[16,5,64,112]`, generated model-space와 같은 해상도 |
| driving latent | `[16,5,32,56]`, 이번 z_src 대체값이 아님 |
| reference latent | `[16,1,64,112]`, 정지 참조이며 source video가 아님 |
| E_px | `[17,512,896]`, B-032 float compositor로 재현 |
| M_lat | `[1,1,5,64,112]`, batch/channel broadcast |

M은 E의 f0, f1..4, f5..8, f9..12, f13..16 각각의 시간 max, 공간8×8 max pooling, 공간3×3 max pooling 한 번으로 만든다. 1은 편집 자유 영역이며 0은 source 제약 영역이다. 이 규칙은 기존 source/target support를 보수적으로 포함하려는 근사다. VAE의 실제 receptive field 전체를 계산한 지도도, 새 출력의 정답 matte도 아니다. 새 target이 기존 E 밖으로 벗어나면 마스크를 다시 그려 개선을 만들지 않고 MASK_INCOMPATIBLE 위험으로 기록한다.

원본 semantic mask는 RGB 색상별 의미를 가진다. 이를 `gray>0`으로 읽으면 흰 배경까지 개체로 오인할 수 있다. B-032 E는 의미 마스크나 객체 alpha가 아니라 source·output target union과 고정 dilation/feather에서 파생된 편집 선택 지도다. uint8 support PNG는 검토용 양자화이며 float 원본으로 대체하지 않는다.

## 4. 코드 연결: history까지 같은 제약을 보아야 한다

실제 pinned scheduler `step()`은 `convert_model_output` 반환값을 corrector에 먼저 전달한 뒤 같은 값을 `model_outputs[-1]`에 저장한다. UniP predictor는 이 history를 읽는다. 따라서 원래 converter를 한 번 호출한 직후 제약된 값을 반환하는 좁은 override가 두 경로를 함께 바꾼다. `solver_p=None`이 중요하다. 외부 predictor를 지정하면 원래 raw model_output을 받는 우회 경로가 생긴다. [step의 전달 순서](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/utils/fm_solvers_unipc.py#L688-L730).

CFG positive/negative의 model 호출과 결합은 유지한다. observer 때문에 추가 forward를 하지 않으며 40 step × 2 branch = 80 forward다. 변경은 모델 가중치나 attention이 아니라 scheduler가 저장·사용하는 clean prediction이다. 구현은 [clean_constraint.py](../experiments/B-033-clean-prediction-constraint/code/clean_constraint.py)의 `CleanConstraintScheduler.convert_model_output`과 `mix_clean`이며, [phase_sample.py](../experiments/B-033-clean-prediction-constraint/code/phase_sample.py)는 final 저장 직전에 40 step·80 forward·40 converter 적용을 확인한다. [phase_vae.py](../experiments/B-033-clean-prediction-constraint/code/phase_vae.py)는 원본 encode, source 복원, 최종 혼합 decode와 별도 STEP decode를 구분한다. 실제 적용 횟수는 [METHOD](../experiments/B-033-clean-prediction-constraint/METHOD.md) 및 [RESULTS](../experiments/B-033-clean-prediction-constraint/RESULTS.md)에 연결한다. 실제 완료 기록은 아래처럼 코드 검사와 시각 관측을 분리한다.

## 실제 실행과 정적 관측

실제 S는 40 step·80 forward를 완료했다. converter trace는 index 0..39의 40행이며 모두 finite, CPU FP32 `[1,16,5,64,112]`였다. 첫 sigma는 약 0.999666이고 마지막 converter sigma는 약 0.071361이다. 마지막 저장 latent가 곧 sigma=0에서 converter를 한 번 더 호출했다는 뜻은 아니다. 최종 latent는 FP32 `[16,5,64,112]`로 저장·재로딩이 일치했고, 별도 D도 finite `[3,17,512,896]` 출력을 확보했다. 이 사실은 기술 실행 PASS이며 영상 목표 전체의 PASS가 아니다.

전체 17프레임 시트와 사전 고정 local 0/8/16의 같은 crop을 정적으로 확인했다. STEP은 높은 밝은 차체와 큰 창, 후면 노출 증가를 유지하며 source의 낮고 짙은 Mini형 차량으로 명백히 돌아가지는 않았다. 같은 RGB_POST 뒤에도 B-032와 FINAL_LATENT_ONLY의 뒤 바퀴 아래 적색·검정 조각이 STEP에서는 훨씬 작은 옅은 조각으로 줄어 보인다. 따라서 원거리 배경 복사만이 아니라 경계·접촉 주변의 부분 개선 근거가 있다. 그러나 작은 밝은 흔적은 남고 실제 접지·그림자 정확성은 UNCERTAIN이다.

이 정적 관측은 FINAL_LATENT_ONLY 대조군이 필요한 이유를 보여 준다. 최종 혼합만으로 큰 원거리 그래픽은 줄어도 같은 영역의 바퀴 아래 조각은 남았다. STEP의 작은 조각은 다른 sampling 경로에서 나온 결과지만, 한 case·한 seed의 관측으로 일반적인 개선량이나 최적 방법을 확정할 수 없다. 실제 연속 시청은 수행하지 않았으므로 temporal=UNVERIFIED다. E 밖 원본 복원은 여전히 합성식의 성질이며 방법 성능 점수로 세지 않는다.

## 5. 선행 방법과 이번 비교의 한계

RePaint는 pretrained DDPM의 역확산 과정에서 알려진 이미지 영역을 활용하는 inpainting 방법이다. B-033은 그 DDPM 일정이나 재샘플링을 재현하지 않는다. [RePaint 논문](https://arxiv.org/abs/2201.09865).

Blended Latent Diffusion은 latent 공간의 국소 이미지 편집을 다루며 재구성 부정확성도 별도 문제로 취급한다. 이번에는 그 최적화 전체를 이식하지 않고, 최종 latent 혼합과 sampling 중 제약을 구분하는 제한된 영상 기준선을 시험한다. [Blended Latent Diffusion 논문](https://arxiv.org/abs/2206.02779).

알려진 영역의 일치는 직접 강제한 성질이다. 자유 영역 내부 그래픽이 줄어드는 것은 간접 효과이므로 실제 비교가 필요하다. 같은 RGB_POST 뒤에도 target 외형·거친 회전이 유지되며 경계·접촉이 개선되어야 추가 sampler 비용의 근거가 된다. 원거리 배경만 깨끗하거나 source Mini형 차량으로 회귀하면 목표 성공이 아니다. 차량 한 사례·한 seed·기존 output-mask-assisted 진단이며 자동 편집이나 미사용 일반화를 검증하지 않는다.

## 6. 이해 확인 질문

1. FINAL_LATENT_ONLY 없이 RGB_POST와 STEP_CONSTRAINED만 비교하면 어떤 효과를 잘못 sampling 효과로 해석할 수 있는가?
2. scheduler 반환 후 sample만 덮어쓰는 것과 convert 반환값을 바꾸는 것은 multistep history 관점에서 어떻게 다른가?
3. M=0에서 clean prediction이 z_src와 같다는 사실만으로 최종 RGB의 그 영역이 원본과 pixel exact라고 할 수 있는가?

## 별도 해설

1. 비선형 VAE decoder의 latent 혼합·주변 문맥 효과가 섞인다. 마지막 혼합 대조군은 추가 40 step의 이득이 단순 decode 효과를 넘는지 분리한다.
2. 후단 덮어쓰기는 다음 상태와 과거 prediction history의 관계를 별도로 깨뜨릴 수 있다. converter 반환을 바꾸면 현재 corrector와 저장 history가 같은 제약된 clean estimate를 사용한다. 그래도 원래 solver의 이론 보장이 그대로 이어지는 것은 아니다.
3. 아니다. latent source 자체가 압축 복원이고 decoder는 주변을 섞는다. pixel exact는 최종 RGB_POST의 E=0 복사에서만 직접 얻으며, 손실 MP4에서는 다시 구분해야 한다.
