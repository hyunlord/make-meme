# B-014 실행 기록

**RUNNING / ADAPTATION 감사·CPU 계약 준비 / GPU NOT_RUN.** 시작원격 `152b6771397176ac0eb1860debc0902331c5d523`를 확인하고 기존 문서worktree를 ff-only로 갱신했다. [PLAN](PLAN.md)과 [결정](../../decisions/20261024-B-013-review-and-B-014.md)을 실행 지시로 사용한다. 2026-10-24 02:40KST(2026-10-23 17:40UTC)를 보수적 시작으로 계산하며3시간 harddeadline20:40UTC,workerdeadline20:30UTC다.

1. 진행: 공식 Eq.(2)/Wan pipeline/lp_utils/yaml과SCAIL 연결 감사, 변경점·불변조건 CPU 검증.
2. 대기: 실제코드/filter/schedule/budget/input 고정·commit/push·독립검토.
3. 조건부: B-013 LAB_MOV Pcache/noise를 읽기전용으로 재사용,PROBE최대1·S최대1·D최대1. P0·재시도0·모델/데이터다운로드/학습/imagegen0. CPU계약실패면ADAPTATION_BLOCKED.
4. 대기: SOURCE/B013MOV/STILL/ALG 전체17장·local0/12/14/16, 전신/국소/개체/형상/접촉 분리. 시간품질은 연속시각관찰 없으면UNVERIFIED.
5. 대기: RESULTS/ADAPTATION_AUDIT/이론·실측·재현·원격동기화·비공개ZIP 양호스트검증.

기존72GiB시작/24GiB실행headroom·swap0·타서비스 보호, tiny CUDA 선행/anchor·mixedloader·FlashAttention·단계분리·final latent 우선보존을 유지한다. 원본negative+CFG*(lowpositive-lownegative)를 순차3forward로 초기8step에만 적용해40step88forward를 기대한다. 단순low-low CFG, batch3, first-frame overwrite, cache수정은 하지 않는다. 이전B/A기록과자산은보존한다.
