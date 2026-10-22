# B-006 재현과 비공개 자료

## 버전과 실행 범위

- 문서 시작 HEAD: `f6819d2a5e487516896e1169237d910bd98354fd`
- 최초 schema/CPU 코드 사전등록: `5a001865026f8a1a6000877a4133aed502a77fd2`
- 관측 validator 보완/CPU heatmap 코드 사전등록: `4e0403ac80ca9edb0d4524d282c4a44d86561ac9`
- 실제 source/Canny는 B005에 보존된 B003 bg-real seed20261022의 `target`/`condition` 복사본이다. generated `output-*.png`를 쓰지 않는다.
- 코드/입력 hash는 이 폴더의 JSON, 실제 좌표·명령·raw 환경 기록은 비공개 ZIP을 참조한다. 개인 원본은 공개 저장소에 없으므로 코드만으로 같은 영상을 재현할 수 있다고 주장하지 않는다.

## CPU 가시화

기존 Pillow/ffmpeg가 있는 격리 환경을 사용했다. 새 라이브러리를 설치하지 않았다. `${B005_ROOT}`는 기존 보존 결과, `${RUN_ROOT}`는 새로운 비공개 출력 폴더다.

```sh
mkdir -p "${RUN_ROOT}/tools"
cp code/annotation_schema.json code/prepare_inputs.py code/render_motion.py "${RUN_ROOT}/tools/"
python3 "${RUN_ROOT}/tools/prepare_inputs.py" "${B005_ROOT}" "${RUN_ROOT}"
# 비공개 annotations/annotated_landmarks.json을 확보하거나 직접 원본을 보고 기록한다.
# 스크립트는 수동 관측점을 자동 추정하지 않는다.
python3 "${RUN_ROOT}/tools/render_motion.py" "${RUN_ROOT}"
```

기존 원본을 덮어쓰지 않는다. renderer는 지정한 출력 폴더의 파생 파일을 다시 만들므로 재검토에는 새 RUN_ROOT를 사용한다. renderer의 관측 계약은 visible에만 좌표 허용, hidden/unobservable은 null, contact possible/unknown은 touching=null이다. 원본 좌표계를 유지하며 부위 warp나 smoothing을 하지 않는다.

## PyTorch CPU heatmap

기존 Spark B 환경에서 다음을 실행했다. CPU torch 연산이며 VACE/SCAIL 가중치 로드가 없다.

```sh
CUDA_VISIBLE_DEVICES='' OMP_NUM_THREADS=1 "${BASELINE_ROOT}/.venv/bin/python" code/test_joint_heatmaps.py
CUDA_VISIBLE_DEVICES='' OMP_NUM_THREADS=1 "${BASELINE_ROOT}/.venv/bin/python" code/joint_heatmaps.py \
  "${RUN_ROOT}/annotations/annotated_landmarks.json" "${RUN_ROOT}/reports/heatmap-actual"
```

heatmap 출력 디렉터리는 새 경로여야 한다. float32 `[17,17,72,128]`와 validity/visibility를 함께 보존한다. .pt는 이번 CPU 가시화 tensor이며 pretrained 모델이나 adapter가 아니다. 저장 파일 SHA와 tensor byte SHA를 구분한다.

## 직접 검증한 것과 미검증

입력34파일 해시, 실제 source17장 개별 관측, 대표 ID 확대/전체 시트·궤적의 시각 검토, 관측 모순 fixture, CPU heatmap toy/실제 입력 실행 및 저장 후 검증, MP4의17프레임/24fps를 확인했다. 전문가 재주석 일치도·3D 관절·실제 발 하중·연속 재생 자연스러움은 검증하지 않았다. 연속 시간 품질 UNVERIFIED를 유지한다.

SCAIL-2는 소스/metadata만 조사했고 새로운 diffusion forward, 다운로드, 설치, LoRA 학습은 실행하지 않았다. MODEL_AUDIT의 shape는 코드 유도이며 실제 SCAIL hook shape가 아니다. 실행 환경 전체 의존성 설치 가능성은 이번 검증 범위가 아니다.
