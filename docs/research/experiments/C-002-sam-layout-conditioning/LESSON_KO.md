# C-002: 윤곽을 실제 조건으로 넣는다는 뜻

## 직관: 윤곽은 motion만 담지 않는다

양끝 이미지만 주면 모델은 두 상태 사이의 여러 가능한 움직임 중 하나를 만든다. C-001의 개는 검정/흰 외형을 유지해도 원본 8/16 시점의 정면 진행을 따르지 않았다. 이번에는 그 시점의 원본 대상 윤곽을 주어 중간 진행을 좁힌다. 다만 윤곽에는 source의 위치뿐 아니라 원본 Mini 차체와 개의 체형까지 들어 있다. 정보가 늘어도 target 외형과의 충돌 때문에 결합 품질은 낮아질 수 있다.

이를 $p(Y\mid A_0,A_{32},P)$와 $p(Y\mid A_0,A_{32},P,L_{1:31})$의 차이로 쓴다. 추가 조건은 원하는 정답을 보장하는 제약이 아니다. 기존 pretrained VACE가 해석해야 하는 새로운 입력 조합이며, 이 조합의 품질은 이번 실제 출력으로 판단한다.

## 수식: 세 변수를 분리한다

$S_t$는 SAM의 보이는 객체 영역이다. $L_t=\mathrm{Outline}_3(S_t)$는 흰 바탕에 검정 3px 외곽선을 그린 RGB다. $G_t$는 VACE의 생성 여부 마스크로, 양끝 전체 0·중간 전체 1이다. 검정 선을 생성 영역, 흰 바탕을 보존 영역으로 해석하지 않는다. $S_t$를 $G_t$로 넣지도 않는다.

조건 RGB는 세 가지다. ENDPOINT는 양끝을 제외하고 127, MOV는 시점별 $L_t$, STILL은 모든 중간에 $L_0$를 반복한다. STILL도 동일 생성 모델의 확률적 영상 출력이며 정지 사진 반복물이 아니다. MOV/STILL은 시간 변화의 유용성을 비교하지만, 정적인 $L_0$와 종료 앵커의 구조 충돌도 달라질 수 있어 완벽한 단일 인과효과라고 부르지 않는다.

## 실제 함수와 tensor

`prepare_layouts.render()`의 기존 OpenCV external/simple contour에 두께 3을 사용한다. 내부를 채우거나 팽창·침식·시간 smoothing을 하지 않는다. 미세 SAM speckle도 원래대로 남긴다. `video_generate.condition()`은 모드별 중간 RGB를 검사하고 양끝 RGB/G 검사를 공유한다. 생성 입력은 PNG/in-memory이며 검토 MP4나 source RGB overlay가 아니다.

실제 전처리 축은 B,C,T,H,W다. PIL RGB를 실행 dtype으로 옮겨$\bar X=2X/255-1$로 정규화한다. 흰 layout 바탕은 +1, 검정 선은 −1이다. uint8의 0은 정규화된 중립 0과 다르다. 기존 gray127도 정확한 중립 0이 아니다.

개념적으로 $U=E((1-G)\bar X)$, $R=E(G\bar X)$를 별도로 VAE 인코딩한다. Inactive 분기는 같은 양끝 앵커와 중간 중립 0, reactive 분기는 양끝 중립 0과 중간 layout을 받는다. 두 latent의 16+16 채널에 생성 마스크 64채널을 붙여 96채널 context를 만든다. 새 control branch나 채널을 checkpoint에 추가하지 않았다.

영상 시간 $t=0..32$와 생성 갱신 $s=0..49$는 다르다. 33프레임은 VAE 시간축 9개로 압축되고 50step은 같은 영상 latent를 갱신하는 횟수다. 공간은 480×832→60×104, 실제 첫 noisy latent는 [1,16,9,60,104], context는 [1,96,9,60,104]였다. 기존 nearest-exact 33→9 마스크는 양끝 0을 선택하지 않아 실제 마지막 64채널이 모두 1이었다. RGB 앵커는 inactive branch에 남지만 pixel-exact 출력 고정을 뜻하지 않는다.

`tensor_summary()`는 원래 첫 model_fn 직전 tensor를 읽기 전용 CPU contiguous uint8 view로 확인하여 BF16 원바이트 hash를 구한다. finite/범위/shape/dtype과 effective vace_scale 1.0도 기록한다. 모델 호출을 추가하거나 RNG 상태를 바꾸지 않는다. 새 MOV/STILL의 실제 noise hash를 비교하고, context 차이는 입력 전달 증거로만 사용한다. C-001은 최초 noise hash가 없어 과거 bitwise 동일성을 주장하지 않는다.

## 관측을 해석하는 순서

같은 frame index의 source/ENDPOINT/MOV/STILL을 비교한다. 위치·크기와 회전이 맞아도 내부 관절/고개/접촉은 틀릴 수 있다. 특히 개의 종료 anchor가 source의 자세와 충돌하므로 모든 조건의 동시 정확 일치는 보장되지 않는다. Source silhouette을 따라 원본 체형으로 돌아가면 단순 IoU는 좋아질 수 있지만 target 체형 전이 성공은 아니다. 출력에 새 segmentation/pose 모델을 돌려 정답처럼 채점하지 않는다.

실제 결과는 차량 TRADE_OFF, 개 COARSE_CONTROL_ONLY였다. 개는 MOV에서 거친 접근이 개선됐지만 머리·관절·접촉은 미해결이고, 차량은 장면 손상이 동반됐다. 자세한 같은 인덱스 관측은 [RESULTS](RESULTS.md)에 기록한다. 33장의 연속 프레임은 33개 독립 실험이 아니다. 파일 decode/브라우저 재생은 temporal 품질 검수와 다르며 실제 연속 지각 검수가 없으면 UNVERIFIED다.

## 이해 확인

1. 흰 layout 바탕은 보존 영역인가? 아니다. layout은 RGB 조건이며 생성/보존의 구분은 별도 G가 담당한다.
2. MOV의 source 윤곽 IoU가 높으면 성공인가? 아니다. source 체형 회귀로도 높아질 수 있어 target 외형·내부 동작·장면을 함께 본다.
3. 같은 seed이면 C-001과 noise가 bitwise 같다고 할 수 있는가? 아니다. 이번 새 실행끼리는 실제 hash로 확인하지만 과거 C-001은 그 관측 자료가 없다.
4. MOV가 STILL보다 좋으면 순수 시간 정보 효과인가? 단정할 수 없다. 윤곽의 시간 변화와 종료 앵커 충돌 정도의 차이가 함께 있다.

이 기준선은 새 체형 전이 모듈이 아니다. 실제 상충이 외형이면 target-aware 구조 표현, 위치만 맞고 내부 동작이 틀리면 내부 대응, 효과가 불명확하면 연결 방법의 미검증을 다음 논의 후보로 삼는다. 추가 모듈·학습·GPU 탐색은 이번에 시작하지 않는다.
