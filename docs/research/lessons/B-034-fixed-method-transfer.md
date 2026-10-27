# B-034: 같은 혼합식이라도 적용 시점이 생성 경로를 바꾼다

이 문서의 수식은 고정 B033 구현을 설명한다. 새 알고리즘이나 수렴 보장은 아니다. 실제 결과는 [RESULTS](../experiments/B-034-fixed-method-transfer-validation/RESULTS.md)에 연결한다. 이번 B034에서는 차량 BASE latent까지만 확보하고 종료 가드 때문에 비교 decode/STEP은 미실행이다. 아래 방법 설명을 이번 입력에서 효과가 관측됐다는 주장으로 읽지 않는다.

## 1. 마지막 혼합과 반복 제약

직관: 완성된 그림의 바깥을 원본으로 바꾸는 것과, 그리는 도중 원본 문맥을 계속 반영하는 것은 다르다. 다만 문맥이 target을 source 외형으로 되돌릴 수도 있어 무조건 개선이 아니다.

영상 latent를 z, source의 full-resolution VAE latent를 z_s, 자유 편집 비율을 M∈[0,1]이라 하자. 여기서 시간 지수 k는 영상 프레임이 아니라 denoising step이다. 조건 c는 reference·driving·mask·text를 포함한다. 단순화된 flow 표현에서는 z_σ=(1−σ)z_0+σε, velocity=ε−z_0이면 clean 추정은 ẑ_0=z_σ−σv_θ(z_σ,σ,c)다. 실제 구현에서는 이 식을 재작성하지 않고 고정 공식 scheduler의 converter를 한 번 호출한다.

마지막 혼합은 z_final=M⊙z_BASE+(1−M)⊙z_s이다. 이미 끝난 BASE의 40회 경로에는 영향을 주지 않는다. STEP은 매 k에서 z̃_0,k=M⊙ẑ_0,k+(1−M)⊙z_s를 공식 UniPC corrector/history/predictor에 전달한다. 다음 z_(k+1)이 달라질 수 있으므로 이후 모델 평가의 입력과 최종 결과도 달라질 수 있다. CFG나 velocity 자체를 source로 교체하거나 noisy state에 clean source를 직접 붙이는 것과 다르다.

실제 연결은 [clean_constraint.py](../experiments/B-034-fixed-method-transfer-validation/video_code/clean_constraint.py)의 `convert_model_output` → `super()` → `mix_clean`이다. source는 `[16,5,64,112]`, 저장 M은 `[1,1,5,64,112]`; batch 없는 clean과 batch 있는 clean을 명시적으로 맞춘다. source/mask는 실제 clean의 dtype/device를 따르고 M=0/1은 `torch.where`로 endpoint를 그대로 선택한다. trace의 변화 norm은 개입 크기이며 품질·원인 기여도 점수가 아니다.

## 2. Latent 위치와 RGB 위치가 같지 않은 이유

RGB 편집 support E는 `[17,512,896]`이다. E=1은 generated를 사용할 영역, E=0은 원본을 사용할 영역이다. 객체 불투명도 alpha나 모델의 RED/BLACK semantic channel과 같지 않다. S는 공개 source GT, T는 BASE에서 관측한 target이며 U=S∪T다. source가 더 크면 제거될 기존 객체까지 포함해야 하므로 T만 쓰지 않는다. H=empty는 그림자가 없다는 판정이 아니라 별도 shadow support를 쓰지 않는 한계다.

source clip bbox 긴변 L로 r=max(2,ceil(.02L))를 정하고 Euclidean core 바깥4px를 feather한다. 기존 차량의 r=11은 한 입력의 실현값일 뿐 방법의 상수가 아니다. 시간 묶음 [0],[1..4],[5..8],[9..12],[13..16]의 max, 공간8×8 max,3×3 max guard를 적용해 M을 얻는다. 코드의 `latent_mask`는 이 보수적 coverage 규칙이다.

VAE의 convolution과 시간 문맥 때문에 한 latent cell은 정확히 한 RGB 블록만 나타내지 않는다. max pooling의 coverage 확인은 실제 VAE receptive field 전체 보장이 아니다. source reconstruction은 압축/복원 오차를 보여 주는 별도 대조군이다. 같은 RGB 후합성 Y=(1−E)⊙V+E⊙G를 세 결과에 적용해 먼 배경 복원만으로 STEP이 좋아 보이는 것을 막는다. E=0 원본 exact는 이 수식/저장 구현의 성질이지 모델 우월성이다. 손실 MP4에는 byte-exact 주장을 하지 않는다.

## 3. Mask-given과 자동 편집

공개 source GT와 agent가 실제 BASE를 보고 그린 target polygon이 필요한 비교다. 자동 객체 선택/추적/segmentation이나 독립 인간 GT를 얻은 것이 아니다. BASE를 만든 뒤 T와 E/M 및 관측창을 고정해야 하므로 현재 방법은 output-mask-assisted이며 two-pass다. STEP을 본 뒤 E를 바꾸면 불리한 경계를 숨기는 평가 누수가 생긴다. STEP target이 E 밖으로 나오면 raw/E overlay와 MASK_INCOMPATIBLE을 그대로 남긴다.

생성 앵커 A0도 GT가 아니다. target/source 자세 결합이 실패하면 후단 영상은 미실행이다. 이때 clean 제약 효과는 NOT_RUN이며 앵커 실패를 방법 PASS 또는 FAIL로 대신하지 않는다. 적합한 subset만 보고 전체 자동 시스템이 성공했다고 할 수 없다. 두 새 입력도 관측 뒤에는 개발 사례이고, 사전학습 데이터 중복은 UNKNOWN이다.

## 4. 비용의 세 관점

검증 캠페인은 Qwen 로딩/앵커, 주석, 조건/원본 인코딩, BASE와 STEP, 네 종류 decode, 합성/검토/전송까지 계산한다. 이미 BASE와 support가 있는 사용자는 STEP과 필요한 encode/decode의 증분만 낼 수 있다. 그러나 미래 one-pass 비용은 아직 입증하지 않았다. STEP 자체와 BASE는 각각40step·80forward지만, 현재 support를 얻으려면 BASE가 먼저 필요하다. 단일 worker 시간차를 scheduler 개입의 순수 overhead라고 할 수 없고, CUDA/RSS/cgroup/시스템 가용 메모리도 합산하지 않는다.

## 5. 선행 방법과 구분

[RePaint](https://arxiv.org/abs/2201.09865)는 사전학습된 unconditional DDPM의 역과정에 알려진 이미지 영역을 사용한다. 이번 SCAIL 조건부 flow/UniPC clean converter 개입은 그 알고리즘의 정확한 재현이 아니다. [Blended Latent Diffusion](https://arxiv.org/abs/2206.02779)는 latent 기반 국소 이미지 편집, 재구성 오차 및 얇은 mask 문제를 다룬다. 이번에는 해당 모델이나 재구성 최적화 절차를 설치/실행하지 않는다. 알려진 영역의 혼합이라는 공통 아이디어만으로 신규 논문 기여를 주장하지 않는다. 두 원논문의 공개 초록을 2026-10-27 확인했다.

## 6. 이번 관측과 이론의 경계

실제 차량 BASE x0는 FP32 `[16,5,64,112]`로 저장됐고40step/80forward 및 finite를 확인했다. 이는 영상 VAE decode 입력이 준비됐다는 뜻이지 RGB 외형·동작 품질을 확인했다는 뜻이 아니다. `other_service_work`의 원시 발동 PID/queue 응답이 없어 종료 경합이라는 설명은 가설이다. 후속 assertion을 삭제하면 방법 검증과 실행 정책 변경을 섞게 되므로 이번에는 멈췄다.

인물 앵커는 target 외형을 반영하면서 source의 측면 보행·크기를 잃었다. 이는 A0가 GT가 아니며 앞단의 외형/자세 결합 실패가 별도로 있다는 실제 예다. clean 제약이 이 문제를 해결하거나 악화시켰다는 데이터는 없다. BASE T/E/M을 만들지 않았으므로 output-assisted 주석 비용도 실제0이며 향후 two-pass 전체 비용을 이번 실행 합계로 추정하지 않는다.

## 이해 확인 질문

1. BASE와 STEP의 CFG·초기 noise·NFE가 같아도 최종 latent가 달라질 수 있는 이유는 무엇인가?
2. M이 주석 support를 모두 포함해도 target의 얇은 경계가 보존된다고 보장할 수 없는 이유는 무엇인가?
3. 이미 BASE가 있는 사용자의 증분 비용과 이번 전체 시스템 비용은 왜 다른가?

## 별도 해설

1. converter가 반환하는 clean 추정과 UniPC history가 바뀌면 다음 noisy state가 달라지고, 그 상태를 받은 이후 모델 예측도 달라진다. 동일 noise는 출발점 통제이지 경로 불변 조건이 아니다.
2. 주석 자체가 coarse/uncertain이며 VAE receptive field는 8×8 픽셀과 일대일 대응하지 않는다. STEP target 위치도 BASE와 달라질 수 있다. raw와 동일 E를 함께 확인해야 한다.
3. 증분은 기존 BASE·주석을 이미 지불한 것으로 가정한다. 이번 시스템은 그 둘을 만들고 앵커 실패까지 감수해야 한다. 두 비용을 섞으면 실제 자동화 수준과 처리량을 과장한다.
