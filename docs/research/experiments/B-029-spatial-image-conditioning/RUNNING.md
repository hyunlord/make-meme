# B-029 실제 실행 상태

사전고정 원격 SHA `cbfe745e732102ee59ba640792046e64c369c31d` 확인 후 2026-10-26 03:55:51 UTC 시작했다.

animal METHOD R1 PROBE는 PASS, S는03:55:56 UTC 시작했다. 고정8case 순서와 각 PROBE→S→D를 단일 controller에서 순차 실행한다. reserve/terminal ledger를 별도로 기록하고 실제 receipt·guard·MainPID 종료까지 확인한다. 새 encoder0, 학습0, 재시도0. 최종 상태는 실제 완료 시 갱신한다.

기술 실행과 시각 품질은 분리한다. temporal=UNVERIFIED. 추가 forward·dense attention dump는 없다. 기존 B-0276case 공통 기준선을 보존한다.

04:13:24 UTC animal METHOD R1 완료: 실제40step80forward,40block 각각80gate 적용, finite `[3,17,512,896]`,17frame24fps MP4. 첫 실제 generated 구간은 start1792/length8960/suffix2240/grid5×32×56으로 관측됐다. 이미지 출력 dtype은 FP32였고 gate 평균 오차는1.19e-7. 관측용 추가forward0. animal METHOD R2 S가04:13:30 UTC 시작했다. 현재 sampler reserve2/8, decode완료1/8, 재시도0.

04:30:57 UTC animal METHOD R2도40/80·40block80gate·finite17frame 완료. METHOD2/6, 전체decode2/8. animal CONTROL R1 PROBE 통과 후 S가04:31:02 UTC 시작했다. sampler reserve3/8, 실패/재시도0.

04:48:21 UTC animal CONTROL R1 완료. 실제 CONTROL 모드,40/80·40block80gate·finite17frame, gate 시간별 평균≈1을 확인했다. animal의 두 METHOD와 한 CONTROL이 모두 보존됐다. human METHOD R1 S04:48:26 시작, reserve4/8·decode3/8, 실패/재시도0.

05:05:50 UTC human METHOD R1 완료:40/80·40block80gate·finite17frame. 전체decode4/8(METHOD3,CONTROL1). human METHOD R2 S05:05:55 시작, reserve5/8, 실패/재시도0.

05:23:14 UTC human METHOD R2 완료:40/80·40block80gate·finite17frame. Human pair 완료, 전체decode5/8(METHOD4,CONTROL1). vehicle METHOD R1 S05:23:19 시작, reserve6/8, 실패/재시도0.

05:40:39 UTC vehicle METHOD R1 완료:40/80·40block80gate·finite17frame. 전체decode6/8(METHOD5,CONTROL1). vehicle METHOD R2 S05:40:44 시작, reserve7/8. 마지막 vehicle CONTROL R1까지 고정 순서를 유지하며 실패/재시도0이다.

05:57:58 UTC vehicle METHOD R2 완료:40/80·40block80gate·finite17frame. METHOD6/6 모두 완료, 전체decode7/8. 마지막 vehicle CONTROL R1 S05:58:03 시작, sampler reserve8/8. 실패/재시도0. 이 마지막 case 이후 GPU 실험을 종료한다.

## 최종 종료 — 2026-10-26 06:15:20 UTC

8/8 sampler 및 decode 완료, 24/24 worker COMPLETED. 각 40step·80forward와 40block×80 gate, finite 17frame raw 확인. 자체 worker/watchdog 종료 및 보호 서비스 유지·swap0 확인. 신규 실행은 종료했다. 최종 실측은 MEASUREMENTS.json/COSTS.md를 참조한다.
