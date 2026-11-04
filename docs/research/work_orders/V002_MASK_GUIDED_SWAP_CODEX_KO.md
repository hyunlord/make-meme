# V-002 실행 의뢰서
## 원본 영상을 유지하고 개 영역만 다시 칠한다 — VACE 마스크 편집(MV2V) + SAM 마스크 + 기존 앵커

**새 Codex 세션 가능 · DGX Spark 실행 · Mac 전달 · imagegen 0회 · 영상 생성 최대 5개 · 학습 0회**

> **이 문서는 실행 승인이다. 아래 범위에서 V-002를 실제로 진행해 줘.**
> 같은 범위의 승인을 다시 기다리지 않는다. 실제 권한·안전 정책은 준수한다.

| 항목 | 내용 |
|---|---|
| 저장소 / branch | `hyunlord/make-meme` / `docs/v-research-20261103` (V-001 최신 commit 위에서 계속) |
| 부모 | V-001 (`0cfd0ef` 이후의 최신 기록) |
| 새 실험 경로 | `docs/research/experiments/V-002-mask-guided-swap/` |
| 의뢰서 보존 | `docs/research/work_orders/V002_MASK_GUIDED_SWAP_CODEX_KO.md` |
| 동봉 설정 | `V002_PREDECLARED_CONFIG.json` |

---

## 0. 왜 바꾸나 — V-001에서 확인한 것

- **E1(LTX-2.3 + depth IC-LoRA)**: 영상은 나왔지만 사용자가 직접 보고 판정했다. **"개가 움직이지만 원본과 전혀 다른 동작을 한다."** 원인 분석:
  - IC-LoRA 조건은 1단계(576×320)에만 들어가고, ref0.5라서 조건 영상은 288×160이다. 이 크기에서 개 한 마리는 약 50×60px다.
  - LTX VAE의 시간 압축은 8배다. 73프레임이 latent 10칸이 되어 빠른 발차기가 뭉개진다.
  - 바닥 위의 개는 depth 대비가 약하다.
  - 결과적으로 첫 프레임 앵커만 고정되고 동작은 모델이 지어냈다. **"첫 프레임 + 약한 구조 조건으로 새로 생성"하는 방식의 한계**다.
- **E2(Bernini)**: 1 step 296초(73프레임 40 step이면 약 3.4시간)라 이 장비에서 실용성이 없다. 49프레임 실행 중 Spark가 GPU 드라이버 메모리 할당 실패(`NVRM NV_ERR_NO_MEMORY`)로 멈춰 02:02에 재부팅됐다. **보류.**

이번에는 방식을 바꾼다. **원본 영상을 그대로 두고, SAM 마스크로 개(와 반사) 영역만 다시 칠한다.** 프레임마다 움직이는 마스크의 실루엣이 원본 자세를 직접 담으므로, V-001보다 훨씬 강한 동작 신호가 된다. Wan VACE의 시간 압축은 4배라 시간 방향 정보도 두 배 촘촘하다. 배경은 원본 픽셀이 남는다.

---

## 1. 이번 질문

1. 마스크 편집이 원본 두 개의 **동작(실루엣·위치·타이밍)**을 따라가면서 래브라도·IG 외형으로 바꿀 수 있는가?
2. 마스크 안 depth 조건, 첫 프레임 앵커 고정이 각각 도움이 되는가?
3. 래브라도가 원본 갈색 개의 실루엣 안에 갇혀 작아지는가?
4. 바닥 반사가 새 개체에 맞게 바뀌는가?

**최종 품질 판정은 사용자가 직접 재생해서 내린다.** 자동 측정은 참고값이고 `HUMAN_REVIEW_PENDING`을 유지한다.

---

## 2. 범위

### 수행

- V-001의 구간 `[240,313)`(73프레임·24fps), 캐스팅(오른쪽 앞 원본 갈색 개 → Lab, 왼쪽 뒤 원본 회색 개 → IG), 앵커 1장, 기존 SAM 원본 마스크·반사 판정 결과를 **재사용**한다.
- 마스크·조건 영상을 CPU로 만든다.
- VACE 1.3B 3개 변형 → 자동 규칙으로 1개 선택 → VACE 14B 1회. 별도로 LTX canny 대조 1회. **총 영상 최대 5개.**
- V-001 E1 출력 2개와 이번 출력 전체에 SAM 출력 측정을 실행한다.
- 뷰어·검토 양식·기록·전달까지 한다.

### 0회

- imagegen, 새 앵커, 학습, Bernini 재실행, 외부 API.
- 결과를 보고 마스크 팽창·프롬프트·seed·구간을 바꾸는 재시도.

---

## 3. 운영 — GB10 통합 메모리 대책 (모든 heavy 적재에 적용)

V-001에서 확인한 사실: DGX Spark에서는 모델 파일의 page cache와 CUDA 할당이 같은 메모리 풀을 쓴다. 그래서 같은 가중치가 page cache 한 벌, 텐서 한 벌로 이중으로 잡힐 수 있다. 드라이버 수준의 할당 실패는 MemAvailable·PSI 가드보다 먼저 시스템을 멈출 수 있다. NVIDIA는 큰 모델을 적재하기 전에 buffer cache를 비우라고 안내한다.

1. **적재 직전 page cache 비우기**: `sudo /usr/local/sbin/drop-caches`(사용자가 미리 만든 단일 명령, §3.1). 이 명령이 없거나 sudo가 거부되면, 실행하지 않고 기록만 남긴 뒤 계속 진행한다. 다른 sudo 명령은 쓰지 않는다.
2. **할당기 설정**: 모든 heavy worker에 `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True`.
3. **사전 peak 추정**: 가중치 dtype 크기 + 텍스트 인코더 + VAE + 활성값 추정치가 **100GiB를 넘으면 시작하지 않는다.** 추정 근거를 기록한다.
4. **NVRM 감시**: worker 실행 중 커널 로그(`journalctl -k -f` 또는 `dmesg -w`)를 감시한다. `NV_ERR_NO_MEMORY`가 **한 번이라도** 나오면 즉시 해당 worker를 정상 종료하고 `ENGINE_STOPPED_NVRM`으로 기록한다. 재시도하지 않는다. 사용자 권한으로 커널 로그를 읽을 수 없으면 그 사실을 기록하고, 나머지 가드로 진행한다.
5. V-001 §7의 중단 조건(OOM, MemAvailable < 12GiB가 30초 지속, PSI full > 25%가 60초 지속, 외부 작업 충돌)은 그대로다. worker 메모리 한도는 100GiB이고, `MemoryHigh`는 `MemoryMax`와 같게 둔다.

### 3.1 사용자 사전 작업 (Codex는 하지 않음)

사용자가 Spark에서 한 번 실행한다:

```bash
sudo tee /usr/local/sbin/drop-caches >/dev/null <<'EOF'
#!/bin/sh
sync; echo 3 > /proc/sys/vm/drop_caches
EOF
sudo chmod 755 /usr/local/sbin/drop-caches
echo 'hyunlord ALL=(root) NOPASSWD: /usr/local/sbin/drop-caches' | sudo tee /etc/sudoers.d/drop-caches
sudo chmod 440 /etc/sudoers.d/drop-caches
sudo visudo -c
```

---

## 4. 입력 만들기 (CPU)

### 4.1 공통

- 해상도: **832×480**. V-001 E2 규약을 그대로 쓴다(1280×720 → 853×480 → 가로 중앙 832 크롭). 14B도 같은 해상도를 써서 1.3B 결과와 비교한다.
- 프레임: 73(`4n+1`), 24fps.
- 마스크: V-001에서 저장한 원본 SAM 트랙을 쓴다. 실제 개체 track0(Lab)·track1(IG)와 반사 track2·track3. 반사 판정 규칙은 V-001 개정 2와 같다. 각 트랙을 832×480으로 변환한 뒤 사전 고정값만큼 팽창한다.

| 영역 | 팽창(832×480 기준) | 이유 |
|---|---:|---|
| Lab(track0) | 24px | 래브라도가 원본보다 크게 그려질 여지 |
| IG(track1) | 12px | 경계 여유 |
| 반사(track2·3) | 12px | 반사도 새로 그린다 |

- **생성 마스크**: 위 네 영역의 합집합. **흰색은 반드시 RGB (255,255,255)로 만든다.** C-008에서 PIL 정수 fill이 (255,0,0) 빨강 마스크를 만든 사고가 있었다. 저장한 마스크 PNG의 세 채널 값을 검사해서 기록한다.
- **참조 이미지 2장**: V-001 앵커에서 SAM 앵커 마스크로 Lab과 IG를 각각 잘라 흰 배경에 놓은 crop. VACE 공식 참조 입력 규약(크기·배경)을 따른다.
- **프롬프트**(영문 고정): `Two dogs dancing on a reflective floor in the same room: on the right, a large black Labrador Retriever with a broad chest and thick legs; on the left, a slender grey Italian Greyhound. Their reflections on the floor match them. Keep the original motion, timing, room and camera.`

### 4.2 VACE 1.3B 세 변형

| ID | 마스크 안 내용 | 프레임 0 | 참조 |
|---|---|---|---|
| **M1** | 회색 127 | 원본 프레임 + 마스크 | Lab·IG crop |
| **M2** | 원본 구간의 depth(V-001 depth raw를 같은 규약으로 리샘플, 재추론 0회) | 원본 프레임 + 마스크 | Lab·IG crop |
| **M3** | 회색 127 | **앵커 RGB, 마스크 0(유지)** | Lab·IG crop |

- 마스크 밖은 세 변형 모두 원본 RGB, 마스크 0이다.
- M3는 첫 프레임의 정체성을 고정한다. 대신 앵커의 Lab 윤곽(원본보다 약 1.25배)과 프레임 1의 원본 마스크가 어긋날 수 있다. 이 전환부를 관측 항목으로 남긴다.
- 공식 VACE 코드(`ali-vilab/VACE`의 `vace_wan_inference.py` 계열 `src_video`·`src_mask`·`src_ref_images`) 또는 C 트랙에서 검증한 기존 VACE runner를 쓴다. 기존 runner를 쓰면 C-008/C-009 마스크 수정이 반영된 버전인지 확인한다.
- 설정은 공식 기본값(step·CFG·shift)을 쓰고 실제 값을 기록한다. seed는 `20261103`.

### 4.3 14B 선택 규칙 (결과 전에 고정)

M1–M3 출력에 §6.1 측정을 돌린 뒤 선택한다.
1. 개 2마리 검출 프레임이 66/73 이상인 변형만 후보로 남긴다.
2. 그중 **캐스팅별 실루엣 IoU 평균(Lab·IG 평균)**이 가장 높은 변형을 고른다.
3. 차이가 0.02 이내면 M1을 고른다.
4. 후보가 없으면 14B를 실행하지 않고 `NO_14B_CANDIDATE`로 기록한다.

사람의 판정을 기다리지 않고 이 규칙대로 진행한다.

### 4.4 VACE 14B 1회

- 선택된 변형과 같은 입력. 가중치는 `research/make-meme-c/models/Wan2.1-VACE-14B`(C-005에서 받은 공식본)를 쓴다.
- §3의 대책을 모두 적용한다. C-005는 이 모델을 적재하다 PSI 가드로 멈췄다.
- 시간 측정 1 step → 73프레임 예상이 150분을 넘으면 49프레임으로 줄인다. 49프레임도 225분을 넘으면 `ENGINE_TOO_SLOW`로 기록하고 실행하지 않는다.

### 4.5 LTX canny 대조 1회 (빠른 대조)

- V-001 E1 설정 그대로(1152×640, 앵커 첫 프레임, seed `20261103`)에 Union Control의 **canny**만 쓴다. 공식 CannyEdgePreprocessor 기본값(92/200)을 쓴다.
- 목적: LTX가 조건 신호 종류를 바꾸면 동작을 따라오는지 한 번만 확인한다. depth+canny 혼합이나 강도 조절은 하지 않는다.

---

## 5. 순서와 예산

| 단계 | 승인량 |
|---|---:|
| CPU 입력 제작·검사 | 마스크·조건 영상·참조 crop |
| VACE 1.3B | 3회(M1–M3), seed 1개 |
| SAM 출력 측정 | V-001 E1 2개 + 이번 출력 전부 |
| VACE 14B | 시간 측정 1회 + 생성 1회 |
| LTX canny | 1회 |
| 품질 재시도 | 0회 |
| 전체 상한 | 7시간(마지막 30분은 기록·전달) |

순서: 사용자 사전 작업(§3.1) 확인 → 사전 commit → CPU 입력 → **SAM으로 V-001 E1 출력 측정(기준선 수치)** → M1→M2→M3 → 측정·선택 → 14B → LTX canny → 측정·뷰어·전달.

한 엔진이 막혀도 나머지는 진행한다. 기계적 오류(경로, 형식, 해상도·프레임 배수)는 V-001 개정 4의 사전 허용 규칙대로 고친다. 품질 관련 설정은 바꾸지 않는다.

---

## 6. 측정과 검토

### 6.1 자동 측정 (SAM, 원본 1280×720 좌표로 환산)

| 지표 | 정의 |
|---|---|
| **실루엣 IoU** | 캐스팅별로 출력 마스크와 원본 마스크의 프레임별 IoU(팽창 전 원본 기준). 동작 추종의 주 지표 |
| 궤적 거리 | 캐스팅별 중심 궤적의 평균 거리(화면 가로 대비 %) |
| 개체 수 안정성 | 실제 개체(반사 제외) 2마리가 검출된 프레임 비율 |
| 뒤바뀜 | 캐스팅과 반대로 대응되는 프레임 수 |
| Lab/IG 크기비 | 프레임별 bbox 높이비의 중앙값. 원본 비율과 앵커 비율을 같이 표시 |
| 반사 색 | 반사 트랙과 위 개체의 평균 색 차(참고값) |
| 마스크 밖 보존 | 마스크 밖 영역의 원본 대비 평균 절대 차 |
| 비용 | 실행 시간, 최대 메모리, step 수, NVRM·가드 이벤트 |

V-001 E1 두 개에도 같은 지표를 계산해, 사용자의 "전혀 다른 동작" 판정을 수치로 남긴다.

### 6.2 진단 시트

출력마다 9시점(0, 9, 18, …, 72)을 한 줄로 놓는다: 원본 / 모델 입력(마스크 적용 영상) / 출력 / 출력 SAM 실루엣과 원본 실루엣 겹침.

### 6.3 뷰어

동기 재생: 원본 / V-001 E1-s1 / M1 / M2 / M3 / 14B / LTX-canny. 모두 같은 표시 크기로 맞춘다. 실행되지 않은 열은 NOT_RUN으로 표시한다. 수치 표와 진단 시트 링크를 붙이고, 빈 `HUMAN_REVIEW.md` 양식(V-001과 같은 항목)을 둔다.

---

## 7. 판정과 다음

- 기술: 변형별 `RAN` / `ENGINE_STOPPED_NVRM` / `ENGINE_STOPPED_GUARD` / `ENGINE_TOO_SLOW` / `NO_14B_CANDIDATE` / `BLOCKED_*`.
- 품질: `HUMAN_REVIEW_PENDING`.
- 다음 후보(자동 시작하지 않음):
  - 동작이 따라오고 외형도 되면 → **V-003: 15초 전체를 구간 분할 생성.**
  - 동작은 따라오는데 Lab이 작으면 → Lab 마스크를 앵커 기준으로 키우는 규칙 검토.
  - 동작이 여전히 안 따라오면 → 마스크 편집 자체의 한계로 기록하고 원인을 다시 진단.

---

## 8. 산출물·전달

`PLAN.md`, `INPUTS_PUBLIC.json`(hash만), `MASK_CHECK.json`(채널 값·팽창·면적), `RUNS.json`, `METRICS.json`, `RESULTS.md`(영상·비용을 먼저, 검사 세부는 뒤에), `HUMAN_REVIEW.md`, `METHOD_KO.md`, `REPRODUCE.md`.

`METHOD_KO.md`는 짧게 다음 세 가지만 다룬다:
1. 첫 프레임에서 생성하는 방식(V-001 E1)과 마스크 편집(V-002)이 동작 정보를 얻는 경로의 차이.
2. VACE에서 마스크·회색 127·참조 이미지·마스크 안 depth가 각각 하는 일.
3. VAE 시간 압축(LTX 8배, Wan 4배)이 빠른 동작에 미치는 영향.

전달: 개인 미디어는 Git에 올리지 않는다. 문서·비민감 코드·hash만 push한다. compact ZIP 1개를 Mac `~/Downloads/V002-review-<날짜>.zip`에 두고, 무결성 확인은 한 줄 요약만 쓴다. HISTORY/ROADMAP에 한 줄씩 기록한다. 후속 생성은 예약하지 않는다.

## 근거

[S1] V-001 기록: https://github.com/hyunlord/make-meme/tree/docs/v-research-20261103/docs/research/experiments/V-001-anchor-propagation-baseline
[S2] NVIDIA DGX Spark 통합 메모리·buffer cache 안내: https://build.nvidia.com/spark/vlm-finetuning/troubleshooting.md
[S3] VACE 공식 저장소(마스크·참조 입력): https://github.com/ali-vilab/VACE
[S4] C-008 마스크 색 오류 기록: https://github.com/hyunlord/make-meme/tree/docs/c-research-20261028/docs/research/experiments/C-008-conditioning-parity

## 실행 시작

위 범위에서 지금 V-002를 시작해 줘. §3.1 사용자 사전 작업 여부를 확인하고, 사전 commit 후 끝까지 진행한다. 실제 권한·안전·필수 자료 문제만 보고한다.
