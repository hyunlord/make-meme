# B-006 사전 계획 — 동물 동작 표현과 영상 직접 조건화의 적합성 검증

작성: 2026-10-22 · 상태: **PLANNED / NOT_RUN** · parent: B-005

## 0. 단계 전환

B-005의 2×2×2seed 결과: R-bg/R-gray와 C-real/C-null을 바꾸면 출력 자세가 변하지만, 실제 Labrador 정체성과 원본 뒷발 직립·머리/발 타이밍을 함께 수용한 결과 **0/8**. 입력 경로가 작동하는지 진단하는 목적은 달성. 같은 회색/검정 대체 입력 실험 반복은 종료한다.

**새 질문:** 원본 17프레임에서 움직임을 신뢰할 수 있게 표현하는 방법은 무엇인가? 그리고 그 표현을 실제 받는 로컬 영상 생성 모델이 있어 DGX Spark 연구에 적합한가?

이번은 단순 pose 추정 모델 개발이나 14B 모델 추가 설치를 약속하는 작업이 아니다. *동작 표현의 정보 손실, 입력 인터페이스, 장비 가능성*을 검증하고 다음 실질적인 생성 baseline 하나를 결정한다.

## 1. 방향성·경계·자원 상한

- 연구 B만 진행. A(native imagegen-only MCP) 코드·자산·기록은 동결.
- 실제 Lab/IG 사진과 원본 영상만 읽기 전용으로 사용. A가 imagegen으로 만든 영상/이미지를 B 참조·학습 입력으로 가져오지 않는다.
- Codex imagegen, 외부 생성 API, 유료 GPU, 타 연구자 프로세스 중단, sudo/driver/swap/clock 변경 금지.
- **새 대형 모델 다운로드 0, 신규 diffusion 영상 생성 0회, optimizer 업데이트 0회.** 사전 훈련된 외부 animal pose 모델도 이번에는 필수 설치하지 않는다.
- 최대 **3시간** 내 읽기 전용 코드·문헌 조사, 수동 확인 가능한 **원본 17프레임 동작 주석/가시화**와 생성 모델의 조건 인터페이스 타당성 판정. 별도 GPU 작업이 기존 서비스와 경합하면 CPU만 사용.
- 현재 Spark 모델·환경·디스크·프로세스는 읽기 전용 확인. ARM64/Blackwell 호환성을 다른 GPU 벤치마크에서 추정하지 않는다.
- 기존 B-003/004/005 private input·output 경로는 *직접 확인 후* 재사용; 개인 폴더 경로를 추측하거나 광범위하게 검색하지 않는다.

## 2. Step A — 대상 동작의 실제 정보 감사

기존 고정 source f0..f16의 실제 decoded RGB(17장/24fps), Canny frames를 해시 대조 후 준비한다. 기존 원본이 비공개라면 비공개 작업 디렉토리에서만 처리한다.

핵심 의미 기반 landmark 후보:
- 머리: 코, 양 눈 또는 보이는 쪽 눈, 목 기준
- 몸통: 어깨 중심, 골반 중심(좌우가 구분 가능한 경우 각각)
- 사지: 좌/우 앞다리 어깨–팔꿈치–앞발, 좌/우 뒷다리 고관절–무릎–뒷발
- 추가: 꼬리 기반, 피사체 bbox/중심, 대략적 카메라 방향
- 가시성 상태: **visible / occluded / unobservable**를 명시. 2D 위치가 안 보이면 만들어내지 말고 null 처리하고, 왜 그런지 노트. left/right는 동물 자신의 좌/우로 정의; 카메라 반대 방향 혼동 기록.
- contact는 **visible evidence / possible / unknown**으로 분리. 한 화면에서 실제 3D 접촉·체중 분배를 확정하지 않는다.

APT-36K의 animal keypoint/temporal tracking 틀을 참고하되, 정면으로 서서 춤추는 소형 개체가 학습 분포에 들어간다고 가정하지 않는다. APT-36K의 공식 정의와 우리 수동 landmark mapping을 분리한다. 참고: https://github.com/pandorgan/APT-36K

최초 기준 프레임 0,4,8,12,16을 실제로 보고 수동 anchor 주석을 만들고, 시간이 허락하면 나머지 12프레임을 확장한다. **완성하지 못한 프레임은 NOT_ANNOTATED로 남긴다.** 이전/다음 frame 보간을 ground truth로 사용하지 않는다. 소수 landmark만 정확히 지정할 수 있다면 정확한 부분을 우선한다.

정규화 표현 예:
- 좌표 (x/W,y/H), 가시성 v, instance ID, 해부학적 점 ID
- root-relative: (p_j−p_root)/s_body. s_body 정의와 수치적 불안정/가림을 설명
- body-heading vs 2D torso angle, support/contact cues는 별도
- morphology는 skeleton bone length/체형에서 온 제약이고 motion은 시간별 root/관절 방향/각속도 변화라는 개념을 구분. 단순 scale 정규화가 다른 체형으로의 물리적 retarget을 해결한다고 주장하지 않는다.

## 3. Step B — 3가지 동작 표현의 비교

A. **Canny**: 현재 쓰는 픽셀 경계. 외형/배경 선과 관절 의미의 혼합, 뒤집힘·가림 시 ID 불명확.
B. **semantic keypoints/trajectory**: 관절/가시성/접촉의 해석 가능성과 annotation 오류·2D depth loss, 특히 비정상 직립 자세·좌우 혼동 문제를 기록.
C. **원본 RGB video driving**: 2D 자세/속도/가림/의상·배경 신호까지 보존하는 장점과 source identity/appearance leakage 문제를 같이 기술.

같은 17프레임에서 각 표현의 실제 input visualization을 만들고, **source 동작의 시간 정보 손실**을 비교한다. 잘 되는 프레임 1개만 선택하지 않고 f0/4/8/12/16 및 중요 실패 프레임을 함께 제시한다.

제출: annotated_landmarks.json, keypoint_overlay.mp4, Canny/source/keypoint 비교 정적 이미지, missingness/visibility summary. raw 동물 사진/영상·결과 영상은 GitHub 공개 금지.

## 4. Step C — 동작 조건을 실제 지원하는 모델 코드 감사

반드시 공개된 공식 코드/논문·실제 고정 commit 기반으로 2개 경로를 비교한다.

**후보 1: SCAIL-2** https://github.com/zai-org/SCAIL-2
- official branches \`wan-scail2\`, \`sat-scail2\`와 학습/추론 entrypoint, end-to-end RGB driving vs pose-rendered driving 모드를 구분.
- 실제 reference image/mask, driving video, driving mask, prompt 입력이 무엇인지 추적.
- 동물 driving은 가능하다고 기술돼 있지만 우리 직립 Lab 대체 성공을 보장하지 않는다는 점 명시.
- 공식 가중치 크기/의존성/단일 GPU 및 메모리 최적화/모델 전체 구성/ARM64와 Spark 가능성은 문서·code로 구체적으로 점검. 장비에서 **추론/미세조정 실제 가능 판정은 GPU 실행 전 UNKNOWN**.
- 신규 다운로드/설치/추론 **하지 않는다**.

**후보 2: 기존 Wan2.1-VACE-1.3B**
- 이미 확보한 DiffSynth pinned pipeline의 \`vace_video\`, \`mask\`, \`reference\` 조건 경로를 분석.
- keypoint heatmap, skeleton render, RGB driving 중 **어떤 형식을 model이 실제 학습된 조건으로 받아들이는지** 코드/학습자료를 확인. Python 인터페이스가 3채널 이미지를 받는다는 이유만으로 keypoints를 바꾸어 넣어도 성능이 나올 것이라고 가정하지 않는다.
- 구조 표현 전환이 새 데이터/finetuning 없이 의미 있는 효과를 낼지 판단.

표로 비교: task match / input semantics / native animal support / multi-character potential / checkpoint availability & license / pretrained training data / confirmed vs estimated memory / Spark compatibility unknowns / future LoRA path / hypothesis with most information gain.

선행 연구 참조:
- SCAIL-2: https://arxiv.org/abs/2606.10804
- APT-36K: https://arxiv.org/abs/2206.05683
- Kirin (quad motion, 문제 범위 차이 확인): https://kirin-ani.github.io/

모델의 paper abstract가 지원한다는 주장과 실제 공개 inference code가 지원하는 기능을 분리한다. 이름이 유명해서 선택하거나 개인 웹사이트의 출시 주장만 믿지 않는다.

## 5. 수학·연구 학습 내용

한국어 \`docs/research/lessons/B-006-animal-motion-representation.md\`:
- 2D pose p_{t,j}와 visibility v_{t,j}, image coords, root-relative/scale normalization.
- shape(retarget skeleton lengths) vs motion(relative joint angles, temporal derivatives), 2D ambiguity(occlusion/out-of-plane) 수학.
- frame time Δt=1/24 s, finite differences v=(p_{t+1}−p_t)/Δt; 불완전 annotation에서 미분값 계산 금지, smoothing의 편향.
- latent diffusion/Flow Matching 모델의 구조 condition과 RGB video-driving 조건의 정보 차이. 조건 엔트로피·정보 손실 직관. 엔트로피 숫자를 실제로 추정하지 않고 정성적 설명을 정보이론적 증명이라고 쓰지 않는다.
- 생성 모델이 keypoint를 입력받으려면 **그 표현에 대한 훈련/조건 adapter 경로가 왜 필요한지**, loss와 train target을 실제 지원 여부와 연결.
- 실제 가능한 작은 PyTorch example: joint heatmap renderer 또는 root-relative trajectory plot; 학생이 직접 구현/재실행 가능한 코드·shape.
- 직관 → 식/가정 → tensor → 원본 실측/시각화 → 한계 → 질문 3개/별도 해설.

## 6. 결정 게이트

최종 결론은 **한 개 다음 실험 계획**으로:

- SCAIL-2 official end-to-end driving이 우리 문제에 맞고 Spark feasibility plausible: **B-007에서 제한된 모델 설치/공식 예제 smoke/실제 단일 컷 1개 추론**만 신청. VRAM 부족·의존성 충돌이면 모델 선택/실행 예산을 재평가. 설치나 대규모 다운로드는 B-006의 승인 범위가 아님.
- 기존 VACE가 해부학적 keypoint를 직접 지원하지 않는다면 'keypoint PNG를 vace_video에 넣자'라고 자동 결론 내리지 않는다. 조건 adapter/학습 자료 필요성을 우선 기록.
- source 동작 자체를 2D 관절로 안정적으로 주석하기 힘들면 keypoint-only 생성 경로를 섣불리 선택하지 않는다. RGB video driving을 우선 제안할 수 있다.
- 모든 모델이 불가능해도 **단 하나의 구현 가능성/의존성 장애**를 명시해 다음 해결 순서를 결정한다.

**비교와 모델 선택 자체가 motion transfer 성능 성공이나 논문 새로움은 아니다.** 시각화 완료와 실제 비디오 생성 성공을 구분.

## 7. GitHub 기록·완료 범위

시작 전 연구 브랜치 \`docs/b-research-20261022\`에서 CHARTER/ROADMAP/HISTORY/RECORDING_PROTOCOL과 B-005 RESULTS를 읽고 실제 실행 checkout·공개 문서 worktree의 차이를 기록. 이 PLAN을 사전등록으로 보존하고 작업 코드/수동 annotation schema를 결과 전에 커밋한다.

종료 후 \`docs/research/experiments/B-006-motion-representation/RESULTS.md\`, \`docs/research/lessons/B-006-animal-motion-representation.md\`, HISTORY/ROADMAP 갱신·커밋·원격 HEAD 확인. 개인 영상, 동물 사진, keypoint overlay(실제 영상이 포함), 비밀키, 절대 경로, 대형 모델·캐시와 비공개 입력은 GitHub에 push 금지; schema/이론·비민감 요약/코드만 공개. raw overlay/metadata 등은 private local ZIP에 보존.

ZIP은 Mac/Spark 경로·전송 여부·CRC/파일 hash를 구별해 보고. 이번 B-006는 새 영상 생성 모델 추론/학습 0회, 안전한 비학습식 시각화만 허용. 최대 3시간. 종료 후 next experiment 하나만 추천하고 자동 확대/실행 금지.
