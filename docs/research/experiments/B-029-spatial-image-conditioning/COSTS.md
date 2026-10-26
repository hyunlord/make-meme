# B-029 실제 비용과 종료 상태

## 실행 범위

METHOD 6개 + CONTROL 2개, sampler 8/8, decode 8/8, PROBE 8/8. 각 sampler는 40 scheduler step·80 DiT forward이며 40개 cross-attention block 각각 80 gate 호출을 확인했다. Encoder·학습·다운로드·재시도는 0회다. 모든 raw는 finite, [3,17,512,896], 17프레임이며 원본 FPS 미확인 공개 프레임의 preview는 24fps다.

## 같은 B-027 case와 실행 비용 비교

각 행의 B-027은 같은 task/reference의 기존 결과다. CONTROL은 해당 R1 기준선을 반복 기재한 것이며 기준선을 새로 생성하지 않았다. S 시간에는 모델 로딩·샘플링·최종 저장이 포함되고 D는 별도 worker다. CPU 비교 렌더링 및 전송이 다음 GPU 실행과 중첩됐으므로 격리 성능 benchmark가 아니다.

| Case | B027 S 초 | B029 S 초 | 차이 초 | B027 D 초 | B029 D 초 | B027 CUDA peak GiB | B029 CUDA peak GiB |
|---|---:|---:|---:|---:|---:|---:|---:|
| animal/METHOD/R1 | 1020.901 | 1033.089 | +12.187 | 15.242 | 15.212 | 33.847 | 33.848 |
| animal/METHOD/R2 | 1010.614 | 1032.124 | +21.509 | 15.223 | 15.216 | 33.847 | 33.848 |
| animal/CONTROL/R1 | 1020.901 | 1022.760 | +1.858 | 15.242 | 15.203 | 33.847 | 33.848 |
| human/METHOD/R1 | 1013.827 | 1028.653 | +14.826 | 15.215 | 15.162 | 33.847 | 33.848 |
| human/METHOD/R2 | 1012.767 | 1023.585 | +10.817 | 15.179 | 15.177 | 33.847 | 33.848 |
| vehicle/METHOD/R1 | 1017.030 | 1023.524 | +6.494 | 15.227 | 16.231 | 33.847 | 33.848 |
| vehicle/METHOD/R2 | 1007.164 | 1018.102 | +10.938 | 14.165 | 15.226 | 33.847 | 33.848 |
| vehicle/CONTROL/R1 | 1017.030 | 1020.608 | +3.578 | 15.227 | 15.220 | 33.847 | 33.848 |

80 forward는 기준선과 같지만 gate의 elementwise 곱셈·연결·작은 관측 비용은 추가된다. NFE가 같다는 사실을 비용 증가가 없다는 주장으로 바꾸지 않는다.

## B-028 역사 비교 — 기준선으로 혼합하지 않음

B-028은 별도 reference 정규화 실험이며 B-029의 공통 기준선은 B-027이다. 아래는 같은 task/reference worker 비용의 맥락일 뿐 품질이나 순수 실행 오버헤드를 분리하는 통제 비교가 아니다.

| Case | B028 S 초 | B028 D 초 | B029 METHOD S 초 |
|---|---:|---:|---:|
| animal/R1 | 1025.960 | 15.234 | 1033.089 |
| animal/R2 | 1040.768 | 16.222 | 1032.124 |
| human/R1 | 1039.223 | 14.198 | 1028.653 |
| human/R2 | 1012.874 | 15.196 | 1023.585 |
| vehicle/R1 | 1017.757 | 15.232 | 1023.524 |
| vehicle/R2 | 1004.818 | 16.224 | 1018.102 |

## 단계별 총시간과 자원

| 항목 | 관측 |
|---|---|
| 첫 PROBE 시작부터 마지막 D 종료 wall | 8368.639초 (139.48분) |
| PROBE 완료 service 시간 합 | 40.558초 |
| S 완료 service 시간 합 | 8202.444초 |
| D 완료 service 시간 합 | 122.647초 |
| mem_available_min | 52.982986 GiB |
| rss_peak | 87.391327 GiB |
| rss_anon_peak | 31.900333 GiB |
| rss_file_peak | 56.642059 GiB |
| cgroup_peak_peak | 62.580566 GiB |
| cgroup_anon_peak | 31.900074 GiB |
| cgroup_file_peak | 36.341099 GiB |
| cuda_peak_allocated_peak | 33.848221 GiB |
| cuda_reserved_peak | 33.892578 GiB |
| swap_used_peak | 0.000000 GiB |

cgroup event의 단계별 관측 최댓값: `{"high": 4512, "max": 0, "oom": 0, "oom_kill": 0}`. high 이벤트는 그대로 보존하며 max/OOM과 구분한다. 시스템 가용 메모리, RSS/anon/file, cgroup, CUDA allocator는 서로 다른 회계이므로 합산하지 않는다.

## 준비·검토·전송 비용의 측정 한계

- 사전 계획·구현·CPU/map 검사·리뷰·등록은 GPU 실행 전 수행했다. 03:34~03:55:51 UTC 구간은 약 21분51초의 묶음 wall이며 순수 CPU 개발 시간으로 분리 계측하지 않았다.
- 실제 CPU 계약은 10 passed in 0.75s. map builder의 최초 클래스명 StopIteration과 pytest 환경변수 누락은 pre-GPU 실패로 보존했다.
- 비교 렌더 시간은 review manifest의 `review_build_seconds_before_manifest`에 기록된 case만 실측으로 사용한다. 첫 animal METHOD R1은 UNMEASURED다.
- 초기 전송 및 정적 visual review의 독립 stopwatch는 UNMEASURED다. 이후 packaging/transfer의 실제 start/end는 전달 장부에서 별도로 보고한다. 파일 mtime으로 추정한 시간을 실측으로 제시하지 않는다.
- 부모 에이전트의 전체17장/local0·8·16 정적 검토와 실제 연속 재생 검수는 별개다. temporal=UNVERIFIED.

## 보존·종료 확인

- 최종 latent를 decode 전에 저장했고 모든 8 case의 실제 raw/MP4를 확인했다.
- 모든 frozen code/config/support 및 원본 producer cache/receipt의 사후 hash 일치를 확인했다.
- 모든 worker guard reason은 service_exit, service returncode 0이며 실제 phase/counter/output 검사도 함께 통과했다.
- 일부 watchdog ExecStopPost의 이미 종료된 pipeline unit 관련 “Unit not loaded” 메시지는 원문 장부에 보존한다. 이를 재시도나 sampler 실패로 바꾸지 않았다.
- 자체 pipeline/watchdog inactive, MainPID=0, 자체 실행 code process 없음. 기존 보호 서비스는 계속 실행 중이다.
- 종료시 MemAvailable 94419180 kB, swap total/free 0 kB. 다음 GPU 작업을 예약하거나 실행하지 않았다.

근거: [MEASUREMENTS.json](MEASUREMENTS.json), 비공개 execution ledger·end_state·각 단계 memory trace. 시각 결과와 채택 판단은 RESULTS/ABLATIONS에 별도로 기록한다.
