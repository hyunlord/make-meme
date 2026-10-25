# B-027 실행 비용

**21/21 worker COMPLETED**: ENC 3회, PROBE 6회, S 6회, D 6회. 실제 sampler는 총 240step·480forward였다. 모든 단계의 supervisor는 `service_exit`, returncode 0을 기록했다. 아래 수치는 실제 receipt와 phase/resource log에서 추출했다.

| 과제 | 단계 | 상태 | service elapsed (s) |
|---|---|---|---:|
| animal | ENC | COMPLETED | 93.912 |
| animal | R1_PROBE | COMPLETED | 6.091 |
| animal | R1_S | COMPLETED | 1020.901 |
| animal | R1_D | COMPLETED | 15.242 |
| animal | R2_PROBE | COMPLETED | 5.054 |
| animal | R2_S | COMPLETED | 1010.614 |
| animal | R2_D | COMPLETED | 15.223 |
| human | ENC | COMPLETED | 92.928 |
| human | R1_PROBE | COMPLETED | 6.077 |
| human | R1_S | COMPLETED | 1013.827 |
| human | R1_D | COMPLETED | 15.215 |
| human | R2_PROBE | COMPLETED | 5.079 |
| human | R2_S | COMPLETED | 1012.767 |
| human | R2_D | COMPLETED | 15.179 |
| vehicle | ENC | COMPLETED | 84.782 |
| vehicle | R1_PROBE | COMPLETED | 7.092 |
| vehicle | R1_S | COMPLETED | 1017.030 |
| vehicle | R1_D | COMPLETED | 15.227 |
| vehicle | R2_PROBE | COMPLETED | 5.052 |
| vehicle | R2_S | COMPLETED | 1007.164 |
| vehicle | R2_D | COMPLETED | 14.165 |

## 비용 집계

| 단계 | 완료/계획 | worker 누적 (s) |
|---|---:|---:|
| ENC | 3/3 | 271.622 |
| PROBE | 6/6 | 34.445 |
| S | 6/6 | 6082.304 |
| D | 6/6 | 90.251 |

정상 worker service elapsed 합계는 **6478.622초 (107.977분)**다. 로딩·조건 계산·샘플링·디코딩·worker I/O를 포함하며 GPU kernel 시간은 아니다. 준비·검토·전송 등을 포함한 전체 wall-clock과 구분한다.

사전 worker 진입 거절 **3건**은 별도다: ENC 상대 경로 오류, 소유 watchdog unit 재시작 거절, R1_PROBE의 `PROBE` 인자 오류. 마지막 오류는 attempt 예약·import 이전 assertion에서 종료됐다. 이 세 건을 sampler retry나 정상 worker로 세지 않는다.

## 메모리 회계

| 관측량 | GiB |
|---|---:|
| mem_available_min | 52.634808 |
| swap_used_peak | 0.000000 |
| rss_hwm_peak | 83.138382 |
| rss_peak | 83.138382 |
| rss_anon_peak | 31.929604 |
| rss_file_peak | 52.867771 |
| cgroup_current_peak | 62.476723 |
| cgroup_peak_peak | 62.585609 |
| cgroup_anon_peak | 31.929604 |
| cgroup_file_peak | 40.593021 |
| cuda_allocated_peak | 31.424842 |
| cuda_reserved_peak | 33.892578 |
| cuda_peak_allocated_peak | 33.846958 |

시스템 가용량, RSS/RssAnon/RssFile, cgroup anon/file/current/peak, CUDA allocated/reserved/peak는 중첩되는 서로 다른 회계이므로 합산하지 않았다. 서로 다른 시점의 최대값을 동시에 발생한 한 장면으로 해석하지 않는다. RSS는 관측된 개별 process 최대값이다. cgroup event는 누적 counter 관측치이며 단독 원인 판정이 아니다.

`memory.events.high`의 단계별 관측 최대값은 **6387**, `max`·`oom`·`oom_kill`은 **0**이었다. `high`는 해당 cgroup의 메모리 제한 관련 누적 사건이며 OOM 발생이나 guard 실패와 같지 않다. RSS가 cgroup charge보다 큰 관측도 계정 차이로 그대로 보존했다.

상세 원시 단위와 각 단계 counter·guard·memory는 [MEASUREMENTS.json](MEASUREMENTS.json)에 있다. [reporting_code/README.md](reporting_code/README.md)의 CPU 요약기로 재현할 수 있다. 비용 및 출력 파일 성공은 시각·시간 품질 PASS가 아니다.

## 준비 비용과 전체 시간 경계

공개 데이터 다운로드는 **832,766,765 bytes**, **124.402632초**였다. 7개 sequence에서 12개 입력 후보 묶음을 검토했다. 다운로드 5GiB 상한 안에 있으며, 실제 사용·선정 범위와 이용 조건은 기존 다운로드/입력 명세에 기록돼 있다.

CPU decode·전처리·선정의 개별 시간은 계측되지 않았다(**UNINSTRUMENTED**, 0초가 아님). 위 worker 합계에서 이 비용을 누락한 채 전체 실험 비용이라고 부르지 않는다. 사전 실행 실패 중 R1_PROBE 인자 오류의 service elapsed는 **1.054931초**(returncode 1)이며 정상 worker 합계와 별도로 기록한다. 앞선 ENC launch 거절 2건에는 종료시각이 없어 개별 경과시간을 산출하지 않았다. 세 실패 모두 전체 wall-clock 범위에 포함된다.

전체 작업 시작은 **2026-10-25 15:11:00 UTC**, 마감은 **23:11:00 UTC**다. 최종 wall-clock은 결과 검토·압축·전송·GitHub 기록을 마친 coordinator의 종료시각에서 계산한다. 다운로드와 worker elapsed를 단순 합산한 수치를 전체 wall-clock으로 대신하지 않는다.

## 준비 구간의 상한과 종료 계보

작업시작15:11:00Z에서 첫 실제worker15:22:44.266Z까지704.266초(11분44초)다. 이 구간은 원격 확인·다운로드·선정·CPU전처리·기록·사전오류를 포함하며 순수 전처리CPU시간으로 분해하지 않는다. 마지막D 종료17:20:27.322Z까지는 전체129분27초, 실제worker span은117분43초다. 여기에는 이후 정적 검토·문서·압축·전송이 아직 포함되지 않으며 최종 전달 receipt에서 전체 종료시각을 따로 남긴다.

## 전달 완료 비용

Mac 실제 추출 검증 완료 UTC17:27:39.425267까지 시작 대비8199.425267초(136분39초)다. Spark 압축·CRC·실제추출25.510초, Spark→Mac 전송30.025초, Mac CRC·실제추출3.702초를 실측했다. 중간 검토·동기화·대기까지 포함한 wall-clock이며 agent token/인간 노동 비용은 계측하지 않았다. 이 전달 receipt의 마지막 Git 게시 시간은 이후 별도이며 실험 실행을 추가하지 않는다. 자세한 검증은 [DELIVERY](DELIVERY.md)에 있다.
