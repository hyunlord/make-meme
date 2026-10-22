# B-004 사전 계획 — 참조 시각 정보 제거의 영향 (reference-content ablation)

작성: 2026-10-22 · 상태: **PLANNED / NOT_RUN** · parent: B-003 · GitHub 등록은 새 추론이 수행됐다는 뜻이 아님.

## 1. 연구 질문과 사전 가설

B-002: Lab 참조 사진의 배경을 흰색으로 바꾸자 배경 복사는 줄었으나 착석이 남았다.
B-003: 같은 R-bg에서 Canny(real)과 all-zero(C-null)를 바꾸자 두 seed 모두 real=착석, null=사족으로 달라졌다. 그러나 뒷발 직립 원본 춤은 **0/4**였다. 구조 입력은 출력에 영향을 주지만 원하는 자세 전달에 실패했다.

이번 질문 하나:

> **구조 C-real을 고정하고 reference의 이미지 내용을 Lab R-bg에서 균일 회색으로 바꾸면, 출력의 착석·직립·개체/배경이 어떻게 달라지는가?**

- 가설 H1(탐색): Lab 참조의 시각 내용이 착석을 유도하는 데 기여했다면 회색 참조에서 착석 빈도 또는 형태가 달라질 수 있다.
- H0/대안: 차이가 작거나 직립이 여전히 실패할 수 있다. 회색 참조로 자세가 달라져도, 이 개입은 **외형·자세·정체성 정보를 동시에 제거**하므로 특정 정보만의 인과 효과나 reference-pose 전용 기여를 식별하지 못한다.
- 별도 강조: 회색 이미지를 넣는 것은 **reference branch off/삭제와 다르다.** 회색 RGB는 VAE로 인코딩되어 모델에 들어간다.
- 이 실험은 **diagnostic**이지 동일 개체를 잘 만드는 성능 향상 실험이 아니다.

## 2. 경계와 기존 자산

- A는 동결. B만 사용하며 native imagegen·외부 생성 API·유료 GPU는 금지.
- 기존 Wan2.1-VACE-1.3B revision `574e6a744642ce3bee319afc31496b88bde8aac4`; DiffSynth `f39d731a3e318d25b725eb3389cfddb184619842`의 로컬 실제 파일과 SHA를 확인한다.
- 모든 adapter=null; 학습 optimizer update **0**; 새 모델 다운로드/학습 없음. B-001 도시 LoRA는 사용하지 않는다.
- 동일 원본 동작 `f0..f16` 17프레임, 512×288, 24fps, C-real(Canny70/150), full-white VACE video mask.
- 동일 prompt/negative, BF16, SDPA, cfg=5, sampling_steps=20, `vace_scale=1`, `sigma_shift=5`, scheduler, reference 수 1, 인코딩·pad 규칙; 실제 resolved configuration 검증.
- 평가 seed `20261022`, `20261023`. 모델/정밀도/전처리/시간축/텍스트를 결과 보고 바꾸지 않는다.

## 3. 비교 조건과 최대 호출

| 조건 | 참조 이미지 | 실행 |
|---|---|---|
| **R-bg + C-real** | B-002에서 배경만 흰색으로 만든 실제 Lab R-bg | **기존 B-003 C-real 두 seed 재사용** |
| **R-gray + C-real** | 동일 크기의 균일 **RGB(128,128,128)** 이미지 | seed별 1회, **최대 2회 신규** |

- 중요한 전제: B-003 C-real 기존 결과와 현재의 모델·code hash·resolution·frames·prompt·CFG·sampling_steps·mask·Canny·reference preprocessing·scheduler·initial noise hash가 비교 가능한지 **첫 생성 전에 확인**한다.
- 비교가 안 되는 설정이면 **조용히 기존 영상을 재사용하지 마라**. 이번 최대 2회만 허가되어 있으므로 불완전한 쌍을 억지로 채우지 않고 BLOCKED/부분 완료로 기록하고 중단한다. 승인량 4회로 올리지 않는다.
- 회색 원본 크기/EXIF/비트 깊이는 실제 R-bg decoder가 처리한 형태와 동일하도록 제작한다. 생성 후 모델에 전달된 reference `reference.png`와 prefix latent **shape/hash**를 확인한다.
- `R-gray`는 reference RGB 내용의 단일 개입이다. 텍스트의 'black Labrador', 'reference photo'와 충돌할 수 있으므로 프롬프트는 이번에는 유지하되, 이 충돌을 결과 해석에 명시한다.
- **실제 신규 end-to-end inference 상한 2회**, 실패·실행 중단 포함. 자동 재시도 0회. 전체 작업 2시간 이내, 무거운 GPU 작업 1개. 시스템/다른 작업에 간섭하지 않는다.

## 4. 사전 장부·관측 확인

- 실행 전 로컬의 실제 B-003 코드·검증 자료·원본 파일 존재 및 SHA를 확인한다. 입력 파일이 없으면 찾았다고 추정하지 않는다.
- 모델의 reference encoder와 VACE context 관계를 실제 pinned 코드에서 추적한다. reference 한 장을 넣는 것과 branch 제거의 차이를 설명한다.
- 같은 seed에서 실제 `noise`, positive/negative `context`, inactive/reactive 구조 조건, mask가 일치하는지 해시로 확인한다. **reference prefix만 바뀐다는 기대**를 기록하고 실측과 다르면 다른 변경도 분리한다.
- 파생된 `R-gray` RGB 파일/모델이 실제 받는 `reference.png`, hash, decoded shape/값을 보존한다.
- B-003의 type/lint 검사 미통과 사항을 성능 실험과 구별하고 필요한 경우 영향을 받는 실행 코드만 검사한다. lint가 없어도 정적 검사를 성공으로 꾸미지 않는다.
- 학습 전용 가중치나 cache를 적용한 것처럼 보고하지 않는다.

## 5. 사전 등록 평가와 해석

세부 비교: seed마다 실제 원본 17프레임, R-bg output, R-gray output의 f0/4/8/12/16 + 전프레임 시트 및 비교 MP4(정확한 24fps/17프레임).

관찰할 지표:
1. 자세 범주(착석/사족/뒷발 직립/기타), 지지 발 수와 실제 원본의 상대적 움직임 단계.
2. Lab 정체성(회색 참조가 실제 Lab를 잃는 것은 예상 가능한 손실), 귀·얼굴·체형 및 구조의 붕괴.
3. 배경·참조 복사와 새 방/스튜디오 생성.
4. 시간: 실제 연속 재생 미관찰이면 **UNVERIFIED**. 정지 시트만으로 시간 품질 PASS 금지.
5. 자원: wall time, peak allocated/reserved, OS available, swap, 실패.
6. 실험 목표: **C-real이 reference 이미지가 회색이 되어도 뒷발 직립을 전달할 수 있는가**. 단순히 착석→사족을 직립 성공으로 계산하지 않는다.

해석 제한:
- 회색 참조에서 직립이어도 **Lab identity는 제거된 조건**이므로 애완동물 전이 성공이 아니다.
- 둘 다 착석이어도 'reference 영향 0'으로 단정 금지(회색 자체의 분포 효과, 텍스트, 모델 prior 등이 남음).
- 두 seed와 한 짧은 장면이므로 논문·서비스 일반화 아님.
- 단계가 종료되면 다음 실험 **하나만** 제안하고 자동 실행하지 않는다.

## 6. 공부·수학

한국어 학습 자료 `docs/research/lessons/B-004-reference-condition.md` 생성:
- VACE의 실제 코드와 tensor shape를 기준으로 reference prefix가 어떻게 구성되는지.
- 조건부 벡터장 `v_theta(z_t,t,c_struct,c_ref,c_text)`에 대해 `c_ref`를 바꿨을 때 무엇이 비교되고 무엇을 식별 못 하는지.
- 동일 noise로 paired comparison하는 의미와 seed가 동일하더라도 완전 결정론이 보장되지 않는 이유.
- 이미지 제거 vs 해당 조건 분기 ablation, out-of-distribution neutral reference의 차이.
- 직관 → 수식/가정 → 실제 모듈/텐서 → 이번 관찰 → 해석 한계 → 질문 2~3개/별도 해설.
- 생성된 출력이 없이 예상만 쓸 경우 관측한 것처럼 말하지 않는다.

## 7. GitHub/산출물 필수 기록

**실제 추론 시작 전** 이 PLAN을 새 실험의 사전 등록으로 사용하고, `docs/research/HISTORY.md`·`ROADMAP.md`에 B-004 PLANNED 기록을 커밋/원격 push한다. 실행 코드/config/hash도 결과를 보기 전에 고정한다. 이미 공개된 이 PLAN을 조용히 수정하지 않는다. 변경 시 amendment 기록.

끝나면 `docs/research/experiments/B-004-reference-neutral/RESULTS.md`, 실행 기록/재현, `lessons/B-004-reference-condition.md`, `HISTORY.md`·`ROADMAP.md`를 갱신하고 commit/push한다. 원격 SHA 대조; 실패 시 SYNC_PENDING. `main`/A 수정, force push, reset/clean, 자동 merge 없음. 연구 코드 checkout의 기존 미추적 파일 보존. 기존 `RECORDING_PROTOCOL.md` 준수.

공개 리포지토리에는 **개인 반려동물 사진·집 안 영상·음원·private 경로·raw 출력 MP4·weights/cache/tokens**를 올리지 않는다. 비민감 코드/config (경로 별칭 사용), MD/집계/해시만 공개.

최종 Mac/Spark 양쪽의 접근 가능한 위치를 구별해 작은 검토 ZIP(비공개)을 `/tmp/`에 생성하고 CRC/파일 hash 검사한다. 정확한 원격 문서 URL/branch/commit, 성공·실패·NOT_RUN, 사용한 생성 호출 수, next experiment 하나를 보고한다.

## 8. 차단·중지

실험용 모델/입력 부재, 비교가능한 B-003 재사용 실패, 실제 정밀도/모델 불일치, 권한 없음, 자원 부족, out-of-scope 작업 필요 시 추가 inference 없이 BLOCKED로 기록한다. sudo·OS/드라이버·swap·다른 실행 프로세스 변경 금지. 완료 결과를 사람이 실제로 재생 검수하지 않았다면 temporal UNVERIFIED 유지.
