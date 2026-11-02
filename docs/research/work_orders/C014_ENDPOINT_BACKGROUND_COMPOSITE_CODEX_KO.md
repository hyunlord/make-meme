# C-014 실행 의뢰서
## 양끝 관측 배경을 재사용하는 CPU 후합성 — 위치 제어·외형·경계의 분리 평가

**새 Codex 세션용 · 기존 DGX Spark/Mac 자료 사용 · 추가 학습·모델 추론 0회 · 파생 합성 영상 3개**

> **이 문서는 실행 승인이다. 아래 범위에서 C-014를 실제로 진행해 줘.**
> 의뢰서를 요약하고 같은 범위의 승인을 다시 기다리지 않는다. 실제 도구의 승인·접근 권한·안전 정책은 준수한다. 이번 요청은 아래 연구 작업을 실행할 Codex에게 전달하는 지시이며, 문서를 작성한 대화에서 Spark 작업이 이미 실행됐다는 뜻은 아니다.

| 항목 | 내용 |
|---|---|
| 저장소 | `hyunlord/make-meme` |
| 부모 결과 | C-013 / `11b4313c8d9c1b1c17ccdff70b9b75216cce3868` |
| 공통 장면·앵커·평가기 | C-012 / `6fba3a00d587bc0f130420e0f5b8c264b5e7a548` |
| 재사용할 선행 구현 | B-032 CPU 원본 보존 합성의 blend·출력 불변성 검사 |
| 연구 branch 단서 | `docs/c-research-20261028` — 실제 상태 확인 |
| 새 실험 경로 | `docs/research/experiments/C-014-endpoint-background-composite/` |
| 의뢰서 보존 | `docs/research/work_orders/C014_ENDPOINT_BACKGROUND_COMPOSITE_CODEX_KO.md` |
| 동봉 설정 | `C014_PREDECLARED_CONFIG.json` — 정책값·입력 역할, 런타임 절대경로는 없음 |

---

## 1. 목표: 이미 확보한 제어 결과에 배경 보존을 결합한다

C-012는 같은 양끝에서 학습한 A/B 궤적을 선택적으로 생성했다. C-013은 같은 공·장면·고정 seed에서 미학습 보간 경로와 S자도 따랐다. 다만 공의 윤곽 잔상·무늬 변화가 남았고, seed2에서는 BASE부터 배경이 크게 무너졌다. 이 결과와 `temporal=UNVERIFIED`를 보존한다.

이번에는 새 생성법이나 loss를 만들지 않는다. **기존 출력의 생성된 객체 부분은 유지하고, 이미 관측한 정적 배경만 복원하는 가장 단순한 시스템 기준선**을 만든다.

질문은 세 가지다.

1. 시작·종료 앵커에서 보이는 부분만으로, 정답 renderer의 깨끗한 배경 없이 사용할 배경을 얻을 수 있는가?
2. 이미 생성한 공의 위치·형태를 인위적으로 교정하지 않고, 멀리 떨어진 배경 손상을 줄일 수 있는가?
3. 동일한 보수적 편집 영역을 적용했을 때 경계·대상 주변 오염·무늬 손상이 어떻게 남는가?

**배경 복사 영역의 오차가 0이 되는 것은 합성식의 성질이지 새로운 생성 능력이 아니다.** 주 판단은 위치 제어 보존, 잘림·경계 회귀 여부, 남은 대상 내부 손상, 추가 노동·계산 비용을 함께 본다.

B-032는 원거리 배경 복원과 편집 영역 안의 오염을 구분했다. 그 교훈과 CPU 연산만 재사용한다. B-033의 생성 중 제약, VAE latent 혼합, SCAIL/VACE의 새 sampler는 이번에 실행하지 않는다.

---

## 2. 승인 범위와 제외 범위

### 수행

- 기존 코드·앵커·무손실 생성 프레임·경로·평가 자료 읽기.
- 양끝 앵커에서 배경 plate를 한 번 복원하고 출처 지도 보존.
- 고정된 경로 기반 편집 영역으로 CPU 합성 3건.
- 저장 PNG의 픽셀 불변성·기존 Reader의 위치·외형·경계·배경 비교.
- 새 파생 MP4 3개, 비교 뷰어·결과·해설·commit/push·전달.

### 0회

- 학습·backward·optimizer·checkpoint 변경.
- sampler·DiT forward·VAE encode/decode·T5 등 모델 적재/추론.
- imagegen·SAM·CoTracker·DragAnything·14B.
- 모델·패키지·데이터 다운로드나 새 환경 설치.
- renderer의 sprite/정답 중간 RGB/clean background를 합성 입력으로 사용.
- 생성 객체의 위치 warp·sprite 재삽입·형태 교정·자동 inpainting.
- 출력 양끝을 앵커로 통째로 덮어쓰기·색보정·업스케일·프레임 보간.
- 결과를 보고 mask 반경·feather·경로·사례를 고르는 탐색.

**합성 영상은 허용된 후처리 결과다. 원래 모델이 더 좋은 영상을 생성했다고 보고하지 않는다.** 새로운 객체를 생성하는 것이 아니므로 공 내부의 무늬/윤곽 문제가 남는 것은 예상 가능한 한계다.

---

## 3. 새 Codex 세션 인수와 실행 정책

### 3.1 파일·환경 인수

현재 hostname·사용자·cwd, 저장소 root/remote/branch/HEAD/worktree/미커밋 변경, 적용되는 `AGENTS.md` 등을 확인한다. 과거 세션의 shell 변수·SSH·venv·MCP가 유지됐다고 가정하지 않는다.

이미 Spark에 있으면 SSH를 중첩하지 않는다. 다른 호스트이면 기존 `dgx-spark` 또는 실제 별칭과 기존 인증을 쓴다. 새 키·token을 만들거나 공개하지 않는다. 이전 Claude/Codex 세션 복원은 필요 없다.

C-013 `REPRODUCE.md`, `RUNS.json`, `DELIVERY.json`, `ORIGINAL_MEDIA_SHA256.json`과 C-012의 `TASK_MANIFEST.json`, 실행 설정에서 다음을 찾는다.

- 실제 연구 Python과 기존 NumPy/Pillow/OpenCV/ffmpeg.
- 실제 입력 앵커 `start.png`, `end.png`. **생성 영상의 첫/끝 프레임이 아니다.**
- 아래 세 사례의 무손실 PNG 33장과 원 MP4.
- 부모의 `PATHS.json`, A 중심 좌표·물체 지름·좌표 계약.
- C-012 Reader와 C-013 경로 scorer, RAW 측정 결과.
- B-032 `compositor.py`, `run_composite.py`, 불변성 검사.
- 기존 CPU 실행/보호 경로와 Mac 전달 방식.

C-013 검토 ZIP에도 세 사례의 무손실 프레임이 포함된다. `/tmp`가 없어졌다면 전달 문서의 원본 위치를 찾는다. ZIP이나 파일이 없다고 새 GPU 생성이나 VAE decode를 실행하지 않는다.

동일 C-014가 완료됐으면 중복 실행하지 않는다. 기존 수정은 보존하고 강제 reset하지 않는다. 별도 worktree라도 모델·venv·대형 cache를 복제하지 않는다. 특정 GitHub 플러그인 없이 기존 git/SSH로 가능하면 그 경로를 쓴다.

### 3.2 CPU-only와 기존 가드

이 작업은 CPU 파일 처리다. 기존 연구 Python의 정상 CPU 경로를 사용한다. CUDA를 초기화하거나 모델 worker를 띄우지 않는다. OpenCV·BLAS·ffmpeg는 가능하면 최대 2 thread로 제한하고, 프레임을 순차 처리한다. 목표 최대 RSS 2GiB를 넘으면 원인을 확인하고 중단한다. 이 숫자는 새 시스템 안전 보증값이 아니라 이번 작은 작업의 자원 예산이다.

**시작 정책의 명시적 적용 범위:** CPU 진입에 기존 guarded runner가 필요하면, C-013에서 승인·검증한 시작 정책(기존 전역 swap 점유량은 단독 차단 대신 경고, 새로운 증가·swap-out·PSI·headroom·worker·외부 작업 보호는 유지)을 C-014 CPU 단계에도 동일하게 승계하는 것을 승인한다. 실제 C-013 사본과 diff를 재사용하며 stage·deadline 바인딩만 현재 작업에 맞춘다. 새 임계값이나 가드 예외는 추가하지 않는다.

과거 절대 swap 총량 차단으로 되돌리거나, 경고를 없애려고 `swapoff`·재부팅·타 프로세스 종료를 하지 않는다. 압박·외부 충돌·관측 실패가 실제로 있으면 우회하지 않는다. 공통 정책·서비스를 수정하지 않는다. CPU 작업을 위해 새 launcher나 메모리 관리 프로젝트를 만들지 않는다.

모델 작업과 환경 import 시험을 병렬로 하지 않는다. GPU 작업은 이 의뢰에서 0회다. `torch`는 PNG 입력으로 불필요하면 import하지 않는다. 기존 raw 파일만 남은 경우에도 CPU 안전 로드와 부모의 확정 export 규칙만 사용한다.

---

## 4. 실행 전 고정과 세 사례

접근·환경 확인 이후, **새 수치 분석·plate 제작·합성 전에** 의뢰서·PLAN·동봉 정책·입력 역할·평가 기준을 commit한다. 원격 접근이 안 되면 local commit 시각과 push 지연을 기록한다. 사후 PLAN을 사전 계획이라고 쓰지 않는다.

| Case ID | 부모 출력 | seed | 선택 이유 |
|---|---|---:|---|
| `I50_S1` | C-013 직선 경로 | 20261028 | 상대적으로 깨끗한 결과에 새 회귀를 만들지 않는지 |
| `S_S1` | C-013 S 경로 | 20261028 | 대상의 잔상·무늬 변화가 합성 뒤에도 남는지 |
| `ON2048_S2_A` | C-012 seed2 A, C-013 뷰어에도 포함 | 20261029 | 넓은 배경 붕괴를 줄일 수 있는지 |

각 사례는 RAW(부모 재사용)와 `ENDPOINT_BG_COMPOSITE`(이번 CPU 파생) 한 쌍이다. 새 합성 결과는 총 3개다. 새 mask 방법·hard/soft 비교·추가 seed·BASE 합성을 늘리지 않는다.

기본 입력은 부모 평가와 같은 **416×240 RGB uint8 무손실 PNG 33장**이다. MP4를 decode한 프레임을 무손실 원본이라고 취급하지 않는다. PNG를 얻을 수 없고 검증된 raw만 있다면 부모 export의 범위·rounding을 그대로 사용하고 차이를 기록한다. 신규 VAE decode는 금지한다.

세 case의 frame index 0..32를 그대로 사용한다. 33프레임·16fps MP4의 파일 길이는33/16초, 양끝 표본 간격은32/16초다. 실제 원본 FPS가 확인되지 않았으면 별도 검증한 것처럼 쓰지 않는다.

CPU가 읽을 private 입력 manifest에는 역할·절대경로·파일 hash를 둔다. 공개 문서에는 private 경로를 남기지 않는다. 부모 기록의 hash는 인수 기대값이며 실제 파일 확인을 대신하지 않는다.

---

## 5. 양끝에서 배경 plate 만들기 — 숨겨진 정답을 쓰지 않는다

### 5.1 허용 정보와 알려진 한계

합성용 배경을 만들 때 읽을 수 있는 정보:

- 실제 시작 앵커 `A0`와 실제 종료 앵커 `AT`.
- 사용자가 제어 입력으로 이미 제공한 양끝 중심 `(104,120)`, `(312,120)`.
- 과제에서 이미 알려진 공 지름 `d=56px`.

이것은 크기·궤적이 주어진 단일 강체·정적 배경의 작은 과제다. 자동 분할·실사 배경 추정 성능을 검증하는 실험이 아니다. **`KNOWN_SIZE_AND_PATH / ENDPOINT_OBSERVED_BACKGROUND`**로 명시한다.

금지 입력:
- renderer의 `background.png` 또는 `background()`.
- sprite alpha나 정답 중간 mask로 plate를 복원하는 것.
- generated RAW를 보고 깨끗한 배경 조각을 사후 선택하는 것.
- 새 이미지 생성·inpaint·optical flow·정합·노출 보정.

### 5.2 관측 가능한 배경의 정의

좌표는 부모와 같은 pixel-index 중심이며, 실제 픽셀 `(x,y)`는 정수 index다.

공 반지름 `r=d/2=28`.
양끝 객체 제외 반지름 `r_exclude = r+24 = 52px`로 고정한다.

`U0(p) = [||p-c0|| > 52]`

`UT(p) = [||p-cT|| > 52]`

여기서 U는 해당 앵커에서 객체와 충분히 떨어져 배경으로 관측할 수 있는 영역이다. 정확한 renderer alpha 대신 넉넉한 원형 제외 영역을 쓴다.

필수 검사:

1. 두 앵커의 크기·dtype·좌표가 맞는다.
2. `U0 & UT`에서 두 앵커의 RGB가 exact로 일치한다. 이 toy 장면의 정적·같은 노출 계약을 확인하는 것이다.
3. `U0 | UT`가 전체 화면을 덮는다. 두 앵커에서 동시에 가려진 unknown 픽셀 수는 0이어야 한다.
4. 실제 앵커에 원형 제외 영역 밖으로 뚜렷하게 뻗은 객체·그림자·가림이 없는지 확인한다.

입력 형식·잘못된 파일 때문에 다르면 그 연결 오류를 고친다. 실제로 배경이 달라지거나 unknown이 남으면 **`PLATE_NOT_ESTABLISHED`**로 기록한다. renderer의 숨겨진 배경을 몰래 대입하거나 허용 반경을 결과에 맞춰 조정하지 않는다.

### 5.3 결정적인 복원 규칙

plate `B_hat`은:

- `U0=True`이면 `A0`의 같은 좌표 픽셀을 복사.
- `U0=False`이고 `UT=True`이면 `AT`의 같은 좌표 픽셀을 복사.
- 둘 다 False이면 unknown으로 남기고 위 완료 조건 실패.

같은 좌표 복사만 한다. warp·색 보정·평균화·경계 생성은 하지 않는다. 공통 영역이 exact라면 두 앵커를 붙이는 위치에서 색 차이가 발생할 이유가 없다.

저장:
- `background_from_endpoints.png`.
- 픽셀별 출처 지도 `anchor0/anchor32/unknown`.
- U0/UT, coverage, 공통 영역 차이, source-byte 검증.
- 사용 앵커·경로·크기·고정 반경의 hash/계보.

`B_hat`의 각 픽셀은 유효한 앵커의 같은 위치 픽셀과 exact여야 한다. plate는 세 사례에 동일하게 사용한다.

### 5.4 optional evaluator-only audit

plate와 provenance를 freeze·hash한 **뒤에만**, 별도 평가 코드가 부모 `background.png`를 읽어 `B_hat`이 숨겨진 정답 배경과 일치하는지 확인할 수 있다. 합성 runner에는 이 경로를 전달하지 않는다.

이 audit은 입력 누출 없이 복원이 맞았는지 확인하는 상한 검증이다. 일치하지 않으면 그 오차를 기록하고, 정답 배경의 픽셀을 복사해 고치지 않는다. audit 파일이 없다고 사용자에게 새 자료를 요구하며 멈추지는 않는다. 앵커 관측 계약과 oracle 확인 여부를 구분한다.

---

## 6. 편집 영역은 한 가지 규칙으로 고정한다

목적은 공을 정답 모양으로 자르는 것이 아니라, **공과 주변 여유 영역을 원래 생성 결과로 남기고 먼 배경만 교체**하는 것이다.

각 t의 요청 중심을 `q_t`라 한다. 부모의 승인된 경로 JSON/좌표를 그대로 쓴다. 생성 결과의 검출 중심으로 mask를 이동시키거나 반경을 바꾸지 않는다.

- 공 명목 반지름: 28px.
- 생성 픽셀 보존 core 반지름: `r_core = 28+16 = 44px`.
- 혼합 구간 폭: `feather = 8px`.
- 생성 결과 사용 outer 반지름: `r_outer = 52px`.

`d_t(p)=||p-q_t||`에 대해:

```
alpha_t(p) = 1                                  if d_t <= 44
             0.5 * [1 + cos(pi*(d_t-44)/8)]      if 44 < d_t < 52
             0                                  if d_t >= 52
```

alpha는 원형 객체의 정확한 분할이 아니다. 알려진 지름보다 넓은 경로 중심 envelope이며 **실제 생성 객체 전체를 포함한다는 보장은 없다.** 그 여부는 QA에서 검사한다.

I50, S, seed2 A에 같은 반경·같은 feather를 적용한다. mask를 출력별로 줄이거나 넓히지 않는다. 양끝에도 같은 식을 적용하고 앵커를 통째로 덮어쓰지 않는다.

저장할 것:
- 사용한 요청 중심 33개와 부모 계보.
- float alpha 또는 정확한 재생성 규칙·hash.
- core/transition/outside mask와 미리보기.

미리보기 uint8 alpha를 다시 읽어 본 계산에 사용하지 않는다. 표시용 양자화와 실제 합성을 구분한다.

명목 객체는 core 안에 있지만, RAW의 늘어난 부위·이중 윤곽이 core/outer 밖에 있을 수 있다. 그 현상을 숨기거나 제거해 “외형이 개선됐다”고 주장하지 않는다. **경로 보호 영역 밖의 artifact 억제는 허용된 시스템 처리지만, 객체 잘림 여부와 생성 자체의 실패는 그대로 보고**한다.

---

## 7. 합성 연산과 byte 보존

부모 생성 PNG를 `Y_t`, 양끝 복원 plate를 `B_hat`이라 할 때:

`C_t = alpha_t * Y_t + (1-alpha_t) * B_hat`

이번 단순 기준선은 동일 RGB uint8 코드값 공간에서 혼합한다. 물리적 광도 합성이나 새 색보정 기법이라고 부르지 않는다. 별도 gamma 변환·노출 일치·Poisson blend는 추가하지 않는다.

구현:
- NumPy float64 또는 일관되게 고정한 float 연산으로 혼합.
- `np.rint`, clip[0,255], uint8 변환.
- **alpha=1 위치는 최종 uint8에서 Y_t 원 bytes를 명시적으로 복사.**
- **alpha=0 위치는 B_hat 원 bytes를 명시적으로 복사.**

모든 99프레임에 대해:

```
C_t[alpha==1] == Y_t[alpha==1]        # exact
C_t[alpha==0] == B_hat[alpha==0]      # exact
```

를 PNG 저장/readback 뒤에도 확인한다. 이 exact 성질은 손실 MP4에 주장하지 않는다.

B-032의 blend와 endpoint byte-copy 검사, 입력 hash 불변성, ffmpeg 포장을 참고한다. 다만 B-032의17프레임·896×512·24fps·차량 mask·normalized raw 규칙을 그대로 하드코딩해서 가져오지 않는다. 이번 기준 입력은 부모와 같은 PNG RGB uint8, 416×240·33frames·16fps다.

새 합성 PNG와 MP4는 별도 output 경로에 저장한다. 부모 RAW·MP4·checkpoint·앵커·경로를 수정하지 않는다. MP4는 CPU software encoder를 사용하고 hardware encoder를 시작하지 않는다. `ffmpeg`의 실제 fps·프레임수·해상도를 검사한다.

---

## 8. 원인을 분리하는 평가 — 배경 MAE 하나로 성공하지 않는다

### 8.1 공통 비교 화면

각 사례에서 다음을 같은 프레임 index로 제공한다.

`RAW / ENDPOINT_BG_COMPOSITE / alpha overlay / boundary crop`

처음부터 합성만 보여 주거나 RAW의 손상을 숨기지 않는다. plate와 두 앵커의 출처 지도도 보조 패널로 둔다.

정적 주 시점: `0/4/8/12/16/20/24/28/32`.
전33프레임 detector·수치 검사는 수행한다. 시각적으로 실제 본 범위를 따로 기록한다.

### 8.2 위치·객체 보존

부모 C-012 Reader와 C-013의 경로에 맞는 scorer를 재사용한다. threshold를 바꾸지 않는다. 요청 중심 부근만 검색하지 않고 전체 화면에서 검출한다.

- RAW와POST의 detection/missing/duplicate/peak/center를 각각 기록.
- 부모와 동일한 요청 경로 오차·사전 위치 기준을 재계산.
- 양쪽 모두 valid인 프레임의 center shift를 보고.
- 주 시점 center 변화 `>2px` 또는 POST만 핵심 missing/duplicate가 생기면 위치·판독 회귀로 조사.
- 2px는 이번 pilot의 회귀 경고선이다. 통계적 표준이나 실제 객체 정체성 보장은 아니다.
- 부모 RAW도 현재 같은 Reader로 읽어 실행 비교를 맞춘다. 기존 수치와 차이가 크면 입력·export·scorer 연결 문제부터 확인.

객체 core의 pixels가 exact여도 전체 프레임 template의 판단은 주변 배경 변화로 달라질 수 있다. 검출 변화와 실제 객체 이동을 구분하고, 임계값을 낮춰 PASS로 만들지 않는다.

공의 무늬·띠·반점·윤곽은 core 안에서 바꿀 수 없다. 그 영역이 “더 예뻐졌다”는 주장 대신 pixel 보존과 기존 실패의 잔존을 기록한다.

### 8.3 잘림과 실패 은폐 검사

RAW 위에 r=28/44/52의 원을 표시한 QA 이미지를 만든다. 이것은 판독용 overlay이고 최종 영상에 넣지 않는다.

주 시점 및 전체 시트에서:
- 생성 공·반투명 겹친 윤곽·늘어난 부위가 alpha<1 영역까지 나오는가?
- feather/복사로 부위가 끊기거나 사라지는가?
- 원래 중복 객체가 plate 복사로 사라졌다면 어떤 영역에서 사라졌는가?
- 배경이 깨끗해져 객체가 좋아 보이는 것과, 실제 객체 픽셀 변화는 다른가?

실제 객체 support가 자동으로 완벽히 알려졌다고 가정하지 않는다. target 정답 원이나 알려진 지름으로 RAW의 전체 생성 support를 대신하지 않는다.

- 잘림이 관측되면 `CLIPPING_OBSERVED`.
- 판독 불가능하거나 경계까지 부위가 닿아 불확실하면 `CLIPPING_UNCERTAIN`.
- 관측 범위에서 뚜렷한 잘림이 없으면 `NO_OBVIOUS_CLIPPING_IN_REVIEWED_FRAMES`.

잘림을 고치려고 반경을 사후 변경하지 않는다. 실패한 고정 규칙으로 보존하고 한계를 평가한다. 여러 mask를 만들어 가장 좋은 것만 고르지 않는다.

### 8.4 배경·접합부 구역별 통계

한 개의 배경 점수로 합치지 말고 다음을 나눈다.

A. `COPIED_OUTSIDE`: alpha=0. plate와 exact는 합성식의 보장이다. 품질 기여의 독립 증거가 아니다.
B. `FEATHER_RING`: 44<거리<52. 실제 혼합으로 색·밝기·질감 단절이 생기는지 본다.
C. `PRESERVED_COLLAR`: 32<거리<=44. 명목 공에서4px 이상 떨어진 주변부지만 RAW를 그대로 보존한다. 배경 오염이 여기 남는지 본다.
D. `OBJECT_CORE`: 거리<=28. 참고상 공 내부 영역이나 정확한 생성 객체 분할은 아니다. RAW/POST byte 불변성을 확인한다.

각 구역에서 RAW/POST의 B_hat 대비 RGB MAE·p95·차이25 초과 비율을 보고한다. `OBJECT_CORE`의 B_hat 오차는 배경 오차로 해석하지 않는다. 구역별 픽셀 수를 명시하고 빈 구역은 null로 둔다.

부모 C-013 공통 배경 ROI(기존 A/B 및 네 새 경로의 swept region+8px 바깥)를 재사용할 수 있으면 같은 정의로 RAW/POST 지표도 제공한다. 기존 숫자와 직접 비교할 때는 reference·ROI·프레임 범위·color export가 같아야 한다. 달랐다면 별도 표로 구분한다.

공통 far ROI는 세 case의 모든 outer disk 합집합 바깥으로 추가 정의할 수 있다. 여기는 의도적으로 background를 복사한 영역이므로 exact 확인용이다.

seam 평가:
- 경계 양쪽의 색/질감/명도 연결을 같은 확대 비율로 확인.
- 자른 배경 패치가 공을 따라 이동하는 것처럼 보이는지 확인.
- seed2 A의 넓은 손상이 사라져도 core/feather 안의 모자이크가 움직이는지 확인.
- 공 밑의 새로운 그림자·접촉을 생성했다고 주장하지 않음. 원래 toy에는 가림·가변 그림자·접촉 모델이 없다.

RAW 일부가 plate보다 나쁜 영역을 합성에서 지웠다고 원래 모델 실패를 지우지 않는다. 무엇을 그대로 두고 무엇을 복사했는지 항상 함께 표시한다.

### 8.5 시간 품질

가능한 도구로 실제 연속 영상을 지각 검토하면 reviewer 종류·속도·관측 범위를 적는다. 같은 Codex agent 검토는 독립 human 평가가 아니다. 정적 시트·ffmpeg decode·브라우저 재생 테스트만 했으면 `temporal=UNVERIFIED`를 유지한다.

정적인 plate를 썼다고 시간 경계가 자동으로 안정된 것은 아니다. mask가 움직일 때 생기는 경계 popping·잔해 출현/소실은 별도 문제다.

관측 프레임 간 차이나 moving-ring 통계는 보조 수치로 사용할 수 있지만 지각 품질 PASS를 대신하지 않는다. 검토 기능이 없다는 이유로 남은 CPU 결과 전달을 중단하지 않는다.

---

## 9. 작은 CPU fixture와 계산 검증

새 패키지를 설치하지 않고 기존 unittest/stdlib로 필요한 계약만 검사한다.

1. alpha=1/0의 저장 PNG exact. 혼합 구간은 고정 수식·rounding과 일치.
2. 입력 앵커로만 plate가 구성되고 각 픽셀의 출처가 valid인지.
3. 두 관측 영역의 교집합에 의도적 차이를 넣으면 plate 계약 실패.
4. 두 앵커가 동시에 가린 fixture면 unknown을 배경으로 채우지 않고 실패.
5. 입력 PNG/RGB·좌표축·frame index·해상도 오류 거부.
6. 과하게 늘어진 객체 fixture가 core/outer 경계에서 잘릴 수 있음을 QA로 표시. mask 합성의 exact 검사만으로 객체 보존 PASS를 만들지 않음.
7. 생성 부모 파일 hash가 전후 유지되고 output overwrite를 거부.
8. ZIP manifest는 자기 자신과 ZIP을 hash 대상에서 제외.

CPU fixture는 입출력 계약을 검증한다. 이를 학습된 제어나 영상 품질 성과로 세지 않는다. 테스트 수를 늘리기보다 실제 세 case에 같은 정책을 끝까지 적용한다.

---

## 10. 예산·오류 처리·중단

| 작업 | 정상 승인량 |
|---|---:|
| 앵커 기반 plate | 1개, 세 case 공용 |
| 사전 고정 alpha 정책 | 1종, 조정 탐색 0회 |
| CPU 합성 | 3 case × 33 PNG = 99프레임 |
| 새 파생 MP4 | 3개, 416×240·33frames·16fps |
| 부모 RAW MP4/프레임 | 읽기·재사용 |
| 모델 적재·sampler·VAE·학습·GPU | 0회 |
| 다운로드·환경 설치 | 0회 |

추가 나란한 comparison MP4는 만들지 않아도 된다. 뷰어에서 기존 RAW와 새POST를 동기화해 비교한다. 시트·thumbnail·lossless alpha 자료는 파생 검토물이다.

입력 형식/경로/ffmpeg 포장 등의 기계적 오류는 같은 파일·같은 정책으로 수정할 수 있다. 이미 계산된 PNG를 재사용하고 mask 값을 바꾸지 않는다. 품질 재시도는 0회다.

외형 clipping·seam이 생겨도 실패를 기록하고 예정한 다른 case를 동일 정책으로 마친다. 잘못된 plate·파일·CPU 계약은 결과 해석 전 해결하거나 해당 단계를 BLOCKED로 남긴다.

전체 작업 범위 상한 90분, 마지막15분은 기록·전달에 남긴다. 이는 승인된 범위이지 예상 소요시간이나 완료 보장이 아니다. 환경 인수·추가 문서보다 실제 세 합성과 판정을 우선한다.

---

## 11. 판정: 기술·시스템 이득·한계를 나눠 보고

### 기술 판정

- `ENDPOINT_PLATE_ESTABLISHED` / `PLATE_NOT_ESTABLISHED`.
- `COMPOSITE_PIXEL_CONTRACT_PASS` / FAIL.
- `RAW_IMMUTABLE`.
- `POSITION_RETAINED` / `POSITION_OR_DETECTION_REGRESSION` / UNCERTAIN.
- clipping·seam·시간 품질은 별도.

### 사례별 품질 판정

`POST_COMPOSITE_SCENE_GAIN`:
큰 배경 손상이 줄고, 사전 위치 기준이 유지되며, 검토한 범위에서 새 clipping·큰 경계 손상이 없음. 전체 영상 생성 모델 향상이 아니라 **관측 배경을 재사용한 시스템 효과**다.

`BACKGROUND_GAIN_WITH_BOUNDARY_TRADEOFF`:
먼 배경은 좋아졌으나 moving patch·feather seam·잘림·잔해 소실에 따른 불안정이 발생.

`NO_ESTABLISHED_JOINT_GAIN`:
배경 복사 자체를 제외하면 객체·경계까지 포함한 유용한 결합 개선을 확인하지 못함.

`INPUT_OR_REVIEW_LIMITED`:
plate·파일·평가·시각 관측의 한계로 판단을 제한해야 함.

### 다음 한 가지

- 세 case에서 보존 가능한 배경이 개선되고 경로가 유지된다면: CPU 후합성을 이 toy의 기준선으로 유지. 실제 장면/가림/카메라 일반화는 후속 과제다.
- 외부 배경만 좋아지고 edit core 안의 오염이 주요 병목이면: B-033의 교훈을 참고해 **동일 후합성 뒤에도 이득이 남는 생성 중 문맥 제약**을 다음 후보로 검토. 이번에 구현하지 않는다.
- core의 무늬·윤곽 문제가 주된 미해결이면: identity/형태 안정성을 별도 과제로 선택한다. 배경 합성으로 해결됐다고 하지 않는다.
- clipping이 생기면: 고정 support 가정의 한계. 그 결과만으로 새 segmentation 설치나 mask tuning을 자동 시작하지 않는다.

정적 배경과 알려진 크기·경로의 정보가 많은 toy 문제임을 명시한다. 회전·가림·카메라 이동·동적 배경·새 target 체형·그림자 일반화는 검증하지 않는다. 이 제한된 합성이 성공해도 원래의 범용 영상 편집 연구가 완성된 것은 아니다.

---

## 12. 산출물·한국어 해설·전달

기존 형식으로 문서를 작게 묶는다.

- `PLAN.md`: 인수·고정 사례·정책·평가·예산.
- `INPUTS_AND_PLATE.json`: 입력 hash, source selection, known/unknown, frame lineage.
- `COMPOSITE_CONFIG.json`: 이번 정책 실제 값, 시행 코드 commit.
- `METRICS.json`: frame별 불변성·위치·경계/배경 구역·clipping 관측.
- `RESULTS.md`: 실제 개선과 남은 실패, 다음 후보 하나.
- `METHOD_AND_LESSON_KO.md`: 아래 수식·코드·결과의 연결.
- `REPRODUCE.md`, `DELIVERY.json`: 실제 재현·전송 근거.

한국어 해설:
1. 이전에는 생성 전체를 평가했고, 이번에는 관측 배경을 사용해 출력을 합성한다는 차이.
2. `C=alpha*Y+(1-alpha)*B`에서 바뀌는 영역과 안 바뀌는 영역.
3. plate의 관측 coverage·provenance와 unknown의 의미.
4. 정답 object alpha와 보수적인 edit envelope가 다른 이유.
5. core pixel exact와 생성 객체 전체 보존이 동치가 아닌 이유.
6. copied 영역 MAE0이 독립적인 성능 증명이 아닌 이유.
7. lossless PNG의 exact와 MP4 손실 압축의 차이.
8. 경로·외형·장면·경계·시간을 나눠 보고하는 이유.
9. 실사용에서는 배경 미관측·가림·그림자·카메라 움직임이 추가로 필요한 이유.
10. B-032/B-033에서 재사용한 것과 이번에 아직 하지 않은 것.

뷰어는 세 탭(I50 / S / seed2 A)과 같은 index의 RAW/POST, alpha toggle, 경계 crop, 입력 앵커/plate 출처, 주요 수치로 충분하다. 실제 합성 영상을 먼저 보여 준다. 화면 장식이나 과도한 그래프에 시간을 쓰지 않는다.

원 생성 MP4는 그대로 복사하고 새POST만 인코딩한다. 생성/합성/시트/oracle-audit를 분명히 표기한다. 대형 checkpoint·raw·latent·과거 ZIP은 다시 포장하지 않는다.

새 ZIP 이름은 실제 작업 날짜를 사용한다. manifest는 자신과 ZIP을 제외하고, payload 수와 ZIP 총 파일 수를 따로 기록한다. Spark/Mac의 실제 가능한 전달 위치에 보존하고 크기·SHA256·CRC·실제 추출·payload hash·전송 동일성을 확인한다. 접근하지 못한 호스트를 PASS라고 쓰지 않는다.

공개 Git에는 비민감 코드·문서·필요 hash만 올린다. 개인 경로·token·PID·미디어·weights·latent를 자동 공개하지 않는다. 이번 변경만 stage·commit하고 확인된 연구 branch에 push한다. 기존 C-012/C-013 판정과 BLOCKED 이력을 소급 변경하지 않는다. HISTORY/ROADMAP에 이번 후합성 기준선의 역할을 연결한다.

최종 보고의 첫 질문:
1. 숨겨진 clean background 없이 앵커 두 장으로 plate를 얻었는가?
2. 세 RAW에서 무엇을 그대로 보존하고 무엇을 복사했는가?
3. 경로 제어와 단일 객체 판독이 유지됐는가?
4. seed2의 넓은 배경 손상은 줄었으며, 어디에 잔여 오염이 남는가?
5. 공 잘림·feather seam·moving patch·무늬 변화 중 무엇이 남거나 새로 생겼는가?
6. 이 고정 합성을 저비용 기준선으로 유지할 근거가 있는가?
7. 다음에는 생성 중 제약, 객체 외형, support 추정 중 무엇 하나를 검토해야 하는가?

영상·판정·비용을 먼저, 검사/해시/전송 상세는 뒤에 둔다. 자체 CPU 작업 종료·다른 작업 보존을 확인하고 끝낸다. 후속 학습·생성·mask 탐색을 예약하거나 자동 시작하지 않는다.

---

## 근거 자료

[S1] 부모 C-013 결과·경로·무손실 출력·재현:
https://github.com/hyunlord/make-meme/tree/11b4313c8d9c1b1c17ccdff70b9b75216cce3868/docs/research/experiments/C-013-frozen-unseen-path-generalization

[S2] 공·배경·앵커의 실제 C-012 renderer(이번 합성은 background/sprite 함수를 호출하지 않음):
https://github.com/hyunlord/make-meme/blob/11b4313c8d9c1b1c17ccdff70b9b75216cce3868/docs/research/experiments/C-012-minimal-trajectory-capability/code/render_task.py

[S3] B-032 CPU 합성·byte 불변성·실제 한계:
https://github.com/hyunlord/make-meme/tree/11b4313c8d9c1b1c17ccdff70b9b75216cce3868/docs/research/experiments/B-032-source-preserving-composite-baseline

[S4] B-033 생성 중 제약의 비교 교훈(이번 실행 대상 아님):
https://github.com/hyunlord/make-meme/tree/11b4313c8d9c1b1c17ccdff70b9b75216cce3868/docs/research/experiments/B-033-clean-prediction-constraint

고정 링크는 근거이며 실제 runtime 파일 검증을 대신하지 않는다. 최신 branch로 강제 reset하거나 외부 문서 버전으로 환경을 업그레이드하지 않는다.

## 실행 시작

위 승인 범위에서 지금 C-014를 실제로 시작해 줘. 환경·입력 인수와 사전 commit 이후, 앵커 배경 복원→고정 CPU 합성 세 개→위치/경계/장면 평가→기록·전달까지 수행한다. 계획만 작성하거나 같은 승인을 다시 기다리지 않는다. 실제 권한·안전·필수 자료 문제가 있는 부분만 구체적으로 보고한다.
