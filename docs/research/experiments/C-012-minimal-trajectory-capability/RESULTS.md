# C-012 RESULTS — 같은 양끝에서 A를 주면 A로, B를 주면 B로 가는가 (2026-11-01)

## 한 줄
**예, 현재 point adapter에서 조건부로 그렇다.** 두 clip에 과적합시킨 2048 update checkpoint에서, 같은 양끝·같은 텍스트·같은 noise로 point 궤적만 바꾼 A/B 영상이 각각 요청 경로를 따랐다.
- 첫 seed 20261028: 평균 중심 오차 A 1.8px, B 1.6px, 9/9 시점 식별 → **CAPABILITY_PASS**
- 사전 고정한 두 번째 seed 20261029: 공 경로는 같은 정확도로 따랐지만(2.1/2.3px), 중간 프레임에서 배경 전체가 무너졌다 → PARTIAL_CONTROL
- 종합 판정: **SEED_SENSITIVE_CAPABILITY**

256·1024 checkpoint는 기준을 통과하지 못했다. 이 결과는 TRAIN_PAIR_MEMORIZATION / CAPABILITY_TEST다. 학습한 두 경로 밖의 일반화, 개체 교체, 실제 동물 동작 성공을 뜻하지 않는다.

## 1. 요청 경로와 실제 생성 경로 (사전 9시점, 416×240 좌표)
요청: 시작 (104,120), 끝 (312,120). τ0.5에서 A는 (208,72), B는 (208,168), 간격 96px.

| 방법 | A 평균 오차 | B 평균 오차 | 누락/중복 A·B | 중앙 쪽 맞음 A·B | τ0.5 간격 | matched / swapped | 배경 이동 | 판정 |
|---|---|---|---|---|---|---|---|---|
| ORACLE_RENDERER 정답 (생성 아님) | 0.03 | 0.03 | 0·0 | 5·5 | 96 | 0.02 / 54.9 | 0 | (fixture) |
| VAE 재구성 (진단, 생성 아님) | 0.02 | 0.02 | 0·0 | 5·5 | 96 | 0.02 / 54.9 | 0 | 과제 유효 |
| ENDPOINT_BASE (궤적 입력 없음) | 공이 시작 위치에 머문 뒤 흐려짐, t24·t28 누락 | — | 2 | — | — | — | 0 | 경로 없음 |
| NATIVE_LAYOUT (dense 윤곽) | 2.8 | 1.9 (관측 5점) | 0·4 | 5·1 | 누락 | 3.3 / 47.2 | 0 | NO_CONTROL(기계) |
| adapter 256 | 양끝 2점만 관측 | 19.1 (최대 38) | 7·0 | 0·5 | 누락 | 24.5 / 44.7 | 0 | NO_CONTROL |
| adapter 1024 | 3.3 | 2.4 | 1·2 | 4·3 | 99 | 3.9 / 54.0 | 0 | NO_CONTROL |
| **adapter 2048, seed 20261028** | **1.8** | **1.6** | **0·0** | **5·5** | **95** | **2.1 / 55.2** | **0** | **CAPABILITY_PASS** |
| adapter 2048, seed 20261029 | 2.1 | 2.3 | 0·0 | 5·5 | 95 | 2.8 / 54.8 | **93** | PARTIAL_CONTROL |
| DragAnything (첫 이미지+궤적) | 6.3 | 3.7 | 2·1(끝 부근) | 5·5 | 80 | 5.7 / 56.0 | 0 | PARTIAL_CONTROL |

판독기는 시작 앵커의 공 crop 하나를 template으로 쓰고, 전체 화면에서 TM_CCOEFF_NORMED로 찾는다(요청 경로를 입력하지 않음). peak < 0.50이면 누락이다. 수치와 평면도는 `METRICS.json`과 검토 뷰어에 있다.

## 2. 방법별 판정 (세 질문 분리)
**Q1 과제 유효성 — 확인.**
- 양끝은 byte 동일하고, 중앙 간격은 96px이다.
- 공이 모든 프레임에서 화면 안에 있고, 9점이 mask 안에 있으며, 배경은 바뀌지 않는다.
- VAE 재구성 A/B에서도 공이 peak ≥ 0.98로 식별되고 두 경로가 구분된다.
- fixture: 빈 배경은 missing, 공 두 개는 duplicate, 카메라 (9,6) 이동은 감지된다.

**Q2 현재 adapter — 최소 능력이 있지만 seed에 민감하다.**
- 256: B만 아래로 움직이고, A는 BASE에서 보이던 깨진 물체로 무너졌다.
- 1024: 두 경로로 분기했다. B는 τ0.25–0.375에서 외형이 흐려져 판독기가 놓쳤다.
- 2048 첫 seed: 기준 1–8을 모두 통과했다.
  - 단, A 영상에는 BASE부터 있던 녹색 잔해 물체가 공 옆에 함께 남는다. 판독기는 이를 공 중복으로 보지 않았지만, 외형 품질 결함이다(기준 9는 공 자체에 대해서만 통과).
- 2048 두 번째 seed: 공은 두 경로를 그대로 따랐지만, t4–t24 배경이 어수선한 장면으로 바뀌었다(표식 판독 이동 93px).
  - 이 배경 붕괴가 adapter 때문인지 seed 20261029의 BASE prior 때문인지는 분리하지 않았다. BASE seed 20261029는 예산에 없었다.
- 사전 규칙에 따라 다른 seed는 찾지 않았다.

**Q3 다른 제어 경로**
- **NATIVE_LAYOUT**(정답 mask 윤곽): A는 외형을 유지하며 정확히 따랐다(평균 2.8px).
  - B도 공 모양 덩어리가 B 경로를 따라가지만, 중간에 무늬가 사라진 갈색 덩어리가 되어 판독기가 4개 시점을 놓쳤다. 기계 판정은 NO_CONTROL이다. 시트로 보면 경로 제어는 있고 외형 유지에 실패한 것이다.
  - sparse point보다 많은 공간 정보를 받는 대조군이다.
- **DragAnything**(공식, SVD 기반, 사전학습 그대로): 중앙 5시점은 A/B 모두 맞는 쪽이고, 간격은 80px이다.
  - 후반에 공이 세로로 길쭉해지고 무늬가 바뀌어, A의 마지막 2개 표본과 B의 마지막 표본이 누락됐다. 끝 앵커 입력이 없는 모델이라 끝 위치·외형을 강제할 수단이 없다.
  - 판정은 PARTIAL_CONTROL이다.
  - 같은 backbone의 공정 비교가 아닌 기능 대조다.

## 3. A/B에서 실제로 같았던 것과 다른 것
모든 adapter A/B 쌍에서 동일했던 것:
- 첫 model_fn의 VACE context 96채널 sha(`2c7a6691…`)
- 초기 latent sha(seed별)
- checkpoint sha
- endpoint patch sha(`2f7eee07…`)
- valid/visible sha, motion_available=True
- text

달랐던 것은 point positions sha(A `559876f7…`, B `d29f1233…`)뿐이다.

- BASE·layout·adapter의 VACE context는 학습 cache와 exact로 일치했다(live parity).
- label·파일명은 lookup key로만 쓰고 신경망 입력이 아니다.
- 학습 cache 단계에서도 확인했다: A/B의 patches·anchor_valid·visible·valid·box·context·vace_context·양끝 좌표는 동일하고, 중간 좌표만 다르다.

## 4. 보조 probe (σ1.0 = 순수 noise state, A/B 입력 동일)
| ckpt | σ1.0 cos(δ, u_A−u_B) | σ0.5 cos | A matched / swapped loss (σ1.0) |
|---|---|---|---|
| 256 | 0.80 | 0.95 | 0.28 / 0.73 |
| 1024 | 0.86 | 0.96 | 0.22 / 0.88 |
| 2048 | 0.89 | 0.95 | 0.16 / 0.88 |

point만 바꾸면 예측 차이가 목표 차이 방향으로 정렬된다. C-010/C-011의 동물 자료에서는 −0.15~+0.07이었다. 다만 256에서도 0.80이었는데 영상은 실패했다. probe 정렬은 영상 제어 성공을 대신하지 못한다.

## 5. 결론과 방법 판단
의뢰서 §13 기준으로는 **A의 조건부 판정**이다.
- MINIMAL_CAPABILITY는 첫 seed에서 확인됐지만, 두 번째 seed는 배경 붕괴로 PARTIAL이다 → SEED_SENSITIVE_CAPABILITY.
- 확인한 범위는 "같은 양끝에서 학습한 두 2D 강체 경로를 point 조건으로 고를 수 있다"뿐이다.

판단:
1. **현재 residual 주입 구조는 폐기하지 않는다.**
   - C-010/C-011의 "ON ≈ NULL"은 구조가 궤적을 표현하지 못해서가 아니었다. 이 구조와 FM 목적은 궤적이 명확히 갈리는 자료에서는 분기를 학습한다. 추가 loss 없이 그렇다.
   - C-011이 제안한 "궤적 일치 보조 항"은 이 기능을 얻는 데 필요하지 않았으므로 **철회**한다.
2. **바로 확대하지 않는다.**
   - 두 clip을 2048회(약 32분)나 학습해야 했다.
   - 두 번째 seed에서 장면이 무너졌고, 녹색 잔해 같은 BASE prior 결함이 그대로 남았다.
   - 다음은 확대 학습이 아니라 일반화 시험이 먼저다.
3. **비교 경로**
   - DragAnything은 학습 없이 같은 분기를 부분적으로 보였다. 끝 앵커가 없어서 끝 구간 외형이 무너졌다.
   - native layout도 경로는 따르지만 한쪽 외형을 잃었다.
   - 이번 작은 과제에서 어느 방법도 "외형까지 유지한 완전한 통과"를 두 seed 모두에서 보이지 못했다. 현재 adapter를 우선순위에서 내릴 근거(B)도, 전환할 근거(C)도 없다.

다음 단일 조건(제안, 미실행):
- **같은 장면에서 학습에 없던 중간 경로(예: 진폭·방향이 다른 경로)로 시험한다.**
- 학습한 두 경로만 외운 것인지, 좌표→위치의 연속 관계를 배운 것인지 가른다.
- 반증: 학습하지 않은 경로에서 출력이 학습한 A/B 중 가까운 쪽으로 붙으면(matched < swapped 실패), 현재 학습은 분류 기억이다. 그 경우 좌표 표현과 자료 다양성을 먼저 다룬다.
- 두 번째 seed 배경 붕괴의 원인(adapter vs BASE prior)을 가르는 BASE seed 20261029 1개도 함께 필요하다.

## 6. 비용
- sampler 13: 우리 모델 11(BASE 1, layout 2, adapter 6, 두 번째 seed 2) + DragAnything 2. hard cap 14 이내, 품질 재시도 0.
  - 우리 모델 영상은 각 약 50초(CFG1, model_fn 50). DragAnything 2개를 포함한 단계는 329초(DIFT·로딩 포함), 최대 CUDA 26.5GiB.
- 학습: 2048 update, forward/backward 각 2048. 누적 active 1925초(32분, 상한 90분). peak 4.5GiB. 진단 forward 3, probe forward 24(상한 32).
- 기계 복구:
  - 1구간 첫 시도가 step 195에서 guard에 의해 중단됐다. 원인은 같은 시각 내가 돌린 DragAnything import 시험이 보호 서비스 경로 패키지를 읽은 것이다.
  - 같은 seed로 처음부터 다시 실행해 forward/backward 195를 더 썼다. schedule(clip·σ index)은 동일했고, loss는 GPU 비결정성으로 1e-4 수준 차이가 났다.
- VAE: cache·진단 public encode 6(상한 20), 진단 decode 2. sampler 내부 encode/decode는 영상마다 따로 정상 수행했다.
- DragAnything 준비: 약 64분(상한 90분).
  - 다운로드 11GiB(fp16 변형만, 상한 40GiB). 격리 venv 305MB(Torch는 기존 것 공유).
  - 실패 시도 6번: import 경로, transient unit 이름 중복, peft 버전, 출력 폴더 잔존, fp16 upcast 분기의 미사용 `dinov2` 속성, dtype 혼합. 이 중 2번(r4·r5)은 pipeline 호출까지 갔지만 denoising 전에 멈췄다.
  - 최종 실행은 공식 데모처럼 fp32다. 모델·알고리즘 변경은 없고 wrapper만 고쳤다.
  - 격리 venv 설치 중 pip가 의존성으로 torch 2.15를 venv 안에 받았다. 사용 전에 제거하고 기존 torch 2.14+cu130을 공유했다. 기존 VACE venv는 바뀌지 않았다.
  - 그 밖에 cache 단계 첫 시도는 guard 진입점을 잘못 호출해 GPU 실행 전에 멈췄다.
- SAM·CoTracker·imagegen·14B 0회. guard·메모리·서비스 정책 변경 0.
- 수동 검토: agent 정적 시트 확인. 독립 human 평가가 아니다. 연속 재생을 보지 않았으므로 temporal=UNVERIFIED다.

## 한계
- 과제가 의도적으로 쉽다: 2D 평행이동, 회전·가림 없음, 학습 경로와 평가 경로가 같다.
- 판독기는 공 template 하나로 읽는다. 외형이 크게 바뀐 공(layout B, DragAnything 끝)은 누락으로 처리된다. 이 경우 경로를 따른 사실은 시트로만 확인했다.
- 두 번째 seed BASE가 없어 배경 붕괴의 원인을 가르지 못했다.
