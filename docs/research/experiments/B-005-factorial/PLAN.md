# B-005 — 참조 × 구조 조건 2×2 요인 실험 완성 (사전 계획)

작성: 2026-10-22 · 상태: **PLANNED / NOT_RUN** · 상위 실험: B-002, B-003, B-004

## 0. 방향과 목표

B의 목표는 DGX Spark의 로컬 모델만으로 실질적인 반려동물 동작 전이를 학습·개선하고, 수식·실제 코드·실험을 연결해 연구 기반을 쌓는 것이다. A의 native imagegen·외부 영상 생성 API는 사용하지 않는다. 모델 검증과 서비스/논문 수용은 분리한다.

이번에는 `reference contents`와 `Canny structure contents`의 **조건 상호작용**을 관찰하기 위한 마지막 작은 제거/대체 실험으로 한정한다. 목표는 두 조건 모두 정보가 없을 때의 사전 경향을 포함해 네 조합을 비교하는 것. 이것이 개체·자세를 분리하는 새로운 생성법은 아니다.

## 1. 지금까지의 관측과 질문

- B-003: R-bg + C-real은 두 seed에서 착석, R-bg + C-null은 두 seed에서 사족. 모두 원본 직립 실패.
- B-004: R-bg + C-real은 동일 두 결과 재사용, R-gray + C-real은 seed 20261022 착석, 20261023 뒷발 직립 *형태*. 후자는 실제 Lab 외형·원본 안무 미수용.
- 이 결과는 input sensitivity의 근거이나, 구조 조건으로 *올바른 동작*을 전달했다는 증거가 아니다.

**실험 질문:** R-gray를 고정한 C-real과 C-null의 차이는 무엇인가? 같은 seed에서 얻은 B-003·B-004 기존 결과와 함께 보면 참조 내용과 구조 내용의 효과가 상호작용하는가?

## 2. 사전 등록된 2×2 × 2seed 매트릭스

| 참조 | C-real (원본 Canny) | C-null (all-zero RGB 영상) |
|---|---|---|
| R-bg (실제 Lab, 흰 배경) | **B-003 기존 2 seed 재사용** | **B-003 기존 2 seed 재사용** |
| R-gray (RGB128 단일 참조) | **B-004 기존 2 seed 재사용** | **이번 신규 2 seed만 실행** |

Seed `20261022`, `20261023` 고정. 기존 **6개** 결과는 완전한 실행 설정, 가중치/upstream 버전, decoded source/condition/reference/mask, **실제 initial noise**, CFG/steps/sigma_shift/vace_scale, adapter=null 및 요청 코드가 호환될 때만 재사용한다. 재사용 불가 시 임의 신규 baseline을 만들어 채우지 말고 BLOCKED와 근거를 기록한다.

**신규 추론 최대 2회(실패·거절·재시도 포함), 학습 0회**, 전체 작업 최대 2시간, Heavy GPU job 하나. B의 기존 격리 환경, Wan2.1-VACE-1.3B 모델과 pinned DiffSynth-Studio만 사용. 새로운 모델·생성 API·native imagegen·동물 이미지 생성은 없음. 자동 재시도·seed 탐색 없음.

공통: 512×288 / 17 frames / 24fps, BF16, SDPA, CFG5, 20 steps, sigma_shift5, vace_scale1, full-white video mask, 동일 prompt와 negative, 1 reference. C-null은 **실제 RGB 0의 프레임 17개**이고, VACE branch 제거/latent=0이 아니다. R-gray도 reference branch 제거가 아닌 VAE 인코딩된 RGB128 이미지다. `R-gray+C-null`은 학습 분포 밖 조합일 수 있다.

실행 전에 실제 GitHub `docs/research/CHARTER.md`, `ROADMAP.md`, `HISTORY.md`, `RECORDING_PROTOCOL.md`, B-003/B-004 RESULTS와 관련 실행·관측·검증 코드를 읽는다. git status와 실행 checkout(로컬 연구용) 대 문서 worktree를 구분하고, 강제 reset/clean, main push, 민감 파일 공개를 하지 않는다. PLAN과 resolved config·코드 hash를 결과 관찰 전에 원격에 고정한다.

## 3. 핵심 관측과 검증

1. 실행 중 동일 seed의 noise, 텍스트, mask, inactive/ reactive/ reference prefix의 실제 tensor shapes & hashes를 기록한다. 네 조건 간 기대와 다른 input 변경이 있으면 원인을 설명한다.
2. 8개 결과 모두 원본의 f0/4/8/12/16 contact sheet와 17장 전체 시트, source 비교 영상을 동일 fps/시간축에 놓는다. 실제 속도 시청이 없으면 시간 품질은 UNVERIFIED.
3. 프레임별 착석/사족/뒷발 직립/기타, 발 접촉/카메라 시점/움직임 크기, 실제 Lab 정체성·체형, 붕괴·배경·시간 불연속을 구분한다.
4. **출력에 변화가 있다는 것 ≠ Canny가 원본 안무를 전이했다는 것.** 고정·정지 출력이 유리한 점수만으로 통과하지 않게 한다.
5. 회색/검정의 인위적 중립 입력은 OOD일 수 있다. 둘 다 없다는 의미의 branch-off 또는 무조건 생성이라고 주장하지 않는다.

## 4. 수학과 실험 해석

출력을 `Y_{s,r,c}=G_θ(ε_s;R_r,C_c,T,M,λ)`로 정의한다.
선택한 q는 사전 정의된 *관측 가능한* 특징(예: 원본 대비 직립/동작 단계 대응, 형태 안정성)으로 둔다. 범주 판정은 범주 그대로 보고, 임의 연속형 품질 점수를 만들지 않는다.

조건 효과를 seed별로 관찰:
- `Δ_C(R-bg,s) = q(Y_s(R-bg,C-real)) - q(Y_s(R-bg,C-null))`
- `Δ_C(R-gray,s) = q(Y_s(R-gray,C-real)) - q(Y_s(R-gray,C-null))`
- 설명용 interaction `I_s = Δ_C(R-gray,s) - Δ_C(R-bg,s)`.

q가 수치 의미가 있는 관측치에만 위 차이를 적용한다. 자세 범주/소수 binary 성공은 2×2 표로 우선 제시하고, 2 seed의 상호작용 수치로 통계적 유의성·모델 전반의 인과관계를 주장하지 않는다. 이 interaction은 **특정 고정 모델·입력·seed의 개입 효과**일 뿐, 배경·자세·정체성 독립 역할은 식별하지 못한다.

한국어 학습 자료 `docs/research/lessons/B-005-conditioning-interaction.md`:
- factorial design, paired noise, difference-in-differences의 이론·가정·수식과 이 소규모 실험의 한계
- reference·structure VACE context 텐서 결합의 실제 코드/shape 연결
- OOD 조건, null RGB vs latent0/branch-off, text prior/CFG의 역할
- 간단한 질문 2~3개와 별도 해설.

## 5. 결과에 따른 한 번의 결정

B-005 종료 후 다음 세 범주 중 하나로 추천한다(자동 실행 금지):
- **조건 경로/입력 구현 오류**가 새로 확인됨 → 바로 그 문제만 수정/재검증.
- 입력은 올바르나 네 조합 모두 원본 동작을 제대로 재현하지 못함 → **Canny+reference 방식의 적합성 한계를 기록하고**, 다음에는 동작 전이에 특화된 로컬 모델의 짧은 공식 baseline 또는 실제 video/motion 조건을 더 직접 반영하는 표현을 선택. 동일한 제거 실험을 더 늘리지 않는다.
- 하나 이상 실제 원본 동작과 정체성을 동시에 충족함 → 같은 방식의 미사용 장면에 대한 검증 계획을 우선한다.

회색 참조에서 직립만 나타나도 실제 Lab identity가 없으므로 '동물 밈 생성 성공'으로 판정하지 않는다.

## 6. GitHub 히스토리·산출물

시작 전 계획과 실행 코드·resolved config를 commit/push하여 원격 확인. 주요 단계 후 RUNNING/HISTORY 갱신. 최종 `docs/research/experiments/B-005-factorial/RESULTS.md`, 실행 config·비민감 스크립트·해시·재현, `lessons/B-005-conditioning-interaction.md`, HISTORY, ROADMAP을 커밋/push. 공개 repo에는 개인 반려동물/영상/음원, raw 생성 MP4, 비밀값·개인 절대경로·대형 가중치·캐시 금지.

실제 MP4와 정적 비교 시트, private input hash/run ledger/비민감 공개 요약, 실제 재현 script를 한 ZIP으로 Mac과 Spark의 접근 가능한 `/tmp`에 보존하되 동일 경로가 동일 머신을 뜻하지 않음을 명시. ZIP integrity와 SHA 확인. 종료 후 프로세스 0건 또는 실제 상태 보고. 별도 후속 연구 실행 금지.

**최종 판정은 데이터로:** 이 실험 자체는 COMPLETE가 가능해도 자연스러운 Lab 춤, 두 개체, 15초·Kling 품질은 현재 NOT_RUN/NOT_ACCEPTED. 실제 연속 관찰이 없으면 시간 품질 UNVERIFIED.
