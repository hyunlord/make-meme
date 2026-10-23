# B-008 실행 기록

상태: RUNNING / P·PROBE·S·D NOT_RUN.

시작 원격 HEAD: `c7d38938e51943576637611cdec9ae51902e0d65`.
실행 시작2026-10-23 01:28UTC, 절대 종료04:28UTC. 사용자 지시에 따른 P1/PROBE1/S1/D1, 실패 포함·재시도0. 기존 A/G/H와 미추적 자산을 보존하고 별도 B-008 실행 폴더를 사용한다.

## 단계별 완료 계획

1. COMPLETED: 기존 Lab 입력·prompt·RED mask·17f24fps 계보 확인 및 명시적 case 계약 구현/CPU fixture.
2. COMPLETED: 코드·config·입력 해시 사전 고정과 공개 push, 독립 검토.
3. IN_PROGRESS: fresh P → 종료/회복 → PROBE → 종료/회복 → S → 종료/회복 → D. 선행 실패 시 후속 미실행.
4. PENDING: 전체17장·native24fps 비교·품질 축별 정적 검토·한국어 수학 설명.
5. PENDING: 최종 GitHub 기록·원격 SHA와 비공개 ZIP 양호스트 CRC/해시 검증·자체 프로세스 종료 확인.

이번 목표는 CUDA 원인 감사 확대가 아니라 실제 Lab identity와 RGB driving motion의 첫 품질 기준선이다. sampler 수학·정밀도·72/24GiB 및 swap0 가드는 유지한다. 실제 연속 재생을 관찰하지 못한 경우 temporal=UNVERIFIED다.

## 실행 전 검증

CPU fixture5개(0.76초), critical Ruff와 syntax 검사가 통과했다. 전체 typecheck는 NOT_CLEAN701errors/15files로 별도 기록했다. 신선한 입력 파일·원본34PNG와 독립 CPU 전처리 hash를 확인했고, 실제 P는 같은4개 tensor shape/dtype/hash 일치를 검사한다. 원격 코드/upstream/input424개와 로컬 실행manifest20개 hash가 일치한다. 실제 입력 시트를 보았고 RED 대응·착석 참조·직립 source와 얇은 발/바닥 mask 결함을 확인했다. GPU는 아직 NOT_RUN.

## Lab P 실행 시작

사전 고정 commit `e1424cb088c745ef83ee1ce5d4f4ee05a1e22dec`와 원격 SHA 일치 확인. 입력·코드 독립 검토 통과 후 P1을 시작했다. P에는 DiT가 없으며 기존 Lab 입력에서 새 조건·noise·RNG를 계산한다. 후속 PROBE/S/D는 직전 완료·종료·자원 회복에만 진행한다.

## Lab P 통과

P1은 guarded118.06초에 service_exit0·자체 unit inactive로 완료됐다. Lab 새 캐시는17,685,156bytes, 실제 noise는FP32 `[16,5,112,64]`, reference `[16,1,112,64]`, driving `[16,5,56,32]`, text `[44,4096]`다. 독립 CPU 전처리4개 hash가 실제 P와 일치했다. flattened initial noise 값 hash는 같은 seed/element 수인 H와 같게 관측됐지만 shape는 다르며, 일치를 요구하거나 H cache를 재사용하지 않았다. 검증 대상은 이번 Lab P→S 값/shape/state 계보다. 종료·자원 회복 후 PROBE1으로 진행한다.

## PROBE 통과 / S 시작

PROBE1 guarded6.063초, 실제 tiny CUDA 연산·16leaf 값/device·RNG 검증과 정상 종료를 확인했다. 선행 gate·자원 회복 후 S1을 시작했다. 완료되지 않은 sampler·영상 품질을 PASS로 취급하지 않는다.

## S 첫 forward 통과

실제 첫 forward 완료가 stage 약115.2초에 관측됐다. 캐시 복원·anchor 재검사·DiT device 이동을 통과했고4/40step·8forward까지 확인했다. 이 시점에는 sampler/final latent/video 완료를 주장하지 않는다. 최근 headroom약52.4GiB,swap/OOM0.
