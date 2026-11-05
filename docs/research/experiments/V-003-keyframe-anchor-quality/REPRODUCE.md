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

고정 공식 LTX commit과 기존 E1 환경을 재사용한다. private assembly는 수용 master 앵커를 1152×648로 LANCZOS 리사이즈하고 위아래 4px씩 크롭한다. public `ltx_entry.py`가 설정의 variant·seed·프레임·prompt를 읽는다. 실행 완료 여부와 실제 step·시간은 `RUNS.json`을 따른다.

```sh
E1_PY ltx_entry.py --config PRIVATE_LTX_RUNTIME.json --cpu-only
# 위와 같은 entry를 기존 guarded heavy stage가 실행한다.
RESEARCH_PY post_composite.py V003_SCENE_CONFIG.json PRIVATE_POST_RUNTIME.json
RESEARCH_PY output_metrics.py V003_SCENE_CONFIG.json PRIVATE_METRIC_RUNTIME.json
RESEARCH_PY output_embedding_metrics.py build PRIVATE_BATCH_MANIFEST.json PRIVATE_EMBED_RUNTIME.json
RESEARCH_PY embed_images.py PRIVATE_EMBED_RUNTIME.json
RESEARCH_PY output_embedding_metrics.py merge PRIVATE_BATCH_MANIFEST.json EMBED_REPORT.json METRICS_EMBED.json
```

아직 완료되지 않은 단계를 위 명령 목록만으로 실행 성공으로 해석하지 않는다. RAW MP4는 원래 byte로 보존하며 POST·시트·미리보기는 파생물로 표시한다. 출력의 추적 실패는 누락 상태로 남기고 임의의 개체 대응을 채우지 않는다. 자동 지표는 품질 순위가 아니다.
