# C-008 PLAN — VACE 조건 인코딩 불일치 규명

- experiment_id: C-008-conditioning-parity
- 작성: 2026-10-31 (Claude Code 신규 세션)
- parent: C-007 (19e110431e90931c98277b7e94d6879268929336), 학습·cache 근거 C-006 (c4aef32)
- 의뢰서: [work_orders/C008_CONDITIONING_PARITY_CLAUDE_FRESH_SESSION_KO.md](../../work_orders/C008_CONDITIONING_PARITY_CLAUDE_FRESH_SESSION_KO.md)

> 기록 순서 고지: 이 PLAN은 실행 전 커밋되지 않았다. 첫 GPU 진단(c-elephant)을 실행한 뒤 같은 세션에서 작성했다.
> 질문·고정 변수·예산은 의뢰서 그대로이며, 결과를 본 뒤 바꾼 판정 기준은 없다.

## 인수 상태
- 문서 branch `docs/c-research-20261028`, HEAD=19e1104 (원격 동일). Mac worktree와 Spark 실행 디렉터리는 별개다.
- Spark: 기존 research Python, 기존 DiffSynth 사본(git 아님; `wan_video_vae.py` sha256 17ad9aa4…, `wan_video.py` e3ab58df…), 기존 1.3B 가중치.
- 실행: C-001 `run_guarded.py` + C-003 guard를 변경 없이 사용. stage는 C-007과 같은 cpu→heavy 구조.

## 질문
학습 cache(C)와 실제 생성(G)의 VACE context가 다른 최초 경계와 원인은 무엇이며, 최소 수정 후 두 경로가 독립적으로 일치하는가.

## 경로
- C: C-006 `cache_conditions.py`와 동일 (T5+VAE만 적재, `WanVideoUnit_VACE().process` 직접 호출).
- G: C-007 `generate_video.py`의 `condition()`과 `pipe(...)` 호출 그대로. denoising 첫 iteration 직전 `progress_bar_cmd`에서 중단(DiT forward 0).
- R: 같은 VAE의 causal 계약 검사(첫 프레임 단독/prefix5/미래 프레임 교체).

## 고정
416×240, 33f, BF16, tiled (30,52)/(15,26), 기존 앵커·윤곽·prompt, vace_reference_image=None, 가중치·가드 불변.

## 예산
public VAE encode ≤64(+8), decode ≤4, DiT probe ≤40, 분기A 영상 ≤2, 학습 0, 다운로드 0, 3시간.
