# C-008 통합 작업 의뢰서
# 새 Claude Code 세션용 — VACE 조건 인코딩 불일치 규명·최소 수정
#
# 대상 저장소: hyunlord/make-meme
# 실행 장비: 기존 DGX Spark
# 역할: 새 세션에서 연구 작업을 인수하는 Claude Code
#
# 이 문서는 이전 대화 없이 착수할 수 있도록 작성한 전체 의뢰서다.


## 0. 작업을 인수할 때의 기본 원칙

너는 기존 연구를 처음 인수하는 Claude Code 세션이다.

이전 Codex/Claude 세션의 메모리, shell 변수, 열린 SSH 연결,
작업 디렉터리, Python 환경, 실행 중인 프로세스가
현재 세션에도 유지되어 있다고 가정하지 않는다.

이 문서를 단순히 요약하거나 계획만 작성하는 것으로 끝내지 말고,
사용 가능한 기존 환경에서 아래 범위의 실제 작업을 수행한다.

다만 다음은 구분한다.

- 이전 환경을 찾아 연결하는 데 필요한 최소 확인
- 실제 연구 대상인 조건 인코딩 불일치의 재현·수정
- 이번 범위 밖인 실행기·가드·서비스 재설계

첫 번째 확인을 마치면 두 번째로 바로 진행한다.
세 번째를 새 프로젝트로 시작하지 않는다.

이번 의뢰의 실행 권한은 다음에 한정된다.

- 기존 저장소·연구 자료·실행 코드 읽기
- 기존에 구성된 인증과 SSH를 사용한 Spark 접속
- C-008용 진단 코드·문서·최소 수정 작성
- 정해진 예산 안의 VAE 인코딩·검증
- 조건을 충족할 때만 제한된 DiT 진단과 영상 생성
- 기존 연구 브랜치의 작업 기록·commit·push
- 기존 방식의 Spark↔Mac 결과 전달

별도 승인 없이 하지 않을 것:

- 새로운 모델 학습
- 14B 모델 실행·복구
- imagegen 호출
- 새 모델·데이터·패키지 다운로드
- Torch/CUDA/driver 교체
- 기존 안전 가드·메모리 한도 완화
- 다른 작업·서비스·프로세스 종료
- 원격 기본 브랜치 강제 변경
- 과거 기록·가중치·캐시 삭제 또는 덮어쓰기

이 범위 안의 단순 경로·인자·import 오류는 같은 작업 안에서 수정한다.
단순 오류마다 새 의뢰서나 새 실험 번호를 요구하지 않는다.

실제 접근 권한 부재, 인증 실패, 안전 중단, 자료 유실처럼
현재 도구로 해결할 수 없는 전제는 명확히 보고한다.
존재하지 않는 환경이나 파일을 추정해 실행하지 않는다.


## 1. 전체 연구 목표와 현재 위치

### 최종 목표

입력:
- 원본 영상
- 편집 지시 텍스트
- 선택적 대상 참조 이미지

처리:
- 소수의 편집 앵커 생성
- 원본 객체의 움직임과 편집 객체의 외형 연결
- 로컬 영상 모델로 중간 프레임 생성
- 오류 원인에 맞는 제한적 수정
- 필요할 때 고해상도 복원

목표:
개인 DGX Spark 수준의 장비에서
대상 외형·원본 동작·보호 장면을 함께 유지하는 영상 편집 방법을
수식·구조·학습·실험으로 연구한다.

현재는 특정 개인의 반려견만을 위한 시스템이 아니라,
여러 객체와 영상에 적용 가능한 방법을 연구한다.
새 개인 사진 제공을 이번 작업의 필수 조건으로 삼지 않는다.

### 최근 연구 이력 요약

C-001:
imagegen으로 만든 양끝 앵커와 VACE 1.3B로 실제 영상을 생성했다.
외형은 일부 유지됐으나 원본 중간 동작 보존이 부족했다.

C-002:
SAM의 시간별 윤곽을 실제 영상 조건에 연결했다.
거친 접근·방향 변화는 일부 개선됐지만,
정확한 내부 동작과 보호 장면은 해결되지 않았다.

C-003:
객체 내부 구조선을 추가했으나 추가 이득은 미입증이었다.

C-004:
종료 앵커를 한 번 교정했으나 동작 개선은 미입증이었다.

C-005:
14B 비교를 시도했으나 모델 적재 중 기존 PSI 안전 기준으로 중단됐다.
14B 품질은 미평가다.
이번 C-008에서 이 작업을 복구하지 않는다.

C-006:
VACE 1.3B에 작은 Point–Anchor Adapter를 연결하고 실제 학습했다.
127만여 parameter, 256 update, BASE/ON/NULL 영상 9개를 비교했다.
동작 이득은 미입증이고 ON/NULL에 색 번짐·중복 윤곽이 증가했다.

C-007:
저장된 adapter를 동결하고 CFG1/CFG5 및 여러 sigma에서 진단했다.
CFG1에서도 ON이 BASE보다 회귀했다.
낮은 sigma의 one-step 오차 증가도 관측됐다.
동시에 학습·진단 cache와 실제 생성의 VACE context가 다름을 발견했다.

### 현재 우선순위

새 adapter 구조나 학습 목적을 바꾸기 전에,
학습과 생성에 실제로 같은 의미의 조건이 전달되는지 확인한다.

이번 C-008은 운영 환경 연구가 아니라
모델 입력의 계산 정확성을 확인하는 연구다.


## 2. 반드시 확인할 기준 저장소·커밋·문서

저장소:
https://github.com/hyunlord/make-meme

직전 실험 기준 커밋:
19e110431e90931c98277b7e94d6879268929336

직전 실험 경로:
docs/research/experiments/C-007-frozen-adapter-cfg-diagnostics/

학습·캐시 기준 커밋:
c4aef32de21de4073bd4eb1861df4d35f2eda793

학습·캐시 경로:
docs/research/experiments/C-006-motion-point-adapter-pilot/

참고 DiffSynth 기록 revision:
f39d731a3e318d25b725eb3389cfddb184619842

새 실험 권장 경로:
docs/research/experiments/C-008-conditioning-parity/

전체 의뢰서 권장 보존 경로:
docs/research/work_orders/C008_CONDITIONING_PARITY_CLAUDE_FRESH_SESSION_KO.md

읽을 핵심 자료:

C-007:
- RESULTS.md
- INPUT_PARITY.json
- REPRODUCE.md
- DELIVERY.json
- 실제 진단·생성·replay 코드
- 저장된 실제 VACE context의 계보

C-006:
- METHOD.md
- TRAIN_CONFIG.json
- DATA_SPLIT.json
- REPRODUCE.md
- DELIVERY.json
- code/cache_conditions.py
- code/runtime_common.py
- code/point_features.py
- code/generate_video.py
- code/wan_adapter_forward.py

상위 연구 기록:
- 실제 존재하는 CHARTER 또는 연구 목표 문서
- HISTORY
- ROADMAP
- 현재 적용 중인 실행·보호 경로

실제 설치된 DiffSynth:
- WanVideoUnit_VACE.process
- WanVideoVAE.encode / tiled_encode
- 내부 VideoVAE_.encode / clear_cache
- CausalConv3d
- 시간 downsample과 feature cache 전달
- VAE 적재·래핑·normalization 경로

문서명이 다르거나 파일이 이동했다면 실제 tree와 참조를 따라간다.
추측한 파일명을 계속 호출하며 시간을 쓰지 않는다.

현재 HEAD가 위 커밋보다 뒤에 있을 수 있다.
위 커밋은 연구 근거이며 강제 checkout/reset 지시가 아니다.

기록 revision과 실제 실행 소스가 같다고 자동 가정하지 않는다.
실제로 import된 파일·클래스·관련 파일 hash를 실행 근거로 남긴다.


## 3. 새 세션의 환경 인수 절차

### 3.1 현재 실행 위치 확인

먼저 다음을 확인한다.

- 현재 hostname과 사용자
- 현재 작업 디렉터리
- 현재 디렉터리가 Git 저장소 안인지
- 저장소 루트·remote·branch·HEAD
- 미커밋 변경과 등록된 worktree

저장소에 있는 CLAUDE.md, AGENTS.md 등
현재 작업에 적용되는 지침을 읽는다.

처음부터 새 저장소를 clone하거나 새 Python 환경을 만들지 않는다.
이미 존재하는 make-meme 저장소와 연구 worktree를 우선 찾는다.

현재 저장소가 다른 프로젝트라면
사용자가 제공한 작업 경로와 기존 연구 문서의 경로를 우선 확인한다.
전체 파일시스템을 무제한 검색하지 않는다.

기존 미커밋 변경은 덮어쓰거나 정리하지 않는다.
충돌이 없다면 기존 연구 경로에서 진행한다.
분리가 필요하면 같은 저장소의 별도 worktree를 사용할 수 있지만,
가중치·venv·대형 cache를 복제하지 않는다.

commit할 때는 이번 변경 파일만 명시적으로 stage한다.
다른 작업까지 포함하는 무차별 git add -A를 하지 않는다.
push는 확인된 연구 브랜치에만 수행한다.


### 3.2 Mac·Spark 구분과 SSH

과거 기록에는 다음이 등장했다.

- Spark SSH 별칭: dgx-spark
- Mac 연구 산출물 상위 경로 예:
  /Users/rexxa/research/make-meme-b/
- 검토 자료 예:
  /tmp/C007-review-20261030.zip
  /tmp/C007-review-20261030/index.html

이들은 인수 단서이며 현재 세션에서 존재한다고 보장된 값은 아니다.
Mac 산출물 경로를 저장소 루트로 간주하지 않는다.
과거 로그의 /root/c003_execution 등을 새 작업 디렉터리로 단정하지 않는다.

현재 세션이 이미 Spark에서 실행 중이면 SSH를 중첩하지 않는다.

Mac 등 다른 호스트라면:
- 기존 SSH 설정에서 dgx-spark 또는 실제 사용한 별칭 확인
- 기존 인증을 사용하는 비대화형 연결로 hostname·사용자·현재 경로 확인
- 접속 결과와 연구 기록이 가리키는 장비가 맞는지 확인

새 SSH 키를 만들거나 인증 설정을 덮어쓰지 않는다.
사용자 비밀번호·private key·token을 출력하거나 문서에 넣지 않는다.
인증 실패를 우회하지 않는다.

로컬에 GitHub 플러그인이나 MCP가 없더라도
기존 Git remote와 git CLI로 자료를 읽을 수 있으면 그것을 사용한다.
특정 Codex 전용 도구의 존재를 전제로 삼지 않는다.


### 3.3 Python·모델·실행 경로 찾기

C-007/C-006의 REPRODUCE, 실제 실행 설정, 기존 worker 명령에서
다음의 정확한 경로를 찾는다.

- Spark 저장소/worktree
- 실제 연구 Python executable
- 실제 import되는 DiffSynth 디렉터리
- 기존 VACE 1.3B·VAE·T5 가중치
- C-006 train/validation cache
- C-007 실제 생성 context·trace
- 공통 보호 실행기와 현재 승인된 정책
- 결과를 Mac으로 전달한 기존 방법

이 값을 이번 세션에서 직접 확인한다.
새 shell의 PATH나 이전 세션의 환경변수에 의존하지 않는다.
worker에는 확인된 절대경로를 사용한다.

사용자·호스트·private path는 비공개 실행 설정에 둔다.
공개 GitHub 문서에는 필요한 상대경로와 역할만 남긴다.

환경 확인은 실제 실행에 필요한 범위로 한정한다.
커널·서비스·모든 가중치에 대한 전체 감사를 반복하지 않는다.

새 세션이라는 이유로:
- Torch/CUDA/driver 업그레이드
- 가드 초기화
- systemd 서비스 재작성
- venv 재설치
- 모델 재다운로드
를 하지 않는다.


### 3.4 /tmp 자료가 없을 때

/tmp는 임시 위치이므로 없을 수 있다.

검토 ZIP이 없다면:
1. 저장소의 DELIVERY/REPRODUCE 기록 확인
2. Spark의 원본 산출물·cache 보존 위치 확인
3. 필요한 파일만 사용

검토 ZIP 하나가 없다는 이유만으로
기존 모델 생성이나 SAM 분석부터 재실행하지 않는다.

필수 tensor와 그 계보가 실제로 유실됐다면
어떤 자료가 없고 어느 검증이 불가능한지 정확히 남긴다.
새 세션에서 임의로 대체 자료를 만들어
과거 실행의 원본인 것처럼 취급하지 않는다.


## 4. 이번에 재현할 알려진 불일치

C-007 보고서의 인수 정보는 다음과 같다.
아래 값은 과거 관측이며 이번 실행에서 재확인해야 한다.

같았던 것:
- source/anchor/layout의 실제 RGB
- 생성 여부 마스크
- positive/negative text context
- VACE mask 64채널
- 생성 네 셀 사이의 noise와 VACE context

달랐던 것:
- C-006 학습·진단 cache의 VACE context
- C-007 실제 생성 경로의 VACE context

기록된 차이:
- 전체 context RMS: 약0.766806
- 전체 max_abs: 6.421875
- inactive16채널 RMS: 약1.47018
- reactive16채널 RMS: 약1.16898
- mask64채널: exact
- RGB 특징의 시간 latent0: exact
- RGB 특징의 시간 latent1~8: mismatch

예상 context shape:
[1,96,9,30,52]

중요:
“첫 시간 latent가 같다”와
“첫 영상 프레임을 제외한 모든 것이 틀렸다”는 같은 말이 아니다.
latent 시간 압축과 receptive field를 구분한다.

이번 원인 규명 대상:
위 mismatch가 발생한 최초 경계와 실행상의 원인.

미리 확정하지 않을 것:
- cache reset 누락
- BF16 오차
- inference_mode 문제
- 가중치 차이
- 잘못된 저장물
- adapter 문제
- CFG 문제

증거에 따라 판단한다.


## 5. 고정 입력·설정과 변경 금지 범위

우선 원인 규명:
validation elephant

독립 검증:
validation goat

기존 train/test 분할은 변경하지 않는다.
horsejump-low·lucia·기존 개 편집은 이번 주 생성 대상으로 쓰지 않는다.

고정:
- 기존 VACE 1.3B와 VAE 가중치
- 416×240
- 33프레임
- 기존 실제 시작·종료 앵커
- 기존 중간 동적 윤곽
- G: 양끝 전체0, 중간 전체255
- vace_reference_image=None
- 기존 prompt·negative prompt
- BF16
- tiled=True
- tile_size=(30,52)
- tile_stride=(15,26)
- 기존 VAE scale·normalization
- context 채널 순서

기존 mask33→9 압축 방식은 이번 수정 대상이 아니다.
endpoint clamp, 앵커 덮어쓰기, 새로운 조건 RGB를 추가하지 않는다.

기존 checkpoint0/128/256, cache와 원본 trace는 읽기 전용으로 보존한다.
새 자료는 C-008의 별도 이름공간에 저장한다.

학습용 저장 cache와 VAE 내부의 temporal feature cache는 다른 개념이다.
로그와 해설에서 둘을 혼동하지 않는다.


## 6. 세 인코딩 경로 정의

C — CACHE 경로:
C-006 cache_conditions.py가 실제 사용한
적재·VACE unit 호출·인코딩·저장 경로.

G — GENERATION 경로:
C-007 실제 생성의
적재·pipeline unit 순서·VACE 인코딩 경로.

R — 의미 검증용 REFERENCE 경로:
최초 불일치가 좁혀진 뒤,
같은 가중치·입력·정밀도와 의도된 causal 시간 처리를 확인하기 위한
최소 기준 경로.

C와 G를 처음부터 하나의 helper로 바꾸지 않는다.
원래 차이가 무엇인지 먼저 재현해야 한다.

G는 실제 준비 경로를 수행한 뒤
denoising 직전에 정상적으로 조건을 반환하는 prepare-only 경로를 쓴다.

- 모델 초기화 형태가 원인일 수 있으므로 실제 차이를 먼저 보존한다.
- 필요한 경우 기존1.3B 전체 초기화를 재현할 수 있다.
- 그러나 진단 단계에서 DiT forward나 sampler를 시작하지 않는다.
- num_inference_steps를 임의로0이나1로 바꿔 준비 경로를 달리하지 않는다.
- 의도적 예외로 worker를 실패 처리하기보다 작은 정상 반환 분기를 사용한다.
- 새 launcher나 supervisor를 만들지 않는다.

R은 더 보기 좋은 영상을 만든 경로를 고르는 것이 아니다.
의도된 encoder 계약과 실제 코드 의미를 근거로 정의한다.
공식 코드라는 사실만으로 무조건 올바르다고 가정하지 않는다.


## 7. 최초 불일치 경계를 앞에서부터 찾는다

P0. 디코딩된 RGB·mask·프레임 순서
P1. preprocess_video 이후 normalized tensor
P2. inactive / reactive 분리 tensor
P3. VAE wrapper에 전달된 입력·옵션
P4. 실제 공간 tile·시간 chunk 입력
P5. chunk별 이전 feature cache·출력
P6. mu와 normalization 전후 값
P7. tile 합성 후 branch latent
P8. 최종 VACE context
P9. 저장 전·읽기 후·model_fn 직전 값

같다고 확인된 앞단을 매번 전부 덤프하지 않는다.
차이가 시작되는 곳에서 조사 범위를 좁힌다.

각 경계에서 필요한 기록:
- shape·dtype·device
- 축 의미·프레임 순서
- finite·min·max
- 정확한 tensor hash
- max_abs·RMS
- reference 자체 RMS와 상대 오차
- 필요한 시간별 차이

분모가 거의0인 상대 오차는 null과 이유로 남긴다.
큰 비율 하나만으로 큰 의미 손상이라고 단정하지 않는다.

최종 context는 분리해서 비교한다.
- inactive:0:16
- reactive:16:32
- mask:32:96
- 시간 latent0~8

실제 인코더 입력과 파일 픽셀을 구분한다.
PNG가 같다는 이유만으로 normalized tensor도 같다고 선언하지 않는다.

관측은 detach 후 필요한 범위를 clone해서 남긴다.
공유 view나 mutable cache의 참조를 저장해
나중 값이 바뀌는 것을 관측값으로 쓰지 않는다.

hook은 입력·cache·RNG·출력을 수정하지 않는다.
관측 활성화 여부로 결과가 바뀌면
모델 수정 전에 관측 코드의 간섭부터 해결한다.

대형 activation 전체를 무제한 저장하지 않는다.
처음에는 경계별 요약과 최종 latent를,
이후에는 최초 차이가 나는 소수 chunk/layer만 보존한다.


## 8. 최소 재현과 원인 조사 순서

### 8.1 네 가지 비교

elephant에서 다음을 확인한다.

- C_new ↔ C_old
- G_new ↔ G_old
- C_new ↔ G_new
- 같은 경로의 반복 실행 ↔ 반복 실행

과거 결과와 현재 결과를 구분한다.

현재 C와 G가 같고 과거 cache만 다르면:
과거 provenance·설정·코드·저장물을 먼저 조사한다.

현재도 C와 G가 다르면:
최초 불일치 경계의 실행 상태를 조사한다.

현재 반복 실행 자체가 다르면:
그 변동 범위와 조건을 먼저 측정한다.
모든 차이를 경로 차이라고 분류하지 않는다.

VAE가 deterministic mu를 사용하는지 실제 실행을 확인한다.
VAE라는 이름만으로 posterior random sampling을 가정하지 않는다.


### 8.2 입력이 같을 때 조사할 후보

A. 실제 모델 객체·호출
- import된 클래스와 wrapper
- 실제 호출되는 encode/forward
- module dispatch·monkeypatch
- cache 전용 적재와 full pipeline 적재의 차이
- 가중치·buffer·scale의 실제 적용

B. 시간 처리
- 독립 encode 시작의 내부 상태
- 첫1프레임과 이후4프레임 chunk 범위
- chunk별 convolution index
- 이전 특징의 길이·dtype·device·전달 위치
- wrapper로 인한 causal module 판별 차이
- mutable default의 실제 영향

C. 실행 모드
- module.training
- grad_enabled
- inference_mode
- autocast
- 실제 연산 dtype
- requires_grad 상태

D. 공간·저장 처리
- tile 좌표·개수·경계
- tile 내부와 합성 이후의 차이
- in-place 변경·storage alias
- 저장·읽기 시 값이나 dtype 변화
- 잘못 연결된 파일·stale cache

E. 수치 구현
- 위 요소가 같을 때 kernel·반복 수치 차이 검토

모든 후보의 조합을 탐색하지 않는다.
관측과 코드에 근거가 있는 후보 하나씩만 개입한다.


### 8.3 호출 이력 진단

시간 cache가 관련될 근거가 있으면 제한적으로 수행한다.

- 같은 객체에서 A → A
- A → 시작1프레임 → 종료1프레임 → A
- 필요할 때 A → B → A
- 필요할 때 새 VAE instance의 A

A는 elephant, B는 goat의 고정 입력이다.

과거 cache 생성에서 여러 영상이 처리된 순서가 중요할 수 있다.
필요한 앞선 호출만 재현하고 전체 데이터 작업을 다시 돌리지 않는다.

관련 원격 코드에는 encode 시작의 clear_cache가 이미 있다.
실제 실행에서도 호출되는지와 그 이후 상태 전달을 확인한다.

독립 영상의 reset과
같은 영상의 chunk 사이에 필요한 기억은 다르다.

매 chunk마다 clear_cache를 호출해
두 경로를 똑같이 잘못 계산하게 만드는 수정은 금지한다.


## 9. 원인 확인 후의 최소 수정

원인 확인의 근거:

1. 기존 mismatch 재현
2. 마지막으로 같았던 경계와 최초로 달라진 경계 특정
3. 해당 코드·상태 차이 설명
4. 한 가지 개입으로 차이 제거 또는 설명
5. 독립 호출·두 번째 영상에서 재검증

가능하고 안전하다면 격리된 진단 분기에서
수정 전 동작을 다시 켰을 때 차이가 돌아오는지도 확인한다.

단, 과거 환경을 완전히 재현할 수 없으면
확인한 범위와 남은 UNKNOWN을 구분한다.

허용하는 수정:
- 잘못된 전처리·인자 전달
- 상태 생존·reset 위치
- 입증된 wrapper/module dispatch 오류
- dtype·실행 모드 계약 불일치
- 잘못된 파일·stale cache 연결
- 직렬화·alias 문제

허용하지 않는 수정:
- 원인 미확정 상태의 큰 리팩터링
- 최신 버전으로 교체해 문제를 덮기
- adapter·CFG·학습 목표 변경
- 임의 latent 보정이나 평균화
- 한쪽 context를 다른 쪽에 그대로 복사
- 허용오차를 크게 늘려 PASS 처리
- 안전 정책·offload 정책의 근거 없는 변경

관련 계산을 작은 공통 함수로 추출하는 것은
원인이 확인되고 재발 방지에 필요한 경우에만 허용한다.

공유 환경의 site-packages를 무기록으로 수정하지 않는다.
저장소에 작은 patch 또는 명시적인 적용 경로와 diff를 남긴다.
실제 실행에 적용된 파일·버전을 재확인한다.

변경 후 두 경로가 같은 helper를 독립 실행하는 것은 가능하다.
한 번 계산한 tensor를 공유한 결과를 독립 검증이라고 하지 않는다.


## 10. 경로 일치와 encoder 의미를 별도로 검증한다

### 10.1 경로 일치

수정 후 elephant·goat에서 각각:
- C 경로의 새 인코딩
- G 경로의 새 인코딩
을 독립적으로 수행한다.

실제 초기화 경계 또는 process를 분리해
동일 메모리 객체를 공유한 결과가 아니게 한다.

같은 조건에서 반복 결과가 exact이면 exact equality를 사용한다.
반복 수치 차이가 있으면:

- 같은 경로의 변동을 먼저 측정
- 경로 간 차이를 그 범위와 비교
- tolerance 선택 이유 기록
- EXACT와 NUMERIC_PARITY 구분

C-007의 큰 mismatch를 덮을 허용오차는 사용하지 않는다.
비교 기준을 세울 근거가 부족하면 PARITY_INCONCLUSIVE다.


### 10.2 encoder 의미

실제 causal encoder가 제공해야 하는 계약을 확인한다.

가능한 최소 검사:
- 첫 프레임 단독 encode와 전체 encode의 첫 시간 latent
- 지원되는 prefix 길이1/5/33의 공통 prefix
- 뒤쪽 입력 변화가 이전 시간 latent에 미치는 영향
- 다른 독립 영상 호출 전후의 결과
- 독립 공간 tile 사이의 상태 분리

공간 tile·padding·dtype 등 비교 조건을 맞춘다.
원래 계산 의미가 다른 두 경로에 무조건 exact를 요구하지 않는다.

특히 first/prefix 검사를 할 때:
입력 길이에 따라 달라지는 정당한 padding·chunk 처리와
의도치 않은 과거·미래 정보 누출을 구분한다.

두 경로가 같아져도 의미 검증이 부족하면:
PARITY_ONLY / SEMANTICS_UNVERIFIED
로 기록한다.

이 경우 기존 학습 자료가 정상이라고 자동 승격하지 않는다.


## 11. 학습 자료의 영향 범위를 구분한다

elephant·goat에서 다음을 각각 확인한다.

A. VACE context
- inactive
- reactive
- mask64

B. clean target latent
- source33프레임의 학습 정답 인코딩

C. endpoint-only latent·point patch
- 시작과 종료를 각각 독립 인코딩한 특징
- 3×3 patch 추출 결과

D. text context
- 기존에는 일치
- 이번 원인이 영향을 줄 근거가 없으면 T5 재실행 불필요

첫 시간 latent가 같다는 이유만으로
모든 endpoint 특징이 유효하다고 하지 않는다.
실제 독립 호출과 patch 값을 확인한다.

기존 자료와 새 자료를 다른 이름공간에서 비교한다.
기존 cache·checkpoint를 덮어쓰지 않는다.

필요한 경우 old/new clean target latent를
같은 확인된 decoder로 복원할 수 있다.
이는 RECONSTRUCTION_DIAGNOSTIC이며 신규 생성 성과가 아니다.

decoder도 같은 원인의 영향을 받을 수 있다면
더 좋아 보이는 복원 영상만으로 encoder 정답을 선택하지 않는다.

영향 목록에 각 항목을 다음처럼 표시한다.
- DIRECTLY_VERIFIED
- SAME_PATH_INFERRED
- REBUILD_REQUIRED
- UNKNOWN

두 validation만 직접 검증하고
train8개·test·cross-ID 전체 파일을 직접 검증했다고 쓰지 않는다.
나머지는 실행 경로와 계보에 따른 추정 범위로 구분한다.

학습 자료까지 영향을 받으면:
- 수정된 validation 두 사례의 cache만 우선 보존
- 전체 재생성 대상과 의존 관계를 REBUILD_MANIFEST에 기록
- 원래 cache는 역사 자료로 보존

이번에 전체 데이터 재인코딩이나 재학습까지 자동 확장하지 않는다.


## 12. 원인에 따라 후속 작업을 분기한다

공통:
- optimizer update0회
- checkpoint0/128/256 불변
- adapter scale·projection·학습 목적 변경0
- 새 데이터·모델·imagegen·SAM·CoTracker 실행0

### A. 생성 경로만 잘못됐고 기존 학습 자료가 유효한 경우

전제:
- 학습 조건·target·endpoint 특징의 경로와 대표 검증이 유효
- 생성 경로 수정 완료
- 두 validation의 독립 parity 통과
- encoder 의미 검증 통과
- 미검증 범위는 명시

그때만 elephant에서 영상 두 개를 생성한다.

1. 수정 경로의 BASE / CFG5
2. 수정 경로의 ON checkpoint256 / CFG5

고정:
- 416×240·33frames
- preview16fps
- Euler50
- CFG5
- sigma_shift5
- seed20261028
- BF16·SDPA·tiled VAE
- vace_scale1.0
- 기존 앵커·윤곽·텍스트·생성 마스크

실제 model_fn 직전 context가 독립 검증한 새 조건과 맞는지 확인한다.
각 영상의 실제 초기 noise도 확인한다.

C-007 BASE5/ON5와 함께 비교한다.
이 비교는 생성 경로 수정의 영향이지
새 학습 알고리즘의 성능이 아니다.

양끝 덮어쓰기·후합성·색보정·업스케일링은 하지 않는다.


### B. 학습 cache 또는 target/endpoint 특징이 잘못된 경우

이번에는 재학습하지 않는다.

- 검증된 수정 cache 두 사례 보존
- 영향받은 자료·checkpoint 계보 분류
- 같은 초기화·분할·학습 설정으로 다시 평가하기 위한
  재생성·재학습 범위 명시

기존 checkpoint를 삭제하거나 기술적으로 사용할 수 없다고 단정하지 않는다.
다만 수정된 조건에서 방법의 유효성을 평가하려면
학습 조건을 일치시킨 재학습 비교가 필요한지 명확히 판단한다.

기존 checkpoint를 새 조건에 넣어 결과가 나쁘다는 이유만으로
입력 수정이 잘못됐다고 하지 않는다.
반대로 좋아졌다고 올바른 학습을 새로 완료한 것도 아니다.

이 분기에서는 해석하기 어려운 full video를 억지로 만들지 않는다.
재현·원인·최소 수정·독립 검증·영향 목록이 이번 산출물이다.


### C. 두 경로 모두 수정이 필요하거나 의도된 설정이 달랐던 경우

어느 의미를 기준으로 통일했는지 설명한다.
입력 계약 변경과 버그 수정을 구분한다.

학습 자료 유효성이 확정되지 않으면 B처럼 재학습은 별도 판단한다.
양쪽이 같아졌다는 사실만으로 기존 checkpoint를 정상으로 선언하지 않는다.


### D. 원인 미확정·재현 불가·의미 검증 부족

다음을 남기고 정해진 범위에서 종료한다.

- 마지막으로 같았던 경계
- 처음 달랐던 경계
- 확인·반증한 가설
- 현재 가장 좁혀진 원인 범위
- 다음에 필요한 증거 하나

무제한 인코딩·backend 변경·새 학습으로 확대하지 않는다.


## 13. 선택적 one-step 재평가

parity와 encoder 의미 검증을 통과한 경우에만 수행할 수 있다.
추가 학습은 없다.

구성:
- elephant/goat
- sigma 목표0.95/0.75/0.50/0.20/0.05
- positive/negative text
- BASE/ON-256

최대40 DiT forward.

실제 scheduler에서 가장 가까운 sigma와
모델에 전달된 BF16 timestep을 기록한다.
가능하면 C-007의 고정 noise 구성을 재사용한다.

각 probe의 BASE/ON은 같은 z_sigma와 target을 사용한다.

clean target latent가 수정됐다면:
- 새 target에서 z_sigma와 FM target을 재구성
- 과거 loss와의 차이를 adapter 성능 개선으로 부르지 않음
- “수정 입력에서 기존 checkpoint를 진단”한 결과로 표시

조건만 바뀌고 target은 같다고 확인된 경우에만
같은 state에서 조건 교체의 효과로 해석한다.

생성 중 latent에 정답 velocity가 있다고 가정하지 않는다.
CFG 조합의 변화와 unguided FM 오차를 혼동하지 않는다.

낮은 sigma 회귀가 남으면 그대로 기록한다.
조건 불일치 하나가 모든 손상을 설명해야 한다고 요구하지 않는다.


## 14. 실행 예산과 안전

이번 작업의 중심은 제한된 VAE 인코딩 진단이다.

예산:
- 정상 public VAE encode 최대64회
- 기계적 복구 예비 encode8회
- 진단용 VAE decode 최대4회
- 선택적 DiT probe 최대40회
- 분기A의 정상 full sampler 최대2회
- sampler 기계적 복구 예비1회
- 학습0회
- 다운로드0회

VAE 호출에 여러 영상이 들어가면
호출수·영상수·프레임수를 함께 센다.
batch를 키워 상한을 우회하지 않는다.

내부 tile/chunk 호출은 public encode 호출과 구분한다.
VACE context 한 번은 두 RGB branch 인코딩을 포함하므로
비용을 빠뜨리지 않는다.

원인이 일찍 확인되면 불필요한 후속 진단을 생략한다.
상한을 모두 소진하는 것이 목표가 아니다.

전체 작업 범위 상한3시간.
마지막20분은 정리·전달·종료에 남긴다.
이는 승인된 작업 예산이지 성능 예측이나 완료 시간 보장이 아니다.

실제 환경에서 시간·자원상 완료할 수 없으면
완료한 증거와 미완료 부분을 구분해 제출한다.

기존 정상 보호 실행 경로를 그대로 사용한다.
다음을 바꾸지 않는다.
- PSI 기준
- headroom
- worker swap
- cgroup 한도
- 외부 GPU 작업 보호
- 서비스 보호 정책

과거의 작은 system swap-out 절대0 분기를 되살리지 않는다.
반대로 현재 가드를 느슨하게 하지도 않는다.

단순 코드·경로 오류는 같은 의뢰 안에서 수정한다.
실제 OOM·자원 압박·외부 작업 충돌은 자동 우회하지 않는다.

14B를 올리거나 다른 프로세스를 종료하지 않는다.
VAE/T5/DiT는 필요한 단계별로 사용하고 불필요한 동시 상주를 피한다.


## 15. 수학·로직·코드 해설

한국어 LESSON_KO.md는 실제 원인과 수정에 연결한다.

기호:
X: 조건 RGB
G: 생성 여부 마스크
E_C: cache 인코딩 경로
E_G: 실제 생성 인코딩 경로

c_C = E_C(X,G)
c_G = E_G(X,G)

개념적 조건 구성:
I = (1-G) * Normalize(X)
R = G * Normalize(X)

c = Concat(E_VAE(I), E_VAE(R), MaskEncode(G))

Normalize(X)의0과 uint8 RGB0은 다르다.
실제 코드의 값 범위와 연결해 설명한다.

학습:
L_C = E[ ||v_(theta,psi)(z_sigma,sigma,c_C) - v*||² ]

생성:
z_next = z + delta_sigma * v_(theta,psi)(z,sigma,c_G)

이번에는 theta나psi를 학습하지 않는다.
c_C와c_G의 의미·계산 관계를 바로잡는다.

설명할 항목:
1. 파일 픽셀 일치와 인코더 입력 일치의 차이
2. shape·dtype·axis·호출 이력의 역할
3. 독립 영상 reset과 영상 내부 시간 기억의 차이
4. 첫 latent만 같다는 관측이 주는 단서와 한계
5. eval/no_grad/inference_mode의 차이
6. 조건 mismatch가 학습·생성 해석을 교란하는 방식
7. parity와 encoder 의미 검증이 모두 필요한 이유
8. target latent·endpoint 특징까지 확인하는 이유
9. 잘못된 조건으로 학습한 checkpoint를 해석하는 방법
10. 입력 일치가 회복돼도 adapter 회귀가 남을 수 있는 이유

형식:
직관 → 수식 → 실제 함수·상태 → 최초 차이 →
수정 근거 → 독립 검증 → 남은 한계.

근거 없이 “원인이 모두 밝혀졌다”는 설명을 만들지 않는다.
이론만 반복하고 실제 함수와 관측을 빠뜨리지 않는다.


## 16. 기록·결과물·전달

새 세션의 재인수를 위해 PLAN 또는 실행 설정에 다음을 간단히 남긴다.
- 확인한 저장소·branch·HEAD
- 실제 Python·소스 위치
- 입력과 cache의 계보
- 원래 C/G 경로
- 현재 진행 단계
- 남은 예산

비공개 경로는 private 설정에 둔다.
별도 관리 framework나 대량의 인수 문서를 만들지 않는다.

권장 문서:
- PLAN.md
- ROOT_CAUSE.md
- PARITY.json
- AFFECTED_ARTIFACTS.json
- REBUILD_MANIFEST.json: 필요한 경우
- RESULTS.md
- COSTS.json
- LESSON_KO.md
- REPRODUCE.md
- DELIVERY.json

같은 내용을 여러 문서에 반복하지 않는다.
원인과 증거는 ROOT_CAUSE,
최종 결론은 RESULTS,
다음 판단은 HISTORY/ROADMAP에 연결한다.

판정을 분리한다.
- MISMATCH_REPRODUCED
- FIRST_DIVERGENCE_LOCALIZED
- ROOT_CAUSE_CONFIRMED 또는 UNKNOWN
- PARITY_EXACT / PARITY_NUMERIC / PARITY_INCONCLUSIVE
- ENCODER_SEMANTICS_VERIFIED 또는 UNVERIFIED
- TRAIN_ARTIFACTS_VALID / REBUILD_REQUIRED / UNKNOWN
- FROZEN_CHECKPOINT_REUSE_QUALIFIED / RETRAIN_REQUIRED / UNKNOWN

parity가 통과했다고 영상 품질 PASS로 올리지 않는다.
새 영상을 만들었어도 실제 연속 지각 검수가 없으면
temporal=UNVERIFIED를 유지한다.

검토 자료:
- cache/live의 시간별·채널별 차이
- 최초 불일치 경계와 수정 전후
- target·endpoint 특징 영향표
- 필요한 작은 차이 시각화
- 선택적 재구성 진단
- 분기A에서만 새 BASE/ON 영상

latent 시각화·재구성 영상·실제 생성 영상을 명확히 구분한다.
새 영상이 없으면 NOT_RUN과 이유를 적는다.

compact에는 뷰어·작은 시트·보고서·필요한 영상만 넣는다.
대형 tensor·raw·latent는 별도 보존하고 계보를 연결한다.
모델 가중치나 과거 전체 ZIP을 반복 포장하지 않는다.

파일명의 날짜는 실제 실행 날짜를 사용한다.
기존20261030이라는 문자열을 무조건 새 파일명에 복사하지 않는다.

Spark/Mac의 실제 /tmp 또는 기존 승인된 전달 위치에 보존한다.
접속·전송이 가능한 호스트만 실제로 검증한다.
한쪽에 접근하지 못했다면 양 호스트 동일성 PASS라고 쓰지 않는다.

확인할 것:
- ZIP 크기·SHA256
- CRC
- manifest
- 실제 추출
- 가능한 호스트 사이의 전송 후 동일성

공개 Git에는 비민감 코드·문서·필요한 hash만 올린다.
개인 경로·PID·token·가중치·latent·조건 tensor를 자동 공개하지 않는다.

과거 결과는 수정하지 않고 해석 변경을 추가한다.
기존 failure/UNKNOWN을 소급 PASS로 만들지 않는다.

자체 프로세스 종료와 다른 작업 보존을 확인한다.
관련 변경만 commit하고 연구 브랜치의 원격 SHA를 확인한다.
자동 재개나 후속 학습은 예약하지 않는다.


## 17. 최종 보고는 이 질문부터 답한다

1. 정확히 어느 함수·경계에서 최초로 값이 달라졌는가?
2. 원인은 무엇이며, 어떤 단일 개입으로 확인했는가?
3. 무엇을 최소한으로 수정했는가?
4. 독립적인 두 경로와 두 영상에서 일치했는가?
5. 같은 잘못된 계산으로 맞춘 것이 아닌지 어떻게 확인했는가?
6. 조건 cache·target latent·endpoint 특징 중 무엇이 영향받았는가?
7. 기존 checkpoint를 어떤 범위에서 재사용할 수 있는가?
8. 재학습이 필요하다면 무엇을 다시 만들어야 하는가?
9. 조건 mismatch와 별개로 남은 adapter 회귀는 무엇인가?

실제 결과·원인·수정·다음 판단을 먼저 쓰고,
검사 개수·해시·전송 세부는 근거로 뒤에 둔다.

원인을 못 찾으면 못 찾았다고 정확히 보고한다.
대신 마지막으로 같았던 곳과 처음 다른 곳을 남겨
다음 작업이 처음부터 반복되지 않게 한다.

이번 작업이 끝나면 종료한다.
새 학습·14B 복구·adapter 개조·CFG/scale 탐색은 자동 시작하지 않는다.


## 참고 링크

C-007 결과:
https://github.com/hyunlord/make-meme/tree/19e110431e90931c98277b7e94d6879268929336/docs/research/experiments/C-007-frozen-adapter-cfg-diagnostics

C-006 학습·cache 코드:
https://github.com/hyunlord/make-meme/tree/c4aef32de21de4073bd4eb1861df4d35f2eda793/docs/research/experiments/C-006-motion-point-adapter-pilot

기록 revision의 VACE pipeline:
https://github.com/modelscope/DiffSynth-Studio/blob/f39d731a3e318d25b725eb3389cfddb184619842/diffsynth/pipelines/wan_video.py

기록 revision의 VAE:
https://github.com/modelscope/DiffSynth-Studio/blob/f39d731a3e318d25b725eb3389cfddb184619842/diffsynth/models/wan_video_vae.py

위 링크는 코드 근거다.
현재 Spark에 실제 설치된 파일과 일치하는지는 별도로 확인한다.
문서를 읽기 위해 실행 환경을 최신 버전으로 업그레이드하지 않는다.
