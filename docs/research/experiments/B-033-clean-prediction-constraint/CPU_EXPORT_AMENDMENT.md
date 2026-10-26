# CPU PNG endpoint export 보정

GPU 실행 전 고정한 `postcompose.py`는 보존하고 사용하지 않는다. source uint8을 model-space float로 변환한 뒤 floor로 다시 uint8로 만들면, E0 영역의17프레임에서3,585,163개 채널 값이 원본과 최대1/255 달랐다. 이것은 마스크나 생성 결과의 차이가 아닌 부동소수점 왕복 양자화 문제다.

새 `postcompose_export.py` SHA256 `4135627e1a6aada074bc67729b145d0f1e2565a473e332b229507380aa9433e4`는 동일한 Efloat·blend 수식·고정 source/target support를 사용하되, 저장 PNG에서 E0은 원본 source uint8을 명시적으로 복사하고 E1은 decoded raw의 고정 floor 양자화값을 복사한다. PNG를 실제로 다시 읽어 두 endpoint를 검사한다. 경계 float 혼합은 같다.

이 변경은 이미 요구한 exact-E0 계약을 지키기 위한 CPU export 수정이다. 마스크·생성계수·VAE·sampler·CFG·입력·noise는 변경하지 않았다. 기존 frozen script와 실행 freeze를 덮어쓰지 않았다. 추가 encode/decode/sampler는0이다. 결과를 유리하게 바꾸는 경계 조정이 아니다.
