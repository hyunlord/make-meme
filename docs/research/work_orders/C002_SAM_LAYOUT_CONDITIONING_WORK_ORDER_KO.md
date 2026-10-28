# C-002 통합 작업 의뢰서
# 기존 양끝 앵커 + SAM 동적/정적 윤곽 조건의 영상 생성 비교

저장소: hyunlord/make-meme

C-001 기준 커밋:
5ba0cdbe4a11bb35ae77ce638acbbcc501e90da2

권장 문서 경로:
docs/research/work_orders/C002_SAM_LAYOUT_CONDITIONING_WORK_ORDER_KO.md

실험 경로:
docs/research/experiments/C-002-sam-layout-conditioning/


## 0. 이번 작업의 목표와 위치

최종 연구 목표는 다음과 같다.

원본 영상 + 편집 지시 + 선택적 대상 참조 이미지
→ 소수의 편집 앵커 생성
→ 원본 객체·동작과 편집 객체의 연결
→ 로컬 영상 생성
→ 원본 동작·대상 외형·보호 장면을 함께 유지하는 영상 편집

C-001에서는 실제 native imagegen 앵커4장과 영상2개를 확보했다.
그러나 영상 모델은 원본 중간 프레임이나 SAM의 시간별 구조를
생성 조건으로 사용하지 않았다.

이번 질문은 다음 하나다.

“같은 양끝 앵커와 같은 영상 모델에서,
원본 객체의 시간별 윤곽을 중간 조건으로 전달하면,
양끝 조건만 사용하는 경우나 정적인 윤곽을 반복하는 경우보다
원본의 움직임 진행을 더 잘 따르는가?”

이번은 SAM 분석 결과를 실제 생성 입력으로 연결하는 첫 기준선이다.
새로운 객체 대응 신경망이나 논문용 최종 알고리즘을 만드는 단계는 아니다.

마스크 윤곽에는 위치·크기·실루엣과 원본 체형이 함께 들어 있다.
순수 동작만 전달한다고 가정하지 않는다.
정확한 관절·접촉·새 체형으로의 동작 전이가 해결됐다고도 가정하지 않는다.

A/B 기록과 환경을 보존한다.
B-034 복구, 새로운 서비스 관리, 새로운 실행기 개발은 하지 않는다.


## 1. 착수 시 확인할 것

최신 원격·로컬 상태와 C-001의 실제 branch/worktree를 확인한다.
C-001이 사용한 C 트랙 작업 경로를 이어서 사용한다.

과거 B 연구 브랜치명을 그대로 가정해 checkout하거나,
기준 커밋으로 강제 reset하지 않는다.
기존 변경과 다른 작업을 덮어쓰지 않는다.

C-002가 이미 실행 중이거나 완료됐으면 중복 실행하지 않는다.

다음 C-001 문서를 읽는다.

- RESULTS.md
- BACKEND_CONTRACT.md
- SAM_ANALYSIS.md
- INPUTS.json
- ANCHORS.json
- NUMERICS.json
- COSTS.json
- code/video_generate.py
- 기존 실제 실행 명령과 보호 실행 경로

연구 상위 문서의 실제 위치를 확인해 함께 읽는다.
CHARTER, HISTORY, ROADMAP 및 C 트랙 방향 문서가 해당한다.

기존 파일·모델·마스크가 있는지 필요한 범위에서 확인하되,
완료된 전체 가중치·커널·서비스 감사를 반복하지 않는다.


## 2. 역할 분담과 변경 범위

Codex Astra:
- 기존 자료와 코드를 읽고 입력 조건 변환을 구현한다.
- 실험 조건·수식·평가 기준을 고정한다.
- Spark 작업을 실행하고 실제 결과를 검토한다.
- 한국어 해설·재현·GitHub 이력을 작성한다.

DGX Spark:
- 기존 환경과 VACE checkpoint를 사용한다.
- 정해진 MOV/STILL 영상4개를 생성한다.
- 실제 모델 입력·실행량·출력·자원을 기록한다.

이번에 새로 하지 않는 것:
- imagegen 호출 및 앵커 수정
- 원본·앵커의 SAM 재분석
- 다른 이미지/영상 모델 설치
- 새 checkpoint·패키지 다운로드
- 모델 학습·LoRA·attention gate
- point tracker·flow·depth·pose 모델 추가
- 업스케일링·보간·후합성·얼굴 복원
- 새 공개 사례 또는 개인 사진 확보

조건 RGB의 중간 프레임만 바꾼다.
영상 backbone·가중치·샘플러·앵커·caption·생성 마스크는 유지한다.


## 3. 고정 입력과 기존 대조군

C-001의 두 사례를 그대로 사용한다.

A. case_rigid
- source: car-roundabout의 기존33프레임
- target reference: 기존 car-shadow 참조
- 시작·종료 앵커: C-001의 실제 생성 파일

B. case_nonrigid
- source: dog의 기존33프레임
- target reference: 기존 dog-gooses 참조
- 시작·종료 앵커: C-001의 실제 생성 파일

정확한 frame ID·파일·crop/resize·hash는 INPUTS.json과 실제 자료를 따른다.
다른 인덱스나 더 좋은 사진으로 교체하지 않는다.

공통 출력/입력 좌표:
- width832 × height480
- 33프레임
- 앵커 위치0/32
- source_fps=null
- preview_fps=16
- timebase_assumed=true

33/16초의 파일 지속시간과
32/16초의 양끝 표본 간격을 구분한다.
원본의 실제 초 단위 타이밍을 확인했다고 하지 않는다.

기존 C-001 생성2개를 ENDPOINT 대조군으로 재사용한다.
이를 다시 생성하지 않는다.

기존 앵커의 원본 대비 자세·발 위치·배경 차이를 보존한다.
앵커가 완벽한 편집 정답이라는 전제로 평가하지 않는다.


## 4. 실험 구성 — 2사례 × 2신규 조건

각 사례에서 다음 세 결과를 비교한다.

조건 ENDPOINT:
- C-001 기존 결과.
- 양끝은 기존 편집 앵커.
- 중간31장은 RGB127의 회색 빈 프레임.

조건 LAYOUT_MOV:
- 양끝은 동일한 편집 앵커.
- 중간31장은 해당 source 시점의 SAM 윤곽 안내.

조건 LAYOUT_STILL:
- 양끝은 동일한 편집 앵커.
- 중간31장은 source 첫 프레임의 SAM 윤곽을 반복.

신규 생성은 다음 네 셀이다.

1. case_rigid / LAYOUT_MOV
2. case_rigid / LAYOUT_STILL
3. case_nonrigid / LAYOUT_MOV
4. case_nonrigid / LAYOUT_STILL

결과를 보기 전에 실행 순서와 설정을 고정한다.
첫 조건의 품질이 나쁘다는 이유로 짝 대조군을 생략하지 않는다.
실제 입력 오류·자원 위험은 별도 중단 사유다.

STILL은 생성 모델이 만드는 영상이다.
정지 사진을 반복한 출력이나 동작 조건을 완전히 끈 분기가 아니다.

MOV/STILL 비교에는 윤곽의 시간 변화뿐 아니라
종료 앵커와의 구조적 충돌 정도 차이도 포함될 수 있다.
이를 완벽한 “시간 정보 하나만의 순수 인과효과”라고 부르지 않는다.


## 5. SAM 마스크를 윤곽 안내로 변환

기존 SAM 분석에서 선택된 edited_subject의 visible mask를 사용한다.

- source 각33장의 선택 track을 그대로 사용한다.
- 다른 차량·관목·배경 객체를 합치지 않는다.
- GT로 마스크를 교체하지 않는다.
- 이미 수행한 SAM을 다시 호출하지 않는다.
- 기존 마스크의 털·바퀴·얇은 경계 오차는 한계로 남긴다.

기존 마스크 좌표와 source/anchor 좌표의 대응을 확인한다.
이미832×480이면 재변환하지 않는다.
다른 좌표계로 저장됐다면 기존 C-001의 정확한 변환만 적용한다.
라벨 마스크 resize는 nearest 방식으로 처리하고 기록한다.

윤곽 렌더링은 공식 VACE의 의미와 맞춘다.

참조 코드:
ali-vilab/VACE
commit 48eb44f1c4be87cc65a98bff985a26976841e9f3
vace/annotators/layout.py

고정 규칙:
- 배경: RGB(255,255,255)
- 선: RGB(0,0,0)
- 외곽선: RETR_EXTERNAL
- contour approximation: CHAIN_APPROX_SIMPLE
- 선 두께:3px
- 객체 내부를 검정으로 채우지 않는다.
- mask augmentation, bbox 대체, 팽창·침식·시간 smoothing은 하지 않는다.
- 글자·객체 번호·색상 범례를 모델 입력에 그리지 않는다.

기존 OpenCV/CPU 도구로 같은 렌더링을 수행한다.
이미 있는 SAM 마스크를 사용하므로
LayoutTrackAnnotator의 분할·검출 전체 파이프라인을 다시 실행하지 않는다.

윤곽 이미지는 uint8 RGB로 확정해 저장한다.
float64 canvas 같은 중간 dtype을 그대로 넘기지 않는다.

원본 위에 윤곽을 그린 overlay는 검토 자료로만 사용한다.
원본 RGB overlay를 생성 조건으로 넘기지 않는다.
그래야 원본의 털색·차체 RGB가 추가로 유입되지 않는다.

입력 오류로 파일을 잘못 읽었으면 같은 작업 안에서 수정한다.
실제 마스크가 비어 있거나 잘못된 객체를 가리키면 사실을 기록하고,
다른 객체나 새 segmentation으로 조용히 바꾸지 않는다.


## 6. 세 종류의 마스크·이미지를 구분한다

다음 이름을 분리한다.

S_t:
SAM의 원본 객체 영역. 윤곽을 그리는 재료.

L_t:
S_t에서 렌더링한 RGB layout 이미지.

G_t:
VACE가 조건을 처리하는 데 사용하는 생성 여부 마스크.

S_t를 G_t로 사용하지 않는다.
윤곽 이미지에서 검은 객체·흰 배경이라는 사실을
VACE 생성/보존 마스크 의미로 해석하지 않는다.

기존 VACE 생성 마스크는 그대로 유지한다.

- t=0,32: 프레임 전체0
- t=1..31: 프레임 전체255
- 모델 내부에서는 기존 normalization으로0/1 처리

모델 입력 X는 다음과 같다.

ENDPOINT:
X_0=A_0, X_32=A_32
X_t=RGB127, 1≤t≤31

LAYOUT_MOV:
X_0=A_0, X_32=A_32
X_t=L_t, 1≤t≤31

LAYOUT_STILL:
X_0=A_0, X_32=A_32
X_t=L_0, 1≤t≤31

vace_reference_image=None은 유지한다.
앵커를 별도 reference 목록으로 옮기지 않는다.

조건은 PNG/인메모리 RGB로 전달한다.
검토용 조건 MP4를 다시 읽어 모델 입력으로 사용하지 않는다.


## 7. 실제 VACE 연결 — RGB 조건만 변경

기존 C-001 video_generate.py와 실행 경로를 재사용한다.

기존 condition 함수에 명시적인 condition_mode를 추가하는 정도의
작은 변경으로 구현한다.

권장 모드:
- endpoint
- layout_mov
- layout_still

endpoint 모드에서는 기존 회색 중간 입력 검사를 그대로 유지한다.
모든 모드의 검사를 지우거나 느슨하게 해서 통과시키지 않는다.
MOV/STILL에는 각각의 기대 RGB 검사를 추가한다.

기존 pretrained VACE의 조건 인코딩을 그대로 사용한다.
개념적으로 normalized 입력 X와 mask G에 대해:

X_inactive = (1-G) * X
X_reactive = G * X

를 별도로 VAE 인코딩하고 마스크 표현과 결합한다.

이번 변경의 의도:
- 양끝 앵커의 inactive 조건은 유지.
- 중간 reactive 조건이 빈 RGB에서 layout으로 변경.
- 생성 마스크 자체는 유지.

실제 설치된 DiffSynth의 텐서 축·normalization·branch 이름을 확인해
이 설명과 실행 경로가 일치하는지 짧게 기록한다.
가이드 이름만 보고 조건이 전달됐다고 선언하지 않는다.

공식 layout 표현을 활용하지만,
“양끝 편집 RGB + 중간 source 윤곽”이라는 조합의 품질은 미검증이다.
이 조합이 공식적으로 성능 보장된 task라고 보고하지 않는다.

학습하지 않은 새로운 control branch나 임의의 추가 tensor 채널을
checkpoint에 연결하지 않는다.


## 8. 고정 모델·샘플링 설정과 알려진 한계

C-001의 실제 설정을 유지한다.

- Wan-AI/Wan2.1-VACE-1.3B
- 모델 revision:
  574e6a744642ce3bee319afc31496b88bde8aac4
- DiffSynth 기록 revision:
  f39d731a3e318d25b725eb3389cfddb184619842
- 실제 설치 파일 해시는 C-001 freeze를 기준으로 확인
- BF16
- SDPA
- tiled VAE
- adapter OFF
- FlowMatchScheduler("Wan")의 기존 Euler 경로
- num_inference_steps=50
- CFG=5
- sigma_shift=5
- seed=20261028
- rand_device=cpu
- 832×480,33frames
- 각 사례의 기존 prompt와 negative_prompt 그대로

공식 VACE runner의 UniPC/shift16 설정으로 바꾸지 않는다.
SCAIL40step/shift3도 가져오지 않는다.

VACE conditioning scale 등 명시하지 않은 값도
현재 C-001의 실제 적용값을 확인·기록하고 유지한다.
품질이 나쁘다고 임의 조절하지 않는다.

알려진33→9 시간 마스크 압축 한계를 유지한다.
nearest-exact에서 양끝0 mask가 빠지는 현상과
RGB inactive 조건이 남는 사실을 구분한다.

이번에 다음을 하지 않는다.
- 시간 mask 압축 방식 수정
- endpoint latent clamp
- 양끝 이미지 출력 덮어쓰기
- 첫/마지막 몇 프레임 반복으로 조건 보강

마스크 압축 수정 효과와 layout 효과가 섞이지 않게 한다.


## 9. 최소 사전검사와 실제 입력 관측

기존 보호 실행 경로와 절대경로 계약을 재사용한다.
새 launcher/supervisor/systemd 관리 구조를 만들지 않는다.

생성 전에 필요한 검사만 한다.

1. 두 사례의33 source mask와 네 앵커가 올바른 좌표·순서인가?
2. 두 새 조건의0/32 RGB가 기존 앵커와 픽셀 단위로 같은가?
3. MOV의 중간 RGB가 각 시점 layout과 같은가?
4. STILL의 중간31장이 같은 L_0인가?
5. 생성 마스크33장과 실제 압축 마스크가 두 조건에서 같은가?
6. prompt·negative·model·scheduler·shape가 고정됐는가?
7. mask·조건 RGB의 dtype/range/channel이 올바른가?

한 번에 큰 이미지 tensor를 반복 dump하지 않는다.
조건 이미지, shape, 범위, hash와 작은 요약으로 충분하다.

실제 inference에서는 기존 첫 model_fn 호출 직전에
최초 noisy latent와 실제 VACE condition의
shape·dtype·해시·유한값을 필요한 범위에서 기록한다.

관측용 추가 DiT forward는 하지 않는다.
원래 함수의 tensor·출력·RNG를 변경하지 않는다.

MOV/STILL의 초기 noise는 동일해야 한다.
같은 seed라는 말만 하지 말고 새 두 실행의 실제 noise hash를 비교한다.

C-001에 초기 noise 자체의 검증 자료가 없다면
C-001과는 “같은 seed·생성 경로”라고만 기록한다.
과거 bitwise 동일성을 확인한 것처럼 쓰지 않는다.
이를 위해 ENDPOINT를 다시 생성하지 않는다.

새 조건 텐서가 실제 모델까지 전달됐는지도 확인한다.
shape/hash 차이가 있다는 사실은 조건 활용이나 품질 개선의 증거가 아니다.


## 10. 실행 예산과 기계적 오류 처리

정상 신규 영상은4개다.

- 각50 scheduler step
- 각100 model_fn call 예상
- final latent·raw·33프레임·MP4 보존
- 기존 ENDPOINT2개는 재사용

새 imagegen0회, 학습0회, 입력 SAM 재추론0회.
새 모델/패키지/데이터 다운로드0회.

기계적 실패 복구는 다음처럼 제한한다.

- 모델을 올리기 전의 경로·인자·import·dtype 오류:
  같은 의뢰 안에서 수정하고 다시 CPU 검사할 수 있다.
  이런 오류마다 새 실험 번호나 별도 승인 문서를 만들지 않는다.

- GPU heavy 실행:
  기본4회에 기계적 복구용 예비1회를 포함해 총최대5회.
  모델 로딩 중 실패한 heavy 시작도 장부에 포함한다.

- 품질이 나빠서 재생성:
  0회. seed·prompt·두께·모델을 바꿔 다시 만들지 않는다.

- final latent가 이미 저장된 후 decode/encoding 실패:
  sampler를 다시 돌리지 않는다.
  저장된 latent로 VAE-only 복구를 전체최대1회 허용한다.
  CPU MP4 포장 오류는 기존 raw/PNG로 수정한다.

- OOM·외부 GPU 충돌·메모리 압박·가드 위반:
  자동 재시도하거나 기준을 완화하지 않는다.

정상 완료 셀을 중복 생성하지 않는다.
실패·부분 완료·예비 사용량을 모두 기록한다.

기존 C-001에서 실제 성공한 환경과 보호 경로를 유지한다.
SAM·서비스·가드 전체 회귀검사를 새 프로젝트처럼 반복하지 않는다.

전체 작업 상한3시간, 마지막20분은 기록·전달에 남긴다.
CPU 조건 준비·관련 검사 목표상한40분.
완벽한 부가 지표 때문에 실제 영상 생성을 뒤로 미루지 않는다.

다른 서비스·프로세스를 종료하지 않는다.
새로운 안전 정책을 이번 실험에 도입하지 않는다.


## 11. 출력 보존

각 성공 영상에서 다음을 보존한다.

- 실제 사용한 condition RGB33장
- 실제 생성 마스크와 압축 결과 요약
- 설정과 입력 계보
- 실제 noise·condition 관측 요약
- final latent: 원자 저장 및 readback 검증
- raw decoded tensor
- 모든 출력33프레임
- 원본 속도의 generated.mp4
- step/model_fn/시간/메모리 기록

출력 양끝을 앵커 이미지로 교체하지 않는다.
장식 제거·원본 배경 합성·색보정·warp·얼굴 복원·SR·보간도 하지 않는다.

raw 단계의 실패를 후처리로 숨기지 않는다.
조건 이미지와 실제 생성 프레임을 혼동하지 않게 표기한다.


## 12. 평가 — 원본 진행에 가까워졌는지와 외형 회귀를 함께 본다

생성 전에 원본·기존 앵커·ENDPOINT를 실제로 보고
각 사례의 관측 항목을 짧게 고정한다.

전체33장을 검토하고,
고정 프레임0/4/8/12/16/20/24/28/32를 비교 시트에 포함한다.
C-001에서 차이가 지적된8/16을 반드시 포함한다.

A. 차량
- 은색 높은 차체·루프레일·창/후미등 등 target 특징
- 원본 Mini형 외형으로 돌아가는지
- 우측 이동과 후면 노출 증가의 순서
- 같은 프레임에서의 위치·크기·거친 회전 상태
- 표지판·배경 차량·난간 등의 보호
- 바퀴·차체 경계·접촉의 새로운 손상

B. 개
- 검정/흰 털·주둥이·가슴·발 등 target 특징
- 원본 크림색 개나 원본 체형으로 회귀하는지
- 접근과 몸 방향 변화
- local8/16의 정면 진행·고개 상태
- 발디딤의 관측 가능한 순서
- 꼬리·얼굴·다리의 형태
- 울타리·수풀·잔디 등의 보호

판정 축을 분리한다.

1. 위치·크기 이동
2. 거친 방향·실루엣
3. 시간별 동작 진행
4. 내부 자세·발디딤
5. target 외형
6. 양끝 앵커 충실도
7. 보호 장면
8. 형태·접촉·그림자
9. 실제 연속 품질
10. 비용

마스크 윤곽은 관절 정답이 아니다.
위치만 개선됐으면 위치 개선으로만 보고한다.
발 접촉·가려진 부위는 증거가 없으면 UNCERTAIN이다.

원본 mask와 출력의 IoU가 높아졌다는 이유로
target 체형 전이 성공이라고 하지 않는다.
원본 모양으로 돌아가도 IoU는 좋아질 수 있다.

이번에는 출력 정량화를 위해 새 segmentation·pose 모델을 추가하지 않는다.
기존 도구로 실제 검증 가능한 수치를 낼 수 없다면
정적 관측표와 불확실성으로 보고한다.

기존 endpoint RGB L1 진단은 유지할 수 있다.
그러나 전체 화면 L1을 개체 정체성이나 동작 정확도 점수로 쓰지 않는다.

자동 재정렬·시간축 이동·동적 time warping을 해서
MOV가 잘 맞아 보이게 비교하지 않는다.
원본과 생성의 같은 프레임 인덱스를 비교한다.

앵커의 자세 오차가 있는 구간은 별도로 표시한다.
원본과 앵커가 충돌하는데 모든 조건을 동시에 정확히 맞출 수 있다고
가정하지 않는다.


## 13. 비교 해석과 채택 기준

세 결과를 다음 순서로 해석한다.

ENDPOINT ↔ MOV:
빈 중간 입력 대신 동적 layout을 넣은 전체 효과.

ENDPOINT ↔ STILL:
시간 변화가 없는 구조 안내 자체를 추가한 효과.

MOV ↔ STILL:
같은 종류의 구조 표현에서 원본의 시간 변화를 반영한 조건의 유용성.

두 새 조건 모두 나빠질 수 있다.
그 경우 공식 구조 표현을 사용했다는 이유로 성공을 주장하지 않는다.

조건 조합의 분포 차이, 원본 체형 유입,
앵커와 layout의 충돌, 조건 활용 부족을 가능한 설명으로 구분한다.
한 번의 실패로 원인을 하나로 확정하지 않는다.

사례별 판정:

- USEFUL_MOTION_GAIN:
  MOV가 원본 진행에 더 가깝고 target 외형·장면의 뚜렷한 회귀가 없음.

- COARSE_CONTROL_ONLY:
  위치·크기·실루엣은 개선되지만 관절·머리·접촉은 미해결.

- TRADE_OFF:
  동작은 개선되지만 target 외형 또는 장면·형태가 나빠짐.

- NO_ESTABLISHED_GAIN:
  STILL/ENDPOINT 대비 뚜렷한 이득이 없거나 일관되지 않음.

- WORSE:
  결합 품질이 명확하게 회귀.

- INCONCLUSIVE:
  앵커 충돌·입력/조건 문제·관측 부족 등으로 효과를 판단하기 어려움.

모델 실행 PASS와 품질 판정을 분리한다.
두 사례·단일 seed 결과를 일반화 성능이나 논문 최종 기여로 확대하지 않는다.
33프레임을33개 독립 실험으로 세지 않는다.

실제 연속 재생 검수를 수행했다면
검토 주체·속도·확인 사항을 기록한다.
파일 decode나 재생 가능성 검사만 했다면 temporal=UNVERIFIED다.


## 14. 수식·이론·코드 해설

한국어 해설은 이번 실제 변경과 연결한다.
이전 이론 전체를 다시 복제하지 않는다.

반드시 설명할 내용:

1. 양끝만 조건화한 분포와 원본 구조까지 조건화한 분포의 차이

   p(Y | A0, A32, P)
   p(Y | A0, A32, P, L1:31)

   조건이 늘었다고 원하는 품질이 반드시 좋아지는 것은 아님을 설명한다.

2. 세 변수의 차이

   S_t: 객체 영역
   L_t: 윤곽 RGB
   G_t: VACE 생성 여부 마스크

3. 실제 inactive/reactive 인코딩

   U = Encoder((1-G) * Normalize(X))
   R = Encoder(G * Normalize(X))

   이는 normalized domain의 개념식이다.
   실제 구현의 축·중립값·VAE 처리와 연결해서 설명한다.
   uint8 RGB0을 모델 내부 중립값0과 혼동하지 않는다.

4. 영상 프레임33개와 생성50step의 차이

   프레임 인덱스 t와 생성 진행도 s를 구분한다.
   50step이50프레임을 의미하지 않는다.

5. VAE 시간 압축33→9의 의미와 mask 압축 한계

   조건의 시간 정보가 압축되는 과정과
   RGB 앵커 조건/마스크 채널을 구분한다.

6. 윤곽이 제공하는 정보와 잃는 정보

   위치·크기·거친 형태는 주지만,
   내부 관절·앞뒤 부위·정확한 발 접촉은 충분히 나타내지 않을 수 있다.
   원본 체형 정보도 함께 들어간다.

7. 왜 MOV/STILL이 필요한가

   단순한 형태 추가와 시간 변화의 유용성을 구분한다.
   동시에 종료 앵커 충돌이라는 해석 한계도 명시한다.

8. 다음 구조 연구와의 관계

   이 기준선은 새로운 체형 전이 모듈이 아니다.
   관측된 상충을 바탕으로 향후
   target-aware motion representation,
   객체 내부 대응,
   외형 기억·신뢰도 중 무엇이 필요한지 논의한다.

직관 → 수식 → 실제 함수·tensor → 관측 결과 → 반례/한계 순서로 작성한다.
짧은 이해 확인 질문과 해설도 포함한다.


## 15. GitHub 이력

이번 전체 의뢰서를 work_orders에 보존한다.
실행 전 다음을 고정한다.

- 상위 연구 목표와 이번 제한된 질문
- C-001과의 차이
- 두 사례·네 신규 셀
- layout 렌더링 규칙
- 실제 입력 구성과 기대 변경
- 설정·예산·평가 기준
- 실행 코드와 부모 커밋

권장 실험 문서:

- PLAN.md
- METHOD.md
- CONDITIONS.json
- RESULTS.md
- COSTS.json
- REPRODUCE.md
- LESSON_KO.md
- DELIVERY.json

필요 파일만 만들고 같은 내용을 다수 문서에 반복하지 않는다.
HISTORY·ROADMAP에는 방향·목표·실제 관측·다음 판단을 이어서 기록한다.

C-001의 PARTIAL/UNVERIFIED와 A/B의 실패·보류를 삭제하거나
이번 결과로 소급 PASS 처리하지 않는다.

공개 GitHub에는 코드·비민감 문서·필요한 hash만 올린다.
개인 경로·PID·모델 가중치·cache·latent·민감 미디어는 공개하지 않는다.
공개 데이터도 재배포 조건을 확인한다.

실행 전후 commit/push와 원격 SHA 일치를 실제 확인한다.
이번 응답에서 계획만 만들었는데 GPU까지 수행한 것처럼 쓰지 않는다.


## 16. 검토 산출물과 전달

사례별 한 화면에서 다음을 비교한다.

SOURCE
TARGET REFERENCE
START / END ANCHOR
ENDPOINT
LAYOUT_MOV
LAYOUT_STILL

추가로 실제 MOV/STILL 조건 영상·source SAM overlay를 제공한다.
조건 영상은 “모델 입력”, 출력 영상은 “생성 결과”라고 명확히 표시한다.

검토 뷰어:
- 같은 프레임 인덱스의 슬라이더
- 동일 preview16fps의 나란한 재생
- 전체33프레임 접근
- 고정 프레임 비교 시트
- 대상과 주변 장면을 볼 수 있는 확대
- 입력/조건/결과/한계를 함께 표시

기존 C-001 source·앵커·ENDPOINT를 재사용한다.
기존 MP4와 새 raw 생성 MP4는 가능하면 파일 바이트를 그대로 전달한다.
나란한 비교 MP4·thumbnail·contact sheet는 새 파생물임을 명시한다.
전체 작업을 “영상 재인코딩0”이라고 일괄 표현하지 않는다.

검토 ZIP은 작은 compact로 만든다.
- 입력과 앵커
- 기존 ENDPOINT2개
- 신규 생성4개
- 조건 미리보기
- 뷰어·시트·보고서·재현 자료

raw tensor·final latent·무손실 전체 프레임은 별도 full에 보존한다.
C-001 full과 가중치를 반복 중복 포장하지 않는다.
단순 용량 감축을 위해 실제 생성 MP4의 화질을 낮추지 않는다.

실제 Spark/Mac /tmp에 저장하고 다음을 확인한다.
- ZIP 크기·SHA256
- CRC
- manifest의 파일 크기·hash
- 실제 추출
- 전송 후 양 호스트 바이트 일치

하지 않은 검증을 PASS로 보고하지 않는다.
자체 실행 프로세스 종료와 다른 작업 보존을 확인한다.


## 17. 최종 보고 순서와 종료

최종 보고는 검사 개수보다 다음 질문에 먼저 답한다.

1. MOV는 ENDPOINT/STILL보다 원본 진행을 더 잘 따랐는가?
2. 무엇이 개선됐는가:
   위치·크기·거친 방향·내부 동작 중 어디까지인가?
3. target 외형·체형·보호 장면에 어떤 부작용이 생겼는가?
4. 현재 앵커의 자세 오차가 비교에 어떤 한계를 만들었는가?
5. 실제 추가 비용과 실패·복구 사용량은 얼마인가?
6. 다음 연구에서 바꿀 부분 하나는 무엇인가?

동작 개선이 없으면 그 결과로 종료한다.
새 mask 색·선 두께·seed·prompt·모델을 자동 탐색하지 않는다.

동작만 좋아지고 target 체형이 나빠졌다면
target-aware 구조 변환의 필요성 후보로 기록한다.

위치만 좋아지고 관절·고개가 틀리면
내부 대응·점 궤적의 필요성 후보로 기록한다.

조건 효과가 불명확하면
새 연결 방법이 검증되지 않았다고 기록한다.
이를 해결하기 위한 추가 GPU 실험은 이번에 자동 시작하지 않는다.

이번 네 결과와 기존 두 기준선을 함께 검토한 뒤,
다음 수식·구조·학습 개입은 사용자와 논의해서 정한다.


## 참고 근거

C-001 결과·실행 계약·코드:
https://github.com/hyunlord/make-meme/tree/5ba0cdbe4a11bb35ae77ce638acbbcc501e90da2/docs/research/experiments/C-001-hybrid-endpoint-baseline

공식 VACE layout 구현:
https://github.com/ali-vilab/VACE/blob/48eb44f1c4be87cc65a98bff985a26976841e9f3/vace/annotators/layout.py

공식 VACE 조건 인코딩:
https://github.com/ali-vilab/VACE/blob/48eb44f1c4be87cc65a98bff985a26976841e9f3/vace/models/wan/wan_vace.py
