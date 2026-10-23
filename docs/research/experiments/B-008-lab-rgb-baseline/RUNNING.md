# B-008 실행 기록

상태: RUNNING / P·PROBE·S·D NOT_RUN.

시작 원격 HEAD: `c7d38938e51943576637611cdec9ae51902e0d65`.
실행 시작2026-10-23 01:28UTC, 절대 종료04:28UTC. 사용자 지시에 따른 P1/PROBE1/S1/D1, 실패 포함·재시도0. 기존 A/G/H와 미추적 자산을 보존하고 별도 B-008 실행 폴더를 사용한다.

## 단계별 완료 계획

1. IN_PROGRESS: 기존 Lab 입력·prompt·RED mask·17f24fps 계보 확인 및 명시적 case 계약 구현/CPU fixture.
2. PENDING: 코드·config·입력 해시 사전 고정과 공개 push, 독립 검토.
3. PENDING: fresh P → 종료/회복 → PROBE → 종료/회복 → S → 종료/회복 → D. 선행 실패 시 후속 미실행.
4. PENDING: 전체17장·native24fps 비교·품질 축별 정적 검토·한국어 수학 설명.
5. PENDING: 최종 GitHub 기록·원격 SHA와 비공개 ZIP 양호스트 CRC/해시 검증·자체 프로세스 종료 확인.

이번 목표는 CUDA 원인 감사 확대가 아니라 실제 Lab identity와 RGB driving motion의 첫 품질 기준선이다. sampler 수학·정밀도·72/24GiB 및 swap0 가드는 유지한다. 실제 연속 재생을 관찰하지 못한 경우 temporal=UNVERIFIED다.
