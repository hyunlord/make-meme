# C-012 통합 작업 의뢰서
# 새 Claude Code 세션용
# 최소 궤적 제어 기능 증명과 공개 방법 비교
#
# 저장소: hyunlord/make-meme
# 장비: 기존 DGX Spark
# 실행 담당: Claude Code
#
# 이번 목표는 현재 adapter를 반드시 살리는 것이 아니다.
# 실제 제어 성공을 얻거나, 이 경로의 확대 개발을 멈출 근거를 얻는다.

(보존 메모: 사용자가 대화에 붙여 넣은 의뢰서 원문을 그대로 옮겼다. 원문 후반부의 띄어쓰기 누락은 원문 그대로다. 이어서 받은 실행 승인 메시지는 맨 아래 "실행 승인" 절에 옮겼다.)


## 0. 이번 작업이 이전 실험과 다른 점

최종 연구 목표는 다음과 같다.

원본 영상 + 텍스트 + 선택적 참조 이미지
→ 소수의 편집 앵커
→ 원본 동작과 새 대상 외형 연결
→ 개인 DGX Spark에서 실행 가능한 영상 편집

현재까지:
- VACE 1.3B로 양끝 앵커 기반 생성 경로를 확보했다.
- 동적 윤곽은 일부 거친 동작을 제어했다.
- 학습 캐시의 RGB 마스크 오류를 찾아 정상화했다.
- 정상 조건에서도 현재 point adapter의 추가 동작 이득은 미입증이다.
- C-010에서는 궤적 신호가 예측까지 전달됨을 확인했다.
- C-011에서는 동적 윤곽을 제거해도 ON/NULL 차이가 유용한 제어로
  이어지지 않았다.

이제 일반 동물 영상에서 작은 차이를 계속 진단하는 방식을 멈춘다.

이번 핵심 질문:

“같은 물체·배경·시작 이미지·종료 이미지·텍스트·초기 noise에서
궤적 A를 주면 A로, 궤적 B를 주면 B로 움직이게 할 수 있는가?”

처음에는 일반화가 아니라 최소 기능을 검증한다.
아주 작은 학습 자료에 과적합하는 것을 명시적으로 허용한다.

최종 산출물은 다음 중 하나여야 한다.
- 같은 양끝에서 서로 다른 두 경로를 실제로 따르는 생성 영상.
- 현재 구조가 정해진 쉬운 과제와 자원 예산에서도 이를 보이지 못했다는
  결과와, 이 경로의 확대 개발을 멈추거나 변경할 판단.

loss 감소·gradient 연결·출력 차이·검사 통과만으로 성공하지 않는다.
새 보조 loss를 하나 더 붙이는 작업으로 바꾸지 않는다.


## 1. 기준 이력과 새 세션 인수

최신 기준:
8b7a4f404f200046bc7b9abc183fd51e916d4fe4

부모 실험:
docs/research/experiments/C-011-endpoint-only-trajectory-ablation/

관련 경로:
- C-006-motion-point-adapter-pilot
- C-008-conditioning-parity
- C-009-corrected-conditioning-retrain
- C-010-trajectory-signal-diagnostics

권장 새 경로:
docs/research/experiments/C-012-minimal-trajectory-capability/

의뢰서 보존:
docs/research/work_orders/C012_MINIMAL_TRAJECTORY_CAPABILITY_KO.md

새 세션은 이전 shell·SSH·cwd·환경변수·Python 연결을 가정하지 않는다.

먼저 확인:
- hostname·사용자·현재 디렉터리
- 저장소 root·remote·branch·HEAD·worktree
- 미커밋 변경
- CLAUDE.md·AGENTS.md 등 실제 지침
- 기존 정상 Python·가중치·실행 가드·산출물 위치

기존 연구 브랜치 단서:
docs/c-research-20261028

기존 SSH 별칭 단서:
dgx-spark

위 이름을 존재하는 값으로 단정하지 말고 실제 설정으로 확인한다.
이미 Spark에서 실행 중이면 SSH를 중첩하지 않는다.

기존 저장소·연구 환경을 우선 사용한다.
다른 작업을 reset·삭제·덮어쓰기하지 않는다.
가중치와 대형 cache를 worktree마다 복제하지 않는다.

동일 C-012가 이미 실행 중이거나 완료됐으면 중복 실행하지 않는다.

읽을 핵심 자료:
- C-011 RESULTS / CONDITIONS / REPRODUCE
- C-009 정상 마스크·cache·초기 상태 복원 코드
- C-006 PointCondition / PointAnchorAdapter / adapted_forward
- 실제 정상 train·generate 경로와 보호 정책
- 상위 HISTORY·ROADMAP

과거 마스크 오류나 시간 cache 원인 탐색을 다시 시작하지 않는다.
확정된 정상 계약과 회귀 검사를 재사용한다.


## 2. 이번에 답할 세 가지 질문

Q1. 평가 과제가 실제로 구별 가능한가?
- 같은 양끝이지만 두 경로의 중간 위치가 충분히 달라야 한다.
- 정답 영상과 VAE 재구성에서 두 경로가 구별돼야 한다.

Q2. 현재 adapter는 작은 과제에라도 제어를 학습하는가?
- 같은 checkpoint·같은 noise에서 point 궤적만 바꿔
  실제 객체의 경로가 바뀌어야 한다.

Q3. 다른 제어 경로는 같은 기능을 보여 주는가?
- 기존 VACE의 동적 윤곽 조건.
- 공개 사전학습 DragAnything 경로 하나.

이 세 질문은 서로 다른 판정이다.
평가기나 자료가 잘못됐는데 adapter 실패라고 하지 않는다.
외부 모델을 실행하지 못했는데 외부 방법도 실패했다고 하지 않는다.


## 3. 최소 과제 — 같은 양끝, 반대 중간 경로

### 3.1 기본 장면

기본 과제는 다음으로 고정한다.

- 해상도416×240
- 33프레임
- 정적 카메라
- 정적 배경
- 분명하게 구별되는 무늬가 있는 공 1개
- 물체의 회전·변형·크기 변화 없음
- 가림·접촉·그림자 변화 없음
- 추가 객체 없음

CPU의 결정적 renderer로 학습 정답을 만든다.
기존 Pillow/NumPy/OpenCV 범위에서 구현한다.
imagegen·새 이미지 모델·웹 이미지 수집은 필요하지 않다.

공은 단순 단색 점이 아니라:
- 명확한 원형 외곽
- 고정된 음영
- 비대칭 표면 무늬
를 가진 하나의 sprite로 만든다.

배경은 공과 구분되는 단순한 정적 표면이며,
카메라 이동을 확인할 수 있는 작은 고정 표식을 둔다.
공과 혼동되는 같은 모양의 무늬를 배경에 반복하지 않는다.

기본 공 지름 d=56px.
렌더링·배경·색·무늬·alpha를 결정하는 seed와 코드를 기록한다.

실사 영상 일반화와 자연스러운 물리 동작을 입증하는 과제가 아니다.
이번에는 명확한 2D 위치 제어만 검증한다.


### 3.2 경로 A/B

화면 좌표는 x가 오른쪽, y가 아래쪽으로 증가한다.

tau = t / 32

x(t) = W * (0.25 + 0.50*tau)

y_A(t) = H * (0.50 - 0.20*sin(pi*tau)^2)
y_B(t) = H * (0.50 + 0.20*sin(pi*tau)^2)

W=416, H=240.

따라서:
- 시작 위치는 둘 다 (104,120)
- 종료 위치는 둘 다 (312,120)
- 가운데에서는 A가 위쪽, B가 아래쪽
- 가운데 두 경로 간 차이는96px

부동소수점 sin 값 때문에 양끝이 달라지지 않도록
t=0,32의 offset은 명시적으로0으로 둔다.

A/B의 첫 프레임과 마지막 프레임은 byte 단위로 같아야 한다.
가능하면 별도로 렌더링한 두 파일을 비교하는 대신,
동일하게 생성한 양끝 프레임을 두 정답에 공유한다.

A/B는 같은 sprite와 배경을 같은 방식으로 평행 이동시킨다.
어느 경로인지 나타내는 문자·색·물체 ID·배경 표식을 추가하지 않는다.


### 3.3 텍스트와 배역

공통 텍스트 예:
“A single patterned ball slides across a plain tabletop.
The camera remains fixed.”

A/B에서 동일한 문자열과 negative prompt를 사용한다.
up/down/upper/lower 같은 경로 정답을 텍스트에 넣지 않는다.

시작·종료 앵커:
renderer의 실제0/32프레임.

점 조건:
공 내부의 같은 위치에9개의 점을 고정한다.
중심점과 중심 주변의8개 점을 사용할 수 있다.

모든 점은:
- 전 프레임 visible=True
- valid=True
- 양끝 anchor_valid=True
- 동일 track ID
- 동일한 endpoint patch
- 동일 motion_available=True
를 사용한다.

A/B 사이에 바뀌는 것은 실제 중간 좌표와 그 파생 이동량뿐이다.
코드의 문자열 label이나 파일명이 신경망 입력에 들어가지 않게 한다.

CoTracker·SAM을 실행하지 않는다.
renderer에서 정답 mask·점·중심을 직접 얻는다.
따라서 TRACK_GIVEN / MASK_GIVEN 과제라고 표시한다.


## 4. 정답 제작과 모델 생성은 엄격히 구분

renderer로 만든 A/B 영상은 다음 용도만 허용한다.

- 학습 target
- source motion의 정답
- 평가기의 검증
- VAE 재구성 진단
- native layout 대조군의 선언된 mask 입력

우리 point 모델과 DragAnything의 추론에는
중간 정답 RGB를 넣지 않는다.

금지:
- source 중간 프레임을 생성 결과로 복사
- 공 sprite를 최종 생성 영상에 다시 붙이기
- 정답 위치로 출력 객체를 warp
- 첫·마지막 출력을 앵커로 덮어쓰기
- 생성 후 영상의 경로를 합성으로 수정
- 정답 latent를 sampler 초기값으로 사용

renderer가 정확한 경로를 그렸다는 것은
영상 생성 모델이 제어를 배웠다는 증거가 아니다.
ORACLE_RENDERER / TRAIN_TARGET로 명확히 구분한다.


## 5. 입력 적합성과 평가기 검증

신규 GPU 실행 전에:
- 과제 정의
- 경로·seed·sprite
- 성공 기준
- 학습 상한
- 출력 checkpoint
- 공개 비교 방법
을 PLAN에 고정하고 commit한다.

먼저 CPU에서:
- A/B 양끝 exact
- 중앙 경로 분리
- 객체가 모든 프레임 안에 있음
- mask와point가 sprite에 맞음
- 배경 고정
을 확인한다.

그다음 기존 VAE로 A/B를 encode→decode한다.
주요 목적은 다음이다.
- 416×240과시간압축에서도 공이 식별되는가?
- 정답 경로 A/B가 재구성에서 구분되는가?
- 평가기가 재구성의 작은 색·경계 변화에도 동작하는가?

이는 생성 sampler가 아니라 RECONSTRUCTION_CONTROL이다.

VAE 재구성에서조차 공을 찾지 못하거나 경로가 구분되지 않으면
학습 실패로 판정하지 않는다.
자료·평가 문제인지 제한된 범위에서 확인한다.

좌표 변환·색 채널·alpha·shape 같은 기계적 오류는 같은 작업에서 수정한다.
여러 시각 디자인을 생성 모델로 시험해 잘 나온 장면을 고르는 것은 금지한다.

과제 자체가 부적합하면 TASK_NOT_VALIDATED로 보고한다.
그 상태에서 2048회 학습을 강행하지 않는다.


## 6. 대조군 1 — 기존 VACE를 이용한 확인

### 6.1 ENDPOINT_BASE

현재 VACE 1.3B의 정상 endpoint 경로를 사용한다.

- 양끝은 실제 공 앵커
- 중간 조건 RGB는(127,127,127)
- G는 양끝0, 중간255의 정상 RGB 마스크
- adapter OFF
- CFG1
- Euler50
- shift5
- 416×240·33frames
- seed20261028

정상 영상1개를 생성한다.

BASE에는 A/B의 궤적이 들어가지 않으므로,
동일 noise의 A용BASE와B용BASE를 중복 생성할 필요가 없다.
같은 결과를 두 목표 경로와 비교한다.

이 기준선이 어느 쪽 경로를 우연히 따르는지는 관측할 수 있지만,
동일 입력 하나로 두 경로를 모두 선택적으로 따를 수는 없다.


### 6.2 NATIVE_LAYOUT_A/B

기존에 실행한 VACE layout 경로를 이용한다.
각 정답 mask로 동적 외곽선을 만들고,
양끝·텍스트·noise·나머지 설정은 유지한다.

A/B 각각1회, 총2개를 생성한다.

공 외곽선을 제공하므로 sparse point adapter보다
더 많은 중간 공간 정보를 받는 대조군이다.

따라서:
- “VACE에 강한 구조 정보를 주면 이 과제를 수행할 수 있는가”를 본다.
- 같은 입력 정보량을 가진 공정한 sparse point 경쟁 모델이라고 하지 않는다.
- 이를 새로운 자체 알고리즘이나 외부 논문 재현으로 부르지 않는다.

이 결과가 실패해도 즉시 외부 방법과 adapter를 모두 실패 처리하지 않는다.
기반 모델의 장면 생성 능력과 조건 활용에 한계가 있을 수 있음을 기록한다.


## 7. 대조군 2 — 공식 DragAnything 한 개만

### 7.1 선정 이유와 범위

공개 구현:
https://github.com/showlab/DragAnything

공식 데모:
demo.py

확인된 데모의 입력:
- 첫 이미지
- 첫 이미지의 객체 mask
- 시간별 객체 trajectory
- DIFT 기반 entity representation
- 공개 사전학습 control model

이번에는 VideoSwap·다른 모델까지 함께 설치하지 않는다.
DragAnything 한 경로만 제한적으로 실행한다.

이것은 같은 backbone의 공정한 성능 순위 비교가 아니다.
이미 발표된 궤적 제어 경로가
이 작은 기능을 실제로 보여 줄 수 있는지 확인하는 기능 대조다.


### 7.2 환경과 가중치

실제 사용할 Git commit과 모델 revision을 고정한다.
README와 실제 demo의 요구 모델·입력을 확인한다.

현재 공식 데모에 등장하는 구성:
- Stable Video Diffusion img2vid
- DragAnything control model
- entity 특징 추출용 모델

정확한 파일·revision·license는 다운로드 전에 확인한다.
기존 로컬에 검증된 파일이 있으면 재사용한다.

신규 모델 다운로드 총상한40GiB.
필요한 형식의 파일만 받고,
FP32/FP16·다른 checkpoint 변형을 중복 다운로드하지 않는다.

가중치 접근 동의·인증이 필요하면 기존 정상 권한만 사용한다.
접근제어를 우회하거나 사용자 비밀정보를 기록하지 않는다.

비상업 연구 허용 범위와 코드·가중치 조건을 각각 확인한다.
이 작업 결과가 상업 배포 가능한 시스템이라고 자동 분류하지 않는다.

별도 격리 환경은 허용한다.
단, 기존 VACE venv·Torch·CUDA·driver를 덮어쓰지 않는다.

기존 Spark 호환 Torch를 활용할 수 있는 경로를 우선한다.
requirements.txt를 검토 없이 실행해 CPU Torch나
호환되지 않는 CUDA 패키지로 바꾸지 않는다.

새 CUDA kernel 빌드·driver 변경·대형 framework 구축은 하지 않는다.
CLI inference wrapper와 경로·입력 연결의 작은 수정은 허용한다.

준비·호환성 해결 범위는 최대90분.
그 범위에서 실행할 수 없으면
COMPARATOR_BLOCKED와 정확한 원인을 남기고 중단한다.

외부 비교가 막혔다고 주력 최소 기능 시험까지 중단하지 않는다.
반대로 설치 실패를 알고리즘 성능 실패라고 하지 않는다.


### 7.3 입력·출력 비교

같은 첫 이미지와 A/B의 정규화 경로를 사용한다.
첫 mask는 renderer의 정답을 사용해도 된다.
추가 SAM 설치는 하지 않는다.

공식 모델이 마지막 앵커를 입력받지 않는다면
없는 기능을 새로 만들어 억지로 맞추지 않는다.
“첫 이미지+궤적”과 “양끝 이미지+궤적”의 차이를 표에 명시한다.

공식 지원 해상도·프레임 수를 우선한다.
현재 데모의576×320·20frames는 참고값이며
실제 고정 commit과checkpoint의 계약을 확인한다.

우리416×240 원본을 변환할 때:
- 종횡비 유지
- 동일한 letterbox/좌표 affine 적용
- A/B의 같은 첫 프레임 사용
- 출력 중심 좌표를 원래 정규화 좌표로 되돌려 평가
한다.

서로 다른 프레임 수는 tau=i/(N-1)의 동일 경로 함수로 입력한다.
출력 영상을 시간 warp해서 정답에 맞추지 않는다.
native FPS와비교용 재생 속도를 구분한다.

A/B에서:
- 같은 model
- 같은 첫 이미지
- 같은 entity 특징
- 같은 sampling 설정
- 같은 초기 noise와가능한 기타난수
를 사용한다.

DIFT 특징 추출의 난수도 고정하고
같은 첫 이미지에서 얻은 특징을 A/B가 공유한다.
다른 trajectory를 넣을 때마다 외형 특징까지 무작위로 바꾸지 않는다.

기본 A/B 영상각1회, 총2개.
결과가 나쁘다고 seed·control strength·prompt를 탐색하지 않는다.

공식 raw 결과를 보존한다.
추가 후합성·경로 보정은 하지 않는다.


## 8. 현재 adapter의 최소 능력 학습

### 8.1 이번 학습은 일반화 실험이 아니다

학습 자료는 위 A/B 두 영상뿐이다.
평가도 우선 그 두 경로에서 수행한다.

TRAIN_PAIR_MEMORIZATION / CAPABILITY_TEST라고 표시한다.
일반화·새 개체 교체·실제 동물 동작 성공을 주장하지 않는다.

이 시험의 목적:
“현재 주입 경로가 필요한 제어 관계를 작은 경우에라도
표현하고 학습할 수 있는가?”


### 8.2 고정할 구조

기존 PointAnchorAdapter를 그대로 사용한다.
- 기존 MLP·projection
- 마지막네 DiT block 주입
- 기존 spatial kernel
- 기존 temporal grouping
- FP32 adapter master
- BF16 backbone
- 같은 VAE·T5·VACE
- 동결 backbone

새 cross-attention·LoRA·encoder를 추가하지 않는다.
residual scale을 키우지 않는다.
좌표 단위를 임의로 증폭하지 않는다.

C-011의 학습된 checkpoint에서 이어 학습하지 않는다.
기존에 보존한 동일 구조의 step000 초기값을 사용한다.
새 optimizer와이번 학습의RNG·cursor를 별도로 만든다.


### 8.3 이번 기능 시험의 학습 설정

기존과 같은:
- AdamW
- lr1e-4
- betas(0.9,0.999)
- weight_decay0.01
- gradient clip1
- batch1
- FM 목표 epsilon−z0
- 객체/배경 면적 정규화 MSE의 합
- 1000-step Wan training grid, shift5
를 사용한다.

다음은 최소 기능 시험을 위한 의도적인 변경이다.
- 자료: 두 개의 명확한 경로 A/B
- NULL dropout:0
- negative-text dropout:0
- 주 생성 CFG:1
- 최대학습량:2048 update

이 변경을 C-011과의 단일 변수 인과비교라고 부르지 않는다.
이번은 모듈에 가장 명확한 학습 과제를 주는 능력 시험이다.

NULL 조건에서 서로 다른 두 정답을 동시에 학습시키지 않는다.
A/B 모두 실제 해당 trajectory를 제공한다.
두 clip은 균형 있게 번갈아 사용하고,
각 update에서 새로운noise·sigma를 사용한다.

중간 clean RGB/latent를추론 조건으로 넣지 않는다.
학습 target으로만 사용한다.

point features는동일 양끝에서독립 인코딩해 얻는다.
A/B의endpoint patch가같은지 확인한다.
같은 endpoint라고 전체 target video에서feature를잘라 쓰지 않는다.

frame별loss mask는renderer의 실제 객체 mask를 사용한다.
마스크를현재 예측에서 얻어 loss를 피하는 경로를 만들지 않는다.

이번에 추가하지 않는 loss:
- endpoint latent patch 일치
- 새 contrastive loss
- 새 trajectory regression head
- perceptual·flow·pose loss
- CFG-aware loss

기존 FM 과제가 이 명확한 조건 분기를 배울 수 있는지 먼저 본다.


## 9. 학습량은 고정 상한 안에서 기능으로 판단한다

checkpoint:
0,256,1024,2048.

각256/1024/2048에서:
- 동일 seed20261028
- 같은 endpoint context
- 같은text·sigma grid·CFG1
- point A 또는point B
로 A/B 영상두개를 생성한다.

한 checkpoint의 두 출력은 반드시 같은 가중치를 사용한다.
A와B 각각을 따로 학습한 모델로 생성하지 않는다.

A/B 출력이 사전 성공 기준을 모두 만족하면:
- 그 checkpoint에서 학습을 중단한다.
- 사전 고정된 두 번째 seed20261029로
  같은 A/B 영상두개를 추가 확인한다.

여러 checkpoint 중예쁜프레임을 섞지 않는다.
“최초 기준 통과 checkpoint” 정책과 모든 이전 결과를 공개한다.

첫seed에서통과했지만두 번째seed에서실패하면:
SEED_SENSITIVE_CAPABILITY로남기고,
더좋은seed를찾지않는다.

2048회에서도조건분기를보이지못하면
그설정의학습을더늘리지않는다.
추가loss·scale·주입위치변경을같은작업안에서시작하지않는다.

이는이구조가수학적으로불가능하다는증명이아니다.
현재명시된능력시험과예산에서계속투자할근거가부족하다는판단이다.

학습벽시계상한90분.
안전하게상한에도달하면마지막checkpoint를보존하고
실제완료update를명시한다.
2048회미완료를2048회실패와같이쓰지않는다.


## 10. 정답 조건이 실제로 사용됐는지 확인

정상 RGB 마스크 계약을 재사용한다.

중간 RGB:
Image.new('RGB', size, (127,127,127))

생성 마스크:
Image.new('RGB', size, (v,v,v))
v=0 at t0/t32, otherwise255

mask64만이아니라실제세채널과전체VACE context를확인한다.

우리point모델의A/B 생성에서동일해야하는것:
- 시작·종료앵커
- VACE context 전체96채널
- text
- initial noisy latent
- 생성sigma/timestep
- checkpoint
- visibility/valid/anchor_valid/motion_available
- endpoint patch·box width

달라야하는것:
- 중간 point 좌표
- 그 좌표에서 계산되는delta/offset/spatial placement

파일명·경로명·A/B label을모델에추가하지않는다.
A/B용별도prompt·noise·checkpoint는금지다.

point 궤적A/B를서로교환하면출력도교환되는지
동일설정의저장영상으로확인한다.
단순히sample label에따라다른출력이만들어지는코드가없는지점검한다.

같은noise에서출력이다르다는사실만으로성공하지않는다.
실제물체의경로가요청한경로와맞아야한다.


## 11. 평가 — 궤적을 입력으로 쓰는 추적기로 점수를 만들지 않는다

### 11.1 사전 평가 위치

tau:
0, 1/8, 2/8, 3/8, 4/8, 5/8, 6/8, 7/8, 1

우리33프레임에서는:
0,4,8,12,16,20,24,28,32.

외부모델은자기프레임의실제tau를기준으로
가장가까운표본을선택하고그시각의정답함수를사용한다.
프레임수가다르다고우리원본index를그대로적용하지않는다.

전체프레임도시트·영상으로확인해
표본사이의소실·중복·순간이동을표시한다.


### 11.2 물체 위치 판독

기본은요청경로를숨긴출력에서물체의실제중심을읽는것이다.

기존OpenCV의template/색·형태기반검출을보조로사용할수있다.
다만:
- 전체화면에서찾는다.
- 정답경로근처만탐색하지않는다.
- 여러후보중정답에가까운것을자동선택하지않는다.
- 객체가없거나두개면missing/duplicate로기록한다.

검출규칙은생성출력을보기전에고정한다.
정답A/B·VAE재구성·객체없는배경·중복객체fixture로검증한다.

자동검출이변형된객체에적합하지않으면
블라인드정적이미지의수동중심주석을주평가로사용할수있다.
그때도입력경로와정답위치를보지않고,
같은규칙을모든모델에적용한다.

같은세션agent의주석은독립human평가가아니다.
신뢰하기어려운중심은억지숫자로채우지않는다.

입력point그자체나주입한heatmap을출력위치로사용하지않는다.
평가영상을정답좌표로warp하지않는다.


### 11.3 성공 기준

다음은이작업의pilot 기준이지공식benchmark 표준이아니다.

A/B각각:
1. 사전9시점중최소8시점에서단일객체가분명히식별된다.
2. missing/duplicate 시점과그부근을제외해좋은점수만계산하지않는다.
   누락수와관측위치오차를별도로필수보고한다.
3. 관측된시점의평균중심오차가0.35d 이하이다.
4. 시작과종료의중심오차가각0.35d 이하이다.
5. 중앙5시점(tau=0.25..0.75)중최소4개에서
   A는기준선위쪽, B는기준선아래쪽에있다.
6. tau0.5의A/B출력중심간격이정답간격의절반이상이다.
7. 올바른경로와매칭한오차가서로바꿔매칭한오차보다명확히작다.
   권장조건: matched error <= 0.5*swapped error.
8. 카메라전체가움직이거나배경을함께옮겨만든가짜제어가아니다.
9. 원래물체가사라지고색조각만경로를따라가는경우가아니다.

d는원래물체지름56px를기준좌표로사용한다.
외부출력은원래좌표로환산해서계산한다.

누락이1개있어도그것이중앙핵심분기시점이면
완전한CAPABILITY_PASS로올리지않는다.
부분제어로분리한다.

배경표식과객체의상대이동을함께본다.
배경전체의translation·크롭·줌은별도실패로표시한다.

공의세부무늬가조금달라도경로제어는평가할수있지만,
동일객체유지판정은따로둔다.
형태·외형붕괴가심하면품질있는제어성공으로보지않는다.


## 12. 수치 진단은 작은 보조 검사로 한정

이번에는C-010 전체진단을다시돌리지않는다.

허용할보조probe:
- 같은A/B 정답
- 같은noise
- sigma1.0/0.95/0.50/0.05
- 해당checkpoint의ON_A/ON_B

특히sigma1에서는:
z_sigma=epsilon으로A/B 입력state가같다.
text·endpoint context도같고point만다르다.

목표velocity 차이는:
u_A-u_B = -(z0_A-z0_B)

동일state에서point를바꿨을때예측차이가
이목표차이와어느정도정렬되는지기록할수있다.

이는조건구별을보는보조검사다.
probe에서정렬돼도실제영상제어성공을대체하지않는다.

sigma1은이번진단에포함되는값이며,
별도의새학습손실이나고sigma 전용학습을추가하지않는다.

정상probe forward 상한32회.
대형gradient dump·다시유한차분·전체checkpoint 순회진단은하지않는다.


## 13. 결과에 따른 방법 단위 결정

다음표의결론중실제근거에맞는것을선택한다.

A. 현재adapter가최소과제에서두경로를따름
- MINIMAL_CAPABILITY_ESTABLISHED
- 2D 강체이동의학습가능성만확인.
- 학습하지않은경로·외형·회전·가림검증은후속작업.
- 실제동물편집성공으로확대하지않음.

B. 현재adapter는실패하고공개방법은성공
- CURRENT_ADAPTER_DEPRIORITIZED
- 기존방법을작동기준으로두고표현·주입·학습차이를비교.
- 현재adapter에보조loss를계속붙이는경로는중단.
- 전체하이브리드프로젝트의실패가아님.

C. 현재adapter는실패하지만native layout은성공
- 생성모델이더강한공간조건으로는과제를수행한근거.
- point→유효한생성조건으로연결하는경로가우선문제.
- VACE 입력쪽표현또는기존학습된control 경로를다음후보로검토.
- sparse/dense 정보량차이를명시.

D. 모두실패하지만renderer/VAE는정상
- 현재제한된설정에서기능증거없음.
- task의생성prior 적합성과비교모델조건을구분.
- “point제어는불가능”이라고확대하지않음.
- 현재adapter의자동확대학습은중단.

E. 외부방법이설치·가중치·호환성문제로미실행
- COMPARATOR_NOT_EVALUATED
- 자체adapter결과와별도로기록.
- 문서검토를기존방법재현성공으로바꾸지않음.

F. 평가기·입력·VAE재구성부터유효하지않음
- TASK_NOT_VALIDATED
- 알고리즘품질판정하지않음.
- 필요한가장작은수정하나만명시.

현재방법의중단은이구조의수학적불가능성선언이아니다.
더이상근거없이투자를반복하지않기위한개발판단이다.


## 14. 실행 예산

정상우리모델sampler:
- endpoint BASE 1
- native layout A/B 2
- adapter checkpoint256/1024/2048의A/B 최대6
- 최초통과checkpoint의두번째seed A/B 최대2
합계최대11.

공개비교sampler:
- DragAnything A/B 2.

정상전체최대13 sampler.
기계적실행복구예비1회를더해hard cap14.
품질재시도는0회.

학습:
- 현재adapter만최대2048 optimizer update
- batch1
- 정상학습forward/backward각최대2048
- 초기값·중간checkpoint·optimizer/RNG 저장
- 학습벽시계상한90분

VAE:
- 공통endpoint 독립encode
- A/B target encode
- endpoint/layout 조건cache·대표live parity
- 입력적합성재구성decode
- 각sampler의정상조건encode/decode
를구분해계산한다.

캐시제작·진단용public VAE encode 상한20회,
진단용decode 최대2회.
sampler 내부의정상encode/decode는별도계수한다.

공개모델의entity 특징추출은공식필요범위에서1회캐시하고공유한다.
SAM·CoTracker·imagegen0회.
14B작업0회.

외부다운로드최대40GiB,
외부환경호환성작업최대90분,
전체작업범위상한6시간.
마지막30분은결과정리·전달에남긴다.

시간상한은실험허용범위이지완료예측이아니다.
현재adapter의학습량을무한히늘리거나외부모델을계속바꾸지않는다.

이미완료된sampler의decode가실패하면latent에서복구한다.
sampler를다시실행하지않는다.
VAE-only 기계복구는전체최대1회.

경로·인자·import·파일포맷오류는같은의뢰안에서고친다.
그때마다새실험번호·별도의뢰를만들지않는다.

실제OOM·안전가드·외부작업충돌은자동우회하지않는다.
기존PSI·headroom·swap·서비스보호기준을변경하지않는다.
다른프로세스를종료하지않는다.


## 15. 문서·전달은 가볍게, 영상과 결정은 앞에

신규GPU작업전에:
- 의뢰서
- task·평가·예산·설정
- 과제코드와input manifest
를commit한다.

기존실험의많은문서를그대로복제하지않는다.
필수문서는다음정도로묶는다.

- PLAN.md
- TASK_MANIFEST.json
- RUNS.json
- METRICS.json
- RESULTS.md
- METHOD_AND_LESSON_KO.md
- REPRODUCE.md
- DELIVERY.json

최종보고의첫화면:
“요청한 A/B 경로”와“실제로생성한 A/B 영상”.
그다음성공여부와방법계속/중단판단.
검사개수·hash·전송기록은뒤에둔다.

검토뷰어:
- 공통시작·종료이미지
- 정답A/B: renderer임을명시
- VAE재구성: 진단임을명시
- endpoint BASE
- native layout A/B
- 현재adapter의checkpoint별A/B
- 외부방법A/B 또는미실행사유
- 실제중심경로와요청경로
- 누락·중복·배경이동·외형손상
- 시간·메모리·학습량

모델명과경로정답을가린정적평가를먼저남길수있다.
같은세션agent 평가를독립human 검수라고하지않는다.

실제연속재생을봤으면주체·속도·범위를기록한다.
그렇지않으면temporal=UNVERIFIED를유지한다.
위치제어의기계적지표와연속지각품질은별도다.

raw·latent·checkpoint는비공개로보존한다.
compact에는보기위한MP4·시트·뷰어·보고서만넣는다.
기존모델가중치·과거full ZIP을중복포장하지않는다.

생성원본을화질낮춰덮어쓰지않는다.
비교용리사이즈·재인코딩은파생물로구분한다.

Spark/Mac의실제/tmp또는승인된전달위치에보존한다.
접근가능한호스트에대해서만실제동일성을확인한다.

검증:
크기·SHA256·CRC·manifest·실제추출·전송동일성.
수행하지않은검증을PASS로기록하지않는다.

공개GitHub에는비민감코드·문서·필요hash만게시한다.
새공개모델의가중치·제한자료·개인경로·token을자동공개하지않는다.
외부라이선스·재배포조건을각각기록한다.

HISTORY/ROADMAP:
- C-012가왜일반영상진단에서최소기능시험으로바뀌었는지
- 무엇이실제로작동했는지
- 어떤방법을계속하고어떤방법을보류하는지
를남긴다.

작업종료시자체프로세스정리·다른작업보존·원격commit일치를확인한다.
추가loss·새모듈·다음학습을자동시작하지않는다.


## 16. 한국어 해설의 핵심

다음질문에실제결과로답한다.

1. 왜같은양끝에서서로다른중간경로를만들었는가?
2. 왜이번에는두영상에과적합해도되는가?
3. 왜그성공이일반화나개체교체성공은아닌가?
4. 같은noise와같은text에서point만바꾼다는것의의미는무엇인가?
5. gradient·출력차이와의도한제어성공은어떻게다른가?
6. native layout과sparse point의입력정보량은어떻게다른가?
7. 첫프레임만받는공개모델과양끝모델의비교한계는무엇인가?
8. 더긴학습을허용한것과무제한튜닝은어떻게다른가?
9. 현재adapter가실패했을때어디까지결론낼수있는가?
10. 실제영상편집목표로돌아가기위한후속조건은무엇인가?

endpoint patch 일치loss를이번에추가하지않은이유도설명한다.
“같은표면점이면시간마다VAE patch가같아야한다”는가정을
검증하지않고학습정답으로쓰지않기위함이다.

이번결과를또다른진단보고서만으로끝내지않는다.
실제기능성공또는명확한방법우선순위변경이최종결론이어야한다.


## 참고

C-011:
https://github.com/hyunlord/make-meme/tree/8b7a4f404f200046bc7b9abc183fd51e916d4fe4/docs/research/experiments/C-011-endpoint-only-trajectory-ablation

DragAnything:
https://github.com/showlab/DragAnything

공식 데모:
https://github.com/showlab/DragAnything/blob/main/demo.py

공식 논문:
https://arxiv.org/abs/2403.07420

VideoSwap 참고:
https://videoswap.github.io/supplementary/videoswap_supp.html

VideoSwap은이번설치·실행대상이아니다.
방법간표현·감독의차이를설명하는참고자료로만사용한다.

외부저장소main과모델배포는실제사용시immutable revision으로고정한다.
문서에공개돼있다는사실을Spark실행성공으로대신하지않는다.


---

## 실행 승인 (사용자 후속 메시지, 요약 없이 핵심 문장 보존)

- C-012 의뢰서 전체를 실제로 진행한다. 의뢰서를 전달한 목적은 실행이다.
- DragAnything 공식 코드와 SVD img2vid·control model·entity 특징 추출 모델 가중치를 신규 다운로드 총상한 40GiB 안에서 확보하는 것을 승인한다. Spark 별도 격리 환경을 승인한다. 기존 VACE 환경의 Torch/CUDA/driver·패키지는 변경하지 않는다. 새 결제·유료 API·접근제어 우회는 승인하지 않는다.
- DragAnything은 비교에 포함한다. 실제 접근 제한이나 호환성 문제로 90분 안에 실행할 수 없을 때만 COMPARATOR_BLOCKED로 남기고, 자체 최소 기능 시험은 계속한다.
- 현재 adapter를 step000에서 최대 2048 update 학습하는 것을 승인한다(학습 90분, 전체 6시간). 기준 통과 시 확인 후 조기 종료한다. 끝까지 통과하지 못하면 추가 loss·scale 변경 없이 확대 개발 중단 근거로 기록한다. 시간은 예산이지 소진 목표가 아니다.
- 8b7a4f4는 연구 기준 커밋이지 강제 reset 지시가 아니다. 의뢰서·PLAN·최소 과제·평가 기준을 신규 실행 전에 commit한다.
- 순서: renderer·평가기 검증 → VAE 재구성 → BASE·native layout → adapter 학습·A/B 생성 → DragAnything 비교 → 최종 판단·전달.
- 승인 범위 안에서는 다시 승인을 요청하며 멈추지 않는다. 경로·인자·import·입력 연결 오류는 같은 작업 안에서 고친다. 안전 가드 중단·외부 작업 충돌·권한 부재·예산 초과 필요성은 우회하지 않고 기록한다. 결과가 나쁘다고 seed·prompt·모델·loss를 탐색하지 않는다.
- 최종 결과 첫머리: "같은 양끝 이미지와 같은 noise에서 궤적 A를 주면 A로, 궤적 B를 주면 B로 움직이는가?" 실제 생성 A/B 영상과 경로 오차를 먼저 제시하고, adapter·native layout·DragAnything의 성공·실패·미실행을 구분한다. renderer 영상이나 VAE 재구성을 제어 성공으로 보고하지 않는다. 후속 실험은 자동 시작하지 않는다.
