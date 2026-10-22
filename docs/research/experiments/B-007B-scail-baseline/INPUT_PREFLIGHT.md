# B-007B 입력 및 writer 사전 검증

입력 준비 **COMPLETED**, 기존 Lab 마스크 정밀도 **PARTIAL_UNRESOLVED**. 이 검사는 diffusion 실행이나 동물 영상 품질 수용이 아니다.

## Lab 입력
B-007A의 148개 artifact SHA256을 다시 확인했다. reference, red instance mask, 17장 원본 RGB 및 v2 국소 수정 마스크를 바이트 그대로 별도 B-007B 입력에 복사했다. 원본 B-007A 파일은 수정하지 않았다.

모델 캔버스는 H896×W512이다. reference와 driver는 동일한 기존 resize/center-crop 좌표를 유지한다. 사진의 portrait 방향 때문에 원본 가로 장면의 양옆은 잘리며, 전체 카메라 구도 재현을 뜻하지 않는다. B-007A의 개별 17장 정적 관찰과 119개 보이는 관측점의 crop 검사를 재사용한다. f0/f1 뒷발 주변 반사와 얇은 경계 잔여는 수정하지 않고 PARTIAL로 유지한다. 새 학습식/비학습식 마스크 처리는 하지 않았다.

입력 RGB/mask MP4는 각각 17프레임, 24fps, 0.708333초다. 원본 표본 시각은 i/24, 첫~끝 간격은 16/24초다. red ID가 reference/driver에서 동일하며, 배경은 black이다.

## 공식 smoke 입력
고정 SCAIL commit `78fe19576bb06be96c2375e088574a262a300edb`의 `examples/animation_001/`에서 ref.jpg, ref_mask.jpg, rendered_v2.mp4, rendered_mask_v2.mp4 네 Git blob을 추출했다. 총 1,004,819바이트이며 별도 모델 다운로드가 아니다. 파일별 blob/SHA는 private input_gate0.json에 기록했다.

공식 원본 RGB와 mask는 모두 2048×1080, 65프레임, **16fps**다. 첫 17개 decoded 프레임을 순서 그대로 lossless RGB MP4로 저장하여 17프레임, 16fps, 1.062500초를 확인했다. 24fps로 재표시하지 않았다. 공식 ref 및 driver f0/f8/f16과 mask를 직접 정적으로 확인했다. reference는 바닷가의 여성, driver는 실내에서 춤추는 여성이며 두 마스크에서 blue ID가 대응한다. reference의 white 배경과 driver의 black 배경은 공식 입력 그대로다. 장식/가림 경계가 완벽하다는 주장은 하지 않는다. 이 공식 인간 예제는 Lab 품질 증거가 아니다.

## Writer 통합 검사
격리 generate.py에 `--output_fps`를 추가하고 양수 검사 및 실제 cache_video 호출의 fps 전달만 변경한다. 기존 upstream 및 B-007A는 보존한다. CPU 테스트는 원본 RGB tensor를 실제 upstream cache_video와 parser/호출 AST에 전달한다. 모델 객체/확산을 모킹하여 생성 성공을 주장하지 않는다.

초기 실제 encoding은 imageio가 PyAVPlugin을 선택하면서 `quality` 인자를 지원하지 않아 실패했다. upstream retry는 이미 uint8이 된 tensor를 다시 normalize하여 마지막에는 별도 dtype 오류를 출력했다. Python exception trace로 최초 오류를 확인했다. B001/B007B 환경에서 imageio_ffmpeg가 없음을 확인했다. B007B 격리 환경에 imageio-ffmpeg 0.6.0을 준비한 뒤 같은 테스트 코드를 `/usr/bin/ffmpeg` backend로 실행해 exit 0을 확인했다. 원본 cache_video 구현이나 retry 동작은 변경하지 않았다. 초기 실패는 writer_initial_failure.json에 보존했다.

실제 출력은 H896×W512, 17프레임, 24/1fps, 0.708333초이며 SHA256은 `840945d6b99801699da79c1a14f7e425936cdd9e390a7137b2e1a8968ff9a7eb`다. parser는 output_fps=0을 거부했다. cfg의 기본 16fps가 명시적 24fps로 전달되는 실제 저장 경로를 검사했다. 입력 tensor는 `[3,17,896,512]` float 원본 RGB이며 diffusion 출력이 아니다. CPU 실행 환경은 torch2.14.0+cu130, torchvision0.29.0+cu130, imageio2.38.1이다. CUDA가 포함된 패키지명은 GPU 실행 증거가 아니다.

학습된 16fps prior는 output_fps 설정으로 바뀌지 않는다. Lab24fps의 속도/시간 품질은 실제 확산 출력에서 별도 검사해야 하며 현재 UNVERIFIED다.

## 재현
```sh
python code/input_gate0.py B007A_ROOT PINNED_SCAIL_ROOT B007B_ROOT
PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=4 IMAGEIO_FFMPEG_EXE=/usr/bin/ffmpeg B007B_ROOT/environment/bin/python code/writer_integration.py B007B_ROOT
```

공개 문서에는 개인 사진/영상이나 절대 개인 경로를 포함하지 않는다. 실제 입력·출력·SHA 장부는 private 연구 폴더에 보존한다.
