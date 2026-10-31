# C-009 통합 작업 의뢰서
# 새 Claude Code 세션용
# 정상 마스크 기반 조건 캐시 재생성·동일 설정 재학습·생성 비교

저장소: hyunlord/make-meme
실행 장비: 기존 DGX Spark
역할: 기존 연구를 인수해 C-009를 수행하는 Claude Code

C-008 기준:
ecaa653
docs/research/experiments/C-008-conditioning-parity/

C-006 학습 기준:
c4aef32de21de4073bd4eb1861df4d35f2eda793
docs/research/experiments/C-006-motion-point-adapter-pilot/

C-007 평가·영상 기준:
19e110431e90931c98277b7e94d6879268929336
docs/research/experiments/C-007-frozen-adapter-cfg-diagnostics/

기존 연구 브랜치 단서:
docs/c-research-20261028
실제 현재 branch/worktree와 원격 상태를 확인한 뒤 사용한다.

권장 새 실험 경로:
docs/research/experiments/C-009-corrected-conditioning-retrain/

권장 의뢰서 보존 경로:
docs/research/work_orders/C009_CORRECTED_CONDITIONING_RETRAIN_KO.md


## 0. 목표와 이번 의뢰의 완료 기준

최종 연구 목표는 다음과 같다.

원본 영상 + 편집 지시 + 선택적 참조 이미지
→ 소수의 편집 앵커
→ 원본 동작과 편집 대상 외형의 연결
→ 개인 DGX Spark에서 실행 가능한 영상 편집

C-006은 점 궤적·가시성·앵커 특징을 전달하는 작은 adapter를
VACE 1.3B에 연결해 학습했으나 영상 품질이 회귀했다.

C-007은 CFG1에서도 회귀가 나타나고 낮은 sigma에서 오차가
증가함을 관측했다. 동시에 학습 cache와 실제 생성의
VACE context 불일치를 발견했다.

C-008은 원인을 확정했다.

학습 캐시 생성 코드:
Image.new('RGB', size, 255)

실제 생성된 중간 마스크:
(255, 0, 0)

의도한 마스크:
(255, 255, 255)

이 때문에 학습 시 조건 RGB의 R만 reactive 분기로,
G/B는 inactive 분기로 인코딩됐다.
실제 생성은 정상 흰색 마스크를 사용했다.

마스크를 명시적인 (v,v,v)로 바꾸자
독립 cache 경로와 실제 생성 경로가 elephant/goat에서 exact로 일치했다.
VAE 시간 cache·적재 형태·dtype 등을 이번에 다시 원인 탐색하지 않는다.

이번 질문은 하나다.

“잘못된 vace_context만 정상화하고
같은 초기 상태·자료·학습 설정으로 다시 학습하면,
기존 회귀가 줄어드는가?
그리고 화면 손상 감소를 넘어 실제 궤적 제어의 이득이 있는가?”

완료 범위:
1. 영향받은 조건 캐시 재생성.
2. 불변 필드·채널 계약·생성 입력 일치 확인.
3. 기존 step 0에서 256회 재학습.
4. 정상 조건에서 BASE/기존 adapter/새 adapter의 one-step 비교.
5. 새 ON/CFG1, ON/CFG5, NULL/CFG5 영상 생성.
6. 기존 BASE와 실제 품질·비용 비교.
7. 결과·해설·GitHub 기록·검토물 전달.

캐시 수정이나 loss 그래프만 만들고 끝내지 않는다.
안전하게 실행 가능한 경우 실제 영상 비교까지 수행한다.

이번은 확인된 입력 오류를 수정한 통제된 재실험이다.
새 아키텍처·새 학습 목적·새 논문 기여를 동시에 추가하지 않는다.


## 1. 새 세션 환경 인수

이전 Codex/Claude 세션의 shell 변수·SSH 연결·cwd·Python 환경이
현재 세션에 남아 있다고 가정하지 않는다.

먼저 확인:
- 현재 hostname·사용자·작업 디렉터리
- 저장소 root·remote·branch·HEAD·worktree
- 미커밋 변경과 현재 실행 중인 동일 실험
- CLAUDE.md·AGENTS.md 등 실제 적용 지침

기존 저장소와 연구 환경을 우선 찾는다.
처음부터 새 저장소·venv·실행기를 만들지 않는다.
과거 커밋으로 강제 reset하지 않고 다른 작업을 덮어쓰지 않는다.

현재 세션이 Spark에 있으면 SSH를 중첩하지 않는다.
다른 호스트라면 기존 SSH 설정에서 dgx-spark 또는 실제 사용 별칭을
확인하고 기존 인증으로 접속한다.

새 SSH 키·token을 만들거나 비밀값을 출력하지 않는다.
특정 Codex 전용 도구·MCP가 없어도 기존 git·SSH·Python으로
수행 가능한 경로를 사용한다.

C-006~008의 REPRODUCE·DELIVERY·실행 설정에서 다음을 찾는다.
- 실제 연구 Python
- 실제 DiffSynth 소스 경로
- VACE 1.3B·VAE·T5 가중치
- 기존 cache-v2와 cross-cache
- train-v2의 checkpoint-000/128/256
- updates.jsonl과 초기 학습 상태
- C-008의 수정된 validation cache·PARITY 기록
- C-007의 BASE/ON 영상·실제 입력 trace
- 기존 보호 실행 경로와 결과 전달 방식

과거 /tmp 파일이 없으면 DELIVERY가 가리키는 원본 보존 위치를 찾는다.
검토 ZIP 부재를 이유로 과거 생성·추적을 다시 돌리지 않는다.

동일 C-009가 이미 완료됐으면 중복 실행하지 않는다.
부분 완료라면 자기 작업의 새 캐시·checkpoint만 검증해서 이어간다.
과거 오류 조건의 checkpoint를 이어 학습하지 않는다.

환경 인수는 최소 범위로 끝낸다.
서비스·커널·가중치 전체 감사를 반복하지 않는다.

ecaa653은 착수 시 전체 commit SHA로 해석해 기록한다.
현재 HEAD가 더 뒤라면 기존 변경을 보존한다.


## 2. 읽을 근거와 기록 순서

C-008:
- RESULTS.md
- ROOT_CAUSE.md
- AFFECTED_ARTIFACTS.json
- REBUILD_MANIFEST.json
- PARITY.json
- 수정 마스크 helper와 회귀 테스트
- DELIVERY·REPRODUCE에 해당하는 실제 자료

C-006:
- DATA_SPLIT.json
- TRAIN_CONFIG.json
- METHOD.md
- 실제 train-v2 config와 실행 코드
- code/cache_conditions.py
- code/cross_cache.py
- code/train_adapter.py
- code/training_state.py
- code/point_adapter.py
- code/wan_adapter_forward.py
- point exclusion sidecar
- checkpoint·cache 계보

C-007:
- RESULTS.md
- INPUT_PARITY.json
- sigma/probe 구성
- CFG 설정이 실제 호출에 연결된 생성 코드
- validation용 inference whitelist sidecar
- BASE1/BASE5와 기존 ON1/ON5의 실제 설정·trace

읽기와 경로 확인 후, 신규 GPU 실행 전에 다음을 고정한다.
- 이 의뢰서
- PLAN
- 재생성 목록
- 학습 설정과 초기 상태
- 평가 모델·sigma·영상 세 셀
- 예산·기존 결과 재사용 기준

이를 commit하고 가능한 기존 원격에 push한 뒤 실행한다.
접근 장애가 있다면 local commit 시각과 push 지연을 기록한다.
실행 후 PLAN을 소급해서 사전 계획처럼 작성하지 않는다.

현재 변경에 관련된 파일만 명시적으로 stage한다.
다른 사용자 작업을 포함하는 무차별 git add -A는 하지 않는다.


## 3. 고정 범위와 금지 사항

유지:
- VACE 1.3B
- C-006 adapter 구조·parameter 수
- 학습 split·clip·point·exclusion
- 실제 양끝 이미지와 기존 편집 앵커
- 원본 동적 윤곽
- clean target latent
- endpoint patch
- T5 embedding
- loss mask
- 학습률·optimizer·loss·dropout·sigma 분포
- 생성 해상도·step·CFG·noise seed
- 기존 실행 가드

변경:
- 학습·진단 cache의 vace_context
- 캐시 생성에서 사용하는 RGB 마스크 생성 코드
- 새 캐시 계보와 이를 잘못 읽지 않게 하는 최소 검사
- 새 출력·checkpoint 경로

하지 않음:
- 14B 복구
- imagegen
- SAM·CoTracker·구조선 추출 재실행
- 새 데이터·모델·패키지 다운로드
- Torch/CUDA/DiffSynth upgrade
- adapter 구조·잔차 scale·학습 loss 변경
- 학습 횟수 탐색
- 새 prompt·seed·CFG 탐색
- 고해상도·보간·후합성
- 가드·service·allowlist 수정

과거 오류 캐시와 checkpoint는 역사 자료로 읽기 전용 보존한다.
기존 C-006/C-007 코드 파일을 수정해 역사적 재현을 깨지 않는다.
C-009용 작은 수정본이나 명시적인 적용 패치를 남긴다.


## 4. 데이터 분할과 재생성 목록

기존 원본 영상 단위 분할을 유지한다.

Train 8:
bear, blackswan, bmx-bumps, boat,
bus, camel, cows, dance-twirl

Validation 2:
elephant, goat

기존 test 2:
horsejump-low, lucia

기존 exploratory cross-ID:
C-001/C-002 dog와 기존 편집 앵커

이번 주 생성 평가는 elephant만 사용한다.
test와 cross-ID의 캐시는 정상화하지만,
해당 영상들을 새로 생성하거나 학습에 넣지 않는다.

재생성 대상:
- 주 cache 12개
- cross-cache dog 1개
- 각 자료의 vace_context만 교체

C-008의 정상 validation 두 개는
파일 hash·실제 조건·버전·입력 계보가 맞으면 재사용한다.
재사용 가능하면 기본 신규 인코딩은
나머지11개 context × inactive/reactive 2회 =22 encode다.

수정 validation 자료가 실제로 유실됐거나 계보가 맞지 않으면
두 개를 같은 확정 경로로 다시 인코딩할 수 있다.
그 경우 기본 재생성은26 encode이며 이유를 기록한다.
원인 규명 실험을 처음부터 반복하지 않는다.

12개 cache와 cross-cache의 실제 파일명·key는 기존 manifest를 따른다.
이 문서의 sequence 이름을 보고 임의 경로를 만들어 읽지 않는다.


## 5. 정상 마스크 계약과 캐시 재생성

### 5.1 확정된 마스크 생성

C-008에서 검증한 helper를 재사용한다.
논리적으로 다음 계약이다.

v = 0 if frame_index in (0,32) else 255
mask = Image.new('RGB', (416,240), (v,v,v))

기존 Image.new('RGB', size, v)의 단일 정수 fill을 사용하지 않는다.

공통 mask helper를 재사용할 수 있지만,
generation 경로는 원래 정상 helper를 그대로 유지한다.
양쪽을 같은 오류로 바꿔 맞추지 않는다.

각 실제 인코딩 직전에:
- shape33×240×416×3
- uint8 RGB
- R=G=B 전체 픽셀
- 양끝은 전 채널0
- 중간31장은 전 채널255
를 검사한다.

Normalize 이후 마스크가0/1이고 세 채널이 같은지도 확인한다.

회귀 테스트:
- 정상 tuple fill 통과
- 의도적으로 만든 legacy red fill은 세 채널 검사에서 실패
- 마스크 채널0이나 mask64만 비교하면 legacy가 통과할 수 있음을 확인

이 테스트를 위해 잘못된 cache를 GPU로 다시 만들지는 않는다.

### 5.2 재생성 입력

C-006/C-008과 같은:
- 원본 anchor/layout33장
- BF16
- tiled=True
- tile_size=(30,52)
- tile_stride=(15,26)
- vace_reference_image=None
- VACE 조건 encoder
를 사용한다.

source 중간 RGB를 layout 대신 넣지 않는다.
생성 마스크33→9 압축 로직은 변경하지 않는다.
새 앵커·후처리·prompt를 추가하지 않는다.

### 5.3 기존 필드 보존

원래 cache payload는 제한된 torch.load(weights_only=True)로 읽는다.
재생성 단계에서 point exclusion을 적용하는 학습용 load_cache를 호출해
patches·valid 등을 먼저 변경하지 않는다.

새 payload는 원본의 다음 key를 그대로 보존한다.
- clean_latent: 원래 존재하는 자료만
- patches
- positions
- visible
- valid
- anchor_valid
- box_wh
- context
- negative_context
- loss_mask: 원래 존재하는 자료만
- sequence·split·prompt 등 기존 메타데이터

vace_context만 새 tensor로 교체한다.
새 provenance는 별도 manifest에 기록하는 방식을 우선한다.

각 자료에서:
- 기존·새 key 집합
- vace_context 이외 tensor의 shape/dtype/byte hash
- 기존 비tensor 값
을 비교해 불변성을 확인한다.

test/cross-ID cache에 새 clean_latent를 추가하지 않는다.
원래 없는 정답 데이터를 편의상 넣지 않는다.

새 vace_context의 mask64가 기존과 같을 수 있다는 사실은 정상이다.
확인할 것은 전체96채널, 특히 두 RGB branch다.

새 cache는 별도 디렉터리에 원자 저장하고 readback한다.
원래 cache-v2를 덮어쓰지 않는다.
쓰기 가능한 공유 tensor나 덮어써질 symlink로 연결하지 않는다.


## 6. 인코딩 일치 검증은 기존 결과를 활용해 좁게 수행

C-008의 원인 규명과 causal VAE 검사를 전부 반복하지 않는다.
다음 세 가지만 새 실행에 연결한다.

1. 새 캐시 생성 직전의 마스크 세 채널 계약.
2. 새 validation cache와 실제 generation 준비 경로의 독립 일치.
3. 학습·생성 코드가 새 cache namespace를 실제로 읽는지 확인.

elephant/goat 각각에서 실제 생성 prepare 경로를 독립 실행한다.
최초 DiT forward 전에 VACE context를 얻고 정상 종료한다.

다음과 비교:
- 새 validation vace_context
- C-008에서 검증한 white-mask 결과
- elephant의 경우 C-007 저장된 실제 generation context

같은 장비·가중치·dtype에서 C-008은 exact였다.
우선 exact 일치를 기대하고, 다르면 허용오차를 늘리지 않는다.

불일치가 생기면:
- 실제 파일·mask 채널·입력 순서·import 경로 등
  새 연결 과정의 직접적인 오류만 먼저 확인한다.
- 수정 가능한 단순 오류는 같은 작업 안에서 고친다.
- 이미 확정된 temporal cache 가설부터 다시 탐색하지 않는다.
- 설명되지 않는 mismatch 상태에서 재학습을 강행하지 않는다.

전체 train/test/cross-ID에서 독립 generation 경로를 다시 돌리지 않는다.
각 자료의 채널·불변 필드 검사를 수행하고,
대표 두 validation의 독립 encoder 일치를 근거로 범위를 표시한다.

실제 학습 config가 원래 cache-v2로 되돌아가지 않았는지,
새 cache manifest ID와 읽은 파일 hash를 남긴다.

cache schema에 white-mask 계약 버전을 부여한다.
C-009 학습이 legacy red-mask cache를 읽으면 명확히 실패하게 한다.
이를 위해 새로운 데이터 플랫폼이나 캐시 관리 framework를 만들지 않는다.


## 7. 초기 상태 복원 — 기존 256회 상태를 이어 학습하지 않는다

사용할 시작 상태:
C-006 train-v2의 실제 checkpoint-000.

복원할 것:
- adapter 초기 parameter
- step0 optimizer 상태
- CPU RNG
- CUDA RNG
- 전용 sampling generator 상태
- train order
- cursor
- completed_updates=0

초기 projection뿐 아니라 MLP 초기 parameter도 같아야 한다.
같은 seed로 새 모듈을 만들었다는 설명만으로 대신하지 않는다.

기존 checkpoint128/256과 그 optimizer moment는
재학습 시작값으로 사용하지 않는다.
추가256회나 warm start는 이번 비교가 아니다.

복원 순서:
1. 필요한 모델·adapter·optimizer 객체 생성.
2. 새 cache/config를 연결.
3. 저장된 step0 parameter·optimizer·order/cursor 복원.
4. 학습 RNG를 복원.
5. 새로운 학습 시작.

캐시 재생성·진단·module 생성에서 소비된 RNG를
학습 RNG에 섞지 않는다.

원래 checkpoint의 config에 들어 있는 과거:
- output/cache 경로
- deadline
- elapsed time
- 완료 장부
를 실행에 그대로 적용하지 않는다.

런타임 경로·예산·새 계보만 새 값으로 바꾸고,
모델·학습 하이퍼파라미터와 random schedule은 유지한다.
허용한 runtime 차이를 별도 config diff에 남긴다.

새 C-009 step000을 저장하고,
원래 step000과 adapter 초기값·optimizer 초기 상태·RNG·cursor를 비교한다.

초기 checkpoint가 실제로 유실됐으면
정확한 재초기화가 가능하다고 꾸미지 않는다.
복구 가능한 기존 저장물을 먼저 찾고,
불가능하면 INIT_PARITY_UNAVAILABLE로 남긴다.
다른 초기화로 진행할 경우 이번의 동일 초기화 비교가 아니므로
추가 승인 없이 조용히 대체하지 않는다.


## 8. 학습 계약 — 캐시 외에는 C-006과 동일

기반 모델:
Wan2.1-VACE-1.3B
기록 revision:
574e6a744642ce3bee319afc31496b88bde8aac4

실제 기존 실행 환경과 checkpoint를 사용한다.
기록된 revision과 로컬 파일의 기존 검증 근거를 연결한다.

Adapter:
- 1,275,072 trainable parameter
- MLP303→192→192
- 네 projection192→1536
- DiT block26~29 앞의 기존 주입
- FP32 master
- 기존 kernel·정규화·시간 grouping
- 기존 point exclusion
- 구조 변경 없음

Frozen:
DiT·VACE·T5·VAE.

학습:
- 416×240,33frames
- batch1
- 256 optimizer update
- AdamW
- lr1e-4
- betas(0.9,0.999)
- weight_decay0.01
- grad_clip1.0
- BF16 backbone
- FP32 loss
- 기존 non-reentrant checkpointing
- SDPA
- train/data seed20261030
- null probability0.25
- negative-text probability0.10
- negative prompt:
  blurry, distorted, deformed, watermark

negative-text dropout은 기존과 같이
positive caption을 실제 negative embedding으로 교체하는 방식이다.
빈 문자열이나zero tensor로 바꾸지 않는다.

FM:
- Wan1000-step training grid
- shift5
- 추가 timestep weight1
- z_sigma=(1-sigma)z0+sigma*epsilon
- target=epsilon-z0

Loss:
객체 영역의 면적 정규화 MSE
+ 배경 영역의 면적 정규화 MSE
두 항 weight1:1.

이번에는 다음을 추가하지 않는다.
- 저sigma oversampling
- 새 noise schedule
- residual norm 제한
- base prediction 정규화
- CFG-aware loss
- pose·identity·flow·contact loss
- dropout 비율 변경
- block 위치 변경

낮은 sigma 회귀가 이미 관측됐다는 이유로
재학습 전에 그 부분까지 고치지 않는다.
이번에는 정상 캐시만 바꾼 결과를 먼저 본다.

매 update에서 새로운noise·sigma와 기존의 균형 clip 순서를 사용한다.
고정 tuple 반복 실험으로 축소하지 않는다.

원래 train-v2의 updates.jsonl과 비교해:
- step
- clip
- timestep/grid index
- NULL 여부
- negative-text 여부
의 schedule이 같은지 확인한다.

과거 noise tensor가 저장되지 않았다면
모든 과거 noise가 bitwise 같다고 주장하지 않는다.
복원한 generator와 동일 호출 순서로 재현한 범위를 명시한다.

새 로그·검사 때문에 학습 generator를 소비하지 않는다.
GPU 연산의 완전한 결정성을 확인하지 못한 부분은 별도로 남긴다.
동일 설정은 최종 학습 가중치가 기존과 같아야 한다는 뜻이 아니다.


## 9. Gradient·저장 검사는 기존 경로를 재사용

C-006에서 검증한 gradient 경로를 유지한다.

- adapter 이전 frozen prefix는 현재noisy input으로 계산.
- adapter 이후 마지막4개 block과 head는 gradient 통과.
- frozen weight의 업데이트는 없음.
- 기존 VACE hints 계산 순서 유지.
- 조건 cache와 noisy-state-dependent hidden을 혼동하지 않음.

현재 update의noise/sigma가 다른데
이전 prefix hidden을 재사용하는 최적화를 추가하지 않는다.

최소 검사:
- 정상 조건에서 native/bypass/zero-adapter의 일치
- optimizer에 adapter만 포함
- gradient finite
- projection과 MLP의 예상 gradient 연결
- 기존 frozen parameter 불변
- 신규 checkpoint 저장/readback
- 같은 probe에서 신규 checkpoint reload 일치

기존 구현의 검사와 허용오차를 재사용한다.
검사를 통과시키기 위해 사후 tolerance를 늘리지 않는다.
매 update마다 수GB의 backbone 전체hash를 반복 계산하지 않는다.

저장:
step000,128,256.

optimizer·RNG·generator·order·cursor·완료update를 함께 저장한다.
새 checkpoint에는 학습에 사용한 white-mask cache manifest를 연결한다.

최종 생성에는 마지막 완료 checkpoint를 사용한다.
validation/test 결과로 가장 좋아 보이는 checkpoint를 고르지 않는다.

256회 미완료라면 TRAIN_PARTIAL로 기록한다.
기존256회와 동일 학습량의 비교를 마쳤다고 쓰지 않는다.
새 작업의 마지막 정상 checkpoint에서만
누적256회 상한 안의 기계적 재개를 허용한다.


## 10. 수치 평가 — 같은 정상 조건에서 비교

### 10.1 원래 학습 중 validation 유지

C-006과 같이 step0/128/256에서:
- validation elephant/goat
- grid index200/500/800
- 기존 고정probe noise
- positive text·ON
을 사용한다.

기존과 같은 평가 절차를 유지하되
오류 캐시에서 나온 과거loss와 직접 차감해
“입력 수정 덕분에 몇% 향상”이라고 해석하지 않는다.

새 loss는 정상 조건에서의 값이다.
과거값은 오류 조건의 역사적 수치로 분리한다.

### 10.2 C-007형 확대 probe

재학습 후 다음을 고정한다.

입력:
elephant/goat의 정상 context.

sigma 목표:
0.95,0.75,0.50,0.20,0.05.

Text:
positive와 기존 negative.

모델:
1. BASE
2. OLD_ON_256: C-006 오류 조건 학습 checkpoint
3. NEW_ON_256: 이번 정상 조건 학습 checkpoint

총:
2×5×2×3=60 DiT forward.

같은 probe의 세 모델은 동일한:
- z_sigma
- target velocity
- text embedding
- 정상 VACE context
- point condition
을 사용한다.

source clean_latent는 재학습·이 probe에만 사용한다.
sampler에 전달하지 않는다.

실제 scheduler에서 가장 가까운sigma,
FP32 scheduler timestep,
실제 모델에 들어간BF16 timestep을 모두 기록한다.

C-007의고정probe seed와구성을 재사용한다.
단순히 같은숫자seed라고 과거 noisy tensor 일치를 추정하지 않는다.

보고:
- 객체 MSE
- 배경 MSE
- 두 항의 합
- 같은 정상 context에서의 BASE 대비 변화
- OLD_ON과 NEW_ON의 차이
- 낮은sigma 회귀의 잔존 여부

OLD_ON은 잘못된 조건에서 학습한 역사적 진단군이다.
정상 조건에서 학습한 방법과 동등하게 준비된 모델인 것처럼 표시하지 않는다.

양성·negative 예측을 재사용해 CFG 변화량을 계산할 수 있다.
이를 위해 추가forward를 만들지 않는다.
CFG조합과 unguided FM target의 차이를 곧바로 학습 오류로 부르지 않는다.

원래C-007의red-context probe 수치와
새white-context probe 수치를 직접 비교해
순수한학습개선으로해석하지않는다.


## 11. 실제 영상 — 기본 신규3개, 기존 BASE 재사용

영상 입력은 C-007 validation elephant 하나로 고정한다.
결과를 본 뒤 goat나 다른 사례로 바꾸지 않는다.

기존 재사용:
- C-007 BASE / CFG1
- C-007 BASE / CFG5
- C-007 OLD_ON / CFG1, CFG5는 역사적 비교 패널

신규:
1. NEW_ON / CFG1
2. NEW_ON / CFG5
3. NEW_NULL / CFG5

새 adapter는 최종256 checkpoint를 공통 사용한다.
NULL도 같은 checkpoint와 endpoint 특징을 사용한다.
NULL은 adapter OFF가 아니다.

ON과NULL은 기존 make_null 의미를 유지한다.
NULL에 source 중간 궤적·가시성을 다시 넣지 않는다.
두 조건의 동적 윤곽은 같으므로
NULL이 모든 동작 정보를 제거한 입력이라고 설명하지 않는다.

생성 설정:
- 416×240
- 33frames
- preview16fps
- source_fps=null
- Euler50
- sigma_shift5
- seed20261028
- rand_device=cpu
- BF16
- SDPA
- tiled VAE
- vace_scale1.0
- 같은prompt/negative
- 같은양끝·동적윤곽·G

CFG만 사전 계획의1 또는5다.
CFG1은positive branch를사용하는것이지무조건부생성이아니다.

실제 cfg_scale 인자가 pipeline에전달되는지확인한다.
CFG1은50 model_fn call,
CFG5는각100 model_fn call이기대된다.
생성기내sigma 선택은scheduler step index를기준으로한다.
CFG분기 call 수를생성step으로잘못세지않는다.

기본신규합계:
3 sampler,150 scheduler step,250 model_fn call.

### 11.1 기존 BASE 재사용 조건

기존 BASE와 다음이맞는지확인한다.
- 논리RGB·G
- 실제전체96채널VACE context
- text context
- noise tensor
- timestep/sigma grid
- sampler·precision·decode설정

처음model_fn에서관측한actual context를
새white cache와비교한다.
이번에는mask64만맞는것으로통과시키지않는다.

기존BASE 파일이나필수provenance가실제로유실돼
신뢰할수있는비교가불가능한경우에만
같은조건의BASE1/BASE5 최대2개재생성을허용한다.

이는대조군자료복구이지품질재시도가아니다.
왜재사용하지못했는지와추가비용을기록한다.

실제입력이의도와다르게변한경우에는
새BASE를만들어차이를덮지말고입력연결오류부터고친다.

### 11.2 생성의 정답 누출 차단

validation 원본cache에는clean_latent가있다.
이를그대로생성코드의point cache로넘기지않는다.

C-007의검증된inference whitelist sidecar를재사용한다.
자료를다시만들어야하면point/endpoint 관련허용key만복사한다.

sampler는실제pipeline이독립인코딩한정상VACE context를사용한다.
clean target latent는시작값·hint·feature로쓰지않는다.
clean_latent 부재assert를삭제해실행을통과시키지않는다.

생성원본latent를decode전에원자저장하고readback한다.
raw·전체33PNG·MP4를보존한다.

첫/마지막출력을앵커로덮어쓰지않는다.
후합성·색보정·SR·보간·얼굴보정은하지않는다.


## 12. 품질 판정 — 손상 감소와 동작 제어를 분리

source와모든비교결과를같은frame index로본다.
전체33장과고정0/4/8/12/16/20/24/28/32를포함한다.

C-007에서관측한사건을재사용한다.
- 코끼리의우측·멀어지는진행
- 관측가능한발의낮은위치·들림·다시내려오는순서
- source의실제먼지/물줄기등가림
- 건물·바위·나무보호
- 붉은파편·투명화·중복윤곽
- 양끝일치와종료부잔상

정확한해부학적좌우·관절·접촉GT는없다.
관측가능한사건으로만평가하고없는정답을만들지않는다.

반드시분리할비교:

A. NEW_ON ↔ OLD_ON, 같은CFG
정상조건재학습으로과거손상이얼마나줄었는가?

B. NEW_ON ↔ BASE, 같은CFG
새모듈이기반모델보다실제로도움이되는가?

C. NEW_ON ↔ NEW_NULL, CFG5
공유adapter·앵커특징이아닌실제중간궤적의추가이득이있는가?

D. NEW_ON CFG1 ↔ NEW_ON CFG5
CFG상호작용의관측.
BASE1/BASE5의차이도함께보고,
낮은CFG의변화를adapter개선으로혼동하지않는다.

ON이옛ON보다덜깨져도BASE보다나쁘면
“오류수정효과,방법추가이득미입증”이다.

NULL도비슷하게좋아지면
실제중간궤적의기여가확립됐다고하지않는다.

사전관측항목에대해
BETTER / SIMILAR / WORSE / UNCERTAIN을남긴다.
손상된출력의부위를억지로찾아정밀RMSE를만들지않는다.

실제연속시청을했다면검토주체·속도·범위를기록한다.
PNG·시트·ffmpeg decode·브라우저재생기능만확인했다면
temporal=UNVERIFIED를유지한다.

이번은validation 개발사례한개·한seed의재실험이다.
독립test일반화나논문성능으로확대하지않는다.


## 13. 완료 판정과 후속 결정

계산·자료 판정:
- WHITE_MASK_CONTRACT_VERIFIED
- CACHE_REBUILD_COMPLETE
- NONCONTEXT_FIELDS_UNCHANGED
- CACHE_LIVE_PARITY_VERIFIED
- INIT_PARITY_VERIFIED
- TRAIN_SCHEDULE_MATCHED 또는 제한 명시
- TRAIN_COMPLETE_256
- CHECKPOINT_RELOAD_VERIFIED
- MATCHED_GENERATION_COMPLETE

품질 판정은별도다.

CONDITION_FIX_REDUCES_DAMAGE:
과거adapter보다화면손상이줄었음.
동작이득은아직별도판단.

OBSERVED_TRAJECTORY_GAIN:
같은CFG에서NEW_ON이BASE와NEW_NULL보다
관측가능한동작을더잘따르고큰외형·장면회귀가없음.

COMMON_ADAPTER_GAIN_ONLY:
ON/NULL이비슷하게개선되어중간궤적의추가기여미입증.

TRADE_OFF:
동작일부이득과외형·장면손상동반.

NO_ESTABLISHED_GAIN:
정상조건재학습후에도기반모델대비이득미입증.

INCONCLUSIVE:
입력·학습완료·측정·대조군한계로판단어려움.

수정후낮은sigma 회귀가남으면다음연구후보로기록한다.
하지만이번안에서loss·sigma분포·residual scale을바꾸지않는다.

새결과가좋아도C-006/C-007을소급PASS로고치지않는다.
“오류조건학습의과거결과”와“정상조건재학습결과”를구분한다.

이번종료후에만다음중하나를제안한다.
- 독립영상·편집앵커확장검증
- 정상조건에서도남은잔차/학습문제진단
- 실제궤적활용이약한경우표현·주입구조개선

자동으로후속학습·새모듈·14B복구를시작하지않는다.


## 14. 실행 예산·중단·복구

### 기본 계산량

캐시:
- 정상validation2개재사용시신규22 public VAE encode
- 재사용불가시최대26 encode
- 두validation의독립generation prepare 검증4 encode
- 캐시/prepare 단계정상상한30 encode

위수와실제영상생성시의조건encode는분리기록한다.
새영상3개는통상inactive/reactive6 encode가추가된다.
공개VAE호출·내부tile/chunk·프레임수를혼동하지않는다.

학습:
- 누적256 update
- 학습forward/backward각256회
- 기존validation18 forward 예상
- 기존gradient/reload진단5 forward 예상
- 실제추가호출이있으면별도로기록

확대probe:
- 최대60 DiT forward

영상:
- 정상신규3 sampler
- 대조군자료복구가필요할때만최대2 sampler 추가
- 기계적실행복구예비1 sampler
- 따라서전체sampler상한6회

이미정상출력을얻은셀은재생성하지않는다.
품질재시도·다른seed탐색0회.

decode실패는저장된latent에서복구한다.
sampler를다시실행하지않는다.
VAE-only 기계복구는전체최대1회허용한다.

### 학습 시간과 부분 완료

원래active training상한9000초를유지한다.
그상한에도달하면checkpoint를저장한다.
256회미달이면동일학습량비교미완료로기록한다.

전체작업범위상한4시간.
마지막30분은평가·전달·종료에남긴다.
이는승인된계산범위이지실행시간예측이나완료보장이아니다.

과거실행은짧았더라도현재상태의속도를보장하지않는다.
보조검사·문서화만늘려실제학습과비교를계속뒤로미루지않는다.

### 운영 규칙

기존정상보호경로·Python·모델을재사용한다.
새가드·실행기·운영정책을만들지않는다.

PSI·headroom·worker swap·외부GPU·서비스보호를완화하지않는다.
과거시스템swap-out 절대0 분기를복원하지도않는다.

단순경로·인자·device·import오류는같은작업안에서수정한다.
안전중단·OOM·외부작업충돌은자동우회하지않는다.

학습기계복구는C-009의마지막정상checkpoint에서
누적256회범위로만한다.
오류조건의옛checkpoint256으로대체하지않는다.

checkpoint·cache·진단·생성사용량을분리해서보고한다.
“heavy몇회”만으로실제학습·추론량을숨기지않는다.


## 15. 한국어 수식·코드 해설

실제수정과관측에연결된LESSON_KO.md를작성한다.

핵심기호:
c_bad = red-mask 조건cache
c_good = white-mask 조건cache
psi_0 = 동일adapter 초기값
psi_bad = 기존오류조건학습결과
psi_good = 이번정상조건학습결과

학습비교:
psi_bad = Train(psi_0, c_bad, 고정학습schedule)
psi_good = Train(psi_0, c_good, 같은학습schedule)

실제비교는같은c_good에서수행한다.
v_base(z,sigma,c_good)
v_(psi_bad)(z,sigma,c_good)
v_(psi_good)(z,sigma,c_good)

설명할것:
1. 마스크세채널오류가inactive/reactive를어떻게바꿨는가.
2. mask64가같아도전체조건은왜다를수있는가.
3. vace_context만바꾸고다른필드를유지하는이유.
4. 왜256회에서이어학습하지않고같은step0에서시작하는가.
5. seed동일성과실제RNG·cursor·호출순서동일성의차이.
6. 서로다른조건에서계산한과거/새loss를직접비교하면안되는이유.
7. 화면손상감소와point-motion 추가이득의차이.
8. BASE/ON/NULL이각각분리하는효과.
9. 낮은sigma 회귀가수정후에도남을수있는이유.
10. validation개발비교와새held-out일반화평가의차이.

새연구기법을발명한것처럼오류수정을포장하지않는다.
정상입력에서방법가설을평가할수있게되었다는의미로설명한다.

직관→수식→실제함수/값→관측→한계순서로쓴다.
짧은이해확인질문과답을붙일수있지만이론을과도하게반복하지않는다.


## 16. 산출물·전달·최종 보고

필수기록을기존스타일로간결하게남긴다.

- PLAN.md
- CACHE_REBUILD.json
- PARITY.json
- TRAIN_CONFIG.json
- TRAIN_REPLAY_CHECK.json
- RESULTS.md
- COSTS.json
- LESSON_KO.md
- REPRODUCE.md
- DELIVERY.json

계산량·예산·수동검토시간은실제로측정한값만기록한다.
미측정값은null과이유로둔다.
새연구번호를CPU오류마다늘리지않는다.

보존:
- 정상cache13개와원본계보
- 불변필드검증
- 새checkpoint0/128/256
- optimizer/RNG/cursor
- 새학습로그
- 정상context의60probe
- 신규영상final latent/raw/전체33PNG/MP4

검토뷰어:
SOURCE / 기존BASE1·BASE5 /
기존OLD_ON1·OLD_ON5 /
NEW_ON1·NEW_ON5·NEW_NULL5.

화면을한꺼번에과도하게작게만들기보다
같은CFG와ON/NULL을쉽게비교할수있는탭또는모드로구성한다.
전체33프레임과고정시트·실제재생을제공한다.

OLD_ON은“오류조건으로학습한역사적결과”로표시한다.
BASE는정상generation기준선임을표시한다.
새영상을만들지못한셀은NOT_RUN으로남긴다.

compact:
- 원생성MP4
- 필요한source/앵커
- 작은비교시트·뷰어
- 결과·해설·재현자료

대형cache·optimizer·raw·latent는별도비공개보존한다.
모델가중치·과거전체ZIP을중복포장하지않는다.
생성MP4화질을낮춰용량을맞추지않는다.
새비교MP4/thumbnail은파생물로표시한다.

Spark/Mac의실제/tmp또는기존승인된전달경로에보존한다.
파일날짜는실제작업날짜를쓴다.
한호스트에접근못했다면양호스트동일성PASS를주장하지않는다.

검증:
- 크기·SHA256
- ZIP CRC
- manifest
- 실제추출
- 가능한호스트간전송동일성

공개Git에는비민감코드·문서·필요hash만게시한다.
원본/생성미디어·개인경로·token·PID·cache·latent·가중치는
자동으로공개하지않는다.

HISTORY/ROADMAP에는
오류조건의과거실험과정상조건재학습을구분해연결한다.
모든과거판정은보존하고해석변경을추가한다.

최종보고는아래질문부터답한다.

1. 13개조건cache중무엇을재생성·재사용했는가?
2. vace_context 외의자료와초기학습상태가유지됐는가?
3. 같은256회학습이실제로완료됐는가?
4. 정상조건에서낮은sigma 회귀가줄었는가?
5. 새영상의색번짐·중복윤곽은줄었는가?
6. NEW_ON이BASE와NEW_NULL보다실제동작을잘따르는가?
7. 외형·장면손상은남거나새로생겼는가?
8. 다음은확장검증인가,정상조건에서도남은방법문제의수정인가?

실제영상·판정·비용을먼저제시한다.
검사개수·hash·전송상세는근거로뒤에둔다.

자체프로세스종료와다른작업보존을확인한다.
commit/push와연구브랜치원격일치를확인한다.
이후자동학습·추가생성·14B재개는하지않는다.


## 참고 근거

C-008 원인·영향·재생성:
https://github.com/hyunlord/make-meme/tree/ecaa653/docs/research/experiments/C-008-conditioning-parity

C-006 원래 학습·초기 상태·설정:
https://github.com/hyunlord/make-meme/tree/c4aef32de21de4073bd4eb1861df4d35f2eda793/docs/research/experiments/C-006-motion-point-adapter-pilot

C-007 정상 생성 기준선·probe:
https://github.com/hyunlord/make-meme/tree/19e110431e90931c98277b7e94d6879268929336/docs/research/experiments/C-007-frozen-adapter-cfg-diagnostics

위자료의존재를현재로컬파일검증으로대신하지않는다.
실제사용한commit·파일·경로·입력계보를확인하고진행한다.
