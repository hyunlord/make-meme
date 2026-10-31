# C-012 PLAN — 같은 양끝, 반대 중간 경로: 최소 궤적 제어 능력 시험

- experiment_id: C-012-minimal-trajectory-capability
- 작성: 2026-11-01. 모든 신규 GPU 실행(VAE·학습·sampler·DragAnything) 전에 커밋한다.
- 연구 기준: 8b7a4f404f200046bc7b9abc183fd51e916d4fe4 (C-011). branch `docs/c-research-20261028`, 강제 reset 없음.
- 의뢰서: [work_orders/C012_MINIMAL_TRAJECTORY_CAPABILITY_KO.md](../../work_orders/C012_MINIMAL_TRAJECTORY_CAPABILITY_KO.md)

## 핵심 질문
같은 양끝 이미지·텍스트·초기 noise에서 궤적 A를 주면 A로, B를 주면 B로 움직이는가?
- Q1 과제가 구별 가능한가(renderer·VAE 재구성·평가기).
- Q2 현재 adapter가 두 clip 과적합 조건에서라도 제어를 배우는가.
- Q3 다른 제어 경로(VACE 동적 윤곽, DragAnything)는 같은 기능을 보이는가.
세 판정은 분리한다.

## 과제 (CPU renderer, `code/render_task.py`)
- 416×240, 33 frames, 정적 카메라·배경. 공 1개(d=56px), 원형 외곽, 고정 음영, 비대칭 무늬(파란 띠·흰 점·노란 점·검은 점). 회전·변형·크기 변화·가림·그림자 없음.
- 배경: 베이지 탁자면 + seed 20261201 정적 질감 + 서로 다른 모양의 고정 표식 4개(십자·사각·삼각·막대). 둥근 무늬 없음.
- 경로(픽셀 index 좌표): τ=t/32, x = W(0.25+0.5τ), y_A = H(0.5 − 0.2 sin²πτ), y_B = H(0.5 + 0.2 sin²πτ). t=0,32의 offset은 명시적 0. 시작 (104,120), 끝 (312,120), 중앙 간격 96px.
- 양끝 프레임은 한 번만 렌더링해 A/B가 공유한다(byte 동일). 같은 sprite를 bilinear 평행이동한다.
- 텍스트(A/B 공통): "A single patterned ball slides across a plain tabletop. The camera remains fixed." negative 'blurry, distorted, deformed, watermark'.
- 점: 공 중심 + 반지름 14px의 8점 = 9점, 전 프레임 visible/valid=True, anchor_valid=True. 정규화 (x+0.5)/W.
- 라벨: ORACLE_RENDERER / TRAIN_TARGET / TRACK_GIVEN / MASK_GIVEN. CoTracker·SAM 0회.
- CPU 검사(사전 확인 완료, Spark dry run): 양끝 byte 동일, 중앙 간격 96.0px, 전 프레임 화면 안·면적 일정, 9점 모두 mask 안, 객체 밖 배경 픽셀 불변.

## 평가기 (`code/evaluate.py`, 생성 결과를 보기 전에 고정)
- 판독: 시작 앵커의 공 주변 64×64 crop 하나를 template으로 **전체 화면**에서 TM_CCOEFF_NORMED. 요청 경로는 입력하지 않는다.
  - peak < 0.50 → missing
  - 두 번째 peak(첫 peak에서 1d 밖)가 0.50 이상이고 첫 peak의 0.75배 이상 → duplicate
  - 정답에 가까운 후보를 고르지 않는다.
- 배경 이동: 4개 표식을 각각 전체 화면에서 matching하고, 이동량 중앙값을 쓴다.
- 표본: τ = 0, 1/8, …, 1 → 33프레임에서는 0,4,…,32. 외부 모델은 자기 프레임 i/(N−1) 중 가장 가까운 것을 쓰고, 그 τ의 정답 함수와 비교한다.
- fixture(CPU, 통과): 정답 A/B 오차 0.03px(peak 0.999), 정답 쌍 CAPABILITY_PASS, 빈 배경 missing(peak 0.21), 공 두 개 duplicate, 카메라 이동(9,6) 감지(10.8px).
- VAE 재구성 A/B도 생성 전에 같은 판독기로 검증한다(RECONSTRUCTION_CONTROL).
- 판독기가 변형된 출력에 맞지 않으면 블라인드 정적 시트 수동 주석으로 대체할 수 있다. 같은 규칙을 모든 방법에 적용하고, 같은 세션 agent 주석임을 표시한다.

### 성공 기준 (pilot; A/B 각각, d=56, 0.35d = 19.6px)
1. 9시점 중 8 이상에서 단일 객체 식별
2. missing/duplicate 수와 관측 오차를 별도 보고(제외해서 점수를 만들지 않음)
3. 관측 시점 평균 중심 오차 ≤ 19.6px
4. 시작·끝 오차 각각 ≤ 19.6px
5. 중앙 5시점(τ 0.25–0.75) 중 4개 이상에서 A는 y<120, B는 y>120
6. τ0.5의 A/B 출력 중심 간격 ≥ 48px
7. 내부 7시점에서 matched 평균 오차 ≤ 0.5 × swapped 평균 오차
8. 배경 표식 이동 중앙값 ≤ 3px(전 표본)
9. 공 외형 유지: template peak ≥ 0.50(색 조각만 따라가는 경우 제외), 시트로 확인

판정:
- 1–9 모두 통과하고 중앙(τ0.25–0.75)에 누락이 없으면 **CAPABILITY_PASS**
- 5·6만 통과하면 **PARTIAL_CONTROL**
- 그 밖에는 **NO_CONTROL**

BASE는 궤적 입력이 없으므로 A·B 경로 각각에 대한 오차만 보고한다.

## 실행 순서와 설정
공통 VACE 1.3B: CFG 1, Euler 50, shift 5, 416×240×33, seed 20261028, 정상 white 마스크 (v,v,v), endpoint 중간 RGB (127,127,127).
1. `build_cache.py`
   - endpoint VACE context를 A/B 공유로 1회 만든다.
   - 양끝은 각각 독립 단일 프레임 encode로 point patch를 얻는다(A/B patch 동일 assert).
   - A/B target을 encode한다. loss mask는 renderer mask를 쓴다.
   - 진단 decode 2회로 재구성 A/B를 만든다.
   - public encode 6회, decode 2회.
2. RECONSTRUCTION_CONTROL 판정(CPU).
   - 재구성에서 공 식별 실패나 경로 구분 실패가 나오면 **TASK_NOT_VALIDATED**로 멈춘다. 2048 학습을 강행하지 않는다.
3. ENDPOINT_BASE 1개를 만든다(adapter OFF).
4. NATIVE_LAYOUT_A/B 2개를 만든다. C-006 규칙(흰 바탕·검은 외곽선 두께 3)으로 정답 mask에서 윤곽을 만들고 `layout_mov`로 넣는다. 양끝·텍스트·noise는 같다.
   - 이 대조군은 sparse point보다 많은 공간 정보를 받는다.
5. adapter 학습(`train_capability.py`)
   - 구조: 기존 PointAnchorAdapter 그대로(MLP·projection·마지막 4 block·kernel·grouping·FP32 master·BF16 backbone).
   - 초기값: C-006 `checkpoint-000.pt`의 adapter 값만 쓴다. optimizer·RNG·cursor는 새로 만들고 train seed는 20261104다. C-011 학습 checkpoint는 쓰지 않는다.
   - 학습 설정: AdamW lr 1e-4, β(0.9, 0.999), wd 0.01, clip 1, batch 1, FM target ε−z0, 객체/배경 면적 정규화 MSE 합, shift5 1000-grid.
   - 의도적 변경(단일 변수 비교 아님): 자료 A/B 두 clip(epoch마다 randperm(2)로 번갈아), NULL dropout 0, negative-text dropout 0, 최대 2048 update.
   - 추가 loss 없음.
   - segment 0→256→1024→2048로 나눠 돌린다. 각 segment는 adapter·optimizer·generator·order·cursor·RNG를 그대로 이어받는다.
   - 학습 벽시계 상한은 누적 active 5400초(90분)다.
   - 각 checkpoint마다 보조 probe 8 forward를 한다(σ 1.0/0.95/0.50/0.05 × point A/B, 공유 noise seed 20261105, 총 ≤ 24 ≤ 32). 기록 항목: cos(pred_A−pred_B, u_A−u_B), matched/swapped loss.
6. 각 checkpoint 256 → 1024 → 2048마다:
   - 같은 가중치·noise·context로 ON(point A)과 ON(point B) 영상 2개를 만든다.
   - 기준을 통과하면 학습을 멈추고, 같은 checkpoint에서 seed 20261029로 A/B 2개를 만든다.
   - seed 20261029에서 실패하면 SEED_SENSITIVE_CAPABILITY로 판정한다. 다른 seed는 찾지 않는다.
7. DragAnything A/B 2개.

### A/B 동일·차이 확인
- 동일해야 하는 것: 첫 model_fn의 vace_context 96채널 sha, 초기 latent sha, text, checkpoint sha, endpoint patch·box·visibility·valid·anchor_valid·motion_available.
- 달라야 하는 것: 중간 point 좌표뿐.
- label·파일명은 lookup에만 쓰고 신경망 입력이 아니다.

## DragAnything (공식 1개, 기능 대조)
- 코드: github.com/showlab/DragAnything @ `79355363218a7eb9b3437a31b8604b6d436d9337`. 저장소에 LICENSE 파일이 없어 코드 재배포 조건은 미확인이며, 공개 repo에는 넣지 않는다.
- 가중치(받은 것은 fp16 변형만, 합계 약 11GiB로 상한 40GiB 이내):
  - `stabilityai/stable-video-diffusion-img2vid` @ `9cf024d5…`: unet·image_encoder·vae fp16, license "other"(SVD community license, 비상업 연구 범위로 사용)
  - `weijiawu/DragAnything` @ `f66fb7cc…`: apache-2.0
  - `windwhinny/chilloutmix` @ `e0bf5dae…`: DIFT entity 특징용, HF repo에 license 표기 없음(원 모델은 CreativeML OpenRAIL-M로 알려짐, 미확인)
- 별도 venv를 만든다. 기존 VACE venv의 Torch 2.14+cu130을 재사용하는 경로를 우선한다. VACE venv는 변경하지 않는다. requirements.txt는 그대로 실행하지 않는다.
- 입력과 해상도:
  - 공식 데모 해상도 576×320, 20 frames, motion_bucket 180, control scale 1.0, decode_chunk 8
  - 첫 프레임을 종횡비 유지 letterbox로 넣는다(scale 4/3 → 555×320, 좌 10/우 11 pad). 같은 affine으로 경로를 변환하고, τ = i/19는 같은 경로 함수에서 얻는다.
  - 첫 mask는 renderer 정답을 같은 letterbox로 넣는다. entity는 공 하나다.
- 끝 앵커는 입력하지 않는다(모델 미지원). 표에 "첫 이미지+궤적"으로 명시한다.
- DIFT 특징은 첫 이미지에서 고정 seed로 1회만 계산해 A/B가 공유한다. sampler generator seed는 20261028이다. A/B는 같은 noise를 쓴다.
- 출력은 letterbox를 역변환(crop 후 resize)해 416×240 좌표로 판독한다. 시간 warp는 하지 않는다.
- 준비·호환성 작업은 최대 90분이다. 그 안에 실행하지 못하면 COMPARATOR_BLOCKED로 기록하고, 성능 실패로 보지 않는다.

## 예산
- sampler(우리 모델):
  - BASE 1, layout 2, adapter 최대 6, 두 번째 seed 최대 2 = 최대 11
  - DragAnything 2
  - 기계 복구 예비 1, hard cap 14, 품질 재시도 0
- 학습: 최대 2048 update, forward/backward 각 ≤ 2048, 진단 forward 3, probe ≤ 24.
- VAE: cache·진단용 public encode 6(상한 20), 진단 decode 2(상한 2). sampler 내부 encode/decode는 따로 센다.
- 다운로드 ≤ 40GiB(실제 약 11GiB). 외부 호환성 작업 ≤ 90분, 전체 ≤ 6시간.
- SAM·CoTracker·imagegen·14B 0회.
- guard·PSI·headroom·swap·서비스 정책은 바꾸지 않는다. 실행은 C-001 run_guarded + C-003 guard(cpu → heavy)를 그대로 쓴다.

## 결론 규칙 (의뢰서 §13)
- A. adapter가 통과하면 MINIMAL_CAPABILITY_ESTABLISHED. 2D 강체 이동의 학습 가능성만 확인한 것이다.
- B. adapter는 실패하고 DragAnything은 통과하면 CURRENT_ADAPTER_DEPRIORITIZED.
- C. adapter는 실패하고 native layout은 통과하면 point를 유효한 생성 조건으로 연결하는 경로가 우선 문제다. VACE 입력 쪽 표현이 다음 후보다.
- D. 모두 실패하고 renderer/VAE는 정상이면 기능 증거 없음. adapter 확대 학습을 중단한다.
- E. 외부 방법을 실행하지 못하면 COMPARATOR_NOT_EVALUATED.
- F. 평가기·재구성이 유효하지 않으면 TASK_NOT_VALIDATED.

중단 판단은 수학적 불가능성 선언이 아니라 개발 투자 판단이다. 추가 loss·scale·주입 위치 변경·다음 학습은 자동 시작하지 않는다.
