# C-003 통합 작업 의뢰서
# 같은 동적 윤곽에서 객체 내부 구조의 시간 변화가 유용한가?

저장소: hyunlord/make-meme

부모 실험:
C-002-sam-layout-conditioning

부모 기준 커밋:
853ee952795246648b3a6e46d37d5dead03abef3

권장 실험 경로:
docs/research/experiments/C-003-internal-structure-conditioning/

권장 의뢰서 보존 경로:
docs/research/work_orders/C003_INTERNAL_STRUCTURE_WORK_ORDER_KO.md


## 0. 최종 연구 목표와 이번 질문

최종 목표는 다음과 같다.

원본 영상 + 편집 지시 + 선택적 대상 참조 이미지
→ 소수의 편집 앵커 생성
→ 원본 객체와 편집 객체의 역할·동작 연결
→ 로컬 영상 생성
→ 대상 외형·원본 동작·보호 장면을 함께 유지하는 영상 편집

C-001은 양끝 앵커로 실제 중간 영상을 만들었다.
C-002는 기존 SAM 윤곽을 중간 생성 조건으로 연결했다.

C-002의 개 사례에서는 정면 접근 등 거친 진행이 개선됐지만,
머리·관절·교대 보행·발 접촉은 여전히 불확실하다.
차량은 보호 장면 손상이 동반된 TRADE_OFF다.

이번 질문은 다음 하나다.

“같은 동적 외곽선과 같은 양끝 앵커에서,
객체 내부의 시간별 구조를 추가하면
외곽선만 사용하거나 내부 구조를 고정한 경우보다
원본의 머리·다리 진행을 더 잘 따르는가?”

이번은 내부 정보의 유용성을 확인하는 표현 기준선이다.
아직 실제 관절 대응·3D pose·target 체형 전이 모듈을
구현하거나 학습하는 실험이 아니다.

구조선은 관절 정답이 아니다.
RGB 색을 제거해도 원본의 체형·털 경계·질감·가림 정보는 남을 수 있다.
이를 순수한 motion-only 또는 identity-free 표현으로 부르지 않는다.

A/B 이력과 C-001/C-002 결과를 보존한다.
B-034 복구나 새로운 실행기·안전 정책 설계를 시작하지 않는다.


## 1. 착수 전 상태와 자료 확인

C 트랙의 실제 branch/worktree와 최신 HEAD를 확인한다.
부모 커밋으로 강제 reset하거나 과거 B 브랜치명을 추정해 사용하지 않는다.
다른 작업과 기존 수정 내용을 덮어쓰지 않는다.

같은 C-003이 실행 중이거나 완료됐다면 중복 생성하지 않는다.

읽을 자료:
- C-002 RESULTS.md
- C-002 METHOD.md
- C-002 CONDITIONS.json
- C-002 NUMERICS.json
- C-002 code/video_generate.py
- C-001 INPUTS.json
- C-001 ANCHORS.json
- C-001 BACKEND_CONTRACT.md
- C-001 SAM_ANALYSIS.md
- 실제 C 트랙 HISTORY·ROADMAP·상위 연구 방향 문서

이번에는 C-001/C-002의 개 사례만 사용한다.
차량 결과는 역사·회귀 사례로 보존하며 새 차량 영상을 만들지 않는다.

기존 source·anchor·SAM mask·layout·baseline 파일을 재사용한다.
검토 ZIP에 없는 무손실 자료는 기존 Spark 산출물에서 읽는다.
없는 파일을 얻기 위해 완료된 생성이나 SAM 분석을 다시 실행하지 않는다.


## 2. 역할과 실행 범위

Codex Astra:
- 내부 구조 조건과 대조군을 구현한다.
- 가설·수식·입력·평가 기준을 실행 전에 고정한다.
- Spark 실행을 조율하고 실제 비교 결과를 해석한다.
- 한국어 이론·코드 해설과 GitHub 이력을 남긴다.

DGX Spark:
- 필요한 구조선 추출을 수행한다.
- 기존 VACE로 새 영상 두 개를 생성한다.
- 조건·noise·출력·시간·메모리를 기록한다.

이번 imagegen 호출은0회다.
기존 개의 시작·종료 앵커를 수정하지 않는다.
SAM 입력 재추론0회, 모델 학습0회다.

새 점 추적기·pose·depth·flow 모델은 추가하지 않는다.
임의의 색깔 점이나 해골 그림을 넣고
pretrained VACE가 관절 의미를 이해한다고 가정하지 않는다.


## 3. 고정 입력과 비교표

기존 case_nonrigid를 사용한다.

- source: C-001/C-002의 dog 33프레임
- target reference: 기존 dog-gooses 참조
- 양끝 앵커: 기존 imagegen 결과 두 장
- 동적 외곽선: C-002 LAYOUT_MOV의 실제 layout33장
- SAM mask: 기존 selected edited_subject의 visible mask33장

정확한 파일·frame ID·좌표 변환은 기존 manifest를 따른다.
다른 구간이나 더 좋은 reference로 바꾸지 않는다.

공통 좌표와 시간:
- 832×480
- 33프레임
- 앵커 위치0/32
- source_fps=null
- preview_fps=16
- timebase_assumed=true

33/16초의 파일 지속시간과
32/16초의 양끝 표본 간격을 구분한다.
원본의 실제 초 단위 타이밍을 확인한 것으로 보고하지 않는다.

주 비교는 세 조건이다.

A. OUTLINE_ONLY
   C-002의 기존 개 LAYOUT_MOV 출력 재사용.
   새 생성0회.

B. INTERNAL_DYNAMIC
   같은 동적 외곽선
   + 각 source 시점에서 추출한 내부 구조선.
   새 생성1회.

C. INTERNAL_HOLD
   같은 동적 외곽선
   + 첫 프레임 내부 구조를 현재 객체 bbox로 옮긴 조건.
   새 생성1회.

INTERNAL_HOLD는 화면에 고정한 그림이 아니다.
객체의 위치·크기 변화는 따라가고,
정규화된 내부 무늬·구조의 시간 변화만 제한한다.

이는 진짜 정지 자세나 완전한 motion-off 분기가 아니다.
현재 실루엣에 의한 clipping과 bbox 변환 때문에
HOLD에도 일부 시간 변화가 남는다는 한계를 명시한다.

C-001 ENDPOINT와 C-002 LAYOUT_STILL은
필요하면 별도 역사 패널에 보여 주되,
이번 핵심 대조군은 위 세 조건으로 고정한다.


## 4. 생성 전 실제 동작 관측

source와 기존 두 앵커, C-002 MOV를 직접 확인한다.
원본 RGB는 조건 추출과 평가에 사용하며,
영상 생성기에 그대로 전달하지 않는다.

고정 프레임:
0/4/8/12/16/20/24/28/32

출력 생성 전에 다음을 간단한 표로 기록한다.

- 머리의 화면상 방향과 높이 변화
- 보이는 코·귀·앞다리 경계
- 구분 가능한 앞발의 전후 배치
- 몸통 접근과 크기 변화
- 발·다리의 겹침 및 관측 불가능 구간
- 기존 종료 앵커와 source의 자세 충돌

각 항목은 OBSERVED / OCCLUDED / AMBIGUOUS로 구분한다.
화면 왼쪽 발과 동물의 해부학적 왼쪽 앞발을 혼동하지 않는다.
가려진 관절·발 좌표를 추정 정답으로 채우지 않는다.

평가를 위해 필요한 소수의 보이는 표면점은
고정 프레임에서 주석할 수 있다.
그 점을 실제 관절·접촉 GT로 부르지 않는다.
주석 시간은 전체20분 이내로 제한한다.

완벽한 보행 GT가 없다는 이유로 실험 전체를 중단하지 않는다.
명확히 볼 수 있는 사건과 불확실한 항목을 나눠 평가한다.

29~32번의 앵커 충돌은 별도로 표시한다.
이 구간을 숨기거나 평가에서 없애지 않는다.
0~28번의 진행과 종료부를 구분해 해석한다.


## 5. 내부 구조 추출기 — 공식 VACE scribble 한 종

사용할 구현:
ali-vilab/VACE
commit 48eb44f1c4be87cc65a98bff985a26976841e9f3
vace/annotators/scribble.py
vace/configs/video_preproccess.py

공식 클래스:
ScribbleAnnotator / ScribbleVideoAnnotator

공식 가중치 경로:
VACE-Annotators/scribble/anime_style/netG_A_latest.pth

기존 로컬 가중치·환경에 있는지 먼저 확인한다.
없으면 공식 ali-vilab/VACE-Annotators 배포에서
해당 파일 한 개만 다운로드하는 것을 허용한다.
다운로드 상한64MiB다.
실제 repository revision·파일 SHA256·크기·출처를 기록한다.
전체 VACE-Annotators 저장소나 다른 모델은 다운로드하지 않는다.

공식 모듈 구성과 가중치 key/shape를 맞춰 strict load한다.
weights_only=True를 사용하고 임의 pickle 실행으로 우회하지 않는다.
동일한 기존 Torch 환경을 사용하며 대형 환경 upgrade는 하지 않는다.

평가 모드·inference_mode, 공식 FP32 연산 경로를 유지한다.
FP16 변환·양자화·학습·dropout 활성화는 하지 않는다.
필요한 최소 source를 재사용할 수 있지만 연산 의미를 바꾸지 않는다.

source33장을 한 번 처리하고 raw 구조선 결과를 캐시한다.
full-frame source를 추출기에 넣은 뒤 내부 영역만 선택한다.
마스크로 먼저 잘라 생기는 인공 경계가 추출 결과를 지배하지 않게 한다.

입력 source는 기존832×480 무손실 프레임이다.
검토용 JPEG·MP4를 다시 decode한 것으로 대체하지 않는다.

구조선의 grayscale 범위와 polarity를 실제 확인한다.
공식 출력·예제 의미를 기준으로 검정 선/흰 바탕을 확정한다.
필요한 polarity 변환은 생성 전에 한 번 고정하고 기록한다.
출력 품질을 보고 반전·threshold·선 두께를 탐색하지 않는다.

모델이 만든 선에는 털·눈·무늬·질감·조명 경계도 포함될 수 있다.
관절만 추출했다고 보고하지 않는다.

가중치나 필수 실행 경로를 확보하지 못하면
ANNOTATOR_UNAVAILABLE로 구체적인 이유를 남긴다.
Canny·다른 lineart 모델·무작위 가중치로 조용히 대체하지 않는다.
완료된 C-002를 다시 생성하는 작업으로 바꾸지도 않는다.

구조 추출기와 VACE를 동시에 메모리에 올리지 않는다.
추출 완료 후 해당 프로세스를 종료하고 캐시를 사용한다.


## 6. 외곽선과 내부 정보가 섞이지 않도록 영역 정의

다음 기호를 구분한다.

S_t:
기존 SAM의 source 객체 영역.

L_t:
C-002의 동적 외곽선 RGB.
흰 바탕, 검정3px 외곽선.

J_t:
공식 scribble 추출기의 grayscale 구조선.
흰색이 비선 영역, 어두운 값이 선인 표현으로 고정.

I_t:
새 내부 정보를 허용할 공통 영역.

G_t:
VACE 생성 여부 마스크.
SAM 객체 영역과 다른 값이다.

I_t는 다음 고정 규칙으로 만든다.

- S_t 안에서 경계까지의 Euclidean distance가4px보다 큰 위치.
- 동시에 기존 L_t가 흰색인 위치.
- 두 신규 조건에 완전히 같은 I_t 적용.

예:
I_t = (distance_inside(S_t) > 4) AND (L_t_gray == 255)

이것은 추출 정보의 공간 선택일 뿐,
기존 SAM mask나 C-002 외곽선을 바꾸는 것이 아니다.

외곽선·객체 밖·경계대의 RGB는
C-002 L_t와 픽셀 단위로 동일해야 한다.

고정4px를 결과에 따라 줄이거나 키우지 않는다.
얇은 발·귀·꼬리의 일부가 내부 영역에서 제외될 수 있음을 기록한다.
제외된 부위까지 내부 구조를 제공했다고 주장하지 않는다.

작은 speckle을 제거하거나 mask를 새로 다듬지 않는다.
동일 좌표에서 구조 추출이 잘못 연결된 경우는 입력 오류로 수정하되,
실제 source 구조를 임의로 보정하지 않는다.


## 7. 두 내부 조건의 수식과 실제 구성

단순 screen-space 반복은 객체 이동까지 막으므로 사용하지 않는다.
SAM bbox를 이용해 전체 위치·크기와 내부 구조를 분리한다.

S_t의 bbox 중심을 c_t,
폭·높이를 D_t=diag(w_t,h_t)라 두고
정규화 좌표 u∈[-1/2,1/2]^2를 정의한다.

A_t(u)=c_t+D_t u
A_t^{-1}(p)=D_t^{-1}(p-c_t)

이것은 bbox 좌표 변환이다.
회전 정렬·의미적 관절 대응·3D 변환이 아니다.

내부 선의 강도를 다음처럼 정의한다.

d_t(p)=I_t(p) * (1-J_t(p)/255)

공식 polarity를 확정한 뒤 이 정의를 적용한다.
입력으로 사용할 선을 임의로 이진화하지 않는다.

정규화 canvas는256×256으로 고정한다.

d_t^N(u)=Sample(d_t,A_t(u))

- grayscale 구조는 bilinear
- 영역 mask는 nearest
- 범위 밖의 선 강도는0
- 좌표의 pixel-center 규약과 bbox 끝점 규약을 명시

두 신규 조건 모두 같은 정규화·역변환 경로를 거친다.
DYNAMIC만 원본 해상도 그대로 쓰고 HOLD만 resize해서
보간 처리 차이가 커지게 하지 않는다.

INTERNAL_DYNAMIC의 내부 선:

D_t^dyn(p)=I_t(p) * Sample(d_t^N,A_t^{-1}(p))

INTERNAL_HOLD의 내부 선:

D_t^hold(p)=I_t(p) * Sample(d_0^N,A_t^{-1}(p))

HOLD는 source 첫 프레임의 정규화 내부 구조를 사용한다.
더 선명한 중간 프레임으로 사후 변경하지 않는다.
원본 전체 이동·크기 변화와 현재 I_t는 동일하게 유지한다.

다음 limitations를 명시한다.

- bbox 변환은 비강체 자세의 정답 대응이 아니다.
- HOLD에는 확대·축소·clipping에 의한 변화가 남는다.
- DYNAMIC/HOLD의 선 밀도와 보이는 부분은 달라질 수 있다.
- 두 조건의 종료 앵커와 충돌 정도도 다를 수 있다.
- 따라서 순수한 관절 운동의 인과효과라고 주장하지 않는다.

각 중간 layout을 다음처럼 구성한다.

K_t^mode(p) =
    L_t(p),                               I_t(p)=0
    round(255 * (1-D_t^mode(p))),          I_t(p)=1

grayscale 결과를 같은 값의3채널 RGB로 만든다.
양 조건 모두 I_t 밖의 픽셀은 기존 L_t와 정확히 같아야 한다.

새 내부 조건은 source-derived structural information이다.
원본의 RGB 색을 그대로 쓰지는 않지만,
source 형태·질감·외형 정보가 완전히 제거된 표현은 아니다.


## 8. 모델 입력 구성 — 양끝과 생성 마스크 유지

최종 조건 영상은 두 신규 조건 모두 다음 구조다.

X_0=A_0
X_32=A_32
X_t=K_t^mode, 1≤t≤31

양끝 앵커는 C-001 원본 파일 그대로 사용한다.
앵커에 구조선을 그리거나 crop·warp·재생성하지 않는다.

VACE 생성 마스크 G:
- t=0,32: 프레임 전체0
- t=1..31: 프레임 전체255

vace_reference_image=None 유지.
S_t나 I_t를 G_t로 사용하지 않는다.

조건은 무손실 PNG 또는 인메모리 RGB로 전달한다.
검토용 MP4나 source+선 overlay는 모델 입력으로 사용하지 않는다.

기존 코드의 mode 검사에 새 모드를 추가한다.
권장:
internal_dynamic
internal_hold

기존 endpoint/layout_mov/layout_still 검사는 유지한다.
새 모드의 grayscale0..255 허용을 위해
기존 모든 입력 검사를 제거하지 않는다.

새 모드에서는 다음을 확인한다.
- uint8 RGB,832×480,33장
- RGB 세 채널의 값 동일
- 양끝 앵커 픽셀 불변
- G 전체 불변
- 내부 허용 영역 밖은 기존 L_t와 pixel-exact
- DYNAMIC/HOLD가 의도한 서로 다른 내부 조건인가

참조·조건이 다른 채널이나 branch로 전달되지 않게 한다.
새 checkpoint 채널·임의 control tensor를 추가하지 않는다.

현재 pretrained VACE에 layout과 scribble 내부 정보를 합친
미검증 조합을 주는 실험임을 기록한다.
공식 scribble 모듈을 썼다고 이 혼합 조건의 성능까지
공식 검증된 것으로 보고하지 않는다.


## 9. 고정 영상 모델과 실제 조건 확인

C-002의 VACE 환경을 그대로 사용한다.

- Wan2.1-VACE-1.3B
- 기존 checkpoint revision 및 실제 파일
- 기존 DiffSynth pipeline
- BF16, SDPA, tiled VAE
- adapter OFF
- Euler50
- CFG5
- sigma_shift5
- seed20261028
- rand_device=cpu
- 832×480·33frames·preview16fps
- 해당 개 사례의 prompt와 negative_prompt 그대로
- 기존 effective vace_scale1.0 유지

공식 별도 runner의 UniPC/shift16으로 바꾸지 않는다.
SCAIL이나 다른 영상 모델로 전환하지 않는다.

기존33→9 마스크 시간 압축과 양끝0 누락 한계는 유지한다.
endpoint clamp·압축 방식 수정·양끝 이미지 덮어쓰기를 하지 않는다.

실제 최초 model_fn에서 기존 관측 hook을 재사용한다.

- noisy latent shape/dtype/hash
- VACE context shape/dtype/hash/finite
- mask64채널 hash
- effective scale

예상 shape:
noise [1,16,9,60,104]
context [1,96,9,60,104]

새 두 실행의 noise hash는 같아야 한다.
C-002에 기록된 noise hash와도 대조한다.
불일치 시 입력·seed·실행 경로를 확인하고
같다고 가정한 결과 해석을 하지 않는다.

생성 마스크는 정확히 동일해야 한다.
inactive 입력 RGB는 동일하고,
reactive 입력의 내부 구조만 변경됐는지 확인한다.

실제 인코더 연산의 미세 수치 차이와
파일·논리 입력의 불변성은 구분한다.
대형 텐서의 bitwise 재현만을 위한 추가 생성은 하지 않는다.

관측용 추가 DiT forward와 대형 attention dump는0회다.
최초 latent/context를 읽는 것이 RNG나 모델 입력을 바꾸지 않게 한다.


## 10. 입력 품질 점검은 짧게, 실제 생성까지 수행

추출 후 source33장·scribble·I_t·두 조건을 나란히 확인한다.

점검할 것:
- source와 내부 구조의 시간 인덱스가 맞는가?
- 머리·다리 부근에 실제로 추가 구조가 존재하는가?
- 배경 선이 조건으로 들어가지 않는가?
- 외곽선이 보존되는가?
- HOLD가 객체를 따라 이동하는가?
- 보간이나 좌표 반전 오류가 없는가?

이 확인은 구조 입력의 유효성을 보는 것이다.
생성 결과가 좋아질 것 같은 입력으로 tuning하지 않는다.

구조선이 일부 부위를 표현하지 못하면
그 부위는 NOT_REPRESENTED로 표시하고 나머지 관측을 진행한다.
완벽한 관절 구조가 없다는 이유로 모든 실행을 막지 않는다.

다만 내부 정보가 사실상 전부 비어 있거나,
추출기·좌표 오류 때문에 두 신규 조건이 같아진 경우에는
무의미한 영상 생성을 하지 말고 구체적으로 보고한다.
다른 표현·모델을 자동 추가하지 않는다.

조건 준비·검사가 끝나면
문서나 구조선 PNG만 제출하고 종료하지 않는다.
유효한 두 조건으로 실제 비교 영상을 만든다.


## 11. 실행 예산·오류 처리·자원

정상 영상 생성:
- INTERNAL_DYNAMIC1회
- INTERNAL_HOLD1회
- 각각50step·100 model_fn call
- 정상 합계100step·200 model_fn call

영상 heavy 시도는 기본2회에 기계적 복구 예비1회를 더해 최대3회다.
모델 로딩 후 실패한 heavy 시작도 기록한다.

품질을 이유로 seed·prompt·선 강도·내부 margin을 바꿔
재생성하는 것은0회다.

구조 추출:
- source33장에 대한 완료된 extraction pass1회
- raw 결과 캐시
- 기존 결과가 정확히 같은 조건으로 있으면 재사용
- 보조 extractor 비용은 영상 생성 비용과 별도 기록

추가 허용:
- 공식 scribble 소형 가중치 한 파일, 필요할 때만 ≤64MiB

금지:
- imagegen
- SAM 재추론
- 새 대형 모델·점 추적기
- 학습·LoRA
- 새 패키지·Torch/CUDA upgrade
- 추가 영상 사례
- 후합성·업스케일·보간

경로·인자·dtype·import 등 모델 시작 전 오류는
같은 작업 안에서 수정하고 CPU 검사를 이어갈 수 있다.
이런 오류마다 새 연구 번호나 별도 의뢰를 만들지 않는다.

최종 latent가 저장된 뒤 decode가 실패하면
sampler를 재실행하지 않는다.
저장된 latent의 VAE-only 복구를 전체최대1회 허용한다.
MP4 포장 오류는 기존 raw/PNG로 수정한다.

외부 GPU 작업·OOM·실제 메모리 압박 등 안전 중단은
자동 재시도하거나 기준을 완화하지 않는다.

실행기·가드·서비스 정책은 C-002에서 성공한 경로를 재사용한다.
이전 B-034 운영 실험을 재개하거나 새 운영 정책을 만들지 않는다.
모든 실행 경로·입력·출력은 기존 공통 절대경로 계약을 유지한다.

전체 작업 상한3시간.
마지막20분은 기록·전달·종료에 남긴다.
새로 필요한 분석·조건 구현 목표상한45분이다.

완벽한 부가 평가 때문에 실제 영상 생성을 뒤로 미루지 않는다.


## 12. 평가 — 내부 동작과 source 외형 회귀를 함께 본다

핵심 비교:
SOURCE / TARGET / ANCHORS /
C002 OUTLINE_ONLY / INTERNAL_DYNAMIC / INTERNAL_HOLD

전체33프레임과 고정 인덱스
0/4/8/12/16/20/24/28/32를 비교한다.
local8/16과29~32를 반드시 포함한다.

별도로 평가한다.

A. 전체 이동
정면 접근·위치·크기 진행이 C-002보다 나빠지지 않았는가?

B. 머리·내부 구조
고개 방향·높이, 주둥이·귀·목 연결이 원본 사건에 가까워졌는가?

C. 다리 진행
관측 가능한 앞발의 전후 배치와 다리 겹침의 순서가 가까워졌는가?
보이는 발끝 위치가 낮다는 이유만으로 접촉 성공이라고 하지 않는다.

D. target 외형
검정/흰 털, 주둥이·가슴·발의 특징이 유지되는가?
source의 크림색 외형·무늬·체형으로 회귀하지 않는가?

E. 보호 장면
울타리·수풀·잔디·카메라·비대상 영역의 손상이 늘지 않았는가?

F. 형태·시간
다리 추가·융합, 얼굴 붕괴, 순간적인 분절,
종료부의 급격한 전환이 줄거나 늘었는가?

G. 비용
구조 추출·조건 변환·영상 생성·검토·주석 비용이 각각 얼마인가?

raw와 실제 생성 MP4를 검토한다.
좋은 프레임만 선택하거나 출력별 시간축을 이동하지 않는다.
자동 warp·동적 시간 정렬로 잘 맞아 보이게 하지 않는다.

추출 구조선과 출력 구조선이 비슷하다는 것만으로
원본 동작을 맞췄다고 평가하지 않는다.
조건을 만든 모델을 유일한 평가기로 쓰지 않는다.

새 segmentation·pose 모델을 평가용으로 설치하지 않는다.
보이는 사건·소수의 관측 가능한 위치와 전체 프레임 검토를 사용한다.
불확실하면 수치를 억지로 만들지 않는다.

가능하면 출력 이름을 가린 비교 시트로 검토하되,
같은 에이전트의 관측을 독립 human 평가라고 쓰지 않는다.

실제 연속 재생을 지각 검수했다면
누가·어떤 속도로·무엇을 확인했는지 기록한다.
브라우저 재생 성공·ffmpeg decode·정적 시트만 확인했다면
temporal=UNVERIFIED를 유지한다.


## 13. 해석과 방법 판정

OUTLINE_ONLY ↔ DYNAMIC:
내부 구조를 추가한 전체 효과.

OUTLINE_ONLY ↔ HOLD:
객체 위치·크기를 따르는 초기 내부 구조를 추가한 효과.

DYNAMIC ↔ HOLD:
시점별 내부 구조 변화가 추가로 유용한지.

이 비교에서 바뀌는 것은 관절만이 아니다.
선 밀도·질감·가림·bbox 보간·현재 마스크 clipping도 영향을 줄 수 있다.
단일 원인을 확정하지 않는다.

판정 후보:

USEFUL_INTERNAL_GAIN
- 관측 가능한 내부 동작이 두 대조군보다 개선되고
  target 외형·전체 이동·장면의 뚜렷한 회귀가 없음.

COARSE_GAIN_ONLY
- 전체 접근이나 실루엣만 좋아지고 내부 진행은 미입증.

APPEARANCE_ONLY
- 구조선이 외형 세부에는 영향을 줬지만 내부 동작 이득은 미입증.

TRADE_OFF
- 내부 동작 일부가 개선됐지만 source 외형 복사,
  target 손상·배경 회귀가 동반됨.

NO_ESTABLISHED_GAIN
- 두 대조군 대비 뚜렷하거나 일관된 이득이 없음.

WORSE
- 결합 품질이 명확하게 나빠짐.

INCONCLUSIVE
- 조건 표현의 부적합, 앵커 충돌, 관측 부족 등으로
  가설 효과를 판단하기 어려움.

조건 전달 PASS와 품질 판정을 분리한다.
hash가 달라졌다는 사실을 조건 활용 성공으로 올리지 않는다.

한 개의 개발 영상·한 seed다.
일반화·논문 성능·정확한 개체 일치·완전한 동작 전이를 주장하지 않는다.

기존 C-002 차량 TRADE_OFF와 개 COARSE_CONTROL_ONLY,
C-001 PARTIAL, A/B 이력은 그대로 보존한다.


## 14. 수학·구조·코드 해설

한국어 설명은 이번 실제 입력과 출력에 연결한다.

필수 주제:

1. 외곽선만으로 내부 자세가 유일하게 결정되지 않는 이유.
   서로 다른 자세 q1,q2가 비슷한 silhouette을 가질 수 있음을 설명.

2. 전역 위치·크기와 객체 내부 변화의 분리.
   p=c_t+D_t u의 의미와 bbox 정규화의 한계.

3. DYNAMIC과 HOLD의 정확한 차이.
   HOLD가 완전히 정적인 영상 조건은 아니라는 점.

4. S_t / L_t / J_t / I_t / G_t의 구분.
   객체 마스크, 윤곽 RGB, 내부 구조선, 내부 적용 영역,
   VACE 생성 여부 마스크를 혼동하지 않도록 설명.

5. 실제 조건 인코딩.
   U=Encoder((1-G)*Normalize(X))
   R=Encoder(G*Normalize(X))
   내부 구조가 reactive 경로로 들어가는 과정과
   16+16+64채널의 실제 context 연결.

6. 33프레임·9개 시간 latent·50 생성 step의 차이.
   영상 시간 t와 생성 진행도 s를 분리.

7. 정보가 추가돼도 품질이 좋아진다고 보장되지 않는 이유.
   source 형태·질감 누수, target 앵커와의 충돌,
   pretrained 모델이 보지 못한 혼합 표현 가능성.

8. 다음 방법 연구와의 관계.
   이번은 구조선 proxy의 기준선이며,
   시간별 의미 대응·가시성·confidence·target retargeting은 아직 아님.

직관 → 수식 → 실제 함수/tensor → 결과 → 반례·한계 순서로 작성한다.
실제 관측을 설명하지 못하는 장식용 수식을 늘리지 않는다.
짧은 이해 확인 질문과 답도 남긴다.


## 15. GitHub 기록과 산출물

착수 전:
- 전체 의뢰서 보존
- PLAN에 질문·입력·조건·예산·평가 고정
- annotator 코드·가중치 출처·실제 revision/hash 기록
- DYNAMIC/HOLD 조건과 영상 입력을 생성 전에 고정
- 실행 코드 commit/push 및 원격 확인

종료 후:
- RESULTS.md
- METHOD.md
- CONDITIONS.json
- COSTS.json
- REPRODUCE.md
- LESSON_KO.md
- DELIVERY.json
- 필요한 작은 평가표와 코드

기존 스타일을 재사용하고 같은 내용을 여러 문서에 반복하지 않는다.
HISTORY·ROADMAP에는 목표·가설·실제 관측·다음 판단을 연결한다.
새 운영 수정이나 CPU 테스트 개수를 연구 성과로 세지 않는다.

원본 미디어·앵커·가중치·latent·개인 경로·PID를
공개 GitHub에 올리지 않는다.
공개 데이터도 재배포 조건을 확인한다.

검토 뷰어:
- 원본·참조·두 앵커
- C-002 개 MOV 기준선
- 신규 DYNAMIC/HOLD 두 출력
- 실제 내부 조건 DYNAMIC/HOLD
- SAM 윤곽·내부 적용 영역·구조선 시각화
- 전체33프레임 슬라이더
- 같은16fps 비교
- 고정 프레임 및 머리·다리 확대
- 판정과 한계

모델 입력 조건과 실제 생성 결과를 명확히 구분한다.

compact:
- 비교 MP4·앵커·조건 미리보기
- 뷰어·작은 시트·보고서·재현 자료

full 또는 기존 로컬 보존 경로:
- 구조선 raw·무손실 조건
- 신규 raw/latent
- 전체 무손실 출력 프레임

기존 C-001/C-002 full과 가중치를 중복 포장하지 않는다.
실제 생성 MP4를 용량 때문에 다시 낮은 화질로 변환하지 않는다.
새 비교영상·thumbnail은 새 파생물로 표시한다.

실제 Spark/Mac /tmp에 저장하고
CRC·파일 크기·SHA256·manifest·실제 추출·전송 동일성을 확인한다.
하지 않은 검증은 했다고 보고하지 않는다.

자체 프로세스 종료와 다른 작업 보존을 확인한다.


## 16. 최종 보고와 종료

최종 보고의 첫 질문은 다음이다.

1. DYNAMIC은 기존 윤곽-only와 HOLD보다
   원본의 머리·다리 진행을 더 잘 따랐는가?
2. 실제로 개선된 것은 내부 움직임인가,
   전체 위치·크기인가, 외형 세부인가?
3. target 외형과 보호 장면에 어떤 손해가 생겼는가?
4. 구조선이 표현하지 못한 부위와 앵커 충돌은 무엇인가?
5. 추가 비용은 얼마이며 다음 구조를 연구할 근거가 생겼는가?

이번 두 결과 이후 종료한다.
다른 margin·정규화 크기·선 강도·seed·prompt를 자동 탐색하지 않는다.
점 추적기·pose 모델·새 학습·target 체형 모듈도 자동 시작하지 않는다.

이득이 있으면:
실제로 어느 내부 정보가 유용했는지를 분석하고,
그 정보를 더 선택적으로 전달하는 대응·신뢰도 모듈을 다음 후보로 삼는다.

이득이 없으면:
정보가 불충분한 것과 모델이 조건을 사용하지 못하는 것을 구분한다.
구조선 실패를 객체 내부 대응 연구 전체의 실패로 확대하지 않는다.

source 외형 복사가 커지면:
내부 구조와 원본 외형을 분리하는 표현·학습이 필요한 후보로 기록한다.

다음 수식·아키텍처·학습 개입은
이번 입력과 실제 두 출력을 사용자와 검토한 뒤 결정한다.


## 참고 근거

C-002 부모 결과:
https://github.com/hyunlord/make-meme/tree/853ee952795246648b3a6e46d37d5dead03abef3/docs/research/experiments/C-002-sam-layout-conditioning

공식 VACE scribble:
https://github.com/ali-vilab/VACE/blob/48eb44f1c4be87cc65a98bff985a26976841e9f3/vace/annotators/scribble.py

공식 VACE preprocessing 설정:
https://github.com/ali-vilab/VACE/blob/48eb44f1c4be87cc65a98bff985a26976841e9f3/vace/configs/video_preproccess.py

공식 annotator 배포:
https://huggingface.co/ali-vilab/VACE-Annotators/tree/main/scribble/anime_style

가중치 배포의 main은 실제 다운로드 시 immutable revision으로 기록한다.
기록된 링크가 현재 로컬에 설치·검증됐다는 뜻은 아니다.
