# B-014 실행 기록

**RUNNING / ADAPTATION 감사·CPU 계약 준비 / GPU NOT_RUN.** 시작원격 `152b6771397176ac0eb1860debc0902331c5d523`를 확인하고 기존 문서worktree를 ff-only로 갱신했다. [PLAN](PLAN.md)과 [결정](../../decisions/20261024-B-013-review-and-B-014.md)을 실행 지시로 사용한다. 2026-10-24 02:40KST(2026-10-23 17:40UTC)를 보수적 시작으로 계산하며3시간 harddeadline20:40UTC,workerdeadline20:30UTC다.

1. 진행: 공식 Eq.(2)/Wan pipeline/lp_utils/yaml과SCAIL 연결 감사, 변경점·불변조건 CPU 검증.
2. 대기: 실제코드/filter/schedule/budget/input 고정·commit/push·독립검토.
3. 조건부: B-013 LAB_MOV Pcache/noise를 읽기전용으로 재사용,PROBE최대1·S최대1·D최대1. P0·재시도0·모델/데이터다운로드/학습/imagegen0. CPU계약실패면ADAPTATION_BLOCKED.
4. 대기: SOURCE/B013MOV/STILL/ALG 전체17장·local0/12/14/16, 전신/국소/개체/형상/접촉 분리. 시간품질은 연속시각관찰 없으면UNVERIFIED.
5. 대기: RESULTS/ADAPTATION_AUDIT/이론·실측·재현·원격동기화·비공개ZIP 양호스트검증.

기존72GiB시작/24GiB실행headroom·swap0·타서비스 보호, tiny CUDA 선행/anchor·mixedloader·FlashAttention·단계분리·final latent 우선보존을 유지한다. 원본negative+CFG*(lowpositive-lownegative)를 순차3forward로 초기8step에만 적용해40step88forward를 기대한다. 단순low-low CFG, batch3, first-frame overwrite, cache수정은 하지 않는다. 이전B/A기록과자산은보존한다.

## 실행 전 계약 고정

CPU 계약9개 PASS, 실제 부모 cache16leaf 및 원본/RNG 불변 PASS, 별도 코드 검토 PASS. 실행 manifest SHA `71be87d69e5e10d6e7ac52219123413aa4582a3f5c4b8ec6b0816b96dc8965cb`를 고정했다. 공개27개 code/config와 비공개 allowed-process config1개를 실제 해시 대조했다. Spark의 PROBE/S/D 세 worker는 총330개 manifest 항목을 검증했다. 가중치 전체 신규 재해시는 하지 않았으며 기존 receipt 및 fresh size/mtime를 사용한다.

ALG0..7 활성,8..39 기존 CFG;40step·88forward. P0/PROBE최대1/S최대1/D최대1, 재시도0. 기존 runtime24GiB/start72GiB·swap0 가드 유지. CPU fixture는14B numeric replay나 품질 통과가 아니다. 초기 helper의 exhaustive match fallback 진단을 계산 변경 없이 수정해 typecheck0error/0warning을 확인했다. 최종 CPU9개는0.69초 PASS다. 과거 진단과 superseded receipt는 비공개에 보존했다. 기존 동적 runtime 전체 strict typing을 새로 확립했다는 주장은 하지 않는다.

`configs/allowed_gpu_processes.json`은 기존 서비스 PID를 담아 비공개로 보존하고 공개 manifest에는 해시만 둔다. 이 커밋 시점 신규 GPU 실행0이다.

## 종료 상태

PROBE/S/D 각1회 COMPLETED, P0, actual40step88forward. 출력과 final latent를 보존했다. 전체17장 정적 검토에서 전신FAIL·국소PARTIAL·개체UNCERTAIN·시간UNVERIFIED, 목표 품질 개선 미입증. 자세한 최종 상태는 RESULTS와 RUN_LEDGER를 따른다. 사전 기록은 변경하지 않는다.
