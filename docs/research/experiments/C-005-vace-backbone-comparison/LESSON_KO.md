# 같은 조건에서 모델을 바꾼다는 것

## 직관과 질문

C-002의 동적 윤곽은 위치·실루엣을 주지만 내부 자세나 보호 배경을 모두 주지 않는다. 더 큰 모델은 그 빈 부분에 다른 사전 지식을 적용할 수 있다. 그러나 원하는 원본 동작을 정확히 채운다는 보장은 없다. 이번에는 새 대응 모듈보다 먼저 동일 입력에서 두 공식 checkpoint의 실제 품질과 비용을 확인한다.

## 수식과 실제 입력

영상 결과를 Y, 양끝 앵커를 A0,A32, 동적 윤곽을 L1:31, 텍스트를 P라 하면 비교하는 것은 서로 다른 모델 θ의 `pθ(Y | A0,A32,L1:31,P)`다. 조건을 고정하더라도 θ에는 크기뿐 아니라 학습된 가중치와 구조 차이가 함께 들어 있다. 따라서 파라미터 수 하나의 인과효과가 아니다.

SAM 영역 S_t는 윤곽 L_t를 만드는 재료이며 VACE의 생성 마스크 G_t와 다르다. 이번 X0/X32는 원래 앵커, X1..31은 기존 L_t다. G0/G32는0, 중간은1이다. 실제 normalized domain에서 `U=Encoder((1-G)*Normalize(X))`, `R=Encoder(G*Normalize(X))`를 만들고 U16+R16+mask64로 context96채널을 구성한다. 내부 중립값0은 uint8 검정0이 아니다.

33개의 영상 시간 표본 t가 VAE에서9개 latent 시간으로 압축된다.50개의 denoising step s는 이 latent 영상을 점진적으로 갱신하는 생성 진행도이며50프레임을 뜻하지 않는다. 기존 nearest-exact33→9에서 양끝0 mask가 빠지는 한계를 유지하되 inactive RGB 앵커가 존재하는 사실과 구분한다. 끝 프레임을 앵커로 덮어쓰지 않는다.

## 함수와 비용

`video_generate.condition`은 C-002와 픽셀 단위로 같은 X/G를 만든다. 변경된 연결은 exact shard index와 native ModelConfig memory 옵션이다. 최초 model_fn에서 noise/context/mask를 읽고, 원래 scheduler.step50 뒤 latent를 원자 저장한다. 관측을 위한 추가 DiT forward는 없다.

BF16 가중치 bytes는 전체 peak가 아니다. 저장 F32/BF16, meta 초기화, tensor별 cast, T5 clone, file cache, CUDA allocator와 activation이 다르게 생존한다. disk onload는 CPU에 전체 diffusion 사본을 두지 않지만 I/O와 실행 비용을 늘릴 수 있다.24GiB cache 기준은 hardcap이 아니므로 실제 host/cgroup/CUDA/headroom을 각각 기록한다.1.3B와 다른 offload 경로의 비용을 순수한 아키텍처 속도 차이라고 부르지 않는다.

## 결과와 반례

실제 두 출력의 관측은 완료 후 [RESULTS](RESULTS.md)에 연결한다. 큰 모델도 target을 잘 그리면서 source 움직임을 놓치거나, 더 자연스러운 새 배경을 만들어 보호 장면을 해칠 수 있다. 둘 다 결합 목표 성공이 아니다. 같은 noise·context hash도 품질 개선의 증거가 아니다.

## 이해 확인

Q.14B가 더 예쁜 강아지를 만들면 이번 목표의 성공인가? A. 아니다. 머리·보이는 발의 진행과 target 외형, 배경 보호를 함께 비교해야 한다.

Q.32.294GiB BF16 가중치면64GiB worker에서 항상 안전한가? A. 아니다. T5/VAE, 임시 복사, activation, allocator/file cache를 포함한 실제 경로가 다르며 안전 보장은 아니다.

Q.두 모델의 seed만 같으면 비교 입력이 같다고 할 수 있나? A. 실제 noise bytes와 X/G·텍스트·scheduler를 확인해야 하며, memory path 차이는 별도로 한정한다.
