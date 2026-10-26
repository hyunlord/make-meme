# B-032 재현

기존 환경의 Python/NumPy/SciPy/Pillow/PyTorch와 ffmpeg만 사용한다. 신규 설치는 없다. 실제 CPU 검증 환경은 Python 시스템의 기존 executable, NumPy 2.4.3, SciPy 1.17.1, PyTorch 2.11.0이다. 아래 변수는 비공개 manifest에 기록된 승인된 로컬 파일을 가리키며 공개 저장소에는 미디어나 개인 절대 경로를 넣지 않는다.

```sh
python3 -m unittest discover -s code -p 'test_*.py'
python3 code/prepare_cpu_inputs.py --raw "$B031_RAW" --polygons "$PRIVATE_POLYGONS" --output "$NEW_PREP_DIR"
python3 code/run_composite.py "$PRIVATE_FROZEN_MANIFEST" --output "$NEW_OUTPUT_DIR"
```

`prepare_cpu_inputs.py`는 `torch.load(map_location='cpu', weights_only=True)`로 기존 FP32 CTHW raw만 읽는다. shape `[3,17,512,896]`와 finite [-1,1]을 확인하고 `permute(1,2,3,0).contiguous()`로 THWC를 저장한다. GPU/모델/VAE는 호출하지 않는다. private polygon의 실제 17개 정수 좌표를 Pillow L image에 rasterize한다. 좌표는 결과를 보고 다시 추정하지 않는다. 이미 존재하는 output에는 쓰지 않는다.

Frozen manifest의 모든 입력 SHA256을 확인하고 source RGB17개·source semantic mask17개·target support17개·A0 support·lossless generated numpy를 읽는다. RED는 정확한 RGB `[255,0,0]`으로 선택한다. manifest의 private 경로가 전송 후 바뀌면 해당 경로만 명시적으로 재바인딩하고 입력 파일 내용 hash는 유지해야 한다. 기존 실험 manifest를 덮어쓰지 않는다.

사전 실행 code/input freeze는 `175453622e52146f68c1af5e7336c6c75e1346b6`에 기록됐다. 원본 raw와 파생 float 및 annotation hash는 `INPUT_FREEZE.json`에 공개 가능한 hash만 보존했다. 사후 추가된 prepare utility는 실제 준비 과정을 재현하는 코드이며 기존 합성 정책·출력을 변경하지 않았다. replay 18파일은 실제 실행 입력과 byte-identical이었다.

Runner는 두 출력만 생성하고 기존 결과 폴더가 있으면 거부한다. 같은 관측값으로 반경/경계를 다시 튜닝하지 않는다. 실험 재현과 승인되지 않은 새 실험을 구분한다. 이번 실제 실행은 1회, 두 파생 MP4다.

검증은 stdlib unittest 4개와 실제 입력 endpoint/coverage/hash/ffprobe 검사다. 새 test package를 설치하지 않았다. 동적 미디어에는 calibrated temporal metric을 적용하지 않았으며 직접 연속 재생 품질 관찰은 `UNVERIFIED`다.
