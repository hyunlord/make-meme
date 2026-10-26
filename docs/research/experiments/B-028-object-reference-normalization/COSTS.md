# B-028 실제 비용과 기술 수용

최종 sampler 6/6, decode 6/6, worker 21/21 COMPLETED. 실제 각 40step·80forward로 총 240step·480forward다. final latent는 decode 전에 저장했고 여섯 raw/MP4를 보존했다. 재시도·학습·설치·새 다운로드 0.

실행 첫 ENC부터 마지막 D 종료까지 **6291.113초(104.852분)**. 준비·검토·전송은 이 구간 밖 비용도 있으므로 전체 연구 wall-clock과 같지 않다.

| 구간 | 실행 수 | worker 시간 합계(초) |
|---|---:|---:|
| ENC | 3 | 24.244 |
| PROBE | 6 | 30.371 |
| S | 6 | 6141.400 |
| D | 6 | 92.306 |

| case | sampler 초 | decode 초 |
|---|---:|---:|
| animal/R1 | 1025.960 | 15.234 |
| animal/R2 | 1040.768 | 16.222 |
| human/R1 | 1039.223 | 14.198 |
| human/R2 | 1012.874 | 15.196 |
| vehicle/R1 | 1017.757 | 15.232 |
| vehicle/R2 | 1004.818 | 16.224 |

## 메모리: 서로 다른 회계

아래 값을 합산하지 않는다. RSS는 관측된 개별 process 최대이며 여러 process 합이 아니다. 파일 mapping과 allocator 예약은 물리적인 추가 사본과 같지 않다.

| 관측 | GiB |
|---|---:|
| mem_available_min | 49.157 |
| rss_peak | 84.884 |
| rss_anon_peak | 31.920 |
| rss_file_peak | 55.070 |
| cgroup_peak_peak | 62.583 |
| cgroup_anon_peak | 31.920 |
| cgroup_file_peak | 40.553 |
| cuda_peak_allocated_peak | 33.847 |
| cuda_reserved_peak | 33.893 |

Swap 사용 관측0. cgroup high 이벤트는 최대6315로 **0이 아니며**, max/oom/oom_kill은 관측0이다. high는 압력/회수 관련 이벤트이며 여기서 OOM 또는 원인 확정으로 해석하지 않는다. 모든 terminal reason은 service_exit, returncode0이며 guard 종료는 없었다. 불완전 JSONL 행0. 일부 S 중 CPU 비교 렌더와 전송이 겹쳐 고립된 속도 benchmark가 아니다.

03:31:53 UTC 마지막 D 종료 후 두 소유 unit inactive, 보호된 기존 서비스 PID 유지, MemAvailable 94026916kB(89.671GiB), swap0을 확인했다.

## 증거와 한계

- [MEASUREMENTS.json](MEASUREMENTS.json): 실제 단계 receipt·counter·phase·자원·파일 SHA256.
- [CONDITIONS.json](CONDITIONS.json): own-parent 비교6변경/10보존, encoder 호출 장부.
- [PREREGISTRATION.json](PREREGISTRATION.json): 실행 전 code/config/input 고정.
- [REPRODUCE.md](REPRODUCE.md): 재현과 CPU 요약 방법.

CPU 요약 최초 저장에서 root reports 폴더 누락 오류가 있었고 폴더 생성 후 reporter만 다시 실행했다. GPU나 sampler 재시도는 아니다. watchdog 종료 시 이미 사라진 자기 pipeline unit에 대한 unit-not-loaded 메시지도 원문 로그에 보존했다. 실제 결과·counter·파일과 service receipt를 함께 판정했다.

기술 실행 COMPLETED는 시각 과제 PASS가 아니다. 원본 reference의 낮은 해상도와 가림 누락은 q=0.8 확대 후에도 남는다. temporal=UNVERIFIED이며 실제 연속 시청 판정을 하지 않았다.
