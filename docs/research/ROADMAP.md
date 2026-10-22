# B 트랙 로드맵

마지막 계획 갱신: 2026-10-22. 날짜가 아니라 증거를 기준으로 다음 단계로 이동한다.

| 단계 | 질문 / 목표 | 상태 | 다음 단계에 필요한 근거 |
|---|---|---|---|
| B-001 학습 기반 | Spark에서 toy 생성 모델과 VACE LoRA를 실제로 학습·추론할 수 있는가? | 실행 완료 보고 / 제한적 학습 경로 확인 | 기존 코드·설정·출력 보존; 일반화와 구분 |
| B-002 참조 배경 비교 | 같은 Lab 참조에서 배경만 바꾸면 결과 배경·자세에 어떤 영향이 있는가? | COMPLETED / 동작 전이 미수용 | 두 seed 배경 변화·착석 유지; [결과](experiments/B-002-reference-background/RESULTS.md) |
| B-003 구조 조건 비교 | R-bg 고정에서 실제/무정보 Canny 영향은? | COMPLETED / 직립 춤 미수용 | 2/2쌍 자세 변화,0/4직립; [결과](experiments/B-003-structure-condition/RESULTS.md) |
| 과제 적합 데이터 | 개체 외모와 동작을 분리해 학습할 수 있는 input/condition/target은 무엇인가? | BACKLOG | 허용된 데이터, scene/identity 단위 split, 정답과 누수 정의 |
| 제한된 학습 개입 | LoRA/adapter/조건 주입 하나가 어떤 실패를 줄이는가? | BACKLOG | 학습 전후 동일 조건 비교와 미학습 샘플 검증 |
| 확장 검증 | 더 긴 동작·큰 체형 차이·두 개체에서도 성립하는가? | BACKLOG | 실패율·자원·여러 seed, 외부 개체/동작 평가 |
| 서비스 / 논문 | 제품 가치 또는 연구 기여를 입증할 수 있는가? | 미결정 | 응용 반복 성공과 계산비용 / 선행 연구 대비 기여 |

## 현재 결정

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
