# CPU 재현 — 모델/학습 실행 없음

시작 기준 `ffe0369682eb2b0c3a903c44a2f23d5ff91b2299`, 선정 규칙 `3898e4b`, 복사/시트 코드 `c6838be`, 실제 case 검증 코드 freeze `16b1479`. [PREREGISTERED_CODE](PREREGISTERED_CODE.json)는 코드와 원본 private manifest의 SHA를 포함한다. 학습·추론 환경을 checkout하거나 설치할 필요가 없다.

## 기존 파일에서 검토 case 구성

기존 허용 자료 root가 있는 경우에만 실행한다. source나 mask가 없으면 다운로드/새 segmentation으로 대체하지 않는다.

```sh
DATA_ROOT='<existing-B-root>' RUN_ROOT='<new-private-B017-root>' \
  sh review_code/prepare_review_cases.sh
```

사전 inventory의 retrieved f0 reference/mask가 필요하다. script는 기존 source/Lab/B012 입력만 읽고 원본은 변경하지 않는다. output case가 이미 있으면 덮어쓰지 않고 종료한다. JPEG로 변환하거나 R/D/Y 내용을 보정하지 않는다.

## 전달된 작은 case 검사

Mac에서 기존 Python3.14.4/Pydantic2.12.5 및 ffmpeg/ffprobe를 사용했다. 모델 라이브러리는 import하지 않는다. `DATA_MANIFEST.json`은 원래 private provenance 경로를 보존한다. 별도 `DATA_MANIFEST.portable.json`은 같은 case를 manifest 디렉터리 기준 상대경로로 가리킨다. 두 입력의 실제 CPU 검사 결과가 바이트 동일했다.

압축 해제 폴더에서:

```sh
python3 public/experiment/code/validate_cases.py \
  private/DATA_MANIFEST.portable.json --output /tmp/B017-local-validation.json
```

JSON은 완비/권한/수준별 실패를 포함한다. CLI exit0은 검사 완료이지 training-ready 승인이나 모든 case PASS가 아니다. `structural_media_complete`, `pair_available`, `training_ready`, `missing_fields`, `blockers`를 함께 읽는다.

## 작은 회귀 검사

```sh
cd public/experiment/code
python3 -m pytest -q test_validator.py
uvx --offline ruff check .
uvx --offline basedpyright --project pyrightconfig.json --pythonpath "$(command -v python3)"
```

11개 synthetic fixture는 검증기 동작만 확인한다. offline tool cache는 이번 Mac에 이미 있었으며 새 의존성 다운로드는0이다. 다른 호스트의 offline cache가 없으면 설치하지 않고 그 검사를 NOT_RUN으로 남긴다. 새로운 train 명령을 이 문서에 포함하지 않는다.

## 보존·범위

14개 actual media-role SHA가 inventory와 일치하고 원본복사/decoded equality를 별도 기록했다. 공식 source audit는 source_manifest의 WAN/SAT revision·파일해시를 사용하며 환경/모델을 변경하지 않았다. GPU·whole-model·cache encode·optimizer update·새 생성0. 본 raw case 구성만으로 공식 SAT loader의 bucket/fps/LoRA 연결까지 검증된 것은 아니다.
