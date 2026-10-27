# CONTINUATION_01 support freeze

S는 기존 공개 원본 RED semantic support를 그대로 읽었다. 17장 파일 해시가 부모와 정확히 같다. T는 RECOVERY_01에서 실제 생성된 **SUV/왜건형 차량**의 agent coarse polygon이다. 원하는 노출 바퀴·클래식 target의 GT가 아니며, A0 silhouette로 대신하지 않았다. H=empty로 유지했다.

주석/정적 검토는 07:16:50–07:20:59 UTC, 약 250초다. 전체 17프레임의 BASE를 보고 각 frame의 윤곽을 표시했다. STEP/CONTROL 출력은 아직 없었다. 독립 인간 정답이나 자동 segmentation으로 보고하지 않는다. 얇은 mirror, 바퀴 외곽, 어두운 underbody/접촉 경계는 **MASK_PARTIAL**이다. 후반 우측 하부의 coarse 오차가 남는다. 보이지 않는 면이나 shadow를 추정해 채우지 않았다.

## 고정 계산

기존 B034 `compositor.py`의 `radius_for_sources`와 `mask_assisted`를 변경 없이 사용했다. source clip union bbox의 긴 변 L=178px로 r=max(2,ceil(0.02L))=4px를 얻었다. U=S∪T를 Euclidean 4px로 확장한 core에 E=1, 그 외곽 4px feather를 적용했다. H는 공집합이다.

기존 `clean_constraint.py::latent_mask` 함수 본문을 AST로 그대로 읽어 CPU에서 실행했다. Wan/scheduler 전체 import를 피하기 위한 로딩 방식이며, 함수 수식 변경은 없다. 시간 max 그룹 [0],[1..4],[5..8],[9..12],[13..16] → 공간 8×8 max → 3×3 guard를 유지한다. E=[17,512,896] FP32, M=[1,1,5,64,112] FP32이고 M 평균은 0.0570869595다. 이는 자유 편집 support의 평균이며 품질 지표가 아니다.

S/T core의 E=1과 대응 latent coverage M=1을 실제 검사했다. 고정 해시와 원래 함수 파일 SHA는 [SUPPORT_FREEZE.json](SUPPORT_FREEZE.json)에 있다. private MASK_FREEZE에는 17 S/T 파일, E/M, 주석의 해시와 평가 crop이 들어 있다. 본체 및 하부 접촉 crop은 source/BASE를 보고 STEP 전에 고정했으며 이후 변경하지 않는다.

## 해석 범위

잘못 생성된 BASE SUV를 기준으로 잡은 E/M이 바람직한 새 target의 더 다른 실루엣을 제한할 수 있다. STEP이 영역 밖으로 나가도 mask를 늘려 구제하지 않는다. 이 한계는 input/output-mask-assisted 비교의 일부다. 동일 E로 세 결과를 후합성하며, E=0 원본 exact는 합성식의 성질이지 모델 성능이 아니다. 대상 외형이 애초에 없으므로 그 외형의 non-regression을 PASS로 만들지 않는다.

고정 detail crop은 모든 source-union 경계를 포함하지 않는다. 우측 crop 밖의 도로 seam·잔상은 full-frame 17장과 영상에서 함께 검토한다. BASE_RGB_POST f16에서 이 범위의 도로 톤 차이와 하부 조각이 관측됐으며, crop이나 E를 사후 변경하지 않았다.
