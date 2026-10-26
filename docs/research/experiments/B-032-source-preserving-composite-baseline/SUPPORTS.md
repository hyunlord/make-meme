# B-032 편집 support

두 결과는 같은 B-031 lossless raw를 사용했다. 원본 GT의 선택 객체 RED 픽셀을 S로 읽고, 기존 A0 support를 고정 영역 계산에 사용했다. 생성 결과를 보고 고정 영역을 조절하지 않았다.

FIXED_ENVELOPE는 source 17장과 A0 support union bbox의 각 방향을 폭·높이의 10%씩 확장했다. 좌상은 floor, 우하는 ceil, canvas로 clip했다. 실제 exclusive xyxy는 `[147,162,754,423)`이다. Rectangle 경계에서 픽셀 중심의 안쪽 거리를 8로 나눈 선형 feather를 사용하므로 첫 안쪽 중심의 값은 0.5/8이다. 같은 E를 17장 모두에 적용했다.

MASK_ASSISTED의 T는 실제 생성 영상의 주행 차량을 agent가 프레임마다 그린 17개 polygon이다. 전 17장의 raw와 polygon 시트를 확인했으며 source GT 복사나 프레임 간 보간은 사용하지 않았다. 전체 annotation wall time은 345.005초다. 얇은 안테나·roof rail과 wheel/contact contour는 약 최대 15px의 coarse 불확실성이 있고 `MASK_PARTIAL`이다. 독립 human GT나 자동 segmentation 결과가 아니다.

접촉/투사 그림자를 확실히 구분할 수 없어 H는 모든 프레임에서 비어 있다. 그림자가 없다는 판정이 아니다. 그림자 누락과 경계 부조화는 미해결이다.

U=S∪T의 Euclidean dilation 반경은 source clip bbox 긴변으로 계산한 r=11이다. dilation core는 E=1이고 바깥 4px를 선형 feather했다. 모든 프레임에 같은 규칙을 적용했다. 결과를 본 뒤 polygon·반경·feather를 수정하지 않았다.

실제 17장 검사에서 두 방법 모두 주석된 T의 E=0 밖 픽셀 0, E<1 픽셀 0, S의 E<1 픽셀 0이다. 따라서 **주석된 support에 대해** SUPPORT_UNDERSHOOT는 관측되지 않았다. 미주석 얇은 부위까지 완전한 coverage라는 뜻은 아니다.

합성 전 RGB/CTHW와 프레임 순서를 확인했다. raw는 FP32 `[3,17,512,896]`, 범위 [-1,1]이며 CPU에서 THWC로 옮겼다. source bytes는 FP32 `source/127.5-1`로 표현했다. E=0/1은 명시적인 원본 float 복사로 검증했다. PNG는 `floor((clip(y,-1,1)+1)*127.5)`이며 E=0은 원본 uint8을 다시 직접 복사하여 round-trip 오차를 피했다. E=1은 같은 규약의 generated uint8과 정확히 같다. 이 pixel exact는 MP4 손실 인코딩 전의 성질이다.

지원영역 시각화 PNG는 E를 255 단계로 표시한 검토용이며 합성에는 float E를 사용했다. `code/compositor.py`가 정책의 실행 정의이고 private `polygons.json` 및 frozen manifest가 재현 입력이다.
