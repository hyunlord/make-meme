# B-007E 입력 감사

새 생성·다운로드 없이 B-007B의 기존 입력을 읽었다. Lab 파일 38개와 공식 source/derivative 파일 6개의 기존 SHA256을 fresh 재계산해 모두 일치했다. private manifest에는 전체 78개 파일의 hash·크기·해상도와 CPU contact sheet 생성 내역을 보존했다. 이미지와 개인 절대 경로는 공개하지 않는다.

## 실제 입력·시간축

| 입력 | Lab | 공식 animation_001 |
|---|---|---|
| 참조 | 실제 검은 Lab 사진 | 공식 ref.jpg |
| 개체 ID mask | reference/driver RED | reference/driver BLUE |
| driver 파일 | driver-24fps.mp4 | driver-17frames.mp4 |
| mask 파일 | mask-24fps.mp4 | mask-17frames.mp4 |
| ffprobe 결과 | 17f,24/1fps,512×896 | 17f,16/1fps,2048×1080 |
| 파일 길이 | 0.708333초 | 1.062500초 |
| sample endpoint 간격 | 16/24초 | 16/16초 |
| 목표 H×W | 896×512 | 512×896 |

Lab는 원본 f0…16 순서를 유지한다. 둘 다 frame duplication·interpolation·fps 재표시는 하지 않는다. 공식 원본 RGB/mask는 65f16fps였고 기존 derivative는 첫17장을 lossless RGB로 인코딩한 것이다.

## 정확한 crop geometry

고정 [resize_for_rectangle_crop](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/utils/scail_utils.py#L35)의 aspect-preserving resize 후 center crop을 사용한다. RGB와 해당 mask에는 동일 geometry를 적용한다.

- Lab RGB/ref/mask는 이미 W512H896이므로 추가 crop=0.
- 공식 reference W1920H1080 → W910H512 → left7,top0,W896H512.
- 공식 driving W2048H1080 → W970H512 → left37,top0,W896H512.

private sheet는 이 geometry의 Pillow BICUBIC preview다. 실제 runtime의 torchvision BICUBIC와 pixel hash가 같다고 주장하지 않는다. runtime tensor hash는 별도로 관측한다.

## 정적 시각 관찰과 한계

f0/f8/f16의 RGB·mask와 두 reference를 실제로 봤다. Lab source는 한 마리의 뒷발 직립, reference는 앉은 검은 Lab다. 같은 red ID로 연결되지만 체형·포즈는 서로 다르다. 가는 발·꼬리·바닥 반사 주변의 기존 경계 결함은 **PARTIAL_UNRESOLVED**로 유지했다. 수정·새 segmentation 모델은 없다.

공식 예제는 한 명의 춤추는 인물이며 BLUE ID가 일치한다. reference mask의 배경은 WHITE, driving mask 배경은 BLACK이다. 이를 임의로 Lab RED/BLACK로 통일하지 않는다. 인물의 하체는 원본 구도에서 이미 잘려 있으므로 전신 발 위치 평가 baseline이 아니다. 머리 장식·손 주변 mask 경계도 완전한 정답 segmentation으로 취급하지 않는다.

공식 파일 출처는 [고정 animation_001](https://github.com/zai-org/SCAIL-2/tree/78fe19576bb06be96c2375e088574a262a300edb/examples/animation_001)이다. 공식 prompt `The girl is dancing`은 [README 예제](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/README.md#L319)를 따른다. upstream 공개 예제라는 provenance와 개별 인물·미디어의 포괄적 재배포 권리는 구분하며 private sheet만 만들었다. 연속 재생은 관찰하지 않았으므로 시간 품질은 **UNVERIFIED**다.
