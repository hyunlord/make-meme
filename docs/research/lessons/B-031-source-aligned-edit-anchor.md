# B-031: 생성 앵커와 영상 전이의 역할 분리

이 문서는 실행 코드의 계산 계약을 설명한다. 실제 생성 수·성공·실패는 [RESULTS](../experiments/B-031-source-aligned-edit-anchor/RESULTS.md), 단계별 판정은 [STAGES](../experiments/B-031-source-aligned-edit-anchor/STAGES.md)를 따른다. 코드가 존재한다는 사실은 영상 품질의 증거가 아니다.

## 1. 직관: 참조 자세를 지우는 대신 시작 자세를 맞춘다

기존 참조는 원하는 대상의 외형과 그 사진의 자세·배경을 함께 담는다. 배경을 회색으로 바꾸어도 자세가 제거되지 않는다. B-031은 대상의 모습과 source 첫 자세를 동시에 만족하는 정지 편집 결과 A0를 먼저 만들고, 그것을 영상 모델의 참조로 사용한다. 정지 편집기가 이를 해결하는지는 실험 대상이며 가정할 수 없다.

설명용 확률 모형은 다음과 같다.

\[
A_0\sim p_\phi(A\mid V_0,R,P_I),\quad
R_* = M_A\odot A_0+(1-M_A)\odot(128,128,128),\quad
Y\sim p_\theta(Y\mid V,R_*,P_V,M_D,\mathrm{replacement}).
\]

V는 source 영상, V0는 첫 RGB 프레임, R은 target track의 사진, PI는 정지 편집 지시, PV는 고정된 영상 caption이다. MA는 생성 A0에서 실제 대상의 support, MD는 source의 기존 driving 의미 마스크다. R*는 uint8 RGB 처리의 설명식이다. 모델 내부 정규화 범위에서 숫자128을 곧바로 곱하는 식이 아니다.

A0는 Y의 ground truth가 아니며, 두 모델의 오차가 누적될 수 있다. source를 그대로 복사하면 source 자세·장면은 맞아도 identity-changing 편집은 실패한다. target 사진을 그대로 옮기면 외형은 보여도 source 자세·위치가 어긋난다. 이 두 실패를 별도로 검사해야 한다.

## 2. 입력과 실제 tensor 경로

[prepare_inputs.py](../experiments/B-031-source-aligned-edit-anchor/code/prepare_inputs.py)는 모든 6개 입력에 같은 GT bbox + 10% margin 규칙을 적용한다. Image1은 source 전체896×512, Image2는 target 원천 RGB의 crop이며 support 밖만128이다. crop의 고정 규칙은 대상의 자세를 source 실루엣으로 변형하는 연산이 아니다. 작은 crop의 화질 부족과 가림은 그대로 남는다.

[qwen_runner.py](../experiments/B-031-source-aligned-edit-anchor/code/qwen_runner.py)의 `QwenImageEditPlusPipeline` 호출은 `image=[Image1, Image2]` 순서를 유지한다. 고정 model revision은 `6f3ccc0b56e431dc6a0c2b2039706d7d26f22cb9`다. 파이프라인 내부 vision/VAE용 resize와 실제 입력 이미지는 별도 evidence로 보존한다. 두 이미지가 파일 수준에서 같은 크기여야 하는 것도, 원래 crop 크기 그대로 내부 encoder에 들어가는 것도 아니다. 실제 내부 shape는 runtime 기록의 값을 읽어야 한다.

R1 A0가 사전 평가를 통과한 경우에만 [phase_reference.py](../experiments/B-031-source-aligned-edit-anchor/video_code/phase_reference.py)가 R*를 인코딩한다. 이 함수의 명시적 입력 계약은 RGB와 semantic mask 각각 `[3,512,896]`이다. mask helper의 prefix 계약은 `[28,1,64,112]`이며 7색상 채널의 시간 패킹을 포함한다. 이것은 RGB alpha matte가 아니다.

같은 함수는 공식 `WanVAE.encode([rgb[:,None]])`와 `CLIPModel.visual([rgb[:,None]])`를 각각 호출한다. VAE reference는 CTHW 배열이며 예상 `[16,1,64,112]`; CLIP의 실제 shape·dtype는 고정 parent cache와 비교한다. 이 문서의 예상 shape를 실제 관측으로 대신하지 않는다. 새 reference의 VAE·CLIP·semantic mask만 양 CFG branch에 연결한다. T5·driving VAE·target VAE·DiT는 이 encoder 단계에서 다시 계산하지 않는다.

[anchor_contract.py](../experiments/B-031-source-aligned-edit-anchor/video_code/anchor_contract.py)는 양 branch의 reference 관련 최대6개 leaf만 변경하도록 검사한다. 같은 값이 우연히 나오는 leaf까지 반드시 달라야 한다는 조건은 없다. driving·text·noise·RNG·scheduler의 불변과 reference의 실제 변경 허용을 구분한다.

## 3. 앵커는 frame0 hard constraint가 아니다

SCAIL은 R*를 VAE prefix와 image context 등의 조건으로 사용한다. `[reference 조건, generated latent, driving 조건]`의 계산 경로에서 정보가 상호작용하지만 R*를 출력 첫 프레임으로 강제 복사하지 않는다. 따라서 A0의 자세가 맞아도 영상의 첫 프레임 또는 후반 형태가 달라질 수 있다.

설명용 조건부 속도장을 \(v_\theta(z_\tau,\tau;c)\)라 쓰면, 고정된 noise에서 조건 c가 바뀔 때 sampling 경로도 바뀐다. CFG는 같은 noisy latent에서

\[
\hat v=u(z_\tau,c_{\rm visual})+w\{c(z_\tau,c_{\rm visual},P_V)-u(z_\tau,c_{\rm visual})\}
\]

로 설명할 수 있다. 여기서 `c`라는 양성 prediction 기호와 조건 묶음은 혼동하지 않아야 한다. 실제 구현은 [phase_sample.py](../experiments/B-031-source-aligned-edit-anchor/video_code/phase_sample.py)의 고정 공식 sampler 추출 경로다. 양 branch의 `ref_latents`, `clip_fea`, `pose_latents`, `ref_masks` 객체 연결을 최초 forward에서 확인하고, 별도 관측용 forward를 실행하지 않는다.

40개의 scheduler step은 17개의 영상 frame과 다른 축이다. τ는 denoising/noise 시간, frame index k는 영상의 순서다. 기존 CFG로40step·80forward를 수행하며, preview24fps는 원본 FPS가 확인됐다는 뜻이 아니다. `source_fps=null`, `timebase_assumed=true`를 유지한다.

## 4. 순차 메모리 수명과 비용

Qwen의 이미지 모델과 SCAIL의 큰 DiT를 동시에 상주시켜야 할 수학적 이유는 없다. A0를 CPU 파일로 저장한 후 이미지 worker를 종료하고, SCAIL 조건 인코딩·sampler·VAE decode를 별도 worker에서 순차 실행한다.

\[
\mathrm{peak}_{\rm sequential}\ne \mathrm{size}(W_Q)+\mathrm{size}(W_S),\qquad
T_{\rm total}=T_{\rm download}+T_{\rm load}+T_{\rm image}+T_{\rm mask}+T_{\rm encode}+T_{\rm sample}+T_{\rm decode}+T_{\rm review}.
\]

첫 식은 peak가 두 파일 크기의 단순 합이 아니라는 뜻이지, sequential peak가 항상 작고 안전하다는 보증이 아니다. CPU offload는 통합 메모리 장치에 새 물리 RAM을 만들지 않는다. parameters·activations·allocator cache·파일 매핑·임시 복사가 각 phase에서 다르게 존재한다. 시스템 MemAvailable, RSS, cgroup, CUDA allocated/reserved는 중복되는 회계가 있어 합산하면 안 된다.

[phase_sample.py](../experiments/B-031-source-aligned-edit-anchor/video_code/phase_sample.py)의 완료 callback은 실제40step·80forward, finite, latent shape를 확인하고 final x0를 decode 전에 원자적으로 저장한다. 이 latent는 initial noise나 reference prefix가 아니며, reference prefix를 제외한 generated 구간이다. decode 실패가 sampling 재실행 권한을 만들지 않는다.

## 5. 결과를 해석하는 단위

A0 실패는 정지 편집 실패다. A0가 적합하지만 영상에서 자세·형태·장면이 무너지면 영상 전이 단계의 한계다. 두 단계가 모두 양호해도 공개 개발 패널의 제한된 사례이며, 미사용 일반화나 새로운 알고리즘의 증거가 아니다. R1만 사전 영상 대상으로 정했으므로 R2가 더 좋아도 교체하지 않는다. 영상이 생성되지 않은 case도 표에서 제외하지 않는다.

실제 결과는 RESULTS의 여섯 앵커와 최대 세 영상 표를 함께 읽는다. 프레임 시트의 정적 판독, MP4 디코딩 가능, 실제 사람의 연속 시청은 서로 다른 증거다. 연속 시청 기록이 없으면 temporal=UNVERIFIED다. 두 모델을 연결했으므로 전체 비용을 기존 단일모델과 비교해야 하며, 단일 sampler 시간만으로 효율 개선을 주장할 수 없다.

## 6. 이번 실행에서 관측된 tensor와 실패 위치

Human R1의 실제 encoder hook 기록에서 vision `image_grid_thw=[2,3]`, `pixel_values=[1504,1176]` shape를 확인했다. `[2,3]`은 두 이미지의 grid metadata 행렬 크기이지 이미지의 공간 크기가 아니다. VAE 입력은 source `[1,3,1,768,1344]`, target `[1,3,1,1056,992]` BF16이었다. 요청 출력896×512와 encoder 입력 resize를 혼동하지 않아야 한다.

첫 DiT 호출의 `hidden_states=[1,9916,64]`, positive text `[1,504,3584]`, negative text `[1,396,3584]`가 기록됐다. 공간 패킹에 따른 generated1792 + source4032 + target4092 =9916 token으로 shape가 연결된다. 이는 입력 길이 확인이며, 특정 token이 identity나 pose를 담당한다는 인과 증거가 아니다. 최종 생성 packed latent는 `[1,1792,64]` BF16으로 분리 저장됐다.

6개 A0는 모두 기술적으로 저장됐다. 정적 판독에서 animal R1은 검은 장모 외형을 반영했지만 낮은 참조 자세가 남았고, human R1은 의상은 반영했지만 source 팔/다리 배치 대신 참조 방향과 펼친 치마를 따랐다. 두 사례는 정지 편집 단계에서 막혔으므로 영상 전파를 실행하지 않는다. R2에서 일부 자세가 나아 보여도 사전 R1 선택을 바꾸지 않았다. Vehicle R1은 높은 은색 차체와 source의 우향·중앙 하단 배치를 함께 반영하여 정적 영상 진입 후보가 됐다. 이후 영상 결과는 RESULTS에서 분리한다.

이미지 worker의 CUDA peak allocated는60,057,443,328bytes, peak reserved는63,206,064,128bytes였다. 샘플링된 시스템 최소 MemAvailable은27,847,270,400bytes, swap 사용은0이었다. `pipeline_released`라는 phase 이름에도 실제 allocated40,917,650,944bytes가 남았다. 따라서 `del`/`empty_cache`만으로 완전 해제를 주장하지 않는다. 남은 참조 원인은 UNKNOWN이며, 실제 프로세스 종료(MainPID0)와 시스템 가용 메모리96,412,590,080bytes 회복을 별도로 확인한 뒤 SCAIL을 시작했다. cgroup/RSS/CUDA/시스템 수치를 합산하지 않는다.

B-031의 R_star는 B-027보다 생성된 외형, source에 맞춘 방향·위치·크기, 수동 support가 함께 달라진다. 차량이 개선되더라도 순수한 pose 하나의 인과효과나 Qwen 모델 자체의 필수성을 입증하는 비교가 아니다. 원래 여섯 입력 중 animal/human R1의 정지 편집 실패와 영상 미실행을 유지한 채 분해형 기준선 전체를 평가한다.

차량 영상은 실제40step·80forward와 finite `[3,17,512,896]` decode,17프레임 MP4 저장을 통과했다. 전체17장 정적 판독에서는 높은 은색 차체와 대략적인 회전 진행이 관측됐지만, A0에는 없던 큰 차량 부품형 그래픽이 좌하단 보호 노면에 나타나 지속됐다. 따라서 정지 앵커 적합성과 영상 보호 장면 성공은 분리되며, 후자는 FAIL이다. 그래픽의 특정 encoder·attention 원인은 이 관측으로 식별할 수 없다. 원본과 정확한 회전량·접지·시간적 안정성은 UNCERTAIN/UNVERIFIED이며 결합 목표 개선은 미입증이다.

## 이해 확인 질문

1. A0가 target을 잘 닮고 source 첫 자세도 맞으면 영상 전체의 motion 성공을 바로 선언할 수 있는가?
2. R*의 대상 픽셀이 A0와 동일하면 VAE와 CLIP 특징도 대상 내부에서 동일하다고 볼 수 있는가?
3. 이미지 모델 worker 종료 후 영상 모델을 로딩하면 왜 메모리가 안전하다고 자동 판정할 수 없는가?

## 별도 해설

1. 아니다. A0는 조건이지 hard clamp가 아니다. 후속 영상 모델이 source의 변화 방향·순서·타이밍을 유지하는지 별도로 비교해야 한다. 정지 참조 복사는 motion 성공이 아니다.
2. 아니다. 인코더 receptive field와 attention이 주변 문맥을 사용하므로 중립 배경 처리도 특징을 바꾼다. RGB 픽셀 보존은 특징 불변을 뜻하지 않는다.
3. 프로세스 분리는 동시 모델 상주를 줄이지만, 현재 로딩·생성 단계 자체의 peak가 가용 통합 메모리보다 클 수 있다. 실제 회복 상태와 단계별 guard를 확인해야 한다.
