# B-015 진행 기록

2026-10-24 KST. 시작 원격 HEAD `7214ed16e550169d92eaeb5e98a36fc7fc5d5a5a`를 확인했다. [PLAN](PLAN.md)과 [결정](../../decisions/20261024-B-014-review-and-B-015.md)은 변경하지 않는다.

## 착수 — GPU NOT_RUN

B-013 LAB_STILL의 실제 조건 캐시를 읽기 전용으로 재사용하고 B-014 MOV와 실제16leaf의4변경/12보존을 검증한다. 동일한 필터 tensor를 STILL parent에 묶은 새 sidecar로 저장한다. MOV sidecar 또는 원본 캐시는 수정하지 않는다.

B-014 수식·필터·활성구간·정밀도·sampler 코드는 유지한다. 최소 parent 검사와 실제 입력·deadline 연결만 변경하며 CPU 검증·실행 코드·config·parent 계보를 commit/push한 뒤 PROBE→S→D를 진행한다.

예산 P0, PROBE/S/D 각최대1, 재시도0. 40step88forward, ratio0.4·i0..7·CFG5, 같은 source f7~23·17f24fps. 3시간 작업 상한은 보수적으로19:00UTC부터22:00UTC까지 계산하며 worker cutoff는 더 이른21:25UTC다. 72GiB 시작/24GiB 실행·swap0 가드를 유지한다.

이 한 칸으로 CFG/ALG×MOV/STILL 비교를 닫는다. ALG_STILL의 정적인 외형이 좋아도 기존 ALG_MOV의 목표품질 실패를 뒤집지 않는다. 정량 보정 없는 interaction/gain, branch norm 기반 cosine/벡터 상쇄 수치는 만들지 않는다. 연속 재생 품질을 관찰하지 못하면 temporalUNVERIFIED다.
