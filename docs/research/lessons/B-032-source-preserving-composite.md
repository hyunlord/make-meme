# B-032 — 의미 마스크, 객체 alpha, 편집 영역의 차이

## 직관: 생성기를 바꾸지 않고 어느 픽셀을 쓸지 바꾼다

B031 차량 raw에는 target형 차량과 큰 도로 그래픽이 함께 있다. B032는 기존 raw의 내용이나 움직임을 다시 생성하지 않는다. 원본을 쓸 곳과 기존 생성을 쓸 곳을 명시해 같은 raw의 저비용 대조군 두 개를 만든다. 원본을 복사한 구간이 정확해지는 것은 합성기의 성질이며, 모델이 원본 보존을 학습한 결과가 아니다.

세 종류의 mask를 구별한다.

| 표현 | 뜻 | 이번에 하는 역할 |
|---|---|---|
| SCAIL semantic mask | 색상과 시간 패킹으로 학습된 대상/배경 조건 | 기존 생성 때 쓰인 조건, 이번에 재인코딩하지 않음 |
| 객체 alpha | 물리적 혼합·가림을 근사하는 전경의 투명도 | 이번 coarse polygon은 정밀 alpha matte가 아님 |
| 편집 가중치 E | 출력에서 generated를 사용할 비율 | 원본 객체 제거 영역과 새 실루엣·필요 배경까지 포함 |

## 수식과 가정

같은 좌표의 source RGB를 V, 기존 generated RGB를 G라 하면

\[
Y_{t,c,y,x}=(1-E_{t,y,x})V_{t,c,y,x}+E_{t,y,x}G_{t,c,y,x}.
\]

E는 `[T,H,W]`, V/G/Y는 같은 색·범위의 `[T,H,W,C]` 또는 대응하는 CTHW 배열이다. 이번 T=17,H=512,W=896,C=3이며 변환은 실행 코드에서 명시한다. 시간 t는 영상 frame index이지 diffusion noise time이 아니다. 이번에는 noise step을 실행하지 않는다.

E=0이면 source exact, E=1이면 generated exact다. 이를 보장하려면 두 입력을 같은 수치 범위로 맞추고 경계만 float로 혼합해야 한다. MP4로 인코딩한 뒤의 디코딩 픽셀은 압축 때문에 이 원시 배열의 exact 조건과 다를 수 있다. 표시용 uint8 변환과 계산 검증을 구분한다.

원본 객체 support S와 새 대상 support T가 다르면 T만 사용하는 것은 충분하지 않다. T 밖에 있던 원본 바퀴·차체가 남을 수 있기 때문이다. 반대로 S만 쓰면 새 차량의 높은 루프·넓은 실루엣이 잘린다. 따라서 mask-assisted 기준은

\[
U_t=S_t\cup T_t\cup H_t,
\qquad C_t=\operatorname{dilate}(U_t,r)
\]

를 사용한다. H는 확인 가능한 직접 접촉 그림자를 별도로 표시했을 때만 포함한다. 불명확한 그림자를 정답처럼 채우지 않는다. r은 clip의 source bbox 긴 변 L에서 `max(2,ceil(0.02L))`로 고정하며, core C 안은1이고 바깥4px band만1→0으로 변한다.

FIXED_ENVELOPE는 source17장과 A0 support의 합집합 bbox에 각 방향10% margin을 더하고 안쪽8px feather를 적용한다. generated 영상의 그래픽을 보고 ROI를 줄이지 않는다. 이 정적 영역은 간단하지만 불필요한 생성 배경도 더 많이 포함할 수 있다.

## 실제 코드와 검증

[compositor.py](../experiments/B-032-source-preserving-composite-baseline/code/compositor.py)의 `fixed_envelope`가 정적 bbox 정책을, `radius_for_sources`와 `mask_assisted`가 source-target union 정책을 계산한다. `blend`는 HWC RGB와 HW 편집 가중치의 shape·범위를 검사하고 합성하며, `to_uint8`는 표시·인코딩용 변환이다. 실측 bbox·반경·면적·coverage는 [SUPPORTS](../experiments/B-032-source-preserving-composite-baseline/SUPPORTS.md)와 [REPRODUCE](../experiments/B-032-source-preserving-composite-baseline/REPRODUCE.md)에 연결한다. 코드의 존재만으로 시각 수용을 선언하지 않는다.

[build_review.py](../experiments/B-032-source-preserving-composite-baseline/media_code/build_review.py)의 `sheets`는 네 조건 전체17장을 동일 canvas 크기로 표시한다. `CROPS`는 local0/8/16의 차체·바퀴/접지·하단 그래픽을 모든 조건에서 같은 좌표로 보여준다. 이 확대는 검토 이미지일 뿐 실제 영상을 warp하거나 좋은 부분만 출력하는 연산이 아니다. MP4는 existing source/raw 두 개와 새 합성 파생물 두 개를 구분한다.

## 배경 재노출·그림자·가림의 한계

새 차량의 체형이 작아져 원래 차량 뒤의 바닥이 드러나야 한다면, 그 바닥은 source의 가려진 영역에 실제 관측값이 없다. S를 포함해 G를 가져와도 G가 잘 복원했는지 확인해야 한다. 단순 합성식이 미관측 배경을 알아내지는 못한다.

그림자는 객체 투명도와 다른 현상이다. 원본 그림자와 새 차량 그림자가 동시에 남으면 이중화될 수 있고, 둘 다 잘리면 부유해 보일 수 있다. coarse support와 고정 dilation은 그림자의 물리적 정확성을 보장하지 않는다. 얇은 경계, 접지, 반사, 앞쪽 occluder는 별도로 UNCERTAIN/MASK_PARTIAL을 기록한다.

그래픽이 E=0 영역에 있으면 source 복사로 없어지지만 E=1 내부나 차량과 겹치면 그대로 남는다. 그때 해당 오염만 수동으로 지워 합성 기준선을 유리하게 만들지 않는다. 결과는 [RESULTS](../experiments/B-032-source-preserving-composite-baseline/RESULTS.md)의 실제 관측을 따른다.

## 이번 실측과 정적 관측

실행된 정적 bbox는 exclusive `(147,162,754,423)`, mask-assisted dilation은11px였다. 두 조건 모두17장에서 E=0/source와 E=1/generated의 float·표시용 uint8 exact 검사가 통과했고, 주석된 target support의 core 밖 pixel은0이었다. 이것은 주석된 support를 자르지 않았다는 검사이지, coarse polygon이 실제 모든 털·반사·그림자를 정확히 포함했다는 증거가 아니다. H는 불확실하여 빈 집합으로 남겼다. target polygon의 약15px 불확실성 표시는 독립 ground truth나 보정된 통계 오차가 아니며, 그림자·얇은 경계의 수용을 대신하지 않는다.

local0/8/16 정적 확대에서 두 합성은 큰 도로 그래픽을 줄이면서 흰색 target형 차체와 거친 회전을 유지했다. 고정 영역은 하단 그래픽 조각을 더 크게 남겼고, mask-assisted에서도 뒤 바퀴 아래/뒤쪽에 붉은 획이 남았다. 이 획은 편집 영역 안의 G에 존재하므로 source-exact 바깥 검사가 통과해도 제거되지 않는다. 차체 주변의 바닥 색차·접지·그림자 경계는 별도 한계이며, 시간 경계 흔들림은 연속 시청 전 UNVERIFIED다. 최종 판정은 전체17장 검토를 포함한 RESULTS에 기록한다.

## 출력 합성과 생성 중 제약

출력 합성은 완료된 RGB 두 장의 선택·혼합이다. 생성 중 제약은 noise level별 latent와 solver 상태에서 원본 문맥을 반영하는 다른 계산이다. 이번에는 후자를 구현하거나 효율·품질 이득을 주장하지 않는다. 향후 방법은 raw뿐 아니라 이 저비용 합성 대조군 대비 경계·그림자·편집 내부 오류 또는 수동 노동을 얼마나 줄이는지 확인해야 한다.

기존 B031의 generation 비용은 이미 지출됐다. 새 GPU 계산0은 기존 비용0이 아니다. mask 준비, CPU 합성, 새 영상 인코딩, 검토, 패키징·전송을 별도 비용으로 보고한다. 한 차량의 정적 개선은 동물·사람 앵커 자세 실패나 다양한 객체의 자동 편집을 해결한 증거가 아니다. 실제 연속 시청이 없으면 temporal=UNVERIFIED를 유지한다.

## 이해 확인 질문

1. E=0 영역의 source 오차가0이면 영상 모델의 장면 보존 능력이 개선됐다고 말할 수 있는가?
2. 새 차량 T만 정확하게 따낸 뒤 source에 붙이면 왜 원본 차량 잔상이 남을 수 있는가?
3. MASK_ASSISTED가 FIXED_ENVELOPE보다 깨끗해도 자동 편집 성공이라고 할 수 없는 이유는 무엇인가?

## 별도 해설

1. 아니다. 원본 값을 직접 복사하는 산술적 계약을 검증한 것이다. target 외형·동작·경계와 편집 면적을 함께 봐야 한다.
2. S에서 T 밖으로 나오는 원본 차체·바퀴 영역이 제거되지 않기 때문이다. S와 T의 union이 필요하지만 union 내부의 G 자체가 잘못됐으면 합성만으로 해결되지 않는다.
3. 실제 출력의 대상 support를 사후 agent가 표시했기 때문이다. 동일한 품질을 자동으로 얻는 방법, 주석 불확실성, 시간적 안정성, 비용은 별도 미해결 항목이다.
