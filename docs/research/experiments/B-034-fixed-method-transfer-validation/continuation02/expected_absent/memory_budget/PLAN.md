# B-034 MEMORY_BUDGET_01 — 작업 메모리 보호와 전역 관측 분리

기준 ac954015987d7df5d4bf822c852cb8bce065fc9a. 사용자 이번 명시 승인에 따른 새 heavy 시도 최대1회·성공 latent decode 최대1회이며 과거 소진을 복원하지 않는다. 이전 EXPECTED_ABSENT_02 SYSTEM_SWAP 중단·UNKNOWN 원인·실패 장부는 불변이다. 시작 시각2026-10-28T03:53:00Z(최초 도구보다 보수적), 전체 종료05:23:00Z, heavy cutoff05:08:00Z. 운영 수정·CPU 목표04:18:00Z. 마지막15분 기록·전달.

## 사전 고정 계약

시작 MemAvailable≥72GiB, system swap≤64MiB, 10초 관측에서 swap-out 변화 없음·PSI full 비율10% 미만. 실행중 headroom24GiB, 기존 cap=min(64GiB,available−24GiB), high=cap−2GiB 및 MemorySwapMax=0 유지. S0와 전역 counters/history는 STEP부터 decode 종료까지 단일 원장으로 유지한다. 전역swap 증가≥64MiB, 최근10초 swap-out≥64MiB, full PSI≥10%, 자체swap>0/max!=0/OOM증가/명시 allocation 예외, 외부GPU·서비스·신원·관측 실패에 중단한다. 수치는 이번 운영 예산이며 Linux/DGX 공식 안전 보증이 아니다.

작은 안정256KiB는 GLOBAL_SWAP_WARNING이며 과거 원인UNKNOWN. 누락·권한 오류를0으로 만들지 않는다. host 실제page size를 사용하며 system/cgroup PSI·MemoryHigh events를 함께 기록한다. high 증가 자체는OOM이 아니고 cap 자동상향·재시도는0이다.

## 변경·검증·실행 순서

1. 기존 코드/실제 baseline을 읽고 새 시도 전용 복사본의 두 판정 경로에 작은 공통 memory verdict를 연결한다. 기존 loader/bootstrap/OPTIONAL_EXPECTED_ABSENT/신원/종료 guard는 재사용한다.
2. CPU에서256KiB허용, 자체swap/OOM/headroom/급증/swap-out/PSI/관측오류 차단, 실제page size와 단계간S0보존을 검증한다.
3. 새 root/unit/deadline/config·freeze·B007E_LOADER_REPORT 쓰기 경로와 실제 CPU preflight를 확인한다. 공개 계획/코드를 추론 전에 commit한다.
4. 실제 startup10초 통과 시 STEP heavy1회만 실행한다.40step/80forward/clean40 및 atomic final latent readback을 요구한다. 정상 자체종료·회복 뒤 VAE1회. decode실패로 sampler재실행하지 않는다.
5. 성공 시 기존 BASE/FINAL_LATENT_ONLY와 raw·동일RGB_POST 비교. target차체/노출바퀴/열린상부·SUV잔존·접근·보호장면·경계/접촉/그림자 분리. 배경만개선은결합FAIL, BASE의target부재에비회귀PASS없음, temporal UNVERIFIED(연속검수없음).
6. 위험/계약오류면 추가예산없이비교미완료/운영보류 종료. HISTORY/ROADMAP에 운영과과학결과분리, 신규영상없으면품질성과없음. compact/full중복없이 CRC/hash/실제추출/Spark→Mac전송검증, 명시파일만commit/push/remoteSHA확인.

새 launcher/supervisor framework/service manager 없음. BASE/CONTROL 생성·decode,source/reference encoder,imagegen,학습,설치,다운로드0. 모델/정밀도/noise/RNG/scheduler/양CFG/E/M/B033clean_constraint/prompt/crop불변. 서비스/외부프로세스조작,swapoff/swapon,swappiness/reboot/drop_caches/driver/전역설정변경0. 추가사례/seed/설정탐색자동시작없음. 개인경로·신원·가중치·조건tensor는공개하지않는다.
