# B-013 실행 기록

**RUNNING / 양 P 완료·조건 비교 PASS / PROBE·S·D 순차 진행.** 시작2026-10-24 00:43 KST(2026-10-23 15:43 UTC), hard deadline19:43 UTC, worker deadline19:30 UTC. 시작 원격 HEAD `28a8540172768481efad7013281a7ce649985245`를 확인했고 기존 문서 worktree를 fast-forward로 갱신했다. A와 이전 B 입력·결과·사용량은 보존한다.

[PLAN](PLAN.md), [전환 결정](../../decisions/20261024-B-012-review-and-B-013.md)에 따라 기존 B-012 source[7,24) driving RGB/mask와 B-009 실제 Lab RGB·RED+WHITE reference mask를 재사용한다. 신규 LAB_MOV/LAB_STILL 각각1회, full sampler 최대2회·실패포함·재시도0, 각 조건 P/PROBE/S/D 최대1회다. source MOV/STILL은 재생성하지 않는다.

1. COMPLETED: 실제 입력76개 byte 계보·참조 외형·기존 자원/코드 검토. 새 crop·mask·사진 편집은 없다. 전처리 CPU helper는 대응 B-012 driving과 정확히 일치한다.
2. PREREG_READY: Lab prompt/config/18개 실행 코드 해시 고정. 내부4변경/12보존 및 대응 B-012의7변경/9보존 검사와 reference-mask prefix/zero suffix 검사 준비. CPU9검사·864개 실행 전 무결성 검사 및 별도 read-only 검토 PASS. 실제 P latent 통과를 뜻하지 않는다. typecheck는 NOT_CLEAN이며 새 comparator의 dynamic interface diagnostics86개를 별도로 공개했다.
3. 양 P COMPLETED: 사전 고정 `f02896f825703a321c84127d4ef8135720176811` 원격 확인 후 실제 Lab 조건을 각각 인코딩했다. 내부4변경/12보존 및 대응 B-0127변경/9보존 PASS, 모든 보존 leaf는 bit-exact다. positive T5는91→108토큰, negative는1토큰이며 길이 보정은 없다. 두 worker 종료 후84.099GiB가용·swap0·owned unit inactive를 확인했다. 각 PROBE/S/D를 순차 실행하며 조건·안전 실패는 후속 중지, 단순 첫 출력 품질 실패는 STILL 생략 사유가 아니다.
4. NOT_RUN: 사전local0/12/14/16 및 전체17장, 전신 자세/국소roll/실제개체·체형 별도 관측. temporal은 실제 연속 품질 관찰이 없으면 UNVERIFIED.
5. PENDING: 결과·수학·실측·재현·GitHub 원격 동기화, 비공개 ZIP 양호스트 CRC/hash.

기존 tiny CUDA 선행/anchor·mixed loader·FlashAttention·phase 분리·final latent 저장과72GiB시작/24GiB실행headroom·swap0·타 서비스 보호를 유지한다. 모델·다운로드·학습·LoRA·imagegen·외부 생성0. 완료 후 추가 seed/low-pass/SR/모델 변경을 시작하지 않는다.

B-012 codegraph entry 경고는 TOOLING_WARNING이며 완료된 생성 결과와 분리한다. 정확한 hook 위치/entry 유형은 현재 미확인이고 이번 단계에서 플러그인 삭제·hook 전체 해제·환경 재설치를 하지 않는다.
