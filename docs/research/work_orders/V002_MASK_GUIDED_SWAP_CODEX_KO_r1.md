# V-002 실행 의뢰서 (개정판 r1)
## 원본 영상을 유지하고 개 영역만 다시 칠한다 — VACE 마스크 편집(MV2V) + SAM 마스크 + 기존 앵커

**새 Codex 세션 가능 · DGX Spark 실행 · Mac 전달 · imagegen 0회 · 영상 생성 최대 5개 · 학습 0회**

> **이 문서는 실행 승인이다. 아래 범위에서 V-002를 실제로 진행해 줘.**
> 같은 범위의 승인을 다시 기다리지 않는다. 실제 권한·안전 정책은 준수한다.
> 이 개정판은 2026-11-04 첫 실행(`9f78153`, BLOCKED_EXTERNAL_GPU, 영상 0/5)을 대체한다. 첫 실행의 기록·입력·판정은 보존하고 소급 수정하지 않는다.

| 항목 | 내용 |
|---|---|
| 저장소 / branch | `hyunlord/make-meme` / `docs/v-research-20261103` (`9f78153` 위에서 계속) |
| 부모 | V-001 (`0cfd0ef`), V-002 첫 실행 (`9f78153`) |
| 실험 경로 | `docs/research/experiments/V-002-mask-guided-swap/` (같은 경로, `RESUME_R1/` 하위에 이번 실행 기록) |
| 의뢰서 보존 | `docs/research/work_orders/V002_MASK_GUIDED_SWAP_CODEX_KO_r1.md` |
| 동봉 설정 | `V002_PREDECLARED_CONFIG_r1.json` |

### r1에서 바뀐 것

1. **외부 GPU 작업이 있으면 멈추지 않고 기다린다**(§3.2). 첫 실행을 막은 작업은 사용자의 `dgx-serving` r25 grid 벤치마크였다.
2. **VACE 14B는 transformer를 bf16 파일로 먼저 변환한다**(§4.4). 첫 실행의 128GiB 추정은 fp32 원본 page cache 58.9GiB가 대부분이었다.
3. **drop-caches helper는 14B와 LTX의 필수 조건**이다. 없으면 그 두 단계만 건너뛴다(§3.1).
4. `fls-slot-keeper`가 범용 heavy 슬롯 관리자이면 그것을 쓴다(§3.3).
5. 첫 실행에서 만든 마스크·M1–M3 입력·canny 조건을 **재사용**한다(§4.1).

---

## 0. 배경 — V-001에서 확인한 것

- **E1(LTX-2.3 + depth IC-LoRA)**: 영상 2개가 나왔고, 사용자가 직접 보고 판정했다. **"개가 움직이지만 원본과 전혀 다른 동작을 한다."** 원인 분석:
  - 조건은 1단계(576×320)에만 들어가고, ref0.5라서 조건 영상은 288×160이다. 이 크기에서 개 한 마리는 약 50×60px다.
  - LTX VAE의 시간 압축이 8배라 빠른 동작이 뭉개진다.
  - 바닥 위의 개는 depth 대비가 약하다.
  - 결과적으로 첫 프레임만 고정되고 동작은 모델이 지어냈다.
- **E2(Bernini)**: 1 step 296초라 실용성이 없다. 49프레임 실행 중 `NVRM NV_ERR_NO_MEMORY`로 Spark가 멈췄고 재부팅됐다. **보류.**
- **GB10 통합 메모리**: 모델 파일의 page cache와 CUDA 할당이 같은 풀을 쓴다. 그래서 같은 가중치가 이중으로 잡힐 수 있고, 드라이버 수준 할당 실패는 MemAvailable·PSI 가드보다 먼저 시스템을 멈출 수 있다. NVIDIA는 큰 모델 적재 전에 buffer cache를 비우라고 안내한다.

이번 방식: **원본 영상을 그대로 두고 SAM 마스크로 개와 반사 영역만 다시 칠한다.** 움직이는 마스크 실루엣이 원본 자세를 직접 담는다. Wan VACE의 시간 압축은 4배다. 배경은 원본 픽셀이 남는다.

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

- V-001의 구간 `[240,313)`(73프레임·24fps), 캐스팅(오른쪽 앞 원본 갈색 개 → Lab=track0, 왼쪽 뒤 원본 회색 개 → IG=track1), 반사(track2·3), 앵커 1장을 재사용한다.
- 첫 실행에서 만든 입력을 hash로 검증해 재사용한다.
- V-001 E1 출력 2개에 SAM 측정(기준선 수치).
- VACE 1.3B 3개 변형 → 자동 규칙으로 1개 선택 → VACE 14B 1회. 별도로 LTX canny 대조 1회. **총 영상 최대 5개.**
- 측정·뷰어·검토 양식·기록·전달.

### 0회

- imagegen, 새 앵커, 학습, Bernini, 외부 API.
- 결과를 보고 마스크 팽창·프롬프트·seed·구간을 바꾸는 재시도.
- 다른 프로세스·서비스 종료, 공통 가드 코드 수정, sudo의 다른 용도 사용.

---

## 3. 운영

### 3.1 GB10 통합 메모리 대책 (모든 heavy 적재)

1. **page cache 비우기**: heavy 모델 적재 직전마다 `sudo -n /usr/local/sbin/drop-caches`를 실행하고 결과를 기록한다(사용자가 설치한 단일 명령).
   - helper가 없거나 거부되면: **VACE 1.3B와 SAM은 진행**하고, **VACE 14B와 LTX canny는 `SKIPPED_NO_CACHE_HELPER`로 건너뛴다.**
2. **할당기 설정**: 모든 heavy worker에 `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True`.
3. **사전 peak 추정**: 가중치·텍스트 인코더·VAE·활성값·원본 파일 page cache 추정이 **100GiB를 넘으면 시작하지 않는다.** 근거를 기록한다.
4. **NVRM 감시**: worker 실행 중 커널 로그를 감시하고, `NV_ERR_NO_MEMORY`가 한 번이라도 나오면 즉시 worker를 정상 종료한다. `ENGINE_STOPPED_NVRM`으로 기록하고 재시도하지 않는다.
5. worker 한도는 `MemoryMax=MemoryHigh=100GiB`. V-001 §7의 중단 조건(OOM, MemAvailable < 12GiB가 30초 지속, PSI full > 25%가 60초 지속)은 그대로다.

### 3.2 외부 GPU 작업 — 기다린다

- 각 heavy 단계 시작 전, 60초 간격으로 GPU compute 프로세스와 알려진 외부 배치(예: `dgx-serving`의 `r25_grid` 부모 프로세스)를 관측한다.
- **3분 연속(3표본)으로 외부 GPU 프로세스와 외부 배치 부모가 모두 없을 때 시작한다.** 자식 프로세스 사이의 순간 공백은 종료로 보지 않는다.
- 대기는 단계마다 최대 120분, 전체 누적 최대 180분이다. 넘으면 남은 단계를 `BLOCKED_EXTERNAL_GPU`로 기록하고, 끝난 단계까지 전달한다.
- 실행 중에 외부 GPU 작업이 새로 나타나면, 진행 중인 생성은 끝까지 마치되 결과에 `CONCURRENT_EXTERNAL_GPU`를 표시하고, 다음 단계는 다시 기다린다. 다른 작업을 종료하지 않는다.
- 상시 서비스(millie 데모, ht-estate API·임베딩, fls-play 등 CPU 서비스)는 외부 GPU 작업으로 보지 않는다. 시작 시 그 메모리 사용량만 기록한다.

### 3.3 fls-slot-keeper

`fls-slot-keeper.service`(설명: "the DGX slot keeper (who takes a heavy slot)")를 읽기 전용으로 확인한다.
- 다른 프로젝트도 쓸 수 있는 문서화된 인터페이스가 있으면, V-002 heavy 단계마다 슬롯을 받아 실행하고 끝나면 반납한다. §3.2 관측은 그대로 병행한다.
- fls 전용이거나 인터페이스가 불분명하면 쓰지 않고, 확인한 내용만 기록한다. 서비스 설정은 바꾸지 않는다.

---

## 4. 입력과 실행

### 4.1 입력 — 첫 실행 산출물 재사용

첫 실행(`8a7d4cf`·`9f78153`)에서 만든 다음 파일을 `INPUTS_PUBLIC.json`·`MASK_CHECK.json`의 hash와 대조해 재사용한다. hash가 다르거나 파일이 없으면 아래 규약으로 다시 만들고 차이를 기록한다.

- 해상도 832×480(1280×720 → 853×480 → 가로 중앙 832 크롭), 73프레임(`4n+1`), 24fps.
- 생성 마스크: Lab 24px, IG 12px, 반사 12px 팽창(832×480 기준)의 합집합. **흰색 RGB (255,255,255) 세 채널 검사 필수**(C-008 빨강 마스크 사고).
- 참조 이미지 2장: 앵커에서 SAM 앵커 마스크로 잘라 흰 배경에 놓은 Lab·IG crop.
- 프롬프트(영문 고정): `Two dogs dancing on a reflective floor in the same room: on the right, a large black Labrador Retriever with a broad chest and thick legs; on the left, a slender grey Italian Greyhound. Their reflections on the floor match them. Keep the original motion, timing, room and camera.`
- seed `20261103`.

### 4.2 V-001 E1 기준선 측정 (먼저)

V-001 E1 두 출력에 §5.1 지표를 계산한다. 사용자의 "전혀 다른 동작" 판정과 나란히 수치로 남기기 위해서다.

### 4.3 VACE 1.3B 세 변형

| ID | 마스크 안 내용 | 프레임 0 | 참조 |
|---|---|---|---|
| **M1** | 회색 127 | 원본 프레임 + 마스크 | Lab·IG crop |
| **M2** | 원본 depth(V-001 depth raw를 CPU로 리샘플, 재추론 0회) | 원본 프레임 + 마스크 | Lab·IG crop |
| **M3** | 회색 127 | **앵커 RGB, 마스크 0(유지)** | Lab·IG crop |

- 마스크 밖은 모두 원본 RGB, 마스크 0이다.
- M3의 첫 프레임 마스크 0은 VACE 마스크의 시간 압축 때문에 latent 수준의 엄격한 고정을 보장하지 않는다(첫 실행에서 기록한 제한). 앵커 Lab 윤곽(약 1.25배)과 프레임 1 원본 마스크 사이의 전환부를 관측 항목으로 남긴다.
- 공식 VACE 코드 또는 C 트랙에서 검증한 runner(C-008/C-009 마스크 수정 반영본)를 쓴다. step·CFG·shift는 공식 기본값이고 실제 값을 기록한다.

### 4.4 14B 선택과 실행

**선택 규칙 (결과 전에 고정)**
1. 실제 개 2마리 검출 프레임이 66/73 이상인 변형만 후보로 남긴다.
2. 그중 캐스팅별 실루엣 IoU 평균(Lab·IG 평균)이 가장 높은 변형을 고른다.
3. 차이가 0.02 이내면 M1을 고른다.
4. 후보가 없으면 `NO_14B_CANDIDATE`로 기록하고 14B를 건너뛴다.

사람의 판정을 기다리지 않는다.

**bf16 변환 (14B 실행 전, CPU)**
- `research/make-meme-c/models/Wan2.1-VACE-14B`의 transformer 저장 dtype을 확인한다.
- fp32이면 CPU에서 shard 단위로 bf16 safetensors로 변환한다. 낮은 우선순위, 순차 처리, `CUDA_VISIBLE_DEVICES=""`.
- 모든 tensor가 `원본.to(torch.bfloat16)`과 bit 단위로 같은지 검증한다(V-001 E2와 같은 방식). 원본은 보존한다.
- 로더가 bf16으로 적재하는지 코드로 확인하고 변환본을 적재한다.
- 변환 후 사전 peak를 다시 추정한다(기대값: bf16 transformer 약 32GiB + T5/VAE 약 11GiB + 활성값 약 24GiB ≈ 67GiB). **100GiB 이하일 때만 진행한다.**

**실행**
- 선택된 변형과 같은 입력. §3.1의 모든 대책을 적용한다.
- 시간 측정 1 step → 73프레임 예상이 150분을 넘으면 49프레임으로 줄인다. 49프레임도 225분을 넘으면 `ENGINE_TOO_SLOW`로 건너뛴다.

### 4.5 LTX canny 대조 1회

V-001 E1 설정 그대로(1152×640, 앵커 첫 프레임, distilled two-stage, Union IC-LoRA 강도 1.0, seed `20261103`)에 조건만 **canny**로 바꾼다. 공식 CannyEdgePreprocessor 기본값(92/200)을 쓴다. 첫 실행에서 만든 canny 조건 영상을 hash로 확인해 재사용한다.

### 4.6 순서와 예산

| 단계 | 승인량 |
|---|---:|
| 입력 재사용 검증 | CPU |
| V-001 E1 SAM 측정 | 2개 |
| VACE 1.3B | 3회(M1–M3) |
| M1–M3 SAM 측정·선택 | 3개 |
| 14B bf16 변환 | CPU 1회 |
| VACE 14B | 시간 측정 1회 + 생성 1회 |
| LTX canny | 1회 |
| 출력 SAM 측정 | 생성된 모든 출력 |
| 품질 재시도 | 0회 |
| 실행 상한 | 7시간(외부 GPU 대기 시간 제외) + 대기 최대 180분. 마지막 30분은 기록·전달 |

순서: 인수 → `RESUME_R1` 사전 commit → helper·slot keeper 확인 → 입력 검증 → E1 SAM 측정 → M1 → M2 → M3 → 측정·선택 → 14B 변환 → 14B → LTX canny → 측정·뷰어·전달.

- 한 단계가 막혀도 나머지는 진행한다.
- **기계적 오류**(경로·형식·해상도·프레임 배수)는 V-001 개정 4의 사전 허용 규칙대로 스스로 고치고 기록한다. 품질 관련 설정은 바꾸지 않는다.
- **중간 전달**: M1–M3가 끝나면 14B로 넘어가기 전에 검토 페이지와 compact ZIP을 한 번 갱신·전달한다. 이후 단계가 막혀도 1.3B 결과는 사용자가 볼 수 있게 한다.

---

## 5. 측정과 검토

### 5.1 자동 측정 (SAM, 원본 1280×720 좌표로 환산)

| 지표 | 정의 |
|---|---|
| **실루엣 IoU** | 캐스팅별 출력 마스크와 원본 마스크(팽창 전)의 프레임별 IoU. 동작 추종의 주 지표 |
| 궤적 거리 | 캐스팅별 중심 궤적의 평균 거리(화면 가로 대비 %) |
| 개체 수 안정성 | 실제 개체(반사 제외) 2마리가 검출된 프레임 비율 |
| 뒤바뀜 | 캐스팅과 반대로 대응되는 프레임 수 |
| Lab/IG 크기비 | 프레임별 bbox 높이비의 중앙값. 원본 비율·앵커 비율과 함께 표시 |
| 반사 색 | 반사 트랙과 위 개체의 평균 색 차(참고값) |
| 마스크 밖 보존 | 마스크 밖 영역의 원본 대비 평균 절대 차 |
| 비용 | 실행 시간, 최대 메모리, step 수, NVRM·가드·대기 이벤트 |

### 5.2 진단 시트

출력마다 9시점(0, 9, …, 72)을 한 줄로 놓는다: 원본 / 모델 입력(마스크 적용 영상) / 출력 / 출력과 원본 실루엣 겹침.

### 5.3 뷰어

동기 재생: 원본 / V-001 E1-s1 / M1 / M2 / M3 / 14B / LTX-canny. 같은 표시 크기로 맞추고, 실행되지 않은 열은 이유와 함께 NOT_RUN으로 표시한다. 수치 표와 진단 시트 링크를 붙이고, 빈 `HUMAN_REVIEW.md` 양식을 둔다.

---

## 6. 판정과 다음

- 기술: 단계별 `RAN` / `ENGINE_STOPPED_NVRM` / `ENGINE_STOPPED_GUARD` / `ENGINE_TOO_SLOW` / `NO_14B_CANDIDATE` / `SKIPPED_NO_CACHE_HELPER` / `BLOCKED_EXTERNAL_GPU` / `CONCURRENT_EXTERNAL_GPU` 표시.
- 품질: `HUMAN_REVIEW_PENDING`.
- 다음 후보(자동 시작하지 않음):
  - 동작이 따라오고 외형도 되면 → **V-003: 15초 전체를 구간 분할 생성.**
  - 동작은 따라오는데 Lab이 작으면 → Lab 마스크를 앵커 기준으로 키우는 규칙 검토.
  - 동작이 여전히 안 따라오면 → 마스크 편집 자체의 한계로 기록하고 원인을 다시 진단.

---

## 7. 산출물·전달

`RESUME_R1/` 아래에 `PLAN.md`, `INPUT_REUSE_CHECK.json`, `RUNS.json`, `METRICS.json`, `WAIT_LOG.json`(외부 GPU 관측·대기), `RESULTS.md`(영상·비용을 먼저, 검사 세부는 뒤에), `HUMAN_REVIEW.md`, `REPRODUCE.md`를 둔다. 실험 루트의 `METHOD_KO.md`는 필요한 경우에만 갱신한다.

개인 미디어는 Git에 올리지 않는다. 문서·비민감 코드·hash만 push한다. compact ZIP을 Mac `~/Downloads/V002-review-<날짜>-r1.zip`에 두고, 무결성 확인은 한 줄 요약만 쓴다. HISTORY/ROADMAP에 한 줄씩 기록한다. 후속 생성은 예약하지 않는다.

## 근거

[S1] V-001 기록: https://github.com/hyunlord/make-meme/tree/docs/v-research-20261103/docs/research/experiments/V-001-anchor-propagation-baseline
[S2] V-002 첫 실행 기록: https://github.com/hyunlord/make-meme/commit/9f78153
[S3] NVIDIA DGX Spark 통합 메모리·buffer cache 안내: https://build.nvidia.com/spark/vlm-finetuning/troubleshooting.md
[S4] VACE 공식 저장소: https://github.com/ali-vilab/VACE
[S5] C-008 마스크 색 오류 기록: https://github.com/hyunlord/make-meme/tree/docs/c-research-20261028/docs/research/experiments/C-008-conditioning-parity

## 실행 시작

위 범위에서 지금 V-002 r1을 시작해 줘. 외부 GPU 작업이 있으면 §3.2대로 기다린 뒤 진행한다. 실제 권한·안전·필수 자료 문제만 보고한다.
