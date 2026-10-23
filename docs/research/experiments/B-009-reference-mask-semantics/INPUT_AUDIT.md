# B-009 입력 마스크 독립 검증

상태: **PASS_CPU_ONLY**. GPU 또는 모델 forward를 실행하지 않았다. 기존 B-008 원본을 변경하지 않고 새 마스크만 읽어 검사했다.

| 항목 | 관측 |
|---|---|
| 이미지 크기 | 512×896, RGB |
| RED 전경 | 113,928픽셀; RGB 값과 위치가 이전 마스크와 완전히 같음 |
| BLACK→WHITE | 344,824픽셀; 기존 BLACK 위치에서만 변경 |
| 기타 색상 | 0픽셀 |
| 원본 reference RGB | SHA256 `703884c8e2a657d4294cf4e74efeb463c9cd6e05e1ad582f99d6546b954cfdce` |
| 기존 마스크 | SHA256 `281d5d7ebacfc510b2eba8cedc2b12cc9e5399c5024715e67a5006859cf8d6f3` |
| 새 마스크 | SHA256 `ea54f417f109793210c405d2452152b839fd57f81329811fb650958e830bab9f` |
| 새 전처리 tensor | float32 `[3,896,512]`, 값 SHA256 `67c43d812cd0f8f889defa496357929aae73d96b0a6ac9421c1eb9e1ffbd3ff3` |
| 기존 전처리 tensor | float32 `[3,896,512]`, 값 SHA256 `3db4b9af4beec7cb7664d24b8e1fe1db512f9e79e6979f635587579628aacb31` |

## 실제 helper 경로

고정 upstream `78fe19576bb06be96c2375e088574a262a300edb`의 `wan/utils/scail_utils.py`에서 이미지 전처리·center crop·색상 압축 함수 세 개를 AST로 추출하여 CPU에서 실행했다. 파일 SHA256은 `59de115e3b61a3aae7c7e1bf8a2f1be8abc76efff58ec2fbe463af3a24e956f6`이다. 입력이 이미 목표 크기이므로 추가 구도 변경은 없다.

채널 판정은 엄격한 `>225`에 해당하며, WHITE/RED/GREEN/BLUE/YELLOW/MAGENTA/CYAN 순으로 일곱 채널을 만든다. BLACK은 일곱 채널 모두 0이다. WHITE는 배경 가시성 채널이며 RGB를 지우는 alpha가 아니다. RGB 참조 자체는 별도 입력으로 유지된다.

Reference helper 출력은 `[28,1,112,64]`이다. WHITE 위치 `[0,7,14,21]`만 달라졌고 모든 나머지 채널은 정확히 같았다. 기존 WHITE는 전부 0, 새 WHITE+RED는 모든 위치에서 정확히 1이다. 공간 area 축소 때문에 경계에는 분수 점유율이 있으며 이 값을 이진 마스크로 설명하지 않는다. 관측한 float32 RED 평균은 0.2483433336, 새 WHITE 평균은 0.7516566515이다.

이 검사는 reference 단독 CPU 경로 검증이다. 두 CFG branch의 전체 `[28,6,112,64]`와 driving 부분, 실제 P 캐시 비교는 실행 장부의 별도 검사로 확인해야 한다. 다른 RGB/driving 자료의 재사용은 기존 입력 해시와 runner의 재검증으로 추적한다.

## 정적 관찰과 제한

실제 RGB/이전 마스크/새 마스크 비교 시트를 열어 확인했다. 앉아 있는 검은 Lab의 기존 RED 실루엣과 앞다리 사이의 배경 틈은 보존됐으며 BLACK 배경만 WHITE로 바뀌었다. 전경 분할 정확도가 새로 개선됐다는 의미는 아니다. 기존 driving 마스크의 발·바닥 경계 문제는 **PARTIAL_UNRESOLVED**로 유지한다.

Animation 모드에서 WHITE 배경을 보이도록 했으므로 침실이 남는 현상만으로 실패 판정을 하지 않는다. 실제 직립 자세·앞발·동작 대응, 개체 동일성, 시간 품질은 생성 결과와 별도로 평가한다. 이 CPU 검사로 해당 품질을 승인하지 않는다. 개인 사진과 비교 시트는 공개 저장소에 포함하지 않는다.
