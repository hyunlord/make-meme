# V-003 재현 기록

이 문서는 실제 수행한 순서와 역할을 기록한다. 대형 가중치·개인 입력·절대경로·시스템 영수증은 비공개 실행 manifest에 보존한다. 기존 실행을 재현한다는 이유로 sampler를 자동 재실행하지 않는다.

## 입력 및 앵커

- 공개 `V003_SCENE_CONFIG.json`의 구간·배역·키프레임·프롬프트·게이트를 사용한다.
- V-001의 canonical 원본 73 PNG와 원본 SAM 292 mask를 기존 hash와 대조했다. V-002 canny 입력도 동일 hash를 확인했다.
- native imagegen은 원본 키프레임·사용자 Lab 사진·사용자 IG 사진·수용 앵커0를 실제 이미지 입력으로 받았다. frame0은 재사용이며 신규 여섯 장은 각 1회 호출했다. 원출력은 그대로 보존하고 master는 LANCZOS로 1280×720으로 변환했다.
- 각 앵커의 기존 ComfyUI SAM3.1 실행은 Spark의 기존 연구 Python과 고정된 `anchor_sam.py` 사본을 사용했다. 기존 source SAM을 재추론하지 않았다.

```sh
RESEARCH_PY anchor_sam.py PRIVATE_SAM_RUNTIME.json --cpu-only
RESEARCH_PY anchor_sam.py PRIVATE_SAM_RUNTIME.json
RESEARCH_PY anchor_gates.py V003_SCENE_CONFIG.json PRIVATE_GATE_RUNTIME.json GATE_REPORT.json
```

실제 heavy 호출은 위 entry를 직접 실행하지 않고 기존 guarded runner의 CPU stage → 완료 영수증 확인 → Spark tmux의 heavy stage 순서였다. 각 단계 전 외부 GPU·배치 부모 180초 연속 부재 관측, helper, cgroup, NVRM·OOM·메모리·PSI 보호를 적용했다. private `prepare_anchor.py`와 `run_one_heavy.sh`에 실제 경로 및 명령이 보존된다.

G6 정정은 기존 SAM 출력의 CPU 재평가이며 이전 판정을 삭제하지 않았다. G6 상한은 참고값으로만 남기고 하한만 실패로 판단한다. G7은 기존 로컬 SigLIP vision pooler crop cosine이며 gate에 사용하지 않는다.

## 영상 및 측정 실행 계약

고정 공식 LTX commit과 기존 E1 환경을 재사용한다. private assembly는 수용 master 앵커를 1152×648로 LANCZOS 리사이즈하고 위아래 4px씩 크롭한다. public `ltx_entry.py`가 설정의 variant·seed·프레임·prompt를 읽는다. K1·K2·K3의 두 seed, 총 여섯 생성은 완료했으며 각 11 scheduler step·11 denoiser call을 기록했다. 시간·메모리·가드 영수증은 `RUNS.json`을 따른다. 출력 SAM 여섯 개와 CPU POST 여섯 개도 완료했다. 기존 로컬 임베딩 worker는 앵커 7개와 출력 프레임 438개, 총 445개 image item을 처리했고 `reports/embedding-metrics.json`으로 병합했다. 관련 guarded 단계는 정상 종료했고 NVRM 이벤트는 0이었다. 전달 무결성은 별도 DELIVERY 기록으로 확인한다.

```sh
E1_PY ltx_entry.py --config PRIVATE_LTX_RUNTIME.json --cpu-only
# 위와 같은 entry를 기존 guarded heavy stage가 실행한다.
RESEARCH_PY post_composite.py V003_SCENE_CONFIG.json PRIVATE_POST_RUNTIME.json
RESEARCH_PY output_metrics.py V003_SCENE_CONFIG.json PRIVATE_METRIC_RUNTIME.json
RESEARCH_PY output_embedding_metrics.py build PRIVATE_BATCH_MANIFEST.json PRIVATE_EMBED_RUNTIME.json
RESEARCH_PY embed_images.py PRIVATE_EMBED_RUNTIME.json --cpu-only
# 임베딩 모델 적재도 기존 guarded heavy stage를 거친다.
RESEARCH_PY embed_images.py PRIVATE_EMBED_RUNTIME.json
RESEARCH_PY output_embedding_metrics.py merge PRIVATE_BATCH_MANIFEST.json EMBED_REPORT.json METRICS_EMBED.json
```

각 명령의 런타임 역할은 다음과 같다. `RESEARCH_PY`와 `E1_PY`는 기존 연구·E1 Python 절대경로를 private 설정에서 읽는 표기이며 새 환경을 뜻하지 않는다. 코드의 실행 사본과 입력은 stage별로 동결한다.

- private `prepare_ltx.py`는 variant·seed_index·수용 앵커 목록으로 조건 PNG와 immutable 실행 묶음만 만든다. 기존 guarded CPU stage의 정상 종료를 확인한 뒤 `run_one_heavy.sh NAME CUTOFF_EPOCH`를 Spark tmux에서 정확히 한 번 실행했다. `ltx_entry.py`는 같은 공식 Python API를 여섯 실행에 사용한다.
- 출력 MP4를 CPU에서 디코딩한 `000.png`–`072.png`가 출력 SAM·측정·POST의 RAW 프레임이다. 이는 PNG 저장 이후 무손실인 **MP4 디코딩 파생 프레임**이며, 모델의 MP4 인코딩 전 RGB나 latent가 아니다. 원본 MP4는 수정하지 않는다.
- private `prepare_output_sam.py`가 완성된 RAW PNG 수·크기와 생성 영수증을 검증해 기존 SAM stage를 만든다. `run_output_sam_batch.sh`는 여섯 생성의 정상 종료부터 확인하고 출력마다 CPU→heavy를 순차 실행한다. 원본 SAM은 재사용하고 출력 SAM은 native 1152×640에서 실행한다.
- private `process_output.py`는 생성 receipt의 실제 `images` 배열에서 target frame·source anchor·offset·binding을 읽는다. 조건 PNG와 원본 앵커 hash를 검증한 뒤 CPU POST, 파생 POST MP4(libx264/CRF18/yuv420p), 지표를 만든다. SSIM에는 실제 모델 입력으로 변환했던 조건 PNG를 사용하여 두 번째 리사이즈를 피한다. 원본 배경 RGB의 POST 변환은 BICUBIC, master SAM 마스크 변환은 NEAREST다.
- embedding batch manifest의 `outputs[].keyframes=[{frame,anchor_id}]`도 실제 receipt에서 만든다. K3의 0/17/33/49/65는 각각 0/12/36/48/60 앵커와 비교하며, guide 시점 목록으로 대체하지 않는다. 앵커 벡터는 한 번 계산해 재사용하고 각 출력의 전 프레임을 앵커0와, 조건 시점을 해당 앵커와 비교한다. 출력 crop은 저장된 고정 캐스팅과 해당 프레임의 실제 개체 판정만 사용한다. 미확립 캐스팅·누락은 null이며 평균에는 관측 수를 함께 기록한다.

위 생성·SAM·POST·임베딩 완료는 명령 목록 자체가 아니라 각 완료 영수증과 병합 산출물로 확인했다. 이 기술적 완료를 사용자 품질 승인으로 해석하지 않는다. RAW MP4는 원래 byte로 보존하며 POST·시트·미리보기는 파생물로 표시한다. 출력의 추적 실패는 누락 상태로 남기고 임의의 개체 대응을 채우지 않는다. 자동 지표는 품질 순위가 아니다.

`ffmpeg` 디코딩·PNG 검사·브라우저 재생 가능 여부는 연속 지각 검수가 아니다. `temporal=UNVERIFIED`, `quality=HUMAN_REVIEW_PENDING`을 유지하며 빈 사용자 검토 양식을 전달한다.
