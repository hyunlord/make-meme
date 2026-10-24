# B 트랙 로드맵

현재 상태 갱신: 2026-10-25. 날짜가 아니라 증거를 기준으로 다음 단계로 이동한다.

**현재: B-024 RUNNING / GPU NOT_RUN.** [계획](experiments/B-024-reference-rgb-isolation/PLAN.md). 정식replacement와같은입력을유지하고reference비객체RGB만중립화해VAE/CLIP배경누수를한번검사한다. B023기술PASS/원본보존FAIL을보존한다. 연결확인은30분으로한정하고구체적결함은중단,원인UNKNOWN만으로무한감사하지않는다.

**B-017 당시 요약: COMPLETED_CPU_AUDIT / RIGHTS_PENDING / DATA_GAP.** [결과](experiments/B-017-paired-animal-data/RESULTS.md): 검토용 완비case2·Lab미완성후보1, training-ready0·실제cross-IDpair0. 충분한reference자세다양성은미입증이다. 다음은권한있는실제Lab자연동작자료확보하나이며생성·학습0. ALG/H120은기본채택하지않는다.

**B-015 당시 요약: COMPLETED / 고정 ALG pilot CLOSED.** [결과](experiments/B-015-alg-driving-control/RESULTS.md): 남은 ALG_STILL1회로2×2를 완성했다. 두 STILL은 상대적으로 선명한 착석, 두 MOV는 후반 머리 변화와 얼굴 손상이며 전신FAIL·목표품질NOT_ESTABLISHED·temporalUNVERIFIED다. 추가ALG탐색은 중단한다. 아래 과거 기록은 당시 상태다.

| 단계 | 질문 / 목표 | 상태 | 다음 단계에 필요한 근거 |
|---|---|---|---|
| B-001 학습 기반 | Spark에서 toy 생성 모델과 VACE LoRA를 실제로 학습·추론할 수 있는가? | 실행 완료 보고 / 제한적 학습 경로 확인 | 기존 코드·설정·출력 보존; 일반화와 구분 |
| B-002 참조 배경 비교 | 같은 Lab 참조에서 배경만 바꾸면 결과 배경·자세에 어떤 영향이 있는가? | COMPLETED / 동작 전이 미수용 | 두 seed 배경 변화·착석 유지; [결과](experiments/B-002-reference-background/RESULTS.md) |
| B-003 구조 조건 비교 | R-bg 고정에서 실제/무정보 Canny 영향은? | COMPLETED / 직립 춤 미수용 | 2/2쌍 자세 변화,0/4직립; [결과](experiments/B-003-structure-condition/RESULTS.md) |
| 과제 적합 데이터 | 개체 외모와 동작을 분리해 학습할 수 있는 input/condition/target은 무엇인가? | BACKLOG | 허용된 데이터, scene/identity 단위 split, 정답과 누수 정의 |
| 제한된 학습 개입 | LoRA/adapter/조건 주입 하나가 어떤 실패를 줄이는가? | BACKLOG | 학습 전후 동일 조건 비교와 미학습 샘플 검증 |
| 확장 검증 | 더 긴 동작·큰 체형 차이·두 개체에서도 성립하는가? | BACKLOG | 실패율·자원·여러 seed, 외부 개체/동작 평가 |
| 서비스 / 논문 | 제품 가치 또는 연구 기여를 입증할 수 있는가? | 미결정 | 응용 반복 성공과 계산비용 / 선행 연구 대비 기여 |

## 초기 결정 — 당시 기록 보존

B-002에서는 새 학습 update를 하지 않는다. B-001에서 학습한 도시 복원과 Lab 춤 전이는 다른 과제이므로, 도시 LoRA 학습량 증가를 Lab 실패 해결책으로 사용하지 않는다.

## B-002 이후의 조건부 분기

- R-bg에서 방 배경만 줄고 착석 자세가 남음: 배경 영향의 국소적 근거. 다음에는 자세와 구조 조건의 경쟁을 연구한다.
- R와 R-bg가 비슷하게 실패: 제거 방식·mask·공식 condition 처리·고정 sampling 설정의 한계를 검토한다. 모델 능력 부재로 즉시 일반화하지 않는다.
- P가 원본 구도에 더 가까움: source와 reference의 정합성이 영향을 줄 수 있다. P는 검은 Lab를 요구하는 같은 prompt를 유지하므로 순수한 동일 개체 복원 대조군이 아니라는 점을 함께 해석한다.
- 입력 처리에 실제 결함 발견: 이번 실험을 INVALID_SETUP 또는 BLOCKED로 기록한다. 수정 전후 결과를 한 통제 실험으로 섞지 않고 새 revision을 계획한다.

이 분기는 자동 추가 실행 허가가 아니다. 한 비교 후 다음 실험 하나만 제안한다.

## 변경 이력

- 2026-10-22: B-001 완료 보고를 이관하고 B-002를 사전 계획했다. 장기 목표, 학습 목표와 품질 목표를 분리했다. P 대조군의 prompt/reference 충돌을 명시했다.

## B-002 실제 결론 (2026-10-22)

두 seed에서 참조 배경의 구체적 복사가 줄었지만 착석 자세는 남았다. P 직립은 실제Lab 개체 일치나 Canny 효과의 독립 증거가 아니다. 다음 실험은 R-bg와 나머지 조건을 고정한 Canny/무정보 Canny 한 요인 비교만 제안한다. 아직 NOT_RUN이며 새 학습·모델·추가 생성 승인이 아니다.

## B-003 착수 (2026-10-22)

사용자가 위 조건부 비교를 승인했다. [B-003 PLAN](experiments/B-003-structure-condition/PLAN.md): R-bg 고정, 실제/무정보 Canny × 두 seed의 frozen baseline 비교. 상태 PLANNED, 학습0회, 전체제작 승인이 아니다. 이전 NOT_RUN 문구는 B-002 종료 당시의 상태다.

## B-003 실제 결론 (2026-10-22)

신규4/4완료·학습0·실패0. 실제 구조 latent 변화 및 두 seed의 real착석/null사족 차이는 구조 영향이 있음을 지지한다. 원하는 직립 춤 전달은0/4이며 reference 단독 지배도 확정할 수 없다. 다음 하나는 C-real 고정에서 R-bg 대 균일 회색 reference 한 장 비교다. 개체정보도 제거되므로 품질개선 아닌 조건기여 진단이며 아직 NOT_RUN/미승인이다. 기존 B-003 착수 PLANNED 항목은 시작 당시 기록이다.

## B-004 계획 등록 (2026-10-22)

- 상태 **PLANNED / NOT_RUN**. C-real을 고정하고 균일 회색 참조(R-gray)와 기존 Lab R-bg를 비교한다. [B-004 PLAN](experiments/B-004-reference-neutral/PLAN.md).
- 기존 B-003 C-real의 두 seed를 실제 조건·노이즈 검증 후 재사용하면 새 추론은 최대 2회이며 학습은 0회다. 이 재사용이 불가능하면 결과를 억지로 짝짓지 않고 BLOCKED로 보고한다.
- 연구 질문은 reference 시각정보 개입에 대한 출력 민감도이며, identity/pose를 독립 분리한 결과나 실제 춤 전이의 수용이 아니다.

## B-004 실제 결론 (2026-10-22)

COMPLETED: 신규2·재사용2·학습0. R-gray에서1/2seed직립형태,1/2착석. 참조내용민감도는관측됐으나실제Lab개체/안무전이미수용. Canny고정이므로직립의구조인과효과미식별. 시간UNVERIFIED. [결과](experiments/B-004-reference-neutral/RESULTS.md). 다음하나는R-gray고정C-real/C-null비교제안이며NOT_RUN/미승인. 기존PLANNED는사전기록이다.

## B-005 계획 등록 (2026-10-22)

- 상태 **PLANNED / NOT_RUN**. [B-005 PLAN](experiments/B-005-factorial/PLAN.md).
- R-bg/R-gray × C-real/C-null의 2×2 요인 비교를 두 seed에서 완료하는 마지막 작은 frozen 조건 제거 실험. 기존 B-003의 4개 및 B-004의 2개를 엄격 검증 후 재사용하여 **R-gray+C-null 두 회만 신규 실행**, 학습0.
- 결과가 네 조합 모두 원본 춤+실제 Lab identity를 충족하지 못하면 같은 입력 제거 실험의 반복을 중단하고, 실제 동작 조건을 더 직접적으로 쓰는 로컬 동작 전이 baseline/표현 연구를 선택한다. 서비스·논문 가치를 앞서 선언하지 않는다.

## B-005 실제 결론 (2026-10-22)

COMPLETED: 신규2·재사용6·실패0·학습0. 전체2×2×2seed통제검증통과,모든조합에서실제Labidentity+원본춤동시수용실패. 입력민감도와seed에따른반응차이는있지만유용한동작전이미입증. 시간UNVERIFIED. [결과](experiments/B-005-factorial/RESULTS.md).

동일Canny/reference제거실험은여기서종료한다. 다음하나는명시적동물관절궤적·가시성·발접촉표현의원본동작보존및모델연결적합성검증이다. 아직NOT_RUN/미승인이며자동설치·학습·추론하지않는다. 이전PLANNED기록은사전상태로보존한다.


## B-006 연구 방향 전환 (2026-10-22)

- **PLANNED / NOT_RUN**: [B-006 PLAN](experiments/B-006-motion-representation/PLAN.md).
- B-002~005의 input sensitivity 진단은 완료. 조건 형태를 바꿔도 8셀 모두 실제 Lab 정체성과 원본 안무를 동시 수용하지 못했으므로 **동작 표현/모델 조건 인터페이스 적합성**을 다음 연구 대상으로 정한다.
- 다음은 17프레임에서 Canny/관절·가시성·접촉/RGB driving의 동작 정보 보존 능력, 공식 SCAIL-2 및 현 VACE의 실제 입력 경로, DGX Spark 환경의 실용성을 비교한다.
- **B-006의 GPU 생성/학습 모델 실행 0회**; 새로운 pretrained 14B 체크포인트 다운로드·설치도 없음. 예산·구현 가능성 검사 후 B-007의 제한된 공식 baseline 한 건을 별도로 결정. 단순 keypoint 시각화만으로 생성 모델이 그 조건을 지원한다고 주장하지 않는다.

## B-006 실제 결론 (2026-10-22)

**COMPLETED: 동작 표현 감사·공식 모델 인터페이스 검토.** 원본17프레임에서 보이는 표면점119개와 미관측170개를 구분하고, 실제 관절 중심/3D 접촉을 지어내지 않았다. CPU overlay·궤적·heatmap 완료는 생성 성공과 다르다. [결과](experiments/B-006-motion-representation/RESULTS.md).

다음 한 경로는 **B-007 공식 SCAIL-2 Wan RGB driving의 제한된 baseline**이다. 현재 FlashAttention 의존성 부재, ARM64/GB10 kernel·변환/로딩 peak UNKNOWN,16fps 기본 출력과 원본24fps의 차이가 선행 조건이다. 모델 파일 약80GB 및 추가 변환 공간은 별도 예산을 필요로 한다. 설치·추론·학습은 이번에 실행하지 않았고 다음 승인 전 자동 시작하지 않는다. 임의 animal skeleton을 VACE에 대입하거나 Canny/reference 제거 실험을 반복하지 않는다.

## B-007A 사전 실행 가능성 검증 (2026-10-22)

- 상태 **PLANNED / NOT_RUN**. [B-007A PLAN](experiments/B-007-scail-preflight/PLAN.md).
- 목표: SCAIL-2 Wan RGB driving baseline을 새 80GB 다운로드 전에 DGX Spark GB10에서 실행 가능한지 판단. 실제 flash-attn 호출 형태·SM121 kernel smoke, reference/driving 색상 mask 의미와 24fps 원본 시간축, crop, checkpoint 변환 중 메모리/디스크 위험 확인.
- B-007A는 모델 전체 다운로드0/영상 diffusion 추론0/학습0; 격리 환경의 bounded dependency 설치/작은 attention 연산만 예정. 통과도 14B model load 및 Lab 춤 성공 증명이 아니다.
- 다음 별도 결정 B-007B: 정식 체크포인트 확보·변환·공식 예제와 실제 단일 컷 추론. 이번 PLAN만으로 자동 승인하지 않는다.

## B-007A 실제 결론 (2026-10-22)

**COMPLETED: 실제 작은 FlashAttention kernel PASS4.** CPU 색상 mask/geometry/timebase 검증 완료, 경계 PARTIAL. 전체 모델 변환/로딩/추론과14B peak는 아직 NOT_RUN/NOT_MEASURED다. [결과](experiments/B-007-scail-preflight/RESULTS.md). 다음 하나는 별도 승인된 B-007B SCAIL-2 Wan RGB driving baseline이며, 현재는80GB 다운로드·추론을 시작하지 않는다. 이전 PLANNED/RUNNING은 역사 기록으로 보존한다.

## B-007B — 실제 모델 baseline (2026-10-22 사전 계획)

- 상태 **PLANNED / NOT_RUN**. [B-007B PLAN](experiments/B-007B-scail-baseline/PLAN.md).
- B-007A FA2 BF16 tiny QKV4/4 PASS는 전체14B 실행 증명이 아님. checkpoint 대용량 eager load·safetensors load의 peak 위험이 있음.
- **게이트 순서:** fresh Spark 자원/색상 mask·24fps → 소형 fixture로 메모리 안전 SAT→Wan 변환 방식 검증 → 필요 파일 최대85GB selective download → 변환/로딩 자원 측정 → 공식 예제 1건 및 Lab 실제 단일17f 1건까지 조건부 추론.
- 신규 전체 diffusion inference 최대2회·학습0·다른 작업 비간섭. memory safe path 증명 못 하면 대형 변환을 강행하지 않고 BLOCKED. 영상이 나오면 동작·개체·시간적 품질을 독립 평가하며 Kling 수용 주장을 피한다.

## B-007B 실제 결론 (2026-10-22)

**BLOCKED / baseline 미확보.** 소형변환검증·필수다운로드해시는통과했지만실제SAT의NumPy pickle globals를안전metadata검사가거부했다. 전체변환·모델·영상NOT_RUN,추론0/2·학습0. 모델능력이나FlashAttention실패의증거가아니다. [결과](experiments/B-007B-scail-baseline/RESULTS.md).

다음한경로는동일공식checkpoint의비텐서RNG메타데이터를객체실행없이안전하게분리하고tensor/storage동등성을검증할수있는지감사하는것이다. 이를확인하기전추론재개·다른모델·LoRA학습을자동진행하지않는다. 이전B007B계획과B007A통과기록은역사기록으로유지한다.

## B-007C — checkpoint 비텐서 RNG 메타데이터 감사 (2026-10-22)

- **PLANNED / NOT_RUN**. [B-007C PLAN](experiments/B-007C-checkpoint-audit/PLAN.md).
- B-007B는 tensor checkpoint 다운로드 성공 이후 NumPy pickle globals 관련 **명시적 fail-closed 정책**에서 BLOCKED. 실제 대형 변환·SCAIL 로딩/생성/학습을 아직 시도하지 않았다.
- 다음 목표는 원본 SAT ZIP/data.pkl의 pickle GLOBAL+memo/storage 관계를 **객체 실행 없이** 감사하고, 공식 tensor-only export 또는 안전한 제한 loader 경로의 위험·동등성 증거를 확보하는 것. 새로운 실험용 fixture 외 실제 checkpoint에 broad allowlist/weights_only=False 사용 금지.
- 모델 재다운로드0, diffusion 추론0, 학습0. 감사만 완료돼도 full 14B inference PASS가 아니다. 안전한 경로를 확보한 경우에만 다음 bounded conversion/model baseline을 별도 검토.

## B-007C 실제 결론 (2026-10-22)

**AUDIT_PASS: 고정 checkpoint 비실행 의존성 감사 + 소형 제한 loader 검증 + 후속 한 경로 선정.** NumPy globals의 RNG 전용 구문 의존성과 원본 SHA 보존을 확인했다. synthetic legacy alias/dynamic dtype/CPU storage parity는 검증됐지만 실제65GB 로딩·변환·모델 실행은 NOT_RUN이다. [결과](experiments/B-007C-checkpoint-audit/RESULTS.md).

다음 후보 하나는 **원본 SHA·환경 고정, 실제 격리 검증, exact scoped safe_globals/weights_only CPU mmap의 metadata-only 확인을 선행하는 bounded tensor-only 변환**이다. 실제 제한 loader의 메모리·storage parity와 보안 격리는 후속 실행에서 검증해야 한다. B-007B 영상 baseline은 여전히 미확보이며 다음 단계 승인 전 대형 변환·모델·추론을 자동 시작하지 않는다.

## B-007D — 실제 체크포인트 제한 로딩·조건부 변환 (2026-10-22)

- **PLANNED / NOT_RUN.** [B-007D PLAN](experiments/B-007D-safe-conversion/PLAN.md).
- B-007C의 pickle graph 감사와 작은 fixture는 필요한 선행근거이나 실제 65GB 로딩 무위험/메모리 fit을 증명하지 않는다. 다음 단계는 **OS 격리 검증 → 실제 65GB metadata-only FakeTensor / weights_only + 정확한 scoped NumPy4종 확인 → 제한적 실제 변환** 순서다.
- 실패/새 global/격리 미구현/자원 부족 시 BLOCKED로 종료하고 모델 변환을 강행하지 않는다. full SCAIL 14B 모델 load·diffusion 영상 생성·학습은 B-007D에서 0회로 유지. checkpoint 재다운로드도 하지 않는다.
- 실제 tensor mapping·dtype·shape·값 검증까지 완료하면 그 다음 단일 경로는 **별도 승인된 모델 로딩과 짧은 공식/Lab 영상 추론**이다.

## 2026-10-22 — B-007D 실제 제한 변환 완료

**CONVERSION_PASS, 모델 실행·영상 baseline NOT_RUN.** OS 격리·정확한 scoped globals·실제 metadata 통과 후 두 번째이자 마지막 CPU mmap load로 SAT→Wan tensor-only 변환을 완료했다. 원본987개에서 mapped1,307개를 만들고 모든 값 hash·dtype·shape·QKV 순서와 원본 SHA를 검증했다. 전체 변환 guard456.759초, cgroup cap32GiB, 표본 RSS 약53GiB(서로 다른 회계), OOM0. 실제 load2회·재시도0. [결과](experiments/B-007D-safe-conversion/RESULTS.md), [이론](lessons/B-007D-real-checkpoint-loading.md).

다음 하나는 별도 승인된 SCAIL 모델 적재·공식/Lab17프레임 제한 baseline이다. CPU 변환 성공은 GPU 모델 fit·영상 동작·개체 품질 성공이 아니다. 이번에는 모델·추론·학습을 시작하지 않았다.

## B-007E — 실제 모델 적재와 RGB driving 최초 baseline (2026-10-22)

- 상태 **PLANNED / NOT_RUN**. [B-007E PLAN](experiments/B-007E-scail-forward/PLAN.md).
- B-007D SAT→Wan F32 65.58GB safetensors 변환/전체 tensor parity PASS는 실제 모델·GPU forward 통과를 보장하지 않는다. loader의 FP32 weight 일시적 중복·T5/CLIP/VAE/activation과 128GB 통합메모리 중복 계산 위험을 선행 점검.
- 최대 두 가지 bounded 로딩 방법만 검증. 적재 가능할 때 공식17프레임 기준선 1회와 Lab17프레임 RGB-driving 1회(max diffusion sampler 2회), 학습0·대형 재다운로드0. 실패한 gate에서는 안전하게 BLOCKED·메모리 실측 제출.
- 이번 목표는 실제 모델의 최초 영상 결과와 자원·개체·동작·시간평가 기준선을 확보하는 것. 자동으로 15초/두 동물/LoRA/후속 모델로 확대하지 않는다.

## 2026-10-22 — B-007E 실제 적재·첫 forward 통과, 영상 출력 차단

**LOAD_PASS / FIRST_FORWARD_PASS / VIDEO_OUTPUT_BLOCKED.** 실제 SCAIL pipeline은268.587초에 적재,1,307tensor strict검사와12,992-token 첫 finite forward를 통과했다. 공식 sampler1회에서40/40 progress 뒤 post-sampler offload/decode 경계의 MemAvailable23.899GiB가24GiB 하한을 밑돌아 자기 프로세스만 종료했다. 정확한 종료 subphase는UNOBSERVED이며 OOM/FlashAttention 실패로 단정하지 않는다. 최종 raw/MP4/denoisedlatent 없음, Lab NOT_RUN, 추론1/2·학습0·다운로드0. [결과](experiments/B-007E-scail-forward/RESULTS.md).

다음 하나는 final latent 저장·phase hook과 post-loop DiT GPU 유지 경로의 제한된 메모리 전이 검증이다. 별도 승인 전 새 sampler·모델·학습을 자동 시작하지 않는다. 기존 계획·과거 NOT_RUN은 해당 시점 기록으로 보존한다.

## B-007F 착수 (2026-10-23)

**RUNNING / sampler NOT_RUN.** [PLAN](experiments/B-007F-post-sampler-memory/PLAN.md). B-007E의 메모리 전이 가설을 검증하기 위해 post-loop DiT CPU 이동 한 곳만 생략하고, decode 전 final latent·실제 완료 counter를 보존한다. 공식 예제 실패 시 Lab는 실행하지 않는다. 같은24GiB headroom 유지, 신규 sampler 최대2회·3시간·학습0. 실패 시 저장 latent의 decode만 다음 후보로 남기며 자동 실행하지 않는다.

## B-007F 실제 결론 (2026-10-23)

**BLOCKED / MP4·final latent 미확보.** 전체 적재331.44초 후 첫 DiT forward 이전의 headroom guard로 공식1/2 시도가 종료됐다. 초기 noise만 보존됐고 변경한 post-sampler 정책은 NOT_REACHED다. Lab NOT_RUN, 추가 sampler·학습0. [RESULTS](experiments/B-007F-post-sampler-memory/RESULTS.md).

다음 한 작업은 기존 E/F trace·코드에 대한 첫 forward 이전 메모리 수명 CPU-only 감사다. 실제 final latent가 없으므로 decode-only 재개는 아직 불가능하다. 새 모델 로딩·추론은 별도 결정 전 자동 실행하지 않는다.

## B-007G 착수 (2026-10-23)

**RUNNING / P·S·D NOT_RUN.** [PLAN](experiments/B-007G-phase-separated-baseline/PLAN.md). F는 post-sampler 변경에 도달하지 않았으므로 그 정책을 반증하지 않는다. 제한된 E/F CPU 비교와 함께 조건·DiT·decode의 불필요한 동시 상주를 줄이는 순차 프로세스 구조를 시험한다. 같은 공식17f16fps·noise·scheduler·dtype·24GiB 하한을 유지하며 새 sampler 최대1회다. 실패 시 재시도하지 않고 저장된 조건/최종 latent와 정확한 경계를 남긴다.

## B-007G 종료 (2026-10-23)

**CONDITION_CACHE_PASS / S_FAILED / D_NOT_RUN.** P143.331초에 실제 조건과 동일 initial noise를 저장했다. S121.054초 시도는 CPU DiT 적재 후 첫 조건의 CUDA 복원에서 `cuDevicePrimaryCtxRetain` OOM으로 종료됐고 sampler loop·첫 forward에 도달하지 않았다. 24GiB 가드 종료가 아니며 정확한 드라이버/메모리 원인은 UNKNOWN이다. 신규 슬롯1/1 사용, 재시도0, final latent/MP4 없음. [결과](experiments/B-007G-phase-separated-baseline/RESULTS.md).

다음 하나는 기존 P 캐시를 활용하는 S의 CUDA context/CPU weight 수명 사전 진단이다. decode-only용 final latent는 없으며 새 sampler는 자동 실행하지 않는다.

## B-007H 착수 (2026-10-23)

**RUNNING / probe·S·D NOT_RUN.** 원격 `51daacac291f161a21edeac3a551375fdd24f08c`와 [PLAN](experiments/B-007H-cuda-lifecycle/PLAN.md)을 확인했다. G의 조건 캐시를 재사용하며 P는 반복하지 않는다. 같은 서비스 환경의 작은 실제 CUDA 연산과 leaf별 복원 검증을 선행하고, 통과하면 별도 worker에서 CPU DiT 적재 전 CUDA 연산을 수행한다. initialized flag와 실제 연산 성공을 구분하며 원인을 사전 확정하지 않는다. probe1·CPU DiT load1·sampler1·decode1 상한, 선행 실패 시 후속 중지, 기존72/24GiB·swap0 가드 보존.

## B-007H 종료 (2026-10-23)

**PROBE/S/D PASS / 공식17프레임 MP4·final latent 확보.** G 조건을 재사용하고 CPU DiT 적재 전 실제64-byte CUDA 연산을 완료했다. S1회에서80 forward·40step, D1회에서896×512·16fps·1.0625초 영상을 저장했다. guarded S1199.009초/D15.228초, 최소 MemAvailable52.44GiB, swap/OOM0. P·재시도·Lab·학습0. G 원인UNKNOWN과 시간 품질UNVERIFIED를 유지한다. [RESULTS](experiments/B-007H-cuda-lifecycle/RESULTS.md).

다음 하나는 기존 Lab 참조/RGB/mask의 제한된17프레임 baseline이다. 별도 결정 전 자동 실행하지 않는다.

## B-008 착수 (2026-10-23)

**RUNNING / Lab P·PROBE·S·D NOT_RUN.** 원격 `c7d38938e51943576637611cdec9ae51902e0d65`와 [PLAN](experiments/B-008-lab-rgb-baseline/PLAN.md), [단계 전환 결정](decisions/20261023-B-007H-to-B-008.md)을 확인했다. H의 공식 MP4 확보를 기반으로 실행 진단에서 실제 Lab 품질 연구로 옮긴다. 성공한 tiny CUDA 선행/anchor·단계 분리·loader를 유지하고 기존 실제 사진/RED mask/f0~16으로 Lab 전용 P를 만든다. 가로 공식값을 삭제해 우회하지 않고 case별 manifest로 검증한다. 3시간, P1/PROBE1/S1/D1·학습0·재시도0. 결과 관찰 전 코드·config를 고정한다.

## B-008 종료 (2026-10-23)

**P/PROBE/S/D PASS / Lab MP4·final latent 확보 / 직립 동작 전달 FAIL.** 실제17f24fps·512×896,40step80forward, 신규 sampler1회·재시도/학습0. 전체17장 정적 검토에서 검은 Lab 외형은 유지됐지만 참조의 착석·침실 구도가 남아 원본 직립/앞발 동작을 재현하지 못했다. 특정 개체UNCERTAIN, temporalUNVERIFIED. S1066.317초, D15.219초, 최소MemAvailable51.978GiB,swap/OOM0. [RESULTS](experiments/B-008-lab-rgb-baseline/RESULTS.md).

다음 한 실험은 동일 source 동물의 첫 프레임을 참조로 한 RGB-driving 자기 재현 진단이다. 기본 동물 움직임 재현과 cross-identity/체형 전이의 어려움을 구분하려는 계획이며 새 실행은 별도 결정 전 시작하지 않는다.

## B-009 착수 및 B-008 해석 보완 (2026-10-23)

**RUNNING / P·PROBE·S·D NOT_RUN.** [독립 검토 결정](decisions/20261023-B-008-review-and-B-009.md)에 따라 자기 재현보다 [reference mask 단일 변경](experiments/B-009-reference-mask-semantics/PLAN.md)을 우선한다. 기존 Lab mask의 정확한BLACK만WHITE로 바꾸고RED·RGB·driving·text·모드·seed·sampler는 유지한다. B-008을 대조군으로 재사용하며 새 P/PROBE/S/D 각1회·sampler1회·재시도/학습0이다.

해석 정정: animation의WHITE는 참조 배경 가시성 조건이므로 침실이 남는 것 자체를 실패로 판단하지 않는다. B-008의 직립 전달 실패 관측은 유지한다. 공식 mixed-fps 학습 설명상 writer16fps 기본값을 고정16fps 학습 분포의 증거로 사용할 수 없다. 과거 기록은 보존하고 현재 해석을 이 항목으로 보완한다.

## B-009 종료 (2026-10-23)

**실행/조건통제 PASS · 직립/앞발 전달 FAIL.** 각P/PROBE/S/D1회,40step80forward,17f24fps MP4와 final latent 확보. 양 CFG WHITE prefix만 바뀌고 나머지14leaf는비트동일했다. 전체17장 정적 검토에서 B-008/B-009 모두 착석과 내려놓은 앞발을 유지했다. WHITE 하나로 충분하지 않으며 침실 유지 자체는 실패가 아니다. 실제 개체UNCERTAIN,temporalUNVERIFIED. S1093.089초/D15.233초,최소가용51.975GiB,swap/OOM0,cgroup high2101. [RESULTS](experiments/B-009-reference-mask-semantics/RESULTS.md).

다음 후보 하나는 source-first-frame 자기 재현과 생성 없는first-frame-repeat 정적 대조군의 동작 비교다. 직립 복사만으로 성공 처리하지 않으며 판별 어려우면INCONCLUSIVE. 이번에는 실행하지 않았다. 추가 생성/학습은 별도 결정 전 진행하지 않는다.

## B-010 착수 (2026-10-23)

B-009 WHITE 단일 변경으로 직립/앞발 전달이 회복되지 않아 색상 탐색을 끝내고 [동물 자기 재현](experiments/B-010-animal-self-reenactment/PLAN.md)을 진단한다. 원본f0를 reference로 사용하고 실제17프레임의 변화가 STATIC COPY보다 잘 전달되는지를 묻는다. GPU 전에 표면점 관측가능성과 기준을 고정하며 직립 복사 자체는 성공이 아니다. 새P/PROBE/S/D각최대1회·sampler1·재시도/학습0. 현재 NOT_RUN. [진행](experiments/B-010-animal-self-reenactment/RUNNING.md).

## B-010 생성 전 중단 (2026-10-23)

**DIAGNOSTIC_INSUFFICIENT / GPU NOT_RUN.** source f0 반복 STATIC COPY를 먼저 만들고 보이는 표면점20개 비교를 수행했다. E_copy15.5107px가 전파된 평균 관측오차19.4222px보다 작고 앞발 변화도 오차 범위였다. 일부 머리 위치 변화는 관측됐으나 전체 이동/배율과 분리한 관절 동작 증거가 부족했다. 원본 무동작이나 모델 실패가 아니라 현재 주석 정밀도의 한계다. P/PROBE/S/D모두0, 새로운 latent/생성영상 없음. [RESULTS](experiments/B-010-animal-self-reenactment/RESULTS.md).

다음 한 작업은 동일17프레임의 실제512×896 표면점 직접 재주석 CPU 감사다. 이를 이번에 수행하거나 새 sampler/구간/seed로 자동 확대하지 않았다.

## B-011 착수: 측정 정밀도와 탐색 생성 분리 (2026-10-23)

**RUNNING / 생성 NOT_RUN.** B-010의 DIAGNOSTIC_INSUFFICIENT는 유지한다. [B-011 PLAN](experiments/B-011-exploratory-self-reenactment/PLAN.md)은 같은17프레임에서 일부 화면상 변화가 관측되는 정상 입력의 탐색 생성1회를 허용한다. 정확한 관절 정량성이 부족하면 해당 B평가는 INCONCLUSIVE이며 A의 시간 변화 관측까지 계속 미루지 않는다. 원본/STATIC COPY/출력 전체를 비교하고 단순 직립·전체 흔들림을 안무 성공으로 올리지 않는다. 이후에도 불명확하면 같은17장 재주석 반복 대신 더 명확한 source-only 구간 검토 한 가지를 후속 후보로 남긴다.

## B-011 실제 결론과 다음 한 작업 (2026-10-23)

**COMPLETED / 실행 PASS / A화면 변화 대응 근거 / B관절 운동 INCONCLUSIVE.** 자기 재현1회에서17f24fps·finite final latent를 확보했다. 원본과 비슷한 화면 변화는 관측됐고 고정20변위의 raw 잔차는 정적 복사16.5407px/생성3.5212px였다. 그러나 출력 오차가 보정되지 않았고 앞발 위치가 불확실하여 gain UNDEFINED·temporal UNVERIFIED이며 Lab cross-identity 전이 성공은 아니다. [RESULTS](experiments/B-011-exploratory-self-reenactment/RESULTS.md).

후속 후보는 기존 원본의 더 명확한 머리·앞발 상대 움직임을 가진 짧은 구간을 **source-only로 검토**하는 한 작업이다. 같은17프레임 재주석을 다시 반복하지 않는다. 새 구간 생성·seed·low-pass·모델 변경·학습은 NOT_RUN이며 자동 실행하지 않는다. 이전 착수 NOT_RUN은 당시 이력이다.

## B-012 착수 (2026-10-23)

**RUNNING / 생성 NOT_RUN.** [PLAN](experiments/B-012-clear-motion-driving-control/PLAN.md)에 따라 source-only 최초 적합 구간을 고정하고, 같은reference/text/noise에서 동적 RGB+mask(MOV)와 첫RGB+첫mask 반복(STILL)의 모델 생성pair를 비교한다. 정적출력 STATIC COPY와 정적입력 STILL을 구분한다. 단순 변화량·직립이 아닌 source 상대 사건의 방향·순서·시점을 평가하며 정확한 좌표는 불확실성을 유지한다. 최대2sampler·각1회·4시간·학습0, 추가전이/low-pass/seed/모델은 실행하지 않는다.
## B-012 입력 고정 (2026-10-23)

source-only 후보3개 중 f7~23을 고정했다. 동일reference/text/noise의 MOV 대 STILL로 RGB+mask 시간 정보의 추가 기여를 검토한다. CPU 입력·계약 검증 완료, 실제 sampler는 아직 NOT_RUN. 기존 B-011의 정밀 운동/기여 미입증을 보존하며 [실행 기록](experiments/B-012-clear-motion-driving-control/RUNNING.md)을 따른다.

## B-012 종료: 동적 driving의 제한된 상대 동작 근거 (2026-10-23)

**COMPLETED / 실행·조건 통제 PASS / temporal UNVERIFIED.** source-only f7~23에서 MOV/STILL 각각 P/PROBE/S/D1회·40step80forward·17f24fps MP4와 final latent를 확보했다. 양 CFG driving4leaf만 변경되고 나머지12leaf는 실제 bit-exact였다. 전체17장 정적 검토에서 MOV는 후반 머리-몸통 상대 roll의 방향·순서를 원본에 가깝게 재현했고 STILL은 초기 자세 부근이었다. 한 same-identity pair의 동적RGB+mask 공동 기여에 대한 탐색적 근거이며 정밀 앞발·접촉·Lab 전이는 미입증이다. sampler2/2·실패/재시도/학습0, 최소 시스템가용52.095GiB·swap/OOM0. [RESULTS](experiments/B-012-clear-motion-driving-control/RESULTS.md).

다음 연구 제안은 같은 [7,24) 구간의 실제 Lab cross-identity 전이 비교 하나다. NOT_RUN이며 이번에 추가 생성·모델·학습을 시작하지 않았다. 앞선 단계의 RUNNING/NOT_RUN 기록은 당시 이력으로 보존한다.

## B-013 착수: 같은 driving에서 Lab 전이의 전신·국소 제어 분리 (2026-10-24)

**RUNNING / GPU NOT_RUN.** 시작 원격 `28a8540172768481efad7013281a7ce649985245`의 [PLAN](experiments/B-013-lab-driving-transfer/PLAN.md)과 [결정](decisions/20261024-B-012-review-and-B-013.md)을 확인했다. B-012 same-identity의 동적RGB+mask 기여를 실제 Lab 과제에서 비교한다. 기존 source[7,24) 처리RGB/mask 및 결과2개를 보존·재사용하며 새LAB_MOV/LAB_STILL만각1회다. Lab 내부가 주 통제이며 source/Lab 사이 reference·자세·체형·장면·text 차이를 순수identity효과로 부르지 않는다. 전신직립·국소머리roll·실제개체를 별도 평가한다. 4시간·sampler최대2·재시도/학습0, codegraph경고는TOOLING_WARNING으로 분리한다. [진행](experiments/B-013-lab-driving-transfer/RUNNING.md).

## B-013 조건 통과·생성 진행 (2026-10-24)

양 Lab P 완료. 실제 pair4변경/12보존 및 대응 B-0127변경/9보존 통과이며 보존 leaf는 모두 bit-exact다. 새 Lab reference/task 조건을 생성한 것이며 source cache 전체를 재사용하지 않았다. 품질 판단은 두 PROBE/S/D 결과의 사전 사건·전체17장 관측 이후로 남긴다. [진행](experiments/B-013-lab-driving-transfer/RUNNING.md).

## B-013 종료: 착석 전신과 국소 머리 반응의 분리 (2026-10-24)

**COMPLETED / 실행·조건 PASS / 전신 FAIL / 국소 PARTIAL / temporal UNVERIFIED.** LAB_MOV/LAB_STILL 각각 P/PROBE/S/D1회·40step80forward·finite final latent·17f24fps MP4를 확보했다. pair4변경/12bit-exact, 대응 B-0127변경/9bit-exact로 입력 계보를 확인했다. 전체17장 정적 검토에서 두 출력 모두 착석·지지 앞발이 남았다. LAB_MOV의 후반 머리 반응은 더 크지만 눈·주둥이·귀 번짐으로 충실한 roll·실제 개체 유지 수용은 어렵다. 단순 검은 Lab 유사성과 실제 반려견 일치를 구분한다. sampler2/2·실패/재시도/학습0, 최소가용46.139GiB·swap/OOM0, cgroup high4242/3670은 공개한다. [RESULTS](experiments/B-013-lab-driving-transfer/RESULTS.md).

다음 연구 하나는 SCAIL reference conditioning에 ALG의 시간별 참조 완화 원리를 적용할 수 있는지 검토하고 전신 자세 대 개체 보존의 통제 실험을 설계하는 것이다. 공식3branch와2→3forward 비용, 저주파 착석 실루엣·identity 약화 위험, SCAIL 미검증을 명시한다. 이번에는 수정·추론·학습 NOT_RUN이며 자동 실행하지 않는다. 앞선 RUNNING 기록은 당시 이력으로 보존한다.

## B-014 착수: 입력 비교에서 제한된 sampling 개입으로 (2026-10-24)

**RUNNING / CPU 이식 검증 중 / GPU NOT_RUN.** 원격`152b6771397176ac0eb1860debc0902331c5d523`의 [PLAN](experiments/B-014-alg-scail-pilot/PLAN.md)과 [결정](decisions/20261024-B-013-review-and-B-014.md)을 확인했다. B-013의 전신FAIL/국소PARTIAL/얼굴번짐을 보존하며 단순움직임증가를 목표로 삼지 않는다. 공식ALG의 원본negative 기준항을 보존한3항식을 ref-latent 공간필터로 이식하고, CPU계약·사전코드고정이 통과할 때만 기존LAB_MOV조건으로 pilot1회 수행한다. ratio0.4·45×26·bilinearAA·i0..7고정,40step88forward; P0·retry0·학습0·3시간. 새모델·ALG_STILL·추가seed·강도탐색은 실행하지 않는다. [진행](experiments/B-014-alg-scail-pilot/RUNNING.md).

## B-014 실제 결론 (2026-10-24)

공식 ALG3항식의 SCAIL 이식과 단일 pilot은 완료했다. LP는 자세 제거기가 아니며 착석·후기 형태 손상을 해결하지 못했다. 부분적인 초중반 가독성 차이를 전신 동작 또는 전체 개체 보존 성공으로 확장하지 않는다. 모델 설치·추가 baseline·학습은0회다.

다음 연구 하나는 고정 ALG_STILL 한 대조군으로 guidance×driving 상호작용을 확인하는 진단 제안이다. NOT_RUN/별도승인 전이며 강도탐색·추가seed·학습·SR·모델교체를 자동 실행하지 않는다. 이전 B014착수 RUNNING은 당시 기록이다.

## B-015 착수: 고정 ALG pilot 비교 종료를 위한 한 셀 (2026-10-24)

**RUNNING / GPU NOT_RUN.** [PLAN](experiments/B-015-alg-driving-control/PLAN.md)에 따라 기존 세 결과를 보존하고 ALG_STILL 하나만 실행한다. reference/text/noise는 같고 MOV/STILL의 driving RGB+mask만 다르다는 실제 cache 계약을 먼저 확인한다. P0·PROBE/S/D각최대1, 재시도0. 새 sidecar의 STILL parent binding을 유지하고 B-014 수식·필터·스케줄을 바꾸지 않는다. 이 비교 뒤 현재 ALG pilot은 종료하며 정적인 외형 보존을 동작 개선으로 해석하지 않는다.

## B-015 종료 (2026-10-24)

P0·PROBE/S/D각1·40step88forward·finite final latent·17f24fps MP4를 확보했다. 실제4변경/12보존, 새STILL parent sidecar와기존MOV필터값동일, 원본보존을검증했다. 네셀모두착석으로전신FAIL이며두MOV의후반얼굴손상을두STILL의안정성으로뒤집지않는다. 고정ALGpilot은CLOSED이며기본값승격/추가강도/seed탐색없음. [결과](experiments/B-015-alg-driving-control/RESULTS.md). 다음가설하나는animation을유지한reference RoPE H offset만의통제개입으로, 자세전용제거가아닌위치관계변화의검증이다. 아직구현/실행NOT_RUN이며별도결정이필요하다.

## B-016 착수 (2026-10-24)

**RUNNING / GPU NOT_RUN.** 고정 ALG pilot을 종료하고 기본 CFG로 복귀한다. 원격 `6ef151b090d6c839e99d84a3547e7671f128e5ac`의 [PLAN](experiments/B-016-reference-rope-h/PLAN.md)에 따라 기존 LAB_MOV 캐시16leaf와 모든 입력·sampler를 보존한 채 animation reference RoPE H만120으로 지정한다. 격리 코드/CPU fixed-QK 계약/실제 import를 먼저 검증하며 기존 H0 결과를 재사용한다. P0·PROBE/S/D각최대1·40step80forward·3시간·retry/학습0. 이 hybrid가 학습분포 내라는 주장이나 replacement 전체 재현은 하지 않는다. [진행](experiments/B-016-reference-rope-h/RUNNING.md).

## B-016 종료 (2026-10-24)

**COMPLETED / 실행·ref-H 단일 개입 PASS / 전신 FAIL / 품질 개선 NOT_ESTABLISHED / temporal UNVERIFIED.** P0·PROBE/S/D각1·40step80forward, 실제 canonical patch와40blocks×80회 위치검사, 원본16leaf 보존을 확인했다. finite final latent와17f24fps MP4를 확보했지만 H120도 착석·지지 앞발이며 후기 머리/얼굴 손상이 남았다. 일부 차이를 원본 roll·실제 개체 동시 개선으로 올리지 않는다. S1057.032초·최소가용52.605GiB·swap/OOM0. [RESULTS](experiments/B-016-reference-rope-h/RESULTS.md).

ALG는 기본 채택하지 않고 offset sweep도 종료한다. 다음 가설 하나는 동물 identity/reference 자세 분리를 학습할 허가된 paired 데이터의 타당성 감사다. 다른 개체를 Lab 정답으로 쓰지 않으며 이번에는 데이터 수집·학습·추가 생성 NOT_RUN이다.

## B-017 착수 (2026-10-24)

**RUNNING / 생성·학습0.** ALG/H120을 기본 경로로 채택하지 않고, 허용된 실제 자료로 R/D/Y 학습 예제를 구성할 수 있는지 조사한다. 시작 HEAD `ffe0369682eb2b0c3a903c44a2f23d5ff91b2299`, [PLAN](experiments/B-017-paired-animal-data/PLAN.md), [선정 규칙](experiments/B-017-paired-animal-data/SELECTION_RULES.md). SELF_RECON_SMOKE·SAME_ID_POSE_VARIATION·실제 CROSS_ID_MOTION_PAIR와 권한 상태를 별도 판정한다. 기존 source 개발구간을 독립test로 바꾸지 않으며 다른 개체나 생성실패를 Lab target으로 승격하지 않는다. 3시간CPU중심, 최대8case; 다음 학습은 자동 실행하지 않는다.

## B-017 종료 (2026-10-24)

**COMPLETED_CPU_AUDIT / RIGHTS_PENDING / DATA_GAP.** 등록자료12asset에서 source-file 검토case2개와 실제LabY가없는후보1개를구성했다. 실제CPU14media역할decode·shape·fps·PTS·복사hash통과, 두sourcecase D=Y동일, 독립test0. self파일구조는있지만 원본진위/학습권한UNKNOWN으로training-ready0; f0/f7참조다양성NOT_ESTABLISHED; 실제cross-IDpair0이다. [RESULTS](experiments/B-017-paired-animal-data/RESULTS.md), [학습해설](lessons/B-017-paired-data-and-flow-training.md). 공식Wan/SAT경로의Y·R·D·first_frame/history/loss·genericLoRA와실제recipe차이를확인했다. 생성·모델load·VAEencode·optimizer0. 다음한작업은권한있는실제Lab자연동작영상과다른자세reference/촬영session확보이며, 추가학습·생성은실행하지않는다. ALG/H120은기본경로로채택하지않는다.

## B-018 착수 (2026-10-24)

**RUNNING / 구성요소 검사 준비.** 실데이터 권한·target 부족은 그대로 남지만, synthetic hidden tensor로 LoRA 연결과 공식 FA backward를 별도로 검사한다. [계획](experiments/B-018-lora-component-smoke/PLAN.md)의 단일 모듈·worker1회·최대3 update 경계를 유지한다. 전체 영상 학습과 데이터 확보는 이번 실행에 포함하지 않는다.

## B-018 종료 (2026-10-24)

**단일 attention 구성요소의 실제 backward·adapter update·reload PASS.** synthetic 수치검사로 학습 배선을 분리해 검증했으며 동물data/권한은 여전히 미확보다. 전체모델학습·영상품질·개체/자세분리는NOT_RUN, 정적typing은NOT_CLEAN이다. [결과](experiments/B-018-lora-component-smoke/RESULTS.md). 다음 제안은 동일synthetic계약을 마지막transformerblock 전체로 한 단계 확장할 때의 gradient/메모리 검증 계획 하나다. 추가실행은 하지 않으며 ALG/H120 기본미채택과 이전 실패기록을 유지한다.

## B-019 착수 (2026-10-24)

**RUNNING / 전체 block의 수치 배선 검사 준비.** attention 단독 PASS를 실제 영상 학습으로 확대하지 않고 cross-attention·FFN·residual을 포함한 마지막 한 block을 검사한다. 소형 update/reload와 긴 토큰 자원 결과는 별도 판정한다. 이후 component 숫자만 늘리는 자동 실험은 하지 않으며 B-017의 허용 실데이터 부족은 별도 DATA_PENDING이다.

## 2026-10-24 B-019 종료: 마지막 block의 실제 gradient 경로

[RESULTS](experiments/B-019-transformer-block-backward/RESULTS.md): 소형8forward/3backward/3update·fresh reload/OFF PASS, 긴12,992token 한block1forward/1backward/update0 PASS. FA2실제 backward와 cross/FFN derivative·image/text context gradient를 확인했다. 총worker1·9forward·4backward·3update, 재시도0. 긴CUDA peakallocated5.816GiB는 전체모델 학습 보증이 아니다. B-017실데이터/권한 DATA_PENDING은 유지하며 다음 목표는 권한확인된 실제Lab 자연동작의 동일개체 조건부FM 소형overfit 하나다. 이번에 전체모델/영상/실데이터학습은 NOT_RUN이며 추가component 시리즈나학습은 시작하지 않는다.

## 2026-10-24 B-020 준비 확인: DATA_PENDING, 실행 미착수

최신 원격 `82d22372693a641aa78eaa7974b0a269dab81665`의 [PLAN](experiments/B-020-real-fm-tail-overfit/PLAN.md)을 확인했다. B-019로 구성요소 smoke는 종료한다. 이번 요청에는 실제 Lab 자연동작 Y/R와 사용 범위가 새로 제공되지 않아 기존 데이터 부족을 유지한다. 같은 권한 감사·synthetic 대체 실험·GPU 실행은0이다. [준비 상태](experiments/B-020-real-fm-tail-overfit/STATUS.md)에 누락자료와 실행 재개 조건을 한 번 기록했다. 실제 자료·실행 지시 이후 입력/시간축·3학습tuple/1동일clip 보조tuple·공식FM/head 계약과 코드를 확정할 때만 착수를 기록한다. 현재 PLANNED / DATA_PENDING / GPU NOT_RUN이며 학습을 시작하지 않았다.

## 2026-10-24 B-020 실제 자료 제공 후 착수

**RUNNING / 입력 CPU 확인 완료 / GPU 아직 NOT_RUN.** 사용자가 새 자연동작 영상과 기존 앉은 Lab 사진의 동일 개체 및 비공개 연구 학습·평가 사용을 확인했다. 새 자료의 권한 게이트를 해소하되 B-017의 과거 제3자 자료 권한 부족은 보존한다. [입력 확정](experiments/B-020-real-fm-tail-overfit/INPUT_AMENDMENT.md): 최초 적합 f126~142,30fps,896×512 letterbox, D=Y SELF_RECON_FM_SMOKE. 실제 Y VAE velocity target의 고정3학습/1동일clip noise-time holdout, 마지막block Q/V LoRA 최대20update로 넘어간다. synthetic 구성요소 실험 반복·cross-ID 일반화·전체모델 학습은 이번 목표가 아니다. CPU계약과 런타임 소스 검토 이후 코드/config/hash를 고정하고 단계별 안전 조건하에만 실행한다.

### B-020 실제FM 기술단계 완료·영상 비교 진행

고정prefix와 미분가능한고정head를 사용한 실제Lab FM tail20update/reload/OFF를 완료했다. 생성품질·reference활용·cross-ID 분리는 별도이며 학습후영상 비교가 진행 중이다. 추가튜닝은 수행하지 않는다.

## 2026-10-24 B-020 종료: 실제FM 연결 PASS, 품질 개선 미입증

[RESULTS](experiments/B-020-real-fm-tail-overfit/RESULTS.md): 사용자 허용 실제Lab 자연동작17frame/30fps로 P1·prefix4tuple·실제FM tail20update/10eval·전후sampler각40/80·decode각1을 완료했다. parity/reload/OFF max_abs0·base불변, 고정train/holdout MSE는 소폭 감소했다. 그러나 전후 모두 착석 reference 자세·배경과 후반 머리잘림이 남아 target의서있는전신 FAIL/품질개선 NOT_ESTABLISHED, temporal UNVERIFIED다. 모든자체GPUworker종료·재시도0·swap/OOM0, cgroup high이벤트는실측대로보존한다. 다음은같은조건의사전고정100update로 적합량부족 가설을검사하는연구하나만제안하며 이번에는실행하지않는다. D=Y shortcut·동일clip noiseholdout·cross-ID/일반화 NOT_RUN을유지한다.

## 2026-10-24 B-021 착수

B-020의 실제FM 배선 PASS와 품질개선 미입증을 보존하며, 같은 고정3tuple·초기adapter·optimizer에서20대100update를 비교한다. **RUNNING / 사전검증 중**이며 P/prefix 재계산·새 데이터 감사·rank/lr/layer 탐색은 하지 않는다. 100회 범위 이후 자동 증량 없이 [PLAN](experiments/B-021-fixed-tuple-update-budget/PLAN.md)의 관측에 따라 다음 가설 하나만 고른다.


## 2026-10-24 B-021 종료: update20 replay 중단

[RESULTS](experiments/B-021-fixed-tuple-update-budget/RESULTS.md): 실제 initial+fresh AdamW로20update·8평가를 수행했다. 네 scalar loss replay는 PASS지만 네 adapter tensor는 사전 elementwise 기준을 초과해21이전 중단했다. 0/20 adapter·optimizer·RNG·cursor 저장/readback은 PASS,50/100·새 sampler/decode는 NOT_RUN이다. 100회 품질 효과는 미확인이며 원인은 UNKNOWN이다. 같은 입력의 FA2 backward 수치 반복성 가설 하나만 다음 연구로 제안하고 추가 실행은 하지 않는다. 사후 tolerance 완화·자동 재개는 하지 않으며 과거 품질 미입증을 보존한다.

## 2026-10-24 B-022 착수

독립실행의 엄격한 A/B replay와 동일 checkpoint의 기능 복원을 분리한다. B-021 FAIL은 유지한다. [B-022](experiments/B-022-resumed-update-comparison/PLAN.md)는 저장된20회 상태에서80회만 추가하고 matched20/100을 비교하는 한정 실험이다. 현재 CPU 준비/GPU NOT_RUN, 추가 튜닝·커널 변경·200회 확대는 하지 않는다.

## B-022 최종 상태 (2026-10-24 UTC / 2026-10-25 KST)

위 CPU준비/GPU NOT_RUN은착수당시기록이다. 실제로정확한B02120회상태에서추가80update·matched20/100각sampler/decode를완료했다. 고정4tupleloss감소·재개/reload/base검사PASS이지만사족자세FAIL·품질개선NOT_ESTABLISHED·temporalUNVERIFIED다. 기존B021FAIL은보존한다. [최종결과](experiments/B-022-resumed-update-comparison/RESULTS.md). 자동증량하지않으며새상위방향의B023공식replacement는PLANNED/NOT_RUN이다.

## 2026-10-25 B-023 착수: 원본 보존 편집의 과제 적합성

최신 원격 `fee6896bea73a2cd2a3b5f6c7f5baf062eb505d3`와 B-022 종료를 확인했다. B-023 기존 실행 디렉터리/활성 작업이 없는 상태에서 CPU 입력·계보 검증을 시작했다. B020 실제 Lab f126..142·30fps·896×512·미학습 기준선을 유지하고 ref RED/BLACK + driver RED/WHITE + 공식 replacement를 묶어 비교한다. 과거 밈2case/ROI 후보는 이번 범위가 아니다. 신규 sampler 최대1·decode1, 학습/다운로드/합성0; 미실행 상태에서 코드·EditSpec·조건 차이를 사전 고정한다. 최종 목표는 단일 Spark의 원본 보존 객체 편집이며 이번은 그 첫 제한 기준선이다. 결과에 따라 다음 병목 하나만 선택한다.

## B-023 종료와 범위 유지

상위 목표는 단일Spark의 원본 보존 객체 편집이다. 정식모드 실행이 그 목표의 성공을 보장하지 않았다. EditSpec parser·새MCP·ROI/가림복원·다중객체·효율화는 후속 후보이며 이번에는 구현하지 않았다. 결과 기반 다음 병목 선택을 유지하고 추가생성·학습·합성을 자동 시작하지 않는다.

## 2026-10-25 B-024 착수: 참조 RGB의 배경·padding 분리

[B024 PLAN](experiments/B-024-reference-rgb-isolation/PLAN.md)에 따라 B023정식replacement과제FAIL을보존하고, 같은Lab의reference에서기존REDsupport밖RGB만128로바꾸는한정비교를착수한다. 원본보존객체편집의병목을조건경로에서좁히며VAE/CLIP두경로재계산,semanticmask/모드/noise불변을검증한다. 현재CPU준비/GPU NOT_RUN, 연결확인최대30분·전체3시간·sampler최대1이다. 배경제거는자세제거가아니며새학습/모델/합성은없다.
