# C-005 통합 작업 의뢰서
# 동일한 편집 앵커·동적 윤곽에서 VACE 1.3B와 14B 비교

저장소: hyunlord/make-meme

최신 연구 이력 기준:
e69f8672722b91c1ad07273060d3cb68ffaf7ef1
C-004-end-anchor-consistency

품질 비교 기준:
853ee952795246648b3a6e46d37d5dead03abef3
C-002-sam-layout-conditioning
차량·개 LAYOUT_MOV

권장 실험 경로:
docs/research/experiments/C-005-vace-backbone-comparison/

권장 의뢰서 경로:
docs/research/work_orders/C005_VACE_BACKBONE_COMPARISON_KO.md


## 0. 목적과 이번 작업의 최종 산출물

최종 연구 목표는 다음과 같다.

원본 영상 + 편집 지시 + 선택적 참조 이미지
→ 소수의 편집 앵커
→ 원본 객체·부위 움직임과 target 외형의 연결
→ 개인 DGX Spark에서 실행 가능한 고품질 영상 편집

지금까지 C 트랙은 VACE 1.3B를 사용했다.
이는 기존 실행 가능성·입력 형식·반복 비용을 고려한 기준선 선택이었고,
다른 기반 모델과 비교해 최고 품질로 선정한 것은 아니다.

새 부위 대응·가시성·조건 전달 모듈의 학습에 투자하기 전에,
동일 입력에서 더 큰 공식 모델이 어떤 차이를 만드는지 확인한다.

이번 질문:

“같은 편집 앵커·원본 동적 윤곽·텍스트·샘플링 조건에서
공식 VACE 14B가 기존 VACE 1.3B보다
외형·동작·장면을 더 잘 보존하는가?
그 차이는 Spark에서의 추가 시간·메모리 비용과 함께 어떻게 해석되는가?”

최종 산출물:
- 기존 1.3B 차량·개 결과 두 개
- 신규 14B 차량·개 결과 두 개
- 같은 프레임·같은 재생 시간축의 비교 뷰어
- 품질 축별 판단과 단계별 자원 비용
- 다음 방법 개발에 사용할 모델에 대한 제한된 결정

가중치 다운로드·모델 적재·첫 forward만으로 완료하지 않는다.
안전하고 호환 가능한 경우 실제 두 영상과 비교까지 수행한다.

이번은 두 공개 checkpoint의 동일 입력 실용 비교다.
파라미터 수 하나만의 순수 인과효과를 식별하는 실험이 아니다.
두 사례·한 seed로 일반적 모델 우열이나 성능 상한을 주장하지 않는다.


## 1. 연구 이력과 기존 환경 보존

실제 C 트랙 branch/worktree와 최신 HEAD부터 확인한다.
과거 branch 이름을 추정하거나 기준 커밋으로 강제 reset하지 않는다.
다른 작업·기존 수정·산출물을 덮어쓰지 않는다.

C-005가 이미 실행 중이거나 완료됐다면 중복 실행하지 않는다.

다음 자료를 읽는다.
- C-002 RESULTS.md / METHOD.md
- C-002 CONDITIONS.json / NUMERICS.json / COSTS.json
- C-002 code/video_generate.py
- C-001 INPUTS.json / ANCHORS.json / BACKEND_CONTRACT.md
- C-003 완료 후 적용된 실행·메모리 보호 정책
- C-004의 실제 정상 실행 경로
- 현재 CHARTER·HISTORY·ROADMAP·C 트랙 방향 문서

A/B 이력과 다음 판정을 유지한다.
- B-034 운영 보류
- C-001 PARTIAL
- C-002 차량 TRADE_OFF, 개 COARSE_CONTROL_ONLY
- C-003 NO_ESTABLISHED_GAIN
- C-004 앵커 PARTIAL_BUT_USABLE, 영상 NO_ESTABLISHED_GAIN

C-004 종료 앵커를 이번에 사용하지 않는다.
C-003 내부 구조선도 사용하지 않는다.

과거의 system swap 절대0 또는
START_SWAPOUT_OBSERVED 시작 전용 분기를 되살리지 않는다.
현재 정상 실행된 보호 정책을 재사용하며 새로운 가드를 설계하지 않는다.


## 2. 역할 분담

Codex Astra:
- 기존 입력과 실행 계약 확인
- 공식 14B checkpoint 연결과 최소 코드 수정
- 사전 비교 조건 고정
- 실제 Spark 실행
- 품질·비용 분석
- 수식·코드·한국어 해설과 GitHub 기록

DGX Spark:
- 공식 14B 가중치 저장
- 필요한 조건 인코딩
- 두 영상의 순차 추론·디코딩
- 단계별 자원 계측과 산출물 보존

Mac:
- 검토 자료 확인
- 기존 전달 방식으로 최종 compact 수신

이번 native imagegen 호출은0회다.
앵커는 C-001에서 생성해 C-002가 사용한 네 장을 재사용한다.


## 3. 고정 사례와 비교 행렬

C-002의 두 사례를 그대로 사용한다.

case_rigid:
- source: 기존 car-roundabout 구간
- target: 기존 car-shadow 참조
- 시작·종료 앵커: C-002에서 사용한 두 이미지
- layout: C-002의 실제 시간별 SAM 윤곽
- 기준 출력: 기존 VACE 1.3B LAYOUT_MOV

case_nonrigid:
- source: 기존 dog 구간
- target: 기존 dog-gooses 참조
- 시작·종료 앵커: C-002에서 사용한 두 이미지
- layout: C-002의 실제 시간별 SAM 윤곽
- 기준 출력: 기존 VACE 1.3B LAYOUT_MOV

정확한 frame ID·파일 경로·좌표 변환·hash는 기존 manifest를 따른다.
다른 구간, 더 좋은 reference, 다른 앵커로 교체하지 않는다.

비교 행렬:

차량 / VACE 1.3B / 기존 출력 재사용
차량 / VACE 14B  / 신규 생성1회

개 / VACE 1.3B / 기존 출력 재사용
개 / VACE 14B  / 신규 생성1회

실행 순서는 차량14B → 개14B로 고정한다.
차량 결과가 좋아 보이거나 나빠 보인다는 이유로
입력이나 설정을 바꾸지 않는다.

14B의 안전·호환성 문제가 아닌 단순 품질 실패라면
남은 개 비교도 사전 계획대로 수행한다.

1.3B 재생성은0회다.
기존 출력과 비용 기록을 재사용한다.


## 4. 같은 입력·같은 생성 조건

다음 항목을 유지한다.

- 해상도832×480
- 33프레임
- 앵커 위치0/32
- source_fps=null
- preview_fps=16
- timebase_assumed=true
- condition_mode=layout_mov
- vace_reference_image=None
- 각 사례의 기존 prompt와 negative_prompt
- seed20261028
- rand_device=cpu
- BF16
- SDPA
- tiled VAE
- 기존 Euler scheduler
- num_inference_steps=50
- CFG5
- sigma_shift5
- effective vace_scale1.0
- adapter OFF
- TeaCache·SageAttention·별도 근사 가속 OFF

기존 1.3B와 같은 prompt 문장을 그대로 사용한다.
14B용 prompt 확장·번역·추가 지시를 하지 않는다.
외부 prompt enhancer·유료 inference API를 호출하지 않는다.

조건 RGB:
X0 = 기존 시작 앵커
X32 = 기존 종료 앵커
X1..31 = 기존 C-002의 각 시점 동적 layout

VACE 생성 여부 마스크:
G0,G32 = 프레임 전체0
G1..31 = 프레임 전체255

SAM 객체 마스크와 VACE 생성 마스크를 혼동하지 않는다.
SAM 마스크를 새로 추출하거나 수정하지 않는다.

조건은 기존 PNG 또는 인메모리 RGB로 전달한다.
압축 preview MP4를 모델 입력으로 다시 읽지 않는다.

33/16초의 파일 지속시간과
32/16초의 양끝 표본 간격을 구분한다.
확인하지 못한 원본 FPS를16fps라고 기록하지 않는다.

알려진 한계도 그대로 유지한다.
- 개 종료 앵커의 원본 자세 충돌
- 양끝 입력이 출력 픽셀의 정확한 복사를 보장하지 않음
- 현재33→9 mask 시간 압축에서 양끝0이 누락되는 한계
- 원본 중간 배경 RGB와 다른 객체 track은 생성 입력에 없음

이번에 mask 압축·endpoint clamp·배경 보존 방식을 함께 고치지 않는다.


## 5. 공식 VACE 14B 가중치 확보

사용할 모델:
Wan-AI/Wan2.1-VACE-14B

다음과 혼동하지 않는다.
- Wan2.1 T2V-14B
- Wan2.1 I2V-14B
- FLF2V-14B
- SCAIL
- VACE Preview
- 비공식 quantized checkpoint

다운로드 전에 실제 immutable revision을 고정한다.
main이라는 문자열만 provenance로 남기지 않는다.

공식 config에서 VACE 모델임을 확인한다.
작성 시 확인된 공식 config의 주요 값:
- _class_name: VaceWanModel
- model_type: vace
- dim:5120
- num_layers:40
- num_heads:40
- in_dim:16
- out_dim:16
- vace_in_dim:96
- vace_layers:[0,5,10,15,20,25,30,35]

실제 다운로드 revision의 config를 기준으로 최종 확인한다.
파일 이름에14B가 있다는 사실만으로 올바른 모델이라고 하지 않는다.

1.3B의 hidden dimension·block 수를14B에 강제로 적용하지 않는다.
기존 pipeline의 정상적인14B 인식·변환 경로를 사용한다.
필요한 VACE block이 누락된 일반 T2V 모델을
동일한14B 비교라고 보고하지 않는다.

확보할 것:
- config
- shard index
- index가 요구하는 정확한 diffusion safetensors shards
- 필요한 T5·VAE·tokenizer 구성요소
- license·모델 provenance

기존 T5·VAE·tokenizer가 같은 구성요소라는 근거가 있으면 재사용한다.
파일명만 같다는 이유로 동일하다고 간주하지 않는다.
공식 파일 hash 또는 기존 검증 근거를 확인한다.
다른 버전이면 숨기지 말고 모델 구성 차이에 포함한다.

공식 배포의 model files는 여러 shard로 나뉘어 있다.
glob만 사용해 다른 모델이나 변환본이 섞이지 않게 한다.
index에 필요한 모든 shard와 key가 존재하는지 확인한다.

신규 다운로드 상한80GiB.
이미 검증된 로컬 파일은 재다운로드하지 않는다.
예제 영상·전체 assets·다른 모델·중복 Diffusers 형식은 받지 않는다.

실제 필요한 파일 용량과 임시 공간·출력 공간을 먼저 계산한다.
기존 모델·사용자 파일을 임의로 삭제해 공간을 만들지 않는다.
용량이 부족하면 필요한 공간과 부족량을 구체적으로 보고한다.

공식 파일의 byte size·revision·가능한 원격 checksum과
다운로드 후 hash를 한 번 기록한다.
모든 실험 셀마다 대형 가중치를 다시 전체 해시하지 않는다.

안전한 읽기:
- safetensors는 해당 형식의 loader 사용
- 기존 .pth는 검증된 weights_only 경로 사용
- 임의 pickle 실행이나 출처 불명 checkpoint로 우회하지 않음

다운로드 실패 시 동일 파일의 전송 재개는 가능하다.
이를 새로운 모델·영상 품질 시도로 세지 않되,
실제 전송 비용과 시간은 기록한다.
완료 파일은 중복 복사하지 않는다.

공식 파일을 받는 접근 조건이 있으면 정상 경로를 사용한다.
인증·접근제어를 우회하거나 사용자 token을 공개하지 않는다.


## 6. 기존 DiffSynth 경로에서 최소 연결

C-001/C-002가 사용한 DiffSynth 기록 revision:
f39d731a3e318d25b725eb3389cfddb184619842

이 revision에는 다음 예제가 있다.
- examples/wanvideo/model_inference/Wan2.1-VACE-14B.py
- examples/wanvideo/model_inference_low_vram/Wan2.1-VACE-14B.py

이를 참고하되 예제 전체를 실행하지 않는다.
예제 데이터 다운로드·예제 prompt·다른 영상 생성은 이번 범위가 아니다.

실제 설치된 파일과 기록 revision의 관계를 필요한 범위에서 확인한다.
기존 환경이 이미14B를 지원하면 업그레이드하지 않는다.

기존 video_generate.py의 조건 구성·scheduler·관측 hook을 재사용한다.
변경은 모델 파일 목록·구성요소 경로·새 출력 경로와
필요한 기존 메모리 관리 옵션으로 제한한다.

최소 수정 diff와 실제 effective config를 남긴다.
새 launcher·supervisor·MCP framework를 만들지 않는다.

금지:
- 기존 연구 venv의 Torch/CUDA/driver 교체
- 전체 DiffSynth를 최신 버전으로 자동 업그레이드
- 다른 library로 조용히 전환
- 새 FlashAttention 빌드
- FP8/INT8/INT4 양자화
- step·해상도·길이 축소
- 임의 key 누락 허용 또는 mismatched size 무시
- 1.3B checkpoint와14B 일부 가중치 혼합

기존 pipeline의 문서화된 state-dict 변환은 사용할 수 있다.
그 변환과 load의 key/shape 불일치를 검증한다.
새로운 모델 포맷 변환 연구로 확대하지 않는다.

현재 runtime에서 동일 계약으로 연결할 수 없으면
어느 함수·지원 형식·구성요소가 맞지 않는지 짧게 기록한다.
다른 backend를 설치하는 실험으로 자동 전환하지 않는다.


## 7. 메모리 — 모델 이름이 아니라 실제 적재 경로를 확인

14B라는 이름에2bytes를 곱하는 것만으로
전체 실행 메모리를 추정하지 않는다.

safetensors header·config·loader 코드로 다음을 구분한다.
- 저장된 dtype과 실제 tensor 수/크기
- BF16 계산에 필요한 상주 가중치
- VACE 조건 block
- 텍스트 인코더·VAE
- CPU 원본 tensor와GPU tensor의 중복 생존
- 변환 중 임시 복사
- attention·activation·출력 buffer

파일 용량, host RSS, cgroup memory,
CUDA allocated/reserved, MemAvailable은 다른 측정값이다.
하나를 다른 것의 완전한 대용으로 쓰지 않는다.

Spark에서 CPU offload를 하면 별도의 무한한 메모리가 생긴다고
가정하지 않는다. host와GPU의 전체 점유와 중복을 함께 고려한다.

기존 loader가 큰 원본 state_dict와 변환 후 모델을
동시에 오래 유지하는지 모델 적재 전에 확인한다.
명백히 한도를 넘는 계획으로 일단 올려 보고 OOM을 기다리지 않는다.

가능하면 기존 native의 BF16 적재 경로를 사용한다.
현재 pipeline이 제공하는 dtype-preserving CPU/disk offload는
가중치 정밀도·수학적 설정을 유지하는 범위에서 허용한다.

offload를 사용한다면:
- 로딩 전에 전략을 고정하고 두 사례에 동일 적용
- 계산 BF16 유지
- 사용 옵션·I/O와 실행 시간 기록
- CPU/disk 이동이 수치·실행에 미친 한계 기록
- GPU 총메모리에서2GiB만 빼는 예제값을 그대로 복사하지 않음
- 현재 headroom·worker 한도·전체 시스템 여유를 우선

1.3B와14B의 메모리 관리 방식이 다르면
품질 비교와 구현 비용 비교를 구분한다.
이를 순수 아키텍처의 속도 차이라고 단정하지 않는다.

기존 worker 한도·headroom·swap·외부 작업 보호를 높이거나 끄지 않는다.
정상 작동한 C-003/C-004의 공통 정책을 재사용한다.

한도 안에서 native BF16 실행 계획을 세울 수 없으면
RESOURCE_INFEASIBLE_UNDER_CURRENT_POLICY로 남긴다.
이는 이번 운영 조건의 실행 한계이지 모델 품질 FAIL이 아니다.

이번 작업에서 양자화·새 커널·새 가드 연구를 시작하지 않는다.


## 8. 모델 적재 전의 최소 검사

실제 worker가 사용할 동일한 Python·설정·명령 경로로 검사한다.

필수 확인:
- stage/script/config/input/output의 절대경로
- 실제 WorkingDirectory와 module 검색 경로
-14B shard 목록·config·구성요소 경로
- 기존 VACE14B 지원 경로
- 출력 디렉터리 충돌·쓰기 가능 여부
- 두 사례의 조건 RGB·G·텍스트 불변성
- 실제 적용될 precision·scheduler·attention 경로
- 고정된 메모리 관리 설정

이 검사는 가중치를 두 번 올리는 별도 full-model smoke가 아니다.
가능한 CPU·header 확인으로 끝내고,
최초 실제14B forward는 첫 생성 시도의 일부로 센다.

경로·인자·import·directory 누락 같은 오류는
같은 의뢰 안에서 고치고 필요한 CPU 검사를 다시 한다.
단순 오타마다 새 의뢰·실험 번호·운영 보고서 묶음을 만들지 않는다.

관측 실패·외부 작업·실제 자원 위험은 다르게 다룬다.
그 경우 가드를 우회하거나 프로세스를 임의 종료하지 않는다.

CPU 검사 개수보다 실제 사용되는 실행 계약이 맞는지 확인한다.
이미 정상 동작한 전체 서비스·커널·checkpoint 감사를 반복하지 않는다.


## 9. 실제 입력과 계산 조건의 동일성

모델 실행 직전 비교표를 저장한다.

논리 입력:
- source/anchor/layout의 파일·pixel hash
- prompt/negative의 정확한 문자열 hash
- G33장과 압축 마스크
- frame order
- scheduler timesteps/sigmas
- noise 생성 방식

C-002 noise 기록:
cf71cc3501ff09f876a384a20e9aedea41fb7eaaf956e5da52e8f777c9fbf9ba

예상 latent 계약:
- initial noisy latent [1,16,9,60,104]
- VACE context [1,96,9,60,104]

14B의 hidden dimension이 커졌다고
입력 영상 latent까지 임의로 바꾸지 않는다.
실제 checkpoint·VAE 계약으로 확인한다.

기존 첫 model_fn 관측 hook을 재사용해 다음을 기록한다.
- noise shape/dtype/hash/finite
- VACE context shape/dtype/hash/finite
- mask64채널 hash와 시간별 평균
- effective vace_scale
- 실제 model class와precision

추가 관측용 forward는0회다.
전체 attention dump·매 step 대형 tensor 저장은 하지 않는다.

seed만 같다고 noise 동일성을 선언하지 않는다.
실제 첫 noisy latent를 C-002 기록과 비교한다.

noise가 다르면 가능한 원인을 CPU에서 확인한다.
모델 로딩이 global RNG에 영향을 줬다면
기존과 같은 독립 generator 경로를 재사용한다.
품질을 본 뒤 더 좋은 noise를 고르지 않는다.

논리 조건과 공통 encoder가 같으면 context도 비교한다.
동일하지 않으면 입력 차이, encoder 차이,
수치적 차이 중 무엇인지 근거 범위에서 구분한다.
과거 자료가 부족한데 bitwise 동일성 PASS를 만들지 않는다.

비교 적합성:
MATCHED
- 핵심 논리 입력·noise·수학적 설정이 확인됨.

QUALIFIED
- 조건과 설정은 맞지만 memory path나encoder 등
  불가피한 차이가 있어 범위를 명시해야 함.

NOT_COMPARABLE
- 시간 조건·입력·설정이 달라 직접 비교할 수 없음.

NOT_COMPARABLE 상태로 몰래 영상을 생성해
“모델만 바꾼 결과”라고 보고하지 않는다.
단순 연결 오류라면 같은 범위에서 고치고,
새 구현·설정이 필요하면 이유를 남긴다.


## 10. 실행 예산과 정상 완료 절차

정상 신규 생성:
- 차량14B1회
- 개14B1회
- 각각50 scheduler step
- 기존 CFG 구현에서 각각100 model_fn call 예상
- 각 final latent 저장과 VAE decode1회

정상 합계:
- 신규 영상2개
-100step
-200 model_fn call
- 신규 final latent2개
- 신규 raw 영상2개

별도 단독 demo·warmup full sampler는 실행하지 않는다.
첫 실제 forward를 정상 첫 영상 생성과 연결한다.

실제 model_fn 호출을 세고,
14B에서 기대와 다르면 확인 없이100회라고 보고하지 않는다.
기존 CFG와다른 batched 경로로 바꾸지 않는다.

각 사례에서 scheduler 종료 latent를
decode 전에 원자 저장하고 readback 검증한다.
최종 latent·raw·전체33프레임·MP4를 보존한다.

출력 첫/마지막 프레임을 앵커로 덮어쓰지 않는다.
원본 배경 합성·색보정·문자 제거·SR·보간도 하지 않는다.
우선 raw 생성 품질을 비교한다.

기존 독립 case worker 경로를 우선 사용한다.
모델 상주 재사용을 위한 새 runtime을 만들지 않는다.
기존 경로가 이미 안전한 상주 재사용을 지원한다면 사용할 수 있으나,
case 간 scheduler/RNG/cache 초기화를 확인하고 cold/warm 비용을 나눈다.

두 사례는 순차 실행하며 다른 대형 모델을 함께 상주시키지 않는다.

전체 heavy 시도:
정상2회 + 기계적 복구 예비1회 = 최대3회.

모델 적재 시작 후 실패한 시도도 포함한다.
예비는 코드·경로·형식 연결 오류 복구용이지 품질 재시도용이 아니다.

생성 결과가 나쁘다는 이유로 다음을 하지 않는다.
- seed 변경
- prompt 수정
- step/CFG/shift 조절
- 다른14B 변형 사용
- condition scale 변경
- 더 유리한 사례로 교체

final latent가 저장된 뒤 decode가 실패하면
sampler를 다시 실행하지 않는다.
저장물에 대한 VAE-only 복구를 전체최대1회 허용한다.
영상 인코딩 오류는 기존 raw/PNG로 수정한다.

실제 OOM·안전 가드·외부 작업 충돌이 발생하면
예비를 이용해 기준을 완화하거나 자동 반복하지 않는다.
완료된 결과를 보존하고 구체적인 차단 상태를 보고한다.

전체 작업 상한6시간.
다운로드·준비·실행·검토·전달을 모두 포함한다.
마지막30분은 저장·문서·전달에 남긴다.
시간은 승인된 작업 한도이지 실제 성능 예상치가 아니다.

하나만 완료되면 PARTIAL_COMPLETION으로 보존한다.
두 결과를 채우기 위해 설정을 낮추거나 실행을 숨겨 연장하지 않는다.


## 11. 품질 평가 — 선명함과 동작 정확도를 구분

생성 전에 source·앵커·기존1.3B 결과를 실제로 보고
아래 사건을 관측 가능한 표현으로 짧게 고정한다.

차량:
- 은색 높은 차체·루프레일·창/후미등의 target 특징
- 원본 Mini형 외형으로의 회귀 여부
- 우측 이동·축소·후면 노출 진행
- 같은 프레임에서의 회전 상태
- 빨간 전경 차량의 등장 시점
- 파란 표지판·난간·건물·주변 차량 보존
- 바퀴·차체의 형태·그림자·접촉 불확실성

개:
- 검정/흰 털·얼굴·가슴·발의 target 특징
- 원본 크림색 외형으로의 회귀 여부
- 정면 접근과 크기 변화
- local8/16의 머리·몸 방향
- 관측 가능한 앞발 배치·겹침·진행
- 종료 앵커와 원본의 자세 충돌
- 울타리·수풀·잔디·카메라의 변화
- 다리 중복·얼굴 변화·접촉 불확실성

기존 보고서를 정답 annotation으로 복사하지 않는다.
원본과 출력의 실제 보이는 내용을 다시 확인한다.

모든33장을 같은 frame index로 비교한다.
고정 시트:
0/4/8/12/16/20/24/28/32

개는 다음을 나눠 해석한다.
- 중간1~28
- 종료 접근29~31
- 출력 마지막32

종료 앵커 자체의 오류를14B가 반드시 해결해야 한다고 요구하지 않는다.
앵커를 잘 따르는 것과 원본 자세를 따르는 것이 충돌하는 부분을 표시한다.

차량의 배경 실패는 외형 품질과 따로 판정한다.
새 target 차량이 선명해졌다고 전경 차량·표지판 손상을 무시하지 않는다.

각 품질 축:
- target 외형
- 큰 이동·크기·방향
- 내부 동작의 사건 순서
- 장면·보호 객체
- 형태·가림·경계
- 양끝 앵커 충실도
- 실제 연속 품질

전체화면 L1·source mask IoU를 개체·동작 정답 점수로 쓰지 않는다.
더 큰 모델에서 질감이 달라졌다는 이유만으로 개선이라고 하지 않는다.
원본을 복사해 동작·배경이 맞아도 target 교체 실패면 실패다.

시간 이동·프레임별 warp·출력별 다른 crop으로
잘 맞아 보이게 비교하지 않는다.

가능하면 모델 이름을 가린 A/B 정적·재생 비교를 먼저 작성한다.
그 뒤 실제 모델명을 연결한다.
같은 에이전트나 서브에이전트 검토를 독립 human 평가라고 하지 않는다.

실제 연속 지각 검수는 정적 시트·파일 decode 검사와 구분한다.
가능한 검토 주체가 실제 재생을 보았다면
속도·관측·범위를 기록한다.
그렇지 않으면 temporal=UNVERIFIED를 유지한다.
사용자 추가 답변을 기다리느라 나머지 결과 제출을 막지 않는다.


## 12. 비용 측정 — 과거 비용과 새 비용의 범위를 맞춘다

측정할 것:
- 신규 다운로드 byte·시간
- 모델 cold load
- 조건·텍스트 인코딩
- 실제 sampler
- VAE decode
- 결과 프레임·MP4 인코딩
- worker 전체 시간
- 전체 작업 경과
- 수동 검토·보정 시간: 측정한 범위만
- CUDA peak allocated/reserved: 실제 지원되는 측정값
- host RSS/cgroup peak·최저 MemAvailable
- offload I/O 또는 그 측정 불가 상태

CUDA peak와cgroup peak를 합쳐 무조건 전체 메모리라고 하지 않는다.
측정 누락·분리 불가능 항목은 null과 이유로 남긴다.

C-002의 기존 약5분은 해당 실행기의 elapsed/worker 지표였다.
새14B의 순수 denoising 시간과 바로 나누어
속도가 몇 배라고 보고하지 않는다.

같은 범위의 비용만 비율을 계산한다.
cold/warm, 같은 서비스 상태, offload 차이도 함께 적는다.

imagegen 호출·SAM 재분석은0회이지만,
전체 하이브리드 시스템에 원래 필요했던 비용은 존재한다.
이번 증분 비용과 최종 end-to-end 비용을 구분한다.

14B 파라미터 수가 약10배라는 이유로
시간·메모리도 정확히10배라고 예측하거나 보고하지 않는다.
실제 측정으로만 판단한다.

이번은 추론 적합성 실험이다.
추론이 가능했다고14B 학습도 가능하다고 결론내리지 않는다.


## 13. 판정 — 한 숫자로 억지 승자를 만들지 않는다

사례별 각 축에 대해
BETTER / SIMILAR / WORSE / UNCERTAIN을 기록한다.

종합 관측은 다음 중 적절한 것으로 정리한다.

OBSERVED_JOINT_GAIN
- target 외형·동작·장면을 함께 보았을 때
  뚜렷한 추가 이득이 있고 큰 회귀가 없음.
- 두 개발 사례에서의 제한된 관측이라는 범위 유지.

APPEARANCE_GAIN_ONLY
- 외형·질감·형태는 개선되지만 원본 동작은 미해결.

MOTION_GAIN_WITH_TRADEOFF
- 동작은 나아졌으나 외형·장면·형태 손상이 동반됨.

NO_ESTABLISHED_GAIN
- 현재 같은 설정에서 명확하고 일관된 이득이 없음.

WORSE
- 결합 품질이 명확하게 나빠짐.

INCONCLUSIVE
- 앵커 충돌·관측 부족·비교 조건 차이로 효과 판단이 어려움.

실행 상태는 별도로 기록한다.
COMPLETE / PARTIAL_COMPLETION / BLOCKED_RESOURCE /
BLOCKED_COMPATIBILITY / BLOCKED_EXTERNAL_WORK 등.

실행 실패를 모델 품질 FAIL로 세지 않는다.

고정 Euler50·CFG5·shift5 비교가14B의 최적 설정이라고 주장하지 않는다.
14B가 이 설정에서 좋지 않다고
“큰 모델도 소용없다” 또는 “방법 모듈이 반드시 필요하다”고 확정하지 않는다.

반대로14B가 좋아졌다고 파라미터 수만의 효과라고 단정하지 않는다.
training data·checkpoint·조건 활용 능력·구조가 함께 달라질 수 있다.

두 사례·한 seed다.
33프레임을33독립 실험으로 세지 않는다.
일반화·상용급·논문용 최종 성능·통계적 유의성을 주장하지 않는다.


## 14. 이번 결과로 결정할 다음 방향

자동으로 다음 학습을 시작하지 말고,
아래 의사결정을 실제 결과에 맞춰 제안한다.

A.14B에서도 동일한 내부 동작 문제가 남음
- 부위 ID·시간 궤적·가시성·앵커 특징을 전달하는
  학습형 조건 모듈 연구를 계속할 근거.
- 단, 이것만으로 그 모듈의 효과를 입증한 것은 아님.

B.14B가 외형·동작·장면을 크게 개선
-14B를 고품질 기준선 후보로 보존.
-1.3B의 효율 개선 연구와14B 위의 품질 개선 연구를 구분.

C.14B는 외형만 개선
- 외형 생성 능력과동작 제어 문제를 분리.
- 동작 조건 전달 구조를 다음 주요 표적으로 검토.

D.14B는 좋아졌으나 비용이 큼
- 큰 모델의 품질과작은 모델의 실용성 간 trade-off 기록.
- 작은 모듈·증류 등은 후속 가설로만 남김.

E. 비교가 입력 충돌이나실행 제약으로 불충분
- 미입증으로 종료.
- 무제한 backend 변경·설정 탐색으로 이어가지 않음.

기반 모델을 선택한 뒤에는 모델 비교를 계속 늘리지 말고,
같은 앵커를 더 잘 활용하는 대응·조건 전달 구조와 실제 학습으로 돌아간다.


## 15. 수학·구조·코드 해설

한국어 해설은 이번 비교에 필요한 내용으로 한정한다.

공통 조건:
c = (A0,A32,L1:31,G,P)

두 결과:
Y_small = H_theta_small(c;epsilon)
Y_large = H_theta_large(c;epsilon)

설명할 것:

1. 같은 조건·noise를 쓰는 이유
   결과의 무작위 차이를 줄여 비교하기 위함.
   같은 noise라고 완전한 결정성이나 순수한 크기 효과가 보장되지는 않음.

2. 입력 표현 공간과 모델 hidden dimension의 차이
   두 모델이 같은16채널 영상 latent·96채널 VACE context를 받을 수 있어도,
   내부 block 수·폭·attention 연산량은 다를 수 있음.
   실제 config·모델 summary로 설명.

3. 가중치 메모리의 기본 계산
   M_weight = Σ n_i × bytes(dtype_i)
   여기에조건 모델·encoder·activation·temporary copy가 추가됨.
   파일 용량과실제 peak 메모리가 다른 이유.

4. 시간 복잡도
   dense attention의 대표 항은 sequence length에 대해 이차적이고,
   projection/MLP는hidden dimension·layer 수의 영향을 받음.
   같은33프레임이라도모델 폭이 다르면 계산량이 같지 않음.
   정확한 전체 FLOPs처럼 과장하지 않고 실제 구현과 연결.

5. 같은50step의 의미
   같은 횟수의 생성 갱신이지 같은 FLOPs나같은 실행 시간이 아님.
   33프레임·9개 latent 시간 위치·50 생성 step을 구분.

6. 동작 정보 부족과 생성 능력 부족
   더 큰 모델도 입력에 없는 정확한 사건을 반드시 복원할 수는 없음.
   반대로같은 조건을 더 잘 활용할 가능성도 있음.
   실제 결과가 어느 쪽 설명과 양립하는지 논의하되 원인을 확정하지 않음.

7. 향후 frozen backbone + 작은 조건 모듈 학습
   trainable parameter가 적다는 사실과 backward activation 비용은 다름.
   이번 추론 결과를 학습 메모리 보장으로 바꾸지 않음.

직관 → 수식 → 실제 config/함수 → 관측 → 한계 순서로 작성한다.
모델 일반론을 길게 복제하지 않는다.
결과를 설명하는 수학과 실제 반례를 함께 남긴다.


## 16. 기록·GitHub·전달

작업 시작 전에:
- 전체 의뢰서를 work_orders에 보존
- PLAN에 목표·두 입력·예산·평가·중단 조건 기록
- 모델 revision·파일 목록·실행 전략 고정
- 조건·코드·설정 freeze와commit/push

다음 결과 문서는 기존 스타일로 간결하게 작성한다.
- RESULTS.md
- BACKEND_COMPARISON.md
- CONDITIONS.json
- COSTS.json
- REPRODUCE.md
- LESSON_KO.md
- DELIVERY.json
- 필요한 실행 코드·모델 manifest

HISTORY·ROADMAP에 다음을 연결한다.
- 이번 비교를 하는 이유
- 무엇을 고정하고 무엇을 변경했는지
- 실제 모델 실행과품질 관측
- 비용과한계
- 다음 개발 모델·방법 선택 제안

과거 기록을 삭제하거나 소급 PASS로 고치지 않는다.
CPU 검사 수나가중치 다운로드를 영상 품질 성과로 세지 않는다.

검토 뷰어:
각 사례의 SOURCE / TARGET / START·END ANCHOR /
1.3B MOV / 14B MOV
동적 layout은 접을 수 있는 보조 패널로 제공.

- 같은 프레임 slider
- 같은16fps의나란한 재생
- 전체33프레임 접근
- 고정9프레임 시트
- 대상 외형·발/바퀴·보호 장면 확대
- 사건표·품질 판정·비용 표

모델명을 가린 비교와실제 모델명 표시를 쉽게 전환할 수 있으면 좋다.
화려한 UI 개발 때문에생성과평가를 미루지 않는다.

compact:
- 기존1.3B 원 MP4 두 개
- 신규14B 원 MP4 두 개
- 입력·앵커·필요한 조건 preview
- 뷰어·작은 시트·보고서·재현 자료

full 또는 기존 비공개 보존 경로:
- 신규 final latent·raw·무손실 전체 프레임
- 필요한 실행 증거

14B 가중치를 ZIP에 넣지 않는다.
과거 전체 ZIP과대형 raw를 반복 중복 포장하지 않는다.
용량 때문에원 생성 MP4를 낮은 화질로 재인코딩하지 않는다.
새 비교 영상·JPEG sheet는 파생물이라고 명시한다.

Spark와Mac의 실제 /tmp에 보존하고
ZIP 크기·SHA256·CRC·manifest·실제 추출·전송 동일성을 확인한다.
수행하지 않은 검증은 PASS라고 하지 않는다.

공개 GitHub에는 코드·비민감 문서·필요한 hash만 게시한다.
개인 경로·PID·token·가중치·condition tensor·latent는 공개하지 않는다.
공개 데이터·생성 이미지도 재배포 조건을 확인한다.

작업 종료 시 자체 프로세스 정리와다른 작업 보존을 확인한다.
commit/push·원격 SHA 일치를 확인한다.
추가 실험이나자동 재개를 예약하지 않는다.


## 17. 최종 보고의 첫 질문

1.14B는1.3B보다 무엇을 실제로 개선했는가?
2. 더 선명해진 것과동작이 더 정확해진 것을 구분했는가?
3. target 외형·원본 동작·장면 중어떤 축에 회귀가 있었는가?
4. 기존 앵커의 충돌과현재 조건 경로의 한계는 여전히 남는가?
5. 비교 가능한 실행 시간·메모리·전체 추가 비용은 얼마인가?
6. 다음 방법 개발은1.3B를 유지할지,14B를 기준으로 둘지,
   아니면 현재 자료로 아직 결정할 수 없는가?

최종 보고는 실제 영상 링크와품질·비용 결론부터 제시한다.
검사·hash·전송 상세는 근거로 뒤에 둔다.

이번 두 결과 이후 종료한다.
다른 seed·prompt·sampler·모델·학습을 자동 시작하지 않는다.


## 참고 자료

[R1] 기존 C-002 결과와실행 코드
https://github.com/hyunlord/make-meme/tree/853ee952795246648b3a6e46d37d5dead03abef3/docs/research/experiments/C-002-sam-layout-conditioning

[R2] 기존 C-001 backend 계약
https://github.com/hyunlord/make-meme/blob/e69f8672722b91c1ad07273060d3cb68ffaf7ef1/docs/research/experiments/C-001-hybrid-endpoint-baseline/BACKEND_CONTRACT.md

[R3] 공식14B 모델·파일·설정
https://huggingface.co/Wan-AI/Wan2.1-VACE-14B
https://huggingface.co/Wan-AI/Wan2.1-VACE-14B/tree/main
https://huggingface.co/Wan-AI/Wan2.1-VACE-14B/blob/main/config.json

[R4] 현재 기록 revision의14B 추론 예제
https://github.com/modelscope/DiffSynth-Studio/blob/f39d731a3e318d25b725eb3389cfddb184619842/examples/wanvideo/model_inference/Wan2.1-VACE-14B.py

[R5] 같은 revision의저메모리 예제
https://github.com/modelscope/DiffSynth-Studio/blob/f39d731a3e318d25b725eb3389cfddb184619842/examples/wanvideo/model_inference_low_vram/Wan2.1-VACE-14B.py

공식 배포의main은 다운로드 시immutable revision으로 고정한다.
문서에 링크가 있다는 사실은Spark에서 이미 실행됐다는 뜻이 아니다.