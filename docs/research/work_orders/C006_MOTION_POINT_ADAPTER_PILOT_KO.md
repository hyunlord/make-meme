# C-006 통합 작업 의뢰서
# 부위 궤적·가시성·앵커 특징 조건 모듈의 최소 학습과 생성 비교

저장소: hyunlord/make-meme

최근 연구 이력 기준:
372c779103a6d5867757bc0df6c845bd920a5b7f
C-005-vace-backbone-comparison

재사용할 생성 기준:
C-002-sam-layout-conditioning
VACE 1.3B / LAYOUT_MOV

권장 실험 경로:
docs/research/experiments/C-006-motion-point-adapter-pilot/

권장 의뢰서 경로:
docs/research/work_orders/C006_MOTION_POINT_ADAPTER_PILOT_KO.md


## 0. 목적과 이번 작업의 성격

최종 목표:
원본 영상과 소수의 편집 앵커를 이용해
대상 외형·원본 동작·보호 장면을 함께 유지하는
개인 DGX Spark 기반 영상 편집 방법을 연구한다.

C-001~004에서는 앵커와 조건 RGB 표현을 변경했다.
이번에는 실제 생성 특징에 정보를 전달하는 작은 모듈을 학습한다.

핵심 질문:
“같은 양끝 이미지와 동적 윤곽에서,
점의 시간적 동일성·궤적·가시성과 앵커의 대응 특징을
학습 가능한 경로로 전달하면 동작 재현이 개선되는가?”

검증을 두 수준으로 분리한다.

A. 주 검증:
실제 같은 영상의 양끝 이미지로 중간 영상을 생성한다.
imagegen 앵커의 자세 충돌과 개체 교체 문제를 잠시 분리한다.

B. 확장 진단:
학습된 모듈을 기존 편집 앵커에 적용한다.
같은 개체에서 배운 제어가 다른 외형에서도 유지되는지 탐색한다.

A의 성공을 B의 성공으로 해석하지 않는다.
B의 실패를 곧바로 A의 조건 학습 실패로 해석하지 않는다.

이번은 소규모 방법 타당성 pilot이다.
상용 품질·일반화된 객체 교체·최소 앵커·새 논문 기여를
이 단계에서 입증했다고 주장하지 않는다.

완료 목표:
데이터 분리 → 궤적/앵커 특징 준비 → 모듈 연결 →
제한된 실제 학습 → 실제 생성 대조 → 결과 해석.

추적 overlay, CPU 검사, backward 성공, loss 그래프만으로
연구 작업을 완료했다고 하지 않는다.


## 1. 기존 연구·환경을 보존하고 14B 복구는 제외한다

현재 C 트랙 branch/worktree·HEAD·실행 상태부터 확인한다.
특정 커밋으로 강제 reset하거나 다른 작업을 덮어쓰지 않는다.
동일 작업이 이미 실행 중이거나 완료됐다면 중복 실행하지 않는다.

읽을 자료:
- C-005 RESULTS.md와 실행 중단 상태
- C-002 METHOD.md / RESULTS.md / 생성 코드
- C-001 BACKEND_CONTRACT.md / 입력·앵커 계보
- C-003 완료 이후의 실제 정상 보호 실행 경로
- B-018~022의 학습·gradient·저장/재개 관련 기록
- 현재 HISTORY·ROADMAP·C 트랙 연구 목표

B의 학습 코드를 그대로 복사해 고정 tuple 실험을 반복하지 않는다.
재사용할 것은 안전한 저장·동결 검사·gradient 관측 등 필요한 부분이다.

이번에 하지 않는 것:
- C-005 14B 적재·재시도·양자화·가드 수정
- B-034 복구
- 새 영상 backbone 설치
- 새 imagegen 호출
- 기존 앵커 품질 재생성
- 전체 backbone 또는 기존 VACE adapter fine-tuning
- 고해상도 복원·영상 보간·후합성
- 새 운영 framework·launcher·서비스 관리자

14B 다운로드 자료와 과거 실패·UNKNOWN·NOT_CLEAN은 보존한다.
1.3B를 쓰는 이유는 현재 반복 실행 가능한 기반이기 때문이다.
14B보다 품질이 좋다고 선정한 것이 아니다.


## 2. 첫 구현의 범위와 해상도

이번 주 실험은 학습 비용을 제한하기 위해
416×240·33프레임으로 고정한다.

- 학습과 주 평가 모두 같은 공간 해상도
- 프레임 수33
- 실제 원본 순서 유지
- 출력 preview16fps
- 원본 FPS를 모르면 source_fps=null
- 33/16의 파일 길이와32/16의 양끝 표본 간격 구분

기존832×480 C-002 영상은 역사적 참고자료다.
이번416×240 결과와 직접 비교해 방법 개선이라고 주장하지 않는다.

따라서 이번 평가용 BASE 영상도 같은416×240에서 새로 만든다.
해상도·시간·입력의 차이와 모듈 효과가 섞이지 않게 한다.

이 해상도는 최종 서비스 품질의 목표가 아니다.
작은 모듈의 조건 활용과 gradient·비용을 검증하는 첫 설정이다.
세부 발·얼굴을 관측할 수 없는 경우 그 한계를 기록한다.

새 adapter는 좌표와 공간 kernel을 정규화해 표현하되,
그 사실만으로 고해상도 일반화가 보장된다고 하지 않는다.


## 3. 데이터 — 개인 사진을 요구하지 않고 영상 단위로 분리

### 3.1 자료 선정

기존 로컬 공개 영상 중 연구 사용 근거가 확인되는 자료를 우선한다.
DAVIS 등 원본 프레임과 대상 mask를 확보할 수 있는 자료가 후보다.

데이터 사용 조건과 실제 출처를 확인한다.
“공개 URL이 있다”거나 “평가 코드가 오픈소스다”라는 사실을
영상 자체의 모든 이용·재배포 권한으로 해석하지 않는다.

이번은 비상업 연구 범위다.
원본 미디어·학습 cache·생성 결과의 공개 재배포는 별도로 판단한다.

새 자료가 필요하면 공식 출처의 제한된 subset만 허용한다.
미디어 신규 다운로드 상한2GiB.
사용자 개인 강아지 영상이나 cross-ID 정답 영상의 추가 제공을
필수 전제로 삼지 않는다.

사용 근거가 불명확한 항목은 다른 적합한 공개 자료로 대체하되,
대체는 학습·출력 확인 전에 완료하고 이유를 기록한다.

### 3.2 소형 분할

목표:
- train: 서로 다른 원본 영상8개
- validation: 서로 다른 원본 영상2개
- held-out evaluation: 서로 다른 원본 영상2개

각 영상에서 연속33프레임의 한 구간을 고정한다.
명확한 객체 이동과 일부 비강체 움직임이 포함되도록 구성한다.
움직임 유형·가림·크기 변화의 분포를 기록한다.

학습 결과를 본 뒤 더 좋은 test 영상으로 교체하지 않는다.
같은 원본 영상의 인접 crop이나 다른 구간을 다른 split에 넣지 않는다.
파일명이 달라도 같은 원본·같은 장면이면 같은 그룹으로 묶는다.

C에서 이미 반복 사용한 다음 sequence와 파생물은
train/validation에서 제외한다.
- dog
- dog-gooses
- car-roundabout
- car-shadow

기존 dog 편집은 마지막 exploratory probe로만 사용한다.
새로운 held-out 평가라고 부르지 않는다.

데이터 여건상8/2/2를 채우지 못하면
확보된 독립 영상 수를 명시하고 최소4/1/2까지 축소할 수 있다.
그 아래에서는 독립 평가의 한계를 명확히 보고한다.
같은 영상을 여러 파일로 복제해 수를 채우지 않는다.

split과 구간은 최초 학습 전에 DATA_SPLIT.json으로 고정한다.
이는 우리 adapter의 학습에서 보지 않은 영상이라는 뜻이다.
기반 모델의 사전학습 자료와 중복되지 않았다는 보장은 아니다.

### 3.3 입력과 정답 분리

동일 개체 학습에서:
- 양끝 앵커: 실제 source 첫/마지막 프레임
- 정답 Y: 해당 영상의 실제33프레임
- 동작 조건: 대상 mask의 윤곽과 원본에서 추적한 점
- 텍스트: 짧은 객체·장면·움직임 설명

중간 정답 RGB는 다음에만 사용한다.
- 학습용 target latent
- source 궤적 추출
- 평가

중간 RGB 전체나 그 외형 특징을
새 adapter의 입력으로 전달하지 않는다.
점 궤적·가시성과 선언한 윤곽 이외의
중간 영상 정보를 몰래 추가하지 않는다.

평가 시에도 원본에서 동작 조건을 얻는 것은 허용된 입력이다.
그러나 clean target latent를 sampler 시작값이나
feature injection 입력으로 사용하면 안 된다.

GT mask를 사용한다면
MASK_GIVEN / DATASET_MASK_ASSISTED로 명시한다.
이번에 SAM의 자동 선택·분할 성능을 검증했다고 하지 않는다.


## 4. 점 궤적 추출과 부위 ID의 의미

### 4.1 추적기

기존 환경의 CoTracker3 offline을 우선 사용한다.
없으면 공식 코드와 scaled_offline checkpoint 한 개를 확보할 수 있다.

- repository와 weights revision 고정
- 실제 파일 hash·크기·라이선스 기록
- 신규 tracker 가중치 다운로드 상한1GiB
- weights_only 등 지원되는 안전한 로드 경로
- tracker는 eval·추론 전용, 학습하지 않음
- 공식 inference에 필요한 작은 의존성만 격리 설치 가능
- 기존 Torch/CUDA/driver 교체나 kernel 빌드 금지

CoTracker의 점 추적과 가시성 예측을 사용한다.
출력 API에 없는 confidence를 만들어 내지 않는다.
bool visibility를 잘 보정된 확률이라고 부르지 않는다.

현재 공식 비상업 조건 등 실제 적용 조건을 기록한다.
이 의존성을 사용한 연구물을 상업 배포 가능한 전체 시스템으로
자동 분류하지 않는다.

### 4.2 점 선택

객체 첫 프레임의 mask 내부에서 최대16개 점을 고른다.
위치가 한 곳에 몰리지 않도록 고정 grid/코너 후보에서 공간적으로 선택한다.
선택 seed와 규칙을 고정한다.

저품질·가림·texture 부족을 숨기기 위해
결과를 본 뒤 tracking parameter를 반복 탐색하지 않는다.

기본 선택은 자동 surface point다.
“point3=왼쪽 앞발” 같은 전 영상 공통 해부학적 의미를 부여하지 않는다.

각 track ID는 그 영상 안에서 같은 표면 지점을 연결하는 식별자다.
다른 영상의 동일 번호가 같은 신체 부위인 것은 아니다.

코·귀·발 등의 명확한 부위는 소수의 평가용 주석으로 구분할 수 있다.
사람/에이전트가 부여한 의미와 자동 추적을 분리해서 기록한다.

### 4.3 가시성과 품질

보존할 것:
- q[t,k]: 점 좌표
- visible[t,k]: tracker의 실제 가시성 결과
- valid[t,k]: 범위·파일·명백한 추적 오류 검사
- anchor_valid[0/1,k]: 각 앵커에서 특징을 읽을 수 있는지
- 제외 사유

가려진 점을 정답 위치로 선형 보간해 채우지 않는다.
모델이 추정한 가려진 좌표가 있더라도
관측된 위치와 구분하고 조건 사용을 gate한다.

명백한 이탈은 기록하고 제외할 수 있다.
단순히 SAM 경계 밖이라는 이유만으로 모든 점을 오류라고 단정하지 않는다.
분할 오류와 tracking 오류를 구분할 수 없으면 불확실하게 둔다.

source별 tracker 한 pass를 캐시한다.
점·mask·overlay를 만들었다고 생성 조건 연결 완료로 보지 않는다.
tracker와 VAE/DiT를 동시에 상주시키지 않는다.


## 5. 새 모듈: Point–Anchor Adapter의 최소 구조

이번에는 복잡한 graph network나 전체 ControlNet을 새로 만들지 않는다.
명시적인 sparse point 정보를 작은 특징으로 바꿔
기존 DiT의 마지막 일부 block에 주입한다.

### 5.1 앵커 외형 특징

기존 동결 VAE로 첫/마지막 앵커를 각각 독립적으로 encode한다.
full target video를 encode한 결과에서 양끝 특징을 잘라
adapter 입력으로 쓰지 않는다.
시간 receptive field를 통한 중간 정답 누출을 피하기 위함이다.

각 track의 보이는 앵커 좌표 주변에서
고정3×3 latent patch를 bilinear sampling한다.
Wan latent16채널이라면 한 앵커당144차원이다.
실제 encoder shape·normalization을 확인한다.

두 앵커의 patch·유효성 bit를 함께 사용한다.
보이지 않는 앵커의 특징은0과 명시적인 missing flag로 표현한다.
없는 값을 실제 관측처럼 채우지 않는다.

외형 특징은 동결하고 cache한다.
새 CLIP·DINO·별도 image encoder는 이번에 추가하지 않는다.

### 5.2 궤적 표현

pixel-center 규약과 기존 aspect-fit 변환을 따른다.
좌표는 이미지 크기로 정규화한다.

기본 조건:
- 현재 점 위치
- 유효한 인접 시점의 이동량
- 양끝 위치와의 차이
- 영상 시간
- 가시성·valid bit
- 두 앵커 특징과 anchor_valid
- source motion이 제공됐는지 나타내는 bit
- 생성 진행도 sigma 또는 기존 timestep embedding

부위 번호를 외우는 전역 trainable embedding은 사용하지 않는다.
동일 track의 앵커 특징과 궤적을 묶고,
공유 MLP와 합산으로 처리해 점 순서에 불필요하게 의존하지 않게 한다.

### 5.3 공간 전달

영상 token 위치p에 track 특징을 국소적으로 전달한다.

개념식:

w[t,p,k] =
    valid[t,k] * visible[t,k]
    * exp(-0.5 * spatial_distance(p,q[t,k])²)

m[t,p] =
    sum_k w[t,p,k] * F_psi(anchor_features[k], trajectory[t,k], t, sigma)
    / max(1, sum_k w[t,p,k])

분모에 max(1,...)를 두는 이유는
낮은 신뢰도/가시성 gate가 정규화로 상쇄되지 않게 하기 위함이다.

실제 kernel 폭은 객체 bbox 비율과 token grid 단위를 기준으로
학습 전에 한 번 고정한다.
예: x/y 각각 bbox 크기의8%, 최소1 token 폭.
무한한 kernel 대신3표준편차 범위로 자를 수 있다.
선택한 규칙을 모든 조건에 동일 적용한다.

이 kernel은 실제 해부학적 영향 범위를 아는 모델이 아니다.
전파 범위를 정하는 pilot의 설계값이다.
출력을 보고 폭을 탐색하지 않는다.

### 5.4 영상 시간과 latent 시간

33프레임이9개 latent 시간 위치로 압축되는 구조를 확인한다.
point 조건도 이에 맞게 변환한다.

첫 입력 프레임과 이후4프레임 단위의 명목상 그룹을 사용하되,
이 그룹이 VAE의 정확한 receptive field라고 주장하지 않는다.

각 그룹의 유효 point splat과 특징을 집계한다.
가려진 점의0좌표까지 평균해 가짜 위치를 만들지 않는다.
여러 위치를 평균해 공중의 한 점으로 만드는 것보다,
group 안의 spatial support를 유지하는 집계를 우선한다.

실제 T/H/W flatten 순서와 token 좌표를 CPU fixture로 확인한다.
영상 시간과 diffusion/flow step을 혼동하지 않는다.

### 5.5 DiT 연결 위치

기존1.3B DiT의 마지막4개 block 앞에 작은 residual을 주입한다.
실제 block 수가30이면0-based26~29가 기본이다.
config와 실제 실행 loop를 확인하고 고정한다.

h_l' = h_l + W_l m

- 공유 작은 MLP의 폭은192
- block별 projection W_l
- trainable parameter 총량은 목표3M 이하
- 기존 DiT/VACE/T5/VAE는 모두 동결
- backbone LoRA는 이번에 추가하지 않음

W_l의 출력 projection만 zero-init한다.
동시에 앞단 전체나 별도 gate까지0으로 만들어
학습 신호가 영구 차단되지 않게 한다.

초기 첫 update에서 upstream MLP gradient가0일 수 있다.
zero-init projection을 사용한 결과와 실제 graph 단절을 구분한다.
여러 update 후 gradient·parameter 변화로 확인한다.

현재 model_fn의 block 순서·VACE hint 주입 순서를 보존한다.
학습과 추론이 동일한 adapter 연산을 사용한다.
별도 RGB 점 그림을 VACE에 넣어 이 모듈을 대체하지 않는다.

이 설계는 기존 공개 기능을 조합한 pilot이다.
성능·신규성을 사전에 선언하지 않는다.


## 6. BASE / TRACK_ON / TRACK_NULL을 정확히 구분

BASE:
- 새 adapter의 연산을 완전히 bypass.
- 기존 양끝+동적 윤곽 VACE 생성.

TRACK_ON:
- 학습한 adapter 사용.
- 실제 source의 중간 점 궤적·가시성 사용.

TRACK_NULL:
- 같은 학습한 adapter 사용.
- source 중간 궤적과 중간 visibility는 제공하지 않음.
- 양끝 위치를 선형 연결한 단순 경로와
  앵커에서 얻을 수 있는 외형·유효성 정보만 사용.
- source_motion_available=0.

TRACK_NULL은 adapter OFF가 아니다.
양끝 외형 특징과 학습한 모듈 자체의 효과를 남겨 둔 대조군이다.

source 중간 위치·속도·가시성을 NULL에 몰래 전달하지 않는다.
한쪽 앵커만 유효하면 관측된 앵커에 기반한 명시적 fallback을 사용하고,
missing을 기록한다.

학습 중25% 확률로 clip 전체를 TRACK_NULL 조건으로 바꾼다.
평가에서만 처음 보는 NULL 입력을 사용하는 문제를 줄인다.

ON과NULL 모두 기존 동적 윤곽은 동일하게 유지한다.
따라서 NULL이 원본의 모든 동작 정보를 제거한 조건은 아니다.
비교하는 것은 “윤곽 이외의 point trajectory 추가 이득”이다.

BASE와ON의 차이는 학습된 모듈과 추가 정보의 전체 효과다.
ON과NULL의 차이는 같은 모듈에서 실제 중간 궤적의 유용성이다.


## 7. 학습 목표와 정답 누출 방지

실제 설치된 Wan scheduler의
add_noise / training_target / timestep-sigma 관계를 읽고 따른다.

기본 FM 관계:

z_sigma = (1-sigma) * z0 + sigma * epsilon
target_velocity = epsilon - z0

loss =
    mean((predicted_velocity - target_velocity)²)

여기서z0는 학습 정답 영상의 latent다.
raw sigma와 model timestep을 혼동하지 않는다.
샘플러가 sigma를 감소시키는 방향과 학습 target의 부호를 확인한다.

다른 논문의 x0-prediction·epsilon-prediction 식을
이 모델에 임의로 바꿔 적용하지 않는다.

기본 loss는 객체 영역과 배경을 면적으로 정규화해 나눈다.

L =
    mean_on_object(error²)
    + mean_on_background(error²)

두 영역 weight는1:1로 고정한다.
대상 mask를 latent loss grid에 옮기는 규칙을 기록한다.
loss용 mask와 VACE 생성 마스크를 혼동하지 않는다.

초기에는 별도 identity·pose·flow·contact·perceptual loss를 추가하지 않는다.
loss를 여러 개 넣어 무엇이 효과를 냈는지 알 수 없게 만들지 않는다.

학습마다:
- train clip을 균형 있게 순회·shuffle
- 새로운 noise
- 새로운 timestep/sigma
- TRACK_ON/NULL dropout
을 사용한다.

동일한3~4개(noise,timestep,clip) tuple만 반복 최적화하지 않는다.

cache 가능한 것:
- clean target latent
- endpoint-only VAE 특징
- 텍스트 embedding
- 고정 VACE 조건 context
- 마스크·궤적·좌표 변환

cache하면 안 되는 것:
새 noisy latent·sigma에 의존하는 DiT prefix 결과를
다른 update에도 같은 값처럼 재사용하는 것.

평가 sampler에는clean target latent를 전달하지 않는다.
ground-truth video는평가와source motion 추출에만 사용한다.


## 8. Gradient 경로와 실제 학습 설정

### 8.1 동결 범위

DiT·VACE·VAE·T5의 기존 parameter.requires_grad=False.
optimizer에는 새 adapter parameter만 넣는다.

조건 encoder와 adapter 이전의 frozen prefix는
현재 noisy input을 사용해 no_grad로 계산할 수 있다.

단, 첫 adapter 주입 이후의 frozen block·출력 head는
adapter로 gradient를 전달할 수 있도록 autograd를 유지한다.

추론 pipeline.__call__의 no_grad 경로를
그대로 학습 함수로 사용하지 않는다.
실제 model_fn을 공유하는 별도 training entry를 사용한다.

inference_mode로 만든 tensor를 학습 경로에 억지 연결하지 않는다.
필요하면 일반 no_grad 결과를 명시적으로 detach한다.

기존 VACE hints가 새 adapter와 독립인지 실제 계산 순서로 확인한다.
독립인 부분만 no_grad로 처리한다.

마지막4개 block에 필요하면 non-reentrant gradient checkpointing을 적용한다.
현재 SDPA 경로를 유지하고 새 attention kernel을 설치하지 않는다.

### 8.2 기본 학습 설정

- 최대256 optimizer update
- batch size1
- AdamW
- learning rate1e-4
- betas(0.9,0.999)
- weight decay0.01
- gradient norm clip1.0
- BF16 backbone 연산
- adapter master parameter·optimizer state는FP32
- loss 계산FP32
- train resolution416×240·33frames
- 학습 seed와data 순서 seed를사전 고정

학습 timestep은현재 Wan의1000-step training grid를 기준으로 샘플링한다.
이번 주 objective의추가 timestep weight는1로 고정한다.
scheduler의 inference50-step grid만 반복 학습하지 않는다.

text dropout10%를사용해 CFG의negative text branch에도
새 adapter가 완전히 낯선 상태가 되지 않도록 한다.
이 정책과TRACK_NULL dropout은서로 구분한다.

실제 inference의positive/negative text branch에는
같은 point condition을전달한다.
point condition을text CFG와별도 scale로증폭하는 새 기법은이번에 넣지 않는다.

### 8.3 학습 전후의 최소 검사

첫 실제update들을별도 부품 프로젝트로 떼어내지 않는다.
정상 학습 예산에포함해다음을확인한다.

- adapter bypass가기존 model_fn 출력을보존하는가?
- zero-init 연결이base 출력과일치하는가?
- loss가finite인가?
- optimizer에base parameter가없는가?
- 새projection 및이후upstream module에gradient가도달하는가?
- 학습 후새parameter가변하고base는변하지않는가?
- 저장/재로딩 결과가같은probe에서일치하는가?

수치 오차허용은같은실행환경의repeat 오차와dtype을기준으로사전고정한다.
검사를통과시키려고결과를본뒤허용오차를늘리지않는다.
동시에불필요한전체tensor bitwise replay 연구로확대하지않는다.

base 불변성은optimizer구성·tensor version·필요한표본검사를사용한다.
매 update마다수GB 가중치전체hash를읽지않는다.

첫update에서실제peak를측정한다.
작은trainable parameter수만보고학습메모리가충분하다고하지않는다.


## 9. 학습 예산·checkpoint 선택

목표는256update를한설정으로완료하는것이다.
8/2/2개자료와256update는소형pilot규모이며충분한학습량보장이아니다.

저장:
- step0
- step128
- step256 또는마지막완료step

optimizer·RNG·data cursor·설정·adapter state를함께저장한다.
모듈파일만저장하고정확한재개가가능하다고하지않는다.

validation용고정noise/sigma probe는학습전에만든다.
training loss와validation loss를분리해기록한다.
validation loss로test영상이나방법설정을고르지않는다.

이번출력에사용할checkpoint는마지막완료checkpoint로고정한다.
좋은test영상이나최저test loss에맞춰checkpoint를고르지않는다.

학습 active wall 상한2시간30분.
상한에도달하면마지막정상checkpoint를저장하고,
실행안전이유지되면남은생성비교를진행한다.
update가부족했다면UNDER_TRAINED_PILOT로기록한다.
추가1000update를자동실행하지않는다.

기계적코드오류는원인을고치고마지막정상checkpoint에서
전체update예산안으로재개할수있다.
실제OOM·자원가드·외부작업충돌은자동재시도하지않는다.

loss감소만을학습성공의최종판정으로사용하지않는다.


## 10. 주 평가 — 학습하지 않은 두 영상에서 실제 생성

held-out 두영상각각세조건을생성한다.

1. BASE
2. TRACK_ON
3. TRACK_NULL

정상신규영상6개.

모든조건에서:
- 같은실제양끝이미지
- 같은동적윤곽
- 같은text/negative
- 같은노이즈tensor
- 같은416×240·33frames
- Euler50 / CFG5 / sigma_shift5
- BF16 / SDPA / tiled VAE
- 같은기존마스크시간압축
를사용한다.

변경한rescale에맞게새BASE를만들고,
과거832×480출력을그대로대조군으로대신하지않는다.

동일case의실제초기noise hash를비교한다.
학습RNG와inference RNG를분리한다.

자기재현을검증한다고중간정답RGB·latent를sampler에넣지않는다.
실제first/last anchor와선언한구조조건만사용한다.

모든조건을실행전에고정하고,
BASE가나쁘거나ON이좋아보인다는이유로seed를바꾸지않는다.
같은사례의비교조건을가능한한완결한다.

정상decoder출력의첫/마지막프레임을앵커로덮어쓰지않는다.
후합성·color correction·SR·보간을하지않는다.


## 11. 편집 앵커 확장 진단 — 기존 개 사례 하나

주 평가와별도로기존C-002 개편집을한사례사용한다.
기존시작·종료imagegen앵커를그대로416×240에정해진방식으로변환한다.

C-004 교정종료앵커나C-003 구조선은섞지않는다.
새imagegen호출0회다.

원본의코·귀부근·보이는발등소수의명확한지점에대해
원본양끝과편집앵커의대응위치를제한적으로확인한다.
목표3~6개,최대16개.
사용자가새사진을주어야만진행되는조건은만들지않는다.

원본좌표를target의동일화면좌표로무조건복사하지않는다.
초기기하정렬은고정된양끝기반근사로제한한다.

예시:
q_target(t) =
 (1-tau) * [q_target(0) + B0*(q_source(t)-q_source(0))]
 + tau * [q_target(T) + B1*(q_source(t)-q_source(T))]

B0/B1은원본/target bbox의x/y크기비율에따른diagonal변환이다.
tau는실제클립내정규화시점이다.

이는양끝에맞춘2D근사이지정확한관절retargeting이아니다.
자기재현에서는동일양끝과B=I로원궤적이복원되는지CPU검사한다.

양끝에서부위를확인할수없는점은임의로정답을채우지않는다.
cross-ID진단에는검토가능한점만사용한다.
모든점의대응이불명확하면CROSS_ID_CORRESPONDENCE_UNAVAILABLE로남기고,
주평가6영상은계속보존한다.

cross-ID에서도같은해상도로세조건을생성한다.
- BASE
- TRACK_ON
- TRACK_NULL

추가정상영상최대3개.
C-002의고해상도영상은역사참조패널에만둔다.

종료앵커충돌과수동대응사용을명시한다.
같은개체학습에서다른외형으로의적용은탐색적전이진단이다.
성공하더라도일반적개체교체를입증한것으로확대하지않는다.


## 12. 무엇을 평가하고 어떻게 성공을 판정할 것인가

### 12.1 필수 품질축

- 전체위치·접근·방향·크기
- 보이는부위의시점별위치와움직임순서
- 외형·무늬·체형유지
- 가림후재등장
- 보호배경·다른객체
- 형태붕괴·추가부위·배경파편
- 실제연속품질
- 추가메모리·시간·주석비용

같은인덱스의전체33프레임과
0/4/8/12/16/20/24/28/32를비교한다.
시간축재정렬이나warp로더맞아보이게하지않는다.

주평가의동일개체영상에는실제정답영상이있다.
그러나전체RGB오차가낮다는것만으로동작성공을판정하지않는다.
배경면적이지배할수있기때문이다.

### 12.2 궤적평가

source에서명확히보이는표면점·사건을평가전에고정한다.
가능한범위에서생성영상의대응위치를확인하고,
객체크기로정규화한위치오차·방향·이벤트순서를기록한다.

source만보고평가위치와visibility를정한다.
ON에서잘보이는점만골라평가하지않는다.
출력에해당부위가없으면silent drop하지말고missing으로센다.

input을만든tracker를유일한정답평가기준으로사용하지않는다.
추적기로보조수치를내더라도원본/출력의실제정적검토와구분한다.

정확한점주석이불가능하면임의숫자를만들지않는다.
MOTION_MEASUREMENT_LIMITED와구체적관측범위를명시한다.
추적모델이높은confidence를출력했다고정답으로승격하지않는다.

화면좌우와해부학적좌우를구분한다.
가려진관절·발접촉을관측정답으로채우지않는다.

### 12.3 대조군해석

BASE vs ON:
학습모듈과point조건을추가한전체효과.

BASE vs NULL:
실제중간궤적없이앵커특징과학습모듈을추가한효과.

ON vs NULL:
같은학습모듈에서실제point motion을제공한추가효과.

ON/NULL출력이다르다는사실만으로제어성공이라고하지않는다.
ON이정답움직임에더가깝고다른품질축을과도하게해치지않아야한다.

한개영상·몇프레임의우연한개선으로일반화결론을내리지않는다.
프레임33장을독립표본33개로세지않는다.

실제재생을지각검수한주체·속도·범위를기록한다.
정적시트나ffmpeg decode만확인했다면temporal=UNVERIFIED다.
같은세션의에이전트를독립human평가라고하지않는다.

### 12.4 최종판정

학습/실행판정:
GRADIENT_CONNECTED / TRAIN_COMPLETE / CHECKPOINT_RELOAD
와영상품질판정을분리한다.

품질판정예시:
- OBSERVED_TRAJECTORY_GAIN:
  held-out영상에서ON이BASE/NULL보다동작을더잘따르는근거.
- CONDITION_SENSITIVE_ONLY:
  조건변화에는반응하지만정확도이득미입증.
- ANCHOR_FEATURE_GAIN_ONLY:
  NULL도비슷하게개선되어중간궤적의추가이득미입증.
- TRADE_OFF:
  동작일부개선과외형·장면회귀가동반.
- NO_ESTABLISHED_GAIN:
  추가이득미입증.
- INCONCLUSIVE:
  부족한학습·자료·측정·실행한계로판단어려움.

동일개체성공과cross-ID성공은따로보고한다.
negative결과로끝나도유효한pilot결과다.
loss가감소했다는이유만으로성공으로올리지않는다.


## 13. 실행·비용 상한과 오류 처리

신규정상작업:
- 데이터와point추출·cache
- 실제adapter학습최대256update
- held-out영상6개
- cross-ID진단최대3개
- 정상full sampler최대9회
- 각50step·기존CFG경로의100 model_fn call

full sampler는기계적복구용예비1회를포함해최대10회.
품질재시도·seed탐색·prompt튜닝0회.

decode실패시저장된final latent에서복구한다.
이미완료된sampler를다시실행하지않는다.
VAE-only기계복구는전체최대1회.

학습의비학습validation forward·gradient진단·실제update와
영상sampler forward를별도로센다.
“heavy한번”으로모든계산량을합쳐숨기지않는다.

최대총작업범위8시간.
마지막45분은평가·문서·전달에남긴다.
학습시간상한으로update가부족해도
정상checkpoint의영상비교를우선확보한다.

이시간은승인범위이지작업성능예측이나완료보장이아니다.

다운로드:
- 영상subset≤2GiB
- CoTracker weights≤1GiB
- 기존VACE/T5/VAE 재다운로드0
- 새imagegen0
- 새14B작업0

CPU경로·인자·import오류는같은의뢰안에서수정한다.
새단계번호와관리체계를계속만들지않는다.

기존C-003/C-004의정상보호경로를재사용한다.
메모리·PSI·worker swap·외부GPU·서비스정책을완화하지않는다.
새가드정책·swapoff·재부팅·타프로세스종료금지.

모든대형모델은가능한한단계별순차사용한다.
tracker/T5/VAE의완료자료를cache한뒤불필요한상주를해제한다.

실제안전중단이발생하면미완료단계를정확하게남긴다.
작업을완료하기위해조용히threshold나해상도·model을바꾸지않는다.


## 14. 수학·학습·코드 해설

한국어 LESSON_KO.md는실제구현과결과에연결한다.

필수내용:

1. 기존RGB구조선조건과명시적인track조건의차이.
2. track ID와해부학적부위ID의차이.
3. 가시성과대응정확도·신뢰도의차이.
4. endpoint-only VAE특징을사용하는이유와시간누출위험.
5. spatial kernel과공유point MLP의실제tensor shape.
6. 영상시간t와생성진행도sigma의차이.
7. 33프레임→9시간latent→DiT token배치.
8. z_sigma와epsilon-z0의FM학습목표.
9. 동결backbone에서도adapter이후의gradient가필요한이유.
10. zero-init의첫update와이후gradient전달.
11. BASE/ON/NULL이각각분리하는효과.
12. 자기재현과개체교체전이의차이.
13. 적은trainable parameter와낮은전체학습비용이같지않은이유.
14. 이번자료·해상도·학습량에서결론낼수없는것.

직관 → 수식 → 실제함수·shape →
gradient/출력관측 → 반례·한계순서로작성한다.

단순히loss그래프와구조도만붙이지않고,
실제생성영상에서수식의가설이어디까지맞았는지설명한다.


## 15. 산출물·GitHub·종료

실행전:
- 의뢰서보존
- DATA_SPLIT와사용근거
- MODEL/MODULE설계
- 학습·평가·예산계약
- 정확한base revision/기존환경
- 조건과평가선정기준
를고정하고commit한다.

반드시필요한기록:
- PLAN.md
- DATA_SPLIT.json
- METHOD.md
- TRAIN_CONFIG.json
- RESULTS.md
- COSTS.json
- REPRODUCE.md
- LESSON_KO.md
- DELIVERY.json

동일내용을다수문서에반복하지않는다.
HISTORY/ROADMAP에는새모듈을만든이유와
실제영상결과·미해결문제를연결한다.

보존할것:
- adapter0/중간/최종checkpoint
- optimizer·RNG·cursor
- data/track/endpoint feature cache계보
- loss와실제gradient관측
- 새영상final latent·raw·PNG·MP4
- 같은입력의BASE/ON/NULL비교

검토뷰어:
- train/validation/test구분
- source와실제양끝앵커
- point궤적·가시성
- BASE/ON/NULL의같은인덱스·같은속도비교
- 전체프레임과고정시트
- cross-ID진단은별도패널
- 품질판정과비용

compact에는보기위한영상·시트·보고서만넣는다.
학습cache·가중치·optimizer·대형raw는별도full/로컬보존으로분리한다.
기존자료와14B가중치를반복포장하지않는다.

공개Git에는비민감코드·문서·hash만게시한다.
원본미디어·개인경로·token·PID·가중치·latent를자동공개하지않는다.
데이터와CoTracker의라이선스범위를각각보존한다.

Spark/Mac의실제/tmp에검토물을보존하고
CRC·manifest·실제추출·전송동일성을확인한다.
실제로수행하지않은검증은PASS로쓰지않는다.

최종보고순서:
1. 실제생성영상
2. ON이BASE/NULL보다동작을잘따랐는가
3. 외형·장면의회귀가있는가
4. 동일개체와편집앵커의결과가어떻게다른가
5. 학습량·자원·수동작업비용
6. 다음가설하나

이번pilot후종료한다.
14B복구·추가학습·새모듈·다른seed·고해상도실험을자동시작하지않는다.


## 참고 구현

기존 연구:
https://github.com/hyunlord/make-meme

기존 DiffSynth model_fn 및 block/VACE hint 경로:
https://github.com/modelscope/DiffSynth-Studio/blob/f39d731a3e318d25b725eb3389cfddb184619842/diffsynth/pipelines/wan_video.py

기존 Flow Matching scheduler:
https://github.com/modelscope/DiffSynth-Studio/blob/f39d731a3e318d25b725eb3389cfddb184619842/diffsynth/diffusion/flow_match.py

CoTracker 공식 코드:
https://github.com/facebookresearch/co-tracker

PyTorch autograd:
https://docs.pytorch.org/docs/stable/notes/autograd.html

참고 링크의main/stable은설치버전의고정근거가아니다.
실제사용한revision·파일hash·API를기록하고,
기존환경을문서의최신버전으로자동업그레이드하지않는다.