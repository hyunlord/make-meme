# C-003 재개 — 시작 전 swap-out 절대 0 규칙만 한정 변경

대상 저장소: `hyunlord/make-meme`  
기준 커밋: `4e546e1971c2545d07883890287838b3a064e669`  
대상 실험: `C-003-internal-structure-conditioning`  
상태: 재개 지시 제안. 이 문서를 전달해 승인하기 전에는 실행 권한을 새로 만든 것으로 취급하지 않는다.

## 1. 범위와 변경 승인

C-003의 연구 질문·앵커·모델·입력·대조군은 변경하지 않는다. 새 실험 번호나 새 실행기를 만들지 않는다.

이번 재개에 한해 **시작 단계에서 전역 swap-out이 조금이라도 있으면 차단하던 추가 규칙**을 해제하고, 이미 존재하는 swap 증가량·10초 swap-out·PSI·작업별 메모리 보호 기준으로 판정한다. 이는 명시적인 운영 정책 변경이지, 과거 중단을 오탐 또는 PASS로 소급하는 작업이 아니다.

과거 `START_SWAPOUT_OBSERVED`, CPU import 실패·수정, UNKNOWN, heavy 0 기록을 그대로 보존한다. 현재 외부 작업이나 자원 상태는 과거 로그로 대신하지 않고 다시 확인한다.

새 manager·watchdog·launcher·전체 가드 개편·서비스 재조사·모델 변경은 금지한다. 기존 C-001/C-002에서 실행된 경로를 사용한다. B-034를 다시 시작하지 않는다.

## 2. 확인된 원인과 최소 변경

기존 C guard `memory.py`의 `MemoryBudget.inspect()`는 다음을 이미 검사한다.

- 시작 가용 메모리 72GiB, 실행 중 24GiB
- 시작 전역 swap 점유량 64MiB 초과
- 시작값 대비 swap 점유 증가량 64MiB 이상
- 관측 창 약 10초의 swap-out 64MiB 이상
- 같은 창에서 memory PSI full 비율 10% 이상
- 작업 cgroup의 `swap_current > 0` 또는 `swap_max != 0`
- 작업 OOM/oom_kill, 외부 GPU·서비스 충돌, 관측 오류

그 뒤 아래 시작 전용 규칙이 추가되어 있다.

```python
elif start and swapout > 0:
    verdict['decision'] = 'START_SWAPOUT_OBSERVED'
```

**이번에는 이 추가 차단만 제거한다.** 상위의 증가량·속도·PSI 판정과 시작 10초 관측, `GLOBAL_SWAP_WARNING` 기록을 그대로 유지한다. 경고가 있다고 판정 결과를 강제로 CLEAR로 덮어쓰는 방식은 금지한다.

현재 실제 import되는 파일의 경로와 해시를 확인해 해당 공통 판정 함수의 새 버전 하나를 사용한다. preflight만 수정하고 supervisor가 다른 복사본을 쓰는 상태를 만들지 않는다. 과거 실험의 동결 사본·manifest·receipt는 수정하지 말고, 이번 실행의 코드 버전·freeze를 새로 연결한다.

위 수치는 기존 연구용 운영 예산이지 Linux/NVIDIA의 공식 안전 보증 수치가 아니다. 이번에 이 임계값들을 높이지 않는다. 메모리 한도·외부 작업 보호·서비스 정책·종료 신원 처리도 바꾸지 않는다.

금지: swapoff/swapon, swappiness 변경, drop_caches, 재부팅, 다른 프로세스 종료, 알 수 없는 PID 자동 허용, 서비스 강제 시작/중지.

## 3. 최소 검증만 하고 실제 실험으로 이어갈 것

전체 가드 검사를 새 연구처럼 반복하지 않는다. 바뀐 분기와 중요한 차단이 유지되는지 CPU에서 확인한다.

1. 시작 창 10초 이상·4KiB swap-out·작은 점유 증가·충분한 headroom·낮은 PSI → `GLOBAL_SWAP_WARNING`을 남기고 메모리 판정은 CLEAR.
2. 같은 입력이라도 10초 관측이 미완료이면 기존 START_OBSERVATION_INCOMPLETE 유지.
3. swap 증가량/10초 swap-out/PSI가 기존 중단 기준에 도달하면 차단 유지.
4. 실제 worker가 존재하는 조건에서 작업 swap 사용 또는 OOM이 있으면 차단 유지.
5. 관측 실패·카운터 이상·외부 GPU 작업은 별도 기존 차단 유지.

공개 NUMERICS만으로 과거 전체 관측열을 재현했다고 보고하지 않는다. 실제 private start-samples를 사용할 수 있으면 그 기록을 사용하고, 그렇지 않으면 CPU 입력은 명시적으로 synthetic fixture라 표기한다.

실제 경로에서 `memory.__file__`와 코드 해시, 공통 bootstrap·절대 config/worker 경로를 확인한다. 이미 수정한 sibling import를 재누락하지 않는다. CPU 경로가 모델을 import/load하지 않는지 기존 방식으로 확인한다.

작업 시작 직전부터 기존 10초 관측과 실행 중 감시를 수행한다. 새 실행의 시작 기준값을 기록하고, 한 단계의 실행·decode 중 기준을 새로 잡아 증가량을 지우지 않는다. 다른 작업이 나타나거나 위험 기준을 넘으면 자체 worker만 중단한다.

**사전검사 통과 후 CPU 보고서만 쓰고 종료하지 않는다.** 현재 안전 조건이 충족되면 같은 작업 안에서 아래 원래 연구를 수행한다. 단순 경로·import 오류는 같은 승인 범위 안에서 바로잡되 실제 안전 차단은 우회하거나 자동 반복하지 않는다.

## 4. 원래 C-003 비교 그대로 재개

기존 연구 PLAN/METHOD/전체 의뢰서 및 생성 전 관측표를 유지한다.

- 이미 받은 공식 `netG_A_latest.pth`를 해시 확인 후 재사용. 재다운로드하지 않는다.
- 기존 source 무손실 33장과 SAM mask/layout, 개의 시작·종료 앵커 재사용.
- 공식 FP32 scribble 추출을 완료된 pass 1회로 수행·캐시한다.
- 실제 polarity·선 유효성은 추출 후 입력을 보고 확인한다. 구조선을 관절 GT라고 부르지 않는다.
- 동적 외곽선은 고정. 내부 거리 >4px, 256×256 bbox 정규화, 동일 왕복 보간 등 준비된 조건 변환 규칙 유지.
- INTERNAL_DYNAMIC: 각 시점 내부 구조.
- INTERNAL_HOLD: 첫 프레임 내부 구조를 같은 시점의 객체 bbox로 이동·확대.
- C-002 개 LAYOUT_MOV를 OUTLINE_ONLY 기준선으로 재사용.
- 신뢰할 실제 구조 입력이 만들어지면 신규 영상 두 개를 모두 생성한다.

VACE1.3B, 기존 DiffSynth, BF16/SDPA/tiled VAE, Euler50, CFG5, sigma_shift5, seed20261028, 832×480/33frames/preview16fps, 기존 prompt·negative·VACE mask·scale를 유지한다.

33→9 마스크 압축·앵커 조건을 고치지 않는다. 추가 imagegen·SAM·point tracker·학습·후합성·업스케일·새 모델·새 설치는 0이다.

구조가 실제로 모두 비거나 두 조건이 오류로 같으면 입력 문제를 기록한다. 무의미한 생성이나 다른 표현으로의 조용한 전환은 하지 않는다.

## 5. 예산은 원래 미사용 범위만

이번 중단에서는 추출·영상 heavy가 모두 0회였다. 과거 중단 후 예약이나 권한이 자동 연장되지는 않았으며, 이 문서 전달로 **같은 미사용 연구 범위의 재개**를 승인한다.

- 구조 추출: 완료 pass 1회.
- 영상: DYNAMIC 1회 + HOLD 1회, 각50step/100 model_fn call.
- 영상 heavy 기계적 복구 예비: 기존 의뢰의 1회만 유지, 총최대3회.
- 저장된 final latent 이후 VAE-only 기계적 복구: 기존 전체최대1회.
- 품질 재시도·다른 seed·새 사례: 0회.

구조 추출과 영상 생성 모델을 순차 실행한다. 실제로 사용한 로딩·forward·step·decode를 각각 기록한다. final latent가 있으면 실패한 포장 때문에 sampler를 다시 돌리지 않는다.

원래 C-003의 전체 작업 상한 3시간과 마지막20분 전달 여유를 유지한다. 사소한 운영 수정에 새 연구 단계를 만들지 않는다. 실제 충돌이나 자원 압박이 있으면 중단하고 자동 재개·추가 예산을 만들지 않는다.

## 6. 품질 평가와 기록

비교 질문은 그대로다.

> 같은 외곽선·앵커·noise에서 DYNAMIC이 OUTLINE_ONLY와 HOLD보다 머리·다리 진행을 더 잘 따르는가? target 외형·전체 접근·배경의 손해는 없는가?

전체33프레임, 고정0/4/8/12/16/20/24/28/32, 종료 앵커가 충돌하는29~32를 함께 보고한다. 관측 불가능한 관절·발 접촉은 UNCERTAIN이다. 실제 연속 시청이 없으면 temporal=UNVERIFIED다.

시작 가드의 정책 변경과 영상 방법의 변경을 혼동하지 않는다. 이번에 생성 방법은 바꾸지 않았다. 과거 A/B·C-001·C-002·C-003 중단 기록도 보존한다.

착수 전에 이 amendment와 실제 코드 diff/freeze를 C 연구 브랜치에 기록한다. 완료 후 RESULTS·COSTS·LESSON·HISTORY·ROADMAP을 갱신하고 commit/push·원격 SHA를 확인한다. 신규 품질 결과가 없으면 결과가 있다고 쓰지 않는다.

실제 새 영상·조건·비교 뷰어는 compact, 신규 raw/latent는 full 또는 기존 비공개 보존 경로에 둔다. Spark/Mac /tmp 전송·CRC·manifest·추출·해시를 검증한다. 다시 시작 전 차단되면 기존 미디어 약38MB를 재포장하지 말고 **새 로그와 작은 변경 기록만** 남긴다.

이번 비교 뒤 종료하고, 다음 연구 가설·모델·학습은 자동 시작하지 않는다.

## 검토 근거

- C-003 RESULTS: https://github.com/hyunlord/make-meme/blob/4e546e1971c2545d07883890287838b3a064e669/docs/research/experiments/C-003-internal-structure-conditioning/RESULTS.md
- 사용된 C guard memory.py: https://github.com/hyunlord/make-meme/blob/4e546e1971c2545d07883890287838b3a064e669/docs/research/experiments/C-001-hybrid-endpoint-baseline/code/guard/memory.py
- cgroup별 swap 관측/한도: https://docs.kernel.org/admin-guide/cgroup-v2.html
- PSI 정의와 total 단위: https://docs.kernel.org/accounting/psi.html

이 문서는 검토와 재개 제안이다. 작성 과정에서 Spark·GitHub·가드·모델은 변경하거나 실행하지 않았다.
