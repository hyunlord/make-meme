# 멀티스케일 생성·영상 초해상도 연구 메모

작성: 2026-10-23 · 상태: 문헌·코드 검토와 후보 설계, 새로운 실험은 NOT_RUN.

## 0. 사용자 목표·현재 작업과 경계

사용자는 상용 생성 서비스를 호출하려는 것이 아니라 DGX Spark급 로컬 자원에서 상용 결과에 근접하거나 특정 과제에서 넘어서는 이미지·영상 생성 방법을 이해·학습·개선하려 한다. 낮은 해상도로 생성한 뒤 업스케일하면 비용을 줄일 수 있다는 제작 팁을 아키텍처·학습·평가 질문으로 확장한다.

사용자는 B-009 지시를 전달했다고 보고했다. 이번 메모는 별도 docs/generative-research-program-20261023 브랜치에만 기록하며, 진행 중인 연구 브랜치·코드·예산·입력·결과를 변경하지 않는다. 새 모델 다운로드, 설치, 이미지/영상 생성, 학습은 0회다. 아래 비교표는 실행 승인이 아니라 BACKLOG다. A(native imagegen-only)와 B(local model research)의 경계를 유지한다. 학습형 video-SR를 사용하면 B 실험이며, 이를 A에 몰래 추가하지 않는다.

## 1. 표현과 생성 단계를 구분

- '낮은 화질' 대신 낮은 공간 해상도, 적은 sampling steps, 낮은 FPS, 강한 압축/양자화 중 무엇인지 명시한다. 서로 다른 개입이다.
- 보간 resize: 픽셀 격자를 확대. 새로운 실제 고주파 정보의 복원을 보장하지 않는다.
- VAE latent 생성/디코딩: 압축 특징 공간에서 생성한 뒤 학습된 decoder로 픽셀을 복원한다. latent는 저해상도 RGB 이미지가 아니고, decoder도 임의 입력을 원하는 4K로 올리는 범용 SR이 아니다.
- 외부 video-SR: 완성된 저해상도 영상에 별도 복원/초해상도 모델 적용. 내부 생성기를 바꾸지 않아도 도입 가능.
- cascaded generation: 저해상도 생성과 조건부 고해상도 생성기를 함께 설계·학습한다.
- pyramidal generation: denoising/flow trajectory 자체에서 저→고해상도로 진행한다. 중간 latent resize만으로 정당한 확률 경로가 보존되는 것은 아니다.

B-008 기록(commit 0113a12f89d17665d0c5a3577e69ab19ae5eb29f)을 재조회했다. 출력은 H896×W512, T17이고 generated noise/final latent shape는 [16,5,112,64]다. (공간8배, 시간4배 stride.) 이 경로는 이미 latent-space 생성의 비용 절감을 사용한다. SCAIL pinned README는 mixed-resolution/fps training, e2e 512p/704p, 다른 크기는 H/W32배수 조건을 명시한다. 그러나 256p 등 더 작은 크기의 품질을 보증하지 않는다.

## 2. 확인한 선행 연구와 연결

1. Latent Diffusion (CVPR 2022): 강한 pretrained autoencoder의 latent에서 diffusion을 실행해 계산량과 표현력 균형을 다룬다. https://arxiv.org/abs/2112.10752
2. Imagen Video (2022): base video generator 뒤 spatial/temporal SR 모델을 연결한 cascade. '저해상도에서 만들고 고해상도로 올린다'는 개념 자체는 새 기여가 아니다. https://arxiv.org/abs/2210.02303
3. Pyramidal Flow Matching (2024): 단일 DiT에 여러 spatial stage와 compressed temporal history를 결합하고, stage 경계에 corrective Gaussian renoising을 사용해 확률 경로를 연결한다. https://arxiv.org/abs/2410.05954 · https://arxiv.org/html/2410.05954v2
4. HunyuanVideo-1.5: 공식 구현이 저비용 영상 생성과 별도 few-step SR의 1080p 출력을 안내한다. 우리 Spark에서의 실행 가능성/속도는 미측정. https://github.com/Tencent-Hunyuan/HunyuanVideo-1.5
5. SeedVR2 (2025/ICLR2026): one-step video restoration, adaptive window attention과 adversarial post-training. 이는 모델 팀의 논문/공개 결과이며 로컬 메모리·개체 보존 성능을 여기서 재현하지 않음. Seedance와 다른 프로젝트다. https://arxiv.org/abs/2506.05301 · https://github.com/ByteDance-Seed/SeedVR
6. VideoGigaGAN (2024): 고주파 생성과 temporal consistency 사이의 문제를 분석한다. frame-wise image SR나 단순 temporal module 추가만으로 깜빡임이 해결된다고 가정하지 않는다. https://arxiv.org/abs/2404.12388
7. DLoRAL (2025): consistency/detail 역할의 두 LoRA와 cross-frame retrieval을 연구한다. '동작/세부 분리 LoRA'라는 큰 아이디어만으로 새로움을 주장하지 않는다. https://arxiv.org/abs/2506.15591
8. Perception–Distortion Tradeoff (CVPR 2018): 보기 좋은 결과와 실제 원본 일치가 같은 목표가 아님을 뒷받침한다. 특정 fidelity metric·perceptual metric의 정의와 가정을 확인해야 한다. https://arxiv.org/abs/1711.06077

상용 Kling/Seedance/Higgsfield의 미공개 내부 구조가 이 중 어느 것이라고 단정하지 않는다. 공개 코드·논문에서 확인한 원리만 연구 근거로 사용한다.

## 3. 비용 모델: 해상도를 줄이면 무엇이 줄어드는가

같은 temporal length와 latent/patch stride에서 video token 수 N은 대략 T_lat*H_lat*W_lat/(p_t*p_h*p_w)에 비례한다. 이미지/비디오 조건 토큰도 포함하면 정확한 N은 구현으로 계수한다.

가로·세로를 각각 절반으로 하면 spatial token 부분 N은 약1/4. dense attention의 QK/AV 부분은 O(N²d)이므로 그 부분의 연산량은 약1/16, projection/MLP 등 O(Nd²)은 약1/4. 이는 attention compute의 이론 비교이지 전체16배 가속이나16배 메모리 감소라는 약속이 아니다. FlashAttention은 N² score materialization을 피하지만 같은 dense attention의 연산을 공짜로 없애는 것은 아니다.

예: 출력 W512×H896 → W256×H448. 이 크기는 설명용이고 자동 실행 설정이 아니다. 낮은 resolution에서 모델이 학습 분포를 벗어나거나 작은 발/눈/마스크가 소실될 수 있다. W384×H672 같은 중간 크기 역시 actual pretrained support·품질 확인 전에는 연구 후보다.

C_direct = C_gen(H,W,T)
C_cascade = C_gen(H/r,W/r,T) + C_SR(H,W,T) + C_handoff + C_validation

C_cascade<C_direct일 때만 계산비 절감. 초기 전체 로딩·텍스트 인코딩·SR weight loading·실패/재시도·검수 비용을 포함한다. 상용 credit 가격과 로컬 FLOPs/시간/에너지 비용은 다른 지표다. model parameter bytes는 해상도를 줄여도 그대로다. 작은 크기는 token/activation/decode 비용을 주로 줄이지, 동일 모델의 weight 크기를 줄이지 않는다.

P/S/D의 순차 실행을 유지한다면 SR도 DiT 프로세스가 종료된 뒤 실행할 수 있다. 따라서 모든 모델을 한꺼번에 상주시킬 필요는 없지만 stage 전환·I/O와 실제 OS 메모리를 측정해야 한다.

## 4. 확률적 관점과 보존 조건

설명용 계층 모델:
p(Y_H|c) ≈ integral p_phi(Y_H|Y_L,c) p_theta(Y_L|c) dY_L.

Y_L은 저해상도 영상, Y_H는 고해상도 영상, c는 참조·동작·텍스트·마스크 등의 조건이다. 별도 learned SR에도 reference나 motion 조건을 주는 설계는 가능하지만, 일반 SR이 우리 조건을 지원한다고 가정하지 않는다.

복원 예:
Y_L = D(Y_H) + eta.

D가 downsampling이면 여러 Y_H가 같은 Y_L에 대응한다. 생성형 SR이 복원하는 털·눈·무늬는 실제 사진의 고주파 정답과 다를 수 있다. 따라서 perceptual sharpness와 target identity/motion fidelity를 따로 평가한다. B-008처럼 앉은 자세를 생성한 출력을 단순 SR하면 동작 실패가 자동 해결되는 것이 아니다. 자세가 크게 바뀐다면 '보존형 초해상도'가 아니라 추가 구조 재생성/편집이며 그 비용·부작용을 별도 평가한다.

실험용 residual 표현:
Y_H = U(Y_L) + R_phi(Y_L,reference,driver,epsilon).

설명용 downsample consistency L_dc=||D(Y_H)-Y_L||는 coarse 구조 보존 제약이지 identity/fine detail 정답을 보증하지 않는다. D의 null space에 다양한 잘못된 디테일이 존재할 수 있다.

Flow Matching 피라미드의 난점:
z_tau^L = a(tau) z_0^L + b(tau) epsilon_L.
선형 upsampler U로 늘린 noise는 Cov(U epsilon_L)=U U^T로 일반적으로 I가 아니다. 즉 latent 공간 해상도만 바꾸면 새 단계의 노이즈 통계·위치 encoding·condition 좌표가 맞지 않을 수 있다. Pyramid Flow는 이런 stage 연결과 학습 목표를 설계한다. frozen SCAIL에 임의 resize를 넣어 같은 알고리즘이라 부르지 않는다.

공간축 축소와 시간축 축소는 다른 문제. FPS를 낮추면 움직임의 관측 시각·발 접촉·윙크·회전 이벤트가 소실될 수 있다. 단순 writer FPS 변경은 시간 보간/temporal SR이 아니다. 초기 실험에서는 프레임 수와 원본 sample time을 고정한다.

## 5. 이론→실전 후보 포트폴리오 (전부 NOT_RUN)

| 후보 | 질문 | 첫 최소 반증/학습 | 주요 위험 |
|---|---|---|---|
| 순차 local video-SR | 저해상도 생성+SR이 direct output보다 비용 대비 낫나? | 같은 최종 크기에서 direct/LR+bicubic/LR+VSR 비교 | SR 비용, identity hallucination, flicker |
| 참조 보존형 refinement | target 세부를 강화하면서 참조 pose가 새지 않는가? | 같은 LR clip에 reference-conditioned 여부 한 개입 | pose leakage, generative geometry change |
| latent pyramidal sampling | early steps의 저해상도 연산이 충분한가? | 작은 2D/이미지 toy에서 scale transition/noise covariance 확인 | pretrained mismatch, distribution discontinuity |
| 세부·움직임 역할 분리 adapter | consistency와 detail을 따로 학습하면 어떤 효과가 있나? | existing DLoRAL 등 가장 가까운 baseline부터 분석 | 이미 존재하는 아이디어, fine-tuning 데이터 |
| ROI/불확실성 기반 refinement | 얼굴·발·가림에 연산을 더 쓰면 효율이 좋은가? | 동일 예산 uniform refinement와 비교 | tile 경계, ID 교환, visibility estimator error |
| few-step distillation | step 수를 줄여도 동작 제어가 유지되는가? | teacher와 student를 동일 조건/고정 시험집합 비교 | 값비싼 teacher rollout, mode/condition 저하 |
| temporal SR | 적은 시간 샘플을 추가 프레임으로 복원해도 이벤트가 맞나? | 가림 없는 작은 동작→빠른 회전 순서 | 발차기·윙크 소실, speed 조작/가짜 부드러움 |

모든 후보를 동시에 설치/학습하지 않는다. 후보마다 문헌 차이, 비용, 성공·기각 조건을 먼저 쓰고, 작은 재현에서 관측된 한 병목을 선택한다.

## 6. 후속 실험 로드맵 제안 (B-009 완료 후 별도 PLAN)

### R0: 복원능력과 생성능력을 분리
출처/사용 범위가 확인된 선명한 동물 영상으로 clean HR→고정 degradation→LR pair를 만든다. 원본 HR, bicubic/Lanczos, 작은 video-aware SR, diffusion-based VSR 후보1개를 비교할 수 있다. 아직 실제 backend·Spark 호환성·예산을 확정하지 않았다. CPU resize만으로도 얼굴·발/꼬리가 어느 스케일에서 관측 불가해지는지 먼저 확인 가능하다.

이 복원 실험에는 paired target가 있으므로 PSNR/SSIM 등을 보조지표로 사용할 수 있지만 perceptual texture·ID·동작·temporal 검토가 필요하다. 동일 clip 인접 frame을 train/test에 섞지 않고 identity/scene 단위로 분리한다.

### R1: native 저해상도 생성 + SR
동작을 최소한 재현하는 고정 baseline을 선정한 뒤 여러 해상도의 native output을 생성한다. output을 나중에 줄여서 '저해상도 생성 비용'을 측정하지 않는다. SCAIL 공식 지원 크기와 작은 크기의 distribution-shift를 구분한다.

A direct-HR; B native-LR+bicubic; C same native-LR+video-SR. B/C의 LR는 동일 byte artifact를 재사용한다. 같은 target H/W/FPS/길이에서 비교한다. HR와LR의 seed가 같아도 noise shape와 결과가 같은 counterfactual이라고 주장하지 않는다. 초기 소수 seed는 feasibility screening이고 후속 독립 prompt/개체/동작/seed 평가를 사전 고정한다.

기록: sampler 및 SR cold/warm/전체 시간, weight/activation/OS 메모리, IO, 전체 실패율, ID·동작·구도·fine texture·temporal quality. 무동작 영상은 쉽게 안정적인 점수가 나올 수 있으므로 움직임 크기/이벤트/동작충실도와 joint pass를 함께 본다. cross-identity 생성의 원본 RGB를 pixel 정답으로 쓰지 않는다.

### R2: 한 학습 개입
기존 pretrained VSR로 반복 실패가 확인되면, 작은 adapter/LoRA 또는 마지막 refinement 모듈만 연구한다. synthetic clean downsampling과 실제 generated-LR degradation의 차이를 측정한다. 정답 없는 reference-target 쌍을 ground truth로 만들지 않는다. LR 입력이 잃어버린 세부를 추정하는 불확실성과 identity 보존을 분리한다.

논문 주장 후보는 '저해상도+업스케일을 처음 사용'이 아니라, 특정 일반적 실패를 새 방법/분석으로 개선해 강한 baseline 대비 품질-비용 Pareto frontier를 이동시키는 것이다. reference-guided SR, temporal detail/consistency, pyramidal flow는 선행 연구가 있으므로 정확한 새 차이를 검증해야 한다.

## 7. 학습 산출물과 운영

각 후속 실험은 질문/직관 → 식·가정 → tensor/코드 → small check → 실제 출력 → 실패/한계 → 이해 질문/해설 순서로 작성한다. 이번 권장 질문:
1. VAE decoder와 SR generator의 입력·학습 target이 왜 다른가?
2. H/W를 절반으로 줄일 때 N, attention, MLP, weight memory가 각각 어떻게 바뀌는가?
3. D(Y_H)=Y_L를 만족해도 identity가 달라질 수 있는 이유는 무엇인가?
4. 공간 업샘플된 Gaussian noise가 고해상도 iid Gaussian과 다른 이유는 무엇인가?
5. 정답 HR를 축소한 복원 실험이 실제 LR 생성 결과의 SR 성능을 보증하지 못하는 이유는 무엇인가?

연구 기록은 GitHub Markdown에 계속 남긴다. 이 문서는 방향/이론/후보 기록이며 활성 B-009와 이전 조건 계약에 변화가 없다. 이후 실험을 수행할 때 실제 branch HEAD/PLAN/config/weights/input/noise hash, RESULTS/HISTORY/ROADMAP 및 실측을 별도 실행 기록으로 연결한다. 문헌 검토를 실제 Spark 실행 성공이나 상용 품질 달성으로 보고하지 않는다.
